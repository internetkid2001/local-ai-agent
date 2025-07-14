import React, { useState, useEffect } from 'react';
import { FloatingChatContainer } from './components/Chat/FloatingChatContainer';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';

function App() {
  const [isElectron, setIsElectron] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const { 
    messages, 
    sendMessage, 
    sendMCPCommand,
    connectionState, 
    isConnected,
    agentStatus,
    mcpServers 
  } = useAgentWebSocket('ws://localhost:8080/ws');

  useEffect(() => {
    // Check if running in Electron with proper API
    setIsElectron(
      window.electronAPI !== undefined && 
      typeof window.electronAPI === 'object'
    );
  }, []);

  const handleNewChat = () => {
    // Clear messages (you might want to add this to your WebSocket hook)
    window.location.reload();
  };

  // Listen for Electron events
  useEffect(() => {
    if (isElectron && window.electronAPI && window.electronAPI.onNewChat) {
      try {
        const removeNewChatListener = window.electronAPI.onNewChat(handleNewChat);
        
        return () => {
          if (removeNewChatListener && typeof removeNewChatListener === 'function') {
            removeNewChatListener();
          }
        };
      } catch (error) {
        console.warn('Failed to set up Electron event listeners:', error);
      }
    }
  }, [isElectron]);

  // Hide welcome after first interaction
  useEffect(() => {
    if (messages.length > 0) {
      setShowWelcome(false);
    }
  }, [messages]);

  return (
    <div className="w-screen h-screen bg-transparent overflow-hidden">
      {/* Background blur effect for desktop */}
      <div className="fixed inset-0 bg-black bg-opacity-5 backdrop-blur-sm pointer-events-none"></div>
      
      {/* Welcome overlay for first launch */}
      {showWelcome && (
        <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-30">
          <div className="bg-black bg-opacity-80 backdrop-blur-lg rounded-2xl p-8 max-w-md mx-4 border border-gray-700">
            <div className="text-center text-white">
              <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-purple-400 to-blue-400 rounded-full flex items-center justify-center">
                🤖
              </div>
              <h1 className="text-2xl font-bold mb-2">Local AI Agent</h1>
              <p className="text-gray-300 mb-6">
                Your floating AI assistant is ready! Use <kbd className="px-2 py-1 bg-gray-700 rounded text-sm">Ctrl+B</kbd> to toggle visibility.
              </p>
              
              <div className="space-y-2 text-sm text-gray-400 mb-6">
                <p>• <kbd className="px-1 bg-gray-700 rounded">Ctrl+B</kbd> - Toggle window</p>
                <p>• <kbd className="px-1 bg-gray-700 rounded">Ctrl+H</kbd> - Hide window</p>
                <p>• <kbd className="px-1 bg-gray-700 rounded">Ctrl+Arrow</kbd> - Move window</p>
              </div>
              
              <button
                onClick={() => setShowWelcome(false)}
                className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Chat Container */}
      <FloatingChatContainer
        messages={messages}
        onSendMessage={sendMessage}
        onSendMCPCommand={sendMCPCommand}
        connectionState={connectionState}
        isConnected={isConnected}
        isElectron={isElectron}
        agentStatus={agentStatus}
        mcpServers={mcpServers}
      />
    </div>
  );
}

export default App;