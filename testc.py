import cv2
import numpy as np
import json
import os
import chess
import chess.engine
import threading
import time

# =========================
# CONFIG
# =========================

CAMERA_INDEXES = [8, 7, 3]  # wrist(8), top(6), side(4) - based on camera.txt
CALIB_FILE = "board_calib_4pt.json"
BOARD_SIZE = 800  # The warped board will be BOARD_SIZE x BOARD_SIZE
OCCUPANCY_THRESHOLD = 120  # Adjusted for better detection - lower = more sensitive
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

def calibrate_piece_colors(rotated_board):
    """
    Calibrate by learning the colors of your specific pieces and board
    """
    print("\nCOLOR CALIBRATION MODE")
    print("This will help the system learn your piece and board colors")
    print("Follow the prompts to click on different squares")
    
    sq = BOARD_SIZE // 8
    board_colors = []
    piece_colors = []
    
    # Sample empty squares first
    print("\nStep 1: Click on 3-4 EMPTY squares of different colors")
    print("Click squares, then press SPACE to continue")
    
    cv2.namedWindow("color_calib", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("color_calib", 800, 800)
    
    clicked_samples = []
    
    def color_mouse_cb(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Find which square was clicked
            c = x // sq
            r = y // sq
            if 0 <= r < 8 and 0 <= c < 8:
                x1, y1 = c * sq, r * sq
                x2, y2 = x1 + sq, y1 + sq
                square_img = rotated_board[y1:y2, x1:x2]
                
                # Get average color of the center area
                center = center_crop(square_img, 0.3)  # Use more of the square
                if center is not None:
                    avg_color = np.mean(center.reshape(-1, 3), axis=0)
                    file_char = chr(ord('a') + c)
                    rank_char = str(8 - r)
                    square_name = f"{file_char}{rank_char}"
                    
                    clicked_samples.append((square_name, avg_color, x, y))
                    print(f"Sampled {square_name}: RGB({avg_color[2]:.1f}, {avg_color[1]:.1f}, {avg_color[0]:.1f})")
    
    cv2.setMouseCallback("color_calib", color_mouse_cb)
    
    # Sample empty squares
    while True:
        display_board = rotated_board.copy()
        
        # Draw grid
        for r in range(1, 8):
            cv2.line(display_board, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 1)
            cv2.line(display_board, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 1)
        
        # Mark clicked squares
        for _, _, x, y in clicked_samples:
            cv2.circle(display_board, (x, y), 10, (0, 255, 0), -1)
        
        cv2.putText(display_board, f"Empty squares sampled: {len(clicked_samples)}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(display_board, "Click empty squares, SPACE when done", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("color_calib", display_board)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') and len(clicked_samples) >= 3:
            break
        elif key == 27:  # ESC
            cv2.destroyWindow("color_calib")
            return None
    
    # Store board colors
    board_colors = [color for _, color, _, _ in clicked_samples]
    
    # Now sample pieces
    print(f"\nStep 2: Click on 3-4 squares with PIECES")
    print("Click squares with pieces, then press SPACE to continue")
    
    clicked_samples = []  # Reset for pieces
    
    while True:
        display_board = rotated_board.copy()
        
        # Draw grid
        for r in range(1, 8):
            cv2.line(display_board, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 1)
            cv2.line(display_board, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 1)
        
        # Mark clicked squares  
        for _, _, x, y in clicked_samples:
            cv2.circle(display_board, (x, y), 10, (0, 0, 255), -1)
        
        cv2.putText(display_board, f"Piece squares sampled: {len(clicked_samples)}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(display_board, "Click squares WITH pieces, SPACE when done", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("color_calib", display_board)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') and len(clicked_samples) >= 3:
            break
        elif key == 27:  # ESC
            cv2.destroyWindow("color_calib")
            return None
    
    # Store piece colors
    piece_colors = [color for _, color, _, _ in clicked_samples]
    
    cv2.destroyWindow("color_calib")
    
    # Calculate average colors and thresholds
    avg_board_color = np.mean(board_colors, axis=0)
    avg_piece_color = np.mean(piece_colors, axis=0)
    
    # Calculate color distance threshold
    color_distances = []
    for piece_color in piece_colors:
        min_dist = min([np.linalg.norm(piece_color - board_color) for board_color in board_colors])
        color_distances.append(min_dist)
    
    # Use 80% of the minimum distance as threshold
    color_threshold = np.mean(color_distances) * 0.8
    
    print(f"\nCalibration Results:")
    print(f"Average board color: RGB({avg_board_color[2]:.1f}, {avg_board_color[1]:.1f}, {avg_board_color[0]:.1f})")
    print(f"Average piece color: RGB({avg_piece_color[2]:.1f}, {avg_piece_color[1]:.1f}, {avg_piece_color[0]:.1f})")
    print(f"Color distance threshold: {color_threshold:.1f}")
    
    # Save calibration
    calib_data = {
        'board_colors': [c.tolist() for c in board_colors],
        'piece_colors': [c.tolist() for c in piece_colors], 
        'avg_board_color': avg_board_color.tolist(),
        'avg_piece_color': avg_piece_color.tolist(),
        'color_threshold': color_threshold
    }
    
    try:
        with open('piece_color_calib.json', 'w') as f:
            json.dump(calib_data, f, indent=2)
        print("Color calibration saved to piece_color_calib.json")
    except Exception as e:
        print(f"Failed to save color calibration: {e}")
    
    return calib_data

def load_piece_color_calibration():
    """Load piece color calibration if available"""
    try:
        with open('piece_color_calib.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading color calibration: {e}")
        return None

def is_occupied_color_based(square, color_calib=None):
    """
    Detect pieces based on color calibration
    """
    if square is None or square.size == 0 or color_calib is None:
        return is_occupied(square)  # Fallback to original method
    
    # Get center area of square
    center = center_crop(square, 0.3)
    if center is None:
        return False
    
    # Get average color
    avg_color = np.mean(center.reshape(-1, 3), axis=0)
    
    # Calculate distance to board colors
    board_colors = [np.array(c) for c in color_calib['board_colors']]
    min_board_distance = min([np.linalg.norm(avg_color - board_color) for board_color in board_colors])
    
    # If distance is greater than threshold, it's likely a piece
    threshold = color_calib['color_threshold']
    is_piece = min_board_distance > threshold
    
    return is_piece

def calibrate_empty_squares(rotated_board):
    """
    Calibrate detection by analyzing empty squares to establish baseline
    """
    print("Calibrating with empty board...")
    print("Please ensure the board is completely empty, then press ENTER")
    input()
    
    sq = BOARD_SIZE // 8
    empty_baselines = {}
    
    for r in range(8):
        for c in range(8):
            x1 = c * sq
            y1 = r * sq
            x2 = x1 + sq
            y2 = y1 + sq
            
            square = rotated_board[y1:y2, x1:x2]
            square_c = center_crop(square, CENTER_MARGIN)
            
            if square_c is not None:
                gray = cv2.cvtColor(square_c, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(square_c, cv2.COLOR_BGR2HSV)
                
                baseline = {
                    'brightness': gray.mean(),
                    'variance': np.var(gray),
                    'saturation': hsv[:,:,1].mean(),
                }
                
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                square_name = f"{file_char}{rank_char}"
                empty_baselines[square_name] = baseline
                
    return empty_baselines

def is_occupied_with_baseline(square, baseline=None, threshold_multiplier=1.5):
    """
    Improved piece detection using baseline comparison
    """
    if square is None or square.size == 0:
        return False
    
    # Convert to different color spaces for analysis
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    
    current_brightness = gray.mean()
    current_variance = np.var(gray)
    current_saturation = hsv[:,:,1].mean()
    
    if baseline is not None:
        # Compare against baseline (empty square)
        brightness_diff = abs(current_brightness - baseline['brightness'])
        variance_diff = abs(current_variance - baseline['variance'])
        saturation_diff = abs(current_saturation - baseline['saturation'])
        
        # Thresholds based on baseline
        brightness_occupied = brightness_diff > (baseline['brightness'] * 0.1)  # 10% change
        variance_occupied = variance_diff > (baseline['variance'] * 0.5)  # 50% change
        saturation_occupied = saturation_diff > 15  # Absolute change
        
        votes = [brightness_occupied, variance_occupied, saturation_occupied]
        return sum(votes) >= 2
    else:
        # Fallback to original method
        return is_occupied(square)

def is_occupied(square):
    """
    Enhanced piece detection optimized for red and white chess pieces
    Red pieces = robot/black, White pieces = human/white
    """
    if square is None or square.size == 0:
        return False
    
    # Convert to different color spaces for analysis
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(square, cv2.COLOR_BGR2LAB)
    
    # Get square dimensions for adaptive analysis
    h, w = square.shape[:2]
    center_crop_sq = square[h//4:3*h//4, w//4:3*w//4]  # Focus on center
    
    if center_crop_sq.size == 0:
        return False
    
    # SPECIFIC RED PIECE DETECTION (for 3D printed red pieces)
    # Red pieces detection in HSV space
    hsv_center = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2HSV)
    hsv_full = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    
    # Red color ranges in HSV (red wraps around 0/180)
    # Expanded ranges for 3D printed red pieces
    # Lower red range (0-15 hue) - more permissive
    red_lower1 = np.array([0, 30, 30])  # Lower saturation/value for darker reds
    red_upper1 = np.array([15, 255, 255])
    # Upper red range (165-180 hue) - more permissive  
    red_lower2 = np.array([165, 30, 30])
    red_upper2 = np.array([180, 255, 255])
    
    red_mask1 = cv2.inRange(hsv_center, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv_center, red_lower2, red_upper2)
    red_mask_center = red_mask1 + red_mask2
    
    # Also check full square for red
    red_mask1_full = cv2.inRange(hsv_full, red_lower1, red_upper1)
    red_mask2_full = cv2.inRange(hsv_full, red_lower2, red_upper2)
    red_mask_full = red_mask1_full + red_mask2_full
    
    red_ratio_center = np.sum(red_mask_center > 0) / red_mask_center.size
    red_ratio_full = np.sum(red_mask_full > 0) / red_mask_full.size
    
    # More permissive thresholds for red detection
    red_piece_detected = red_ratio_center > 0.08 or red_ratio_full > 0.05  # Lower thresholds
    
    # SPECIFIC WHITE PIECE DETECTION
    # White pieces detection - high brightness, low saturation
    center_gray = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2GRAY)
    center_hsv = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2HSV)
    
    # White detection criteria
    avg_brightness = center_gray.mean()
    avg_saturation = center_hsv[:,:,1].mean()
    
    # White pieces should be bright with low saturation
    white_piece_detected = (avg_brightness > 180 and avg_saturation < 50) or avg_brightness > 220
    
    # If we detect specific colored pieces, return True immediately
    if red_piece_detected or white_piece_detected:
        return True
    
    # Method 1: Color variance - pieces should have more color variation
    color_variance = np.var(gray)
    variance_occupied = color_variance > 40  # Lowered threshold
    
    # Method 2: Edge detection - pieces have more defined edges
    edges = cv2.Canny(gray, 20, 80)  # Lower thresholds for better detection
    edge_density = np.sum(edges > 0) / edges.size
    edge_occupied = edge_density > 0.01  # Lowered threshold
    
    # Method 3: Brightness analysis - adaptive to center vs edges
    center_brightness = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2GRAY).mean()
    edge_brightness = gray.mean()
    brightness_diff = abs(center_brightness - edge_brightness)
    
    # If there's significant brightness difference between center and edges, likely a piece
    brightness_occupied = brightness_diff > 10 or center_brightness < OCCUPANCY_THRESHOLD
    
    # Method 4: Color saturation analysis
    saturation = hsv[:,:,1].mean()
    center_saturation = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2HSV)[:,:,1].mean()
    saturation_occupied = saturation > 25 or center_saturation > 35
    
    # Method 5: LAB color space analysis (better for color detection)
    lab_a = lab[:,:,1].mean()  # Green-Red component
    lab_b = lab[:,:,2].mean()  # Blue-Yellow component
    
    # Check if colors deviate significantly from neutral (board colors)
    lab_deviation = abs(lab_a - 128) + abs(lab_b - 128)
    lab_occupied = lab_deviation > 15
    
    # Method 6: Texture analysis using Local Binary Patterns concept
    # Simple texture measure: standard deviation of local differences
    gray_float = gray.astype(np.float32)
    sobel_x = cv2.Sobel(gray_float, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_float, cv2.CV_32F, 0, 1, ksize=3)
    texture_measure = np.sqrt(sobel_x**2 + sobel_y**2).std()
    texture_occupied = texture_measure > 8
    
    # Method 7: Histogram-based analysis
    hist = cv2.calcHist([gray], [0], None, [32], [0, 256])  # Fewer bins for robustness
    hist_normalized = hist / hist.sum()
    hist_entropy = -np.sum(hist_normalized * np.log2(hist_normalized + 1e-10))
    hist_occupied = hist_entropy > 3.0  # Higher entropy suggests more complex content
    
    # Method 8: Color clustering - check for multiple distinct colors
    pixels = square.reshape((-1, 3)).astype(np.float32)
    
    # Simple k-means with k=2 to see if there are distinct color regions
    try:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 2, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS)
        
        # If the two clusters are significantly different, likely a piece
        color_distance = np.linalg.norm(centers[0] - centers[1])
        cluster_occupied = color_distance > 30
    except:
        cluster_occupied = False
    
    # Combine all methods with weighted voting
    methods = [
        (variance_occupied, 1.0),      # Color variance
        (edge_occupied, 1.5),          # Edge detection (higher weight)
        (brightness_occupied, 1.2),    # Brightness analysis
        (saturation_occupied, 1.0),    # Saturation
        (lab_occupied, 1.3),           # LAB color space (higher weight)
        (texture_occupied, 1.1),       # Texture analysis
        (hist_occupied, 0.8),          # Histogram entropy
        (cluster_occupied, 1.4),       # Color clustering (higher weight)
    ]
    
    # Calculate weighted vote
    total_weight = sum(weight for _, weight in methods)
    positive_weight = sum(weight for method, weight in methods if method)
    confidence = positive_weight / total_weight
    
    # Require at least 55% confidence (adjustable)
    is_piece_present = confidence >= 0.55
    
    # Debug output for piece detection (uncomment to tune thresholds)
    # print(f"Red ratio center: {red_ratio_center:.3f}, full: {red_ratio_full:.3f}")
    # print(f"White brightness: {avg_brightness:.1f}, saturation: {avg_saturation:.1f}")
    # print(f"Var:{color_variance:.1f}({variance_occupied}) Edge:{edge_density:.3f}({edge_occupied}) "
    #       f"Bright:{brightness_diff:.1f}({brightness_occupied}) Sat:{saturation:.1f}({saturation_occupied}) "
    #       f"LAB:{lab_deviation:.1f}({lab_occupied}) Texture:{texture_measure:.1f}({texture_occupied}) "
    #       f"Hist:{hist_entropy:.1f}({hist_occupied}) Cluster:{cluster_occupied} "
    #       f"-> Confidence: {confidence:.2f} = {is_piece_present}")
    
    return is_piece_present

def debug_piece_detection(square):
    """
    Debug function to analyze a square and print detailed color information
    """
    if square is None or square.size == 0:
        print("Invalid square")
        return
    
    # Convert to different color spaces
    gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    
    # Get center crop for analysis
    h, w = square.shape[:2]
    center_crop_sq = square[h//4:3*h//4, w//4:3*w//4]
    
    if center_crop_sq.size > 0:
        center_hsv = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2HSV)
        center_gray = cv2.cvtColor(center_crop_sq, cv2.COLOR_BGR2GRAY)
        
        # Red detection
        red_lower1 = np.array([0, 30, 30])
        red_upper1 = np.array([15, 255, 255])
        red_lower2 = np.array([165, 30, 30])
        red_upper2 = np.array([180, 255, 255])
        
        red_mask1 = cv2.inRange(center_hsv, red_lower1, red_upper1)
        red_mask2 = cv2.inRange(center_hsv, red_lower2, red_upper2)
        red_mask = red_mask1 + red_mask2
        red_ratio = np.sum(red_mask > 0) / red_mask.size
        
        # White detection
        avg_brightness = center_gray.mean()
        avg_saturation = center_hsv[:,:,1].mean()
        
        print(f"DEBUG ANALYSIS:")
        print(f"  Average HSV: H={center_hsv[:,:,0].mean():.1f}, S={center_hsv[:,:,1].mean():.1f}, V={center_hsv[:,:,2].mean():.1f}")
        print(f"  Average BGR: B={square[:,:,0].mean():.1f}, G={square[:,:,1].mean():.1f}, R={square[:,:,2].mean():.1f}")
        print(f"  Red ratio: {red_ratio:.3f} (threshold: 0.08)")
        print(f"  White brightness: {avg_brightness:.1f} (threshold: 180)")
        print(f"  White saturation: {avg_saturation:.1f} (threshold: <50)")
        print(f"  RED detected: {red_ratio > 0.08}")
        print(f"  WHITE detected: {(avg_brightness > 180 and avg_saturation < 50) or avg_brightness > 220}")
        print(f"  OCCUPIED: {is_occupied(square)}")
        print("")

def test_piece_detection_on_board(rotated_board):
    """
    Test piece detection on all squares and show results
    """
    print("\n=== PIECE DETECTION TEST ===")
    sq = BOARD_SIZE // 8
    
    for r in range(8):
        row_results = []
        for c in range(8):
            x1 = c * sq
            y1 = r * sq
            x2 = x1 + sq
            y2 = y1 + sq
            
            square = rotated_board[y1:y2, x1:x2]
            square_c = center_crop(square, CENTER_MARGIN)
            
            file_char = chr(ord('a') + c)
            rank_char = str(8 - r)
            square_name = f"{file_char}{rank_char}"
            
            occupied = is_occupied(square_c)
            row_results.append('●' if occupied else '○')
        
        print(f"Rank {8-r}: {' '.join(row_results)}")
    
    print("     a b c d e f g h")
    print("Legend: ● = Occupied, ○ = Empty")
    print("")

def debug_red_piece_detection(rotated_board):
    """
    Interactive debug mode for red piece detection
    Click on squares to see detailed red detection analysis
    """
    print("\n=== RED PIECE DEBUG MODE ===")
    print("Click on squares to analyze red detection")
    print("Press ESC to exit")
    
    sq = BOARD_SIZE // 8
    
    cv2.namedWindow("red_debug", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("red_debug", 800, 800)
    
    def red_debug_mouse_cb(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Find which square was clicked
            c = x // sq
            r = y // sq
            if 0 <= r < 8 and 0 <= c < 8:
                x1, y1 = c * sq, r * sq
                x2, y2 = x1 + sq, y1 + sq
                square_img = rotated_board[y1:y2, x1:x2]
                
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                square_name = f"{file_char}{rank_char}"
                
                print(f"\n--- ANALYZING SQUARE {square_name} ---")
                
                # Get center crop
                center = center_crop(square_img, 0.3)
                if center is not None:
                    # Convert to HSV
                    hsv_square = cv2.cvtColor(square_img, cv2.COLOR_BGR2HSV)
                    hsv_center = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
                    
                    # Red detection ranges
                    red_lower1 = np.array([0, 30, 30])
                    red_upper1 = np.array([15, 255, 255])
                    red_lower2 = np.array([165, 30, 30])
                    red_upper2 = np.array([180, 255, 255])
                    
                    # Test different red ranges
                    red_mask1_center = cv2.inRange(hsv_center, red_lower1, red_upper1)
                    red_mask2_center = cv2.inRange(hsv_center, red_lower2, red_upper2)
                    red_mask_center = red_mask1_center + red_mask2_center
                    
                    red_mask1_full = cv2.inRange(hsv_square, red_lower1, red_upper1)
                    red_mask2_full = cv2.inRange(hsv_square, red_lower2, red_upper2)
                    red_mask_full = red_mask1_full + red_mask2_full
                    
                    red_ratio_center = np.sum(red_mask_center > 0) / red_mask_center.size
                    red_ratio_full = np.sum(red_mask_full > 0) / red_mask_full.size
                    
                    # Average colors
                    avg_hsv_center = np.mean(hsv_center.reshape(-1, 3), axis=0)
                    avg_bgr = np.mean(square_img.reshape(-1, 3), axis=0)
                    
                    print(f"Average BGR: B={avg_bgr[0]:.1f}, G={avg_bgr[1]:.1f}, R={avg_bgr[2]:.1f}")
                    print(f"Average HSV (center): H={avg_hsv_center[0]:.1f}, S={avg_hsv_center[1]:.1f}, V={avg_hsv_center[2]:.1f}")
                    print(f"Red ratio (center): {red_ratio_center:.3f}")
                    print(f"Red ratio (full): {red_ratio_full:.3f}")
                    print(f"Red detected (threshold 0.08): {red_ratio_center > 0.08 or red_ratio_full > 0.05}")
                    print(f"Is occupied: {is_occupied(square_img)}")
                    
                    # Show if this is likely a red piece
                    if avg_bgr[2] > avg_bgr[0] and avg_bgr[2] > avg_bgr[1]:
                        print("✅ BGR analysis suggests RED piece (R > B and R > G)")
                    else:
                        print("❌ BGR analysis does NOT suggest red piece")
                    
                    if 0 <= avg_hsv_center[0] <= 15 or 165 <= avg_hsv_center[0] <= 180:
                        print("✅ HSV Hue suggests RED piece")
                    else:
                        print("❌ HSV Hue does NOT suggest red piece")
    
    cv2.setMouseCallback("red_debug", red_debug_mouse_cb)
    
    while True:
        display_board = rotated_board.copy()
        
        # Draw grid
        for r in range(1, 8):
            cv2.line(display_board, (0, r * sq), (BOARD_SIZE, r * sq), (255, 0, 0), 1)
            cv2.line(display_board, (r * sq, 0), (r * sq, BOARD_SIZE), (255, 0, 0), 1)
        
        # Add instructions
        cv2.putText(display_board, "Click squares to debug red detection", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_board, "ESC to exit", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("red_debug", display_board)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
    
    cv2.destroyWindow("red_debug")
    print("Red debug mode exited")

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

def detect_board_state_color_based(warped_board, color_calib):
    """Convert warped board image to occupancy matrix using color calibration"""
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
            
            occupancy_matrix[r, c] = is_occupied_color_based(square_c, color_calib)
    
    return occupancy_matrix

def detect_move_from_occupancy_change(prev_occupancy, curr_occupancy):
    """Detect chess move by comparing occupancy matrices - handles normal moves and captures"""
    differences = prev_occupancy != curr_occupancy
    
    # Find squares that changed
    changed_squares = []
    for r in range(8):
        for c in range(8):
            if differences[r, c]:
                file_char = chr(ord('a') + c)
                rank_char = str(8 - r)
                square_name = f"{file_char}{rank_char}"
                was_occupied = prev_occupancy[r, c]
                is_occupied = curr_occupancy[r, c]
                changed_squares.append((square_name, was_occupied, is_occupied))
    
    # Count total pieces before and after
    total_before = np.sum(prev_occupancy)
    total_after = np.sum(curr_occupancy)
    piece_difference = total_before - total_after
    
    # Don't print debug info for minor changes (reduces spam)
    if len(changed_squares) <= 3 and abs(piece_difference) <= 2:
        pass  # Only print for significant changes
    else:
        print(f"Debug: {len(changed_squares)} squares changed, pieces: {total_before} -> {total_after} (diff: {piece_difference})")
    
    # Normal move: one square emptied, one filled (2 changes, same piece count)
    if len(changed_squares) == 2 and piece_difference == 0:
        from_square = None
        to_square = None
        
        for square, was_occupied, is_occupied in changed_squares:
            if was_occupied and not is_occupied:  # Square became empty
                from_square = square
            elif not was_occupied and is_occupied:  # Square became occupied
                to_square = square
        
        if from_square and to_square:
            move = f"{from_square}{to_square}"
            print(f"Normal move detected: {move}")
            return move
    
    # Capture: piece count decreased (but allow for detection errors)
    elif piece_difference >= 1 and len(changed_squares) >= 1:
        # Look for squares that became empty (source)
        from_square = None
        to_square = None
        
        # Find the most likely source square (became empty)
        for square, was_occupied, is_occupied in changed_squares:
            if was_occupied and not is_occupied:
                from_square = square
                break
        
        # For captures, find destination square
        # It might be in changed squares, or might be a square that stayed occupied
        for square, was_occupied, is_occupied in changed_squares:
            if not was_occupied and is_occupied:
                to_square = square
                break
        
        # If no clear destination in changed squares, look for occupied squares
        # that could be the destination based on chess logic
        if from_square and not to_square:
            # This is a capture where the destination square detection might be wonky
            # We could try to infer the destination, but for now, let's be conservative
            print(f"Possible capture from {from_square}, but destination unclear")
            return None
        
        if from_square and to_square:
            move = f"{from_square}{to_square}"
            print(f"Capture detected: {move}")
            return move
    
    # Single change that could be part of a move
    elif len(changed_squares) == 1 and abs(piece_difference) <= 1:
        square_name, was_occupied, is_occupied = changed_squares[0]
        
        if not was_occupied and is_occupied:
            # A square became occupied - look for the most likely empty source
            # Check nearby squares first for efficiency
            file_idx = ord(square_name[0]) - ord('a')
            rank_idx = int(square_name[1]) - 1
            
            # Check common move patterns (adjacent squares, diagonals, etc.)
            for r in range(max(0, rank_idx-2), min(8, rank_idx+3)):
                for c in range(max(0, file_idx-2), min(8, file_idx+3)):
                    if prev_occupancy[7-r, c] and not curr_occupancy[7-r, c]:  # Was occupied, now empty
                        file_char = chr(ord('a') + c)
                        rank_char = str(r + 1)
                        potential_from = f"{file_char}{rank_char}"
                        move = f"{potential_from}{square_name}"
                        print(f"Single change move: {move}")
                        return move
    
    # If too many changes or unclear pattern, likely hand movement or detection error
    if len(changed_squares) > 4 or abs(piece_difference) > 3:
        if len(changed_squares) <= 6:  # Don't spam for very large changes
            print(f"Too many changes ({len(changed_squares)} squares, {piece_difference} pieces) - likely hand movement")
        return None
    
    return None

def get_board_occupancy_from_chess_board(board):
    """Generate expected occupancy matrix from current chess board state"""
    occupancy = np.zeros((8, 8), dtype=bool)
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            # Convert chess square to matrix coordinates
            file_idx = chess.square_file(square)  # 0-7 (a-h)
            rank_idx = 7 - chess.square_rank(square)  # 0-7 (8-1, flipped for display)
            occupancy[rank_idx, file_idx] = True
    
    return occupancy

def get_expected_starting_occupancy():
    """Return the occupancy matrix for standard chess starting position"""
    occupancy = np.zeros((8, 8), dtype=bool)
    
    # Rank 1 (white pieces)
    occupancy[7, :] = True  # Bottom row (rank 1)
    # Rank 2 (white pawns)  
    occupancy[6, :] = True  # Second from bottom (rank 2)
    # Rank 7 (black pawns)
    occupancy[1, :] = True  # Second from top (rank 7)
    # Rank 8 (black pieces)
    occupancy[0, :] = True  # Top row (rank 8)
    
    return occupancy

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
    frame_count = 0

    while not stop_capture:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                frame_array[array_idx] = frame.copy()  # Make sure to copy the frame
            frame_count += 1
            
            # Debug: Print status every 60 frames
            if frame_count % 60 == 0:
                print(f"Camera {camera_idx}: {frame_count} frames captured")
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
    
    # Initialize the frames array (local variable)
    local_frames = [None] * len(CAMERA_INDEXES)
    
    # Start the camera capture threads
    threads = []
    for i, camera_idx in enumerate(CAMERA_INDEXES):
        thread = threading.Thread(target=capture_frames, args=(camera_idx, i, local_frames))
        threads.append(thread)
        thread.start()

    # Wait for the threads to initialize
    print("Waiting for cameras to start...")
    time.sleep(3)  # Give cameras more time to initialize

    # Load calibration or calibrate
    if os.path.exists(CALIB_FILE):
        calib = load_calibration()
    else:
        print("No calibration found, using live camera feed for calibration...")
        # Use the threaded frames for calibration to avoid camera conflicts
        calib = calibrate_with_frame_source(local_frames, "frames")
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
    print("Controls:")
    print("  S = Get Stockfish suggestion")
    print("  M = Make manual move")
    print("  D = Toggle automatic move detection") 
    print("  A = Get suggested move for human")
    print("  C = Confirm move after executing it")
    print("  K = Confirm capture (if detection missed it)")
    print("  N = New game")
    print("  R = Recalibrate board position")
    print("  T = Tune piece detection thresholds")
    print("  P = Calibrate piece colors")
    print("  B = Test piece detection on board")
    print("  X = Debug red piece detection")
    print("  Q = Quit")
    print("")
    print("WORKFLOW:")
    print("1. First time setup: Press 'P' to calibrate piece/board colors")
    print("2. Press 'S' to get Stockfish suggestion")
    print("3. Make the move on the physical board")
    print("4. Press 'D' to enable move detection OR 'C' to confirm manually")
    print("5. Robot will analyze and make its move")
    print("")
    print("CALIBRATION:")
    print("- If pieces aren't detected, press 'P' to calibrate colors")
    print("- Set up the starting position first, then press 'P'")
    print("- Click empty squares first, then squares with pieces")
    print("- If still having issues, press 'T' to tune thresholds")
    print("")

    # Initialize chess board and state tracking
    current_board = chess.Board()
    last_suggestion = None
    last_analysis = None
    move_counter = 0
    # Track board state for move detection
    previous_occupancy = get_expected_starting_occupancy()
    move_detection_active = False  # Start with detection OFF for debugging
    stable_frame_count = 0
    required_stable_frames = 10  # Reduced for faster response
    
    # Game state tracking
    waiting_for_human_move = True  # Human goes first
    waiting_for_robot_move = False
    last_detected_occupancy = None
    move_just_detected = False
    
    # Anti-spam and stability tracking
    last_large_change_time = 0
    hand_movement_cooldown = 3.0  # Seconds to ignore after large changes
    
    # Load color calibration if available
    color_calib = load_piece_color_calibration()
    if color_calib:
        print("Loaded color calibration from piece_color_calib.json")
    else:
        print("No color calibration found - you can create one with 'P'")
    
    print(f"Game started! Expected starting position:")
    print(f"Human (White) goes first - make your move!")
    print(f"Robot will play as Black")
    print(f"Move detection is OFF - press 'D' to enable it later")

    while True:
        # Lock frames to avoid concurrent access issues
        with frame_lock:
            # Check if any frame is None
            if any(frame is None for frame in local_frames):
                # Show loading message instead of skipping
                loading_img = np.zeros((400, 600, 3), dtype=np.uint8)
                cv2.putText(loading_img, "Loading camera feeds...", (50, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow("analysis", loading_img)
                cv2.waitKey(1)
                continue

            top_view = local_frames[1].copy()
            side_view = local_frames[2].copy()
            wrist_view = local_frames[0].copy()

        # Process the top view for chess detection
        try:
            warped_top = warp_board(top_view, calib["points"])
            rotated_board = rotate_board(warped_top)
            
            # Detect current board occupancy using color calibration if available
            if color_calib:
                occupancy_matrix = detect_board_state_color_based(rotated_board, color_calib)
            else:
                occupancy_matrix = detect_board_state(rotated_board)
        except Exception as e:
            print(f"Error processing board: {e}")
            # Create a simple test board if processing fails
            rotated_board = np.zeros((BOARD_SIZE, BOARD_SIZE, 3), dtype=np.uint8)
            occupancy_matrix = np.zeros((8, 8), dtype=bool)

        # Move detection logic - only detect when board is stable
        detected_move = None
        if move_detection_active and not current_board.is_game_over():
            # Check if current occupancy is different from previous
            if not np.array_equal(occupancy_matrix, previous_occupancy):
                # Count total pieces to filter out hand movements
                total_pieces_before = np.sum(previous_occupancy)
                total_pieces_after = np.sum(occupancy_matrix)
                piece_difference = total_pieces_before - total_pieces_after  # Signed difference
                
                # Check if we're in a hand movement cooldown period
                current_time = time.time()
                if current_time - last_large_change_time < hand_movement_cooldown:
                    if stable_frame_count == 0:  # Only print once
                        print(f"⏳ Ignoring changes during cooldown period ({hand_movement_cooldown - (current_time - last_large_change_time):.1f}s remaining)")
                    stable_frame_count = 0
                    continue
                
                # Detect hand movements - if too many pieces change suddenly
                if abs(piece_difference) > 8 or np.sum(occupancy_matrix != previous_occupancy) > 10:
                    print(f"🖐️ Hand movement detected: {total_pieces_before} -> {total_pieces_after} pieces, ignoring for {hand_movement_cooldown}s")
                    last_large_change_time = current_time
                    stable_frame_count = 0
                    continue
                
                # More permissive filtering for piece count changes
                # Allow larger differences but require stability over multiple frames
                max_allowed_difference = 5  # Increased from 3 to handle detection errors better
                
                if abs(piece_difference) <= max_allowed_difference:
                    # Check if occupancy is consistent with a single move
                    detected_move = detect_move_from_occupancy_change(previous_occupancy, occupancy_matrix)
                    
                    # Also check if any expected move matches the current situation
                    if not detected_move and last_suggestion:
                        # Check if the suggested move could be what happened
                        expected_from = str(last_suggestion)[:2]
                        expected_to = str(last_suggestion)[2:4]
                        
                        # Convert to matrix coordinates
                        from_c = ord(expected_from[0]) - ord('a')
                        from_r = 8 - int(expected_from[1])
                        to_c = ord(expected_to[0]) - ord('a')
                        to_r = 8 - int(expected_to[1])
                        
                        # Check if the from square is now empty and to square is occupied
                        if (previous_occupancy[from_r, from_c] and not occupancy_matrix[from_r, from_c] and
                            occupancy_matrix[to_r, to_c]):
                            detected_move = str(last_suggestion)
                            print(f"📍 Matched expected move: {detected_move}")
                    
                    # Don't wait indefinitely for captures - be more flexible
                    if not detected_move and piece_difference > 0:
                        # Only wait a bit for captures, don't get stuck
                        if stable_frame_count < 5:  # Reduced from longer wait
                            print(f"🔍 Possible capture in progress (lost {piece_difference} pieces), waiting... ({stable_frame_count}/5)")
                            stable_frame_count += 1
                            continue
                        else:
                            print(f"⚠️  Capture detection timeout, ignoring changes")
                            stable_frame_count = 0
                            continue
                        
                else:
                    # Too many pieces changed - likely hand movement
                    # But don't print this constantly, only occasionally
                    if stable_frame_count == 0:  # Only print once per disturbance
                        print(f"⚠️  Large board change detected: {total_pieces_before} -> {total_pieces_after} pieces (likely hand movement)")
                    stable_frame_count = 0
                    continue  # Don't process this as a potential move
                
                if detected_move:
                    stable_frame_count += 1
                    if stable_frame_count >= required_stable_frames:
                        # Move detected! Apply it to the board
                        try:
                            move = chess.Move.from_uci(detected_move)
                            if move in current_board.legal_moves:
                                # Check if this matches expected suggestion (if waiting for robot move)
                                if waiting_for_robot_move and last_suggestion and str(move) == str(last_suggestion):
                                    print(f"✅ Robot move confirmed: {detected_move}")
                                    
                                    # Check if it's a capture
                                    is_capture = current_board.is_capture(move)
                                    if is_capture:
                                        captured_piece = current_board.piece_at(move.to_square)
                                        print(f"🎯 Capture! Robot took {captured_piece}")
                                    
                                    current_board.push(move)
                                    move_counter += 1
                                    
                                    # Clear suggestion since it was implemented
                                    last_suggestion = None
                                    last_analysis = None
                                    
                                    # Update tracking state using actual board position
                                    previous_occupancy = get_board_occupancy_from_chess_board(current_board)
                                    stable_frame_count = 0
                                    
                                    # Switch to waiting for human move
                                    waiting_for_robot_move = False
                                    waiting_for_human_move = True
                                    
                                    print("💭 Waiting for human move...")
                                    
                                elif waiting_for_human_move:
                                    print(f"🎯 Human move detected: {detected_move}")
                                    
                                    # Check if it's a capture
                                    is_capture = current_board.is_capture(move)
                                    if is_capture:
                                        captured_piece = current_board.piece_at(move.to_square)
                                        print(f"🎯 Capture! Human took {captured_piece}")
                                    
                                    current_board.push(move)
                                    move_counter += 1
                                    
                                    # Update tracking state using actual board position
                                    previous_occupancy = get_board_occupancy_from_chess_board(current_board)
                                    stable_frame_count = 0
                                    
                                    # Switch to robot turn - get suggestion immediately
                                    waiting_for_human_move = False
                                    waiting_for_robot_move = True
                                    
                                    # Always get robot suggestion after human move (unless game over)
                                    if not current_board.is_game_over():
                                        print("🤖 Getting robot move...")
                                        robot_move = get_stockfish_move(current_board)
                                        if robot_move:
                                            last_suggestion = robot_move
                                            last_analysis = analyze_position(current_board)
                                            print(f"🤖 Robot suggestion: {robot_move}")
                                            print("Execute this move on the board!")
                                        else:
                                            print("❌ No robot move available")
                                            waiting_for_robot_move = False
                                            waiting_for_human_move = True
                                    else:
                                        print("🎉 Game Over!")
                                        waiting_for_robot_move = False
                                        waiting_for_human_move = False
                                else:
                                    print(f"⚠️  Unexpected move detected: {detected_move}")
                                    if last_suggestion:
                                        print(f"    Expected: {last_suggestion}")
                                    print("    Ignoring unexpected move...")
                                    stable_frame_count = 0
                            else:
                                print(f"❌ Detected illegal move: {detected_move} - ignoring")
                                stable_frame_count = 0
                        except Exception as e:
                            print(f"❌ Invalid move format: {detected_move} - {e} - ignoring")
                            stable_frame_count = 0
                else:
                    stable_frame_count = 0
            else:
                # Board is stable (no changes), reset counter
                stable_frame_count = 0

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
        try:
            top_view_resized = cv2.resize(top_view, (300, 300))
            side_view_resized = cv2.resize(side_view, (300, 300))  
            wrist_view_resized = cv2.resize(wrist_view, (300, 300))

            combined_view = np.hstack((top_view_resized, side_view_resized, wrist_view_resized))
            cv2.imshow("camera views", combined_view)
        except Exception as e:
            print(f"Error displaying camera views: {e}")
            # Create placeholder if camera views fail
            placeholder = np.zeros((300, 900, 3), dtype=np.uint8)
            cv2.putText(placeholder, "Camera Error", (350, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.imshow("camera views", placeholder)
        
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
        
        # Show whose turn it is
        if waiting_for_human_move:
            cv2.putText(analysis_img, "Waiting for HUMAN move", (10, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        elif waiting_for_robot_move:
            cv2.putText(analysis_img, "Execute ROBOT move!", (10, 220), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Show game status
        if current_board.is_checkmate():
            cv2.putText(analysis_img, "CHECKMATE!", (10, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        elif current_board.is_check():
            cv2.putText(analysis_img, "CHECK!", (10, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        elif current_board.is_stalemate():
            cv2.putText(analysis_img, "STALEMATE", (10, 250), 
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
        cv2.putText(analysis_img, "S = Suggestion | M = Manual move", (10, 545), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, "D = Toggle move detect | N = New game", (10, 565), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
        cv2.putText(analysis_img, f"Move detection: {'ON' if move_detection_active else 'OFF'}", 
                   (10, 585), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 
                   (0, 255, 0) if move_detection_active else (255, 0, 0), 1)
        
        cv2.imshow("analysis", analysis_img)

        # Key detection
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            print("\nRecalibrating board position...\n")
            # Use the live threaded frames for recalibration
            calib = calibrate_with_frame_source(local_frames, "frames")
            if calib is None:
                print("Recalibration failed, continuing with old calibration")
        elif key == ord('t'):
            print("\nTuning piece detection thresholds...")
            # Enable debug output for threshold tuning
            print("Analyzing current board state for threshold calibration...")
            sq = BOARD_SIZE // 8
            
            occupied_squares = []
            empty_squares = []
            
            for r in range(8):
                for c in range(8):
                    x1 = c * sq
                    y1 = r * sq
                    x2 = x1 + sq
                    y2 = y1 + sq
                    
                    square = rotated_board[y1:y2, x1:x2]
                    square_c = center_crop(square, CENTER_MARGIN)
                    
                    if square_c is not None:
                        gray = cv2.cvtColor(square_c, cv2.COLOR_BGR2GRAY)
                        hsv = cv2.cvtColor(square_c, cv2.COLOR_BGR2HSV)
                        
                        brightness = gray.mean()
                        variance = np.var(gray)
                        saturation = hsv[:,:,1].mean()
                        
                        edges = cv2.Canny(gray, 30, 100)
                        edge_density = np.sum(edges > 0) / edges.size
                        
                        file_char = chr(ord('a') + c)
                        rank_char = str(8 - r)
                        square_name = f"{file_char}{rank_char}"
                        
                        print(f"{square_name}: Brightness={brightness:.1f}, Variance={variance:.1f}, "
                              f"Edge={edge_density:.3f}, Saturation={saturation:.1f}")
                        
                        # Ask user if this square is occupied
                        user_input = input(f"Is {square_name} occupied? (y/n/skip): ").lower()
                        if user_input == 'y':
                            occupied_squares.append((brightness, variance, edge_density, saturation))
                        elif user_input == 'n':
                            empty_squares.append((brightness, variance, edge_density, saturation))
            
            if occupied_squares and empty_squares:
                print("\nAnalyzing optimal thresholds...")
                # Calculate optimal thresholds
                occ_brightness = [x[0] for x in occupied_squares]
                empty_brightness = [x[0] for x in empty_squares]
                
                optimal_brightness = (max(occ_brightness) + min(empty_brightness)) / 2
                print(f"Suggested OCCUPANCY_THRESHOLD: {optimal_brightness:.1f}")
                print(f"Current threshold: {OCCUPANCY_THRESHOLD}")
                
                # Update threshold
                new_threshold = input(f"Enter new threshold (current={OCCUPANCY_THRESHOLD}): ")
                if new_threshold.strip():
                    try:
                        globals()['OCCUPANCY_THRESHOLD'] = float(new_threshold)
                        print(f"Updated threshold to {OCCUPANCY_THRESHOLD}")
                    except ValueError:
                        print("Invalid threshold value")
        elif key == ord('p'):
            print("\nCalibrating piece colors...")
            print("Set up the board with pieces in starting position first!")
            input("Press ENTER when ready...")
            
            # Use current rotated board for color calibration
            with frame_lock:
                if local_frames[1] is not None:
                    calibration_frame = local_frames[1].copy()
                    warped_calib = warp_board(calibration_frame, calib["points"])
                    rotated_calib = rotate_board(warped_calib)
                    
                    new_color_calib = calibrate_piece_colors(rotated_calib)
                    if new_color_calib:
                        color_calib = new_color_calib
                        print("Color calibration updated!")
                    else:
                        print("Color calibration cancelled")
                else:
                    print("No camera frame available")
        elif key == ord('b'):
            # Test piece detection on current board
            print("\n=== TESTING PIECE DETECTION ===")
            with frame_lock:
                if local_frames[1] is not None:
                    test_frame = local_frames[1].copy()
                    warped_test = warp_board(test_frame, calib["points"])
                    rotated_test = rotate_board(warped_test)
                    
                    test_piece_detection_on_board(rotated_test)
                else:
                    print("No camera frame available")
        elif key == ord('x'):
            # Debug red piece detection
            print("\n=== RED PIECE DEBUG MODE ===")
            with frame_lock:
                if local_frames[1] is not None:
                    debug_frame = local_frames[1].copy()
                    warped_debug = warp_board(debug_frame, calib["points"])
                    rotated_debug = rotate_board(warped_debug)
                    
                    debug_red_piece_detection(rotated_debug)
                else:
                    print("No camera frame available")
        elif key == ord('s'):
            if waiting_for_human_move and not last_suggestion:
                print("\nGetting Stockfish suggestion for human...")
                human_suggestion = get_stockfish_move(current_board)
                if human_suggestion:
                    print(f"Suggested move for human: {human_suggestion}")
                    # Don't set last_suggestion for human moves, just display
                else:
                    print("No suggestion available")
            elif waiting_for_robot_move and not last_suggestion:
                print("\nGetting robot move...")
                robot_move = get_stockfish_move(current_board)
                if robot_move:
                    last_suggestion = robot_move
                    last_analysis = analyze_position(current_board)
                    print(f"Robot move: {robot_move}")
                    print("Execute this move on the board!")
                else:
                    print("No robot move available")
            else:
                if last_suggestion:
                    print(f"Current suggestion: {last_suggestion}")
                else:
                    print("No suggestion needed right now")
        elif key == ord('m'):
            print("\nEnter move (e.g., e2e4): ", end="")
            move_input = input()
            try:
                move = chess.Move.from_uci(move_input)
                if move in current_board.legal_moves:
                    current_board.push(move)
                    move_counter += 1
                    print(f"Move {move_input} played!")
                    
                    # Update expected board state after manual move
                    previous_occupancy = get_board_occupancy_from_chess_board(current_board)
                    
                    # Clear any existing suggestion since we made a manual move
                    last_suggestion = None
                    last_analysis = None
                    
                    # Switch turns based on whose turn it is now
                    if current_board.turn == chess.WHITE:  # Now white's turn (human)
                        waiting_for_human_move = True
                        waiting_for_robot_move = False
                        print("Human's turn")
                    else:  # Now black's turn (robot)
                        waiting_for_human_move = False
                        waiting_for_robot_move = True
                        # Get robot suggestion immediately
                        robot_move = get_stockfish_move(current_board)
                        if robot_move:
                            last_suggestion = robot_move
                            last_analysis = analyze_position(current_board)
                            print(f"Robot move: {robot_move}")
                            print("Execute this move on the board!")
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
            previous_occupancy = get_expected_starting_occupancy()
            waiting_for_human_move = True
            waiting_for_robot_move = False
            move_detection_active = True
            stable_frame_count = 0
            print("Human (White) goes first - make your move!")
        elif key == ord('d'):
            # Toggle move detection
            move_detection_active = not move_detection_active
            print(f"Move detection: {'ON' if move_detection_active else 'OFF'}")
            if move_detection_active:
                print("Move detection enabled - system will automatically detect moves")
            else:
                print("Move detection disabled - use 'M' for manual moves or 'C' to confirm moves")
        elif key == ord('a'):
            # Auto-play mode: get Stockfish suggestion and execute
            if current_board.turn:  # White's turn
                print("Getting human move suggestion...")
                suggested_move = get_stockfish_move(current_board)
                if suggested_move:
                    print(f"Suggested move for human: {suggested_move}")
                    print("Execute this move on the board, then press 'c' to confirm")
                    last_suggestion = suggested_move
        elif key == ord('k'):
            # Confirm capture - useful when detection doesn't catch captures properly
            if last_suggestion:
                move = chess.Move.from_uci(str(last_suggestion))
                if move in current_board.legal_moves:
                    is_capture = current_board.is_capture(move)
                    if is_capture:
                        captured_piece = current_board.piece_at(move.to_square)
                        print(f"🎯 Capture confirmed! Took {captured_piece}")
                    else:
                        print(f"📍 Move confirmed: {last_suggestion}")
                    
                    current_board.push(move)
                    move_counter += 1
                    
                    # Update expected board state
                    previous_occupancy = get_board_occupancy_from_chess_board(current_board)
                    
                    # Clear the suggestion since it's been executed
                    last_suggestion = None
                    last_analysis = None
                    
                    # Switch turns based on whose turn it is now
                    if current_board.turn == chess.WHITE:  # Now white's turn (human)
                        waiting_for_human_move = True
                        waiting_for_robot_move = False
                        print("Human's turn")
                    else:  # Now black's turn (robot)
                        waiting_for_human_move = False
                        waiting_for_robot_move = True
                        # Get robot suggestion immediately
                        if not current_board.is_game_over():
                            robot_move = get_stockfish_move(current_board)
                            if robot_move:
                                last_suggestion = robot_move
                                last_analysis = analyze_position(current_board)
                                print(f"Robot move: {robot_move}")
                                print("Execute this move on the board!")
                        else:
                            print("🎉 Game Over!")
                else:
                    print("Invalid suggested move!")
            else:
                print("No move to confirm")
        elif key == ord('c'):
            # Confirm that a suggested move has been executed
            if last_suggestion:
                print(f"Confirming move: {last_suggestion}")
                current_board.push(last_suggestion)
                move_counter += 1
                
                # Update expected board state
                previous_occupancy = get_board_occupancy_from_chess_board(current_board)
                
                # Clear the suggestion since it's been executed
                last_suggestion = None
                last_analysis = None
                
                # Switch turns based on whose turn it is now
                if current_board.turn == chess.WHITE:  # Now white's turn (human)
                    waiting_for_human_move = True
                    waiting_for_robot_move = False
                    print("Human's turn")
                else:  # Now black's turn (robot)
                    waiting_for_human_move = False
                    waiting_for_robot_move = True
                    # Get robot suggestion immediately
                    if not current_board.is_game_over():
                        robot_move = get_stockfish_move(current_board)
                        if robot_move:
                            last_suggestion = robot_move
                            last_analysis = analyze_position(current_board)
                            print(f"Robot move: {robot_move}")
                            print("Execute this move on the board!")
                    else:
                        print("🎉 Game Over!")
            else:
                print("No move to confirm")

    # Stop capture threads
    stop_capture = True
    
    # Release all camera objects
    for thread in threads:
        thread.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
