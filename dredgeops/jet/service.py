"""Flush water control; the pump start is gated on this subsystem."""

from ..clock import LogicalClock
from ..event import EventBus, topics
from ..store import Journal, keys
from . import calc
from .view import JetView


class JetService:
    """Opens and closes the flush water valve."""

    def __init__(self, journal: Journal, bus: EventBus, clock: LogicalClock) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._open = False

    def open_jet(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("jet-open") as batch:
            self._journal.append(keys.JET_OPEN, {"open": True, "tick": tick}, batch)
        self._open = True
        self._bus.publish(topics.TOPIC_JET_OPENED, tick)
        return tick

    def close(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("jet-close") as batch:
            self._journal.append(keys.JET_OPEN, {"open": False, "tick": tick}, batch)
        self._open = False
        self._bus.publish(topics.TOPIC_JET_CLOSED, tick)
        return tick

    def is_open(self) -> bool:
        return self._open

    def reload(self) -> bool:
        row = self._journal.read(keys.JET_OPEN)
        if row is not None:
            self._open = bool(row["open"])
        return self._open

    def pressure(self, flow: float) -> float:
        return calc.pressure(self._open, flow)

    def nozzle_state(self, flow: float) -> dict[str, object]:
        return calc.nozzle_state(self._open, flow)

    def view(self) -> JetView:
        return JetView(open=self._open)
