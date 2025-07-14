#!/bin/bash

echo "🚀 Launching Full Local AI Agent with MCP Integration"
echo "===================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Local AI Agent MCP System...${NC}"
    
    if [ ! -z "$AGENT_PID" ]; then
        kill $AGENT_PID 2>/dev/null
        echo -e "${GREEN}✅ AI Agent backend stopped${NC}"
    fi
    
    # Stop MCP servers
    echo -e "${BLUE}Stopping MCP servers...${NC}"
    cd ../../../..
    ./scripts/stop_all_mcp_servers.sh > /dev/null 2>&1
    echo -e "${GREEN}✅ MCP servers stopped${NC}"
    
    echo -e "${GREEN}🎯 Complete shutdown successful${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: Please run this script from the frontend directory${NC}"
    echo "   cd /home/vic/Documents/CODE/local-ai-agent/src/agent/ui/frontend"
    exit 1
fi

echo -e "${BLUE}1️⃣ Starting MCP Server Ecosystem...${NC}"
cd ../../../..

# Start all MCP servers
echo "   🔄 Starting filesystem MCP server..."
echo "   🔄 Starting desktop automation MCP server..." 
echo "   🔄 Starting system monitoring MCP server..."

./scripts/start_all_mcp_servers.sh > /dev/null 2>&1

# Wait for MCP servers to initialize
echo -e "${YELLOW}   ⏳ Waiting for MCP servers to initialize...${NC}"
sleep 5

# Check MCP server status
echo -e "${GREEN}   ✅ MCP Server Status:${NC}"
echo "      • Filesystem MCP:     localhost:8765"
echo "      • Desktop Automation: localhost:8766" 
echo "      • System Monitoring:  localhost:8767"

echo ""
echo -e "${BLUE}2️⃣ Starting AI Agent Backend with MCP Integration...${NC}"

# Start the full AI agent backend
python3 -m src.agent.ui.webapp > agent.log 2>&1 &
AGENT_PID=$!

echo -e "${YELLOW}   ⏳ Initializing AI models and MCP connections...${NC}"
sleep 8

# Check if agent is running
if ps -p $AGENT_PID > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ AI Agent backend running (PID: $AGENT_PID)${NC}"
    echo "      • LLM Manager: Local + Cloud models"
    echo "      • Context Manager: Memory and learning"
    echo "      • MCP Integration: All servers connected"
else
    echo -e "${RED}   ❌ Failed to start AI Agent backend${NC}"
    echo "   Check agent.log for details:"
    tail -10 agent.log
    cleanup
fi

echo ""
echo -e "${BLUE}3️⃣ Building Enhanced Desktop Application...${NC}"
cd src/agent/ui/frontend

echo "   📦 Building React app with MCP features..."
npm run build > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ Desktop application built successfully${NC}"
else
    echo -e "${RED}   ❌ Failed to build desktop application${NC}"
    cleanup
fi

echo ""
echo -e "${PURPLE}🎯 Local AI Agent MCP System - Ready!${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🧠 AI Capabilities:${NC}"
echo "   • Local Models: Llama 3.1, Mistral (fast, private)"
echo "   • Cloud Models: Claude Sonnet 4, GPT-4 (advanced reasoning)"
echo "   • Intelligent Routing: Best model selection per task"
echo ""
echo -e "${BLUE}🔧 MCP Automation:${NC}"
echo "   • File Operations: Search, organize, backup with AI intelligence"
echo "   • Desktop Control: Screenshots, window management, UI automation"
echo "   • System Monitoring: Resource tracking, process management"
echo ""
echo -e "${BLUE}🖥️ Desktop Features:${NC}"
echo "   • Natural Language Commands with smart suggestions"
echo "   • Real-time System Dashboard with MCP server status"
echo "   • Multiple AI modes: Automation, Analysis, Chat"
echo "   • System tray integration with global shortcuts"
echo ""
echo -e "${BLUE}🎮 Command Examples:${NC}"
echo "   • 'Take a screenshot and organize my desktop files'"
echo "   • 'Monitor CPU usage and alert if it goes above 80%'"
echo "   • 'Find all Python projects and create documentation'"
echo "   • 'Analyze this screen and suggest workflow improvements'"
echo ""
echo -e "${YELLOW}🔗 System Endpoints:${NC}"
echo "   • AI Agent API: http://localhost:8080"
echo "   • WebSocket: ws://localhost:8080/ws"
echo "   • Filesystem MCP: localhost:8765"
echo "   • Desktop MCP: localhost:8766"
echo "   • System MCP: localhost:8767"
echo ""
echo -e "${GREEN}🚀 Launching Desktop Application...${NC}"

# Launch Electron with MCP system
npm run electron

# Cleanup when desktop app closes
cleanup