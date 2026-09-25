"""Read model for the hopper subsystem."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HopperView:
    gate_open: bool
    compartments: Mapping[str, float]
    capacity: float
    discharge_blocked: bool
    wash_running: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_open": self.gate_open,
            "compartments": dict(self.compartments),
            "capacity": self.capacity,
            "discharge_blocked": self.discharge_blocked,
            "wash_running": self.wash_running,
        }
