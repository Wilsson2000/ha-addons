"""Patch upstream ha-mcp app start.py to use a user's long-lived token."""
import sys
from pathlib import Path

path = Path(sys.argv[1])
src = path.read_text()

replacements = [
    (
        '    os.environ["HOMEASSISTANT_URL"] = "http://supervisor/core"\n',
        '    os.environ["HOMEASSISTANT_URL"] = (\n'
        '        (config.get("ha_url") or "").strip() or "http://127.0.0.1:8123"\n'
        '        if (config.get("ha_token") or "").strip()\n'
        '        else "http://supervisor/core"\n'
        '    )\n',
    ),
    (
        '    os.environ["HOMEASSISTANT_TOKEN"] = supervisor_token\n',
        '    _user_token = (config.get("ha_token") or "").strip()\n'
        '    os.environ["HOMEASSISTANT_TOKEN"] = _user_token or supervisor_token\n'
        '    if _user_token:\n'
        '        log_info("Using long-lived access token from app options (acts as that user)")\n'
        '    else:\n'
        '        log_warning("ha_token not set, falling back to the Supervisor token")\n',
    ),
]
for old, new in replacements:
    if src.count(old) != 1:
        sys.exit(f"patch_start.py: anchor not found exactly once: {old!r}")
    src = src.replace(old, new)

# Upstream prints a generic auth line; drop the misleading one.
src = src.replace('    log_info("Authentication configured via Supervisor token")\n', "")
path.write_text(src)
print("start.py patched")
