from __future__ import annotations

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
