"""Forward selected sensor state changes to ScaleVault as climate telemetry.

Replaces the manual rest_command/automation YAML recipe: the user picks
sensors in the options flow (see config_flow.py), and this module listens for
state changes on them, converts to the units ScaleVault expects, and batches
readings to POST /api/thermostats/ingest on a timer — buffering in memory
(bounded) and retrying on the next tick if ScaleVault is unreachable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util.unit_conversion import TemperatureConverter

from .api import ScaleVaultAuthError, ScaleVaultClient, ScaleVaultConnectionError
from .const import TELEMETRY_FLUSH_INTERVAL_SECONDS, TELEMETRY_MAX_BUFFERED_READINGS

_LOGGER = logging.getLogger(__name__)

_HUMIDITY_DEVICE_CLASS = "humidity"


def _reading_from_state(state: State, enclosure_code: str | None) -> dict[str, Any] | None:
    """Build an ingest reading dict from a sensor's state, or None if the
    state isn't a usable numeric temperature/humidity value right now."""
    if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, None, ""):
        return None
    try:
        value = float(state.state)
    except (TypeError, ValueError):
        return None

    device_class = state.attributes.get("device_class")
    unit = state.attributes.get("unit_of_measurement")
    friendly_name = state.attributes.get("friendly_name")

    reading: dict[str, Any] = {
        "external_device_id": state.entity_id,
        "recorded_at": (state.last_changed or state.last_updated).isoformat(),
    }
    if friendly_name:
        reading["friendly_name"] = friendly_name
    if enclosure_code:
        # Options-flow mapping (config_flow.py's "map" step) — skips
        # ScaleVault's manual/fuzzy device mapper entirely for this sensor.
        reading["enclosure_code"] = enclosure_code

    if device_class == _HUMIDITY_DEVICE_CLASS:
        reading["humidity_pct"] = value
    else:
        # Default to treating it as temperature — matches the options flow's
        # entity selector, which only offers temperature/humidity sensors.
        if unit == UnitOfTemperature.FAHRENHEIT:
            value = TemperatureConverter.convert(value, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)
        reading["temperature_c"] = round(value, 2)

    return reading


class ScaleVaultTelemetryForwarder:
    """Owns the state-change listener and the batched push to ScaleVault."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ScaleVaultClient,
        sensor_entity_ids: list[str],
        sensor_enclosure_map: dict[str, str] | None = None,
    ) -> None:
        self._hass = hass
        self._client = client
        self._sensor_entity_ids = sensor_entity_ids
        self._sensor_enclosure_map = sensor_enclosure_map or {}
        self._buffer: list[dict[str, Any]] = []
        self._unsub_state: Any = None
        self._unsub_timer: Any = None

    def async_start(self) -> None:
        if not self._sensor_entity_ids:
            return
        self._unsub_state = async_track_state_change_event(
            self._hass, self._sensor_entity_ids, self._handle_state_change
        )
        self._unsub_timer = async_track_time_interval(
            self._hass, self._async_flush, timedelta(seconds=TELEMETRY_FLUSH_INTERVAL_SECONDS)
        )

    def async_stop(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        reading = _reading_from_state(new_state, self._sensor_enclosure_map.get(new_state.entity_id))
        if reading is None:
            return
        self._buffer.append(reading)
        if len(self._buffer) > TELEMETRY_MAX_BUFFERED_READINGS:
            # ScaleVault unreachable for a while — drop the oldest readings
            # rather than grow unbounded; a gap beats an OOM.
            overflow = len(self._buffer) - TELEMETRY_MAX_BUFFERED_READINGS
            _LOGGER.warning("ScaleVault telemetry buffer full, dropping %d oldest reading(s)", overflow)
            del self._buffer[:overflow]

    async def _async_flush(self, _now: datetime | None = None) -> None:
        if not self._buffer:
            return
        batch = self._buffer
        self._buffer = []
        try:
            await self._client.async_push_readings(batch)
        except (ScaleVaultAuthError, ScaleVaultConnectionError) as err:
            _LOGGER.warning("Could not push ScaleVault telemetry, will retry next interval: %s", err)
            # Put the batch back (ahead of anything buffered meanwhile) rather
            # than lose it — bounded by the same overflow check as above.
            self._buffer = (batch + self._buffer)[-TELEMETRY_MAX_BUFFERED_READINGS:]
