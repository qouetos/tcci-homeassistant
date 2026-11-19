"""Boutons : les memes que sur le boitier (utilisables dans des automatisations)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TcciConfigEntry
from .entity import TcciEntity

BUTTONS = {"bouton_1": ("/api/press?b=1", "mdi:bed"),
           "bouton_2": ("/api/press?b=2", "mdi:eye"),
           "annuler": ("/api/undo", "mdi:undo")}


async def async_setup_entry(hass: HomeAssistant, entry: TcciConfigEntry, add: AddEntitiesCallback) -> None:
    add(TcciButton(entry.runtime_data, k, path, icon) for k, (path, icon) in BUTTONS.items())


class TcciButton(TcciEntity, ButtonEntity):
    def __init__(self, coord, key: str, path: str, icon: str) -> None:
        super().__init__(coord, key)
        self._path = path
        self._attr_icon = icon

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.post(self._path)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"TCCI : {err}") from err
        await self.coordinator.async_request_refresh()
