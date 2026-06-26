<h1 align="center">
  <br>
  <a href="https://blueprint.hackclub.com/prototype">
    <img src="https://hc-cdn.hel1.your-objectstorage.com/s/v3/d1252b6d5ee8f6e7_group_3.png" width="200">
  </a>
  <br>
  Robby Fischer
  <br>
</h1>

<h4 align="center">
  A chess-playing robotic arm that sees the board through cameras, thinks with the Stockfish engine, and physically moves pieces using the LeRobot SO-ARM101 arm.
</h4>

<div align="center">

![Hack Club](https://img.shields.io/badge/Hack_Club-33d6a6.svg?style=for-the-badge&logo=hackclub&logoColor=white)
![AMD](https://img.shields.io/badge/AMD-ed1c24.svg?style=for-the-badge&logo=amd&logoColor=white)

</div>

<p align="center">
  <a href="#about-us">About Us</a> •
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#hardware">Hardware</a> •
  <a href="#wiring-diagram">Wiring Diagram</a> •
  <a href="#credits">Credits</a>
</p>

---

## About Us

### Our Team!

**Team Name:** TPC

**Team Number:** 18

**GitHub Usernames:**
- @TaniWanKenobi
- @techn1-cal
- @Ckacha

### Project Image

<img src="images/chess.png" alt="Robby_Fischer_Board_Tracker" width="800"/>

---

## Project Media

**Training the arm:**

<video src="https://github.com/user-attachments/assets/0e8f6b65-fb49-4176-8722-4db38d22dfb7" controls muted width="800"></video>

**Demo runs:**

<video src="https://github.com/user-attachments/assets/5e9bfd6d-fc00-46bb-ad35-3a1e8c407205" controls muted width="800"></video>

<video src="https://github.com/user-attachments/assets/f8ae0c36-9d8a-4b76-ac57-83ef428b359a" controls muted width="800"></video>

---

## Hardware

**Bill of Materials:**

| Component | Purpose |
|---|---|
| Hugging Face LeRobot SO-ARM101 | Robotic arm that physically moves chess pieces |
| AMD PC | Runs all vision, chess engine, and arm control software |
| USB Cameras x3 | Wrist-mounted, top-down, and side-angle board views |
| Chess Board (3D printed) | Custom board sized and colored for vision detection |
| Chess Pieces (3D printed) | Custom pieces with consistent brightness for detection |

---

## Overview

Robby Fischer is a fully autonomous chess-playing robot. A human sits down, makes their move on the physical board, and the robot handles everything else: it sees what happened, calculates the best response, and physically moves its own piece.

**How it works end-to-end:**

1. **Board Detection:** Three USB cameras capture the board simultaneously. The top-down camera is the primary source; it's warped via a 4-point perspective transform (homography) to produce a clean bird's-eye view of all 64 squares.

2. **Move Detection:** After the human moves, the system compares the current board image against the previous state. Each square is analyzed using a voting system across three methods: brightness threshold, edge density, and texture variance. If two of three methods agree a square changed, it's flagged, giving the system the "from" and "to" squares of the human's move.

3. **Chess Engine:** The detected move is validated against a tracked `chess.Board` state using the `python-chess` library. If the move is legal, it's applied and Stockfish calculates the best response at depth 15, or with a 1-second time limit.

4. **Arm Execution:** The LeRobot SO-ARM101 arm executes the engine's chosen move on the physical board, completing the loop.

**Game Flow:**

```
Camera Input → Perspective Warp → Square Occupancy Detection → Move Validation → Stockfish → Arm Execution → Repeat
```

Human plays White and moves first. The robot plays Black.

---

## Features

- **Triple-Camera System:** Wrist, top-down, and side-angle cameras run in parallel threads for continuous board monitoring.
- **Perspective Calibration:** A saved 4-point calibration (`board_calib_4pt.json`) maps the physical board to a corrected 800x800 pixel top-down view on every run.
- **Robust Piece Detection:** Occupancy uses a 3-method voting system (brightness, edge density, variance) so a single noisy reading doesn't cause false moves.
- **Stockfish Integration:** Full chess engine analysis with move suggestions, position evaluation, and legal move validation through `python-chess`.
- **Live Board Visualization:** OpenCV windows display the warped board with per-square occupancy indicators and an arrow overlay showing the suggested move.
- **Manual Override:** Keyboard controls let the operator confirm moves, enter moves manually, request hints, or start a new game at any time.

---

## Wiring Diagram

*(coming soon)*

---

## Credits

This project was built with the following open-source tools and sponsors:

- **[Hack Club](https://hackclub.com/) & [AMD](https://www.amd.com/):** provided the hardware and resources that made this project possible
- **[LeRobot (Hugging Face)](https://github.com/huggingface/lerobot):** SO-ARM101 robotic arm platform and control software
- **[Stockfish](https://stockfishchess.org/):** open-source chess engine used for move analysis and decision-making
- **[OpenCV](https://opencv.org/):** computer vision library used for camera capture, perspective transforms, and board visualization
- **[python-chess](https://python-chess.readthedocs.io/):** chess move validation and board state tracking
- **[Onshape](https://www.onshape.com/):** used to CAD and design the custom chess board and pieces
