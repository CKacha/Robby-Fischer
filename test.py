import cv2
import numpy as np
import json
import os

TOP_CAMERA_INDEX = 6
CALIB_FILE = "board_calib_4pt.json"

BOARD_SIZE = 800          
OCCUPANCY_THRESHOLD = 140 
CENTER_MARGIN = 0.25      


clicked_points = []

def mouse_cb(event, x, y, flags, param):
    global clicked_points
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append((x, y))
        print(f"Point {len(clicked_points)}: {x}, {y}")

def calibrate(cap):
    """
    Click points in this order:
    1) a8 (top-left)
    2) h8 (top-right)
    3) h1 (bottom-right)
    4) a1 (bottom-left)
    """
    global clicked_points
    clicked_points = []

    print("\nCALIBRATION MODE")
    print("Click in order:")
    print("1) a8  (top-left)")
    print("2) h8  (top-right)")
    print("3) h1  (bottom-right)")
    print("4) a1  (bottom-left)")
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
        raise RuntimeError("Need exactly 4 points")

    calib = {"points": clicked_points}
    with open(CALIB_FILE, "w") as f:
        json.dump(calib, f, indent=2)

    print("Calibration saved.")
    return calib

def load_calibration():
    with open(CALIB_FILE, "r") as f:
        return json.load(f)

def warp_board(frame, pts):
    src = np.array(pts, dtype=np.float32)
    dst = np.array([
        [0, 0],
        [BOARD_SIZE, 0],
        [BOARD_SIZE, BOARD_SIZE],
        [0, BOARD_SIZE]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(frame, M, (BOARD_SIZE, BOARD_SIZE))

def center_crop(img, margin):
    if img is None or img.size == 0:
        return None
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

def main():
    cap = cv2.VideoCapture(TOP_CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open top camera")

    if os.path.exists(CALIB_FILE):
        calib = load_calibration()
    else:
        calib = calibrate(cap)

    cv2.namedWindow("board", cv2.WINDOW_NORMAL)

    print("\nRUNNING")
    print("R = recalibrate")
    print("Q = quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        warped = warp_board(frame, calib["points"])
        sq = BOARD_SIZE // 8

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

        cv2.imshow("board", warped)

        key = cv2.waitKey(10) & 0xFF
        if key == ord("q"):
            break
        if key == ord("r"):
            print("\nRecalibrating...\n")
            calib = calibrate(cap)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
