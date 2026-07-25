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
