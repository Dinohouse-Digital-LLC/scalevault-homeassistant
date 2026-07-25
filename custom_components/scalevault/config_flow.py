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
from .const import BASE_URL, CONF_BASE_URL, CONF_SENSOR_ENCLOSURE_MAP, CONF_SENSORS, DOMAIN

_UNMAPPED = "Not mapped"


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
    """Pick which climate sensors get forwarded to ScaleVault, and (optionally)
    which enclosure each maps to.

    Step 1 (`init`) is a plain multi-select of `sensor` entities
    (temperature/humidity device class) — see telemetry.py for the
    state-change listener this feeds. Step 2 (`map`) shows one enclosure
    dropdown per selected sensor, populated from `GET /api/ha/targets`, so
    readings can carry an `enclosure_code` and skip ScaleVault's manual
    device mapper entirely. Mapping is optional — an unmapped sensor still
    forwards, and lands in ScaleVault's "unmapped device" list as before.
    """

    def __init__(self) -> None:
        self._sensors: list[str] = []
        self._code_by_label: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._sensors = user_input.get(CONF_SENSORS, [])
            if not self._sensors:
                return self.async_create_entry(data={CONF_SENSORS: [], CONF_SENSOR_ENCLOSURE_MAP: {}})
            return await self.async_step_map()

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

    async def async_step_map(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            new_map = {
                entity_id: self._code_by_label[label]
                for entity_id in self._sensors
                if (label := user_input.get(entity_id, _UNMAPPED)) != _UNMAPPED
            }
            return self.async_create_entry(data={CONF_SENSORS: self._sensors, CONF_SENSOR_ENCLOSURE_MAP: new_map})

        client = ScaleVaultClient(
            async_get_clientsession(self.hass),
            self.config_entry.data.get(CONF_BASE_URL, BASE_URL),
            self.config_entry.data[CONF_API_KEY],
        )
        try:
            targets = await client.async_list_targets()
        except (ScaleVaultAuthError, ScaleVaultConnectionError):
            targets = []
        enclosures = [t for t in targets if t.get("type") == "enclosure"]
        self._code_by_label = {f"{t['name']} ({t['code']})": t["code"] for t in enclosures}
        label_by_code = {code: label for label, code in self._code_by_label.items()}
        options = [_UNMAPPED, *self._code_by_label]

        # Each field's key is the raw entity_id — voluptuous field labels are
        # shown as-is in the HA UI, and there's no per-dynamic-field
        # translation hook, so the sensor's friendly name isn't shown here
        # (it was already visible when picking sensors in step 1).
        current_map: dict[str, str] = self.config_entry.options.get(CONF_SENSOR_ENCLOSURE_MAP, {})
        schema_dict: dict[Any, Any] = {
            vol.Optional(entity_id, default=label_by_code.get(current_map.get(entity_id), _UNMAPPED)): vol.In(options)
            for entity_id in self._sensors
        }

        return self.async_show_form(step_id="map", data_schema=vol.Schema(schema_dict))
