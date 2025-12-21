<h1 align="center">
  <br>
  <a href="https://blueprint.hackclub.com/prototype"><img src="https://hc-cdn.hel1.your-objectstorage.com/s/v3/d1252b6d5ee8f6e7_group_3.png" width="200"></a>
  <br>
  Robby Fischer
  <br>
</h1>

<h4 align="center">
  
Robby Fischer is a chess-playing robotic arm system that uses computer vision and imitation Learning AI to play chess autonomously against human opponents!

</h4>

<div align="center">

![Hack Club](https://img.shields.io/badge/Hack_Club-33d6a6.svg?style=for-the-badge&logo=hackclub&logoColor=white)
![AMD](https://img.shields.io/badge/AMD-ed1c24.svg?style=for-the-badge&logo=amd&logoColor=white)

</div>

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Features">Features</a> •
  <a href="#Algorithim">Algorithim</a> •
  <a href="#credits">Credits</a> •
</p>

<img src="notdone" alt="Robby_Fischer_Build" width="800"/>

## Overview

ChessArm is an intelligent chess system that:
- **Captures** the board state using multiple cameras that track the position of the arm and chess board
- **Detects** opponent moves via vision-based piece tracking
- **Analyzes** the board using Stockfish chess engine
- **Executes** chess moves using the [Hugging Face LeRobot SO‑ARM101 arm](https://github.com/huggingface/lerobot)
  
**Game Flow**: Camera Input → Board Detection → Stockfish AI → Arm Execution → Repeat

## Features

- **Multi-Camera System**: 3  cameras (wrist, top, side) provide robust board state detection
- **Perspective Calibration**: Automatic 4-point calibration for accurate board warping
- **Piece Detection**: Occupancy detection based on brightness threshold (140 units)
- **AI Integration**: Stockfish engine for optimal move suggestions (2-second time limit)
- **Turn-Based Logic**: Automatic alternation between robot (Red) and opponent (White)

## Algorithm

insert img when chris done

## Credits

This project uses the following open-source projects

- **Onshape** was used to CAD the chess pieces and board
- **AMD** and **Hack Club** provided the following:
  - A
  - B
  - C
- Insert more later

 
-  

