import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url) {
  const [connectionState, setConnectionState] = useState('Connecting');
  const [messages, setMessages] = useState([]);
  const websocket = useRef(null);

  useEffect(() => {
    websocket.current = new WebSocket(url);

    websocket.current.onopen = () => {
      console.log('WebSocket Connected');
      setConnectionState('Connected');
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'Connected to AI Agent.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15)
      }]);
    };

    websocket.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'response') {
        setMessages((prev) => [...prev, { 
          type: 'agent', 
          content: data.content,
          timestamp: Date.now(),
          id: Math.random().toString(36).substring(2, 15)
        }]);
      } else if (data.type === 'stream_chunk') {
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.type === 'agent' && lastMessage.request_id === data.request_id) {
            return [...prev.slice(0, -1), { 
              ...lastMessage, 
              content: lastMessage.content + data.content 
            }];
          }
          return [...prev, { 
            type: 'agent', 
            content: data.content, 
            request_id: data.request_id,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15)
          }];
        });
      } else if (data.type === 'stream_end') {
        console.log('Stream ended for request:', data.request_id);
      } else if (data.type === 'error') {
        setMessages((prev) => [...prev, { 
          type: 'system', 
          content: `Error: ${data.message}`,
          timestamp: Date.now(),
          id: Math.random().toString(36).substring(2, 15)
        }]);
      }
    };

    websocket.current.onclose = () => {
      console.log('WebSocket Disconnected');
      setConnectionState('Disconnected');
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'Disconnected from AI Agent.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15)
      }]);
    };

    websocket.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setConnectionState('Error');
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'WebSocket error occurred.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15)
      }]);
    };

    return () => {
      websocket.current.close();
    };
  }, [url]);

  const sendMessage = useCallback((content) => {
    if (!content.trim()) return;

    const userMessage = { 
      type: 'user', 
      content,
      timestamp: Date.now(),
      id: Math.random().toString(36).substring(2, 15)
    };
    setMessages((prev) => [...prev, userMessage]);

    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      websocket.current.send(JSON.stringify({
        type: 'chat',
        content,
        stream: true,
      }));
    } else {
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'WebSocket not connected.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15)
      }]);
    }
  }, []);

  return {
    messages,
    sendMessage,
    connectionState,
    isConnected: connectionState === 'Connected'
  };
}