"""Constants for the ScaleVault integration."""

DOMAIN = "scalevault"

# ScaleVault is a hosted service at a fixed URL, so normal setup only asks the
# user for an API key. Advanced Mode users (HA profile toggle) additionally see
# a base_url field in the config flow, so developers can point at a dev/staging
# server — see config_flow.py.
BASE_URL = "https://scalevault.app"
CONF_BASE_URL = "base_url"

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

# Options-flow keys: which sensor entity_ids the user has chosen to forward
# as climate telemetry, and which ScaleVault enclosure code each maps to (see
# telemetry.py). Live in entry.options, not entry.data, since they're
# changeable post-setup without re-entering the API key.
CONF_SENSORS = "sensors"
CONF_SENSOR_ENCLOSURE_MAP = "sensor_enclosure_map"

# How often buffered readings are pushed to ScaleVault, and the max readings
# held in memory while ScaleVault is unreachable (matches the server's
# per-batch cap in POST /api/thermostats/ingest).
TELEMETRY_FLUSH_INTERVAL_SECONDS = 60
TELEMETRY_MAX_BUFFERED_READINGS = 500
