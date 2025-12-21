<h1 align="center">
  <a href="https://blueprint.hackclub.com/prototype">
    <img src="https://hc-cdn.hel1.your-objectstorage.com/s/v3/d1252b6d5ee8f6e7_group_3.png" width="200" />
  </a>
  <br />
  Robby Fischer
</h1>

<h4 align="center">
  A chess-playing robotic arm system that uses computer vision and imitation-learning-based AI to play chess autonomously against human opponents.
</h4>

<div align="center">

![Hack Club](https://img.shields.io/badge/Hack_Club-33d6a6.svg?style=for-the-badge&logo=hackclub&logoColor=white)
![AMD](https://img.shields.io/badge/AMD-ed1c24.svg?style=for-the-badge&logo=amd&logoColor=white)

</div>

<p align="center">
  <a href="#about-us">About Us</a> •
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#algorithm">Algorithm</a> •
  <a href="#hardware">Hardware</a> •
  <a href="#wiring-diagram">Wiring Diagram</a> •
  <a href="#team">Team</a> •
  <a href="#credits">Credits</a>
</p>

---

## About Us

### Team Information

**Team Name:** The Fischers  
**Team Number:** 18  

**GitHub Usernames:**
- @TaniWanKenobi  
- @techn1-cal  
- @ChanminK  

---

## Project Media

### Build Image

<img src="MISSING_PROJECT_IMAGE_URL" alt="Robby Fischer Build" width="800" />

### Demo Video

> Replace with a linked or embedded demo video once available.

---

## Diagrams

### Algorithm Diagram

<img src="MISSING_ALGORITHM_DIAGRAM_URL" alt="Algorithm Diagram" width="800" />

### Wiring Diagram

<img src="MISSING_WIRING_DIAGRAM_URL" alt="Wiring Diagram" width="800" />

---

## Hardware (BOM)

- Hugging Face **LeRobot SO-ARM101**
- AMD **Ryzen AI PC**
- USB Cameras (×3)
- Chess Board
- 3D-Printed Chess Pieces
- Power Supply
- Miscellaneous wiring and mounting hardware

---

## Overview

**Robby Fischer** is an autonomous robotic chess system that:

- Captures the board state using multiple calibrated cameras
- Detects opponent moves via vision-based piece tracking
- Analyzes positions using the Stockfish chess engine
- Executes physical moves using a robotic arm

**Game Flow:**

Camera Input → Board Detection → Stockfish AI → Arm Execution → Repeat-


---

## Features

- **Multi-Camera System**  
  Wrist, top-down, and side-view cameras

- **Perspective Calibration**  
  Automatic 4-point homography correction

- **Piece Detection**  
  Brightness-based square occupancy detection (threshold = 140)

- **AI Integration**  
  Stockfish chess engine with a 2-second move time limit

- **Turn Logic**  
  Human plays White, robot plays Red

---

## Algorithm

> High-level description of perception → decision → action loop.
> Detailed breakdown to be added after final tuning.

---

## Wiring Diagram

> See diagram above. Detailed pinout and power routing documentation pending.

---

## Credits

This project makes use of the following tools and resources:

- **Onshape** — CAD design for chess pieces and board
- **Stockfish** — Open-source chess engine
- **Hugging Face LeRobot** — Robotic arm platform
- **AMD** and **Hack Club** — Hardware and program support

Additional credits to be added as development continues.
