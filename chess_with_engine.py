#!/usr/bin/env python3
"""
ChessArm - Chess detection with Stockfish integration
Assumes games start from default position, human plays first as White
"""

import cv2
import numpy as np
import json
import os
import chess
import chess.engine
import threading
import time

# =========================
# CONFIG
# =========================

CAMERA_INDEXES = [4, 6, 3]  # wrist, top, side
CALIB_FILE = "board_calib_4pt.json"
BOARD_SIZE = 800
OCCUPANCY_THRESHOLD = 120  # Adjusted for non-standard pieces
CENTER_MARGIN = 0.25
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# =========================
# GLOBALS
# =========================

clicked_points = []
frame_lock = threading.Lock()
frames = [None, None, None]
stop_capture = False

def detect_cameras():
    """Detect available cameras"""
    available_cameras = []
    print("Detecting available cameras...")
    
    for i in range(11):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available_cameras.append(i)
                print(f"Camera {i}: Working (resolution: {frame.shape[1]}x{frame.shape[0]})")
            cap.release()
    
    print(f"Available cameras: {available_cameras}")
    return available_cameras

def load_calibration():
    """Load calibration from file"""
    with open(CALIB_FILE, "r") as f:
        return json.load(f)

def warp_board(frame, pts):
    """Apply perspective transform to get top-down board view"""
    src = np.array(pts, dtype=np.float32)
    dst = np.array([
        [0, 0],
        [BOARD_SIZE, 0],
        [BOARD_SIZE, BOARD_SIZE],
        [0, BOARD_SIZE]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(frame, M, (BOARD_SIZE, BOARD_SIZE))
    return warped

def rotate_board(warped_board):
    """Rotate board for correct orientation"""
    return cv2.rotate(warped_board, cv2.ROTATE_90_COUNTERCLOCKWISE)

def center_crop(img, margin):
    """Crop center of image with margin"""
    h, w = img.shape[:2]
    dx = int(w * margin)
    dy = int(h * margin)
    if h - 2 * dy <= 0 or w - 2 * dx <= 0:
        return None
    return img[dy:h-dy, dx:w-dx]

def is_occupied(square):
    """Detect if square is occupied using multiple methods"""
    if square is None or square.size == 0:
        return False
    
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    
    # Method 1: Brightness threshold
    brightness_occupied = gray.mean() < OCCUPANCY_THRESHOLD
    
    # Method 2: Edge detection
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    edge_occupied = edge_density > 0.02
    
    # Method 3: Variance (texture)
    variance_occupied = np.var(gray) > 100
    
    # Vote: if 2+ methods agree, consider occupied
    vote_count = sum([brightness_occupied, edge_occupied, variance_occupied])
    return vote_count >= 2

def detect_board_state(warped_board):
    """Convert board image to occupancy matrix"""
    sq = BOARD_SIZE // 8
    occupancy_matrix = np.zeros((8, 8), dtype=bool)
    
    for r in range(8):
        for c in range(8):
            x1 = c * sq
            y1 = r * sq
            x2 = x1 + sq
            y2 = y1 + sq
            
            square = warped_board[y1:y2, x1:x2]
            square_c = center_crop(square, CENTER_MARGIN)
            
            occupancy_matrix[r, c] = is_occupied(square_c)
    
    return occupancy_matrix

def get_expected_starting_occupancy():
    """Return occupancy matrix for chess starting position"""
    occupancy = np.zeros((8, 8), dtype=bool)
    
    # White pieces (bottom)
    occupancy[7, :] = True  # Rank 1
    occupancy[6, :] = True  # Rank 2 (pawns)
    # Black pieces (top)
    occupancy[0, :] = True  # Rank 8
    occupancy[1, :] = True  # Rank 7 (pawns)
    
    return occupancy

def get_board_occupancy_from_chess_board(board):
    """Generate expected occupancy from chess.Board state"""
    occupancy = np.zeros((8, 8), dtype=bool)
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            file_idx = chess.square_file(square)
            rank_idx = 7 - chess.square_rank(square)  # Flip for display
            occupancy[rank_idx, file_idx] = True
    
    return occupancy

def detect_move_from_occupancy_change(prev_occupancy, curr_occupancy):
    """Detect move by comparing occupancy matrices"""
    differences = prev_occupancy != curr_occupancy
    
    changed_squares = []
    for r in range(8):
        for c in range(8):
            if differences[r, c]:
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                square_name = f"{file_char}{rank_char}"
                was_occupied = prev_occupancy[r, c]
                is_occupied = curr_occupancy[r, c]
                changed_squares.append((square_name, was_occupied, is_occupied))
    
    # Simple move: one square emptied, one filled
    if len(changed_squares) == 2:
        from_square = None
        to_square = None
        
        for square, was_occupied, is_occupied in changed_squares:
            if was_occupied and not is_occupied:
                from_square = square
            elif not was_occupied and is_occupied:
                to_square = square
        
        if from_square and to_square:
            return f"{from_square}{to_square}"
    
    return None

def get_stockfish_move(board):
    """Get best move from Stockfish"""
    try:
        with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
            result = engine.play(board, chess.engine.Limit(time=1.0))
            return result.move
    except Exception as e:
        print(f"Stockfish error: {e}")
        return None

def analyze_position(board, depth=15):
    """Get detailed analysis from Stockfish"""
    try:
        with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            return info
    except Exception as e:
        print(f"Analysis error: {e}")
        return None

def capture_frames(camera_idx, array_idx, frame_array):
    """Camera capture thread"""
    global stop_capture
    cap = cv2.VideoCapture(camera_idx)
    
    if not cap.isOpened():
        print(f"Failed to open camera {camera_idx}")
        return
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    print(f"Successfully opened camera {camera_idx}")

    while not stop_capture:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                frame_array[array_idx] = frame
        else:
            time.sleep(0.1)

    cap.release()

def chess_to_coords(square_name):
    """Convert chess notation to grid coordinates"""
    file_idx = ord(square_name[0]) - ord('a')
    rank_idx = 8 - int(square_name[1])
    return file_idx, rank_idx

def main():
    global stop_capture
    
    # Check cameras
    available_cameras = detect_cameras()
    print(f"Using cameras: {CAMERA_INDEXES}")
    
    # Check calibration
    if not os.path.exists(CALIB_FILE):
        print(f"No calibration file found: {CALIB_FILE}")
        print("Please run safe_calibrate.py first!")
        return
    
    calib = load_calibration()
    
    # Start camera threads
    frames = [None] * len(CAMERA_INDEXES)
    threads = []
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        thread = threading.Thread(target=capture_frames, args=(camera_idx, i, frames))
        threads.append(thread)
        thread.start()

    time.sleep(2)  # Wait for cameras

    # Setup windows
    cv2.namedWindow("board", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("board", 900, 900)
    cv2.namedWindow("analysis", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("analysis", 400, 600)

    print("\n🎯 ChessArm Chess Engine Integration")
    print("=" * 50)
    print("CONTROLS:")
    print("  S = Get Stockfish suggestion")
    print("  M = Manual move entry")
    print("  D = Toggle move detection")
    print("  A = Get human move suggestion")
    print("  C = Confirm move executed")
    print("  N = New game")
    print("  Q = Quit")
    print("")
    print("WORKFLOW:")
    print("1. Press 'S' to get computer suggestion")
    print("2. Press 'A' to get human move suggestion") 
    print("3. Make move on physical board")
    print("4. Press 'C' to confirm OR 'D' for auto-detection")
    print("5. Robot will respond automatically")
    print("")

    # Initialize game
    board = chess.Board()
    last_suggestion = None
    last_analysis = None
    move_counter = 0
    previous_occupancy = get_expected_starting_occupancy()
    move_detection_active = False
    stable_frame_count = 0

    print("🎮 Game started! Human (White) moves first")
    print("📋 Starting position loaded")

    while True:
        # Get frames
        with frame_lock:
            if any(frame is None for frame in frames):
                continue
            top_view = frames[1].copy()
            side_view = frames[2].copy()
            wrist_view = frames[0].copy()

        # Process board
        warped = warp_board(top_view, calib["points"])
        rotated = rotate_board(warped)
        occupancy = detect_board_state(rotated)

        # Draw board visualization
        sq = BOARD_SIZE // 8
        for r in range(1, 8):
            cv2.line(rotated, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 2)
            cv2.line(rotated, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 2)

        # Draw squares with occupancy
        for r in range(8):
            for c in range(8):
                x1, y1 = c * sq, r * sq
                x2, y2 = x1 + sq, y1 + sq
                
                # Color by occupancy
                occupied = occupancy[r, c]
                color = (0, 0, 255) if occupied else (0, 255, 0)
                cv2.rectangle(rotated, (x1+2, y1+2), (x2-2, y2-2), color, 3)
                
                # Square label
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                label = f"{file_char}{rank_char}"
                cv2.putText(rotated, label, (x1 + 5, y1 + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Occupancy indicator
                status = "●" if occupied else "○"
                cv2.putText(rotated, status, (x1 + 5, y2 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Highlight suggested move
        if last_suggestion:
            from_square = str(last_suggestion)[:2]
            to_square = str(last_suggestion)[2:4]
            
            from_c, from_r = chess_to_coords(from_square)
            to_c, to_r = chess_to_coords(to_square)
            
            from_center = (from_c * sq + sq//2, from_r * sq + sq//2)
            to_center = (to_c * sq + sq//2, to_r * sq + sq//2)
            
            cv2.arrowedLine(rotated, from_center, to_center, (0, 255, 255), 5, tipLength=0.3)
            cv2.putText(rotated, f"Suggested: {last_suggestion}", 
                       (10, BOARD_SIZE - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Show camera views
        top_resized = cv2.resize(top_view, (300, 300))
        side_resized = cv2.resize(side_view, (300, 300))
        wrist_resized = cv2.resize(wrist_view, (300, 300))
        combined = np.hstack([top_resized, side_resized, wrist_resized])

        # Analysis window
        analysis_img = np.zeros((600, 400, 3), dtype=np.uint8)
        
        cv2.putText(analysis_img, "Chess Engine", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(analysis_img, f"Move #{move_counter}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(analysis_img, f"Turn: {'White' if board.turn else 'Black'}", 
                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        if last_suggestion:
            cv2.putText(analysis_img, f"Best move: {last_suggestion}", 
                       (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Game status
        if board.is_checkmate():
            cv2.putText(analysis_img, "CHECKMATE!", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        elif board.is_check():
            cv2.putText(analysis_img, "CHECK!", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        # Controls
        cv2.putText(analysis_img, "Controls:", (10, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
        cv2.putText(analysis_img, "S=Suggestion A=Human help", (10, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, "C=Confirm move M=Manual", (10, 300), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, "N=New game Q=Quit", (10, 320), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)

        # Show windows
        cv2.imshow("board", rotated)
        cv2.imshow("camera views", combined)
        cv2.imshow("analysis", analysis_img)

        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('s'):
            print("\n🤖 Getting Stockfish suggestion...")
            last_suggestion = get_stockfish_move(board)
            last_analysis = analyze_position(board)
            if last_suggestion:
                print(f"💡 Stockfish suggests: {last_suggestion}")
            else:
                print("❌ No suggestion available")
        elif key == ord('a'):
            if board.turn:  # Human's turn (White)
                print("\n👤 Getting human move suggestion...")
                suggested = get_stockfish_move(board)
                if suggested:
                    print(f"💡 Suggested move for you: {suggested}")
                    print("Execute this move, then press 'C' to confirm")
                    last_suggestion = suggested
        elif key == ord('c'):
            if last_suggestion and board.turn:
                print(f"✅ Confirming move: {last_suggestion}")
                board.push(last_suggestion)
                move_counter += 1
                previous_occupancy = get_board_occupancy_from_chess_board(board)
                
                # Robot response
                if not board.is_game_over():
                    robot_move = get_stockfish_move(board)
                    if robot_move:
                        print(f"🤖 Robot plays: {robot_move}")
                        board.push(robot_move)
                        move_counter += 1
                        print("🔧 TODO: Execute with robot arm")
                        
                        last_suggestion = get_stockfish_move(board)
                        last_analysis = analyze_position(board)
                else:
                    print("🏁 Game Over!")
        elif key == ord('m'):
            move_input = input("\n📝 Enter move (e.g., e2e4): ")
            try:
                move = chess.Move.from_uci(move_input)
                if move in board.legal_moves:
                    board.push(move)
                    move_counter += 1
                    print(f"✅ Move {move_input} played!")
                    previous_occupancy = get_board_occupancy_from_chess_board(board)
                    last_suggestion = get_stockfish_move(board)
                else:
                    print("❌ Illegal move!")
            except:
                print("❌ Invalid move format!")
        elif key == ord('n'):
            print("\n🆕 Starting new game...")
            board = chess.Board()
            move_counter = 0
            last_suggestion = None
            previous_occupancy = get_expected_starting_occupancy()
        elif key == ord('d'):
            move_detection_active = not move_detection_active
            print(f"📹 Move detection: {'ON' if move_detection_active else 'OFF'}")

    # Cleanup
    stop_capture = True
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()