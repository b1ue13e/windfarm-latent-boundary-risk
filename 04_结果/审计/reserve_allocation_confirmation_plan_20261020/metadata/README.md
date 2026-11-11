# Hill of Towie open dataset

**Version 2.1.0** — see `CHANGELOG.md` for what changed between versions.

Wind turbine and LiDAR data from Hill of Towie, a 21-turbine Siemens
SWT-2.3-VS-82 wind farm in Scotland. Version 2 extends the v1 release (2016 →
2024-08) to 2026-04 and adds three new data tiers: high-resolution turbine data
(logged on change, roughly 1–25 Hz depending on the tag), 10-min and
high-resolution data from two LiDARs, and telemetry from the Dynamic Yaw wind
farm controller tested Jan–Apr 2026.

Field definitions are in `Hill_of_Towie_data_dictionary.md`. Read that before
using the data — it covers reference frames, the logging behaviour of the
fastlog tier, and known data quality issues.

## Contents

### Data

| File | Description | Coverage |
| --- | --- | --- |
| `2016.zip` … `2025.zip` | 10-minute SCADA archives, one zip per year | full years 2016 – 2025 |
| `2026.zip` | 10-minute SCADA, partial year | 2026-01 – 2026-04 |
| `turbine_fastlog.zip` | High-resolution turbine SCADA and Dynamic Yaw controller telemetry | 2026-01-01 – 2026-04-30 |
| `lidar_data.zip` | ZX300 ground LiDAR + ZXTM nacelle LiDAR on T07 | 2025-08-21 – 2026-04-30 |

### Supporting metadata

| File | Description |
| --- | --- |
| `Hill_of_Towie_data_dictionary.md` | Field definitions and conventions for all three data tiers |
| `Hill_of_Towie_turbine_metadata.csv` | Name, Station ID, lat/lon, model, hub height, rotor diameter, COD |
| `T21_weather_sensors.jpg` | Photo of the primary (ultrasonic) and secondary (mechanical) wind sensors on the nacelle mast, taken on T21 and representative of all 21 turbines |
| `ZXMS-RES029-REP01-01.pdf` | ZX300 deployment report, Aug 2025 |
| `ZXMS-RES035-REP01-01.pdf` | ZXTM deployment report, Dec 2025 |
| `CHANGELOG.md` | Version history, including corrections to previously published information |
| `README.md` | This file |

### Metadata carried over from version 1

These files are unchanged from the v1 release
([zenodo.org/records/14870023](https://zenodo.org/records/14870023)) and cover
the 10-minute SCADA only. They predate the fastlog and LiDAR tiers, and the
field lists in them are subsets rather than exhaustive; see
`Hill_of_Towie_data_dictionary.md` for wider coverage.

| File | Description |
| --- | --- |
| `Hill_of_Towie_tables_description.csv` | One row per SCADA table contained in the year zips |
| `Hill_of_Towie_turbine_fields_description.csv` | Definitions, source table, and units for selected `wtc_*` 10-minute fields |
| `Hill_of_Towie_grid_fields_description.csv` | Definitions, source table, and units for the 10-minute fields in the `tblGrid*` tables |
| `Hill_of_Towie_alarms_description.csv` | Lookup mapping selected `Alarmcode` values in `tblAlarmLog` to descriptions and a stopping/non-stopping flag |
| `Hill_of_Towie_AeroUp_install_dates.csv` | Per-turbine first and last AeroUp retrofit work dates |
| `Hill_of_Towie_ShutdownDuration.zip` | Computed shutdown durations covering the v1 data window based on SCADA data and RES operator logs |

## Turbines

Hill of Towie consists of 21 Siemens SWT-2.3-VS-82 turbines (2.3 MW, 59 m hub,
82 m rotor), named `T01` through `T21`. The SCADA join key is `StationId`
(a.k.a. `StationNr`), which equals `wtg_number + 2304509` at Hill of Towie (so
T01 = 2304510, T21 = 2304530). Coordinates are in
`Hill_of_Towie_turbine_metadata.csv`.

## Data tiers

**10-minute SCADA (`{YEAR}.zip`)** — each zip contains monthly CSV tables named
`{table}_{YYYY}_{MM}.csv`. The main table is `tblSCTurbine`; `tblAlarmLog`
holds alarm events. See `Hill_of_Towie_tables_description.csv` for the full
table list.

**Turbine fastlog (`turbine_fastlog.zip`)** — one Apache Parquet file per tag,
per turbine, per day, under `Filestore/FL/HOT/{station_nr}/{YYYY-MM-DD}/`.
Covers 2026-01-01 → 2026-04-30 for all 21 turbines. Five Dynamic Yaw controller
tags are present on every turbine; a further set of Siemens controller tags is
present on T01, T02, T03, T04, T05, T07, T11, T13 and T14. These files are
logged on change, not sampled at a fixed rate; see the data dictionary before
analysing them.

**LiDAR (`lidar_data.zip`)** — Apache Parquet under
`lidar_data/timeseries/{unit_id}/`, with `Wind10_*` files holding 10-minute
data and `Wind_*` files high-resolution data. Two instruments: the ZX300 (unit
2428), a ground-based profiling LiDAR sited about 280 m north of T11, and the
ZXTM (unit 5060), nacelle-mounted on T07. High-resolution files are provided
only for the Dynamic Yaw campaign window to keep the archive size manageable.

| Instrument | `Wind10_*` (10-min) | `Wind_*` (high-resolution) |
| --- | --- | --- |
| ZX300 (2428) | 2025-08-21 – 2026-04-30 | 2026-01-01 – 2026-04-30 |
| ZXTM (5060) | 2025-12-12 – 2026-04-30 | 2026-01-01 – 2026-04-30 |

Configuration and installation detail is in `ZXMS-RES029-REP01-01.pdf` (ZX300)
and `ZXMS-RES035-REP01-01.pdf` (ZXTM).

## Companion code

Open-source Python code for loading every data tier in this archive is
available at:

https://github.com/resgroup/hill-of-towie-open-source-analysis

## License and citation

This dataset is released by RES on behalf of TRIG under a Creative Commons
Attribution 4.0 (CC-BY-4.0) license and is provided as-is.

If you use it, please cite the dataset DOI
[10.5281/zenodo.14870021](https://doi.org/10.5281/zenodo.14870021), which
always resolves to the most recent version. To cite the exact version you
worked from, use that version's own DOI, listed on Zenodo and in
`CHANGELOG.md`.

Contact: Alex Clerc — `Alex.Clerc@res-group.com` For ZX Lidars enquires use
`support@zxlidars.com`

## Acknowledgement

- Thank you to TRIG for allowing us to make this dataset publicly available.
- Thank you to ZX LiDARs for assisting with LiDAR data and deployment reports.
