from __future__ import annotations
import serial
import time

class SO101Serial:
    """
    Two serial devices:
      - leader: often used for teaching / recording (if applicable)
      - follower: executes commands

    IMPORTANT: You must fill in the real command protocol for your SO-101.
    This is a clean, safe stub that you can adapt.
    """

    def __init__(self, leader_port: str, follower_port: str, baudrate: int = 115200, timeout_s: float = 0.2) -> None:
        self.leader = serial.Serial(leader_port, baudrate=baudrate, timeout=timeout_s)
        self.follower = serial.Serial(follower_port, baudrate=baudrate, timeout=timeout_s)

        # small settle time
        time.sleep(0.2)

    def close(self) -> None:
        try:
            self.leader.close()
        except Exception:
            pass
        try:
            self.follower.close()
        except Exception:
            pass

    # ---------- Low-level send helpers ----------

    def send_follower(self, msg: str) -> None:
        """
        Send a single line command to follower.
        Replace with correct framing if your device needs it.
        """
        if not msg.endswith("\n"):
            msg += "\n"
        self.follower.write(msg.encode("utf-8"))

    def read_follower_line(self) -> str:
        return self.follower.readline().decode("utf-8", errors="ignore").strip()

    # ---------- High-level commands (you will adapt these) ----------

    def move_to_pose_mm(self, x_mm: float, y_mm: float, z_mm: float) -> None:
        """
        TODO: Replace with your arm's actual serial command.
        Example placeholder:
          GOTO X{...} Y{...} Z{...}
        """
        self.send_follower(f"GOTO X{x_mm:.1f} Y{y_mm:.1f} Z{z_mm:.1f}")

    def gripper_open(self) -> None:
        self.send_follower("GRIP OPEN")

    def gripper_close(self) -> None:
        self.send_follower("GRIP CLOSE")

    def home(self) -> None:
        self.send_follower("HOME")
