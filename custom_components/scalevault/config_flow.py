"""Config flow for the ScaleVault integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import BASE_URL, DOMAIN


class ScaleVaultConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ScaleVault."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the ScaleVault API key and validate it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = ScaleVaultClient(
                async_get_clientsession(self.hass), BASE_URL, user_input[CONF_API_KEY]
            )
            try:
                info = await client.async_validate()
            except ScaleVaultAuthError:
                errors["base"] = "invalid_auth"
            except ScaleVaultConnectionError:
                errors["base"] = "cannot_connect"
            else:
                account_id = info.get("account_id")
                if account_id is not None:
                    await self.async_set_unique_id(str(account_id))
                    self._abort_if_unique_id_configured()
                title = info.get("account_name") or "ScaleVault"
                return self.async_create_entry(
                    title=title, data={CONF_API_KEY: user_input[CONF_API_KEY]}
                )

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
