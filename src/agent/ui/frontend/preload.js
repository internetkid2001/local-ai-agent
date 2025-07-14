const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  
  // Window controls
  minimizeToTray: () => ipcRenderer.send('minimize-to-tray'),
  
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
    const validChannels = ['get-app-version', 'get-platform'];
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