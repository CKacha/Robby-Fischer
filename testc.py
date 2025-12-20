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

# =========================
# GLOBALS
# =========================

clicked_points = []
frame_lock = threading.Lock()  # To avoid race conditions when accessing frames
frames = [None, None, None]  # To hold frames from the cameras

# =========================
# CAMERA DETECTION
# =========================

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
    cv2.waitKey(1)
    
    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("calibrate", 800, 600)
    cv2.setMouseCallback("calibrate", mouse_cb)

    start_time = time.time()
    timeout = 60  # 60 second timeout
    
    try:
        while time.time() - start_time < timeout:
            frame = None
            
            if source_type == "capture":
                ret, frame = frame_source.read()
                if not ret:
                    time.sleep(0.01)
                    continue
            elif source_type == "frames":
                # Get frame from threading source
                with frame_lock:
                    if frame_source[1] is not None:  # top camera frame
                        frame = frame_source[1].copy()
                
                if frame is None:
                    time.sleep(0.01)
                    continue

            # Draw clicked points with better visibility
            for i, p in enumerate(clicked_points):
                cv2.circle(frame, p, 10, (0, 0, 255), -1)
                cv2.circle(frame, p, 12, (255, 255, 255), 2)
                cv2.putText(frame, str(i+1), (p[0]+15, p[1]-15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Show instructions with better visibility
            instruction_text = f"Click point {len(clicked_points)+1}/4"
            if len(clicked_points) == 4:
                instruction_text = "Press Q to save calibration"
                
            cv2.rectangle(frame, (5, 5), (400, 40), (0, 0, 0), -1)
            cv2.putText(frame, instruction_text, 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("calibrate", frame)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') and len(clicked_points) == 4:
                break
            elif key == 27:  # ESC key
                print("Calibration cancelled")
                cv2.destroyWindow("calibrate")
                cv2.waitKey(1)
                return None

        # Clean up window
        cv2.destroyWindow("calibrate")
        cv2.waitKey(1)

        if len(clicked_points) != 4:
            print(f"Calibration failed: got {len(clicked_points)} points, need 4")
            return None

        calib = {"points": clicked_points}
        with open(CALIB_FILE, "w") as f:
            json.dump(calib, f, indent=2)

        print("Calibration saved successfully!")
        return calib
        
    except Exception as e:
        print(f"Calibration error: {e}")
        cv2.destroyWindow("calibrate")
        cv2.waitKey(1)
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

    print("\nRUNNING")
    print("R = recalibrate")
    print("Q = quit\n")

    # Initialize chess board
    current_board = chess.Board()

    while True:
        # Lock frames to avoid concurrent access issues
        with frame_lock:
            # Check if any frame is None
            if any(frame is None for frame in frames):
                continue

            top_view = frames[1]
            side_view = frames[2]
            wrist_view = frames[0]

            # Process the top view for chess detection
            warped_top = warp_board(top_view, calib["points"])
            rotated_board = rotate_board(warped_top)

            sq = BOARD_SIZE // 8
            for r in range(1, 8):
                cv2.line(rotated_board, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 2)
                cv2.line(rotated_board, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 2)

            # Add labels on the rotated board
            for r in range(8):
                cv2.putText(rotated_board, str(8 - r), (5, r * sq + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            for c in range(8):
                cv2.putText(rotated_board, chr(ord('a') + c), (c * sq + 15, BOARD_SIZE - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Display the warped, rotated board
            cv2.imshow("board", rotated_board)

        # Show all camera views stacked horizontally
        top_view_resized = cv2.resize(top_view, (300, 300))
        side_view_resized = cv2.resize(side_view, (300, 300))
        wrist_view_resized = cv2.resize(wrist_view, (300, 300))

        combined_view = np.hstack((top_view_resized, side_view_resized, wrist_view_resized))
        cv2.imshow("camera views", combined_view)

        # Key detection
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('r'):
            print("\nRecalibrating...\n")
            # Use the live threaded frames for recalibration
            calib = calibrate_with_frame_source(frames, "frames")
            if calib is None:
                print("Recalibration failed, continuing with old calibration")

    # Stop capture threads
    stop_capture = True
    
    # Release all camera objects
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
