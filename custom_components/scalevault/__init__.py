"""The ScaleVault integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultClient
from .const import BASE_URL, CONF_BASE_URL, CONF_SENSORS, DOMAIN
from .services import async_register_services, async_unregister_services
from .telemetry import ScaleVaultTelemetryForwarder

# Platform.SELECT exposes the account's animals/enclosures as dropdown "target"
# helpers (see select.py) so quick-log services don't require a hand-typed
# A-/E- code. More platforms are added as further capabilities land.
PLATFORMS: list[Platform] = [Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ScaleVault from a config entry."""
    base_url = entry.data.get(CONF_BASE_URL, BASE_URL)
    client = ScaleVaultClient(
        async_get_clientsession(hass), base_url, entry.data[CONF_API_KEY]
    )
    # "client" is required; select.py adds "feeding_select"/"enclosure_select"
    # once its entities exist, so services.py can read the picked target.
    entry_data: dict = {"client": client}
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)

    forwarder = ScaleVaultTelemetryForwarder(hass, client, entry.options.get(CONF_SENSORS, []))
    forwarder.async_start()
    entry_data["telemetry"] = forwarder
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a ScaleVault config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        entry_data["telemetry"].async_stop()
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Options (e.g. the forwarded-sensors list) changed — reload to pick them up."""
    await hass.config_entries.async_reload(entry.entry_id)
