# Local AI Agent - Floating Desktop Application

A beautiful, floating desktop AI assistant inspired by Cluely's design, featuring transparent glass morphism UI and MCP (Model Context Protocol) server integration for desktop automation and computer vision.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Linux Desktop Environment** (tested on Ubuntu/GNOME)
- **Ollama** (for local AI models)

### 🖥️ Command Line Interface

#### 1. Start MCP Servers

```bash
cd /home/vic/Documents/CODE/local-ai-agent

# Start all MCP servers (filesystem, desktop, system)
./scripts/start_all_mcp_servers.sh
```

#### 2. Run Terminal Bridge

```bash
# Start the terminal chat bridge
python3 simple_terminal_bridge.py
```

The terminal bridge provides:
- WebSocket endpoint: `ws://localhost:8090/ws`
- Direct chat interface in terminal
- MCP command integration (`/mcp`, `/status`, `/help`)

#### 3. Available Commands

```bash
# MCP Commands
/mcp desktop take_screenshot    # Take and save screenshot
/status                        # Show system status
/help                          # Show help

# Direct queries
hello                          # Chat with AI
what are my pc specs          # Get system information
```

### 🎨 Floating Desktop App (Electron)

#### 1. Install Dependencies

```bash
cd src/agent/ui/frontend

# Install Node.js dependencies
npm install
```

#### 2. Build the React App

```bash
# Build production React app
npm run build
```

#### 3. Start the Floating Desktop App

```bash
# Launch Electron floating window
npm run electron
```

#### 4. Desktop App Features

- **🎯 Floating Window**: Always-on-top transparent window
- **⌨️ Global Shortcuts**:
  - `Ctrl+B`: Toggle window visibility
  - `Ctrl+H`: Hide window
  - `Ctrl+Arrow Keys`: Move window
  - `Ctrl+N`: New chat
- **🎨 UI Design**: Cluely-inspired dark glass morphism
- **📸 Screenshots**: Save to Desktop/Pictures folder
- **🔌 MCP Integration**: Desktop automation capabilities

## 🛠️ Development

### React Development Server

```bash
cd src/agent/ui/frontend

# Start development server (port 3002)
PORT=3002 npm start
```

### Electron Development

```bash
# Development mode with DevTools
ELECTRON_IS_DEV=true npm run electron
```

### Building for Distribution

```bash
# Build React + Electron app
npm run build-electron

# Create distributable packages
npm run dist
```

## 📁 Project Structure

```
local-ai-agent/
├── README.md                           # This file
├── simple_terminal_bridge.py           # Terminal chat bridge
├── scripts/
│   └── start_all_mcp_servers.sh       # MCP server startup script
├── src/agent/ui/frontend/              # Electron app
│   ├── main.js                        # Electron main process
│   ├── preload.js                     # IPC bridge
│   ├── src/
│   │   ├── App.js                     # React floating UI
│   │   └── hooks/useAgentWebSocket.js # WebSocket connection
│   └── build/                         # Built React app
├── mcp-servers/                        # MCP server implementations
│   ├── desktop/                       # Desktop automation
│   ├── filesystem/                    # File operations
│   └── system/                        # System monitoring
└── docs/                              # Documentation
```

## 🔧 Configuration

### MCP Server Ports

- **8765**: Filesystem server
- **8766**: Desktop server  
- **8767**: System server
- **8090**: Terminal bridge WebSocket

### Window Settings

Default floating window:
- **Size**: 450x600 pixels (min: 350x400, max: 800x700)
- **Position**: Right side of screen (70% from left, 50px from top)
- **Transparency**: Yes, with backdrop blur
- **Always on top**: Yes

## 🐛 Troubleshooting

### Common Issues

1. **MCP Servers not starting**
   ```bash
   # Check if ports are available
   netstat -tulpn | grep -E "(8765|8766|8767)"
   
   # Kill conflicting processes
   sudo fuser -k 8765/tcp 8766/tcp 8767/tcp
   ```

2. **Electron window not showing**
   ```bash
   # Check if Electron process is running
   ps aux | grep electron
   
   # Try global shortcut
   Ctrl+B  # Toggle window
   ```

3. **Screenshots not saving**
   ```bash
   # Install gnome-screenshot
   sudo apt install gnome-screenshot
   
   # Check desktop directory permissions
   ls -la ~/Desktop
   ```

4. **WebSocket connection failed**
   ```bash
   # Restart terminal bridge
   pkill -f simple_terminal_bridge
   python3 simple_terminal_bridge.py
   ```

### Debug Mode

```bash
# Enable Electron DevTools
ELECTRON_IS_DEV=true npm run electron

# Check React console errors
# Press F12 in Electron window
```

## 🔒 Security

The app includes:
- Content Security Policy for Electron
- Local-only connections (no external API calls)
- File system access controls
- Secure IPC communication

## 📝 Recent Updates

- ✅ Fixed TailwindCSS compilation issues
- ✅ Implemented Cluely-inspired floating UI design
- ✅ Added proper glass morphism effects
- ✅ Fixed screenshot save location (Desktop/Pictures)
- ✅ Disabled auto-opening DevTools
- ✅ Added Content Security Policy
- ✅ Improved terminal bridge responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.