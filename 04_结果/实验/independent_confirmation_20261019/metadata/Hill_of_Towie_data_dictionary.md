# Hill of Towie data dictionary

Field definitions for the Hill of Towie open dataset
([10.5281/zenodo.14870021](https://doi.org/10.5281/zenodo.14870021)).

This file covers the fields used by the companion code at
[github.com/resgroup/hill-of-towie-open-source-analysis](https://github.com/resgroup/hill-of-towie-open-source-analysis),
plus the fields most often asked about. It is not an exhaustive list of every
column in the archive. Definitions for further 10-minute SCADA fields are in
`Hill_of_Towie_turbine_fields_description.csv` and
`Hill_of_Towie_grid_fields_description.csv`.

## Conventions

- All timestamps are UTC.
- 10-minute SCADA data is aggregated with `TimeStamp` giving the end of the
  period; subtract 10 minutes for the start of the period.
- Fastlog timestamps are instantaneous point samples.
- LiDAR values are aggregated over a period rather than instantaneous. The
  `Wind10_*` files hold 10-minute aggregates. The `Wind_*` files are higher
  rate but still aggregated, being derived from a batch of 50 Hz returns.
- Wind direction is in degrees increasing clockwise from north and follows the
  meteorological convention: the direction the wind blows from.
- Turbines are named `T01` to `T21`. The SCADA join key `StationId` (also
  `StationNr`) equals `wtg_number + 2304509` at Hill of Towie, so T01 = 2304510
  and T21 = 2304530.

### Reference frames

Direction and yaw signals are in one of two frames:

- **True north.**
- The turbine or LiDAR's calibrated north which may be incorrect. A northing
  correction is required to convert to true north, and that correction can
  change over time e.g. due to re-calibration. This frame is called **turbine
  north** for turbine signals and **instrument north** for the LiDARs.

Fastlog tag names ending in `_true_degrees` are in the true north frame.

Turbine north applies to `wtc_NacelPos`, `wtc_YawPos`, `wtc_ScYawPos`,
`wtc_ActualWindDirection`, `Wtc_TDI_YawPos_Value`, `Wtc_TDI_AcWindDr_Value` and
`computed_driver_post_processed_yaw_target_degrees`. Instrument north applies
to the LiDAR `Met Compass Bearing (deg)`.

The northing corrections used during the Dynamic Yaw campaign are published in
the companion code at
`scripts/wfc_analysis_2026/wind_up_config/northing_corrections/HOT_DY_Design_northing.yaml`
as `[turbine, valid_from, correction_degrees]` triples.

### Missing values

- LiDAR: values from `9987` to `9999` are sentinels indicating bad data.

## Wind sensing

Each turbine has a primary and a secondary wind sensing channel, each covering
both wind speed and wind direction. The controller selects a primary or
secondary source as active. The values below are read from the turbine
controller configuration of T01 and are understood to be the same on all 21
turbines.

| Controller config tag | Value on T01 |
| --- | --- |
| `Wtc_TDI_PriInTyp_PriInTyp` | `Ultrasonic FT anemometer` |
| `Wtc_TDI_SecInTyp_SecInTyp` | `Mechanical KK anemometer` |
| `Wtc_TDI_WsStatus_PriAnemo` | `Active` |
| `Wtc_TDI_WsStatus_SecAnemo` | `Inactive` |
| `Wtc_TDI_WsStatus_PriWVane` | `Active` |
| `Wtc_TDI_WsStatus_SecWVane` | `Inactive` |

The fastlog tag `Wtc_TDI_AcWindDr_Source` reports which wind direction sensor
is active. The active wind speed sensor can be inferred from whether
`wtc_AcWindSp` matches `wtc_PrWindSp` or `wtc_SeWindSp`.

`T21_weather_sensors.jpg` shows the mast carrying both sensors, viewed from
inside the open nacelle canopy on T21 (representative of all 21 turbines): the
mechanical wind vane and anemometer (secondary channel) and the ultrasonic
sensor (primary channel).

## 10-minute SCADA (`{YEAR}.zip`)

Each year zip contains monthly CSV tables named `{table}_{YYYY}_{MM}.csv`.
`Hill_of_Towie_tables_description.csv` lists the tables.

### Wind speed — `tblSCTurbine`

| Field | Description | Unit |
| --- | --- | --- |
| `wtc_AcWindSp` | Wind speed from the active wind sensor, i.e. whichever channel the controller has currently selected. | m/s |
| `wtc_PrWindSp` | Wind speed from the primary wind sensor. | m/s |
| `wtc_SeWindSp` | Wind speed from the secondary wind sensor. | m/s |
| `wtc_PriAnemo` | Primary anemometer raw signal. | m/s |
| `wtc_SecAnemo` | Secondary anemometer raw signal. | m/s |
| `wtc_TetAnFrq` | Tertiary anemometer frequency. The Hill of Towie turbines have no tertiary anemometer. | — |

The tables in this document give definitions. See [Known data quality
notes](#known-data-quality-notes) for fields that hold a constant value or need
a correction applied.

#### `wtc_SecAnemo` vs `wtc_SeWindSp`

`wtc_SeWindSp` is `wtc_SecAnemo` (the secondary anemometer's raw signal) after
a wind-speed-dependent correction. That correction was switched on partway
through the record: on 2017-08-01 for T14 and T17, and on 2018-04-10 for the
other 19 turbines (T01 and T06 one day later, on 2018-04-11). Before its
turbine's switch-on date, `wtc_SecAnemo` and `wtc_SeWindSp` are identical.

`wtc_SecAnemo` is discontinuous across a turbine's switch-on date. In
farm-average terms, `wtc_SecAnemo` / `wtc_PrWindSp` moves from about 1.02
before the switch to about 1.22 shortly after, while `wtc_SeWindSp` /
`wtc_PrWindSp` stays in the region of 1.02–1.05 throughout.

### Wind direction and yaw — `tblSCTurbine`

| Field | Description | Unit |
| --- | --- | --- |
| `wtc_NacelPos` | Nacelle yaw angle, wrapped to [0, 360). Turbine north frame. | deg |
| `wtc_YawPos` | Nacelle yaw angle, wrapped to [0, 360). Turbine north frame. | deg |
| `wtc_ScYawPos` | Yaw position, not wrapped to [0, 360). Equals `wtc_NacelPos` modulo 360. | deg |
| `wtc_ActualWindDirection` | Wind direction, being the nacelle position combined with the wind vane angle. Turbine north frame. First present in the archive from 2022-04. | deg |

Some 10-minute aggregates of circular signals may be incorrect because circular
math is not used in every case. This can be inspected further by comparing
fastlog data with the concurrent 10-minute aggregates.

### Other commonly used fields

| Field | Table | Description | Unit |
| --- | --- | --- | --- |
| `wtc_ActPower` | `tblSCTurGrid` | Active power. | kW |
| `wtc_ReactPwr` | `tblSCTurGrid` | Reactive power. | kVAr |
| `wtc_GenRpm` | `tblSCTurbine` | Generator speed. | rpm |
| `wtc_MainSRpm` | `tblSCTurbine` | Main shaft speed. | rpm |
| `wtc_PitcPosA`, `wtc_PitcPosB`, `wtc_PitcPosC` | `tblSCTurbine` | Blade pitch angle, per blade. | deg |
| `wtc_PowerRef_endvalue` | `tblSCTurbine` | Power reference (active power setpoint) at the end of the period. | kW |
| `wtc_WTOperSt` | `tblSCTurbine` | Turbine operating state code. First present from 2022-04. | — |
| `wtc_AmbieTmp` | `tblSCTurTemp` | Ambient temperature. | °C |
| `wtc_ScReToOp_timeon` | `tblSCTurFlag` | Time ready to operate within the period. | s |
| `wtc_ScInOper_timeon` | `tblSCTurFlag` | Time running within the period. | s |
| `wtc_ScTurSto_timeon` | `tblSCTurFlag` | Time turbine error active within the period. | s |
| `wtc_ScYawOpe_counts` | `tblSCTurFlag` | Count of yaw operations within the period. | — |

Fields are suffixed `_min`, `_max`, `_mean`, `_stddev`, `_endvalue`, `_timeon`
or `_counts` depending on how the turbine controller aggregates them over the
period.

### Schema changes

The set of columns in `tblSCTurbine` is not constant across the record. Changes
include:

| Month | Change |
| --- | --- |
| 2016-08 | `wtc_PwrRedLowSpeed_*` removed |
| 2017-07 | `wtc_BoostAva_*` added |
| 2022-04 | `wtc_ActualWindDirection_*`, `wtc_BoostAct_*` and `wtc_WTOperSt_*` added |

## Turbine fastlog (`turbine_fastlog.zip`)

Layout after extraction:

```
Filestore/FL/HOT/{station_nr}/{YYYY-MM-DD}/FL{station_nr}_{TAG}_{YYYY_MM_DD}.prq
```

One file per tag, per turbine, per day. `.prq` files are Apache Parquet; the
extension is a legacy naming convention only. Each file has a `TimeStamp` index
and one value column.

### Logging behaviour

Fastlog tags are **logged on change**, not sampled at a fixed rate. A row is
written when the value changes by more than a tolerance, so the number of rows
per day varies widely between tags.

A long interval between rows is therefore ambiguous: it means either that the
value held approximately constant, or that logging stopped and the data is
missing. A single tag does not distinguish the two.

`resample_fastlog_tags()` in `src/hot_open/fastlog_helpers.py` in the companion
code resolves this using an assumption, which users should judge for
themselves. It treats `Wtc_TDI_ActPower_Value` and `Wtc_TDI_AcWindSp_AcWindSp`
as busy tags, meaning tags assumed to change frequently while logging is
working, and takes an interval in which no busy tag has a value as an interval
in which logging stopped. Forward filling of the other tags is stopped
across such intervals rather than carried through them.

### Dynamic Yaw tags — all 21 turbines

| Tag | Description |
| --- | --- |
| `computed_core_post_processed_consensus_wind_direction_true_degrees` | The Dynamic Yaw controller's per-turbine wind direction estimate, informed by data from multiple turbines. True north frame. |
| `computed_core_post_processed_core_wake_steering_offset_degrees` | Commanded wake steering yaw offset, signed; positive is counter-clockwise viewed from above. |
| `computed_driver_pre_processed_yaw_direction_true_degrees` | Measured yaw direction with the Dynamic Yaw controller's northing correction applied. True north frame. |
| `computed_driver_post_processed_yaw_target_degrees` | Yaw direction target, including contributions from collective yaw control and wake steering. **Turbine north frame**, not true north. |
| `computed_driver_post_processed_toggle_state` | Dynamic Yaw validation toggle state: 0 = off, 1 = on. |

### Siemens tags — T01, T02, T03, T04, T05, T07, T11, T13, T14 only

| Tag | Description | Unit |
| --- | --- | --- |
| `Wtc_TDI_AcWindSp_AcWindSp` | Wind speed from the active wind sensor. Corresponds to `wtc_AcWindSp`. | m/s |
| `Wtc_TDI_AcWindDr_Value` | Wind direction from the active wind sensor. Corresponds to `wtc_ActualWindDirection`. Turbine north frame. | deg |
| `Wtc_TDI_AcWindDr_Source` | Identifies the active wind direction sensor. Values `1` and `2` occur. | — |
| `Wtc_TDI_YawPos_Value` | Yaw position. Corresponds to `wtc_NacelPos`. Turbine north frame. | deg |
| `Wtc_TDI_YawExec_YawExec` | Yaw drive command. String valued; typical values include `Stop`, `YawCW` and `YawCCW`. | — |
| `Wtc_TDI_ActPower_Value` | Active power. | kW |
| `Wtc_TDI_ReactPwr_Value` | Reactive power. | kVAr |
| `Wtc_TDI_PowerRef_PowerRef` | Power reference (active power setpoint). | kW |
| `Wtc_TDI_ActLimit_Power` | Active power limit. | kW |
| `Wtc_TDI_PowerRed_PowerRed` | Reduced power indication. Takes the values `0` and `1` in this archive. | — |
| `Wtc_TDI_GenState_GenState` | Generator state. String valued; typical values include `LargeOnGrd` and `GeneratOut`. | — |
| `Wtc_TDI_MainSRpm_Value` | Main shaft speed. | rpm |
| `Wtc_TDI_PitcPosA_Value`, `..._PitcPosB_Value`, `..._PitcPosC_Value` | Blade pitch angle, per blade. | deg |

## LiDAR (`lidar_data.zip`)

Layout after extraction:

```
lidar_data/timeseries/{unit_id}/Wind10_{prefix}@Y{YYYY}_M{MM}_D{DD}.parquet
lidar_data/timeseries/{unit_id}/Wind_{prefix}@Y{YYYY}_M{MM}_D{DD}.parquet
```

`Wind10_*` files hold 10-minute aggregates; `Wind_*` files hold the
instrument's higher-rate output, which is itself aggregated from approximately
50 Hz returns. Both are Apache Parquet. Every file carries a large
`Checksum:...` column which should be discarded on load.

### ZX300, unit 2428 — ground-based profiling LiDAR

Located approximately 280 m north of T11. Measurement heights are 17, 28, 38,
48, 58, 68, 78, 88, 99, 181 and 263 m. Heights are measured from the optical
head, roughly 1 m above ground level, so turbine hub height (59 m) corresponds
to the 58 m columns.

Per-height column families: `Wind Direction (deg) at {h}m`, `Horizontal Wind
Speed (m/s) at {h}m`, `Vertical Wind Speed (m/s) at {h}m`. The `Wind10_*` files
add `Horizontal Wind Speed {Min,Max,Std. Dev.} (m/s) at {h}m`, `TI at {h}m` and
`Packets in Average at {h}m`.

Instrument and met station columns: `Met Compass Bearing (deg)`, `Met Tilt
(deg)`, `Met Air Temp. (C)`, `Met Pressure (mbar)`, `Met Humidity (%)`, `Met
Wind Speed (m/s)`, `Met Wind Direction (deg)`, `Battery (V)`, `Generator (V)`,
`Upper Temp. (C)`, `Lower Temp. (C)`, `Pod Humidity (%)`, `GPS`, `Info. Flags`,
`Status Flags`, and rain and fog indicators.

### ZXTM, unit 5060 — nacelle-mounted LiDAR on T07

Each row carries a `Range (m)` value in {10, 48, 64, 85, 126, 208}, the
distance in front of T07 along the beam axis. Rotor segment heights are 26.2,
42.6, 59.0, 75.4 and 91.8 m above the turbine's ground level.

| Column family | Description |
| --- | --- |
| `{Left\|Right} LOS Speed (m/s) at Rotor Segment Height {h}m` | Line-of-sight wind speed for each beam. |
| `PD Wind Yaw Misalignment (deg) at Hub Height`, `PD Horizontal Wind Speed (m/s) at Hub Height` | Pair-derived: computed by resolving the left and right line-of-sight values at hub height assuming uniform flow. |
| `FD Horizontal Wind Speed (m/s) at Hub Height`, `FD Wind Yaw Misalignment (deg)`, `FD Vertical Wind Shear Exponent`, `FD Mean Fit Residual Normalised By Wind Speed`, `FD Fit Flags`, `FD Backscatter (/1.3e-6/m/sr)` | Fit-derived: produced by fitting a few seconds of line-of-sight data to a model assuming uniform flow with power-law shear and no veer. The fit residual quantifies inflow complexity and can be used to filter both the fit-derived and pair-derived outputs. |
| `Inclination Angle {Mean,Std. Dev.} (deg)`, `Roll Angle {Mean,Std. Dev.} (deg)` | Instrument attitude. |
| `Met *` columns | As for the ZX300. `Met Compass Bearing (deg)` is in the instrument north frame. |

Configuration and installation detail is in `ZXMS-RES029-REP01-01.pdf` (ZX300)
and `ZXMS-RES035-REP01-01.pdf` (ZXTM).

## Known data quality notes

- `wtc_PriAnemo` and `wtc_TetAnFrq` hold a constant value throughout the
  record.
- `0.01` appears as a lower limit in several `tblSCTurbine` wind speed fields.
- `wtc_SecAnemo` has a step change on each turbine's secondary-anemometer
  correction switch-on date (2017-08-01 for T14/T17; 2018-04-10/11 for the
  rest) — see [`wtc_SecAnemo` vs `wtc_SeWindSp`](#wtc_secanemo-vs-wtc_sewindsp).
  Use `wtc_SeWindSp` for analysis spanning these dates.
- Turbine north calibration errors can be large and can change in time. Apply
  northing corrections before any directional analysis.

## Contact

Alex Clerc — `Alex.Clerc@res-group.com`
