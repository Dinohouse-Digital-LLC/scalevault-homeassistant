"""Config flow for the ScaleVault integration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import BASE_URL, CONF_BASE_URL, CONF_ENCLOSURE_CODE, CONF_SENSOR_ENTITY_ID, DOMAIN, SUBENTRY_TYPE_SENSOR

_UNMAPPED = "Not mapped"


class ScaleVaultConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ScaleVault."""

    VERSION = 1
    MINOR_VERSION = 2

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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Entry point when ScaleVault rejects the stored API key at setup time."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a replacement API key for the entry ScaleVault rejected."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            base_url = reauth_entry.data.get(CONF_BASE_URL, BASE_URL)
            client = ScaleVaultClient(
                async_get_clientsession(self.hass), base_url, user_input[CONF_API_KEY]
            )
            try:
                await client.async_validate()
            except ScaleVaultAuthError:
                errors["base"] = "invalid_auth"
            except ScaleVaultConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_and_abort(
                    reauth_entry, data_updates={CONF_API_KEY: user_input[CONF_API_KEY]}
                )

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @classmethod
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """One subentry per forwarded sensor — see ScaleVaultSensorMappingSubentryFlow."""
        return {SUBENTRY_TYPE_SENSOR: ScaleVaultSensorMappingSubentryFlow}


class ScaleVaultSensorMappingSubentryFlow(ConfigSubentryFlow):
    """Add, or edit, a single sensor -> ScaleVault-enclosure mapping.

    Replaces the old options flow's multi-select-then-map pages: each mapping
    is now its own subentry, addable/editable/removable independently from
    Settings -> Devices & Services -> ScaleVault, with the sensor's own
    friendly name shown instead of a raw entity_id.
    """

    async def _async_form_context(self) -> tuple[list[dict[str, str]], dict[str, str]]:
        """Enclosure dropdown options, plus description placeholders warning if
        Climate History is off — readings from a mapping added now would be
        silently dropped server-side (see ingest's climate_history check)
        until the account enables it, so surface that before saving instead."""
        entry = self._get_entry()
        client = ScaleVaultClient(
            async_get_clientsession(self.hass),
            entry.data.get(CONF_BASE_URL, BASE_URL),
            entry.data[CONF_API_KEY],
        )
        try:
            data = await client.async_get_targets()
        except (ScaleVaultAuthError, ScaleVaultConnectionError):
            data = {}
        targets = data.get("targets", [])
        enclosures = [t for t in targets if t.get("type") == "enclosure"]
        enclosure_options = [{"value": "", "label": _UNMAPPED}] + [
            {"value": t["code"], "label": f"{t['name']} ({t['code']})"} for t in enclosures
        ]
        # Default to "enabled" when the flag is missing (older server) or the
        # fetch above failed — an unrelated network hiccup shouldn't show a
        # scary warning that isn't actually true.
        climate_history_enabled = bool(data.get("climate_history_enabled", True))
        warning = (
            ""
            if climate_history_enabled
            else (
                "\n\n⚠️ Climate History isn't enabled for this ScaleVault account — readings from this "
                "sensor won't be saved until it is. You can still add the mapping now; it'll start working "
                "the moment the feature is turned on."
            )
        )
        return enclosure_options, {"climate_history_status": warning}

    @staticmethod
    def _schema(
        enclosure_options: list[dict[str, str]], *, default_sensor: str | None, default_enclosure: str
    ) -> vol.Schema:
        sensor_selector = selector.selector(
            {"entity": {"domain": "sensor", "device_class": ["temperature", "humidity"]}}
        )
        schema_dict: dict[Any, Any] = {
            (
                vol.Required(CONF_SENSOR_ENTITY_ID, default=default_sensor)
                if default_sensor is not None
                else vol.Required(CONF_SENSOR_ENTITY_ID)
            ): sensor_selector,
            vol.Optional(CONF_ENCLOSURE_CODE, default=default_enclosure): selector.selector(
                {"select": {"options": enclosure_options, "mode": "dropdown"}}
            ),
        }
        return vol.Schema(schema_dict)

    def _title_for(self, sensor_entity_id: str) -> str:
        state = self.hass.states.get(sensor_entity_id)
        return state.name if state else sensor_entity_id

    @staticmethod
    def _data_from(user_input: dict[str, Any]) -> MappingProxyType[str, Any]:
        return MappingProxyType(
            {
                CONF_SENSOR_ENTITY_ID: user_input[CONF_SENSOR_ENTITY_ID],
                CONF_ENCLOSURE_CODE: user_input.get(CONF_ENCLOSURE_CODE) or None,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new sensor -> enclosure mapping."""
        if user_input is not None:
            sensor_entity_id = user_input[CONF_SENSOR_ENTITY_ID]
            return self.async_create_entry(
                title=self._title_for(sensor_entity_id),
                data=self._data_from(user_input),
                unique_id=sensor_entity_id,
            )

        enclosure_options, description_placeholders = await self._async_form_context()
        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(enclosure_options, default_sensor=None, default_enclosure=""),
            description_placeholders=description_placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the sensor and/or enclosure for an existing mapping."""
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            sensor_entity_id = user_input[CONF_SENSOR_ENTITY_ID]
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                unique_id=sensor_entity_id,
                title=self._title_for(sensor_entity_id),
                data=self._data_from(user_input),
            )

        enclosure_options, description_placeholders = await self._async_form_context()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(
                enclosure_options,
                default_sensor=subentry.data.get(CONF_SENSOR_ENTITY_ID),
                default_enclosure=subentry.data.get(CONF_ENCLOSURE_CODE) or "",
            ),
            description_placeholders=description_placeholders,
        )
