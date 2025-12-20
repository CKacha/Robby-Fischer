import cv2
import numpy as np
import json
import os
import chess
import chess.engine
import threading
import time
from datetime import datetime

# =========================
# CONFIG
# =========================

CAMERA_INDEXES = [4, 6, 3]  # wrist(4), top(6), side(3)
CALIB_FILE = "board_calib_4pt.json"
BOARD_SIZE = 800
OCCUPANCY_THRESHOLD = 140
CENTER_MARGIN = 0.25
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30  # 30 FPS for each camera

clicked_points = []
frame_lock = threading.Lock()
frames = [None, None, None]

# =========================
# CALIBRATION
# =========================

def calibrate_with_frame_source(frame_source, source_type="capture"):
    # Calibration code as before...
    pass

def load_calibration():
    with open(CALIB_FILE, "r") as f:
        return json.load(f)

# =========================
# VISION
# =========================

def warp_board(frame, pts):
    # Same as before...
    pass

def center_crop(img, margin):
    # Same as before...
    pass

def is_occupied(square):
    if square is None or square.size == 0:
        return False
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    return gray.mean() < OCCUPANCY_THRESHOLD

# =========================
# STOCKFISH INTERACTION
# =========================

def get_stockfish_move(current_board):
    with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
        result = engine.play(current_board, chess.engine.Limit(time=2.0))
        return result.move

# =========================
# THREADING FOR CAMERA CAPTURE
# =========================

stop_capture = False

def capture_frames(camera_idx, array_idx, frame_array):
    # Same as before...
    pass

# =========================
# GAME LOGIC
# =========================

def detect_moved_piece(prev_board, curr_board):
    """
    Compare previous and current board states to detect which piece moved.
    Returns the move in UCI format (e.g., 'e2e4').
    """
    diff = prev_board.board_fen() != curr_board.board_fen()
    if diff:
        # Detect the move by comparing pieces before and after
        return curr_board.uci()
    return None

def capture_board_image(board_img, turn):
    """
    Captures and saves the board image with a timestamp filename.
    `turn` is used to differentiate robot's and opponent's turns.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"board_{turn}_{timestamp}.jpg"
    cv2.imwrite(filename, board_img)
    print(f"Board image saved as {filename}")

def start_game():
    """
    This function starts a chess game.
    The robot (Black/Red) plays second, and the opponent (White) plays first.
    """
    print("Starting the game...")
    
    # Create chess board
    current_board = chess.Board()
    print(current_board)

    # Initialize time for both players (1 minute for each)
    start_time = time.time()

    # Capture the initial board image
    top_view = frames[1]
    warped_top = warp_board(top_view, load_calibration()["points"])
    capture_board_image(warped_top, "start")

    # Main game loop
    while not current_board.is_game_over():
        # Check whose turn it is
        is_robot_turn = current_board.turn == chess.BLACK  # Robot plays Black
        
        if is_robot_turn:
            print("Robot's Turn (Black/Red)")
            
            # Capture image of the board to detect moved pieces
            top_view = frames[1]
            warped_top = warp_board(top_view, load_calibration()["points"])
            capture_board_image(warped_top, "robot_move")
            
            moved_piece = detect_moved_piece(prev_board, current_board)
            
            if moved_piece:
                print(f"Robot move detected: {moved_piece}")
                stockfish_move = get_stockfish_move(current_board)  # Get best move from Stockfish
                print(f"Stockfish suggests: {stockfish_move}")
                
                # Execute the robotic arm move (not implemented yet)
                execute_arm_move(stockfish_move)
            
            prev_board = current_board  # Update the previous board state for the next move
            print("Waiting for opponent's move...")
        
        else:
            print("Opponent's Turn (White)")
            
            # Opponent's move is handled the same way (you can use manual input here for now)
            # For now, let's assume the opponent moves manually
            pass
        
        # Implement turn timer (1 minute per player)
        time_left = 60 - (time.time() - start_time)
        if time_left <= 0:
            print(f"Time's up! {'Robot' if is_robot_turn else 'Opponent'} ran out of time.")
            break

        # Display the updated board and remaining time
        print(f"Time left: {time_left:.2f} seconds")
        
        time.sleep(1)  # Pause for 1 second before the next move

    print("Game Over!")
    
# =========================
# MAIN
# =========================

def main():
    # Game start options
    print("Welcome to the Chess Arm Game!")
    print("1. Start Game")
    print("Q. Quit")
    
    choice = input("Enter choice: ")
    
    if choice == '1':
        start_game()
    else:
        print("Exiting game.")

if __name__ == "__main__":
    main()
