from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class OpponentMoveEvent:
    prev_fen: str
    new_fen: str
    uci: str

@dataclass(frozen=True)
class OurMoveEvent:
    uci: str
    plan_summary: str

@dataclass(frozen=True)
class VerifyEvent:
    expected_fen: str
    observed_fen: Optional[str]
    success: bool
