#!/bin/bash

echo "🚀 Quick Launch: Local AI Agent Desktop Application"
echo "=================================================="

# Function to cleanup
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend stopped"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🔄 Starting backend server..."
cd ../../../..
python3 simple_ui_test.py &
BACKEND_PID=$!

echo "⏳ Waiting for backend to start..."
sleep 3

echo "📦 Building React app..."
cd src/agent/ui/frontend
npm run build > /dev/null 2>&1

echo "🖥️ Launching desktop application..."
npm run electron

cleanup