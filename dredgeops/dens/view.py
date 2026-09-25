"""Read model for the density subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DensView:
    baseline: float
    offset: float
    generation: int
    calibrated: bool
    samples: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline,
            "offset": self.offset,
            "generation": self.generation,
            "calibrated": self.calibrated,
            "samples": self.samples,
        }
