from __future__ import annotations
import time

def now_ms() -> int:
    return int(time.time() * 1000)

def sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)
