# Horoskop HR

Home Assistant custom integration that scrapes `https://ehoroskop.net/<znak>/` and exposes:

- daily horoscope (`dnevni`)
- weekly horoscope (`tjedni`)
- monthly horoscope (`mjesecni`)

for all 12 zodiac signs.

## Entities

Integration creates these sensors:

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

Each payload sensor has:

- short state: `generated_at` timestamp
- full payload in attributes under `data`
- source URLs under `source_urls`

This prevents the 255-char state limit issue.

## Output Shape

### `*_raw`

- `dnevni_raw`:
  - `slug` -> `{ znak, url, datum, tekst }`
- `tjedni_raw`:
  - `slug` -> `{ znak, url, datum_od_do, kategorija }`
  - `kategorija` -> `ljubav|posao|zdravlje` -> `{ score, tekst }`
- `mjesecni_raw`:
  - `slug` -> `{ znak, url, mjesec, tekst }`

### `*_formatted`

- same sign keys (`ovan`, `bik`, ...)
- value is a single readable text block per sign

### `*_translated`

- same sign keys
- translated formatted text
- filled only when translation succeeds

## Weekly Score Parsing

Weekly score is extracted from image URL format:

- `zvijezde-4-5.png` -> `score: 4`

## Services

- `horoskop_hr.refresh`
  - Force immediate scrape
- `horoskop_hr.translate`
  - Force translation run

Optional field for both:

- `entry_id`

## Translation

Translation uses `ai_task` service (`generate_data` preferred, `generate_text` fallback).

Options:

- `translation_enabled`
- `translation_language`
- `translation_ai_task_entity` (optional)
- `use_scheduled_refresh` (default: `true`)
- `scheduled_times` (default: `00:30,08:00`)
- `update_interval` is used when scheduled refresh is disabled

## Helper Examples

Add helpers in `input_select`:

```yaml
horoskop_znak_bruno:
  name: Horoskop znak Bruno
  options: [ovan, bik, blizanci, rak, lav, djevica, vaga, skorpion, strijelac, jarac, vodenjak, ribe]

horoskop_znak_barbara:
  name: Horoskop znak Barbara
  options: [ovan, bik, blizanci, rak, lav, djevica, vaga, skorpion, strijelac, jarac, vodenjak, ribe]
```

Template sensor example for Bruno daily text:

```yaml
template:
  - sensor:
      - name: "Horoskop Bruno Dnevni"
        state: >
          {{ now().isoformat() }}
        attributes:
          znak: "{{ states('input_select.horoskop_znak_bruno') }}"
          dnevni: >
            {% set z = states('input_select.horoskop_znak_bruno') %}
            {{ state_attr('sensor.horoskop_dnevni_formatted', 'data').get(z, '') }}
```

## Notes

- Source HTML can change; parser is resilient to small layout shifts, but large site redesign may require parser update.
- Annual/love-only horoscope blocks are intentionally ignored.

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
