import cv2
import numpy as np
import json
import os
import chess
import chess.engine
import threading
import time  # Importing the missing time module

# =========================
# CONFIG
# =========================

CAMERA_INDEXES = [4, 6, 3]  # wrist(2), top(6), side(3) - based on camera.txt
CALIB_FILE = "board_calib_4pt.json"
BOARD_SIZE = 800  # The warped board will be BOARD_SIZE x BOARD_SIZE
OCCUPANCY_THRESHOLD = 140
CENTER_MARGIN = 0.25
FRAME_WIDTH = 640  # Resolution for FPS
FRAME_HEIGHT = 480
FPS = 30  # Set the frame rate to 30 FPS for each camera

clicked_points = []
frame_lock = threading.Lock()  
frames = [None, None, None]  

def detect_cameras():
    """Detect available cameras by testing indices 0-10"""
    available_cameras = []
    print("Detecting available cameras...")
    
    for i in range(11):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available_cameras.append(i)
                print(f"Camera {i}: Working (resolution: {frame.shape[1]}x{frame.shape[0]})")
            else:
                print(f"Camera {i}: Opens but can't read frames")
        cap.release()
    
    if not available_cameras:
        print("No working cameras found!")
    else:
        print(f"Available cameras: {available_cameras}")
    
    return available_cameras

# =========================
# CALIBRATION
# =========================

def mouse_cb(event, x, y, flags, param):
    global clicked_points
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append((x, y))
        print(f"Point {len(clicked_points)}: {x}, {y}")

