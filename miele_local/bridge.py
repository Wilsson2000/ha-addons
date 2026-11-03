"""Miele lokal: probe, commission and MQTT bridge around MieleRESTServer."""
import email.utils
import json
import logging
import os
import sys
import threading
import time

import requests
import urllib3

urllib3.disable_warnings()

OPTIONS = "/data/options.json"
KEYS = "/data/keys.json"
STATE = "/data/state.json"

log = logging.getLogger("miele_local")

# ---------------------------------------------------------------- legacy TLS
import ssl
from requests.adapters import HTTPAdapter


class LegacyTLS(HTTPAdapter):
    """Miele XKM modules use old TLS; allow it (local device, self-signed)."""

    def _ctx(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except (ValueError, AttributeError):
            pass
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        return ctx

    def init_poolmanager(self, *a, **kw):
        kw["ssl_context"] = self._ctx()
        return super().init_poolmanager(*a, **kw)

    def proxy_manager_for(self, *a, **kw):
        kw["ssl_context"] = self._ctx()
        return super().proxy_manager_for(*a, **kw)


SESSION = requests.Session()
SESSION.mount("https://", LegacyTLS())
SESSION.verify = False
SCHEME = {"value": "http"}


def patch_library(scheme):
    """MieleCrypto hardcodes http://; route its calls through SESSION with our scheme."""
    import MieleCrypto

    SCHEME["value"] = scheme

    class _Req:
        @staticmethod
        def _fix(url):
            if url.startswith("http://") and SCHEME["value"] == "https":
                url = "https://" + url[len("http://"):]
            return url

        def get(self, url, **kw):
            kw.setdefault("timeout", 15)
            return SESSION.get(self._fix(url), **kw)

        def put(self, url, **kw):
            kw.setdefault("timeout", 15)
            return SESSION.put(self._fix(url), **kw)

        def __getattr__(self, name):
            return getattr(requests, name)

    MieleCrypto.requests = _Req()


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_keys():
    from MieleCrypto import MieleProvisioningInfo

    opts = load_json(OPTIONS, {}) or {}
    if opts.get("group_id") and opts.get("group_key"):
        keys = {"GroupID": opts["group_id"].strip().upper(), "GroupKey": opts["group_key"].strip().upper()}
        save_json(KEYS, keys)
        return keys
    keys = load_json(KEYS)
    if not keys:
        keys = MieleProvisioningInfo.generate_random().to_dict()
        save_json(KEYS, keys)
        log.info("Ny nyckel skapad (GroupID %s), sparad i /data", keys["GroupID"])
    return keys


# ---------------------------------------------------------------- probe
def probe(host):
    log.info("PROBE %s (bara läsning)", host)
    paths = ["", "Devices", "Devices/", "WLAN", "WLAN/Scan", "Security/Commissioning"]
    for scheme in ("http", "https"):
        for p in paths:
            url = f"{scheme}://{host}/{p}"
            try:
                r = SESSION.get(url, timeout=5,
                                headers={"Accept": "application/vnd.miele.v1+json"})
                body = r.text[:300].replace("\n", " ")
                log.info("%s -> %s %s | %s", url, r.status_code,
                         r.headers.get("Content-Type", ""), body)
            except requests.RequestException as e:
                log.info("%s -> FEL %s: %s", url, type(e).__name__, str(e)[:200])


# ---------------------------------------------------------------- commission
def commission(host):
    keys = get_keys()
    body = json.dumps(keys, sort_keys=True, indent=4)
    headers = {
        "Date": email.utils.formatdate(usegmt=True),
        "Authorization": "MielePairing:Pairing",
        "Content-Type": "application/vnd.miele.v1+json; charset=utf-8",
    }
    ok = False
    for scheme in ("http", "https"):
        url = f"{scheme}://{host}/Security/Commissioning"
        try:
            r = SESSION.put(url, data=body, headers=headers, timeout=10)
            log.info("COMMISSION %s -> %s %s", url, r.status_code, r.text[:300])
            if r.status_code in (200, 201, 204):
                ok = True
                scheme_ok = scheme
                break
        except requests.RequestException as e:
            log.info("COMMISSION %s -> FEL %s", url, e)
    st = load_json(STATE, {}) or {}
    st["commissioned"] = ok
    st["host"] = host
    if ok:
        st["scheme"] = scheme_ok
    save_json(STATE, st)
    if ok:
        log.info("Nyckeln accepterad. Byt mode till run och starta om appen.")
    else:
        log.error("Nyckeln accepterades inte. 403 = maskinen är redan kopplad (återställ Miele@home).")
    return ok


# ---------------------------------------------------------------- run / MQTT
def mqtt_settings():
    token = os.environ.get("SUPERVISOR_TOKEN")
    r = requests.get("http://supervisor/services/mqtt",
                     headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()
    return r.json()["data"]


def run(host, name, poll):
    import paho.mqtt.client as mqtt
    from Server import MieleEndpointConfig

    st = load_json(STATE, {}) or {}
    patch_library(st.get("scheme", "https"))
    keys = get_keys()
    route = st.get("route", "auto") if st.get("host") == host else "auto"
    ep = MieleEndpointConfig({"host": host, "groupId": keys["GroupID"],
                              "groupKey": keys["GroupKey"], "route": route})
    if route == "auto":
        st.update({"host": host, "route": ep.device_route})
        save_json(STATE, st)
    log.info("Ansluten till %s, route %s", host, ep.device_route)

    base = f"miele_local/{name}"
    lock = threading.Lock()
    m = mqtt_settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"miele_local_{name}")
    client.username_pw_set(m.get("username"), m.get("password"))
    client.will_set(f"{base}/availability", "offline", retain=True)

    dev = {"identifiers": [f"miele_local_{name}"], "name": f"{name} (lokal)",
           "manufacturer": "Miele", "model": "Miele@home lokal"}
    avail = {"availability_topic": f"{base}/availability"}

    def disc(component, obj_id, cfg):
        cfg = {**cfg, **avail, "device": dev,
               "unique_id": f"miele_local_{name}_{obj_id}",
               "object_id": f"{name}_lokal_{obj_id}"}
        client.publish(f"homeassistant/{component}/miele_local_{name}/{obj_id}/config",
                       json.dumps(cfg), retain=True)

    def publish_discovery():
        st_t = f"{base}/state"
        disc("sensor", "status", {"name": "Status", "state_topic": st_t,
             "value_template": "{{ value_json.DecodedStatus | default(value_json.Status) }}",
             "json_attributes_topic": st_t})
        disc("sensor", "fas", {"name": "Programfas", "state_topic": st_t,
             "value_template": "{{ value_json.DecodedProgramPhase | default(value_json.ProgramPhase) }}"})
        disc("sensor", "kvar", {"name": "Återstående tid", "state_topic": st_t,
             "unit_of_measurement": "min", "device_class": "duration",
             "value_template": "{{ value_json.RemainingMinutes }}"})
        disc("sensor", "kommando", {"name": "Senaste kommando", "state_topic": f"{base}/result",
             "value_template": "{{ value_json.cmd }} {{ value_json.ok }}",
             "json_attributes_topic": f"{base}/result", "entity_category": "diagnostic"})
        for cmd, label in (("start", "Starta"), ("wakeup", "Väck")):
            disc("button", cmd, {"name": label, "command_topic": f"{base}/cmd",
                 "payload_press": cmd})

    def poll_once():
        with lock:
            j = ep.get_device_summary_annotated()
        client.publish(f"{base}/state", json.dumps(j, default=str), retain=True)
        return j

    def do_cmd(cmd):
        res = {"cmd": cmd, "ok": False, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        try:
            with lock:
                if cmd == "wakeup":
                    res["response"] = ep.set_device_action()
                elif cmd == "start":
                    res["response"] = ep.set_process_action()
                else:
                    res["error"] = "okänt kommando"
            res["ok"] = "error" not in res
        except Exception as e:  # device errors are reported, not fatal
            res["error"] = repr(e)
        log.info("KOMMANDO %s", res)
        client.publish(f"{base}/result", json.dumps(res, default=str), retain=True)
        time.sleep(3)
        try:
            poll_once()
        except Exception:
            pass

    def on_connect(c, userdata, flags, rc, props=None):
        log.info("MQTT ansluten (%s)", rc)
        c.subscribe(f"{base}/cmd")
        publish_discovery()
        c.publish(f"{base}/availability", "online", retain=True)

    def on_message(c, userdata, msg):
        threading.Thread(target=do_cmd, args=(msg.payload.decode().strip(),), daemon=True).start()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(m["host"], int(m["port"]))
    client.loop_start()

    fails = 0
    while True:
        try:
            poll_once()
            if fails:
                client.publish(f"{base}/availability", "online", retain=True)
            fails = 0
        except Exception as e:
            fails += 1
            log.warning("Läsning misslyckades (%s): %r", fails, e)
            if fails == 3:
                client.publish(f"{base}/availability", "offline", retain=True)
        time.sleep(poll)


def main():
    opts = load_json(OPTIONS, {}) or {}
    logging.basicConfig(level=logging.DEBUG if opts.get("debug") else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    host = (opts.get("host") or "").strip()
    mode = opts.get("mode", "probe")
    if not host:
        log.error("Ange host (maskinens IP) i appens inställningar.")
        idle()
    if mode == "probe":
        probe(host)
        idle()
    elif mode == "commission":
        commission(host)
        idle()
    else:
        while True:
            try:
                run(host, opts.get("name", "mrs_potts"), int(opts.get("poll_seconds", 30)))
            except Exception:
                log.exception("Bryggan kraschade, försöker igen om 60 s")
                time.sleep(60)


def idle():
    log.info("Klar. Appen väntar (byt läge i inställningarna och starta om).")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    sys.exit(main())
