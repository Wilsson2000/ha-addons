"""Diagnostics: full /device response with personal data redacted."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import KerblConfigEntry
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN

TO_REDACT = {
    CONF_EMAIL, CONF_PASSWORD, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN,
    "email", "mac", "identifier", "linkingIdentifier", "imei", "iccid", "serialNumber",
    "latitude", "longitude", "lat", "lng", "lon", "telephoneNumber", "emailAddressesNotifications",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: KerblConfigEntry) -> dict[str, Any]:
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "device_response": async_redact_data(entry.runtime_data.raw, TO_REDACT),
    }
