"""Hopper capacity and level arithmetic."""

from typing import Mapping

from ..errors import OutOfRangeError


def default_compartments() -> dict[str, float]:
    """Compartment volumes of a freshly commissioned hopper."""
    return {"bow": 40.0, "mid": 60.0, "stern": 50.0}


def validate_compartments(compartments: Mapping[str, float]) -> dict[str, float]:
    """Reject an empty or non-positive compartment map."""
    if not compartments:
        raise OutOfRangeError("compartment map must declare at least one hold")
    checked: dict[str, float] = {}
    for name, volume in compartments.items():
        if volume <= 0:
            raise OutOfRangeError(f"compartment {name} has a non-positive volume")
        checked[str(name)] = float(volume)
    return checked


def total_capacity(compartments: Mapping[str, float]) -> float:
    return float(sum(compartments.values()))


def fullness(level: float, capacity: float) -> float:
    if capacity <= 0:
        return 0.0
    return float(level) / float(capacity)


def full_verdict(level: float, capacity: float) -> bool:
    return fullness(level, capacity) >= 1.0


def estimated_level(rate: float, factor: float) -> float:
    return float(rate) * float(factor)


def average_level(probes: Mapping[str, float]) -> float:
    if not probes:
        return 0.0
    return float(sum(probes.values())) / len(probes)
