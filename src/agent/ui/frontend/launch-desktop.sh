#!/bin/bash

echo "🚀 Launching Local AI Agent Desktop Application"
echo "==============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to cleanup background processes
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Local AI Agent...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Backend server stopped${NC}"
    fi
    echo -e "${GREEN}🎯 Desktop application closed${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: Please run this script from the frontend directory${NC}"
    echo "   cd /home/vic/Documents/CODE/local-ai-agent/src/agent/ui/frontend"
    exit 1
fi

# Check dependencies
echo -e "${BLUE}1️⃣ Checking system requirements...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
    npm install
fi

echo -e "${GREEN}✅ System requirements satisfied${NC}"
echo ""

# Choose backend mode
echo -e "${BLUE}2️⃣ Select AI Agent Backend Mode:${NC}"
echo "   [1] Simple Test Mode (Mock AI for UI testing)"
echo "   [2] Full AI Agent Mode (Complete local + cloud AI system)"
echo "   [3] Development Mode (React dev server + Electron)"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo -e "${BLUE}🔄 Starting Simple Test Mode...${NC}"
        cd ../../../..
        python3 simple_ui_test.py &
        BACKEND_PID=$!
        cd src/agent/ui/frontend
        ;;
    2)
        echo -e "${BLUE}🧠 Starting Full AI Agent Mode...${NC}"
        cd ../../../..
        # Check if the full agent can be started
        if [ -f "src/agent/ui/webapp.py" ]; then
            python3 -m src.agent.ui.webapp &
            BACKEND_PID=$!
        else
            echo -e "${YELLOW}⚠️  Full agent not available, falling back to test mode${NC}"
            python3 simple_ui_test.py &
            BACKEND_PID=$!
        fi
        cd src/agent/ui/frontend
        ;;
    3)
        echo -e "${BLUE}🛠️ Starting Development Mode...${NC}"
        cd ../../../..
        python3 simple_ui_test.py &
        BACKEND_PID=$!
        cd src/agent/ui/frontend
        sleep 3
        echo -e "${BLUE}Starting React development server...${NC}"
        npm start &
        REACT_PID=$!
        sleep 5
        echo -e "${BLUE}Launching Electron in development mode...${NC}"
        ELECTRON_IS_DEV=true npm run electron
        kill $REACT_PID 2>/dev/null
        cleanup
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Wait for backend to start
echo -e "${YELLOW}⏳ Waiting for AI Agent backend to initialize...${NC}"
sleep 3

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AI Agent backend is running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Failed to start AI Agent backend${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}3️⃣ Building React application...${NC}"
npm run build > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ React application built successfully${NC}"
else
    echo -e "${RED}❌ React build failed${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo -e "${BLUE}4️⃣ Launching Desktop Application...${NC}"
echo ""
echo -e "${GREEN}🎯 Local AI Agent Desktop - Ready!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}💡 Features:${NC}"
echo "   • AI Command Interface with natural language processing"
echo "   • System Dashboard with real-time agent status"
echo "   • Intelligent model routing (Local + Cloud AI)"
echo "   • Desktop automation and MCP integration"
echo "   • Always-on system tray presence"
echo ""
echo -e "${BLUE}🎮 Controls:${NC}"
echo "   • Ctrl+N: New chat session"
echo "   • Ctrl+H: Hide to system tray"
echo "   • Ctrl+Q: Quit application"
echo ""
echo -e "${YELLOW}🔗 Backend: http://localhost:8080${NC}"
echo -e "${YELLOW}📱 WebSocket: ws://localhost:8080/ws${NC}"
echo ""

# Launch Electron
npm run electron

# Cleanup when Electron closes
cleanup