def calibrate_with_frame_source(frame_source, source_type="capture"):
    """
    Calibrate using either a direct capture object or frame array
    frame_source: either cv2.VideoCapture object or frames array
    source_type: "capture" for VideoCapture, "frames" for frame array
    """
    global clicked_points
    clicked_points = []

    print("\nCALIBRATION MODE")
    print("Click in order:")
    print("1) a8 (top-left)")
    print("2) h8 (top-right)")
    print("3) h1 (bottom-right)")
    print("4) a1 (bottom-left)")
    print("Press Q when done, ESC to cancel\n")

    # Destroy any existing windows first
    cv2.destroyAllWindows()
    cv2.waitKey(100)  # Wait for windows to close
    
    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow("calibrate", 800, 600)
    cv2.setMouseCallback("calibrate", mouse_cb)

    start_time = time.time()
    timeout = 60  # 60 second timeout
    frame_count = 0
    
    try:
        while time.time() - start_time < timeout:
            frame = None
            frame_count += 1
            
            if source_type == "capture":
                ret, frame = frame_source.read()
                if not ret:
                    print("Warning: Cannot read from calibration camera")
                    time.sleep(0.1)
                    continue
            elif source_type == "frames":
                # Get frame from threading source
                try:
                    with frame_lock:
                        if frame_source[1] is not None:  # top camera frame
                            frame = frame_source[1].copy()
                except Exception as e:
                    print(f"Frame access error: {e}")
                    time.sleep(0.05)
                    continue
                
                if frame is None:
                    if frame_count % 100 == 0:  # Print every 100 attempts
                        print("Waiting for camera frame...")
                    time.sleep(0.05)
                    continue

            # Create frame copy to avoid modifying original
            display_frame = frame.copy()

            # Draw clicked points with better visibility
            for i, p in enumerate(clicked_points):
                cv2.circle(display_frame, p, 10, (0, 0, 255), -1)
                cv2.circle(display_frame, p, 12, (255, 255, 255), 2)
                cv2.putText(display_frame, str(i+1), (p[0]+15, p[1]-15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Show instructions with better visibility
            instruction_text = f"Click point {len(clicked_points)+1}/4"
            if len(clicked_points) == 4:
                instruction_text = "Press Q to save calibration"
                
            # Create instruction overlay
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (5, 5), (500, 45), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0, display_frame)
            
            cv2.putText(display_frame, instruction_text, 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Add corner labels to help user
            corner_labels = ["a8 (TOP-LEFT)", "h8 (TOP-RIGHT)", "h1 (BOTTOM-RIGHT)", "a1 (BOTTOM-LEFT)"]
            if len(clicked_points) < 4:
                cv2.putText(display_frame, f"Next: {corner_labels[len(clicked_points)]}", 
                           (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            cv2.imshow("calibrate", display_frame)

            # Use shorter waitKey to prevent freezing
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') and len(clicked_points) == 4:
                print("Saving calibration...")
                break
            elif key == 27:  # ESC key
                print("Calibration cancelled by user")
                cv2.destroyWindow("calibrate")
                cv2.waitKey(100)
                return None
            elif key == ord('c'):  # Clear points
                clicked_points = []
                print("Cleared calibration points")

        # Clean up window
        cv2.destroyWindow("calibrate")
        cv2.waitKey(100)  # Ensure window is destroyed

        if len(clicked_points) != 4:
            print(f"Calibration failed: got {len(clicked_points)} points, need 4")
            if time.time() - start_time >= timeout:
                print("Calibration timed out")
            return None

        calib = {"points": clicked_points}
        
        # Validate calibration points (basic check)
        if len(set(clicked_points)) != 4:
            print("Error: Duplicate calibration points detected")
            return None
            
        try:
            with open(CALIB_FILE, "w") as f:
                json.dump(calib, f, indent=2)
            print("Calibration saved successfully!")
            return calib
        except Exception as e:
            print(f"Failed to save calibration: {e}")
            return None
        
    except KeyboardInterrupt:
        print("\nCalibration interrupted by user")
        cv2.destroyWindow("calibrate")
        cv2.waitKey(100)
        return None
    except Exception as e:
        print(f"Calibration error: {e}")
        cv2.destroyWindow("calibrate")
        cv2.waitKey(100)
        return None

def calibrate(cap):
    """Legacy function for backwards compatibility"""
    return calibrate_with_frame_source(cap, "capture")

def load_calibration():
    with open(CALIB_FILE, "r") as f:
        return json.load(f)

# =========================
# VISION
# =========================

def warp_board(frame, pts):
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
    return cv2.rotate(warped_board, cv2.ROTATE_90_COUNTERCLOCKWISE)

def center_crop(img, margin):
    h, w = img.shape[:2]
    dx = int(w * margin)
    dy = int(h * margin)
    if h - 2 * dy <= 0 or w - 2 * dx <= 0:
        return None
    return img[dy:h-dy, dx:w-dx]

def is_occupied(square):
    if square is None or square.size == 0:
        return False
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    return gray.mean() < OCCUPANCY_THRESHOLD

# =========================
# CHESS BOARD STATE DETECTION
# =========================

def detect_board_state(warped_board):
    """Convert warped board image to occupancy matrix"""
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

def occupancy_to_fen(occupancy_matrix, reference_board=None):
    """Convert occupancy matrix to FEN notation
    This is a simplified approach - in practice you'd need piece recognition"""
    
    if reference_board is None:
        # Start with standard chess starting position
        reference_board = chess.Board()
    
    # For now, we'll just track piece movements from the starting position
    # In a full implementation, you'd need computer vision to identify piece types
    
    # Convert occupancy to simple FEN (this is simplified)
    fen_rows = []
    for r in range(8):
        fen_row = ""
        empty_count = 0
        
        for c in range(8):
            if occupancy_matrix[r, c]:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                # For now, just use 'p' for any piece (you'd need piece recognition)
                fen_row += "p" if r > 3 else "P"
            else:
                empty_count += 1
        
        if empty_count > 0:
            fen_row += str(empty_count)
        
        fen_rows.append(fen_row)
    
    return "/".join(fen_rows) + " w - - 0 1"

# =========================
# STOCKFISH INTERACTION
# =========================

def get_stockfish_move(current_board):
    """Get best move from Stockfish"""
    try:
        with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
            result = engine.play(current_board, chess.engine.Limit(time=1.0))
            return result.move
    except Exception as e:
        print(f"Stockfish error: {e}")
        return None

def analyze_position(current_board, depth=15):
    """Get detailed analysis from Stockfish"""
    try:
        with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
            info = engine.analyse(current_board, chess.engine.Limit(depth=depth))
            return info
    except Exception as e:
        print(f"Analysis error: {e}")
        return None

# =========================
# THREADING FOR CAMERA CAPTURE
# =========================

stop_capture = False

def capture_frames(camera_idx, array_idx, frame_array):
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
            print(f"Error capturing frame from camera {camera_idx}")
            time.sleep(0.1)  # Brief pause before retry

    cap.release()
    print(f"Released camera {camera_idx}")

# =========================
# MAIN
# =========================

def main():
    global stop_capture
    
    # First, detect available cameras
    available_cameras = detect_cameras()
    print(f"Attempting to use cameras: {CAMERA_INDEXES}")
    
    # Check if our desired cameras are available
    for camera_idx in CAMERA_INDEXES:
        if camera_idx not in available_cameras:
            print(f"WARNING: Camera {camera_idx} not found in available cameras!")
    
    # Initialize the frames array
    frames = [None] * len(CAMERA_INDEXES)
    
    # Start the camera capture threads
    threads = []
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        thread = threading.Thread(target=capture_frames, args=(camera_idx, i, frames))
        threads.append(thread)
        thread.start()

    # Wait for the threads to initialize
    time.sleep(2)  # Sleep a bit to ensure threads are capturing frames

    # Load calibration or calibrate
    if os.path.exists(CALIB_FILE):
        calib = load_calibration()
    else:
        print("No calibration found, using live camera feed for calibration...")
        # Use the threaded frames for calibration to avoid camera conflicts
        calib = calibrate_with_frame_source(frames, "frames")
        if calib is None:
            print("Calibration failed!")
            stop_capture = True
            for thread in threads:
                thread.join()
            return

    cv2.namedWindow("board", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("board", 900, 900)
    
    cv2.namedWindow("analysis", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("analysis", 400, 600)

    print("\nRUNNING")
    print("R = recalibrate")
    print("S = get Stockfish suggestion")
    print("M = make a move (enter in format: e2e4)")
    print("N = new game")
    print("Q = quit\n")

    # Initialize chess board
    current_board = chess.Board()
    last_suggestion = None
    last_analysis = None
    move_counter = 0

    while True:
        # Lock frames to avoid concurrent access issues
        with frame_lock:
            # Check if any frame is None
            if any(frame is None for frame in frames):
                continue

            top_view = frames[1].copy()
            side_view = frames[2].copy()
            wrist_view = frames[0].copy()

        # Process the top view for chess detection
        warped_top = warp_board(top_view, calib["points"])
        rotated_board = rotate_board(warped_top)
        
        # Detect current board occupancy
        occupancy_matrix = detect_board_state(rotated_board)

        sq = BOARD_SIZE // 8
        
        # Draw board grid and occupancy visualization
        for r in range(1, 8):
            cv2.line(rotated_board, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 2)
            cv2.line(rotated_board, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 2)

        # Visualize occupancy and draw square info
        for r in range(8):
            for c in range(8):
                x1 = c * sq
                y1 = r * sq
                x2 = x1 + sq
                y2 = y1 + sq
                
                # Color squares based on occupancy
                occupied = occupancy_matrix[r, c]
                color = (0, 0, 255) if occupied else (0, 255, 0)  # Red if occupied, green if empty
                cv2.rectangle(rotated_board, (x1+2, y1+2), (x2-2, y2-2), color, 3)
                
                # Add square labels
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                label = f"{file_char}{rank_char}"
                cv2.putText(rotated_board, label, (x1 + 5, y1 + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Show occupancy status
                status = "●" if occupied else "○"
                cv2.putText(rotated_board, status, (x1 + 5, y2 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Highlight suggested move if available
        if last_suggestion:
            from_square = str(last_suggestion)[:2]
            to_square = str(last_suggestion)[2:4]
            
            # Convert chess notation to grid coordinates
            def chess_to_coords(square_name):
                file_idx = ord(square_name[0]) - ord('a')  # a=0, b=1, etc.
                rank_idx = 8 - int(square_name[1])  # 8=0, 7=1, etc. (flipped)
                return file_idx, rank_idx
            
            from_c, from_r = chess_to_coords(from_square)
            to_c, to_r = chess_to_coords(to_square)
            
            # Draw arrow for suggested move
            from_center = (from_c * sq + sq//2, from_r * sq + sq//2)
            to_center = (to_c * sq + sq//2, to_r * sq + sq//2)
            
            cv2.arrowedLine(rotated_board, from_center, to_center, (0, 255, 255), 5, tipLength=0.3)
            cv2.putText(rotated_board, f"Suggested: {last_suggestion}", 
                       (10, BOARD_SIZE - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Display the warped, rotated board
        cv2.imshow("board", rotated_board)

        # Show all camera views stacked horizontally
        top_view_resized = cv2.resize(top_view, (300, 300))
        side_view_resized = cv2.resize(side_view, (300, 300))
        wrist_view_resized = cv2.resize(wrist_view, (300, 300))

        combined_view = np.hstack((top_view_resized, side_view_resized, wrist_view_resized))
        cv2.imshow("camera views", combined_view)
        
        # Create analysis display
        analysis_img = np.zeros((600, 400, 3), dtype=np.uint8)
        
        # Show current board state
        cv2.putText(analysis_img, "Chess Analysis", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.putText(analysis_img, f"Move #{move_counter}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        cv2.putText(analysis_img, f"Turn: {'White' if current_board.turn else 'Black'}", 
                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        if last_suggestion:
            cv2.putText(analysis_img, f"Best move: {last_suggestion}", 
                       (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if last_analysis:
            score = last_analysis.get("score", {})
            if hasattr(score, 'relative') and score.relative:
                score_text = f"Eval: {score.relative.score(mate_score=1000)}"
                cv2.putText(analysis_img, score_text, (10, 180), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Show game status
        if current_board.is_checkmate():
            cv2.putText(analysis_img, "CHECKMATE!", (10, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        elif current_board.is_check():
            cv2.putText(analysis_img, "CHECK!", (10, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        elif current_board.is_stalemate():
            cv2.putText(analysis_img, "STALEMATE", (10, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)
        
        # Show recent moves
        moves_list = list(current_board.move_stack)
        y_offset = 260
        cv2.putText(analysis_img, "Recent moves:", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        for i, move in enumerate(moves_list[-8:]):  # Show last 8 moves
            move_text = f"{len(moves_list) - 7 + i}: {move}"
            cv2.putText(analysis_img, move_text, (10, y_offset + 30 + i*25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Instructions
        cv2.putText(analysis_img, "Controls:", (10, 520), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
        cv2.putText(analysis_img, "S = Stockfish suggestion", (10, 545), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, "M = Make move", (10, 565), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, "N = New game", (10, 585), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        
        cv2.imshow("analysis", analysis_img)

        # Key detection
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            print("\nRecalibrating...\n")
            # Use the live threaded frames for recalibration
            calib = calibrate_with_frame_source(frames, "frames")
            if calib is None:
                print("Recalibration failed, continuing with old calibration")
        elif key == ord('s'):
            print("\nGetting Stockfish suggestion...")
            last_suggestion = get_stockfish_move(current_board)
            last_analysis = analyze_position(current_board)
            if last_suggestion:
                print(f"Stockfish suggests: {last_suggestion}")
            else:
                print("No suggestion available")
        elif key == ord('m'):
            print("\nEnter move (e.g., e2e4): ", end="")
            move_input = input()
            try:
                move = chess.Move.from_uci(move_input)
                if move in current_board.legal_moves:
                    current_board.push(move)
                    move_counter += 1
                    print(f"Move {move_input} played!")
                    # Get new suggestion after move
                    last_suggestion = get_stockfish_move(current_board)
                    last_analysis = analyze_position(current_board)
                else:
                    print("Illegal move!")
            except:
                print("Invalid move format!")
        elif key == ord('n'):
            print("\nStarting new game...")
            current_board = chess.Board()
            move_counter = 0
            last_suggestion = None
            last_analysis = None

    # Stop capture threads
    stop_capture = True
    
    # Release all camera objects
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
