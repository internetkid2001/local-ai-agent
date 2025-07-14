import React, { useState, useEffect } from 'react';
import { DesktopChatContainer } from './components/Chat/DesktopChatContainer';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';

function App() {
  const [isElectron, setIsElectron] = useState(false);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <DesktopChatContainer
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