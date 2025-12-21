<h1 align="center">
  <br>
  <a href="https://notaroomba.dev"><img src="https://hc-cdn.hel1.your-objectstorage.com/s/v3/d1252b6d5ee8f6e7_group_3.png" width="200"></a>
  <br>
  Robby Fischer
  <br>
</h1>


Robby Fischer is a chess-playing robotic arm system that uses computer vision and imitation Learning AI to play chess autonomously against human opponents!

## Overview

ChessArm is an intelligent chess system that:
- **Captures** the board state using multiple cameras that track the 
- **Detects** opponent moves via vision-based piece tracking
- **Analyzes** the board using Stockfish chess engine
- **Executes** moves with a Le Robot arm
- **Verifies** move completion through visual feedback

**Game Flow**: Camera Input → Board Detection → Stockfish AI → Arm Execution → Repeat

## Features

- **Multi-Camera System**: 3  cameras (wrist, top, side) provide robust board state detection
- **Perspective Calibration**: Automatic 4-point calibration for accurate board warping
- **Piece Detection**: Occupancy detection based on brightness threshold (140 units)
- **AI Integration**: Stockfish engine for optimal move suggestions (2-second time limit)
- **Turn-Based Logic**: Automatic alternation between robot (Red) and opponent (White)


## Setup
It uses a {} set up overhead to check the chessboard, and a [] to look at the LeRobot Arm for (). 

Chess-playing robot arm system:
Camera -> Board State (FEN) -> Stockfish -> Plan -> Robot Macros -> Verify -> Repeat

