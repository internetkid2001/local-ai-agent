# Changelog - Local AI Agent Floating Desktop App

## [Version 2.0] - 2025-01-14

### 🎨 Major UI Overhaul - Cluely-Inspired Floating Interface

#### ✅ Fixed UI Styling Issues
- **Fixed TailwindCSS compilation**: Resolved version conflicts between TailwindCSS v3 and v4
- **Removed CRACO dependency**: Switched back to standard Create React App for better compatibility
- **Updated PostCSS configuration**: Fixed plugin references for proper CSS compilation
- **Restored glass morphism effects**: Backdrop blur, transparency, and gradient effects now working

#### 🎯 Floating Window Implementation
- **Always-on-top transparent window**: Proper floating behavior with backdrop blur
- **Cluely-inspired design**: Dark theme with purple gradient accents and glass effects
- **Optimal window positioning**: Right side of screen (70% from left, 50px from top)
- **Smart window sizing**: 450x600 default, with min/max constraints (350x400 to 800x700)

#### ⌨️ Enhanced User Experience
- **Global shortcuts implementation**:
  - `Ctrl+B`: Toggle window visibility
  - `Ctrl+H`: Hide window  
  - `Ctrl+Arrow Keys`: Move window in cardinal directions
  - `Ctrl+N`: New chat session
- **Window management**: Minimize, hide, and close controls with macOS-style buttons
- **Auto-resize**: Window adjusts size based on content dynamically

### 🔧 Development Experience Improvements

#### 🛠️ Developer Tools & Security
- **DevTools auto-open disabled**: No longer opens automatically (can still open with F12)
- **Content Security Policy added**: Enhanced security for Electron renderer process
- **Security warnings resolved**: Proper CSP configuration eliminates development warnings
- **App title updated**: Changed from "React App" to "Local AI Agent"

#### 📱 Build System Fixes
- **React build optimization**: Production builds now properly compile TailwindCSS
- **CSS bundle size**: Increased from 734B to 5.27KB (indicates proper compilation)
- **File structure cleanup**: Removed unnecessary CRACO configuration files

### 📸 Enhanced Screenshot Functionality

#### 🎯 User-Friendly Screenshot Location
- **Desktop/Pictures priority**: Screenshots now save to accessible user folders
- **Fallback hierarchy**: Desktop → Pictures → Home directory
- **Clear file naming**: `local_ai_agent_screenshot.png` for easy identification
- **Path feedback**: UI shows exact save location after capture

### 🌐 Terminal Bridge Improvements

#### 💬 Enhanced Chat Interface
- **Improved connection handling**: Better WebSocket stability and reconnection logic
- **MCP command integration**: Seamless integration with desktop automation commands
- **Status monitoring**: Real-time connection status indicators
- **Command feedback**: Clear responses for user actions

### 📁 Updated Project Structure

#### 🗂️ File Organization
```
src/agent/ui/frontend/
├── main.js                    # Enhanced with floating window logic
├── preload.js                # Updated IPC bridge
├── src/
│   ├── App.js                # Redesigned Cluely-like interface  
│   ├── index.css             # Updated with floating styles
│   └── hooks/
│       └── useAgentWebSocket.js  # Improved WebSocket handling
├── public/
│   └── index.html            # Added CSP and proper title
└── package.json              # Updated dependencies and scripts
```

### 🔄 Configuration Changes

#### ⚙️ Updated Settings
- **TailwindCSS**: Downgraded from v4 to stable v3.4.17
- **PostCSS**: Updated plugin configuration for proper compilation
- **Package scripts**: Switched from CRACO to react-scripts
- **Electron security**: Enhanced Content Security Policy

#### 🚀 Port Configuration
- **8090**: Terminal bridge WebSocket endpoint
- **8765**: Filesystem MCP server
- **8766**: Desktop MCP server  
- **8767**: System MCP server
- **3002**: React development server (fallback port)

### 🐛 Bug Fixes

#### 🔨 Resolved Issues
1. **TailwindCSS not compiling**: Fixed version conflicts and configuration
2. **Electron showing wrong UI**: Resolved build file loading and CSS compilation
3. **DevTools auto-opening**: Disabled for better user experience
4. **Screenshot location inaccessible**: Changed from `/tmp/` to user directories
5. **Security warnings**: Added proper Content Security Policy
6. **Window management**: Fixed focus and always-on-top behavior

### 🎯 Key Features Working

#### ✅ Verified Functionality
- **🎨 Floating UI**: Beautiful transparent window with glass morphism
- **⌨️ Global shortcuts**: All keyboard shortcuts working correctly
- **📸 Screenshots**: Saving to Desktop/Pictures folders successfully  
- **🔌 WebSocket**: Stable connection to terminal bridge
- **🖥️ MCP Integration**: Desktop automation commands functional
- **📱 Responsive**: Window adapts to content changes
- **🔒 Security**: CSP implemented, no security warnings

### 📖 Documentation Updates

#### 📝 New Documentation
- **README.md**: Comprehensive setup and usage instructions
- **CHANGELOG.md**: Detailed change tracking (this file)
- **Running instructions**: Step-by-step command line and desktop app usage
- **Troubleshooting guide**: Common issues and solutions
- **Development setup**: Instructions for contributors

### 🚀 Next Steps

#### 🔮 Planned Improvements
1. **AI Backend Integration**: Replace basic chat with proper Claude API
2. **Enhanced MCP Capabilities**: Better computer vision and automation
3. **Settings Panel**: User-configurable preferences
4. **Theme Customization**: Multiple visual themes
5. **Performance Optimization**: Reduce memory usage and startup time

---

## Previous Versions

### [Version 1.0] - Initial Implementation
- Basic MCP server integration
- Command-line interface
- Desktop automation capabilities
- File system operations
- System monitoring tools