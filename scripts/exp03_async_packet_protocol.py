"""EXP-03 packet-level asynchronous telemetry protocol.

The simulator operates on integer dispatch steps. Every packet carries the
four audit fields required by the preregistration: event_time, arrival_time,
channel_id, and sequence_id. The buffer is causal: at dispatch step t it can
only expose packets with arrival_time <= t. Same-arrival packets are ordered
by (arrival_time, sequence_id, channel_id); duplicate/stale sequence numbers
are rejected and packets arriving after the finite buffer deadline are marked
missing rather than backfilled into the past.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class Packet:
    event_time: int
    arrival_time: int
    channel_id: str
    sequence_id: int
    value: float

    def key(self) -> Tuple[int, int, str]:
        return (self.arrival_time, self.sequence_id, self.channel_id)


@dataclass(frozen=True)
class BufferPolicy:
    max_lateness: int = 2
    drop_late: bool = True
    allow_future_backfill: bool = False

    def __post_init__(self) -> None:
        if self.max_lateness < 0:
            raise ValueError("max_lateness must be non-negative")
        if self.allow_future_backfill:
            raise ValueError("future backfill is prohibited by the causal protocol")


class CausalPacketBuffer:
    """Online packet buffer with explicit late/missing semantics."""

    def __init__(self, channels: Sequence[str], policy: BufferPolicy | None = None):
        self.channels = tuple(channels)
        self.policy = policy or BufferPolicy()
        self._packets: Dict[Tuple[int, str], Packet] = {}
        self._last_sequence: Dict[str, int] = {c: -1 for c in self.channels}
        self.dropped_late: List[Packet] = []
        self.dropped_duplicate: List[Packet] = []

    def ingest(self, packet: Packet, now: int) -> None:
        if packet.channel_id not in self.channels:
            raise ValueError(f"unknown channel: {packet.channel_id}")
        if packet.arrival_time > now:
            raise ValueError("cannot ingest a packet before its arrival_time")
        if packet.sequence_id <= self._last_sequence[packet.channel_id]:
            self.dropped_duplicate.append(packet)
            return
        self._last_sequence[packet.channel_id] = packet.sequence_id
        if now - packet.event_time > self.policy.max_lateness and self.policy.drop_late:
            self.dropped_late.append(packet)
            return
        self._packets[(packet.event_time, packet.channel_id)] = packet

    def view(self, now: int, event_time: int) -> Tuple[Dict[str, float], Dict[str, bool]]:
        values: Dict[str, float] = {}
        mask: Dict[str, bool] = {}
        for channel in self.channels:
            packet = self._packets.get((event_time, channel))
            visible = packet is not None and packet.arrival_time <= now
            mask[channel] = visible
            if visible:
                values[channel] = packet.value
        return values, mask

    def snapshot(self, now: int, event_time: int) -> Dict[str, object]:
        values, mask = self.view(now, event_time)
        return {"now": now, "event_time": event_time, "values": values, "mask": mask}


def make_trace(
    event_values: Mapping[str, Sequence[float]],
    delays: Mapping[str, Sequence[int]],
    seed: int = 0,
) -> List[Packet]:
    """Create a deterministic packet trace from integer-step event series.

    Sequence ids are channel-local and monotone. Delay values are non-negative
    integer steps. The RNG is only used to stable-sort equal arrivals by a
    reproducible sequence tie-break; values themselves are never perturbed.
    """
    del seed  # retained in the API to make the trace seed explicit upstream
    packets: List[Packet] = []
    for channel, series in event_values.items():
        channel_delays = delays[channel]
        if len(series) != len(channel_delays):
            raise ValueError(f"length mismatch for {channel}")
        for event_time, (value, delay) in enumerate(zip(series, channel_delays)):
            if int(delay) < 0:
                raise ValueError("delays must be non-negative integer steps")
            packets.append(Packet(event_time, event_time + int(delay), channel, event_time, float(value)))
    return sorted(packets, key=lambda p: p.key())


def replay_trace(
    packets: Iterable[Packet],
    channels: Sequence[str],
    n_steps: int,
    policy: BufferPolicy | None = None,
) -> List[Dict[str, object]]:
    """Replay packets and return one causal snapshot per integer dispatch step."""
    ordered = sorted(packets, key=lambda p: p.key())
    by_arrival: Dict[int, List[Packet]] = {}
    for packet in ordered:
        by_arrival.setdefault(packet.arrival_time, []).append(packet)
    buffer = CausalPacketBuffer(channels, policy)
    snapshots: List[Dict[str, object]] = []
    for now in range(n_steps):
        for packet in by_arrival.get(now, []):
            buffer.ingest(packet, now)
        values, mask = buffer.view(now, now)
        snapshots.append({"time": now, "values": values, "mask": mask})
    return snapshots
