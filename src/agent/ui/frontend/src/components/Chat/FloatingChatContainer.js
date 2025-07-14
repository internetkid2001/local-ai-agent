import React, { useState, useRef, useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ConnectionStatus } from '../Agent/ConnectionStatus';

export const FloatingChatContainer = ({
  messages,
  onSendMessage,
  onSendMCPCommand,
  connectionState,
  isConnected,
  isElectron,
  agentStatus,
  mcpServers
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Handle dragging
  const handleMouseDown = (e) => {
    if (e.target.closest('.drag-handle')) {
      setIsDragging(true);
      const rect = containerRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && containerRef.current) {
      const newX = e.clientX - dragOffset.x;
      const newY = e.clientY - dragOffset.y;
      
      containerRef.current.style.left = `${newX}px`;
      containerRef.current.style.top = `${newY}px`;
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  // Window controls
  const handleMinimize = () => {
    if (isElectron && window.electronAPI) {
      window.electronAPI.hideWindow();
    } else {
      setIsMinimized(true);
    }
  };

  const handleClose = () => {
    if (isElectron && window.electronAPI) {
      window.electronAPI.hideWindow();
    }
  };

  return (
    <div 
      ref={containerRef}
      className="floating-chat-container"
      style={{
        position: 'fixed',
        top: '50px',
        right: '50px',
        width: '400px',
        height: isMinimized ? '60px' : '600px',
        background: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '16px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
        zIndex: 10000,
        overflow: 'hidden',
        transition: 'height 0.3s ease-in-out'
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <div className="drag-handle flex items-center justify-between p-3 border-b border-gray-700 cursor-move">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-400 to-blue-400"></div>
          <span className="text-white text-sm font-medium">Local AI Agent</span>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Connection indicator */}
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-400' : 'bg-red-400'
          }`}></div>
          
          {/* Window controls */}
          <button
            onClick={handleMinimize}
            className="w-5 h-5 rounded-full bg-yellow-500 hover:bg-yellow-400 flex items-center justify-center text-xs"
          >
            −
          </button>
          <button
            onClick={handleClose}
            className="w-5 h-5 rounded-full bg-red-500 hover:bg-red-400 flex items-center justify-center text-xs"
          >
            ×
          </button>
        </div>
      </div>

      {/* Content */}
      {!isMinimized && (
        <div className="flex flex-col h-full">
          {/* Connection Status */}
          <div className="p-2 border-b border-gray-700">
            <ConnectionStatus 
              connectionState={connectionState}
              isConnected={isConnected}
              agentStatus={agentStatus}
              mcpServers={mcpServers}
              compact={true}
            />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-hidden">
            <MessageList 
              messages={messages} 
              className="h-full p-4 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
            />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-700">
            <MessageInput
              onSendMessage={onSendMessage}
              onSendMCPCommand={onSendMCPCommand}
              isConnected={isConnected}
              className="bg-gray-800 border-gray-600 text-white placeholder-gray-400"
            />
          </div>

          {/* Quick actions */}
          <div className="p-2 border-t border-gray-700 flex justify-between items-center">
            <div className="flex space-x-2">
              <button 
                onClick={() => onSendMessage('Take a screenshot')}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-lg transition-colors"
              >
                📸 Screenshot
              </button>
              <button 
                onClick={() => onSendMessage('What can you see on my screen?')}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors"
              >
                👁️ Analyze
              </button>
            </div>
            
            {isElectron && (
              <div className="flex space-x-1">
                <button
                  onClick={() => window.electronAPI.moveWindow('left')}
                  className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                  title="Move Left (Ctrl+Left)"
                >
                  ←
                </button>
                <button
                  onClick={() => window.electronAPI.moveWindow('right')}
                  className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                  title="Move Right (Ctrl+Right)"
                >
                  →
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Minimized state */}
      {isMinimized && (
        <div 
          className="flex items-center justify-between h-full px-4 cursor-pointer"
          onClick={() => setIsMinimized(false)}
        >
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-400 to-blue-400"></div>
            <span className="text-white text-sm">Local AI Agent</span>
          </div>
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-400' : 'bg-red-400'
          }`}></div>
        </div>
      )}
    </div>
  );
};