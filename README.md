# Horoskop HR for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

`horoskop_hr` dohvaća horoskop sadržaj sa `ehoroskop.net` i izlaže ga kroz senzore u Home Assistantu.

## Što integracija radi
- Dohvaća horoskop za svih 12 znakova:
  - dnevni
  - tjedni
  - mjesečni
- Generira više tipova payload senzora (`raw`, `formatted`, `translated`)
- Ima ručne servise za refresh i prijevod
- Podržava automatski prijevod preko `ai_task` servisa

## Instalacija
### HACS (preporučeno)
1. Otvori HACS.
2. Idi na `Integrations`.
3. `Custom repositories` -> dodaj ovaj repo kao `Integration`.
4. Instaliraj `Horoskop HR`.
5. Restartaj Home Assistant.

### Manual
1. Kopiraj `custom_components/horoskop_hr` u HA `custom_components` direktorij.
2. Restartaj Home Assistant.

## Konfiguracija
1. `Settings` -> `Devices & Services` -> `Add Integration`.
2. Odaberi `Horoskop HR`.
3. Nakon inicijalnog setupa opcije se podešavaju kroz `Configure`:
   - `update_interval` (sekunde, 300-86400)
   - `use_scheduled_refresh` (true/false)
   - `scheduled_times` (npr. `00:00,08:00`)
   - `translation_enabled`
   - `translation_language`
   - `translation_ai_task_entity` (opcionalno)

Napomena:
- Integracija je `single instance` (jedna instanca po HA sustavu).

## Entiteti
Kreira sljedeće senzore:

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

## Struktura podataka
Svi payload senzori imaju:
- kratko stanje (`state`) kao timestamp generiranja
- puni sadržaj u atributu `data`
- izvore u atributu `source_urls`

To je namjerno zbog HA limita duljine `state` vrijednosti.

### `*_raw`
- `dnevni_raw`: `{ znak, url, datum, tekst }`
- `tjedni_raw`: `{ znak, url, datum_od_do, kategorija }`
  - `kategorija`: `ljubav|posao|zdravlje` -> `{ score, tekst }`
- `mjesecni_raw`: `{ znak, url, mjesec, tekst }`

### `*_formatted`
- isti ključevi znakova (`ovan`, `bik`, ...)
- vrijednost je čitljiv, formatiran tekst po znaku

### `*_translated`
- isti ključevi znakova
- preveden sadržaj formatiranog teksta
- puni se kad prijevod uspije

## Servisi
- `horoskop_hr.refresh`
  - odmah pokreće dohvat podataka
- `horoskop_hr.translate`
  - ručno pokreće prijevod trenutnih payloada

Opcionalno za oba servisa:
- `entry_id`

## Translation status
`sensor.horoskop_translation_status` prikazuje stanje prijevoda i atribute:
- `last_attempt`
- `last_success`
- `error_message`
- `language`

## Ograničenja
- Izvor je HTML scrape: ako se layout izvora značajno promijeni, parser treba prilagodbu.
- Sadržaj i dostupnost ovise o vanjskom izvoru (`ehoroskop.net`).

## HACS update flow
HACS prikazuje update kada postoji novi release/tag i veći `manifest.json` `version`.

Preporučeni flow:
1. Povećaj `custom_components/horoskop_hr/manifest.json` -> `version`.
2. Merge/push na `main`.
3. Objavi release/tag `vX.Y.Z`.

## Podrška
Bugove i feature requestove prijavi kroz GitHub Issues.

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
