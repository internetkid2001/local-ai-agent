const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  
  // Window controls for floating window
  toggleWindow: () => ipcRenderer.invoke('toggle-window'),
  hideWindow: () => ipcRenderer.invoke('hide-window'),
  showWindow: () => ipcRenderer.invoke('show-window'),
  moveWindow: (direction) => ipcRenderer.invoke('move-window', direction),
  getWindowState: () => ipcRenderer.invoke('get-window-state'),
  updateContentDimensions: (dimensions) => ipcRenderer.invoke('update-content-dimensions', dimensions),
  
  // Legacy support
  minimizeToTray: () => ipcRenderer.invoke('hide-window'),
  
  // Generic send method for compatibility
  send: (channel, data) => {
    // Whitelist of allowed channels
    const validChannels = ['minimize-to-tray', 'new-chat', 'show-about'];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },
  
  // Generic invoke method for compatibility
  invoke: (channel, data) => {
    const validChannels = [
      'get-app-version', 'get-platform', 'toggle-window', 
      'hide-window', 'show-window', 'move-window', 'get-window-state', 'update-content-dimensions'
    ];
    if (validChannels.includes(channel)) {
      return ipcRenderer.invoke(channel, data);
    }
  },
  
  // Chat controls
  onNewChat: (callback) => {
    ipcRenderer.on('new-chat', callback);
    return () => ipcRenderer.removeListener('new-chat', callback);
  },
  
  // About dialog
  onShowAbout: (callback) => {
    ipcRenderer.on('show-about', callback);
    return () => ipcRenderer.removeListener('show-about', callback);
  },
  
  // Generic listener for compatibility
  on: (channel, callback) => {
    const validChannels = ['new-chat', 'show-about'];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, callback);
      return () => ipcRenderer.removeListener(channel, callback);
    }
  },
  
  // Send notifications (optional)
  showNotification: (title, body) => {
    if (Notification.permission === 'granted') {
      new Notification(title, { body });
    }
  }
});

// Request notification permission on load
window.addEventListener('DOMContentLoaded', () => {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
});