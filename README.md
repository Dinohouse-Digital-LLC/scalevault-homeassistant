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
4. To forward climate telemetry, open the ScaleVault integration's **Configure** and pick your
   temperature/humidity sensors. Their state changes are batched and pushed automatically —
   reload the integration (or revisit Configure) any time you add or remove sensors.

The key is account-scoped and carries only the permissions you grant (climate telemetry by
default; husbandry actions and read access are separate opt-ins). It is **not** a login and does
not consume a user seat.

## Roadmap

This integration is the Home Assistant half of ScaleVault's
[`home-assistant-integration` plan](https://github.com/Dinohouse-Digital-LLC). Planned capabilities,
roughly in build order:

- [x] **Climate telemetry → ScaleVault** — pick sensors in the integration's options (gear icon → Configure)
      and their state changes are batched and pushed automatically, no `rest_command` YAML required. Mapping
      each device to a specific enclosure still happens in ScaleVault's device mapper (Settings →
      Home Assistant) — config-flow sensor-to-enclosure dropdowns are still open.
- [x] **Target dropdowns** — `select.scalevault_feeding_target` / `select.scalevault_enclosure_target`
      list your account's animals/enclosures by name (`targets:list` scope), fetched at setup.
- [x] **Quick-log actions** — `scalevault.log_feeding` / `log_watering` / `log_cleaning` services so a
      physical button, NFC tag, or voice command logs a husbandry event with one tap. `target` is now
      optional — omit it to use the matching select entity's current pick instead of a hand-typed code.
- [ ] **Reverse feed (stretch)** — expose ScaleVault husbandry state (e.g. "overdue for weighing")
      as Home Assistant sensors for dashboards and automations

## Development

The integration lives under `custom_components/scalevault/`:

| File | Purpose |
| --- | --- |
| `manifest.json` | Integration metadata (domain, version, requirements) |
| `const.py` | Domain + API path constants |
| `api.py` | Async HTTP client for the ScaleVault API |
| `config_flow.py` | UI setup flow (URL + API key, with validation) and the options flow (sensor picker) |
| `telemetry.py` | State-change listener + batched/retried push of climate readings |
| `select.py` | Feeding/enclosure target dropdown entities |
| `services.py` | Quick-log services (`log_feeding`/`log_watering`/`log_cleaning`) |
| `__init__.py` | Config-entry setup / teardown |
| `strings.json` / `translations/` | Config-flow and services UI text |

`push`, `pull_request`, and a nightly schedule run **hassfest** and **HACS** validation via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml).

## License

[Apache License 2.0](LICENSE) © Dinohouse Digital LLC
