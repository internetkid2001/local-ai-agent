#!/bin/bash

echo "🚀 Starting Local AI Agent Desktop Development Environment"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down development environment..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend server stopped"
    fi
    if [ ! -z "$REACT_PID" ]; then
        kill $REACT_PID 2>/dev/null
        echo "✅ React dev server stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "1️⃣ Starting backend server..."
cd ../../..
python3 simple_ui_test.py &
BACKEND_PID=$!
sleep 3

echo "2️⃣ Starting React development server..."
cd src/agent/ui/frontend
npm start &
REACT_PID=$!
sleep 5

echo "3️⃣ Launching Electron desktop app..."
ELECTRON_IS_DEV=true npm run electron

# Wait for background processes
wait