"""Entite de base."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TcciCoordinator


class TcciEntity(CoordinatorEntity[TcciCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coord: TcciCoordinator, key: str) -> None:
        super().__init__(coord)
        uid = coord.config_entry.entry_id
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_translation_key = key
        server = (coord.data or {}).get("status", {}).get("server")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name="TCCI",
            manufacturer="TCCI",
            model="Serveur cloud" if server else "Boîtier ESP32-C3",
            configuration_url=coord.api.url,
        )
