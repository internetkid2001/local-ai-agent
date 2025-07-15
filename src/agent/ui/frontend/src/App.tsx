import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Eye, EyeOff, Settings, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';
import { useDragging } from './hooks/useDragging';
import { Message } from './types/messages';

const App: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [timer, setTimer] = useState('00:00');
  const [isVisible, setIsVisible] = useState(true);
  const [askInput, setAskInput] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [isElectron, setIsElectron] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { 
    messages, 
    sendMessage, 
    connectionState, 
    isConnected
  } = useAgentWebSocket('ws://localhost:8090/ws');

  // Add dragging functionality
  const { position, isDragging, handleMouseDown } = useDragging({ x: 50, y: 50 });

  // Check if running in Electron
  useEffect(() => {
    setIsElectron(window.electronAPI !== undefined);
    
    // Auto-resize window based on content
    if (window.electronAPI && containerRef.current) {
      const resizeObserver = new ResizeObserver(() => {
        if (containerRef.current && window.electronAPI) {
          const { scrollHeight, scrollWidth } = containerRef.current;
          window.electronAPI.updateContentDimensions?.({ 
            width: Math.min(scrollWidth + 32, 400), 
            height: Math.min(scrollHeight + 32, 600) 
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

  // Timer functionality
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setSeconds(prev => {
          const newSeconds = prev + 1;
          const mins = Math.floor(newSeconds / 60);
          const secs = newSeconds % 60;
          setTimer(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
          return newSeconds;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);

  const toggleRecording = () => {
    if (!isRecording) {
      setSeconds(0);
      setTimer('00:00');
    }
    setIsRecording(!isRecording);
  };

  const handleAskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (askInput.trim() && isConnected) {
      sendMessage(askInput.trim());
      setAskInput('');
    }
  };

  const formatMessage = (message: Message) => {
    if (message.type === 'system') {
      // Check if it's a system command response with emoji indicators
      const isSystemCommand = message.content.includes('🖥️') || message.content.includes('⚙️') || 
                             message.content.includes('💾') || message.content.includes('💿') || 
                             message.content.includes('📸') || message.content.includes('📁');
      
      return (
        <div className="mb-3 p-3 bg-muted rounded-lg border">
          <div className={`text-sm whitespace-pre-wrap font-mono ${isSystemCommand ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
            {message.content}
          </div>
        </div>
      );
    }
    
    if (message.type === 'user') {
      return (
        <div className="mb-3 flex justify-end">
          <div className="bg-primary text-primary-foreground px-4 py-2 rounded-lg max-w-[240px] break-words">
            {message.content}
          </div>
        </div>
      );
    }
    
    if (message.type === 'agent') {
      return (
        <div className="mb-3 flex items-start gap-3">
          <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <div className="bg-card text-card-foreground px-4 py-2 rounded-lg max-w-[240px] break-words border">
            {message.content}
          </div>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div className="min-h-screen bg-transparent p-6">
      {/* Floating Window */}
      <div 
        ref={containerRef}
        className="fixed z-50"
        style={{ 
          left: `${position.x}px`, 
          top: `${position.y}px`,
          cursor: isDragging ? 'grabbing' : 'auto'
        }}
      >
        <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 dark:border-slate-700/30 w-80 floating-chat-container">
          {/* Header with recording controls - Make draggable */}
          <div 
            className={`flex items-center justify-between p-4 border-b border-border/50 select-none ${
              isDragging ? 'cursor-grabbing' : 'cursor-grab'
            }`}
            onMouseDown={handleMouseDown}
          >
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                isRecording ? 'bg-blue-500 animate-pulse' : 
                isConnected ? 'bg-green-500' : 'bg-gray-300'
              }`} />
              <span className="text-sm font-medium text-foreground">
                {isRecording ? timer : 'Local AI Agent'}
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsVisible(!isVisible)}
                className="h-8 w-8 p-0"
              >
                {isVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0"
              >
                <Settings className="h-4 w-4" />
              </Button>
              {isElectron && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => window.electronAPI?.hideWindow?.()}
                  className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                >
                  ×
                </Button>
              )}
            </div>
          </div>

          {/* Ask AI Input */}
          <div className="p-4 border-b border-border/50">
            <form onSubmit={handleAskSubmit} className="flex items-center gap-2">
              <Input
                placeholder={isConnected ? "Ask AI ⌘ ↵" : "Connecting..."}
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
                disabled={!isConnected}
                className="flex-1 bg-muted/50 border-border/50 text-sm"
              />
              <Button
                type="submit"
                size="sm"
                disabled={!isConnected || !askInput.trim()}
                className="px-3 py-1"
              >
                <Send className="h-3 w-3" />
              </Button>
            </form>
            <div className="text-xs text-muted-foreground mt-1">
              Connection: {connectionState}
            </div>
          </div>

          {/* AI Response Area */}
          {isVisible && (
            <div className="p-4 min-h-[200px] max-h-[400px] overflow-y-auto">
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground">
                  <div className="text-4xl mb-4">🤖</div>
                  <p className="text-sm mb-2">Welcome to Local AI Agent</p>
                  <p className="text-xs">Try these commands:</p>
                  <div className="mt-3 space-y-1 text-xs">
                    <p><code className="bg-muted px-1 rounded">/help</code> - Show help</p>
                    <p><code className="bg-muted px-1 rounded">/status</code> - System status</p>
                    <p><code className="bg-muted px-1 rounded">/mcp desktop take_screenshot</code> - Screenshot</p>
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
          )}

          {/* Quick Actions */}
          {isVisible && (
            <div className="p-4 border-t border-border/50">
              <div className="grid grid-cols-2 gap-2 mb-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/mcp desktop take_screenshot')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  📸 Screenshot
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/mcp system get_system_info')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  🖥️ System Info
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/mcp system get_processes')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  ⚙️ Processes
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/mcp system get_memory_info')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  💾 Memory
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/mcp system get_disk_usage')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  💿 Disk
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendMessage('/help')}
                  disabled={!isConnected}
                  className="text-xs"
                >
                  ❓ Help
                </Button>
              </div>
            </div>
          )}

          {/* Footer with mic control */}
          <div className="p-4 flex items-center justify-center border-t border-border/50">
            <Button
              onClick={toggleRecording}
              size="sm"
              variant={isRecording ? "destructive" : "default"}
              className="flex items-center gap-2"
            >
              {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              {isRecording ? 'Stop Listening' : 'Start Listening'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
