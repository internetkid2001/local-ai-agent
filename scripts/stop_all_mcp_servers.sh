#!/bin/bash
"""
Stop All MCP Servers Script

Stops all running MCP servers for the local AI agent.

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

# Function to stop an MCP server
stop_mcp_server() {
    local name=$1
    local pidfile="$PROJECT_DIR/logs/${name}_mcp.pid"
    
    print_status "Stopping $name MCP server..."
    
    if [[ -f "$pidfile" ]]; then
        local pid=$(cat "$pidfile")
        
        if kill -0 $pid 2>/dev/null; then
            # Send SIGTERM first
            kill $pid
            
            # Wait up to 10 seconds for graceful shutdown
            local count=0
            while kill -0 $pid 2>/dev/null && [[ $count -lt 10 ]]; do
                sleep 1
                ((count++))
            done
            
            # If still running, force kill
            if kill -0 $pid 2>/dev/null; then
                print_warning "Force killing $name MCP server (PID: $pid)"
                kill -9 $pid
            fi
            
            print_success "$name MCP server stopped"
        else
            print_warning "$name MCP server was not running (stale PID file)"
        fi
        
        # Remove PID file
        rm -f "$pidfile"
    else
        print_warning "No PID file found for $name MCP server"
    fi
}

# Function to stop servers by port
stop_by_port() {
    local port=$1
    local name=$2
    
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [[ -n "$pids" ]]; then
        print_status "Stopping processes on port $port ($name)..."
        for pid in $pids; do
            kill $pid 2>/dev/null
            print_success "Stopped process $pid on port $port"
        done
    fi
}

# Main execution
main() {
    print_status "Stopping Local AI Agent MCP Servers..."
    echo
    
    # Stop servers by PID files
    stop_mcp_server "filesystem"
    stop_mcp_server "desktop"
    stop_mcp_server "system"
    
    # Also try to stop by port in case PID files are missing
    if command -v lsof &> /dev/null; then
        echo
        print_status "Checking for remaining processes on MCP ports..."
        stop_by_port 8765 "filesystem"
        stop_by_port 8766 "desktop"
        stop_by_port 8767 "system"
    fi
    
    echo
    print_success "MCP Server shutdown complete!"
    
    # Clean up log directory if empty
    if [[ -d "$PROJECT_DIR/logs" ]] && [[ -z "$(ls -A "$PROJECT_DIR/logs")" ]]; then
        rmdir "$PROJECT_DIR/logs"
    fi
}

# Trap Ctrl+C
trap 'echo; print_warning "Shutdown interrupted"; exit 1' INT

# Run main function
main