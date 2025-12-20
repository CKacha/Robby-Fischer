import cv2
import numpy as np
import json
import os
import chess
import chess.engine
import time

CAMERA_INDEXES = [4, 6, 3]  # wrist(4), top(6), side(3)
CALIB_FILE = "board_calib_4pt.json"
BOARD_SIZE = 800  
OCCUPANCY_THRESHOLD = 140
CENTER_MARGIN = 0.25
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

clicked_points = []

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
# MAIN
# =========================

def main():
    # Open all cameras
    caps = [cv2.VideoCapture(idx) for idx in CAMERA_INDEXES]
    if not all([cap.isOpened() for cap in caps]):
        raise RuntimeError("Could not open one or more cameras")

    if os.path.exists(CALIB_FILE):
        calib = load_calibration()
    else:
        calib = calibrate(caps[0])

    cv2.namedWindow("board", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("board", 900, 900)

    print("\nRUNNING")
    print("R = recalibrate")
    print("Q = quit\n")

    # Initialize chess board
    current_board = chess.Board()

    while True:
        # Capture frames from all cameras
        frames = [cap.read()[1] for cap in caps]

        if any(frame is None for frame in frames):
            continue

        # Process top-down view for chess detection (index 1 is the top camera)
        warped = warp_board(frames[1], calib["points"])
        sq = BOARD_SIZE // 8

        # Loop through all squares and check occupancy
        for r in range(8):
            for c in range(8):
                x1 = c * sq
                y1 = r * sq
                x2 = x1 + sq
                y2 = y1 + sq

                square = warped[y1:y2, x1:x2]
                square_c = center_crop(square, CENTER_MARGIN)

                occ = is_occupied(square_c)

                color = (0, 0, 255) if occ else (0, 255, 0)
                cv2.rectangle(warped, (x1, y1), (x2, y2), color, 1)

                # Chess coordinates
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                label = f"{file_char}{rank_char}"

                cv2.putText(
                    warped,
                    label,
                    (x1 + 5, y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )

        # Display all camera feeds in a grid layout
        wrist_view = frames[0]
        side_view = frames[2]

        # Resize for display consistency
        wrist_view = cv2.resize(wrist_view, (300, 300))
        side_view = cv2.resize(side_view, (300, 300))
        warped = cv2.resize(warped, (600, 600))

        # Stack the views: wrist (left), top (middle), side (right)
        combined_view = np.hstack((wrist_view, warped, side_view))

        # Show the combined view along with the warped board
        cv2.imshow("board", warped)
        cv2.imshow("camera views", combined_view)

        # Check for chess piece movement (simple logic here)
        if cv2.waitKey(10) & 0xFF == ord("q"):
            break
        if cv2.waitKey(10) & 0xFF == ord("r"):
            print("\nRecalibrating...\n")
            calib = calibrate(caps[0])

        # Get Stockfish move (just an example)
        stockfish_move = get_stockfish_move(current_board)
        print(f"Stockfish suggests: {stockfish_move}")

    # Release all camera objects
    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
