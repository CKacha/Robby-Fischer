from __future__ import annotations
from typing import List

LABELS = [
    "empty",
    "wp","wn","wb","wr","wq","wk",
    "bp","bn","bb","br","bq","bk",
]

class PieceModelStub:
    """
    Stub that returns an empty board. Replace with a HF model wrapper later.
    Interface is what matters right now.
    """
    def predict_grid(self, board_img) -> List[List[str]]:
        return [["empty" for _ in range(8)] for _ in range(8)]
