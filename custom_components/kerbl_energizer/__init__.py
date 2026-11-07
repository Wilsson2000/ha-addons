"""Kerbl Smart Energizer (AKO) via the Kerbl Welt cloud."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KerblClient
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN
from .coordinator import KerblCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type KerblConfigEntry = ConfigEntry[KerblCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: KerblConfigEntry) -> bool:
    client = KerblClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_ACCESS_TOKEN),
        entry.data.get(CONF_REFRESH_TOKEN),
    )
    coordinator = KerblCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KerblConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
