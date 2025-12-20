#!/usr/bin/env python3
"""
Simple camera detection and test script for ChessArm
Run this first to see which cameras are available
"""

import cv2
import time

def test_camera(index):
    """Test a single camera index"""
    print(f"\nTesting camera {index}...")
    
    cap = cv2.VideoCapture(index)
    
    if not cap.isOpened():
        print(f"  ❌ Cannot open camera {index}")
        return False
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret:
        print(f"  ❌ Camera {index} opens but cannot read frames")
        cap.release()
        return False
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"  ✅ Camera {index} working!")
    print(f"     Resolution: {width}x{height}")
    print(f"     FPS: {fps}")
    
    # Show a preview window for 2 seconds
    cv2.imshow(f"Camera {index}", frame)
    cv2.waitKey(2000)
    cv2.destroyWindow(f"Camera {index}")
    
    cap.release()
    return True

def main():
    print("ChessArm Camera Detection Tool")
    print("=" * 40)
    
    working_cameras = []
    
    # Test cameras 0-10
    for i in range(11):
        if test_camera(i):
            working_cameras.append(i)
    
    print(f"\n🎥 Working cameras found: {working_cameras}")
    
    if working_cameras:
        print("\nYou can use these camera indices in your CAMERA_INDEXES list:")
        print(f"CAMERA_INDEXES = {working_cameras[:3]}  # Use first 3 cameras")
    else:
        print("\n❌ No working cameras found!")
        print("Check:")
        print("1. Are cameras connected?")
        print("2. Run: sudo chmod 666 /dev/video*")
        print("3. Try unplugging and reconnecting cameras")

if __name__ == "__main__":
    main()