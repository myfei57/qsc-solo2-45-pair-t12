"""Sea valve and discharge alarm.

The sea valve only opens behind an open hopper gate, and the discharge alarm only
latches while the sea valve is shut, so a discharge can never start mid-transfer.
"""

from typing import Any, Protocol

from ..clock import LogicalClock
from ..errors import PreGateError
from ..event import EventBus, topics
from ..interlock import Latch, PreGate
from ..store import Journal, keys
from . import calc
from .view import ValveView


class GateSource(Protocol):
    """Anything that owns the hopper gate."""

    def gate_open(self) -> bool: ...


class DischargeLatch(Protocol):
    """Anything that owns the discharge release."""

    def lock_discharge(self) -> int: ...

    def release_latch(self) -> int: ...

    def can_discharge(self) -> bool: ...


class ValveService:
    """Sea valve, discharge alarm latch and stroke positioning."""

    def __init__(self, journal: Journal, bus: EventBus, clock: LogicalClock) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._gate_gate = PreGate("valve.sea", journal, keys.HOPPER_GATE)
        self._alarm_latch = Latch(
            "valve.discharge",
            set_conditions=("sea_closed",),
            clear_conditions=("sea_closed",),
        )
        self._sea_open = False

    # ----------------------------------------------------------------- reading

    def sea_open(self) -> bool:
        return self._sea_open

    def alarm_active(self) -> bool:
        return self._alarm_latch.is_set

    def discharge_ready(self, hopper: DischargeLatch) -> bool:
        return not self.alarm_active() and hopper.can_discharge()

    def stroke(self) -> dict[str, Any] | None:
        return self._journal.read(keys.VALVE_STROKE)

    def view(self) -> ValveView:
        return ValveView(sea_open=self._sea_open, alarm=self.alarm_active())

    # ------------------------------------------------------------------ writes

    def open_sea(self, hopper: GateSource) -> dict[str, Any]:
        """Open the sea valve; the hopper gate has to be open and durable first."""
        if not hopper.gate_open():
            raise PreGateError("valve: hopper gate is not open")
        self._gate_gate.require()
        tick = self._clock.tick
        with self._journal.transaction("valve-sea") as batch:
            self._journal.append(keys.VALVE_SEA, {"open": True, "tick": tick}, batch)
        self._sea_open = True
        self._bus.publish(topics.TOPIC_SEA_OPENED, tick)
        return {"sea_open": True, "tick": tick}

    def set_alarm(self, hopper: DischargeLatch) -> dict[str, Any]:
        """Latch the discharge alarm; refused while the sea valve is open."""
        self._alarm_latch.set({"sea_closed": not self._sea_open})
        hopper.lock_discharge()
        tick = self._clock.tick
        with self._journal.transaction("valve-alarm") as batch:
            self._journal.append(keys.VALVE_ALARM, {"alarm": True, "tick": tick}, batch)
        self._bus.publish(topics.TOPIC_VALVE_ALARM, True)
        return {"alarm": True, "tick": tick}

    def clear_alarm(self, hopper: DischargeLatch) -> dict[str, Any]:
        """Clear the discharge alarm; the latch conditions still have to hold."""
        self._alarm_latch.clear({"sea_closed": not self._sea_open})
        hopper.release_latch()
        tick = self._clock.tick
        with self._journal.transaction("valve-alarm") as batch:
            self._journal.append(keys.VALVE_ALARM, {"alarm": False, "tick": tick}, batch)
        self._bus.publish(topics.TOPIC_VALVE_ALARM, False)
        return {"alarm": False, "tick": tick}

    def set_stroke(self, position: float, target: float) -> dict[str, Any]:
        row = {
            "position": float(position),
            "target": float(target),
            "tick": self._clock.tick,
        }
        with self._journal.transaction("valve-stroke") as batch:
            self._journal.append(keys.VALVE_STROKE, row, batch)
        return {"stroke": row, "verdict": calc.stroke_verdict(position, target)}

    def stroke_verdict(self, position: float, target: float) -> str:
        return calc.stroke_verdict(position, target)

    def reload(self) -> ValveView:
        sea = self._journal.read(keys.VALVE_SEA)
        if sea is not None:
            self._sea_open = bool(sea["open"])
        alarm = self._journal.read(keys.VALVE_ALARM)
        if alarm is not None:
            self._alarm_latch.restore(bool(alarm["alarm"]))
        return self.view()
