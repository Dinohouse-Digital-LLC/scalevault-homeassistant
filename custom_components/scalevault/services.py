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

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import DOMAIN

SERVICE_LOG_FEEDING = "log_feeding"
SERVICE_LOG_WATERING = "log_watering"
SERVICE_LOG_CLEANING = "log_cleaning"

ATTR_TARGET = "target"
ATTR_NOTES = "notes"

_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TARGET): cv.string,
        vol.Optional(ATTR_NOTES): cv.string,
    }
)

_ACTION_BY_SERVICE = {
    SERVICE_LOG_FEEDING: "fed",
    SERVICE_LOG_WATERING: "watered",
    SERVICE_LOG_CLEANING: "cleaned",
}


def _get_client(hass: HomeAssistant) -> ScaleVaultClient:
    clients: dict[str, ScaleVaultClient] = hass.data.get(DOMAIN, {})
    if not clients:
        raise HomeAssistantError("No ScaleVault connection is configured")
    # Single-account scaffold: services aren't yet bound to a specific config
    # entry, so use whichever one is loaded.
    return next(iter(clients.values()))


async def _handle_action(hass: HomeAssistant, action: str, call: ServiceCall) -> None:
    client = _get_client(hass)
    payload: dict[str, Any] = {
        "action": action,
        "target": call.data[ATTR_TARGET],
        "idempotency_key": str(uuid.uuid4()),
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
