# Landtagswahl Baden-Wuerttemberg 2026 - Tracking Template

## Tracking Window

Automated tracking is scheduled to commence at **2026-03-08 18:00 CET**.
No official results are expected before **2026-03-08 18:00 CET**, so polling is intentionally disabled until then.

## Data Sources (Planned)

- `komm.one` municipality APIs (template: `https://wahlergebnisse.komm.one/lb/produktion/wahltermin-{wahltermin}/{ags}` + `/daten/api/...`)
- Statistik BW single CSV: `https://www.statistik-bw.de/fileadmin/user_upload/Wahlen/Landesdaten/ltw26_daten.csv` (fallback: `https://www.statistik-bw.de/fileadmin/user_upload/Presse/Pressemitteilungen/2026021_LTW26-Dummy-Datei.csv`)
- Wahlkreis geometry (GeoJSON ZIP): `https://www.statistik-bw.de/fileadmin/user_upload/medien/bilder/Karten_und_Geometrien_der_Wahlkreise/LTWahlkreise2026-BW_GEOJSON.zip`
- Wahlkreis geometry (SHP ZIP): `https://www.statistik-bw.de/fileadmin/user_upload/medien/bilder/Karten_und_Geometrien_der_Wahlkreise/LTWahlkreise2026-BW_SHP.zip`

## Wahlkreis Map

![Wahlkreis status map](data/ltw26/metadata/wahlkreis-status.svg)

Map file and status table are prepared from official published geometry in `data/ltw26/metadata/`.

## Party Totals (First and Second Votes)

### Erststimmen

| Party | `komm.one` Count | `komm.one` Share | `statla` Count | `statla` Share | Delta Count (`komm.one`-`statla`) | Delta Share (`komm.one`-`statla`) |
|---|---:|---:|---:|---:|---:|---:|
| GRÜNE | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| CDU | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| SPD | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| FDP | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| AfD | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die Linke | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| FREIE WÄHLER | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die PARTEI | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| dieBasis | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| ÖDP | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Volt | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Bündnis C | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| BSW | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die Gerechtigkeitspartei | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Tierschutzpartei | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Werteunion | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Anderer Kreiswahlvorschlag | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| **TOTAL** | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |

### Zweitstimmen

| Party | `komm.one` Count | `komm.one` Share | `statla` Count | `statla` Share | Delta Count (`komm.one`-`statla`) | Delta Share (`komm.one`-`statla`) |
|---|---:|---:|---:|---:|---:|---:|
| GRÜNE | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| CDU | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| SPD | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| FDP | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| AfD | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die Linke | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| FREIE WÄHLER | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die PARTEI | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| dieBasis | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| KlimalisteBW | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| ÖDP | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Volt | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Bündnis C | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| PDH | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Verjüngungsforschung | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| BSW | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Die Gerechtigkeitspartei | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| PDR | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| PdF | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Tierschutzpartei | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| Werteunion | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |
| **TOTAL** | 0 | 0.00% | 0 | 0.00% | +0 | +0.00% |

## Operations

- Local run after start: `python scripts/poll_ltw26.py`
- SQLite history DB (local cache, not committed): `data/ltw26/history.sqlite`
- Rebuild SQLite from git deltas: `python scripts/rebuild_history_sqlite_from_git_deltas.py`
- Minute automation: `.github/workflows/poll.yml`
