"""Configuration : URL du boitier (http://tcci.local) ou du serveur cloud + jeton.

- user / zeroconf : ajout
- reconfigure     : changer l'URL et/ou le jeton (memes entites, memes entity_id)
- reauth          : demande automatique d'un nouveau jeton quand l'ancien est refuse
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_TOKEN, CONF_URL, DOMAIN
from .coordinator import TcciApi, TcciAuthError


def _clean_url(url: str) -> str:
    url = url.strip().rstrip("/")
    return url if url.startswith(("http://", "https://")) else "http://" + url


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

    # ---- ajout
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = _clean_url(user_input[CONF_URL])
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

    # ---- reconfiguration (Parametres -> Appareils et services -> TCCI -> ⋮ -> Reconfigurer)
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            url = _clean_url(user_input[CONF_URL])
            new_tok = (user_input.get(CONF_TOKEN) or "").strip()
            if user_input.get("clear_token"):
                token = None
            else:
                token = new_tok or entry.data.get(CONF_TOKEN)   # vide = on garde le jeton actuel
            other = next((e for e in self._async_current_entries() if e.unique_id == url and e.entry_id != entry.entry_id), None)
            if other:
                errors["base"] = "already_configured"
            else:
                err, st = await self._validate(url, token)
                if err:
                    errors["base"] = err
                else:
                    return self.async_update_reload_and_abort(
                        entry, unique_id=url, title="TCCI cloud" if st.get("server") else "TCCI boîtier",
                        data={CONF_URL: url, CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default=entry.data.get(CONF_URL, "")): str,
                vol.Optional(CONF_TOKEN): str,
                vol.Optional("clear_token", default=False): bool,
            }),
            description_placeholders={"url": entry.data.get(CONF_URL, "")},
            errors=errors,
        )

    # ---- jeton refuse : HA propose de le remplacer (notification "Reconfiguration requise")
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = (user_input.get(CONF_TOKEN) or "").strip() or None
            err, _ = await self._validate(entry.data[CONF_URL], token)
            if err:
                errors["base"] = err
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )
