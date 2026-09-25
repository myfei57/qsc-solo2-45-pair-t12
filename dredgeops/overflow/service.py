"""Overflow door control.

The spill judgement needs the hopper capacity, which is cached and dropped whenever
the hopper reports a rebuilt compartment map.
"""

from typing import Any, Protocol

from ..clock import LogicalClock
from ..event import EventBus, topics
from ..store import Journal, keys
from . import calc
from .view import OverflowView


class CapacitySource(Protocol):
    """Anything that can report the hopper capacity."""

    def capacity(self) -> float: ...


class OverflowService:
    """Shuts and opens the overflow door and judges spill conditions."""

    def __init__(self, journal: Journal, bus: EventBus, clock: LogicalClock) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._closed = False
        self._capacity_cache: float | None = None

    def closed(self) -> bool:
        return self._closed

    def close(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("overflow-close") as batch:
            self._journal.append(keys.OVERFLOW_GATE, {"closed": True, "tick": tick}, batch)
        self._closed = True
        self._bus.publish(topics.TOPIC_OVERFLOW_CLOSED, tick)
        return tick

    def open_gate(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("overflow-open") as batch:
            self._journal.append(keys.OVERFLOW_GATE, {"closed": False, "tick": tick}, batch)
        self._closed = False
        self._bus.publish(topics.TOPIC_OVERFLOW_OPENED, tick)
        return tick

    def capacity(self, hopper: CapacitySource) -> float:
        """Capacity of the hopper, reused until the compartment map changes."""
        if self._capacity_cache is None:
            self._capacity_cache = hopper.capacity()
        return self._capacity_cache

    def flow(self, level: float, rate: float) -> float:
        return calc.flow(level, rate, self._closed)

    def spill_verdict(self, level: float, capacity: float) -> bool:
        return calc.spill_verdict(level, capacity, self._closed)

    def residual(self, level: float) -> float:
        return calc.residual(level)

    def judge_full(self, hopper: CapacitySource, level: float) -> bool:
        return calc.judge_full(level, self.capacity(hopper))

    def wire(self) -> None:
        """Forget the cached capacity when the hopper map is rebuilt."""
        self._bus.subscribe(topics.TOPIC_MAP_REBUILT, self._on_map_rebuilt)

    def reload(self) -> OverflowView:
        row = self._journal.read(keys.OVERFLOW_GATE)
        if row is not None:
            self._closed = bool(row["closed"])
        return self.view()

    def view(self) -> OverflowView:
        return OverflowView(
            closed=self._closed,
            cached_capacity=0.0 if self._capacity_cache is None else self._capacity_cache,
        )

    def _on_map_rebuilt(self, event: Any) -> None:
        self._capacity_cache = None
