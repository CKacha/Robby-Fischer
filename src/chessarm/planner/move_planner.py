from __future__ import annotations
import chess
from chessarm.planner.plan_types import PlanStep

def make_plan(board: chess.Board, uci: str) -> list[PlanStep]:
    """
    Convert a UCI move into physical steps.
    v1 supports: normal + capture.
    TODO: castling, en passant, promotion.
    """
    mv = chess.Move.from_uci(uci)
    if mv not in board.legal_moves:
        # still return a basic move plan; orchestrator may stop later
        return [PlanStep(type="MOVE", src=chess.square_name(mv.from_square), dst=chess.square_name(mv.to_square), meta={})]

    src = chess.square_name(mv.from_square)
    dst = chess.square_name(mv.to_square)

    steps: list[PlanStep] = []
    if board.is_capture(mv):
        # remove piece on destination square (or en passant later)
        steps.append(PlanStep(type="REMOVE", src=dst, meta={"reason": "capture"}))
    steps.append(PlanStep(type="MOVE", src=src, dst=dst, meta={}))
    steps.append(PlanStep(type="HOME", meta={}))
    return steps
    