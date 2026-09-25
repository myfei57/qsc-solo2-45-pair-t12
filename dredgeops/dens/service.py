"""Density baseline and efficiency verdicts.

The baseline is a parameter set with a generation. Replacing the probe moves the
generation on without writing a new baseline, which leaves the previous baseline
expired, so every efficiency verdict is refused until a fresh calibration lands.
"""

from typing import Any

from ..clock import LogicalClock
from ..errors import StaleArtifactError
from ..event import EventBus, topics
from ..store import Journal, keys
from ..verdict import (
    ABOVE_MODE,
    Band,
    VerdictHistory,
    Window,
    WindowEvaluator,
    WindowVerdict,
)
from ..version import Confirmations, Generations
from . import calc
from .view import DensView

BASELINE_NAME = "dens.baseline"
DENS_NAME = "dens"
SAMPLE_LIMIT = 50
WINDOW_SIZE = 3
BAND = Band(900.0, 1300.0)


class DensService:
    """Density baseline, sample window and efficiency verdicts."""

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
        self._band = BAND
        self._history = VerdictHistory("dens.efficiency")
        self._sustained = WindowEvaluator(
            Window(WINDOW_SIZE),
            100.0,
            ABOVE_MODE,
            WINDOW_SIZE,
        )

    # ----------------------------------------------------------------- reading

    def baseline(self) -> dict[str, Any] | None:
        return self._journal.read(keys.DENS_BASELINE)

    def offset(self) -> float:
        row = self.baseline()
        if row is None:
            return 0.0
        return float(row["offset"])

    def generation(self) -> int:
        row = self.baseline()
        if row is None:
            return 0
        return int(row["generation"])

    def require_fresh_baseline(self) -> dict[str, Any]:
        """Return the baseline in force or refuse a verdict built on a stale one."""
        row = self.baseline()
        if row is None:
            raise StaleArtifactError("no density baseline has been calibrated")
        self._generations.require_current(
            BASELINE_NAME,
            int(row["generation"]),
            "density baseline",
        )
        return row

    def history(self) -> VerdictHistory:
        return self._history

    def samples(self) -> tuple[dict[str, Any], ...]:
        rows = self._journal.read(keys.DENS_SAMPLES)
        if rows is None:
            return ()
        return tuple(rows)

    def sample_average(self) -> float:
        return calc.average(self.samples())

    def view(self) -> DensView:
        row = self.baseline()
        return DensView(
            baseline=0.0 if row is None else float(row["baseline"]),
            offset=self.offset(),
            generation=self.generation(),
            calibrated=row is not None,
            samples=len(self.samples()),
        )

    # ------------------------------------------------------------------ writes

    def calibrate(self, baseline: float, confirmation_id: str) -> dict[str, Any]:
        """Adopt a new baseline under a confirmation and a new generation."""
        self._band.require(baseline, "density baseline")
        self._confirmations.redeem(confirmation_id, BASELINE_NAME, DENS_NAME)
        generation = self._generations.advance(BASELINE_NAME, "dens-generation")
        tick = self._clock.tick
        row = {
            "baseline": float(baseline),
            "offset": float(baseline),
            "generation": generation,
            "tick": tick,
        }
        with self._journal.transaction("dens-calibrate") as batch:
            self._journal.append(keys.DENS_BASELINE, row, batch, generation=generation)
        self._bus.publish(topics.TOPIC_BASELINE_SET, generation)
        self._sustained.window.clear()
        return dict(row)

    def replace_probe(self) -> int:
        """Move the generation on so the stored baseline can no longer be used."""
        generation = self._generations.advance(BASELINE_NAME, "dens-probe")
        self._bus.publish(topics.TOPIC_BASELINE_INVALIDATED, generation)
        return generation

    def add_sample(self, reading: float) -> dict[str, Any]:
        rows = list(self.samples())
        rows.append({"reading": float(reading), "tick": self._clock.tick})
        rows = rows[-SAMPLE_LIMIT:]
        with self._journal.transaction("dens-sample") as batch:
            self._journal.append(keys.DENS_SAMPLES, rows, batch)
        return {"samples": len(rows), "average": calc.average(rows)}

    # ----------------------------------------------------------------- verdicts

    def efficiency(self, reading: float) -> float:
        baseline = self.require_fresh_baseline()
        return calc.efficiency(reading, float(baseline["offset"]))

    def verdict_of(self, reading: float) -> str:
        value = self.efficiency(reading)
        result = calc.verdict(value)
        self._history.record(
            result,
            self._journal.watermark,
            self._clock.tick,
            f"reading={reading}",
        )
        return result

    def sustained_verdict(self, reading: float) -> WindowVerdict:
        """Efficiency verdict that only holds across a full window of readings."""
        return self._sustained.push(self.efficiency(reading))

    def reload(self) -> DensView:
        return self.view()
