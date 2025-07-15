import React, { useState, useEffect, useRef } from 'react';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';

function App() {
  const [isElectron, setIsElectron] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [isMinimized, setIsMinimized] = useState(false);
  const containerRef = useRef(null);
  const messagesEndRef = useRef(null);

  const { 
    messages, 
    sendMessage, 
    connectionState, 
    isConnected
  } = useAgentWebSocket('ws://localhost:8090/ws');

  useEffect(() => {
    // Check if running in Electron
    setIsElectron(window.electronAPI !== undefined);
    
    // Auto-resize window based on content
    if (window.electronAPI && containerRef.current) {
      const resizeObserver = new ResizeObserver(() => {
        if (containerRef.current) {
          const { scrollHeight, scrollWidth } = containerRef.current;
          window.electronAPI.updateContentDimensions?.({ 
            width: Math.min(scrollWidth + 32, 500), 
            height: Math.min(scrollHeight + 32, 700) 
          });
        }
      });
      
      resizeObserver.observe(containerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Listen for Electron events
  useEffect(() => {
    if (isElectron && window.electronAPI) {
      try {
        const cleanup = window.electronAPI.onNewChat?.(() => {
          window.location.reload();
        });
        return cleanup;
      } catch (error) {
        console.warn('Failed to set up Electron event listeners:', error);
      }
    }
  }, [isElectron]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && isConnected) {
      sendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const formatMessage = (message) => {
    // Format system messages and commands differently
    if (message.type === 'system') {
      return (
        <div className="mb-3 p-3 bg-gray-800 bg-opacity-50 rounded-lg border border-gray-600">
          <div className="text-gray-300 text-sm whitespace-pre-wrap">{message.content}</div>
        </div>
      );
    }
    
    if (message.type === 'user') {
      return (
        <div className="mb-3 flex justify-end">
          <div className="bg-purple-600 text-white px-4 py-2 rounded-lg max-w-xs break-words">
            {message.content}
          </div>
        </div>
      );
    }
    
    if (message.type === 'agent') {
      return (
        <div className="mb-3">
          <div className="bg-gray-700 text-white px-4 py-2 rounded-lg max-w-xs break-words">
            {message.content}
          </div>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div 
      ref={containerRef}
      className="w-full h-full bg-black bg-opacity-90 backdrop-blur-lg border border-gray-600 rounded-2xl overflow-hidden shadow-2xl"
      style={{ minWidth: '350px', minHeight: '400px', maxWidth: '500px', maxHeight: '700px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800 bg-opacity-50">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-gradient-to-r from-purple-400 to-blue-400 animate-pulse"></div>
          <span className="text-white font-medium text-sm">Local AI Agent</span>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Connection status */}
          <div 
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          ></div>
          
          {/* Minimize button */}
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="w-6 h-6 rounded-full bg-yellow-500 hover:bg-yellow-400 flex items-center justify-center text-black text-xs font-bold transition-colors"
            title="Minimize"
          >
            −
          </button>
          
          {/* Close button */}
          <button
            onClick={() => window.electronAPI?.hideWindow?.()}
            className="w-6 h-6 rounded-full bg-red-500 hover:bg-red-400 flex items-center justify-center text-white text-xs font-bold transition-colors"
            title="Hide (Ctrl+H)"
          >
            ×
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages Area */}
          <div className="flex-1 p-4 overflow-y-auto" style={{ height: '300px', maxHeight: '500px' }}>
            {messages.length === 0 ? (
              <div className="text-center text-gray-400 mt-8">
                <div className="text-4xl mb-4">🤖</div>
                <p className="text-sm">Welcome to Local AI Agent</p>
                <p className="text-xs mt-2">Type a message or try:</p>
                <div className="mt-3 space-y-1 text-xs">
                  <p><code className="bg-gray-700 px-1 rounded">/help</code> - Show help</p>
                  <p><code className="bg-gray-700 px-1 rounded">/status</code> - System status</p>
                  <p><code className="bg-gray-700 px-1 rounded">/mcp desktop take_screenshot</code> - Screenshot</p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id}>
                  {formatMessage(message)}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-700 p-4 bg-gray-800 bg-opacity-30">
            <form onSubmit={handleSubmit} className="flex space-x-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={isConnected ? "Type a message..." : "Connecting..."}
                disabled={!isConnected}
                className="flex-1 bg-gray-700 bg-opacity-50 text-white placeholder-gray-400 px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-sm"
              />
              <button
                type="submit"
                disabled={!isConnected || !inputValue.trim()}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium"
              >
                Send
              </button>
            </form>
            
            {/* Quick Actions */}
            <div className="flex space-x-2 mt-3">
              <button
                onClick={() => sendMessage('/mcp desktop take_screenshot')}
                disabled={!isConnected}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-xs rounded transition-colors"
              >
                📸 Screenshot
              </button>
              <button
                onClick={() => sendMessage('/status')}
                disabled={!isConnected}
                className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-xs rounded transition-colors"
              >
                📊 Status
              </button>
              <button
                onClick={() => sendMessage('/help')}
                disabled={!isConnected}
                className="px-3 py-1 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-600 text-white text-xs rounded transition-colors"
              >
                ❓ Help
              </button>
            </div>
          </div>
        </>
      )}

      {/* Minimized State */}
      {isMinimized && (
        <div 
          className="p-4 cursor-pointer hover:bg-gray-800 hover:bg-opacity-30 transition-colors"
          onClick={() => setIsMinimized(false)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-400 to-blue-400"></div>
              <span className="text-white text-sm">Local AI Agent</span>
            </div>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;