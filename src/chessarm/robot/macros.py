from __future__ import annotations
import logging
from chessarm.robot.so101_client import SO101Serial
from chessarm.robot.kinematics import BoardKinematics
from chessarm.planner.plan_types import PlanStep

log = logging.getLogger(__name__)

class RobotMacros:
    def __init__(self, serial: SO101Serial, kin: BoardKinematics, robot_cfg: dict) -> None:
        self.serial = serial
        self.kin = kin
        self.safe_z = float(robot_cfg.get("safe_z_mm", 80))
        self.grasp_z = float(robot_cfg.get("grasp_z_mm", 10))
        self.tray_pose = robot_cfg.get("tray_pose", {"x_mm": 220, "y_mm": 0, "z_mm": 80})

    def home(self) -> None:
        log.info("Robot: home()")
        self.serial.home()

    def pick(self, square: str) -> bool:
        log.info(f"Robot: pick({square})")
        p_safe = self.kin.square_center_pose(square, z_mm=self.safe_z)
        p_grasp = self.kin.square_center_pose(square, z_mm=self.grasp_z)

        self.serial.move_to_pose_mm(p_safe.x_mm, p_safe.y_mm, p_safe.z_mm)
        self.serial.move_to_pose_mm(p_grasp.x_mm, p_grasp.y_mm, p_grasp.z_mm)
        self.serial.gripper_close()
        self.serial.move_to_pose_mm(p_safe.x_mm, p_safe.y_mm, p_safe.z_mm)
        return True

    def place(self, square: str) -> bool:
        log.info(f"Robot: place({square})")
        p_safe = self.kin.square_center_pose(square, z_mm=self.safe_z)
        p_grasp = self.kin.square_center_pose(square, z_mm=self.grasp_z)

        self.serial.move_to_pose_mm(p_safe.x_mm, p_safe.y_mm, p_safe.z_mm)
        self.serial.move_to_pose_mm(p_grasp.x_mm, p_grasp.y_mm, p_grasp.z_mm)
        self.serial.gripper_open()
        self.serial.move_to_pose_mm(p_safe.x_mm, p_safe.y_mm, p_safe.z_mm)
        return True

    def remove(self, square: str) -> bool:
        log.info(f"Robot: remove({square}) -> tray")
        ok = self.pick(square)
        if not ok:
            return False
        self.serial.move_to_pose_mm(float(self.tray_pose["x_mm"]), float(self.tray_pose["y_mm"]), float(self.tray_pose["z_mm"]))
        self.serial.gripper_open()
        return True

    def execute_plan(self, plan: list[PlanStep]) -> bool:
        for step in plan:
            if step.type == "HOME":
                self.home()
            elif step.type == "REMOVE":
                assert step.src is not None
                if not self.remove(step.src):
                    return False
            elif step.type == "MOVE":
                assert step.src is not None and step.dst is not None
                if not self.pick(step.src):
                    return False
                if not self.place(step.dst):
                    return False
            else:
                log.error(f"Unknown step: {step}")
                return False
        return True
