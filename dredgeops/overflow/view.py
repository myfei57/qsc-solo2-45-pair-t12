"""Read model for the overflow subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OverflowView:
    closed: bool
    cached_capacity: float

    def to_dict(self) -> dict[str, Any]:
        return {"closed": self.closed, "cached_capacity": self.cached_capacity}
