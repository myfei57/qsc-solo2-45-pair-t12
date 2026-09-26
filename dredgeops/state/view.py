"""Consolidated read model."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ControlState:
    tick: int
    committed_keys: int
    events: int
    watermark: int
    subsystems: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "committed_keys": self.committed_keys,
            "events": self.events,
            "watermark": self.watermark,
            "subsystems": {name: value for name, value in self.subsystems.items()},
        }
