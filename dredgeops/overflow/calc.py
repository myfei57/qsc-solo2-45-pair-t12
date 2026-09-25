"""Spill and overflow arithmetic."""


def flow(level: float, rate: float, closed: bool) -> float:
    """Overflow discharge; a shut door passes nothing."""
    if closed:
        return 0.0
    return float(level) * float(rate) * 0.02


def spill_verdict(level: float, capacity: float, closed: bool, margin: float = 0.95) -> bool:
    return float(level) > float(capacity) * margin and not closed


def residual(level: float, share: float = 0.6) -> float:
    if level <= 0:
        return 0.0
    return float(level) * float(share)


def judge_full(level: float, capacity: float) -> bool:
    return float(level) >= float(capacity)
