"""Shared entity base."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KerblCoordinator


class KerblEntity(CoordinatorEntity[KerblCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KerblCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_unique_id = f"{device_id}_{key}"
        data = coordinator.data.get(device_id, {})
        dtype = data.get("deviceType") if isinstance(data.get("deviceType"), dict) else {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=data.get("brand") or "AKO / Kerbl",
            model=dtype.get("name") or data.get("itemNumber") or "Smart Energizer",
            name=data.get("description") or data.get("name") or "Kerbl Smart Energizer",
            sw_version=data.get("firmwareVersion"),
        )

    @property
    def device_data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.data
