from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any

StepType = Literal["REMOVE", "MOVE", "HOME"]

@dataclass(frozen=True)
class PlanStep:
    type: StepType
    src: Optional[str] = None
    dst: Optional[str] = None
    meta: Dict[str, Any] = None
