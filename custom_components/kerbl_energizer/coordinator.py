"""Polling coordinator."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KerblApiError, KerblAuthError, KerblClient, find_energizers
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class KerblCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches /device and keeps energizers keyed by id."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: KerblClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.raw: dict[str, Any] = {}
        self._logged_keys = False

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            raw = await self.client.get_devices_raw()
        except KerblAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KerblApiError as err:
            raise UpdateFailed(str(err)) from err

        self.raw = raw
        entry = self.config_entry
        if (
            entry.data.get(CONF_ACCESS_TOKEN) != self.client.access_token
            or entry.data.get(CONF_REFRESH_TOKEN) != self.client.refresh_token
        ):
            self.hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_ACCESS_TOKEN: self.client.access_token,
                    CONF_REFRESH_TOKEN: self.client.refresh_token,
                },
            )

        devices = find_energizers(raw)
        if not self._logged_keys:
            self._logged_keys = True
            _LOGGER.warning(
                "Kerbl /device groups: %s; energizers found: %d; energizer fields: %s",
                {k: (len(v) if isinstance(v, list) else type(v).__name__) for k, v in raw.items()},
                len(devices),
                sorted(devices[0].keys()) if devices else [],
            )
        return {str(d.get("id")): d for d in devices if d.get("id") is not None}
