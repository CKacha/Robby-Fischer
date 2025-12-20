from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import logging
import chess

from chessarm.vision.stability import FenStability
from chessarm.chess.rules import infer_opponent_move_from_fens, validate_fen
from chessarm.chess.stockfish_engine import StockfishEngine
from chessarm.planner.move_planner import make_plan
from chessarm.robot.macros import RobotMacros

log = logging.getLogger(__name__)

class State(Enum):
    INIT = auto()
    WAIT_OPPONENT = auto()
    THINK = auto()
    ACT = auto()
    VERIFY = auto()
    RECOVER = auto()
    STOP = auto()

@dataclass
class Context:
    board: chess.Board
    current_fen: str

class ChessArmStateMachine:
    def __init__(
        self,
        stability: FenStability,
        engine: StockfishEngine,
        robot: RobotMacros,
        stable_k: int = 6,
    ) -> None:
        self.state = State.INIT
        self.stability = stability
        self.engine = engine
        self.robot = robot
        self.ctx: Context | None = None
        self.stable_k = stable_k
        self._expected_fen_after_our_move: str | None = None
        self._our_uci: str | None = None

    def step(self, observed_fen: str) -> None:
        """
        Call repeatedly with the latest observed FEN (or empty string if not available).
        """
        if self.state == State.STOP:
            return

        if self.state == State.INIT:
            if not observed_fen or not validate_fen(observed_fen):
                log.info("INIT: waiting for valid initial FEN...")
                return
            self.ctx = Context(board=chess.Board(observed_fen), current_fen=observed_fen)
            self.state = State.WAIT_OPPONENT
            log.info("INIT: locked initial position.")
            return

        assert self.ctx is not None

        # Feed stability tracker every tick
        if observed_fen:
            self.stability.push(observed_fen)

        stable = self.stability.get_stable(k=self.stable_k)
        if self.state == State.WAIT_OPPONENT:
            if not stable:
                return
            if stable == self.ctx.current_fen:
                return

            # Opponent moved: infer move
            uci = infer_opponent_move_from_fens(self.ctx.board, self.ctx.current_fen, stable)
            if not uci:
                log.warning("WAIT_OPPONENT: stable change detected but couldn't infer legal move. Continuing.")
                # don’t update state; keep looking
                self.ctx.current_fen = stable  # optional: comment this out if you want stricter behavior
                return

            log.info(f"Opponent move inferred: {uci}")
            self.ctx.board.push_uci(uci)
            self.ctx.current_fen = self.ctx.board.fen()
            self.stability.reset()
            self.state = State.THINK
            return

        if self.state == State.THINK:
            # Ask Stockfish
            our = self.engine.best_move(self.ctx.board)
            if not our:
                log.error("THINK: Stockfish returned no move. Stopping.")
                self.state = State.STOP
                return
            self._our_uci = our
            plan = make_plan(self.ctx.board, our)
            log.info(f"Our move: {our} | plan steps: {len(plan)}")
            self._expected_fen_after_our_move = self._expected_fen_after_move(self.ctx.board, our)
            self._plan = plan
            self.state = State.ACT
            return

        if self.state == State.ACT:
            assert self._our_uci is not None
            assert self._expected_fen_after_our_move is not None
            # Execute plan on robot
            ok = self.robot.execute_plan(self._plan)
            if not ok:
                log.error("ACT: robot plan execution failed. Going to RECOVER.")
                self.state = State.RECOVER
                return
            # Update internal board AFTER physical act
            self.ctx.board.push_uci(self._our_uci)
            self.ctx.current_fen = self.ctx.board.fen()
            self.stability.reset()
            self.state = State.VERIFY
            return

        if self.state == State.VERIFY:
            # Wait for stable observation matching expected
            if not stable:
                return
            expected = self._expected_fen_after_our_move
            if stable.split(" ")[0] == expected.split(" ")[0]:
                # Compare piece placement only for v1 (more tolerant)
                log.info("VERIFY: success (piece placement matches).")
                self.state = State.WAIT_OPPONENT
                self.stability.reset()
                return
            log.warning("VERIFY: mismatch. Going to RECOVER.")
            self.state = State.RECOVER
            return

        if self.state == State.RECOVER:
            # v1 recovery: stop safely (you can add retries later)
            log.error("RECOVER: stopping for safety. Manual intervention required.")
            self.robot.home()
            self.state = State.STOP
            return

    @staticmethod
    def _expected_fen_after_move(board: chess.Board, uci: str) -> str:
        tmp = board.copy(stack=False)
        tmp.push_uci(uci)
        return tmp.fen()
