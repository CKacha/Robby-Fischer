#!/usr/bin/env python3
"""
Safe calibration tool for ChessArm
This prevents the freezing issue by using a simpler calibration approach
"""

import cv2
import numpy as np
import json
import time

CALIB_FILE = "board_calib_4pt.json"
clicked_points = []

def mouse_callback(event, x, y, flags, param):
    """Mouse callback for calibration clicks"""
    global clicked_points
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append([x, y])  # Store as list for JSON serialization
        print(f"Point {len(clicked_points)}: ({x}, {y})")
        if len(clicked_points) == 4:
            print("All 4 points collected! Press 'q' to save or 'r' to reset")

def safe_calibration():
    """Safe calibration that won't freeze VSCode"""
    global clicked_points
    clicked_points = []
    
    print("Safe Calibration Mode")
    print("=" * 30)
    print("1. Click on: a8 (top-left corner)")
    print("2. Click on: h8 (top-right corner)")  
    print("3. Click on: h1 (bottom-right corner)")
    print("4. Click on: a1 (bottom-left corner)")
    print("")
    print("Controls:")
    print("- Click to add point")
    print("- 'r' = reset points")
    print("- 'q' = save calibration (after 4 points)")
    print("- ESC = cancel")
    print("")
    
    # Try multiple camera indices
    cap = None
    for camera_idx in [6, 4, 3, 2, 1, 0]:  # Try top camera first
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                print(f"Using camera {camera_idx}")
                break
            cap.release()
        cap = None
    
    if cap is None:
        print("ERROR: No working camera found!")
        return None
    
    # Set up window with proper flags to prevent freezing
    window_name = "Chess Board Calibration"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window_name, 800, 600)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    timeout_start = time.time()
    timeout_duration = 120  # 2 minute timeout
    
    try:
        while True:
            # Check timeout
            if time.time() - timeout_start > timeout_duration:
                print("Calibration timed out after 2 minutes")
                break
                
            ret, frame = cap.read()
            if not ret:
                print("Can't read from camera")
                time.sleep(0.1)
                continue
            
            # Make a copy to draw on
            display_frame = frame.copy()
            
            # Draw collected points
            for i, point in enumerate(clicked_points):
                cv2.circle(display_frame, tuple(point), 8, (0, 0, 255), -1)
                cv2.circle(display_frame, tuple(point), 12, (255, 255, 255), 2)
                cv2.putText(display_frame, str(i+1), 
                           (point[0] + 15, point[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Status overlay
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (10, 10), (600, 100), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0, display_frame)
            
            if len(clicked_points) < 4:
                status_text = f"Click corner {len(clicked_points) + 1}/4"
                corner_names = ["a8 (TOP-LEFT)", "h8 (TOP-RIGHT)", 
                               "h1 (BOTTOM-RIGHT)", "a1 (BOTTOM-LEFT)"]
                next_corner = corner_names[len(clicked_points)]
                cv2.putText(display_frame, status_text, (20, 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Next: {next_corner}", (20, 65),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            else:
                cv2.putText(display_frame, "Press Q to SAVE calibration", (20, 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(display_frame, "Press R to RESET points", (20, 65),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            cv2.imshow(window_name, display_frame)
            
            # Handle key presses (short timeout to prevent freezing)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                print("Calibration cancelled")
                break
            elif key == ord('r'):
                clicked_points = []
                print("Points reset")
            elif key == ord('q') and len(clicked_points) == 4:
                # Save calibration
                calib_data = {"points": clicked_points}
                try:
                    with open(CALIB_FILE, 'w') as f:
                        json.dump(calib_data, f, indent=2)
                    print(f"Calibration saved to {CALIB_FILE}")
                    print(f"Points: {clicked_points}")
                    return calib_data
                except Exception as e:
                    print(f"Failed to save calibration: {e}")
                    break
    
    except KeyboardInterrupt:
        print("\nCalibration interrupted")
    except Exception as e:
        print(f"Calibration error: {e}")
    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        # Extra cleanup to prevent hanging
        cv2.waitKey(100)
        for i in range(5):
            cv2.destroyAllWindows()
            cv2.waitKey(1)
    
    return None

def test_calibration():
    """Test existing calibration by showing warped board"""
    if not os.path.exists(CALIB_FILE):
        print(f"No calibration file found: {CALIB_FILE}")
        return
    
    try:
        with open(CALIB_FILE, 'r') as f:
            calib = json.load(f)
        print(f"Loaded calibration: {calib}")
        
        # Test with camera
        cap = None
        for camera_idx in [6, 4, 3, 2, 1, 0]:
            cap = cv2.VideoCapture(camera_idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    break
                cap.release()
            cap = None
        
        if cap is None:
            print("No camera available for testing")
            return
        
        # Apply perspective transform
        points = np.array(calib["points"], dtype=np.float32)
        board_size = 800
        dst_points = np.array([
            [0, 0],
            [board_size, 0], 
            [board_size, board_size],
            [0, board_size]
        ], dtype=np.float32)
        
        matrix = cv2.getPerspectiveTransform(points, dst_points)
        
        cv2.namedWindow("Calibration Test", cv2.WINDOW_NORMAL)
        
        print("Testing calibration - press ESC to exit")
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
                
            # Apply transform
            warped = cv2.warpPerspective(frame, matrix, (board_size, board_size))
            
            # Draw grid
            for i in range(1, 8):
                cv2.line(warped, (0, i * board_size // 8), (board_size, i * board_size // 8), (0, 255, 0), 2)
                cv2.line(warped, (i * board_size // 8, 0), (i * board_size // 8, board_size), (0, 255, 0), 2)
            
            cv2.imshow("Calibration Test", warped)
            
            if cv2.waitKey(30) & 0xFF == 27:  # ESC
                break
        
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(100)
        
    except Exception as e:
        print(f"Test failed: {e}")

def main():
    """Main calibration tool"""
    print("ChessArm Safe Calibration Tool")
    print("=" * 40)
    
    if os.path.exists(CALIB_FILE):
        print(f"Existing calibration found: {CALIB_FILE}")
        choice = input("(t)est existing, (r)ecalibrate, or (q)uit? ").lower()
        
        if choice == 't':
            test_calibration()
            return
        elif choice == 'q':
            return
        # else: fall through to recalibrate
    
    print("Starting new calibration...")
    result = safe_calibration()
    
    if result:
        print("\n✅ Calibration successful!")
        test_choice = input("Test the calibration? (y/n): ").lower()
        if test_choice == 'y':
            test_calibration()
    else:
        print("\n❌ Calibration failed or cancelled")

if __name__ == "__main__":
    main()