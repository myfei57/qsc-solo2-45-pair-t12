"""Survey line geometry and track arithmetic."""

import math
from typing import Any


def geometry(start: float, spacing: float, lines: int) -> list[float]:
    """Origins of a parallel survey pattern."""
    if lines < 0:
        raise ValueError("line count must not be negative")
    return [float(start) + index * float(spacing) for index in range(lines)]


def line_origin(index: int, spacing: float) -> float:
    if index < 0:
        return 0.0
    return float(index) * float(spacing)


def distance(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    return math.hypot(float(lat_b) - float(lat_a), float(lon_b) - float(lon_a))


def track(done: int, latched: bool) -> dict[str, Any]:
    """How many lines are closed, open and planned so far."""
    open_lines = 1 if latched else 0
    return {"total": done + open_lines, "closed": done, "open": open_lines}
