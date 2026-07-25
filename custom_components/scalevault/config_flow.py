"""Config flow for the ScaleVault integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import BASE_URL, CONF_BASE_URL, CONF_SENSORS, DOMAIN


class ScaleVaultConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ScaleVault."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the ScaleVault API key (and, in Advanced Mode, a base URL
        override for pointing at a dev/staging server) and validate it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input.get(CONF_BASE_URL, BASE_URL)
            client = ScaleVaultClient(
                async_get_clientsession(self.hass), base_url, user_input[CONF_API_KEY]
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
                    title=title,
                    data={CONF_API_KEY: user_input[CONF_API_KEY], CONF_BASE_URL: base_url},
                )

        schema_dict: dict[Any, Any] = {vol.Required(CONF_API_KEY): str}
        if self.show_advanced_options:
            schema_dict[vol.Optional(CONF_BASE_URL, default=BASE_URL)] = str
        schema = vol.Schema(schema_dict)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> ScaleVaultOptionsFlow:
        return ScaleVaultOptionsFlow()


class ScaleVaultOptionsFlow(OptionsFlow):
    """Pick which climate sensors get forwarded to ScaleVault as telemetry.

    A plain multi-select of `sensor` entities (temperature/humidity device
    class) — see telemetry.py for the state-change listener this feeds.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SENSORS, [])
        schema = vol.Schema(
            {
                vol.Optional(CONF_SENSORS, default=current): selector.selector(
                    {
                        "entity": {
                            "domain": "sensor",
                            "device_class": ["temperature", "humidity"],
                            "multiple": True,
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
