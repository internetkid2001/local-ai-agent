const { ipcMain, desktopCapturer, screen } = require('electron');
const path = require('path');
const fs = require('fs').promises;

// Import our Python bridge (adjust path as needed)
const { PythonBridge } = require('./python-bridge');

class AIHandlers {
  constructor() {
    this.pythonBridge = new PythonBridge();
    this.setupHandlers();
  }

  setupHandlers() {
    // Screenshot capture
    ipcMain.handle('capture-screenshot', async (event) => {
      try {
        const sources = await desktopCapturer.getSources({
          types: ['screen'],
          thumbnailSize: screen.getPrimaryDisplay().size
        });

        if (sources.length > 0) {
          const screenshot = sources[0].thumbnail;
          return {
            success: true,
            dataUrl: screenshot.toDataURL(),
            size: screenshot.getSize()
          };
        }
        
        return { success: false, error: 'No screen sources available' };
      } catch (error) {
        console.error('Screenshot capture error:', error);
        return { success: false, error: error.message };
      }
    });

    // Process AI query with screenshots
    ipcMain.handle('process-query', async (event, data) => {
      try {
        const { screenshots, model } = data;
        
        // Prepare request for Python backend
        const request = {
          type: 'analyze',
          model: model,
          screenshots: screenshots,
          timestamp: new Date().toISOString()
        };

        // Send to Python backend via our bridge
        const response = await this.pythonBridge.sendRequest(request);
        
        return {
          success: true,
          result: response.result,
          model_used: response.model_used,
          processing_time: response.processing_time
        };
      } catch (error) {
        console.error('Query processing error:', error);
        return { success: false, error: error.message };
      }
    });

    // Process audio query
    ipcMain.handle('process-audio-query', async (event, data) => {
      try {
        const { audio, screenshots, model } = data;
        
        // Save audio temporarily
        const tempAudioPath = path.join(__dirname, 'temp', `audio_${Date.now()}.wav`);
        await fs.writeFile(tempAudioPath, Buffer.from(audio, 'base64'));

        // Prepare request for Python backend
        const request = {
          type: 'analyze_audio',
          model: model,
          audio_path: tempAudioPath,
          screenshots: screenshots,
          timestamp: new Date().toISOString()
        };

        // Send to Python backend
        const response = await this.pythonBridge.sendRequest(request);
        
        // Clean up temp file
        await fs.unlink(tempAudioPath).catch(console.error);
        
        return {
          success: true,
          result: response.result,
          transcription: response.transcription,
          model_used: response.model_used,
          processing_time: response.processing_time
        };
      } catch (error) {
        console.error('Audio query processing error:', error);
        return { success: false, error: error.message };
      }
    });

    // Get available models
    ipcMain.handle('get-available-models', async (event) => {
      try {
        const response = await this.pythonBridge.sendRequest({
          type: 'get_models'
        });
        
        return {
          success: true,
          models: response.models,
          current: response.current_model
        };
      } catch (error) {
        console.error('Get models error:', error);
        return { success: false, error: error.message };
      }
    });

    // Set preferred model
    ipcMain.handle('set-preferred-model', async (event, model) => {
      try {
        const response = await this.pythonBridge.sendRequest({
          type: 'set_model',
          model: model
        });
        
        return {
          success: true,
          model: response.model
        };
      } catch (error) {
        console.error('Set model error:', error);
        return { success: false, error: error.message };
      }
    });

    // Save results
    ipcMain.handle('save-results', async (event, data) => {
      try {
        const resultsDir = path.join(__dirname, 'results');
        await fs.mkdir(resultsDir, { recursive: true });
        
        const filename = `result_${Date.now()}.json`;
        const filepath = path.join(resultsDir, filename);
        
        await fs.writeFile(filepath, JSON.stringify(data, null, 2));
        
        return {
          success: true,
          filepath: filepath
        };
      } catch (error) {
        console.error('Save results error:', error);
        return { success: false, error: error.message };
      }
    });

    // Load history
    ipcMain.handle('load-history', async (event) => {
      try {
        const resultsDir = path.join(__dirname, 'results');
        const files = await fs.readdir(resultsDir).catch(() => []);
        
        const history = [];
        for (const file of files) {
          if (file.endsWith('.json')) {
            const filepath = path.join(resultsDir, file);
            const content = await fs.readFile(filepath, 'utf8');
            history.push(JSON.parse(content));
          }
        }
        
        return {
          success: true,
          history: history.sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
          )
        };
      } catch (error) {
        console.error('Load history error:', error);
        return { success: false, error: error.message };
      }
    });

    // Get system info
    ipcMain.handle('get-system-info', async (event) => {
      try {
        const response = await this.pythonBridge.sendRequest({
          type: 'system_info'
        });
        
        return {
          success: true,
          info: response.info
        };
      } catch (error) {
        console.error('System info error:', error);
        return { success: false, error: error.message };
      }
    });
  }

  // Send status updates to renderer
  sendStatusUpdate(window, status) {
    if (window && !window.isDestroyed()) {
      window.webContents.send('model-status-change', status);
    }
  }

  // Send progress updates to renderer
  sendProgressUpdate(window, progress) {
    if (window && !window.isDestroyed()) {
      window.webContents.send('processing-progress', progress);
    }
  }

  // Cleanup
  async cleanup() {
    await this.pythonBridge.cleanup();
  }
}

module.exports = AIHandlers;
