"""Constants for the ScaleVault integration."""

DOMAIN = "scalevault"

# ScaleVault is a hosted service at a fixed URL, so normal setup only asks the
# user for an API key. The base_url field, for developers pointing at a
# dev/staging server, lives in a collapsed config-flow section instead — see
# config_flow.py. (Used to be gated on the Advanced Mode profile toggle, but
# HA removed that in 2026.6.)
BASE_URL = "https://scalevault.app"
CONF_BASE_URL = "base_url"
SECTION_ADVANCED = "advanced_options"

# Sent as the X-ScaleVault-Client header on every request, so ScaleVault's
# Settings UI can tell a real custom-component connection apart from the
# manual rest_command/webhook recipe (which never sends this header).
CLIENT_IDENTIFIER = "home-assistant"

# API paths (provisional — mirror the endpoints described in the ScaleVault
# "home-assistant-integration" plan; keep in sync as the server side lands).
API_VALIDATE = "/api/ha/validate"
API_TARGETS = "/api/ha/targets"
API_INGEST = "/api/thermostats/ingest"
API_ACTIONS = "/api/ha/actions"

# Pre-0.2.0 options-flow keys (a sensor multi-select plus an entity_id-keyed
# map, both stored in entry.options). Superseded by one config subentry per
# sensor (see SUBENTRY_TYPE_SENSOR below) — kept only so async_migrate_entry
# in __init__.py can read old entries' options one last time and convert them.
CONF_SENSORS = "sensors"
CONF_SENSOR_ENCLOSURE_MAP = "sensor_enclosure_map"

# One config subentry per forwarded sensor (config_flow.py's
# ScaleVaultSensorMappingSubentryFlow), each storing CONF_SENSOR_ENTITY_ID and
# optionally CONF_ENCLOSURE_CODE in its data. Replaces the options flow above —
# subentries can be added/edited/removed individually instead of through one
# multi-select-then-map options screen.
SUBENTRY_TYPE_SENSOR = "sensor_mapping"
CONF_SENSOR_ENTITY_ID = "sensor_entity_id"
CONF_ENCLOSURE_CODE = "enclosure_code"

# How often buffered readings are pushed to ScaleVault, and the max readings
# held in memory while ScaleVault is unreachable (matches the server's
# per-batch cap in POST /api/thermostats/ingest).
TELEMETRY_FLUSH_INTERVAL_SECONDS = 60
TELEMETRY_MAX_BUFFERED_READINGS = 500
