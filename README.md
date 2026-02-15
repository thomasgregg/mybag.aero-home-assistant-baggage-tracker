# Mybag.aero Baggage Tracker

Home Assistant custom integration for tracking delayed baggage status from mybag.aero.

Supported airlines:
- Austrian
- Lufthansa
- Swiss

## What you get
For each configured baggage file, the integration creates:
- `sensor.<name>_status`
- `binary_sensor.<name>_found`

`sensor` state values:
- `searching`
- `updated`
- `not_found`
- `error`

Useful sensor attributes:
- `airline`
- `reference_number`
- `family_name`
- `bag_title`
- `headline`
- `details`
- `tracing_statuses`
- `no_of_bags_updated`
- `record_status`
- `message`
- `is_searching`
- `checked_at`
- `source_url`

## Install (End User, via HACS)
1. Open Home Assistant.
2. Go to `HACS -> Integrations -> Custom repositories`.
3. Add this repository URL as type `Integration`:
   - `https://github.com/thomasgregg/mybag.aero-home-assistant-baggage-tracker`
4. Install `Mybag.aero Baggage Tracker` from HACS.
5. Restart Home Assistant.
6. Go to `Settings -> Devices & Services -> Add Integration`.
7. Search for `Mybag.aero Baggage Tracker`.
8. Enter:
   - Airline (`austrian`, `lufthansa`, `swiss`)
   - Reference number in file-reference format (for example `ABCOS12345`)
   - Family name
   - Scan interval in minutes

## Notes
- No Playwright or browser binaries are required.
- Data is fetched via direct HTTPS calls to `wtss-api.mybag.aero`.

## README sync
This repository intentionally uses this single root `README.md` for both GitHub and HACS (`hacs.json` has `render_readme: true`), so docs stay in sync.
