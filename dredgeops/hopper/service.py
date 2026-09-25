"""Mud hopper control.

The compartment map is a parameter set: it carries a generation and a rebuild has to
be confirmed before it is accepted. Each discharge batch is recorded once, so a
repeated batch identifier is refused rather than double counted.
"""

from typing import Any, Mapping, Protocol

from ..clock import LogicalClock
from ..event import EventBus, topics
from ..store import Journal, keys
from ..verdict import (
    ABOVE_MODE,
    BatchRegistry,
    VerdictHistory,
    Window,
    WindowEvaluator,
    WindowVerdict,
)
from ..version import Confirmations, Generations
from . import calc
from .view import HopperView

MAP_NAME = "hopper.map"
HOPPER_NAME = "hopper"
WINDOW_SIZE = 3


class RateSource(Protocol):
    """Anything that can report a volumetric rate for a pump speed."""

    def rate(self, speed: float) -> float: ...


class HopperService:
    """Hopper gate, compartment map, level estimate and discharge latch."""

    def __init__(
        self,
        journal: Journal,
        bus: EventBus,
        clock: LogicalClock,
        generations: Generations,
        confirmations: Confirmations,
        batches: BatchRegistry,
    ) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._generations = generations
        self._confirmations = confirmations
        self._batches = batches
        self._gate = False
        self._map = calc.default_compartments()
        self._rate_cache: dict[float, float] = {}
        self._history = VerdictHistory("hopper.fullness")
        self._sustained = WindowEvaluator(
            Window(WINDOW_SIZE),
            1.0,
            ABOVE_MODE,
            WINDOW_SIZE,
        )

    # ----------------------------------------------------------------- reading

    def gate_open(self) -> bool:
        return self._gate

    def compartments(self) -> dict[str, float]:
        return dict(self._map)

    def capacity(self) -> float:
        return calc.total_capacity(self._map)

    def fullness(self, level: float) -> float:
        return calc.fullness(level, self.capacity())

    def full_verdict(self, level: float) -> bool:
        return calc.full_verdict(level, self.capacity())

    def probes(self) -> dict[str, float]:
        row = self._journal.read(keys.HOPPER_PROBES)
        if row is None:
            return {"bow": 0.0, "mid": 0.0, "stern": 0.0}
        return {str(name): float(level) for name, level in row.items()}

    def average_level(self) -> float:
        return calc.average_level(self.probes())

    def wash_state(self) -> dict[str, Any]:
        row = self._journal.read(keys.HOPPER_WASH)
        if row is None:
            return {"running": False, "tick": 0}
        return {"running": bool(row["running"]), "tick": int(row["tick"])}

    def can_discharge(self) -> bool:
        released = self._journal.read(keys.HOPPER_RELEASE)
        if released is None:
            return True
        return bool(released["released"])

    def batch_total(self) -> float:
        return float(sum(float(entry["volume"]) for entry in self.batch_entries()))

    def batch_entries(self) -> tuple[Mapping[str, Any], ...]:
        return self._batches.entries()

    def view(self) -> HopperView:
        return HopperView(
            gate_open=self._gate,
            compartments=self.compartments(),
            capacity=self.capacity(),
            discharge_blocked=not self.can_discharge(),
            wash_running=self.wash_state()["running"],
        )

    # ------------------------------------------------------------------ writes

    def open_gate(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("hopper-gate") as batch:
            self._journal.append(keys.HOPPER_GATE, {"open": True, "tick": tick}, batch)
        self._gate = True
        self._bus.publish(topics.TOPIC_GATE_OPENED, tick)
        return tick

    def close_gate(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("hopper-gate") as batch:
            self._journal.append(keys.HOPPER_GATE, {"open": False, "tick": tick}, batch)
        self._gate = False
        self._bus.publish(topics.TOPIC_GATE_CLOSED, tick)
        return tick

    def rebuild(self, compartments: Mapping[str, float], confirmation_id: str) -> dict[str, Any]:
        """Replace the compartment map under a confirmation and a new generation."""
        checked = calc.validate_compartments(compartments)
        self._confirmations.redeem(confirmation_id, MAP_NAME, HOPPER_NAME)
        generation = self._generations.advance(MAP_NAME, "hopper-map-generation")
        row = {
            "compartments": checked,
            "generation": generation,
            "tick": self._clock.tick,
        }
        with self._journal.transaction("hopper-map") as batch:
            self._journal.append(keys.HOPPER_MAP, row, batch, generation=generation)
        self._map = dict(checked)
        self._bus.publish(topics.TOPIC_MAP_REBUILT, generation)
        return dict(row)

    def set_probe(self, name: str, level: float) -> dict[str, float]:
        probes = self.probes()
        probes[str(name)] = float(level)
        with self._journal.transaction("hopper-probe") as batch:
            self._journal.append(keys.HOPPER_PROBES, probes, batch)
        return probes

    def estimate_level(self, pump: RateSource, speed: float) -> float:
        """Level estimate for a pump speed, reused until the curve generation moves."""
        key = float(speed)
        rate = self._rate_cache.get(key)
        if rate is None:
            rate = pump.rate(key)
            self._rate_cache[key] = rate
        return calc.estimated_level(rate, 1.5)

    def time_to_fill(self, pump: RateSource, speed: float) -> float:
        rate = calc.estimated_level(pump.rate(speed), 1.0)
        if rate <= 0:
            return 0.0
        return self.capacity() / rate

    def sustained_full(self, level: float) -> WindowVerdict:
        """Full verdict that only holds once a whole window of samples agrees."""
        verdict = self._sustained.push(self.fullness(level))
        self._history.record(
            verdict.verdict,
            self._journal.watermark,
            self._clock.tick,
            f"fullness={verdict.average:.3f}",
        )
        return verdict

    def history(self) -> VerdictHistory:
        return self._history

    def lock_discharge(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("hopper-release") as batch:
            self._journal.append(
                keys.HOPPER_RELEASE,
                {"released": False, "tick": tick},
                batch,
            )
        self._bus.publish(topics.TOPIC_DISCHARGE_LOCKED, tick)
        return tick

    def release_latch(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("hopper-release") as batch:
            self._journal.append(
                keys.HOPPER_RELEASE,
                {"released": True, "tick": tick},
                batch,
            )
        self._bus.publish(topics.TOPIC_DISCHARGE_FREED, tick)
        return tick

    def record_batch(self, batch_id: str, compartment: str, volume: float) -> dict[str, Any]:
        """Record a discharge batch; a repeated identifier is refused."""
        self._batches.reserve(
            batch_id,
            {
                "compartment": compartment,
                "volume": float(volume),
                "tick": self._clock.tick,
            },
        )
        self._bus.publish(topics.TOPIC_HOPPER_BATCH, batch_id)
        return {
            "batch_id": batch_id,
            "compartment": compartment,
            "volume": float(volume),
            "total": self.batch_total(),
        }

    def start_wash(self) -> int:
        return self._set_wash(True)

    def stop_wash(self) -> int:
        return self._set_wash(False)

    def wire(self) -> None:
        """Drop the level cache whenever the discharge curve changes."""
        self._bus.subscribe(topics.TOPIC_CURVE_SET, self._on_curve_change)
        self._bus.subscribe(topics.TOPIC_MAP_REBUILT, self._on_map_change)

    def reload(self) -> HopperView:
        gate = self._journal.read(keys.HOPPER_GATE)
        if gate is not None:
            self._gate = bool(gate["open"])
        stored_map = self._journal.read(keys.HOPPER_MAP)
        if stored_map is not None:
            self._map = {str(k): float(v) for k, v in stored_map["compartments"].items()}
        return self.view()

    # ---------------------------------------------------------------- internals

    def _set_wash(self, running: bool) -> int:
        tick = self._clock.tick
        with self._journal.transaction("hopper-wash") as batch:
            self._journal.append(
                keys.HOPPER_WASH,
                {"running": running, "tick": tick},
                batch,
            )
        return tick

    def _on_curve_change(self, event: Any) -> None:
        self._rate_cache = {}

    def _on_map_change(self, event: Any) -> None:
        self._sustained.window.clear()
