"""Read model for the suction arm subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DragView:
    lowered: bool
    depth: int
    active_line: str
    line_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "lowered": self.lowered,
            "depth": self.depth,
            "active_line": self.active_line,
            "line_count": self.line_count,
        }
