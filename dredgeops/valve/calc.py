"""Valve travel verdicts."""


def stroke_verdict(position: float, target: float, tolerance: float = 2.0) -> str:
    """Whether the valve has reached its target position."""
    delta = abs(float(position) - float(target))
    if delta <= tolerance:
        return "seated"
    return "traveling"
