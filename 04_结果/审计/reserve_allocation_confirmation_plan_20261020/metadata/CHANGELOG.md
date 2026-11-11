# Changelog

Version history of the Hill of Towie open dataset.

Each Zenodo version has its own DOI. The concept DOI
[10.5281/zenodo.14870021](https://doi.org/10.5281/zenodo.14870021) always
resolves to the latest version.

Versions follow `MAJOR.MINOR.PATCH`:

- **MAJOR** — data removed, renamed, or restructured in a way that breaks
  existing code.
- **MINOR** — data or files added, backwards compatible.
- **PATCH** — corrections that add no new data.

## 2.1.0 — 2026-09-08

`10.5281/zenodo.22662930`

Documentation only. No measurement data changed; every data file is identical
to 2.0.0.

### Corrected

- `computed_driver_post_processed_yaw_target_degrees` reference frame. This
  fastlog tag was documented in 2.0.0 as being "in true-north reference". That
  was wrong: it is in the turbine north frame.
- First appearance of `wtc_ActualWindDirection`. This field is present in the
  10-minute SCADA from 2022-04. Earlier statements of it beginning in 2023 were
  incorrect.
- Fastlog sampling description. 2.0.0 described native sampling as
  "approximately 1-25 Hz (signal dependent), log on change". The log-on-change
  behaviour is the operative part and the rate figure was easily misread as a
  guarantee. A day-tag file with a single row means the value held constant all
  day or was not logged at some point; the two cases can be distinguished using
  a busy tag, as now described in the data dictionary.

### Added

- `Hill_of_Towie_data_dictionary.md` — field definitions, units, reference
  frame conventions and known data quality notes.
- `CHANGELOG.md` — this file.
- A version number in `README.md`.
- `T21_weather_sensors.jpg` — photo of the primary and secondary wind sensors
  on the nacelle mast.

### Changed

- `README.md` reduced to an overview of the archive contents. Field-level
  description moved to the data dictionary.

## 2.0.0 — 2026-05-18

[10.5281/zenodo.20204946](https://doi.org/10.5281/zenodo.20204946)

### Added

- 10-minute SCADA extended from 2024-08 to 2026-04 (`2024.zip` completed,
  `2025.zip` and `2026.zip` added).
- `turbine_fastlog.zip` — high-resolution (~1 Hz) turbine controller data and
  Dynamic Yaw controller telemetry for all 21 turbines, 2026-01-01 to
  2026-04-30.
- `lidar_data.zip` — 10-minute and high-resolution data from two LiDARs: the
  ZX300 ground-based profiling unit sited north of T11, and the ZXTM
  nacelle-mounted unit on T07.
- `ZXMS-RES029-REP01-01.pdf` and `ZXMS-RES035-REP01-01.pdf` — LiDAR deployment
  reports.

Supporting metadata files were carried over unchanged from 1.0.0.

## 1.0.0 — 2025-03-28

[10.5281/zenodo.14870023](https://doi.org/10.5281/zenodo.14870023)

Initial release. 10-minute SCADA and alarm log data for the 21 turbines from
2016-01 to 2024-08, with turbine metadata, table and field description files,
an alarm code lookup, AeroUp retrofit dates, and computed shutdown durations.
