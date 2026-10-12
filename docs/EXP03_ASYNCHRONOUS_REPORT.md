# EXP-03 Asynchronous Telemetry Protocol

**Status:** PROTOCOL MATERIALIZED; COMPUTE EXECUTION PENDING

This document records the protocol closure before Metis execution. The current
outputs are a synthetic asynchronous envelope, not an estimate of industrial
arrival prevalence.

## Frozen protocol

- Time is an integer dispatch-step grid; one source step is 10 minutes.
- Each packet contains `event_time`, `arrival_time`, `channel_id`, and `sequence_id`.
- At dispatch step `t`, a model may read only packets with `arrival_time <= t`.
- Same-arrival packets are ordered by `(arrival_time, sequence_id, channel_id)`.
- Packets later than the finite `max_lateness` buffer deadline are dropped and
  represented by the shared missing mask; they are never backfilled into the past.
- All challengers and Site-Local Wspd-Bins receive the same realized packet
  trace and missingness mask.
- Primary estimand: paired PSREI-vs-delay curve and critical point `tau*`.
  `tau*` is not defined solely by a 10% violation crossing.
- The 10% value is a pre-registered operating target corresponding to `q*=0.90`.
  Sensitivity targets are 5%, 10%, and 15%.

## Local verification

- `tests/test_exp03_async_arrival.py`: 5 passed.
- Regression with existing arrival-feed tests: 10 passed.
- Materialized trace: 144 packets across 48 integer steps and 3 channels.
- Trace SHA256: `247bd671d86b62d7ca19633e11af5aa79253c38b56558033861b0af2884bf944`.
- Input hash file: `artifacts/exp03_async/input_trace_hash.txt`.

## Execution boundary

Metis execution must produce paired PSREI-vs-delay outputs before any scientific
interpretation. A null or unfavorable result remains valid evidence. Synthetic
arrival parameters must not be described as observed industrial rates.
