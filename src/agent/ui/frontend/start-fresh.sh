#!/bin/bash

echo "🔄 Starting Fresh Local AI Agent Desktop App"
echo "============================================"

# Kill any existing backend processes
echo "🧹 Cleaning up existing processes..."
pkill -f simple_ui_test.py 2>/dev/null
pkill -f electron 2>/dev/null
sleep 2

echo "🔄 Starting backend server..."
cd ../../../..
python3 simple_ui_test.py > /dev/null 2>&1 &
BACKEND_PID=$!

echo "⏳ Waiting for backend to initialize..."
sleep 5

cd src/agent/ui/frontend

echo "📦 Building React application..."
npm run build > /dev/null 2>&1

echo "🖥️ Launching desktop application..."
echo ""
echo "✅ Local AI Agent Desktop - Ready!"
echo "   • AI Command Interface with smart suggestions"
echo "   • System Dashboard with real-time status"
echo "   • Native desktop integration"
echo ""

npm run electron

echo ""
echo "🛑 Desktop app closed. Cleaning up..."
kill $BACKEND_PID 2>/dev/null
echo "✅ Cleanup complete"