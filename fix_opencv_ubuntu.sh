#!/bin/bash
# Fix OpenCV GUI support on Ubuntu
# This script installs the necessary dependencies and reinstalls opencv-python

echo "🔧 Fixing OpenCV GUI support on Ubuntu..."
echo ""

# Install GUI dependencies
echo "📦 Installing GUI dependencies..."
sudo apt update
sudo apt install -y libgtk2.0-dev pkg-config

# Optional: Also install additional dependencies that might help
sudo apt install -y libgtk-3-dev libcanberra-gtk-module libcanberra-gtk3-module

echo ""
echo "🐍 Reinstalling OpenCV with GUI support..."

# Uninstall current opencv
pip uninstall -y opencv-python opencv-contrib-python

# Install opencv with full support
pip install opencv-python opencv-contrib-python

echo ""
echo "✅ Installation complete!"
echo ""
echo "🧪 Testing OpenCV GUI support..."
python3 -c "
import cv2
import numpy as np
try:
    # Test window creation
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.namedWindow('Test', cv2.WINDOW_NORMAL)
    cv2.imshow('Test', test_img)
    cv2.waitKey(1)
    cv2.destroyAllWindows()
    print('✅ OpenCV GUI support is working!')
except Exception as e:
    print(f'❌ OpenCV GUI still not working: {e}')
    print('You may need to run: export DISPLAY=:0')
    print('Or install additional packages.')
"

echo ""
echo "🎮 You can now run your ChessArm application:"
echo "python3 testc.py"