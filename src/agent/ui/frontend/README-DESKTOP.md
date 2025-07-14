# Local AI Agent - Desktop Application

A powerful desktop AI assistant built with React and Electron, featuring a modern glassmorphism design and real-time chat capabilities.

## 🚀 Features

- **Modern UI**: Glassmorphism design with smooth animations
- **Desktop Native**: System tray integration, native menus, and keyboard shortcuts
- **Real-time Chat**: WebSocket-based streaming responses
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Always on Top**: Optional always-on-top mode for quick access
- **Minimize to Tray**: Keep the app running in the background

## 📦 Quick Start

### Development Mode
```bash
# Start development environment (backend + frontend + Electron)
./start-dev.sh
```

### Production Build
```bash
# Build desktop application for distribution
./build-desktop.sh
```

### Manual Development Steps
```bash
# 1. Start the backend server
cd ../../..
python3 simple_ui_test.py

# 2. Build React app
npm run build

# 3. Launch Electron app
npm run electron
```

## 🛠️ Available Scripts

- `npm start` - Start React development server
- `npm run build` - Build React app for production
- `npm run electron` - Launch Electron app (production mode)
- `npm run electron-dev` - Launch Electron app (development mode)
- `npm run dist` - Build distributable packages
- `npm run dist-all` - Build for all platforms (Windows, macOS, Linux)

## 🎯 Desktop-Specific Features

### System Tray
- Minimize to system tray instead of closing
- Right-click tray icon for context menu
- Click tray icon to show/hide window

### Keyboard Shortcuts
- `Ctrl+N` (or `Cmd+N` on macOS) - New chat session
- `Ctrl+H` (or `Cmd+H` on macOS) - Hide to tray
- `Ctrl+Q` (or `Cmd+Q` on macOS) - Quit application

### Window Features
- Resizable window with minimum size constraints
- Always on top mode (via Window menu)
- Fullscreen chat mode for distraction-free conversations
- Native window controls and menus

## 📁 Project Structure

```
frontend/
├── main.js              # Electron main process
├── preload.js           # Secure IPC bridge
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── DesktopChatContainer.js  # Desktop-optimized chat UI
│   │   │   ├── MessageList.js           # Message display
│   │   │   ├── MessageInput.js          # Input component
│   │   │   └── MessageBubble.js         # Individual messages
│   │   ├── ui/                          # Reusable UI components
│   │   └── Agent/                       # Agent-specific components
│   ├── hooks/                           # Custom React hooks
│   └── lib/                             # Utility functions
├── build/               # React production build
├── dist/                # Electron distribution packages
└── assets/              # Application icons and resources
```

## 🔧 Configuration

### Electron Builder
The app uses electron-builder for packaging. Configuration is in `package.json` under the `build` key:

- **Linux**: Builds AppImage and Debian packages
- **Windows**: Builds NSIS installer
- **macOS**: Builds DMG installer with Apple Silicon support

### WebSocket Connection
The app connects to the backend via WebSocket at `ws://localhost:8080/ws`. Make sure your backend server is running on port 8080.

## 🎨 UI Design

The desktop version features:
- **Glassmorphism Effects**: Modern transparent panels with backdrop blur
- **Responsive Layout**: Adapts to different window sizes
- **Dark Theme**: Optimized for desktop use with purple gradient background
- **Smooth Animations**: Fade-in effects and hover states
- **Professional Typography**: Carefully selected fonts and spacing

## 🔌 Backend Integration

The desktop app communicates with the AI agent backend through:
- WebSocket for real-time chat streaming
- JSON message protocol for structured communication
- Connection status monitoring with visual indicators
- Automatic reconnection handling

## 📋 Requirements

- Node.js 18+ 
- Python 3.8+ (for backend server)
- Electron 37+
- Modern operating system (Windows 10+, macOS 10.15+, Ubuntu 18.04+)

## 🚨 Troubleshooting

### Common Issues

1. **App won't start**: Make sure backend server is running on port 8080
2. **WebSocket connection failed**: Check firewall settings and port availability
3. **Build fails**: Ensure all dependencies are installed with `npm install`
4. **Tray icon not showing**: Some Linux systems require additional packages for system tray support

### Debug Mode
Run with debug logging:
```bash
ELECTRON_IS_DEV=true npm run electron
```

## 📄 License

This project is part of the Local AI Agent system. See the main project repository for license information.