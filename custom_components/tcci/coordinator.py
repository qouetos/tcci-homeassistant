"""Client API + coordinateur de mise a jour."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import logic
from .const import DOMAIN, EVENT_TCCI, HISTORY_DAYS, HISTORY_INTERVAL, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class TcciAuthError(Exception):
    """Jeton refuse."""


class TcciApi:
    def __init__(self, hass: HomeAssistant, url: str, token: str | None) -> None:
        self.url = url.rstrip("/")
        self._session = async_get_clientsession(hass)
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def _req(self, method: str, path: str) -> Any:
        async with self._session.request(method, self.url + path, headers=self._headers,
                                         timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 401:
                raise TcciAuthError
            if r.status == 404:
                return None
            r.raise_for_status()
            return await r.json(content_type=None)

    async def get(self, path: str) -> Any:
        return await self._req("GET", path)

    async def post(self, path: str) -> Any:
        return await self._req("POST", path)


class TcciCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, api: TcciApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self._last_t: int | None = None
        self._saved: dict = {}           # nuits enregistrees (historique), relues toutes les HISTORY_INTERVAL s
        self._saved_key: tuple | None = None
        self._saved_at = 0.0

    async def _async_update_data(self) -> dict:
        try:
            status = await self.api.get("/api/status")
            settings = await self.api.get("/api/settings") or {}
            now = dt_util.now()
            tz = dt_util.get_default_time_zone()
            d = logic.current_night(now)
            ws, we = logic.win(d, tz)
            saved = await self.api.get(f"/api/night?d={d.isoformat()}")
            if saved:
                row = logic.normalize(saved)
            else:
                events = await self.api.get(f"/api/events?from={int(ws.timestamp()) - 43200}&to={int(we.timestamp())}") or []
                row = logic.derive(events, d, tz, settings, now)
            # historique : relu si la nuit en cours change, si elle vient d'etre enregistree/validee, sinon toutes les 5 min
            key = (d, bool(saved), bool(saved and saved.get("validated")))
            if key != self._saved_key or time.monotonic() - self._saved_at > HISTORY_INTERVAL:
                frm = (d - timedelta(days=HISTORY_DAYS)).isoformat()
                self._saved = await self.api.get(f"/api/nights?from={frm}&to={d.isoformat()}") or {}
                self._saved_key, self._saved_at = key, time.monotonic()
        except TcciAuthError as err:
            raise ConfigEntryAuthFailed("Jeton TCCI refusé") from err   # HA propose de saisir un nouveau jeton
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"TCCI injoignable : {err}") from err

        # evenement HA a chaque nouvel appui
        last_t = status.get("lastT") or 0
        if self._last_t is not None and last_t > self._last_t:
            self.hass.bus.async_fire(EVENT_TCCI, {
                "kind": status.get("lastK"), "time": dt_util.utc_from_timestamp(last_t).isoformat(),
                "in_bed": status.get("inBed"), "awake": status.get("awake"),
            })
        self._last_t = last_t
        return {"status": status, "night": d, "row": row, "stats": logic.stats(row),
                "validated": bool(saved and saved.get("validated")),
                "history": logic.history(self._saved, d, row)}
