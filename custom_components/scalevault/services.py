"""Quick-log action services (Phase 3): feeding, watering, cleaning.

Additive and parameterless only, matching ScaleVault's POST /api/ha/actions
guardrails — these services can create a log entry but never edit or delete
one. Each call generates a fresh idempotency key, so accidental duplicate
service calls are harmless on the server side too.
"""

from __future__ import annotations

import uuid
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import DOMAIN

SERVICE_LOG_FEEDING = "log_feeding"
SERVICE_LOG_WATERING = "log_watering"
SERVICE_LOG_CLEANING = "log_cleaning"

ATTR_TARGET = "target"
ATTR_NOTES = "notes"

_ACTION_SCHEMA = vol.Schema(
    {
        # Optional: omit to use the matching ScaleVault select entity's current
        # pick (select.py) — e.g. a dashboard button can call the service with
        # no target and it feeds/waters/cleans whatever the dropdown is set to.
        vol.Optional(ATTR_TARGET): cv.string,
        vol.Optional(ATTR_NOTES): cv.string,
    }
)

_ACTION_BY_SERVICE = {
    SERVICE_LOG_FEEDING: "fed",
    SERVICE_LOG_WATERING: "watered",
    SERVICE_LOG_CLEANING: "cleaned",
}

# Which select entity (see select.py) backs the default target for each action.
_SELECT_KEY_BY_ACTION = {
    "fed": "feeding_select",
    "watered": "enclosure_select",
    "cleaned": "enclosure_select",
}


def _get_entry_data(hass: HomeAssistant) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No ScaleVault connection is configured")
    # Single-account scaffold: services aren't yet bound to a specific config
    # entry, so use whichever one is loaded.
    return next(iter(entries.values()))


def _resolve_target(entry_data: dict[str, Any], action: str, call: ServiceCall) -> str:
    if ATTR_TARGET in call.data:
        return call.data[ATTR_TARGET]
    select = entry_data.get(_SELECT_KEY_BY_ACTION[action])
    code = select.current_code if select else None
    if not code:
        raise HomeAssistantError(
            "No target given and no ScaleVault target is selected — pass a "
            "target or pick one in the matching ScaleVault select entity."
        )
    return code


async def _handle_action(hass: HomeAssistant, action: str, call: ServiceCall) -> None:
    entry_data = _get_entry_data(hass)
    client: ScaleVaultClient = entry_data["client"]
    payload: dict[str, Any] = {
        "action": action,
        "target": _resolve_target(entry_data, action, call),
        "idempotency_key": str(uuid.uuid4()),
        # HA's own configured local time, not the server's (which may be UTC
        # and land on the wrong calendar day near midnight for the user).
        "occurred_at": dt_util.now().isoformat(timespec="seconds"),
    }
    if ATTR_NOTES in call.data:
        payload["notes"] = call.data[ATTR_NOTES]
    try:
        await client.async_log_action(payload)
    except ScaleVaultAuthError as err:
        if "events:write" in str(err):
            raise HomeAssistantError(
                "Quick-log actions aren't enabled yet — turn on \"Quick-log actions\" for "
                "this connection in ScaleVault under Settings → Home Assistant."
            ) from err
        raise HomeAssistantError(str(err) or "ScaleVault rejected the connection key") from err
    except ScaleVaultConnectionError as err:
        raise HomeAssistantError(str(err) or "Could not reach ScaleVault") from err


def async_register_services(hass: HomeAssistant) -> None:
    """Register the quick-log services (idempotent — safe to call per entry)."""
    if hass.services.has_service(DOMAIN, SERVICE_LOG_FEEDING):
        return

    for service, action in _ACTION_BY_SERVICE.items():

        async def _service_handler(call: ServiceCall, action: str = action) -> None:
            await _handle_action(hass, action, call)

        hass.services.async_register(DOMAIN, service, _service_handler, schema=_ACTION_SCHEMA)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove the quick-log services once the last config entry is unloaded."""
    for service in _ACTION_BY_SERVICE:
        hass.services.async_remove(DOMAIN, service)
