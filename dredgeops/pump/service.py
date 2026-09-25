"""Mud pump sequencing and calibration.

Flush water has to be running before the pump starts and the overflow door has to be
shut before an orderly stop. The pump state itself has to be durable before the arm
may be lowered, which is enforced by the drag subsystem's pre-gate.
"""

from typing import Any, Protocol

from ..clock import LogicalClock
from ..errors import PreGateError
from ..event import EventBus, topics
from ..store import Journal, keys
from ..verdict import Band
from ..version import Confirmations, Generations
from . import calc
from .view import PumpView

PUMP_NAME = "pump"
CURVE_NAME = "pump.curve"


class JetSource(Protocol):
    """Anything that can report whether flush water is running."""

    def is_open(self) -> bool: ...


class OverflowSource(Protocol):
    """Anything that can report whether the overflow door is shut."""

    def closed(self) -> bool: ...


class Liftable(Protocol):
    """Anything that can raise the suction arm."""

    def lift(self) -> int: ...


class Closable(Protocol):
    """Anything that can shut the overflow door."""

    def close(self) -> int: ...


class PumpService:
    """Pump control with flush water, overflow and calibration interlocks."""

    def __init__(
        self,
        journal: Journal,
        bus: EventBus,
        clock: LogicalClock,
        generations: Generations,
        confirmations: Confirmations,
    ) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._generations = generations
        self._confirmations = confirmations
        self._slope_band = Band(0.05, 20.0)
        self._depth = 6
        self._running = False
        self._persisted = False
        self._persisted_tick = 0
        self._curve: dict[str, float] = {"slope": 1.0, "base": 0.0, "generation": 0}

    # ----------------------------------------------------------------- reading

    def depth(self) -> int:
        return self._depth

    def set_depth(self, depth: int) -> None:
        if depth < 0:
            raise ValueError("depth must not be negative")
        self._depth = int(depth)

    def running(self) -> bool:
        return self._running

    def persisted(self) -> bool:
        return self._persisted

    def curve(self) -> dict[str, float]:
        return dict(self._curve)

    def view(self) -> PumpView:
        return PumpView(
            running=self._running,
            depth=self._depth,
            persisted=self._persisted,
            persisted_tick=self._persisted_tick,
            slope=self._curve["slope"],
            base=self._curve["base"],
            generation=int(self._curve["generation"]),
        )

    # ------------------------------------------------------------------ writes

    def persist(self) -> int:
        """Make the pump state durable; the arm drop is gated on this value."""
        tick = self._clock.tick
        with self._journal.transaction("pump-persist") as batch:
            self._journal.append(
                keys.PUMP_STATE,
                {
                    "depth": self._depth,
                    "curve": dict(self._curve),
                    "tick": tick,
                },
                batch,
                generation=int(self._curve["generation"]),
            )
        self._persisted = True
        self._persisted_tick = tick
        self._bus.publish(topics.TOPIC_PUMP_PERSISTED, self._depth)
        return tick

    def start(self, jet: JetSource) -> int:
        """Start the pump; flush water has to be open first."""
        if not jet.is_open():
            raise PreGateError("pump: flush water is not open")
        tick = self._clock.tick
        with self._journal.transaction("pump-start") as batch:
            self._journal.append(
                keys.PUMP_RUNNING,
                {"running": True, "tick": tick},
                batch,
                generation=int(self._curve["generation"]),
            )
        self._running = True
        self._bus.publish(topics.TOPIC_PUMP_STARTED, tick)
        return tick

    def stop(self, overflow: OverflowSource) -> int:
        """Orderly stop; the overflow door has to be shut first."""
        if not overflow.closed():
            raise PreGateError("pump: overflow door is not shut")
        return self._halt(emergency=False)

    def emergency_stop(self) -> int:
        """Stop that bypasses the overflow interlock."""
        return self._halt(emergency=True)

    def shutdown(self, arm: Liftable, overflow: Closable) -> dict[str, Any]:
        """Raise the arm, shut the overflow door, then stop the pump."""
        arm.lift()
        overflow.close()
        tick = self._halt(emergency=False)
        return {"stopped_tick": tick, "running": self._running}

    def recalibrate_curve(self, slope: float, base: float, confirmation_id: str) -> dict[str, Any]:
        """Replace the discharge curve under a confirmation and a new generation."""
        self._slope_band.require(slope, "curve slope")
        self._confirmations.redeem(confirmation_id, CURVE_NAME, PUMP_NAME)
        generation = self._generations.advance(CURVE_NAME, "pump-curve-generation")
        tick = self._clock.tick
        row = {
            "slope": float(slope),
            "base": float(base),
            "generation": generation,
            "tick": tick,
        }
        with self._journal.transaction("pump-curve") as batch:
            self._journal.append(keys.PUMP_CURVE, row, batch, generation=generation)
        self._curve = {"slope": float(slope), "base": float(base), "generation": generation}
        self._bus.publish(topics.TOPIC_CURVE_SET, generation)
        return dict(row)

    def reload(self) -> PumpView:
        """Restore pump state from the committed part of the stream."""
        state = self._journal.read(keys.PUMP_STATE)
        if state is not None:
            self._depth = int(state["depth"])
            self._persisted = True
            self._persisted_tick = int(state["tick"])
            stored = state.get("curve")
            if isinstance(stored, dict):
                self._curve = {
                    "slope": float(stored["slope"]),
                    "base": float(stored["base"]),
                    "generation": int(stored["generation"]),
                }
        running = self._journal.read(keys.PUMP_RUNNING)
        if running is not None:
            self._running = bool(running["running"])
        curve = self._journal.read(keys.PUMP_CURVE)
        if curve is not None:
            self._curve = {
                "slope": float(curve["slope"]),
                "base": float(curve["base"]),
                "generation": int(curve["generation"]),
            }
        return self.view()

    # -------------------------------------------------------------- arithmetic

    def rate(self, speed: float) -> float:
        return calc.discharge(self._curve, speed)

    def time_to_fill(self, speed: float, volume: float) -> float:
        return calc.time_to_fill(self._curve, speed, volume)

    def power(self, speed: float, head: float) -> float:
        return calc.power(self.rate(speed), head)

    def power_factor(self, power_value: float, rated: float) -> float:
        return calc.power_factor(power_value, rated)

    def overload(self, power_value: float, rated: float) -> bool:
        return calc.overload(power_value, rated)

    def pressure(self, head: float, flow: float) -> float:
        return calc.pressure(head, flow)

    def boost_pressure(self, current: float, target: float) -> float:
        return calc.boost_pressure(current, target)

    # ---------------------------------------------------------------- internals

    def _halt(self, emergency: bool) -> int:
        tick = self._clock.tick
        with self._journal.transaction("pump-stop") as batch:
            self._journal.append(
                keys.PUMP_RUNNING,
                {"running": False, "tick": tick, "emergency": emergency},
                batch,
                generation=int(self._curve["generation"]),
            )
        self._running = False
        self._bus.publish(topics.TOPIC_PUMP_STOPPED, {"tick": tick, "emergency": emergency})
        return tick
