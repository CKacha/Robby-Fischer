from __future__ import annotations
import chess
from chessarm.chess.notation import piece_placement

def validate_fen(fen: str) -> bool:
    try:
        chess.Board(fen)
        return True
    except Exception:
        return False

def infer_opponent_move_from_fens(board: chess.Board, prev_fen: str, new_fen: str) -> str | None:
    """
    Given board (which should match prev_fen), infer the single legal move that
    leads to new_fen (by piece placement match). Returns UCI or None.
    """
    target_pp = piece_placement(new_fen)
    if not target_pp:
        return None

    # Ensure board matches prev_fen as best as possible
    try:
        prev_board = chess.Board(prev_fen)
    except Exception:
        prev_board = board.copy(stack=False)

    for mv in prev_board.legal_moves:
        tmp = prev_board.copy(stack=False)
        tmp.push(mv)
        if piece_placement(tmp.fen()) == target_pp:
            return mv.uci()
    return None
