"""Fluid and geometry arithmetic for the suction arm."""


def head_pressure(depth: int, density: float) -> float:
    """Static pressure at the suction head."""
    return float(depth) * float(density) * 0.00981


def suction_pressure(head: float, lift_limit: float = 12.0) -> float:
    """Pressure the pump has to overcome beyond the free lift."""
    if head > lift_limit:
        return float(head) - float(lift_limit)
    return 0.0


def angle_limit(angle: float, limit: float) -> bool:
    """True when the arm angle is past its allowed limit."""
    return float(angle) > float(limit)
