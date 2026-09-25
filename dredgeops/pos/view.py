"""Read model for the survey line subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PosView:
    latched: bool
    active_line: str
    done_lines: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "latched": self.latched,
            "active_line": self.active_line,
            "done_lines": self.done_lines,
        }
