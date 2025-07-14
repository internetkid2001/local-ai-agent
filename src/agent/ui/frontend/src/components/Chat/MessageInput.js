import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export function MessageInput({ onSendMessage, disabled = false, isLoading = false }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-3 bg-black/20 backdrop-blur-sm rounded-b-xl">
      <div className="flex-1 relative">
        <textarea
          className={cn(
            "w-full bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3",
            "text-white placeholder-white/50 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50",
            "transition-all duration-200 text-[13px] leading-relaxed",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          rows={1}
          style={{ 
            minHeight: '44px',
            maxHeight: '120px',
            overflow: 'hidden'
          }}
          onInput={(e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
          }}
        />
      </div>
      <button
        type="submit"
        disabled={!input.trim() || disabled || isLoading}
        className={cn(
          "flex items-center justify-center w-11 h-11 rounded-xl",
          "bg-blue-600/80 hover:bg-blue-500/80 backdrop-blur-sm",
          "text-white transition-all duration-200 shadow-lg",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600/80"
        )}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </button>
    </form>
  );
}