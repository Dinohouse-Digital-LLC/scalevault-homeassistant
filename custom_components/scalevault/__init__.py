"""The ScaleVault integration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import (
    BASE_URL,
    CONF_BASE_URL,
    CONF_ENCLOSURE_CODE,
    CONF_SENSOR_ENCLOSURE_MAP,
    CONF_SENSOR_ENTITY_ID,
    CONF_SENSORS,
    DOMAIN,
    SUBENTRY_TYPE_SENSOR,
)
from .services import async_register_services, async_unregister_services
from .telemetry import ScaleVaultTelemetryForwarder

# Platform.SELECT exposes the account's animals/enclosures as dropdown "target"
# helpers (see select.py); Platform.BUTTON adds an on-demand "re-verify
# connection" action (see button.py). More platforms are added as further
# capabilities land.
PLATFORMS: list[Platform] = [Platform.SELECT, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ScaleVault from a config entry."""
    base_url = entry.data.get(CONF_BASE_URL, BASE_URL)
    client = ScaleVaultClient(
        async_get_clientsession(hass), base_url, entry.data[CONF_API_KEY]
    )

    # Validating here (rather than only at initial config-flow time) means
    # "Reload" doubles as a real connectivity re-check, and a revoked/expired
    # key surfaces as HA's standard reauth prompt instead of failing silently
    # on the next telemetry push or service call.
    try:
        await client.async_validate()
    except ScaleVaultAuthError as err:
        raise ConfigEntryAuthFailed(str(err) or "ScaleVault rejected the API key") from err
    except ScaleVaultConnectionError as err:
        raise ConfigEntryNotReady(str(err) or "Could not reach ScaleVault") from err

    # "client" is required; select.py adds "feeding_select"/"enclosure_select"
    # once its entities exist, so services.py can read the picked target.
    entry_data: dict = {"client": client}
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)

    sensor_entity_ids: list[str] = []
    sensor_enclosure_map: dict[str, str] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_SENSOR:
            continue
        sensor_entity_id = subentry.data[CONF_SENSOR_ENTITY_ID]
        sensor_entity_ids.append(sensor_entity_id)
        enclosure_code = subentry.data.get(CONF_ENCLOSURE_CODE)
        if enclosure_code:
            sensor_enclosure_map[sensor_entity_id] = enclosure_code

    forwarder = ScaleVaultTelemetryForwarder(hass, client, sensor_entity_ids, sensor_enclosure_map)
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
    """Sensor mappings (subentries) changed — reload to pick them up."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """One-time move from the old options-flow sensor list to one subentry per sensor.

    Pre-0.2.0 entries stored forwarded sensors as a multi-select plus an
    entity_id-keyed enclosure map in entry.options (see config_flow.py's
    former ScaleVaultOptionsFlow). ScaleVaultSensorMappingSubentryFlow
    replaces that with one subentry per sensor; this converts existing
    entries the first time they're loaded under the new minor version.
    """
    if entry.version > 1:
        return False

    if entry.minor_version < 2:
        sensors: list[str] = entry.options.get(CONF_SENSORS, [])
        enclosure_map: dict[str, str] = entry.options.get(CONF_SENSOR_ENCLOSURE_MAP, {})
        for sensor_entity_id in sensors:
            state = hass.states.get(sensor_entity_id)
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(
                        {
                            CONF_SENSOR_ENTITY_ID: sensor_entity_id,
                            CONF_ENCLOSURE_CODE: enclosure_map.get(sensor_entity_id),
                        }
                    ),
                    subentry_type=SUBENTRY_TYPE_SENSOR,
                    title=state.name if state else sensor_entity_id,
                    unique_id=sensor_entity_id,
                ),
            )
        hass.config_entries.async_update_entry(entry, options={}, minor_version=2)

    return True
