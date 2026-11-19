"""Integration Home Assistant pour le boitier / serveur TCCI (agenda du sommeil)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, CONF_URL
from .coordinator import TcciApi, TcciCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

TcciConfigEntry = ConfigEntry[TcciCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TcciConfigEntry) -> bool:
    coord = TcciCoordinator(hass, TcciApi(hass, entry.data[CONF_URL], entry.data.get(CONF_TOKEN)))
    await coord.async_config_entry_first_refresh()
    entry.runtime_data = coord
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TcciConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
