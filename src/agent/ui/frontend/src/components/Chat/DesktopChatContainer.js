import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '../ui/card';
import { MessageList } from './MessageList';
import { AdvancedCommandInterface } from '../Agent/AdvancedCommandInterface';
import { AgentDashboard } from '../Agent/AgentDashboard';
import { ConnectionStatus } from '../Agent/ConnectionStatus';
import { Settings, Info, Maximize2, Minimize2, LayoutDashboard, Terminal } from 'lucide-react';
import { cn } from '../../lib/utils';

export function DesktopChatContainer({ 
  messages, 
  onSendMessage,
  onSendMCPCommand,
  connectionState, 
  isConnected,
  isElectron = false,
  agentStatus = {},
  mcpServers = {}
}) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'dashboard'

  const handleMinimizeToTray = () => {
    if (isElectron && window.electronAPI && window.electronAPI.minimizeToTray) {
      try {
        window.electronAPI.minimizeToTray();
      } catch (error) {
        console.warn('Failed to minimize to tray:', error);
      }
    }
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleShowAbout = () => {
    setShowAbout(true);
  };

  // About Dialog Component
  const AboutDialog = () => (
    showAbout && (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
        <Card className="w-96 max-w-[90vw]">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AI</span>
              </div>
              Local AI Agent
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-white/80 text-sm space-y-2">
              <p>A powerful desktop AI assistant built with React and Electron.</p>
              <p><strong>Version:</strong> 1.0.0</p>
              <p><strong>Platform:</strong> {isElectron ? 'Desktop' : 'Web'}</p>
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => setShowAbout(false)}
                className="px-4 py-2 bg-blue-600/80 hover:bg-blue-500/80 rounded-lg text-white text-sm transition-colors"
              >
                Close
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  );

  if (isFullscreen) {
    return (
      <div className="h-screen flex flex-col bg-black/20 backdrop-blur-sm">
        {/* Header Bar */}
        <div className="flex items-center justify-between p-4 bg-black/30 backdrop-blur-md border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-blue-500 rounded-md flex items-center justify-center">
              <span className="text-white font-bold text-xs">AI</span>
            </div>
            <h1 className="text-white font-semibold text-lg">Local AI Agent</h1>
          </div>
          <div className="flex items-center gap-3">
            <ConnectionStatus connectionState={connectionState} />
            <button
              onClick={handleToggleFullscreen}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <Minimize2 className="w-5 h-5 text-white/70" />
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-h-0">
          <MessageList messages={messages} />
          <AdvancedCommandInterface 
            onSendMessage={onSendMessage}
            onSendMCPCommand={onSendMCPCommand}
            disabled={!isConnected}
            isLoading={connectionState === 'Connecting'}
            mcpServers={mcpServers}
            agentStatus={agentStatus}
          />
        </div>

        <AboutDialog />
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl h-screen flex flex-col p-4">
      {/* Header */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-sm">AI</span>
              </div>
              <div>
                <div className="text-xl">Local AI Agent</div>
                <div className="text-xs text-white/60 font-normal">Intelligent Automation System</div>
              </div>
            </CardTitle>
            <div className="flex items-center gap-3">
              <ConnectionStatus connectionState={connectionState} />
              {isElectron && (
                <button
                  onClick={handleMinimizeToTray}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Minimize to Tray"
                >
                  <Minimize2 className="w-4 h-4 text-white/70" />
                </button>
              )}
              <button
                onClick={handleToggleFullscreen}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Toggle Fullscreen Chat"
              >
                <Maximize2 className="w-4 h-4 text-white/70" />
              </button>
              <button
                onClick={handleShowAbout}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="About"
              >
                <Info className="w-4 h-4 text-white/70" />
              </button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Navigation Tabs */}
      <Card className="mb-4">
        <CardContent className="p-1">
          <div className="flex space-x-1">
            <button
              onClick={() => setActiveTab('chat')}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                activeTab === 'chat' 
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" 
                  : "text-white/60 hover:text-white/80 hover:bg-white/5"
              )}
            >
              <Terminal className="w-4 h-4" />
              AI Command Interface
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                activeTab === 'dashboard' 
                  ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" 
                  : "text-white/60 hover:text-white/80 hover:bg-white/5"
              )}
            >
              <LayoutDashboard className="w-4 h-4" />
              System Dashboard
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Content Container */}
      <Card className="flex-1 flex flex-col min-h-0">
        <CardContent className="flex-1 flex flex-col p-4 min-h-0">
          {activeTab === 'chat' ? (
            <div className="flex-1 flex flex-col min-h-0 space-y-4">
              <MessageList messages={messages} />
              <AdvancedCommandInterface 
                onSendMessage={onSendMessage}
                onSendMCPCommand={onSendMCPCommand}
                disabled={!isConnected}
                isLoading={connectionState === 'Connecting'}
                mcpServers={mcpServers}
                agentStatus={agentStatus}
              />
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <AgentDashboard 
                connectionState={connectionState}
                isConnected={isConnected}
                agentStatus={agentStatus}
                mcpServers={mcpServers}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <AboutDialog />
    </div>
  );
}