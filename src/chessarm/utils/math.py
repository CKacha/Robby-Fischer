from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PoseMM:
    """Simple pose container in millimeters for v1."""
    x_mm: float
    y_mm: float
    z_mm: float
    rx_deg: float = 0.0
    ry_deg: float = 0.0
    rz_deg: float = 0.0
