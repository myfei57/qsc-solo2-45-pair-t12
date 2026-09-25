"""Survey line scheduling.

A line latches when it opens. The latch only clears once the measured result has been
committed, so a failed write leaves the line locked instead of silently closing it.
"""

from typing import Any

from ..clock import LogicalClock
from ..errors import DuplicateBatchError, LatchClearError, LatchSetError, MaintenanceError, PreGateError
from ..event import EventBus, topics
from ..interlock import Latch
from ..store import Journal, keys
from . import calc
from .view import PosView


class PosService:
    """Survey line latch, geometry and waypoints."""

    def __init__(self, journal: Journal, bus: EventBus, clock: LogicalClock) -> None:
        self._journal = journal
        self._bus = bus
        self._clock = clock
        self._latch = Latch(
            "pos.line",
            set_conditions=("line_registered",),
            clear_conditions=("result_committed",),
        )
        self._active_line = ""
        self._done = 0

    # ----------------------------------------------------------------- reading

    def latch(self) -> bool:
        return self._latch.is_set

    def active_line(self) -> str:
        return self._active_line

    def done_lines(self) -> int:
        return self._done

    def track(self) -> dict[str, Any]:
        return calc.track(self._done, self._latch.is_set)

    def waypoint(self) -> dict[str, Any] | None:
        return self._journal.read(keys.POS_WAYPOINT)

    def results(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._journal.read(key) for key in self._journal.keys(keys.POS_LINE_RESULT)
        )

    def view(self) -> PosView:
        return PosView(
            latched=self._latch.is_set,
            active_line=self._active_line,
            done_lines=self._done,
        )

    # ------------------------------------------------------------------ writes

    def begin_line(self, line_id: str) -> dict[str, Any]:
        """Open a survey line and set its latch."""
        if not line_id:
            raise PreGateError("pos: a survey line needs an identifier")
        if self._latch.is_set:
            raise LatchSetError("pos: the previous survey line is still latched")
        if line_id == self._active_line:
            raise DuplicateBatchError(f"pos: line {line_id} is already open")
        self._latch.set({"line_registered": True})
        tick = self._clock.tick
        row = {"active": line_id, "done": self._done, "tick": tick}
        with self._journal.transaction("pos-line") as batch:
            self._journal.append(keys.POS_LATCH, {"latched": True, "tick": tick}, batch)
            self._journal.append(keys.POS_LINE, row, batch)
        self._active_line = line_id
        return dict(row)

    def line_done(self, measured_length: float) -> dict[str, Any]:
        """Close the open line; the latch clears only once the result is committed."""
        if not self._latch.is_set:
            raise LatchClearError("pos: no survey line is open")
        written = self._write_result(measured_length)
        self._latch.clear({"result_committed": written})
        tick = self._clock.tick
        row = {"active": "", "done": self._done, "tick": tick}
        with self._journal.transaction("pos-line-close") as batch:
            self._journal.append(keys.POS_LATCH, {"latched": False, "tick": tick}, batch)
            self._journal.append(keys.POS_LINE, row, batch)
        self._active_line = ""
        self._bus.publish(topics.TOPIC_LINE_DONE, self._done)
        return {"done": self._done, "latched": False}

    def set_waypoint(self, name: str, lat: float, lon: float) -> dict[str, Any]:
        row = {
            "name": name,
            "lat": float(lat),
            "lon": float(lon),
            "tick": self._clock.tick,
        }
        with self._journal.transaction("pos-waypoint") as batch:
            self._journal.append(keys.POS_WAYPOINT, row, batch)
        return dict(row)

    def distance_to(self, lat: float, lon: float) -> dict[str, Any]:
        waypoint = self.waypoint()
        if waypoint is None:
            return {"present": False, "distance": 0.0}
        return {
            "present": True,
            "distance": calc.distance(waypoint["lat"], waypoint["lon"], lat, lon),
        }

    def reload(self) -> PosView:
        latched = self._journal.read(keys.POS_LATCH)
        if latched is not None:
            self._latch.restore(bool(latched["latched"]))
        line = self._journal.read(keys.POS_LINE)
        if line is not None:
            self._active_line = str(line["active"])
            self._done = int(line["done"])
        return self.view()

    # -------------------------------------------------------------- arithmetic

    def geometry(self, start: float, spacing: float, lines: int) -> list[float]:
        return calc.geometry(start, spacing, lines)

    def line_origin(self, index: int, spacing: float) -> float:
        return calc.line_origin(index, spacing)

    # ---------------------------------------------------------------- internals

    def _write_result(self, measured_length: float) -> bool:
        self._done += 1
        row = {
            "line_id": self._active_line,
            "length": float(measured_length),
            "index": self._done,
            "tick": self._clock.tick,
        }
        try:
            with self._journal.transaction("pos-result") as batch:
                self._journal.append(
                    f"{keys.POS_LINE_RESULT}/{self._done:06d}",
                    row,
                    batch,
                )
        except MaintenanceError:
            self._done -= 1
            return False
        return True
