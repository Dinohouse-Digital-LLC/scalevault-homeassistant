"""The ScaleVault integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultClient
from .const import BASE_URL, CONF_BASE_URL, DOMAIN
from .services import async_register_services, async_unregister_services

# Platforms are added as capabilities land (e.g. Platform.BUTTON for quick-log
# actions). Empty for the initial scaffold.
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ScaleVault from a config entry."""
    base_url = entry.data.get(CONF_BASE_URL, BASE_URL)
    client = ScaleVaultClient(
        async_get_clientsession(hass), base_url, entry.data[CONF_API_KEY]
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a ScaleVault config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            async_unregister_services(hass)
    return unload_ok
