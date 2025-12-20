from __future__ import annotations

def piece_placement(fen: str) -> str:
    return fen.split(" ")[0] if fen else ""
