"""Suction arm control.

The arm may only be lowered once the pump state is durable, and a new survey line may
only be opened once the previous line's latch has cleared.
"""

from typing import Any, Protocol

from ..clock import LogicalClock
from ..errors import LatchSetError
from ..event import EventBus, topics
from ..interlock import PreGate
from ..store import Journal, keys
from ..verdict import VerdictHistory
from . import calc
from .view import DragView


class PumpSource(Protocol):
    """Anything that can report and restore pump state."""

    def depth(self) -> int: ...

    def reload(self) -> Any: ...


class LatchSource(Protocol):
    """Anything that owns a survey line latch."""

    def latch(self) -> bool: ...

    def begin_line(self, line_id: str) -> dict[str, Any]: ...


class DensitySource(Protocol):
    """Anything that can hand out a baseline that is still in force."""

    def require_fresh_baseline(self) -> dict[str, Any]: ...


class DragService:
    """Arm drop, line scheduling and head efficiency verdicts."""

    def __init__(self, journal: Journal, bus: EventBus, clock: LogicalClock) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._pump_gate = PreGate("drag.lower", journal, keys.PUMP_STATE)
        self._history = VerdictHistory("drag.head")
        self._threshold = 100.0
        self._lowered = False
        self._depth = 0
        self._active_line = ""

    # ----------------------------------------------------------------- reading

    def lowered(self) -> bool:
        return self._lowered

    def depth(self) -> int:
        return self._depth

    def active_line(self) -> str:
        return self._active_line

    def history(self) -> VerdictHistory:
        return self._history

    def line_record(self) -> dict[str, Any]:
        row = self._journal.read(keys.DRAG_LINE)
        if row is None:
            return {"line_id": "", "count": 0}
        return {"line_id": str(row["line_id"]), "count": int(row["count"])}

    def winch(self) -> dict[str, Any] | None:
        return self._journal.read(keys.DRAG_WINCH)

    def view(self) -> DragView:
        return DragView(
            lowered=self._lowered,
            depth=self._depth,
            active_line=self._active_line,
            line_count=self.line_record()["count"],
        )

    # ------------------------------------------------------------------ writes

    def lower(self, pump: PumpSource) -> int:
        """Lower the arm; refuses to move until the pump state is durable."""
        self._pump_gate.require()
        depth = pump.depth()
        tick = self._clock.tick
        with self._journal.transaction("drag-lower") as batch:
            self._journal.append(
                keys.DRAG_LOWER,
                {"depth": depth, "tick": tick},
                batch,
            )
        self._lowered = True
        self._depth = depth
        self._bus.publish(topics.TOPIC_DRAG_LOWERED, depth)
        return depth

    def restart(self, pump: PumpSource) -> int:
        """Recover after a break: restore the pump state, then drop the arm again."""
        pump.reload()
        return self.lower(pump)

    def lift(self) -> int:
        tick = self._clock.tick
        with self._journal.transaction("drag-lift") as batch:
            self._journal.append(keys.DRAG_LIFT, {"lifted": True, "tick": tick}, batch)
        self._lowered = False
        self._bus.publish(topics.TOPIC_DRAG_LIFTED, tick)
        return tick

    def next_line(self, pos: LatchSource, line_id: str) -> dict[str, Any]:
        """Open the next survey line; refuses while the previous latch is set."""
        if pos.latch():
            raise LatchSetError("drag: the previous survey line is still latched")
        pos.begin_line(line_id)
        record = self.line_record()
        row = {
            "line_id": line_id,
            "count": record["count"] + 1,
            "tick": self._clock.tick,
        }
        with self._journal.transaction("drag-line") as batch:
            self._journal.append(keys.DRAG_LINE, row, batch)
        self._active_line = line_id
        self._bus.publish(topics.TOPIC_LINE_STARTED, line_id)
        return dict(row)

    def head(self, dens: DensitySource, reading: float) -> dict[str, Any]:
        """Head efficiency verdict against the baseline that is currently in force."""
        baseline = dens.require_fresh_baseline()
        efficiency = float(reading) - float(baseline["offset"])
        verdict = "high" if efficiency >= self._threshold else "low"
        self._history.record(
            verdict,
            self._journal.watermark,
            self._clock.tick,
            f"reading={reading}",
        )
        return {
            "verdict": verdict,
            "efficiency": efficiency,
            "baseline": float(baseline["baseline"]),
            "generation": int(baseline["generation"]),
        }

    def set_winch(self, cable_out: float, angle: float) -> dict[str, Any]:
        row = {"cable_out": float(cable_out), "angle": float(angle), "tick": self._clock.tick}
        with self._journal.transaction("drag-winch") as batch:
            self._journal.append(keys.DRAG_WINCH, row, batch)
        return {"winch": row, "limited": calc.angle_limit(angle, 70.0)}

    def reload(self) -> DragView:
        lowered = self._journal.read(keys.DRAG_LOWER)
        if lowered is not None:
            self._lowered = True
            self._depth = int(lowered["depth"])
        lifted = self._journal.read(keys.DRAG_LIFT)
        if lifted is not None and lowered is not None:
            if int(lifted["tick"]) >= int(lowered["tick"]):
                self._lowered = False
        line = self.line_record()
        self._active_line = line["line_id"]
        return self.view()

    # -------------------------------------------------------------- arithmetic

    def head_pressure(self, depth: int, density: float) -> float:
        return calc.head_pressure(depth, density)

    def suction_pressure(self, head: float) -> float:
        return calc.suction_pressure(head)

    def angle_limit(self, angle: float, limit: float) -> bool:
        return calc.angle_limit(angle, limit)
