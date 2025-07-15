export interface Message {
  id: string;
  type: 'user' | 'agent' | 'system' | 'progress' | 'mcp_result';
  content: string;
  timestamp: number;
  role?: string;
  request_id?: string;
  metadata?: Record<string, any>;
  isError?: boolean;
  progress?: number;
  result?: any;
}

export interface AgentStatus {
  [key: string]: any;
}

export interface MCPServers {
  [key: string]: any;
}

export interface WebSocketHook {
  messages: Message[];
  sendMessage: (content: string, options?: Record<string, any>) => void;
  sendMCPCommand: (server: string, operation: string, params?: Record<string, any>) => void;
  requestStatus: () => void;
  connectionState: string;
  isConnected: boolean;
  agentStatus: AgentStatus;
  mcpServers: MCPServers;
}
