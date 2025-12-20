from __future__ import annotations
import subprocess
import chess
import chess.engine

class StockfishEngine:
    def __init__(self, path: str = "stockfish", threads: int = 2, hash_mb: int = 128, move_time_ms: int = 250) -> None:
        self.path = path
        self.threads = threads
        self.hash_mb = hash_mb
        self.move_time_ms = move_time_ms
        self.engine = chess.engine.SimpleEngine.popen_uci(self._resolve_path(path))
        self.engine.configure({"Threads": threads, "Hash": hash_mb})

    def _resolve_path(self, path: str) -> str:
        # allow "stockfish" from PATH
        if path == "stockfish":
            return subprocess.check_output(["which", "stockfish"]).decode().strip()
        return path

    def best_move(self, board: chess.Board) -> str | None:
        try:
            limit = chess.engine.Limit(time=self.move_time_ms / 1000.0)
            result = self.engine.play(board, limit)
            return result.move.uci() if result.move else None
        except Exception:
            return None

    def close(self) -> None:
        try:
            self.engine.quit()
        except Exception:
            pass
