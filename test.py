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

CAMERA_INDEXES = [2, 3, 6]  # USB2.0_CAM1(2), UGREEN Camera 2K(3), UGREEN Camera(6)
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
# CALIBRATION
# =========================

def mouse_cb(event, x, y, flags, param):
    global clicked_points
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append((x, y))
        print(f"Point {len(clicked_points)}: {x}, {y}")

def calibrate(cap):
    global clicked_points
    clicked_points = []

    print("\nCALIBRATION MODE")
    print("Click in order:")
    print("1) a8 (top-left)")
    print("2) h8 (top-right)")
    print("3) h1 (bottom-right)")
    print("4) a1 (bottom-left)")
    print("Press Q when done\n")

    cv2.namedWindow("calibrate", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("calibrate", mouse_cb)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        for p in clicked_points:
            cv2.circle(frame, p, 6, (0, 0, 255), -1)

        cv2.imshow("calibrate", frame)

        if cv2.waitKey(10) & 0xFF == ord("q"):
            break

    cv2.destroyWindow("calibrate")

    if len(clicked_points) != 4:
        raise RuntimeError("Calibration failed: need exactly 4 points")

    calib = {"points": clicked_points}
    with open(CALIB_FILE, "w") as f:
        json.dump(calib, f, indent=2)

    print("Calibration saved.")
    return calib

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
    
    print(f"Attempting to connect to cameras: {CAMERA_INDEXES}")
    
    # Set camera permissions first
    for camera_idx in CAMERA_INDEXES:
        os.system(f"sudo chmod 666 /dev/video{camera_idx}")
        print(f"Set permissions for /dev/video{camera_idx}")
    
    # Test camera connections before starting threads
    working_cameras = []
    for camera_idx in CAMERA_INDEXES:
        test_cap = cv2.VideoCapture(camera_idx)
        if test_cap.isOpened():
            working_cameras.append(camera_idx)
            print(f"✅ Camera {camera_idx} is accessible")
            test_cap.release()
        else:
            print(f"❌ Camera {camera_idx} failed to open")
    
    if len(working_cameras) == 0:
        print("❌ No cameras are working! Check connections and permissions.")
        return
    
    print(f"📊 {len(working_cameras)}/{len(CAMERA_INDEXES)} cameras working: {working_cameras}")
    
    # Initialize the frames array
    frames = [None] * len(CAMERA_INDEXES)
    
    # Start the camera capture threads
    threads = []
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        thread = threading.Thread(target=capture_frames, args=(camera_idx, i, frames))
        threads.append(thread)
        thread.start()

    # Wait for the threads to initialize
    print("Waiting for camera threads to initialize...")
    time.sleep(3)  # Give more time for initialization

    # Load calibration or calibrate
    if os.path.exists(CALIB_FILE):
        calib = load_calibration()
    else:
        # Try to use the top camera for calibration
        test_cap = cv2.VideoCapture(CAMERA_INDEXES[1])
        if not test_cap.isOpened():
            print(f"Cannot open camera {CAMERA_INDEXES[1]} for calibration")
            stop_capture = True
            for thread in threads:
                thread.join()
            return
        calib = calibrate(test_cap)
        test_cap.release()

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
                print("Waiting for camera frames...")
                time.sleep(0.1)
                continue

            top_view = frames[1].copy()
            side_view = frames[2].copy()
            wrist_view = frames[0].copy()

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
            test_cap = cv2.VideoCapture(CAMERA_INDEXES[1])
            if test_cap.isOpened():
                calib = calibrate(test_cap)
                test_cap.release()
            else:
                print("Cannot open camera for recalibration")

    # Stop capture threads and clean up
    stop_capture = True
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
