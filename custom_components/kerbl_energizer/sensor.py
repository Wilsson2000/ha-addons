"""Sensors: every numeric top-level field of an energizer becomes a sensor.

v0.1 is deliberately generic, since the energizer payload is not documented.
Fields with 'voltage' in the name get volts, 'battery'/'quality' percent-ish.
"""
from __future__ import annotations

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KerblConfigEntry
from .coordinator import KerblCoordinator
from .entity import KerblEntity


def _label(key: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key).capitalize()


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


async def async_setup_entry(hass: HomeAssistant, entry: KerblConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for device_id, data in coordinator.data.items():
            for key, value in data.items():
                uid = f"{device_id}_{key}"
                if uid in known or not _is_number(value) or key in ("id", "userId"):
                    continue
                known.add(uid)
                new.append(KerblNumberSensor(coordinator, device_id, key))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KerblNumberSensor(KerblEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: KerblCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator, device_id, key)
        self._attr_name = _label(key)
        low = key.lower()
        if "voltage" in low and "battery" in low:
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        elif "voltage" in low:
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        elif low in ("batterystate", "batterylevel"):
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif "quality" in low:
            self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        value = self.device_data.get(self._key)
        return value if _is_number(value) else None
