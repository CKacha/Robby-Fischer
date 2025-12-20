from __future__ import annotations
from collections import deque
from typing import Optional

class FenStability:
    def __init__(self, maxlen: int = 64) -> None:
        self.buf = deque(maxlen=maxlen)

    def push(self, fen: str) -> None:
        self.buf.append(fen)

    def reset(self) -> None:
        self.buf.clear()

    def get_stable(self, k: int = 6) -> Optional[str]:
        if len(self.buf) < k:
            return None
        last = self.buf[-1]
        # stable if last k entries all equal
        for i in range(1, k + 1):
            if self.buf[-i] != last:
                return None
        return last
