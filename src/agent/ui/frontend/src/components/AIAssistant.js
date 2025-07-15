import React, { useState, useRef, useEffect } from 'react';
import GlassCard, { GlassButton, GlassBadge } from './ui/GlassCard';
import ScreenshotQueue from './ScreenshotQueue';
import { showToast } from './ui/Toast';

/**
 * AIAssistant Component
 * Main interface for AI interactions with screenshot capture and voice recording
 */
const AIAssistant = () => {
  const [screenshots, setScreenshots] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto'); // auto, local, cloud
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingIntervalRef = useRef(null);

  // Handle screenshot capture
  const handleScreenshot = async () => {
    try {
      // Request screenshot from Electron main process
      const screenshot = await window.electronAPI.captureScreenshot();
      if (screenshot) {
        const newScreenshot = {
          id: Date.now(),
          dataUrl: screenshot.dataUrl,
          timestamp: new Date().toISOString(),
          name: `Screenshot ${screenshots.length + 1}`
        };
        setScreenshots(prev => [...prev, newScreenshot]);
        showToast('Screenshot captured!', 'success');
      }
    } catch (error) {
      console.error('Screenshot error:', error);
      showToast('Failed to capture screenshot', 'error');
    }
  };

  // Handle voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processAudioQuery(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start recording timer
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      showToast('Recording started...', 'info');
    } catch (error) {
      console.error('Recording error:', error);
      showToast('Failed to start recording', 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
    }
  };

  const processAudioQuery = async (audioBlob) => {
    setIsProcessing(true);
    try {
      // Convert audio to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result.split(',')[1];
        
        // Send to backend for processing
        const response = await window.electronAPI.processAudioQuery({
          audio: base64Audio,
          screenshots: screenshots.map(s => ({
            id: s.id,
            dataUrl: s.dataUrl,
            timestamp: s.timestamp
          })),
          model: selectedModel
        });

        if (response.success) {
          showToast('Query processed successfully!', 'success');
          // Handle response - could update UI with results
        } else {
          showToast('Failed to process query', 'error');
        }
      };
    } catch (error) {
      console.error('Process error:', error);
      showToast('Failed to process audio query', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSolve = async () => {
    if (screenshots.length === 0) {
      showToast('Please capture a screenshot first', 'warning');
      return;
    }

    setIsProcessing(true);
    try {
      const response = await window.electronAPI.processQuery({
        screenshots: screenshots.map(s => ({
          id: s.id,
          dataUrl: s.dataUrl,
          timestamp: s.timestamp
        })),
        model: selectedModel
      });

      if (response.success) {
        showToast('Analysis complete!', 'success');
        // Handle response
      } else {
        showToast('Failed to analyze screenshots', 'error');
      }
    } catch (error) {
      console.error('Solve error:', error);
      showToast('Failed to process request', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteScreenshot = (id) => {
    setScreenshots(prev => prev.filter(s => s.id !== id));
    showToast('Screenshot deleted', 'info');
  };

  // Format recording time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
          case 's':
            e.preventDefault();
            handleScreenshot();
            break;
          case 'r':
            e.preventDefault();
            if (isRecording) {
              stopRecording();
            } else {
              startRecording();
            }
            break;
          case 'Enter':
            e.preventDefault();
            handleSolve();
            break;
          default:
            // Do nothing for other key combinations
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isRecording, screenshots]);

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white p-4 space-y-4">
      {/* Header */}
      <div className="glass-card flex items-center justify-between">
        <h1 className="text-2xl font-bold">AI Assistant</h1>
        <div className="flex items-center gap-2">
          <GlassBadge>
            {screenshots.length} screenshot{screenshots.length !== 1 ? 's' : ''}
          </GlassBadge>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg px-3 py-1 text-sm"
          >
            <option value="auto">Auto Select</option>
            <option value="local">Local (Ollama)</option>
            <option value="cloud">Cloud (Gemini)</option>
          </select>
      </div>
      </div>

      {/* Screenshot Queue */}
      <div className="flex-1 overflow-y-auto">
        <ScreenshotQueue 
          screenshots={screenshots}
          onDelete={handleDeleteScreenshot}
        />
      </div>

      {/* Action Buttons */}
      <div className="glass-card space-y-3">
        {/* Screenshot Button */}
        <GlassButton 
          onClick={handleScreenshot}
          className="w-full flex items-center justify-center gap-2"
        >
          <span>📸</span>
          <span>Capture Screenshot</span>
          <span className="text-xs opacity-70">(Ctrl+S)</span>
        </GlassButton>

        {/* Voice Recording Button */}
        <GlassButton 
          onClick={isRecording ? stopRecording : startRecording}
          variant={isRecording ? 'danger' : 'primary'}
          className="w-full flex items-center justify-center gap-2"
          disabled={isProcessing}
        >
          <span>{isRecording ? '🔴' : '🎤'}</span>
          <span>{isRecording ? `Recording ${formatTime(recordingTime)}` : 'Start Recording'}</span>
          <span className="text-xs opacity-70">(Ctrl+R)</span>
        </GlassButton>

        {/* Solve Button */}
        <GlassButton 
          onClick={handleSolve}
          variant="success"
          className="w-full flex items-center justify-center gap-2"
          disabled={isProcessing || screenshots.length === 0}
        >
          {isProcessing ? (
            <>
              <span className="animate-spin">⏳</span>
              <span>Processing...</span>
            </>
          ) : (
            <>
              <span>🤖</span>
              <span>Analyze with AI</span>
              <span className="text-xs opacity-70">(Ctrl+Enter)</span>
            </>
          )}
        </GlassButton>
      </div>

      {/* Status Bar */}
      {isProcessing && (
        <div className="glass-card glass-card-secondary text-center text-sm">
          <span className="animate-pulse">AI is thinking...</span>
        </div>
      )}
    </div>
  );
};

export default AIAssistant;
