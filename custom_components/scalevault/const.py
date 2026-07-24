"""Constants for the ScaleVault integration."""

DOMAIN = "scalevault"

# ScaleVault is a hosted service at a fixed URL, so the integration only asks the
# user for an API key — the base URL is not configurable.
BASE_URL = "https://scalevault.app"

# API paths (provisional — mirror the endpoints described in the ScaleVault
# "home-assistant-integration" plan; keep in sync as the server side lands).
API_VALIDATE = "/api/ha/validate"
API_TARGETS = "/api/ha/targets"
API_INGEST = "/api/thermostats/ingest"
API_ACTIONS = "/api/ha/actions"
