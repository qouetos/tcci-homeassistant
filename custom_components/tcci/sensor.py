"""Capteurs : etat, dernier appui et indicateurs de la nuit."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TcciConfigEntry
from .entity import TcciEntity
from .logic import fmt


def _state(d: dict) -> str:
    s = d["status"]
    return "eveille" if s.get("inBed") and s.get("awake") else "au_lit" if s.get("inBed") else "leve"


def _st(key: str, f: Callable[[Any], Any] = lambda v: v) -> Callable[[dict], Any]:
    return lambda d: None if not d["stats"] or d["stats"].get(key) is None else f(d["stats"][key])


@dataclass(frozen=True, kw_only=True)
class TcciSensorDesc(SensorEntityDescription):
    value: Callable[[dict], Any]


MIN = dict(native_unit_of_measurement=UnitOfTime.MINUTES, device_class=SensorDeviceClass.DURATION,
           state_class=SensorStateClass.MEASUREMENT)

SENSORS = [
    TcciSensorDesc(key="etat", device_class=SensorDeviceClass.ENUM, options=["leve", "au_lit", "eveille"],
                   icon="mdi:bed", value=_state),
    TcciSensorDesc(key="dernier_appui", device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:gesture-tap-button",
                   value=lambda d: dt_util.utc_from_timestamp(d["status"]["lastT"]) if d["status"].get("lastT") else None),
    TcciSensorDesc(key="sommeil", icon="mdi:sleep", value=_st("tst", round), **MIN),
    TcciSensorDesc(key="temps_au_lit", icon="mdi:bed-clock", value=_st("tib", round), **MIN),
    TcciSensorDesc(key="efficacite", icon="mdi:percent", native_unit_of_measurement=PERCENTAGE,
                   state_class=SensorStateClass.MEASUREMENT, value=_st("se")),
    TcciSensorDesc(key="latence", icon="mdi:timer-sand", value=_st("sol", round), **MIN),
    TcciSensorDesc(key="eveils", icon="mdi:eye-outline", state_class=SensorStateClass.MEASUREMENT, value=_st("nwake")),
    TcciSensorDesc(key="eveil_nocturne", icon="mdi:weather-night", value=_st("waso", round), **MIN),
    TcciSensorDesc(key="sieste", icon="mdi:sofa", value=_st("nap", round), **MIN),
    TcciSensorDesc(key="coucher", icon="mdi:arrow-down-bold", value=_st("bed", fmt)),
    TcciSensorDesc(key="lever", icon="mdi:arrow-up-bold", value=_st("up", fmt)),
]


async def async_setup_entry(hass: HomeAssistant, entry: TcciConfigEntry, add: AddEntitiesCallback) -> None:
    add(TcciSensor(entry.runtime_data, desc) for desc in SENSORS)


class TcciSensor(TcciEntity, SensorEntity):
    entity_description: TcciSensorDesc

    def __init__(self, coord, desc: TcciSensorDesc) -> None:
        super().__init__(coord, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.key not in ("sommeil", "efficacite"):
            return None
        d = self.coordinator.data
        r = d["row"]
        return {"nuit_du": d["night"].isoformat(), "validee": d["validated"],
                "qualite_sommeil": r.get("qs") or None, "qualite_reveil": r.get("qr") or None,
                "forme_journee": r.get("fj") or None}
