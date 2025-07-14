import React from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '../ui/card';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ConnectionStatus } from '../Agent/ConnectionStatus';
import { GripHorizontal, Minimize2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export function ChatContainer({ 
  messages, 
  onSendMessage, 
  connectionState, 
  isConnected, 
  position, 
  isDragging, 
  onMouseDown,
  onMinimize,
  isMinimized = false 
}) {
  if (isMinimized) {
    return (
      <div
        className="fixed z-50 w-12 h-12 bg-blue-600/80 backdrop-blur-md rounded-full shadow-2xl cursor-pointer flex items-center justify-center border border-white/20 hover:scale-105 transition-transform duration-200"
        style={{ left: position.x, top: position.y }}
        onClick={onMinimize}
      >
        <span className="text-white font-bold text-sm">AI</span>
      </div>
    );
  }

  return (
    <Card
      className={cn(
        "fixed z-50 flex flex-col overflow-hidden transition-all duration-300",
        isDragging && "scale-105 shadow-2xl"
      )}
      style={{ 
        left: position.x, 
        top: position.y, 
        width: '380px', 
        height: '520px' 
      }}
    >
      <CardHeader className="pb-2 relative">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            Local AI Agent
          </CardTitle>
          <div className="flex items-center gap-2">
            <ConnectionStatus connectionState={connectionState} />
            <button
              onClick={onMinimize}
              className="p-1 rounded-md hover:bg-white/10 transition-colors duration-200"
            >
              <Minimize2 className="w-4 h-4 text-white/70" />
            </button>
          </div>
        </div>
        
        {/* Drag Handle */}
        <div
          className="absolute inset-x-0 top-0 h-8 flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
          onMouseDown={onMouseDown}
        >
          <GripHorizontal className="w-4 h-4 text-white/30" />
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        <MessageList messages={messages} />
        <MessageInput 
          onSendMessage={onSendMessage} 
          disabled={!isConnected}
          isLoading={connectionState === 'Connecting'}
        />
      </CardContent>
    </Card>
  );
}