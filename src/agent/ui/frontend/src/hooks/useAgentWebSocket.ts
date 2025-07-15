import { useState, useEffect, useRef, useCallback } from 'react';
import { Message, AgentStatus, MCPServers, WebSocketHook } from '../types/messages';

export function useAgentWebSocket(url: string): WebSocketHook {
  const [connectionState, setConnectionState] = useState<string>('Connecting');
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({});
  const [mcpServers, setMcpServers] = useState<MCPServers>({});
  const websocket = useRef<WebSocket | null>(null);

  useEffect(() => {
    websocket.current = new WebSocket(url);

    websocket.current.onopen = () => {
      console.log('WebSocket Connected to AI Agent');
      setConnectionState('Connected');
      
      // Request initial status
      websocket.current?.send(JSON.stringify({
        type: 'status_request'
      }));
      
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'Connected to Local AI Agent with MCP capabilities.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15)
      }]);
    };

    websocket.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connection_status':
          if (data.connected) {
            setMessages((prev) => [...prev, { 
              type: 'system', 
              content: data.message || 'Connected to Local AI Agent',
              timestamp: Date.now(),
              id: Math.random().toString(36).substring(2, 15)
            }]);
            if (data.help) {
              setMessages((prev) => [...prev, { 
                type: 'system', 
                content: data.help,
                timestamp: Date.now(),
                id: Math.random().toString(36).substring(2, 15)
              }]);
            }
          }
          break;
          
        case 'command_result':
          setMessages((prev) => [...prev, { 
            type: 'system', 
            content: data.message,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15)
          }]);
          break;
          
        case 'ai_response':
          setMessages((prev) => [...prev, { 
            type: 'agent', 
            content: data.message,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15),
            role: data.role || 'assistant'
          }]);
          break;
          
        case 'response':
          setMessages((prev) => [...prev, { 
            type: 'agent', 
            content: data.content,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15),
            metadata: data.metadata || {}
          }]);
          break;
          
        case 'stream_chunk':
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
          break;
          
        case 'stream_end':
          console.log('Stream ended for request:', data.request_id);
          break;
          
        case 'error':
          setMessages((prev) => [...prev, { 
            type: 'system', 
            content: `Error: ${data.message}`,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15),
            isError: true
          }]);
          break;
          
        case 'agent_status':
          setAgentStatus(data.status || {});
          break;
          
        case 'mcp_status':
          setMcpServers(data.servers || {});
          break;
          
        case 'task_progress':
          // Handle task progress updates
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.type === 'progress') {
              return [...prev.slice(0, -1), {
                ...lastMessage,
                content: data.message,
                progress: data.progress
              }];
            }
            return [...prev, {
              type: 'progress',
              content: data.message,
              progress: data.progress,
              timestamp: Date.now(),
              id: Math.random().toString(36).substring(2, 15)
            }];
          });
          break;
          
        case 'mcp_result':
          // Handle MCP operation results
          setMessages((prev) => [...prev, {
            type: 'mcp_result',
            content: `MCP ${data.server}: ${data.operation} completed`,
            result: data.result,
            timestamp: Date.now(),
            id: Math.random().toString(36).substring(2, 15)
          }]);
          break;
          
        default:
          console.log('Unknown message type:', data);
      }
    };

    websocket.current.onclose = () => {
      console.log('WebSocket Disconnected from AI Agent');
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
        id: Math.random().toString(36).substring(2, 15),
        isError: true
      }]);
    };

    return () => {
      websocket.current?.close();
    };
  }, [url]);

  const sendMessage = useCallback((content: string, options: Record<string, any> = {}) => {
    if (!content.trim()) return;

    const userMessage: Message = { 
      type: 'user', 
      content,
      timestamp: Date.now(),
      id: Math.random().toString(36).substring(2, 15)
    };
    setMessages((prev) => [...prev, userMessage]);

    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      websocket.current.send(JSON.stringify({
        type: 'chat_message',
        message: content,
        history: messages.slice(-10).map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content
        }))
      }));
    } else {
      setMessages((prev) => [...prev, { 
        type: 'system', 
        content: 'Not connected to MCP Chat Bridge.',
        timestamp: Date.now(),
        id: Math.random().toString(36).substring(2, 15),
        isError: true
      }]);
    }
  }, [messages]);

  const sendMCPCommand = useCallback((server: string, operation: string, params: Record<string, any> = {}) => {
    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      websocket.current.send(JSON.stringify({
        type: 'mcp_command',
        server,
        operation,
        params
      }));
    }
  }, []);

  const requestStatus = useCallback(() => {
    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      websocket.current.send(JSON.stringify({
        type: 'status_request'
      }));
    }
  }, []);

  return {
    messages,
    sendMessage,
    sendMCPCommand,
    requestStatus,
    connectionState,
    isConnected: connectionState === 'Connected',
    agentStatus,
    mcpServers
  };
}