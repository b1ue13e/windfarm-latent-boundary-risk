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
