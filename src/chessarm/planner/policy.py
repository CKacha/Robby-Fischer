from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RecoveryPolicy:
    max_retries: int = 1
