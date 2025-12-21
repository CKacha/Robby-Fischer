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
  Robby Fischer is a chess-playing robotic arm system that uses computer vision and imitation learning AI to play chess autonomously against human opponents.
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

### Our Team!

**Team Name:** The Fischers  
**Team Number:** 18
**GitHub Usernames:**  
- @TaniWanKenobi
- @techn1-cal  
- @ChanminK
  
### Project Image

<img src="MISSING PROJECT IMAGE URL" alt="Robby_Fischer_Build" width="800"/>

---

## Project Media

<img src="MISSING PROJECT IMAGE URL" alt="Robby_Fischer_Build" width="800"/>

(insert video here )

---

## Diagrams

### Algorithm Diagram

<img src="MISSING PROJECT IMAGE URL" alt="Robby_Fischer_Build" width="800"/>



## BOM

- Hugging Face LeRobot SO-ARM101
- AMD AI PC (Ryzen AI)
- USB Cameras (x3)
- Chess Board
- Chess Pieces (3D printed)
- Power Supply
- Misc. wiring and mounts

---


## Overview

ChessArm is an intelligent robotic chess system that:

- **Captures** the board state using multiple calibrated cameras
- **Detects** opponent moves via vision-based piece tracking
- **Analyzes** board positions using the Stockfish chess engine
- **Executes** moves using the Hugging Face LeRobot SO-ARM101 robotic arm

**Game Flow:**  
Camera Input → Board Detection → Stockfish AI → Arm Execution → Repeat

---

## Features

- **Multi-Camera System**: Three cameras (wrist, top-down, side)
- **Perspective Calibration**: Automatic 4-point homography correction
- **Piece Detection**: Brightness-based occupancy detection (threshold = 140)
- **AI Integration**: Stockfish engine with 2-second move time limit
- **Turn Logic**: Alternates between human (White) and robot (Red)

# Credits

This project uses the following open-source projects

- **Onshape** was used to CAD the chess pieces and board
- **AMD** and **Hack Club** provided the hardware and software resources we used!
- **OpenCV** was used for image processing and computer vision tasks
- **Stockfish** was used for chess engine analysis


