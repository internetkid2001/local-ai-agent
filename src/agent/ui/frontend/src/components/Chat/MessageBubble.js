import React from 'react';
import { cn } from '../../lib/utils';
import { formatTime } from '../../lib/utils';
import { User, Bot, AlertCircle } from 'lucide-react';

export function MessageBubble({ message }) {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';
  const isAgent = message.type === 'agent';

  const getIcon = () => {
    if (isUser) return <User className="w-4 h-4" />;
    if (isSystem) return <AlertCircle className="w-4 h-4" />;
    if (isAgent) return <Bot className="w-4 h-4" />;
    return null;
  };

  const getBubbleStyles = () => {
    if (isUser) {
      return "bg-blue-600/80 backdrop-blur-sm text-white ml-8";
    }
    if (isSystem) {
      return "bg-yellow-600/20 backdrop-blur-sm text-yellow-200 border border-yellow-600/30 mx-4";
    }
    if (isAgent) {
      return "bg-gray-700/80 backdrop-blur-sm text-gray-100 mr-8";
    }
    return "bg-gray-600/80 backdrop-blur-sm text-white";
  };

  return (
    <div className={cn(
      "mb-3 animate-in fade-in duration-200",
      isUser ? "flex justify-end" : "flex justify-start"
    )}>
      <div className={cn(
        "max-w-[80%] rounded-2xl px-4 py-3 shadow-lg",
        getBubbleStyles()
      )}>
        <div className="flex items-start gap-2">
          <div className="mt-0.5 opacity-70">
            {getIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </div>
            {message.timestamp && (
              <div className="text-[11px] opacity-50 mt-1">
                {formatTime(message.timestamp)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}