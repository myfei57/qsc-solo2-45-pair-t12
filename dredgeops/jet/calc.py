"""Flush water pressure arithmetic."""

from typing import Any


def pressure(is_open: bool, flow: float) -> float:
    """Nozzle pressure; a closed valve delivers nothing."""
    if not is_open:
        return 0.0
    return 30.0 + float(flow) * 0.4


def nozzle_state(is_open: bool, flow: float) -> dict[str, Any]:
    return {"open": is_open, "pressure": pressure(is_open, flow)}
