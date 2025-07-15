const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Screenshot capture
  captureScreenshot: () => ipcRenderer.invoke('capture-screenshot'),
  
  // AI processing
  processQuery: (data) => ipcRenderer.invoke('process-query', data),
  processAudioQuery: (data) => ipcRenderer.invoke('process-audio-query', data),
  
  // Model management
  getAvailableModels: () => ipcRenderer.invoke('get-available-models'),
  setPreferredModel: (model) => ipcRenderer.invoke('set-preferred-model', model),
  
  // File operations (for saving results)
  saveResults: (data) => ipcRenderer.invoke('save-results', data),
  loadHistory: () => ipcRenderer.invoke('load-history'),
  
  // System info
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  
  // Event listeners
  onModelStatusChange: (callback) => {
    ipcRenderer.on('model-status-change', (event, status) => callback(status));
  },
  
  onProcessingProgress: (callback) => {
    ipcRenderer.on('processing-progress', (event, progress) => callback(progress));
  },
  
  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});
