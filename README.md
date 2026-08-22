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

- Home Assistant 2025.3 or newer (needs config subentry support, for per-sensor mapping)
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
4. To forward climate telemetry, open the ScaleVault integration card and choose **+ Add sensor
   mapping**: pick a temperature/humidity sensor and, optionally, which enclosure it belongs to.
   Repeat per sensor — each one is its own entry, editable or removable independently. State
   changes are batched and pushed automatically once a sensor is mapped.

The key is account-scoped and carries only the permissions you grant (climate telemetry by
default; husbandry actions and read access are separate opt-ins). It is **not** a login and does
not consume a user seat.

If ScaleVault ever rejects the stored key (e.g. it was revoked or rotated), Home Assistant shows a
**Reauthenticate** prompt on the integration — paste the new key there. To check sooner than that,
press the **Re-verify connection** button entity, which re-checks the key without reloading the
integration or interrupting telemetry buffering.

## Blueprints

Ready-made automations under [`blueprints/automation/scalevault/`](blueprints/automation/scalevault/) —
import one via **Settings → Automations & Scenes → Blueprints → Import Blueprint**, pasting its
raw GitHub URL, or copy the file into your `config/blueprints/automation/` directory manually.

| Blueprint | What it does |
| --- | --- |
| [`quick_log_action.yaml`](blueprints/automation/scalevault/quick_log_action.yaml) | Any trigger (button, NFC tag, script, ...) → `scalevault.log_action` with a key you configured in ScaleVault's Settings → Home Assistant. |
| [`quick_log_husbandry.yaml`](blueprints/automation/scalevault/quick_log_husbandry.yaml) | Any trigger → `log_feeding` / `log_watering` / `log_cleaning` directly, with an optional target, no action-key indirection. |
| [`sensor_out_of_range.yaml`](blueprints/automation/scalevault/sensor_out_of_range.yaml) | Watches a temperature/humidity sensor and runs a notify action of your choice when it drifts outside a range you set — fires locally in Home Assistant, independent of any ScaleVault-side alerting. |

None of these cover forwarding sensor readings to ScaleVault itself — that's the continuous
sensor → enclosure mapping already built into the integration (step 4 above, **+ Add sensor
mapping**), which batches and pushes automatically without any automation needed.

## Roadmap

This integration is the Home Assistant half of ScaleVault's
[`home-assistant-integration` plan](https://github.com/Dinohouse-Digital-LLC). Planned capabilities,
roughly in build order:

- [x] **Climate telemetry → ScaleVault** — add one subentry per sensor from the integration card,
      optionally mapping each to an enclosure right there, and their state changes are batched and pushed
      automatically — no `rest_command` YAML, no manual device mapping required.
- [x] **Target dropdowns** — `select.scalevault_feeding_target` / `select.scalevault_enclosure_target`
      list your account's animals/enclosures by name (`targets:list` scope), fetched at setup.
- [x] **Connection status in ScaleVault** — Settings → Home Assistant shows whether this component or the
      manual webhook recipe is actually talking to your account. On the Home Assistant side, setup/reload
      re-validates the key (triggering reauth if it's been revoked), and a **Re-verify connection** button
      checks on demand.
- [x] **Quick-log actions** — `scalevault.log_feeding` / `log_watering` / `log_cleaning` services so a
      physical button, NFC tag, or voice command logs a husbandry event with one tap. `target` is now
      optional — omit it to use the matching select entity's current pick instead of a hand-typed code.
- [x] **Action keys** — `scalevault.log_action` takes just a `key`, configured under ScaleVault's
      Settings → Home Assistant to mean whatever action(s)/target(s) you want. Reassigning what a
      button does becomes an edit in ScaleVault, not a change to this automation — and one key can
      fan out to more than one action and/or target.
- [ ] **Reverse feed (stretch)** — expose ScaleVault husbandry state (e.g. "overdue for weighing")
      as Home Assistant sensors for dashboards and automations

## Development

The integration lives under `custom_components/scalevault/`:

| File | Purpose |
| --- | --- |
| `manifest.json` | Integration metadata (domain, version, requirements) |
| `const.py` | Domain + API path constants |
| `api.py` | Async HTTP client for the ScaleVault API |
| `config_flow.py` | UI setup flow (URL + API key, with validation and reauth) and the sensor-mapping subentry flow |
| `telemetry.py` | State-change listener + batched/retried push of climate readings |
| `select.py` | Feeding/enclosure target dropdown entities |
| `button.py` | On-demand "Re-verify connection" button entity |
| `services.py` | Quick-log services (`log_feeding`/`log_watering`/`log_cleaning`/`log_action`) |
| `__init__.py` | Config-entry setup/teardown, API-key validation, and the one-time options→subentries migration |
| `strings.json` / `translations/` | Config-flow and services UI text |

`push`, `pull_request`, and a nightly schedule run **hassfest** and **HACS** validation via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml).

## License

[Apache License 2.0](LICENSE) © Dinohouse Digital LLC
