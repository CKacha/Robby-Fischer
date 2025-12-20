#!/usr/bin/env python3
"""
Chess integration test for ChessArm
Tests Stockfish integration and visual move display
"""

import cv2
import numpy as np
import chess
import chess.engine
import json
import os
import time

# Simple test of Stockfish integration
def test_stockfish():
    """Test basic Stockfish functionality"""
    print("Testing Stockfish...")
    
    try:
        board = chess.Board()
        print(f"Initial board: {board.fen()}")
        
        # Get Stockfish suggestion
        with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
            result = engine.play(board, chess.engine.Limit(time=1.0))
            print(f"Stockfish suggests: {result.move}")
            
            # Make the move and get analysis
            board.push(result.move)
            analysis = engine.analyse(board, chess.engine.Limit(depth=15))
            print(f"After move: {board.fen()}")
            print(f"Analysis: {analysis}")
            
        return True
    except Exception as e:
        print(f"Stockfish test failed: {e}")
        return False

def test_chess_visualization():
    """Test visual chess board with move arrows"""
    print("Testing chess visualization...")
    
    # Create a test board image
    board_size = 800
    img = np.zeros((board_size, board_size, 3), dtype=np.uint8)
    
    # Draw checkerboard pattern
    sq = board_size // 8
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                color = (240, 217, 181)  # Light squares
            else:
                color = (181, 136, 99)   # Dark squares
            
            x1, y1 = c * sq, r * sq
            x2, y2 = x1 + sq, y1 + sq
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
    
    # Add grid lines
    for i in range(1, 8):
        cv2.line(img, (0, i * sq), (board_size, i * sq), (0, 0, 0), 2)
        cv2.line(img, (i * sq, 0), (i * sq, board_size), (0, 0, 0), 2)
    
    # Add square labels
    for r in range(8):
        for c in range(8):
            x1, y1 = c * sq, r * sq
            
            # Chess notation
            file_char = chr(ord('a') + c)
            rank_char = str(8 - r)
            label = f"{file_char}{rank_char}"
            
            cv2.putText(img, label, (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    
    # Test move arrow (e2 to e4)
    def chess_to_coords(square_name):
        file_idx = ord(square_name[0]) - ord('a')
        rank_idx = 8 - int(square_name[1])
        return file_idx, rank_idx
    
    from_c, from_r = chess_to_coords("e2")
    to_c, to_r = chess_to_coords("e4")
    
    from_center = (from_c * sq + sq//2, from_r * sq + sq//2)
    to_center = (to_c * sq + sq//2, to_r * sq + sq//2)
    
    cv2.arrowedLine(img, from_center, to_center, (0, 255, 255), 8, tipLength=0.3)
    cv2.putText(img, "Test move: e2e4", (10, board_size - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    cv2.imshow("Chess Board Test", img)
    print("Press any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def test_occupancy_detection():
    """Test simple occupancy detection logic"""
    print("Testing occupancy detection...")
    
    # Create test images for occupied vs empty squares
    sq_size = 100
    
    # Empty square (light colored)
    empty_square = np.full((sq_size, sq_size, 3), 200, dtype=np.uint8)
    
    # Occupied square (dark piece)
    occupied_square = np.full((sq_size, sq_size, 3), 200, dtype=np.uint8)
    cv2.circle(occupied_square, (sq_size//2, sq_size//2), 30, (50, 50, 50), -1)
    
    def is_occupied(square, threshold=140):
        if square is None or square.size == 0:
            return False
        gray = cv2.cvtColor(square, cv2.COLOR_BGR2GRAY)
        return gray.mean() < threshold
    
    empty_result = is_occupied(empty_square)
    occupied_result = is_occupied(occupied_square)
    
    print(f"Empty square detected as occupied: {empty_result}")
    print(f"Occupied square detected as occupied: {occupied_result}")
    
    # Show test images
    combined = np.hstack([empty_square, occupied_square])
    cv2.putText(combined, f"Empty: {empty_result}", (10, 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(combined, f"Occupied: {occupied_result}", (110, 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    cv2.imshow("Occupancy Test", combined)
    print("Press any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def main():
    """Run all chess integration tests"""
    print("ChessArm Chess Integration Tests")
    print("=" * 40)
    
    # Test 1: Stockfish
    if test_stockfish():
        print("✅ Stockfish test passed\n")
    else:
        print("❌ Stockfish test failed\n")
        return
    
    # Test 2: Chess visualization
    print("Testing chess board visualization...")
    test_chess_visualization()
    print("✅ Visualization test completed\n")
    
    # Test 3: Occupancy detection
    test_occupancy_detection()
    print("✅ Occupancy detection test completed\n")
    
    print("All tests completed!")
    print("\nNext steps:")
    print("1. Run 'python testc.py' to test with real cameras")
    print("2. Press 'S' in the main app to get Stockfish suggestions")
    print("3. Use 'M' to manually input moves for testing")

if __name__ == "__main__":
    main()