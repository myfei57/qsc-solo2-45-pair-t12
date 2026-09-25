"""Read model for the pump subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PumpView:
    running: bool
    depth: int
    persisted: bool
    persisted_tick: int
    slope: float
    base: float
    generation: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "depth": self.depth,
            "persisted": self.persisted,
            "persisted_tick": self.persisted_tick,
            "slope": self.slope,
            "base": self.base,
            "generation": self.generation,
        }
