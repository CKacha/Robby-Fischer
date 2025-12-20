from __future__ import annotations
from chessarm.utils.math import PoseMM

_FILES = "abcdefgh"

class BoardKinematics:
    """
    v1: simple planar mapping from square -> (x,y) using config origin + square_size_mm.
    Later: replace with calibration transform.
    """
    def __init__(self, robot_cfg: dict) -> None:
        self.origin_x = float(robot_cfg["board_origin"]["x_mm"])
        self.origin_y = float(robot_cfg["board_origin"]["y_mm"])
        self.origin_z = float(robot_cfg["board_origin"]["z_mm"])
        self.square = float(robot_cfg.get("square_size_mm", 25))

    def square_center_pose(self, square: str, z_mm: float) -> PoseMM:
        file = square[0]
        rank = int(square[1])
        fx = _FILES.index(file)  # a=0 ... h=7
        ry = rank - 1            # 1..8 -> 0..7

        x = self.origin_x + fx * self.square
        y = self.origin_y + ry * self.square
        z = self.origin_z + z_mm
        return PoseMM(x_mm=x, y_mm=y, z_mm=z)
