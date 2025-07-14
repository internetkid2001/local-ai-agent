#!/bin/bash
"""
Start All MCP Servers Script

Starts all MCP servers (filesystem, desktop, system) for the local AI agent.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to start an MCP server
start_mcp_server() {
    local name=$1
    local dir=$2
    local port=$3
    local logfile="$PROJECT_DIR/logs/${name}_mcp.log"
    
    print_status "Starting $name MCP server on port $port..."
    
    # Check if port is already in use
    if check_port $port; then
        print_warning "$name MCP server port $port is already in use"
        return 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname "$logfile")"
    
    # Change to server directory
    cd "$dir" || {
        print_error "Cannot change to directory: $dir"
        return 1
    }
    
    # Start server in background
    python3 start_server.py --port $port > "$logfile" 2>&1 &
    local pid=$!
    
    # Wait a moment and check if process is still running
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        print_success "$name MCP server started (PID: $pid)"
        echo $pid > "$PROJECT_DIR/logs/${name}_mcp.pid"
        return 0
    else
        print_error "$name MCP server failed to start"
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting Local AI Agent MCP Servers..."
    echo
    
    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"
    
    # Start filesystem MCP server (port 8765)
    start_mcp_server "filesystem" "$PROJECT_DIR/mcp-servers/filesystem" 8765
    
    # Start desktop automation MCP server (port 8766)
    start_mcp_server "desktop" "$PROJECT_DIR/mcp-servers/desktop" 8766
    
    # Start system monitoring MCP server (port 8767)
    start_mcp_server "system" "$PROJECT_DIR/mcp-servers/system" 8767

    # Start AI Bridge MCP server (port 8005)
    start_mcp_server "ai_bridge" "$PROJECT_DIR/mcp-servers/ai_bridge" 8005
    
    echo
    print_status "MCP Server startup complete!"
    echo
    print_status "Server status:"
    echo "  - Filesystem MCP:     localhost:8765"
    echo "  - Desktop Automation: localhost:8766"
    echo "  - System Monitoring:  localhost:8767"
    echo "  - AI Bridge:          localhost:8005"
    echo
    print_status "Logs are available in: $PROJECT_DIR/logs/"
    print_status "To stop servers, run: $SCRIPT_DIR/stop_all_mcp_servers.sh"
}

# Check dependencies
check_dependencies() {
    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check if required Python packages are installed
    if ! python3 -c "import psutil" 2>/dev/null; then
        print_warning "psutil package not found. Installing..."
        pip3 install psutil
    fi
    
    # Check if lsof is available (for port checking)
    if ! command -v lsof &> /dev/null; then
        print_warning "lsof not found. Port checking may not work properly."
    fi
}

# Trap Ctrl+C
trap 'echo; print_warning "Startup interrupted"; exit 1' INT

# Run dependency check
check_dependencies

# Run main function
main