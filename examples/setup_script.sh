#!/bin/bash
# Setup script for Local AI Agent

set -e  # Exit on any error

echo "=== Local AI Agent Setup ==="
echo "Setting up your local AI agent with MCP integration"

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

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This setup script is designed for Linux systems"
    exit 1
fi

print_status "Checking system requirements..."

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    print_status "Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    print_warning "Ollama is not installed"
    print_status "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    print_success "Ollama installed"
else
    print_success "Ollama found"
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
print_status "Creating project directories..."
mkdir -p logs
mkdir -p data
mkdir -p temp
mkdir -p backups

# Set up configuration
print_status "Setting up configuration..."
if [ ! -f "config/agent_config.yaml" ]; then
    cat > config/agent_config.yaml << EOF
# Local AI Agent Configuration

agent:
  model: "llama3.1:8b"
  max_context: 4096
  temperature: 0.7
  safe_mode: true
  debug: false

servers:
  filesystem:
    enabled: true
    allowed_paths:
      - "/home/vic/Documents"
      - "/home/vic/Downloads"
      - "/tmp"
    max_file_size: "10MB"
    
  system:
    enabled: true
    safe_mode: true
    allowed_commands:
      - "ls"
      - "ps"
      - "top"
      - "df"
      - "free"
    
  desktop:
    enabled: false  # Requires explicit enabling
    screenshot_dir: "/tmp/screenshots"

security:
  audit_logging: true
  require_confirmation: true
  rate_limits:
    filesystem: 100  # operations per minute
    system: 50
    desktop: 20

logging:
  level: "INFO"
  file: "logs/agent.log"
  max_size: "10MB"
  backup_count: 5

ui:
  interface: "cli"
  show_internal_logs: false
  colors: true
EOF
    print_success "Configuration file created"
else
    print_warning "Configuration file already exists"
fi

# Download and setup Ollama model
print_status "Setting up Ollama model..."

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    print_status "Starting Ollama service..."
    ollama serve &
    sleep 5
fi

# Download the model
if ! ollama list | grep -q "llama3.1:8b"; then
    print_status "Downloading Llama 3.1 8B model (this may take a while)..."
    ollama pull llama3.1:8b
    print_success "Model downloaded"
else
    print_success "Model already available"
fi

# Create a simple test
print_status "Creating test files..."
cat > test_agent.py << EOF
#!/usr/bin/env python3
"""Simple test for the AI agent"""

import sys
import os
sys.path.append('src')

from examples.basic_agent import BasicAIAgent

def test_agent():
    print("Testing AI agent...")
    
    # Create test agent
    agent = BasicAIAgent(allowed_paths=["/tmp"])
    
    # Test basic functionality
    response = agent.chat("Hello, can you help me?")
    print(f"Agent response: {response}")
    
    # Test file operations
    response = agent.chat("List the contents of /tmp directory")
    print(f"Directory listing: {response}")
    
    print("Test completed!")

if __name__ == "__main__":
    test_agent()
EOF

chmod +x test_agent.py

# Create launcher script
print_status "Creating launcher script..."
cat > run_agent.sh << EOF
#!/bin/bash
# Launcher script for Local AI Agent

# Activate virtual environment
source venv/bin/activate

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Run the agent
python3 examples/basic_agent.py
EOF

chmod +x run_agent.sh

# Create systemd service (optional)
print_status "Creating systemd service file..."
cat > local-ai-agent.service << EOF
[Unit]
Description=Local AI Agent
After=network.target

[Service]
Type=simple
User=vic
WorkingDirectory=/home/vic/Documents/CODE/local-ai-agent
ExecStart=/home/vic/Documents/CODE/local-ai-agent/venv/bin/python src/main.py
Restart=always
RestartSec=10
Environment=PATH=/home/vic/Documents/CODE/local-ai-agent/venv/bin
Environment=PYTHONPATH=/home/vic/Documents/CODE/local-ai-agent/src

[Install]
WantedBy=multi-user.target
EOF

print_status "Setup completed successfully!"
echo
echo "=== Next Steps ==="
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo
echo "2. Test the basic agent:"
echo "   python3 test_agent.py"
echo
echo "3. Run the agent:"
echo "   ./run_agent.sh"
echo
echo "4. (Optional) Install as system service:"
echo "   sudo cp local-ai-agent.service /etc/systemd/system/"
echo "   sudo systemctl enable local-ai-agent"
echo "   sudo systemctl start local-ai-agent"
echo
echo "=== Configuration ==="
echo "Edit config/agent_config.yaml to customize settings"
echo
echo "=== Documentation ==="
echo "See docs/ directory for detailed documentation"
echo
print_success "Local AI Agent is ready to use!"