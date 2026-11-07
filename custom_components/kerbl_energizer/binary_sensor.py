"""Binary sensors: every boolean top-level field of an energizer."""
from __future__ import annotations

import re

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KerblConfigEntry
from .coordinator import KerblCoordinator
from .entity import KerblEntity


def _label(key: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key).capitalize()


async def async_setup_entry(hass: HomeAssistant, entry: KerblConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for device_id, data in coordinator.data.items():
            for key, value in data.items():
                uid = f"{device_id}_{key}"
                if uid in known or not isinstance(value, bool):
                    continue
                known.add(uid)
                new.append(KerblBoolSensor(coordinator, device_id, key))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KerblBoolSensor(KerblEntity, BinarySensorEntity):
    def __init__(self, coordinator: KerblCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator, device_id, key)
        self._attr_name = _label(key)
        if key == "isOnline":
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        value = self.device_data.get(self._key)
        return value if isinstance(value, bool) else None
