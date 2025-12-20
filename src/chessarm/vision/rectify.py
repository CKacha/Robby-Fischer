from __future__ import annotations
import numpy as np

class BoardRectifier:
    """
    v1: passthrough.
    Later: detect ArUco corners and warp to a canonical top-down board image.
    """
    def __init__(self, board_cfg: dict) -> None:
        self.board_cfg = board_cfg

    def rectify(self, frame_bgr: np.ndarray) -> np.ndarray:
        # TODO: implement ArUco-based homography for robustness
        return frame_bgr
