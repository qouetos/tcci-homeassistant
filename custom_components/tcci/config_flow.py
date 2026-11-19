"""Configuration : URL du boitier (http://tcci.local) ou du serveur cloud + jeton."""
from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_TOKEN, CONF_URL, DOMAIN
from .coordinator import TcciApi, TcciAuthError


class TcciConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._url: str | None = None

    async def _validate(self, url: str, token: str | None) -> tuple[str | None, dict | None]:
        try:
            st = await TcciApi(self.hass, url, token).get("/api/status")
        except TcciAuthError:
            return "invalid_auth", None
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return "cannot_connect", None
        if not isinstance(st, dict) or "inBed" not in st:
            return "not_tcci", None
        return None, st

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            token = (user_input.get(CONF_TOKEN) or "").strip() or None
            err, st = await self._validate(url, token)
            if err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                title = "TCCI cloud" if st.get("server") else "TCCI boîtier"
                return self.async_create_entry(title=title, data={CONF_URL: url, CONF_TOKEN: token})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default=self._url or "http://tcci.local"): str,
                vol.Optional(CONF_TOKEN): str,
            }),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        self._url = f"http://{discovery_info.host}:{discovery_info.port or 80}"
        await self.async_set_unique_id(self._url)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.hostname.removesuffix(".local.")}
        return await self.async_step_user()
