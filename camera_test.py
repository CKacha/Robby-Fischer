#!/usr/bin/env python3
"""
Simple camera test for ChessArm
Tests if cameras are working and displays their feeds
"""

import cv2
import numpy as np
import threading
import time

# Config
CAMERA_INDEXES = [8, 7, 3]  # wrist(8), top(7), side(3) - adjust based on your setup
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# Globals
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
            else:
                print(f"Camera {i}: Opens but can't read frames")
        cap.release()
    
    print(f"Available cameras: {available_cameras}")
    return available_cameras

def capture_frames(camera_idx, array_idx, frame_array):
    """Camera capture thread"""
    global stop_capture
    
    print(f"Starting capture thread for camera {camera_idx}")
    cap = cv2.VideoCapture(camera_idx)
    
    if not cap.isOpened():
        print(f"Failed to open camera {camera_idx}")
        return
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    print(f"Successfully opened camera {camera_idx}")
    frame_count = 0

    while not stop_capture:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                frame_array[array_idx] = frame.copy()
            frame_count += 1
            
            # Print status every 30 frames (about once per second)
            if frame_count % 30 == 0:
                print(f"Camera {camera_idx}: {frame_count} frames captured")
        else:
            print(f"Error capturing frame from camera {camera_idx}")
            time.sleep(0.1)

    cap.release()
    print(f"Released camera {camera_idx}")

def main():
    global stop_capture
    
    # Check cameras
    available_cameras = detect_cameras()
    print(f"Attempting to use cameras: {CAMERA_INDEXES}")
    
    # Check if our desired cameras are available
    for camera_idx in CAMERA_INDEXES:
        if camera_idx not in available_cameras:
            print(f"WARNING: Camera {camera_idx} not found in available cameras!")
    
    # Start camera threads
    frames = [None] * len(CAMERA_INDEXES)
    threads = []
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        thread = threading.Thread(target=capture_frames, args=(camera_idx, i, frames))
        threads.append(thread)
        thread.start()

    print("Waiting for cameras to initialize...")
    time.sleep(3)  # Wait for cameras to start

    # Setup windows
    cv2.namedWindow("Camera Test", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Camera Test", 900, 300)

    print("\n🎥 Camera Test Running")
    print("Controls:")
    print("  Q = Quit")
    print("  R = Reset cameras")
    print("")

    frame_count = 0
    
    while True:
        frame_count += 1
        
        # Get frames with error handling
        with frame_lock:
            current_frames = [f.copy() if f is not None else None for f in frames]
        
        # Create display
        display_frames = []
        
        for i, frame in enumerate(current_frames):
            if frame is not None:
                # Resize frame
                resized = cv2.resize(frame, (300, 300))
                # Add label
                cv2.putText(resized, f"Camera {CAMERA_INDEXES[i]}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                display_frames.append(resized)
            else:
                # Create placeholder
                placeholder = np.zeros((300, 300, 3), dtype=np.uint8)
                cv2.putText(placeholder, f"Camera {CAMERA_INDEXES[i]}", (10, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(placeholder, "No Signal", (10, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                display_frames.append(placeholder)
        
        # Combine frames horizontally
        if len(display_frames) == 3:
            combined = np.hstack(display_frames)
        else:
            combined = np.zeros((300, 900, 3), dtype=np.uint8)
            cv2.putText(combined, "Camera Error", (350, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(combined, f"Frame: {frame_count}", (10, combined.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show combined view
        cv2.imshow("Camera Test", combined)
        
        # Handle input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quitting...")
            break
        elif key == ord('r'):
            print("Resetting cameras...")
            # Could restart camera threads here if needed
        
        # Print status every 60 frames (about once every 2 seconds)
        if frame_count % 60 == 0:
            available_count = sum(1 for f in current_frames if f is not None)
            print(f"Status: {available_count}/3 cameras active, frame {frame_count}")

    # Cleanup
    stop_capture = True
    print("Stopping capture threads...")
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()
    print("Camera test completed!")

if __name__ == "__main__":
    main()