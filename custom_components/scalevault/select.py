"""Dropdown select entities exposing ScaleVault animals/enclosures.

Fetched once at setup (`targets:list` scope) so quick-log services can accept
a picked target from a native HA dropdown instead of requiring a hand-typed
A-/E- code. Reload the integration to pick up newly added animals/enclosures.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ScaleVaultClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_NO_TARGETS_OPTION = "No targets available — reload the integration"


class ScaleVaultTargetSelect(SelectEntity):
    """A dropdown of ScaleVault target codes, labeled by name."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, unique_suffix: str, name: str, targets: list[dict[str, Any]]) -> None:
        self._targets_by_label = {f"{t['name']} ({t['code']})": t["code"] for t in targets}
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = name
        self._attr_options = list(self._targets_by_label) or [_NO_TARGETS_OPTION]
        self._attr_current_option = self._attr_options[0]

    @property
    def current_code(self) -> str | None:
        """The ScaleVault code (e.g. A-0042) behind the currently selected label."""
        return self._targets_by_label.get(self._attr_current_option)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Fetch the account's targets and expose animal/enclosure select entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client: ScaleVaultClient = entry_data["client"]
    try:
        targets = await client.async_list_targets()
    except Exception:  # noqa: BLE001 - a failed fetch shouldn't block setup
        _LOGGER.warning("Could not fetch ScaleVault targets; select entities will be empty", exc_info=True)
        targets = []

    animals = [t for t in targets if t.get("type") == "animal"]
    enclosures = [t for t in targets if t.get("type") == "enclosure"]

    feeding_select = ScaleVaultTargetSelect(entry, "feeding_target", "ScaleVault Feeding target", animals)
    enclosure_select = ScaleVaultTargetSelect(entry, "enclosure_target", "ScaleVault Enclosure target", enclosures)
    entry_data["feeding_select"] = feeding_select
    entry_data["enclosure_select"] = enclosure_select

    async_add_entities([feeding_select, enclosure_select])
