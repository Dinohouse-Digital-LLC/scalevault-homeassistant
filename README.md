# ScaleVault for Home Assistant

A [Home Assistant](https://www.home-assistant.io/) custom integration that connects your
[ScaleVault](https://scalevault.com) reptile-husbandry account to Home Assistant.

Bring temperature and humidity from **any** Home Assistant–supported sensor into ScaleVault —
Inkbird, Govee, SwitchBot, Zigbee/Z-Wave/BTHome, MQTT, and the rest — without ScaleVault having
to build a driver for each one. Home Assistant already speaks to the hardware; this integration
forwards the readings to ScaleVault, where they attach to your enclosures for history and
threshold alerts.

> **Status: early / scaffold.** The config flow and API client exist; telemetry forwarding,
> target mapping, and quick-log actions are being built out. See the [Roadmap](#roadmap).

## Why this exists

ScaleVault could integrate with each thermostat vendor's (often undocumented) cloud API directly,
but that means storing vendor passwords and maintaining a fragile adapter per brand. Home Assistant
already maintains all of those integrations. So ScaleVault integrates with Home Assistant **once**,
and every device Home Assistant supports comes along for free — no vendor passwords stored in
ScaleVault, nothing to reverse-engineer.

## Requirements

- Home Assistant 2024.12 or newer
- A ScaleVault account with an **API key** (generated under **Account Settings → Integrations**)

## Installation

### Via HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category: *Integration*):
   `https://github.com/Dinohouse-Digital-LLC/scalevault-homeassistant`
2. Install **ScaleVault** from HACS.
3. Restart Home Assistant.

_(Once accepted into the HACS default store, the custom-repository step won't be needed.)_

### Manual

Copy `custom_components/scalevault/` into your Home Assistant `config/custom_components/` directory
and restart.

## Configuration

1. In ScaleVault, go to **Account Settings → Integrations** and generate a Home Assistant API key.
   Copy it — it is shown only once.
2. In Home Assistant: **Settings → Devices & Services → Add Integration → ScaleVault**.
3. Paste the API key.

The key is account-scoped and carries only the permissions you grant (climate telemetry by
default; husbandry actions and read access are separate opt-ins). It is **not** a login and does
not consume a user seat.

## Roadmap

This integration is the Home Assistant half of ScaleVault's
[`home-assistant-integration` plan](https://github.com/Dinohouse-Digital-LLC). Planned capabilities,
roughly in build order:

- [ ] **Climate telemetry → ScaleVault** — forward selected sensor readings to your enclosures
- [ ] **Target mapping in the config flow** — pick which enclosure/animal each sensor maps to,
      from dropdowns populated by your ScaleVault account
- [x] **Quick-log actions** — `scalevault.log_feeding` / `log_watering` / `log_cleaning` services so a
      physical button, NFC tag, or voice command logs a husbandry event with one tap. Button entities
      bound to a specific animal/enclosure (rather than a free-text target field) are still open — that
      wants the Phase 1 target-mapping dropdowns below.
- [ ] **Reverse feed (stretch)** — expose ScaleVault husbandry state (e.g. "overdue for weighing")
      as Home Assistant sensors for dashboards and automations

## Development

The integration lives under `custom_components/scalevault/`:

| File | Purpose |
| --- | --- |
| `manifest.json` | Integration metadata (domain, version, requirements) |
| `const.py` | Domain + API path constants |
| `api.py` | Async HTTP client for the ScaleVault API |
| `config_flow.py` | UI setup flow (URL + API key, with validation) |
| `__init__.py` | Config-entry setup / teardown |
| `strings.json` / `translations/` | Config-flow UI text |

`push`, `pull_request`, and a nightly schedule run **hassfest** and **HACS** validation via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml).

## License

[Apache License 2.0](LICENSE) © Dinohouse Digital LLC
