"""Constants for the ScaleVault integration."""

DOMAIN = "scalevault"

# ScaleVault is a hosted service at a fixed URL, so normal setup only asks the
# user for an API key. Advanced Mode users (HA profile toggle) additionally see
# a base_url field in the config flow, so developers can point at a dev/staging
# server — see config_flow.py.
BASE_URL = "https://scalevault.app"
CONF_BASE_URL = "base_url"

# API paths (provisional — mirror the endpoints described in the ScaleVault
# "home-assistant-integration" plan; keep in sync as the server side lands).
API_VALIDATE = "/api/ha/validate"
API_TARGETS = "/api/ha/targets"
API_INGEST = "/api/thermostats/ingest"
API_ACTIONS = "/api/ha/actions"

# Options-flow key: list of sensor entity_ids the user has chosen to forward
# as climate telemetry (see telemetry.py). Lives in entry.options, not
# entry.data, since it's changeable post-setup without re-entering the API key.
CONF_SENSORS = "sensors"

# How often buffered readings are pushed to ScaleVault, and the max readings
# held in memory while ScaleVault is unreachable (matches the server's
# per-batch cap in POST /api/thermostats/ingest).
TELEMETRY_FLUSH_INTERVAL_SECONDS = 60
TELEMETRY_MAX_BUFFERED_READINGS = 500
