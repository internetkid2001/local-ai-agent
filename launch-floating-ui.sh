#!/bin/bash
# Launch script for Local AI Agent Floating Window System
# This script starts the complete system with beautiful UI

echo "🚀 Starting Local AI Agent Floating Window System"
echo "================================================"

# Check if required dependencies are installed
echo "📦 Checking dependencies..."

# Check Python dependencies
if ! python3 -c "import websockets" 2>/dev/null; then
    echo "❌ websockets not installed. Installing..."
    pip3 install websockets
fi

# Check Node.js dependencies
if [ ! -d "src/agent/ui/frontend/node_modules" ]; then
    echo "❌ Node modules not found. Installing..."
    cd src/agent/ui/frontend
    npm install
    cd -
fi

# Build the React app
echo "🔨 Building React application..."
cd src/agent/ui/frontend
npm run build
cd -

# Start the WebSocket server in background
echo "🌐 Starting WebSocket server..."
python3 simple_terminal_bridge.py &
WEBSOCKET_PID=$!

# Wait for WebSocket server to start
echo "⏳ Waiting for WebSocket server to initialize..."
sleep 2

# Test WebSocket connection
echo "🔌 Testing WebSocket connection..."
python3 -c "
import asyncio
import websockets
import json

async def test_connection():
    try:
        async with websockets.connect('ws://localhost:8090/ws') as websocket:
            print('✅ WebSocket server is ready')
            return True
    except Exception as e:
        print(f'❌ WebSocket connection failed: {e}')
        return False

asyncio.run(test_connection())
"

# Start the Electron app
echo "🪟 Launching Floating Window UI..."
cd src/agent/ui/frontend
npm run electron-dev &
ELECTRON_PID=$!

echo ""
echo "🎉 Local AI Agent Floating Window System is now running!"
echo "================================================"
echo ""
echo "📱 Features available:"
echo "   • Beautiful floating window with glassmorphism design"
echo "   • Real-time AI chat with WebSocket connectivity"
echo "   • Recording state with timer and visual indicators"
echo "   • Quick actions: Screenshot, Status, Help"
echo "   • Show/hide toggle functionality"
echo "   • TypeScript-powered with full type safety"
echo ""
echo "🔧 Controls:"
echo "   • Press Ctrl+C to stop the system"
echo "   • Use the eye icon to show/hide the response area"
echo "   • Click the microphone to start/stop recording"
echo "   • Try commands like /help, /status, /mcp desktop take_screenshot"
echo ""
echo "🌐 Backend: WebSocket server running on ws://localhost:8090/ws"
echo "💻 Frontend: Electron app with React UI"
echo ""

# Wait for user to stop the system
wait

# Cleanup
echo "🧹 Cleaning up..."
kill $WEBSOCKET_PID 2>/dev/null
kill $ELECTRON_PID 2>/dev/null

echo "✅ System stopped successfully"
