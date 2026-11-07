"""Config flow: Kerbl Welt e-mail + password."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KerblApiError, KerblAuthError, KerblClient
from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})


class KerblConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _try_login(self, email: str, password: str) -> tuple[KerblClient | None, str | None]:
        client = KerblClient(async_get_clientsession(self.hass), email, password)
        try:
            await client.sign_in()
        except KerblAuthError:
            return None, "invalid_auth"
        except KerblApiError:
            return None, "cannot_connect"
        return client, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()
            client, error = await self._try_login(email, user_input[CONF_PASSWORD])
            if client:
                return self.async_create_entry(
                    title=f"Kerbl ({email})",
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            client, error = await self._try_login(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if client:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
