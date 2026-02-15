# MyBag Tracker (HACS Custom Integration)

Home Assistant custom integration to track delayed baggage status on `mybag.aero`.

Supported airlines:
- Austrian
- Lufthansa
- Swiss

Supported pages:
- `https://mybag.aero/baggage/#/pax/austrian/en-gb/delayed/manage-bag`
- `https://mybag.aero/baggage/#/pax/lufthansa/en-gb/delayed/manage-bag`
- `https://mybag.aero/baggage/#/pax/swiss/en-gb/delayed/manage-bag`

## What it exposes
For each configured bag (config entry), the integration creates:
- `sensor.<...>_status`
- `binary_sensor.<...>_found`

`sensor` state values:
- `searching`: still shows `SEARCHING FOR YOUR BAGGAGE`
- `updated`: status changed from `SEARCHING FOR YOUR BAGGAGE`
- `not_found`: reference number / family name combination not found
- `error`: check failed

Structured attributes on the status sensor include:
- `airline`
- `reference_number`
- `family_name`
- `bag_title`
- `headline`
- `details`
- `message`
- `is_searching`
- `checked_at`
- `source_url`
- `raw_excerpt`

## Install (HACS)
1. Push this repository to GitHub.
2. In Home Assistant: `HACS -> Integrations -> Custom repositories`.
3. Add your repo URL, category: `Integration`.
4. Install `MyBag Tracker`.
5. Restart Home Assistant.
6. Add integration: `Settings -> Devices & Services -> Add Integration -> MyBag Tracker`.
7. Enter:
   - Airline (`austrian`, `lufthansa`, `swiss`)
   - Reference number
   - Family name
   - Scan interval (minutes, default 60)

## Important runtime requirement
This integration uses Playwright. On Home Assistant OS/Container you may need browser binaries:

```bash
python -m playwright install chromium
```

If Chromium is missing, the entity state becomes `error` with details in `message`.

## Local development
Integration files are under:
- `custom_components/mybag_tracker`

HACS metadata:
- `hacs.json`
