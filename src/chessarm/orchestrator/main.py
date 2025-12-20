from __future__ import annotations
import logging

from chessarm.orchestrator.logger import setup_logging
from chessarm.utils.io import read_yaml
from chessarm.vision.camera import UsbCamera
from chessarm.vision.rectify import BoardRectifier
from chessarm.vision.piece_model import PieceModelStub
from chessarm.vision.board_state import BoardStateEstimator
from chessarm.vision.stability import FenStability

from chessarm.chess.stockfish_engine import StockfishEngine
from chessarm.robot.so101_client import SO101Serial
from chessarm.robot.kinematics import BoardKinematics
from chessarm.robot.macros import RobotMacros
from chessarm.orchestrator.state_machine import ChessArmStateMachine

log = logging.getLogger(__name__)

def main() -> None:
    setup_logging(logging.INFO)

    cam_cfg = read_yaml("configs/camera.yaml")
    board_cfg = read_yaml("configs/board.yaml")
    robot_cfg = read_yaml("configs/robot.yaml")
    sf_cfg = read_yaml("configs/stockfish.yaml")

    camera = UsbCamera(
        device_id=int(cam_cfg.get("device_id", 0)),
        width=int(cam_cfg.get("width", 1280)),
        height=int(cam_cfg.get("height", 720)),
        fps=int(cam_cfg.get("fps", 30)),
        show_window=bool(cam_cfg.get("show_window", False)),
    )
    rectifier = BoardRectifier(board_cfg)
    model = PieceModelStub()  # replace with HF model wrapper later
    estimator = BoardStateEstimator(model=model, rectifier=rectifier, board_cfg=board_cfg)

    stability = FenStability(maxlen=64)

    engine = StockfishEngine(
        path=str(sf_cfg.get("engine_path", "stockfish")),
        threads=int(sf_cfg.get("threads", 2)),
        hash_mb=int(sf_cfg.get("hash_mb", 128)),
        move_time_ms=int(sf_cfg.get("move_time_ms", 250)),
    )

    serial = SO101Serial(
        leader_port=str(robot_cfg["leader_port"]),
        follower_port=str(robot_cfg["follower_port"]),
        baudrate=int(robot_cfg.get("baudrate", 115200)),
        timeout_s=float(robot_cfg.get("timeout_s", 0.2)),
    )
    kin = BoardKinematics(robot_cfg)
    robot = RobotMacros(serial=serial, kin=kin, robot_cfg=robot_cfg)

    sm = ChessArmStateMachine(stability=stability, engine=engine, robot=robot, stable_k=int(board_cfg.get("stable_k", 6)))

    log.info("CHESSARM starting. Press Ctrl+C to stop.")
    try:
        with camera:
            while True:
                frame = camera.read()
                fen = estimator.estimate_fen(frame)
                if fen:
                    log.debug(f"Observed FEN: {fen}")
                sm.step(fen or "")
    except KeyboardInterrupt:
        log.info("Stopping...")
    finally:
        try:
            robot.home()
        except Exception:
            pass
        try:
            serial.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
