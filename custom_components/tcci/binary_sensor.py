"""Capteur binaire : au lit."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TcciConfigEntry
from .entity import TcciEntity


async def async_setup_entry(hass: HomeAssistant, entry: TcciConfigEntry, add: AddEntitiesCallback) -> None:
    add([TcciInBed(entry.runtime_data, "au_lit")])


class TcciInBed(TcciEntity, BinarySensorEntity):
    _attr_icon = "mdi:bed"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["status"].get("inBed"))
