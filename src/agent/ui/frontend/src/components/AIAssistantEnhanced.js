import React, { useState, useRef, useEffect } from 'react';
import { GlassCardAdvanced, ContextCard, TagChip, ShimmerText } from './ui/GlassCardAdvanced';
import { FadeInTextAdvanced, MessageBubble } from './ui/FadeInTextAdvanced';
import ScreenshotQueueEnhanced from './ScreenshotQueueEnhanced';
import { showToast } from './ui/Toast';

/**
 * Enhanced AIAssistant Component
 * Advanced interface inspired by Horizon Overlay
 */
const AIAssistantEnhanced = () => {
  const [screenshots, setScreenshots] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');
  const [smarterAnalysis, setSmarterAnalysis] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [currentResponse, setCurrentResponse] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingIntervalRef = useRef(null);

  // Handle screenshot capture
  const handleScreenshot = async () => {
    try {
      const screenshot = await window.electronAPI.captureScreenshot();
      if (screenshot) {
        const newScreenshot = {
          id: Date.now(),
          dataUrl: screenshot.dataUrl,
          timestamp: new Date().toISOString(),
          name: `Screenshot ${screenshots.length + 1}`,
          tags: []
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
    
    // Add user message to history
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: 'Voice query',
      timestamp: new Date().toISOString()
    };
    setConversationHistory(prev => [...prev, userMessage]);
    
    // Add thinking indicator
    const thinkingMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      content: '',
      isThinking: true,
      timestamp: new Date().toISOString()
    };
    setConversationHistory(prev => [...prev, thinkingMessage]);
    
    try {
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result.split(',')[1];
        
        const response = await window.electronAPI.processAudioQuery({
          audio: base64Audio,
          screenshots: screenshots.map(s => ({
            id: s.id,
            dataUrl: s.dataUrl,
            timestamp: s.timestamp
          })),
          model: selectedModel,
          smarterAnalysis
        });

        if (response.success) {
          // Remove thinking indicator and add response
          setConversationHistory(prev => 
            prev.filter(msg => !msg.isThinking).concat({
              id: Date.now() + 2,
              type: 'assistant',
              content: response.result,
              timestamp: new Date().toISOString()
            })
          );
          showToast('Query processed successfully!', 'success');
        } else {
          setConversationHistory(prev => prev.filter(msg => !msg.isThinking));
          showToast('Failed to process query', 'error');
        }
      };
    } catch (error) {
      console.error('Process error:', error);
      setConversationHistory(prev => prev.filter(msg => !msg.isThinking));
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
    
    // Add thinking indicator
    const thinkingMessage = {
      id: Date.now(),
      type: 'assistant',
      content: '',
      isThinking: true,
      timestamp: new Date().toISOString()
    };
    setConversationHistory(prev => [...prev, thinkingMessage]);
    
    try {
      const response = await window.electronAPI.processQuery({
        screenshots: screenshots.map(s => ({
          id: s.id,
          dataUrl: s.dataUrl,
          timestamp: s.timestamp
        })),
        model: selectedModel,
        smarterAnalysis,
        selectedText
      });

      if (response.success) {
        // Remove thinking indicator and add response
        setConversationHistory(prev => 
          prev.filter(msg => !msg.isThinking).concat({
            id: Date.now() + 1,
            type: 'assistant',
            content: response.result,
            timestamp: new Date().toISOString()
          })
        );
        showToast('Analysis complete!', 'success');
      } else {
        setConversationHistory(prev => prev.filter(msg => !msg.isThinking));
        showToast('Failed to analyze screenshots', 'error');
      }
    } catch (error) {
      console.error('Solve error:', error);
      setConversationHistory(prev => prev.filter(msg => !msg.isThinking));
      showToast('Failed to process request', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteScreenshot = (id) => {
    setScreenshots(prev => prev.filter(s => s.id !== id));
    showToast('Screenshot deleted', 'info');
  };

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
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isRecording, screenshots]);

  // Capture selected text
  useEffect(() => {
    const handleTextSelection = () => {
      const selection = window.getSelection();
      const text = selection.toString().trim();
      if (text) {
        setSelectedText(text);
      }
    };

    document.addEventListener('mouseup', handleTextSelection);
    return () => document.removeEventListener('mouseup', handleTextSelection);
  }, []);

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Gradient Background Effect */}
      <div className="absolute inset-0 pointer-events-none">
        <div 
          className="absolute inset-x-0 top-0 h-32 opacity-50"
          style={{
            background: 'radial-gradient(ellipse at top, rgba(139, 92, 246, 0.3) 0%, transparent 70%)'
          }}
        />
      </div>

      <div className="relative z-10 flex flex-col h-full p-4 space-y-4">
        {/* Header */}
        <GlassCardAdvanced 
          className="p-4"
          variant="elevated"
          glow={true}
        >
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">AI Assistant</h1>
            <div className="flex items-center gap-3">
              <div className="text-sm opacity-80">
                {screenshots.length} screenshot{screenshots.length !== 1 ? 's' : ''}
              </div>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-white/10 backdrop-blur-sm border border-white/30 rounded-lg px-3 py-1 text-sm focus:outline-none focus:border-purple-400 transition-colors"
              >
                <option value="auto">Auto</option>
                <option value="local">Local</option>
                <option value="cloud">Cloud</option>
              </select>
            </div>
          </div>
        </GlassCardAdvanced>

        {/* Conversation History */}
        {conversationHistory.length > 0 && (
          <GlassCardAdvanced className="flex-1 p-4 overflow-y-auto max-h-64">
            <div className="space-y-2">
              {conversationHistory.map(message => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isUser={message.type === 'user'}
                  isThinking={message.isThinking}
                />
              ))}
            </div>
          </GlassCardAdvanced>
        )}

        {/* Screenshot Queue */}
        <div className="flex-1 overflow-y-auto">
          <ScreenshotQueueEnhanced 
            screenshots={screenshots}
            onDelete={handleDeleteScreenshot}
          />
        </div>

        {/* Input Area */}
        <GlassCardAdvanced className="p-4" variant="elevated">
          {/* Selected Text Indicator */}
          {selectedText && (
            <div className="mb-3 flex items-center gap-2">
              <TagChip
                tag={{ name: 'Selected text in use', color: '#FFA500' }}
                removable={true}
                onRemove={() => setSelectedText('')}
              />
            </div>
          )}

          {/* Smarter Analysis Toggle */}
          <div className="mb-3 flex items-center justify-between">
            <button
              onClick={() => setSmarterAnalysis(!smarterAnalysis)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-full
                transition-all duration-300
                ${smarterAnalysis 
                  ? 'bg-purple-500/30 border border-purple-400/50 shadow-lg shadow-purple-500/20' 
                  : 'bg-white/10 border border-white/20'
                }
              `}
            >
              <span className="text-sm">🔍</span>
              <span className="text-sm">
                {smarterAnalysis ? 'Deeper Analysis' : 'Quick Analysis'}
              </span>
            </button>

            <div className="flex items-center gap-2 text-xs opacity-60">
              <span>Ctrl+S</span>
              <span>•</span>
              <span>Ctrl+R</span>
              <span>•</span>
              <span>Ctrl+Enter</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={handleScreenshot}
              className="px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-400/30 rounded-lg transition-all flex flex-col items-center gap-1"
            >
              <span className="text-2xl">📸</span>
              <span className="text-xs">Screenshot</span>
            </button>

            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`
                px-4 py-3 rounded-lg transition-all flex flex-col items-center gap-1
                ${isRecording 
                  ? 'bg-red-500/20 hover:bg-red-500/30 border border-red-400/30' 
                  : 'bg-purple-500/20 hover:bg-purple-500/30 border border-purple-400/30'
                }
                ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <span className="text-2xl">{isRecording ? '🔴' : '🎤'}</span>
              <span className="text-xs">
                {isRecording ? formatTime(recordingTime) : 'Record'}
              </span>
            </button>

            <button
              onClick={handleSolve}
              disabled={isProcessing || screenshots.length === 0}
              className={`
                px-4 py-3 bg-green-500/20 hover:bg-green-500/30 
                border border-green-400/30 rounded-lg transition-all 
                flex flex-col items-center gap-1
                ${(isProcessing || screenshots.length === 0) ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <span className="text-2xl">🤖</span>
              <span className="text-xs">Analyze</span>
            </button>
          </div>
        </GlassCardAdvanced>

        {/* Status Indicator */}
        {isProcessing && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
            <ShimmerText text="AI is thinking..." className="text-sm" />
          </div>
        )}
      </div>
    </div>
  );
};

export default AIAssistantEnhanced;
