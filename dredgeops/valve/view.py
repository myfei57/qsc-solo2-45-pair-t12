"""Read model for the sea valve subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValveView:
    sea_open: bool
    alarm: bool

    def to_dict(self) -> dict[str, Any]:
        return {"sea_open": self.sea_open, "alarm": self.alarm}
