"""Discharge, drive load and pressure arithmetic."""

from typing import Mapping


def discharge(curve: Mapping[str, float], speed: float) -> float:
    """Volumetric rate for a pump speed under the current curve."""
    return float(curve["slope"]) * float(speed) + float(curve["base"])


def time_to_fill(curve: Mapping[str, float], speed: float, volume: float) -> float:
    rate = discharge(curve, speed)
    if rate <= 0:
        return 0.0
    return float(volume) / rate


def power(flow: float, head: float) -> float:
    """Shaft power estimate from flow and head."""
    return float(flow) * float(head) * 0.11


def power_factor(power_value: float, rated: float) -> float:
    if rated <= 0:
        return 0.0
    return float(power_value) / float(rated)


def overload(power_value: float, rated: float, limit: float = 1.1) -> bool:
    return power_factor(power_value, rated) > limit


def pressure(head: float, flow: float) -> float:
    """Discharge pressure from static head and flow."""
    return float(head) * 9.81 * 1.02 + float(flow) * 0.35


def boost_pressure(current: float, target: float) -> float:
    if target <= current:
        return 0.0
    return float(target) - float(current)
