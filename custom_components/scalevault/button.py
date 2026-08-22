"""On-demand ScaleVault connection re-check, without reloading the integration.

async_setup_entry (see __init__.py) already validates the API key on every
setup/reload, so this button is for checking sooner than that — e.g. right
after rotating a key in ScaleVault — without restarting telemetry buffering.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import DOMAIN


class ScaleVaultReverifyButton(ButtonEntity):
    """Re-runs the API key validation ScaleVaultClient does at setup time."""

    _attr_should_poll = False
    _attr_name = "ScaleVault Re-verify connection"

    def __init__(self, entry: ConfigEntry, client: ScaleVaultClient) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_reverify_connection"

    async def async_press(self) -> None:
        try:
            info = await self._client.async_validate()
        except ScaleVaultAuthError as err:
            raise HomeAssistantError(str(err) or "ScaleVault rejected the API key") from err
        except ScaleVaultConnectionError as err:
            raise HomeAssistantError(str(err) or "Could not reach ScaleVault") from err

        account_name = info.get("account_name") or "your ScaleVault account"
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "ScaleVault",
                "message": f"Connection to {account_name} verified.",
                "notification_id": f"{DOMAIN}_reverify",
            },
            blocking=False,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScaleVaultReverifyButton(entry, entry_data["client"])])
