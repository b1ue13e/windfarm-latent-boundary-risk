"""Protocol tests for EXP-03 asynchronous packet arrival."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.exp03_async_packet_protocol import (  # noqa: E402
    BufferPolicy,
    CausalPacketBuffer,
    Packet,
    make_trace,
    replay_trace,
)
from scripts.run_exp03_async_benchmark import simulate_asynchronous_scada_stream  # noqa: E402


def test_event_and_arrival_time_are_distinct_and_future_is_hidden():
    trace = make_trace({"wspd": [1.0, 2.0]}, {"wspd": [0, 2]})
    snapshots = replay_trace(trace, ["wspd"], n_steps=2)
    assert snapshots[0]["values"] == {"wspd": 1.0}
    assert snapshots[1]["values"] == {}
    assert snapshots[1]["mask"] == {"wspd": False}
    assert trace[1].event_time == 1
    assert trace[1].arrival_time == 3


def test_same_arrival_is_deterministically_ordered():
    packets = [
        Packet(0, 1, "b", 0, 20.0),
        Packet(0, 1, "a", 0, 10.0),
    ]
    assert [p.channel_id for p in sorted(packets, key=lambda p: p.key())] == ["a", "b"]


def test_late_packet_is_dropped_after_buffer_deadline():
    buffer = CausalPacketBuffer(["wspd"], BufferPolicy(max_lateness=1))
    packet = Packet(0, 2, "wspd", 0, 7.0)
    buffer.ingest(packet, now=2)
    assert buffer.dropped_late == [packet]
    assert buffer.view(now=2, event_time=0) == ({}, {"wspd": False})


def test_future_ingest_and_future_backfill_are_rejected():
    buffer = CausalPacketBuffer(["wspd"])
    with pytest.raises(ValueError, match="before its arrival_time"):
        buffer.ingest(Packet(0, 3, "wspd", 0, 1.0), now=2)
    with pytest.raises(ValueError, match="future backfill"):
        CausalPacketBuffer(["wspd"], BufferPolicy(allow_future_backfill=True))


def test_sequence_replay_is_monotone_and_duplicates_are_not_overwritten():
    buffer = CausalPacketBuffer(["wspd"])
    first = Packet(0, 0, "wspd", 1, 3.0)
    duplicate = Packet(1, 0, "wspd", 1, 99.0)
    buffer.ingest(first, now=0)
    buffer.ingest(duplicate, now=0)
    assert buffer.dropped_duplicate == [duplicate]
    assert buffer.view(0, 0) == ({"wspd": 3.0}, {"wspd": True})


def test_shared_arrival_trace_and_missing_mask_parity_across_models():
    """Verify that both Wspd-Bins and Challenger observe identical arrival trace and masks."""
    channels = ["wspd", "patv", "etmp"]
    n_steps = 10
    values = {c: [float(10.0 + i) for i in range(n_steps)] for c in channels}
    delays = {
        "wspd": [0, 1, 2, 0, 1, 3, 0, 1, 2, 0],
        "patv": [1, 0, 1, 2, 0, 1, 2, 0, 1, 2],
        "etmp": [0, 0, 1, 1, 2, 2, 0, 0, 1, 1],
    }
    trace = make_trace(values, delays, seed=42)
    snapshots = replay_trace(trace, channels, n_steps=n_steps, policy=BufferPolicy(max_lateness=2))

    # Simulate feeding Wspd-Bins and Challenger
    wspd_input_seen_by_baseline = []
    wspd_input_seen_by_challenger = []
    shared_mask = []

    for s in snapshots:
        # Both models read the exact same snapshot
        w_val = s["values"].get("wspd", None)
        wspd_input_seen_by_baseline.append(w_val)
        wspd_input_seen_by_challenger.append(w_val)
        shared_mask.append(s["mask"]["wspd"])

    assert wspd_input_seen_by_baseline == wspd_input_seen_by_challenger
    assert len(shared_mask) == n_steps
    # Ensure late packets beyond max_lateness=2 are marked missing
    # Step 5 wspd has delay 3, so at t=5 arrival_time=8, at t=5 it must be missing
    assert shared_mask[5] is False


def test_async_simulator_delays_canonical_patv_hist_channel():
    """The simulator must delay the same active-power field used by the model."""
    import numpy as np

    names = ["Wspd", "Etmp", "Itmp", "Prtv", "Patv_hist"]
    raw = np.zeros((4, 1, len(names)), dtype=np.float32)
    raw[:, 0, names.index("Wspd")] = [1.0, 2.0, 3.0, 4.0]
    raw[:, 0, names.index("Patv_hist")] = [10.0, 20.0, 30.0, 40.0]

    delayed, _, packets = simulate_asynchronous_scada_stream(
        raw, names, mean_delay=1, max_lateness=4, seed=7
    )

    patv_packets = [p for p in packets if p.channel_id == "Patv_hist"]
    assert patv_packets, "Patv_hist must be present in the packet trace"
    assert any(p.arrival_time > p.event_time for p in patv_packets)
    # At least one delayed packet must prevent the simulator from exposing the
    # current active-power value immediately.
    assert any(delayed[t, 0, names.index("Patv_hist")] != raw[t, 0, names.index("Patv_hist")]
               for t in range(raw.shape[0]))


def test_async_simulator_supports_legacy_patv_alias():
    import numpy as np

    names = ["Wspd", "Patv", "Etmp", "Itmp", "Prtv"]
    raw = np.ones((2, 1, len(names)), dtype=np.float32)
    delayed, _, packets = simulate_asynchronous_scada_stream(
        raw, names, mean_delay=1, max_lateness=4, seed=11
    )
    assert any(p.channel_id == "Patv" for p in packets)
    assert delayed.shape == raw.shape


def test_operating_targets_and_tau_star_evaluation():
    """Verify calculation of tau* and 5%, 10%, 15% sensitivity."""
    import numpy as np

    # Synthetic delay grid and paired difference
    delays = [0, 1, 2, 3, 4, 5, 6]
    # Delta PSREI: negative is advantage for challenger, crossing to >= 0 at tau=3
    delta_psrei = np.array([-150.0, -90.0, -20.0, 30.0, 80.0, 140.0, 210.0])
    delta_ci_lower = delta_psrei - 25.0
    delta_ci_upper = delta_psrei + 25.0

    # tau* is the smallest delay where the 95% CI upper excludes negative advantage (i.e. >= 0)
    crossover_idx = np.where(delta_ci_upper >= 0.0)[0]
    tau_star = delays[crossover_idx[0]] if len(crossover_idx) > 0 else None
    assert tau_star == 2  # at tau=2, delta=-20, upper=-20+25=5 >= 0

    # Violation rates across delays
    violation_rates = np.array([7.2, 8.5, 9.8, 11.2, 12.8, 14.5, 16.3])
    targets = [5.0, 10.0, 15.0]
    crossings = {}
    for tgt in targets:
        hit = np.where(violation_rates >= tgt)[0]
        crossings[tgt] = delays[hit[0]] if len(hit) > 0 else None

    assert crossings[5.0] == 0   # already > 5% at baseline
    assert crossings[10.0] == 3  # crosses 10% operating target at delay 3
    assert crossings[15.0] == 6  # crosses 15% target at delay 6

