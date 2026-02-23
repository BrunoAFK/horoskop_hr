# Horoskop HR for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

`horoskop_hr` fetches horoscope content from `ehoroskop.net` and exposes it as Home Assistant sensors.

## What this integration does
- Fetches horoscope content for all 12 zodiac signs:
  - daily
  - weekly
  - monthly
- Provides structured payload sensors (`raw`, `formatted`, `translated`)
- Supports manual refresh and manual translation services
- Supports optional AI translation via `ai_task`

## Quick start
1. Install via HACS (Custom Repository) or copy manually to `custom_components/horoskop_hr`.
2. Restart Home Assistant.
3. Add integration: `Settings -> Devices & Services -> Add Integration -> Horoskop HR`.
4. Open `Configure` and set options.

## Installation
### HACS (recommended)
1. Open HACS.
2. Go to `Integrations`.
3. Open `Custom repositories`.
4. Add this repository as category `Integration`.
5. Install `Horoskop HR`.
6. Restart Home Assistant.

### Manual
1. Copy `custom_components/horoskop_hr` into your HA `custom_components` directory.
2. Restart Home Assistant.

## Configuration
After adding the integration, use `Configure` to set:
- `update_interval` (seconds, 300-86400)
- `use_scheduled_refresh` (true/false)
- `scheduled_times` (for example: `00:00,08:00`)
- `translation_enabled`
- `translation_language`
- `translation_ai_task_entity` (optional)

Note:
- The integration is single-instance.

## Entities
Created sensors:
- `sensor.horoskop_dnevni_raw`
- `sensor.horoskop_tjedni_raw`
- `sensor.horoskop_mjesecni_raw`
- `sensor.horoskop_dnevni_formatted`
- `sensor.horoskop_tjedni_formatted`
- `sensor.horoskop_mjesecni_formatted`
- `sensor.horoskop_dnevni_translated`
- `sensor.horoskop_tjedni_translated`
- `sensor.horoskop_mjesecni_translated`
- `sensor.horoskop_translation_status`

## Data model
Payload sensors use:
- `state`: short generated timestamp
- `attributes.data`: full payload
- `attributes.source_urls`: source links

This avoids Home Assistant state length limits.

## Services
- `horoskop_hr.refresh`
  - trigger immediate fetch
- `horoskop_hr.translate`
  - trigger translation for current payloads

Optional field:
- `entry_id`

## Translation status sensor
`sensor.horoskop_translation_status` includes:
- `last_attempt`
- `last_success`
- `error_message`
- `language`

## Troubleshooting
- If sensors are empty, run `horoskop_hr.refresh` once manually.
- If translation fails, verify `ai_task` service availability.
- If source layout changes significantly, parser updates may be required.

## HACS updates
HACS shows updates when a newer release/tag is published and `manifest.json` version is higher.

Recommended release flow:
1. Bump `custom_components/horoskop_hr/manifest.json` version.
2. Push to `main`.
3. Publish release/tag `vX.Y.Z`.

## Support
Please use GitHub Issues for bugs and feature requests.

## Disclaimer

This integration retrieves publicly available horoscope data from `https://ehoroskop.net` directly from the user's local Home Assistant instance.

This project:

- Is not affiliated with, endorsed by, or connected to `ehoroskop.net`
- Does not host, store, cache, or redistribute horoscope content
- Does not operate any proxy, API, or intermediate server
- Only provides a tool that allows end users to fetch data directly from the original website

All content remains the property of its respective copyright holder.

Users are responsible for ensuring that their use of this integration complies with the terms of use of `ehoroskop.net` and applicable copyright laws in their jurisdiction.

This integration is intended for personal, non-commercial use only.

If you are the owner of the referenced website and have concerns about this project, please open an issue or contact the maintainer.
