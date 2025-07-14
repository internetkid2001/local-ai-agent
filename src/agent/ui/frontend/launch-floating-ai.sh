#!/bin/bash

# Launch Floating AI Agent Desktop Application
# This script starts the MCP servers and launches the Electron app

echo "🚀 Starting Local AI Agent - Floating Desktop App"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: package.json not found. Please run this script from the frontend directory.${NC}"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start MCP servers
start_mcp_servers() {
    echo -e "${BLUE}📡 Starting MCP servers...${NC}"
    
    # Navigate to project root
    cd ../../../../..
    
    # Start MCP servers using the existing script
    if [ -f "scripts/start_all_mcp_servers.sh" ]; then
        echo -e "${YELLOW}Starting MCP servers with existing script...${NC}"
        ./scripts/start_all_mcp_servers.sh &
        sleep 3
    else
        echo -e "${YELLOW}Starting MCP servers individually...${NC}"
        
        # Start each MCP server
        cd mcp-servers/filesystem && python3 start_server.py &
        cd ../desktop && python3 start_server.py &
        cd ../system && python3 start_server.py &
        cd ../ai_bridge && python3 start_server.py &
        cd ../../
        
        sleep 5
    fi
    
    # Check if servers are running
    echo -e "${BLUE}🔍 Checking MCP server status...${NC}"
    
    if check_port 8765; then
        echo -e "${GREEN}✅ Filesystem MCP Server (8765) - Running${NC}"
    else
        echo -e "${RED}❌ Filesystem MCP Server (8765) - Not running${NC}"
    fi
    
    if check_port 8766; then
        echo -e "${GREEN}✅ Desktop MCP Server (8766) - Running${NC}"
    else
        echo -e "${RED}❌ Desktop MCP Server (8766) - Not running${NC}"
    fi
    
    if check_port 8767; then
        echo -e "${GREEN}✅ System MCP Server (8767) - Running${NC}"
    else
        echo -e "${RED}❌ System MCP Server (8767) - Not running${NC}"
    fi
    
    if check_port 8005; then
        echo -e "${GREEN}✅ AI Bridge MCP Server (8005) - Running${NC}"
    else
        echo -e "${RED}❌ AI Bridge MCP Server (8005) - Not running${NC}"
    fi
    
    # Return to frontend directory
    cd src/agent/ui/frontend
}

# Function to start the backend API
start_backend() {
    echo -e "${BLUE}🔧 Starting Backend API...${NC}"
    
    # Navigate to project root and start the API
    cd ../../../../..
    
    # Check if simple_web.py exists and start it
    if [ -f "simple_web.py" ]; then
        echo -e "${YELLOW}Starting simple web backend...${NC}"
        python3 simple_web.py &
        BACKEND_PID=$!
        sleep 2
    else
        echo -e "${YELLOW}Starting enterprise API backend...${NC}"
        python3 -m src.agent.api.main &
        BACKEND_PID=$!
        sleep 2
    fi
    
    # Check if backend is running
    if check_port 8080; then
        echo -e "${GREEN}✅ Backend API (8080) - Running${NC}"
    elif check_port 8000; then
        echo -e "${GREEN}✅ Backend API (8000) - Running${NC}"
    else
        echo -e "${RED}❌ Backend API - Not running${NC}"
    fi
    
    # Return to frontend directory
    cd src/agent/ui/frontend
}

# Function to build and start Electron app
start_electron() {
    echo -e "${BLUE}🖥️  Building and starting Electron app...${NC}"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing dependencies...${NC}"
        npm install
    fi
    
    # Build the React app
    echo -e "${YELLOW}🔨 Building React application...${NC}"
    npm run build
    
    # Start Electron
    echo -e "${GREEN}🚀 Launching floating AI assistant...${NC}"
    npm run electron
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up processes...${NC}"
    
    # Kill backend if we started it
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Kill MCP servers
    pkill -f "mcp.*server" 2>/dev/null
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
    exit 0
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Main execution
echo -e "${BLUE}🔄 Step 1: Starting MCP servers...${NC}"
start_mcp_servers

echo -e "${BLUE}🔄 Step 2: Starting backend API...${NC}"
start_backend

echo -e "${BLUE}🔄 Step 3: Launching desktop application...${NC}"
start_electron

# Keep script running
echo -e "${GREEN}🎉 Local AI Agent is now running!${NC}"
echo -e "${YELLOW}📱 Use Ctrl+B to toggle the floating window${NC}"
echo -e "${YELLOW}📱 Use Ctrl+H to hide the window${NC}"
echo -e "${YELLOW}📱 Use Ctrl+Arrow keys to move the window${NC}"
echo -e "${YELLOW}❌ Press Ctrl+C to stop all services${NC}"

# Wait for user to stop
wait