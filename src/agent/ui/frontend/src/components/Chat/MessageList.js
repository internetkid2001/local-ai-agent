import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';

export function MessageList({ messages }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-white/50 text-[13px]">
          <div className="text-center">
            <div className="mb-2">👋</div>
            <div>Welcome to Local AI Agent</div>
            <div className="text-[11px] mt-1">Start a conversation to get help</div>
          </div>
        </div>
      ) : (
        messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}