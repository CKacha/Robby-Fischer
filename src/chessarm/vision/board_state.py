from __future__ import annotations
from typing import Optional, List
import numpy as np

from chessarm.vision.piece_model import PieceModelStub

_PIECE_TO_FEN = {
    "wp": "P", "wn": "N", "wb": "B", "wr": "R", "wq": "Q", "wk": "K",
    "bp": "p", "bn": "n", "bb": "b", "br": "r", "bq": "q", "bk": "k",
    "empty": None,
}

class BoardStateEstimator:
    def __init__(self, model: PieceModelStub, rectifier, board_cfg: dict) -> None:
        self.model = model
        self.rectifier = rectifier
        self.board_cfg = board_cfg

        # v1 assumptions
        self.side_to_move = "w"
        self.castling = "KQkq"
        self.ep = "-"
        self.halfmove = 0
        self.fullmove = 1

    def estimate_fen(self, frame_bgr: np.ndarray) -> Optional[str]:
        board_img = self.rectifier.rectify(frame_bgr)
        grid = self.model.predict_grid(board_img)
        fen_board = self.grid_to_piece_placement(grid)
        if not fen_board:
            return None
        # IMPORTANT: v1 uses static metadata; later you’ll maintain this from python-chess state
        fen = f"{fen_board} {self.side_to_move} {self.castling} {self.ep} {self.halfmove} {self.fullmove}"
        return fen

    @staticmethod
    def grid_to_piece_placement(grid: List[List[str]]) -> str:
        """
        grid is 8x8 from rank 8 to rank 1, file a to h (top-left is a8).
        If your camera orientation differs, fix it in rectify().
        """
        rows = []
        for r in range(8):
            empties = 0
            out = ""
            for c in range(8):
                label = grid[r][c]
                fen_piece = _PIECE_TO_FEN.get(label)
                if fen_piece is None:
                    empties += 1
                else:
                    if empties:
                        out += str(empties)
                        empties = 0
                    out += fen_piece
            if empties:
                out += str(empties)
            rows.append(out)
        return "/".join(rows)
