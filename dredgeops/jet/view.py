"""Read model for the flush water subsystem."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JetView:
    open: bool

    def to_dict(self) -> dict[str, Any]:
        return {"open": self.open}
