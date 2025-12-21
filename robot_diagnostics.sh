#!/bin/bash
# Robot diagnostics and fix script for SO101 arm communication issues

echo "🔧 SO101 Robot Arm Diagnostics"
echo "=" * 50

# Check if robot is connected
echo "📡 Checking robot connection..."
if [ -e "/dev/ttyACM1" ]; then
    echo "✅ Robot device found at /dev/ttyACM1"
    ls -la /dev/ttyACM1
else
    echo "❌ Robot device NOT found at /dev/ttyACM1"
    echo "Available USB devices:"
    ls -la /dev/ttyACM* 2>/dev/null || echo "No ttyACM devices found"
    ls -la /dev/ttyUSB* 2>/dev/null || echo "No ttyUSB devices found"
fi

echo ""
echo "🔌 Checking USB connections..."
lsusb | grep -i "serial\|arduino\|arm\|robot" || echo "No obvious robot devices in USB list"

echo ""
echo "⚡ Checking robot power and communication..."
if [ -e "/dev/ttyACM1" ]; then
    # Check if device is accessible
    timeout 5 cat /dev/ttyACM1 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Robot communication port is accessible"
    else
        echo "⚠️  Robot communication port may be busy or have issues"
    fi
    
    # Check permissions
    if [ -r "/dev/ttyACM1" ] && [ -w "/dev/ttyACM1" ]; then
        echo "✅ Robot device permissions OK"
    else
        echo "❌ Robot device permission issues - try:"
        echo "   sudo chmod 666 /dev/ttyACM1"
        echo "   OR add user to dialout group:"
        echo "   sudo usermod -a -G dialout $USER"
    fi
fi

echo ""
echo "🔄 Robot troubleshooting suggestions:"
echo "1. Power cycle the robot arm (turn off/on)"
echo "2. Unplug and reconnect USB cable"
echo "3. Check if another program is using the robot"
echo "4. Try different USB port"
echo "5. Restart the system if needed"

echo ""
echo "🧪 Testing LeRobot connection..."
timeout 10 lerobot-find-cameras opencv 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ LeRobot camera detection works"
else
    echo "⚠️  LeRobot camera detection may have issues"
fi

echo ""
echo "📋 Current processes using robot/cameras:"
lsof /dev/ttyACM* 2>/dev/null || echo "No processes found using robot device"
lsof /dev/video* 2>/dev/null | head -10 || echo "No processes found using cameras"

echo ""
echo "🔧 To fix robot communication errors, try:"
echo "1. Run: sudo systemctl stop ModemManager (if present)"  
echo "2. Run: sudo chmod 666 /dev/ttyACM1"
echo "3. Physically reset the robot arm"
echo "4. Check robot arm power supply"