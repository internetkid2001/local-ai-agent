#!/bin/bash

echo "🧪 Testing Electron App"
echo "======================"

# Kill any existing processes
echo "🧹 Cleaning up..."
pkill -f electron 2>/dev/null || true
pkill -f simple_ui_test.py 2>/dev/null || true
sleep 2

# Start backend
echo "🔄 Starting backend..."
cd ../../../..
python3 simple_ui_test.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend
echo "⏳ Waiting for backend..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Backend is responding"
else
    echo "❌ Backend not responding"
    cat backend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

cd src/agent/ui/frontend

# Build app
echo "📦 Building React app..."
npm run build > build.log 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    cat build.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Test Electron launch
echo "🖥️ Testing Electron launch..."
echo "   Note: If you see the app window, the test is successful!"
echo "   Close the app window to complete the test."

npm run electron 2> electron.log &
ELECTRON_PID=$!

# Wait a bit for Electron to start
sleep 10

# Check if Electron is still running
if ps -p $ELECTRON_PID > /dev/null 2>&1; then
    echo "✅ Electron app launched successfully!"
    echo "   Waiting for you to close the app..."
    wait $ELECTRON_PID
else
    echo "❌ Electron app failed to start"
    cat electron.log
fi

# Cleanup
echo "🧹 Cleaning up..."
kill $BACKEND_PID 2>/dev/null || true
echo "✅ Test complete"