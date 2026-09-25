"""Density arithmetic."""

from typing import Mapping, Sequence

HIGH = "high"
LOW = "low"


def efficiency(reading: float, offset: float) -> float:
    """Reading measured against the calibrated offset."""
    return float(reading) - float(offset)


def verdict(efficiency_value: float, threshold: float = 100.0) -> str:
    if efficiency_value >= threshold:
        return HIGH
    return LOW


def average(samples: Sequence[Mapping[str, float]]) -> float:
    if not samples:
        return 0.0
    return sum(float(sample["reading"]) for sample in samples) / len(samples)
