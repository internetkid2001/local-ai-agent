import React, { useState, useRef, useEffect } from 'react';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';
import './FloatingApp.css';

function FloatingApp() {
  const [inputValue, setInputValue] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [lastMessage, setLastMessage] = useState(null);
  const [windowExpanded, setWindowExpanded] = useState(false);
  const inputRef = useRef(null);
  const recordingIntervalRef = useRef(null);

  const { 
    messages, 
    sendMessage, 
    isConnected
  } = useAgentWebSocket('ws://localhost:8090/ws');

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  // Update last message
  useEffect(() => {
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.type === 'agent' || lastMsg.type === 'system') {
        setLastMessage(lastMsg.content);
      }
    }
  }, [messages]);

  // Recording timer
  useEffect(() => {
    if (isRecording) {
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
      setRecordingTime(0);
    }
    return () => {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
    };
  }, [isRecording]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && isConnected) {
      sendMessage(inputValue.trim());
      setInputValue('');
      setIsExpanded(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsExpanded(false);
      setInputValue('');
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement actual recording functionality
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatResponse = (text) => {
    // Simple formatting for better readability
    const lines = text.split('\n');
    return lines.map((line, index) => {
      // Format emoji lines
      if (line.includes('📸') || line.includes('🖥️') || line.includes('⚙️') || 
          line.includes('💾') || line.includes('💿') || line.includes('📁')) {
        return <div key={index} className="response-header">{line}</div>;
      }
      // Format error messages
      if (line.includes('Error') || line.includes('❌')) {
        return <div key={index} className="response-error">{line}</div>;
      }
      // Format system messages
      if (line.startsWith('•') || line.startsWith('  •')) {
        return <div key={index} className="response-bullet">{line}</div>;
      }
      // Regular lines
      return <div key={index} className="response-line">{line}</div>;
    });
  };

  // Window control handlers
  const handleMinimize = () => {
    if (window.electronAPI) {
      window.electronAPI.hideWindow();
    }
  };

  const handleClose = () => {
    if (window.electronAPI) {
      const confirmed = window.confirm('Are you sure you want to quit Local AI Agent?');
      if (confirmed) {
        window.close();
      }
    }
  };

  return (
    <div className="floating-container">
      {/* Draggable Handle */}
      <div className="drag-handle" />
      
      {/* Window Controls */}
      <div className="window-controls">
        <button 
          className="control-button expand"
          onClick={() => {
            setWindowExpanded(!windowExpanded);
            if (window.electronAPI) {
              window.electronAPI.updateContentDimensions({
                width: windowExpanded ? 420 : 600,
                height: windowExpanded ? 200 : 400
              });
            }
          }}
          title={windowExpanded ? "Shrink" : "Expand"}
        >
          {windowExpanded ? '□' : '❐'}
        </button>
        <button 
          className="control-button minimize"
          onClick={handleMinimize}
          title="Minimize"
        >
          −
        </button>
        <button 
          className="control-button close"
          onClick={handleClose}
          title="Close"
        >
          ×
        </button>
      </div>

      {/* Connection Status Indicator */}
      <div className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
      
      {/* Main Floating Button/Input */}
      <div className={`floating-input-container ${isExpanded ? 'expanded' : ''}`}>
        {!isExpanded ? (
          <button 
            className="floating-button"
            onClick={() => setIsExpanded(true)}
            title="Click to start typing"
          >
            <span className="icon">💬</span>
            <span className="text">Ask anything...</span>
          </button>
        ) : (
          <form onSubmit={handleSubmit} className="input-form">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              className="floating-input"
              autoFocus
            />
            <button 
              type="submit" 
              className="send-button"
              disabled={!inputValue.trim() || !isConnected}
            >
              ↵
            </button>
          </form>
        )}
      </div>

      {/* Recording Button */}
      <button 
        className={`record-button ${isRecording ? 'recording' : ''}`}
        onClick={toggleRecording}
        title={isRecording ? 'Stop recording' : 'Start voice recording'}
      >
        {isRecording ? (
          <>
            <span className="record-icon">⏹</span>
            <span className="record-time">{formatTime(recordingTime)}</span>
          </>
        ) : (
          <span className="record-icon">🎤</span>
        )}
      </button>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button 
          className="action-button"
          onClick={() => sendMessage('/mcp desktop take_screenshot')}
          title="Take screenshot"
          disabled={!isConnected}
        >
          📸
        </button>
        <button 
          className="action-button"
          onClick={() => {
            // First take a screenshot, then analyze it
            sendMessage('/mcp desktop take_screenshot');
            setTimeout(() => {
              sendMessage('I just took a screenshot. Please analyze the file at ~/Desktop/local_ai_agent_screenshot.png and describe what you see.');
            }, 1500);
          }}
          title="Analyze screen"
          disabled={!isConnected}
        >
          👁️
        </button>
        <button 
          className="action-button"
          onClick={() => sendMessage('/mcp system get_info')}
          title="System info"
          disabled={!isConnected}
        >
          💻
        </button>
        <button 
          className="action-button"
          onClick={() => sendMessage('/status')}
          title="MCP Status"
          disabled={!isConnected}
        >
          🔌
        </button>
        <button 
          className="action-button"
          onClick={() => sendMessage('/help')}
          title="Help"
          disabled={!isConnected}
        >
          ❓
        </button>
      </div>

      {/* Response Area (shows last message) */}
      {lastMessage && (
        <div className="response-area">
          <div className="response-content">
            {formatResponse(lastMessage)}
          </div>
          <button 
            className="close-response"
            onClick={() => setLastMessage(null)}
            title="Close"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

export default FloatingApp;
