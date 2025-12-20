import cv2

cap = cv2.VideoCapture(4)  # Try index 4 (for /dev/video4)
if cap.isOpened():
    print("Camera 4 is working!")
else:
    print("Failed to open camera 4")
cap.release()
