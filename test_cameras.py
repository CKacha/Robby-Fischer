#!/usr/bin/env python3
"""
Simple camera test script to debug camera connections
"""

import cv2
import os
import sys

# Based on your camera.txt file
CAMERA_INDEXES = [2, 3, 6]  # USB2.0_CAM1, UGREEN Camera 2K, UGREEN Camera
CAMERA_NAMES = ["USB2.0_CAM1", "UGREEN Camera 2K", "UGREEN Camera"]

def set_permissions():
    """Set camera permissions"""
    for idx in CAMERA_INDEXES:
        os.system(f"sudo chmod 666 /dev/video{idx}")
        print(f"Set permissions for /dev/video{idx}")

def test_single_camera(camera_idx):
    """Test a single camera"""
    print(f"\nTesting camera {camera_idx}...")
    
    cap = cv2.VideoCapture(camera_idx)
    
    if not cap.isOpened():
        print(f"❌ Failed to open camera {camera_idx}")
        return False
    
    print(f"✅ Successfully opened camera {camera_idx}")
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret:
        print(f"❌ Failed to read frame from camera {camera_idx}")
        cap.release()
        return False
    
    print(f"✅ Successfully read frame from camera {camera_idx} - {frame.shape}")
    
    # Show the frame briefly
    cv2.imshow(f"Camera {camera_idx}", frame)
    cv2.waitKey(1000)  # Show for 1 second
    cv2.destroyAllWindows()
    
    cap.release()
    return True

def test_all_cameras():
    """Test all cameras"""
    print("Testing all cameras...")
    set_permissions()
    
    working_cameras = []
    
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        if test_single_camera(camera_idx):
            working_cameras.append((camera_idx, CAMERA_NAMES[i]))
    
    print(f"\n📊 Results:")
    print(f"Working cameras: {len(working_cameras)}/{len(CAMERA_INDEXES)}")
    
    for camera_idx, name in working_cameras:
        print(f"  ✅ Camera {camera_idx}: {name}")
    
    if len(working_cameras) == 0:
        print("❌ No cameras working! Check connections and permissions.")
        return False
    
    return working_cameras

def interactive_test():
    """Interactive test of working cameras"""
    working_cameras = test_all_cameras()
    
    if not working_cameras:
        return
    
    print(f"\nStarting interactive test with {len(working_cameras)} cameras...")
    print("Press 'q' to quit, 'n' to cycle through cameras")
    
    caps = []
    for camera_idx, _ in working_cameras:
        cap = cv2.VideoCapture(camera_idx)
        caps.append(cap)
    
    current_camera = 0
    
    while True:
        if current_camera >= len(caps):
            current_camera = 0
        
        cap = caps[current_camera]
        camera_idx, name = working_cameras[current_camera]
        
        ret, frame = cap.read()
        if ret:
            cv2.putText(frame, f"Camera {camera_idx}: {name}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Camera Test", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            current_camera = (current_camera + 1) % len(caps)
            print(f"Switching to camera {working_cameras[current_camera][0]}")
    
    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        test_all_cameras()