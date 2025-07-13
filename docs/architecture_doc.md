# System Architecture

## Overview

The Local AI Agent system is designed as a modular, secure, and extensible platform that connects a local language model with system capabilities through the Model Context Protocol (MCP).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                     │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   CLI Interface │   Web Interface │     API Interface           │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent Core                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Task Planning  │  Command Parser │    Response Generator       │
│                 │                 │                             │
│  • Intent       │  • NL to        │  • Format responses         │
│    Recognition  │    Function     │  • Error handling           │
│  • Multi-step   │    Calls        │  • User feedback            │
│    Planning     │  • Parameter    │                             │
│  • Error        │    Validation   │                             │
│    Recovery     │                 │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Integration Layer                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Ollama Client │  Function Call  │    Context Management       │
│                 │   Handler       │                             │
│  • Model        │  • Tool         │  • Conversation history     │
│    Management   │    Registration │  • Memory management        │
│  • API calls    │  • Parameter    │  • Context switching        │
│  • Streaming    │    Mapping      │                             │
│  • Error        │  • Result       │                             │
│    Handling     │    Processing   │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Client Layer                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Server Manager  │  Protocol       │    Security Manager         │
│                 │  Handler        │                             │
│ • Connection    │  • Message      │  • Permission control       │
│   Management    │    Routing      │  • Audit logging            │
│ • Health        │  • Serialization│  • Rate limiting            │
│   Monitoring    │  • Error        │  • Safe mode                │
│ • Auto-reconnect│    Handling     │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Servers                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Filesystem      │   System        │    Desktop                  │
│ Server          │   Server        │    Server                   │
│                 │                 │                             │
│ • File ops      │ • Process mgmt  │ • Screenshot                │
│ • Directory     │ • System info   │ • GUI automation            │
│   operations    │ • Command exec  │ • Window mgmt               │
│ • Search        │ • Monitoring    │ • OCR                       │
│ • Metadata      │ • Service ctrl  │ • Mouse/keyboard            │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────────┐
│                    System Resources                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   File System   │  System APIs    │    Desktop Environment      │
│                 │                 │                             │
│ • /home/vic     │ • Process API   │ • X11/Wayland               │
│ • /tmp          │ • System calls  │ • Window manager            │
│ • Network       │ • Hardware      │ • Applications              │
│   storage       │   monitoring    │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Component Details

### 1. User Interface Layer

#### CLI Interface
- **Purpose**: Primary interaction method for development and power users
- **Features**: 
  - Real-time conversation
  - Command history
  - Progress indicators
  - Error display
- **Implementation**: Python with `rich` for enhanced display

#### Web Interface (Future)
- **Purpose**: User-friendly browser-based interface
- **Features**:
  - Chat interface
  - File browser
  - Task dashboard
  - Settings panel
- **Technology**: FastAPI + React/Vue.js

#### API Interface
- **Purpose**: Programmatic access for integrations
- **Features**:
  - RESTful endpoints
  - WebSocket for real-time updates
  - Authentication
  - Rate limiting
- **Technology**: FastAPI with async support

### 2. AI Agent Core

#### Task Planning
```python
class TaskPlanner:
    def __init__(self):
        self.current_context = {}
        self.task_queue = []
    
    async def plan_task(self, user_request: str) -> List[Step]:
        """Break down user request into executable steps"""
        # 1. Analyze intent
        intent = await self.analyze_intent(user_request)
        
        # 2. Identify required capabilities
        capabilities = self.identify_capabilities(intent)
        
        # 3. Create execution plan
        plan = self.create_execution_plan(capabilities)
        
        # 4. Validate plan safety
        validated_plan = self.validate_safety(plan)
        
        return validated_plan
```

#### Command Parser
```python
class CommandParser:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.available_tools = {}
    
    async def parse_to_function_calls(self, llm_response) -> List[FunctionCall]:
        """Convert LLM response to MCP function calls"""
        if "tool_calls" in llm_response:
            return [
                FunctionCall(
                    server=self.map_to_server(call["function"]["name"]),
                    tool=call["function"]["name"],
                    args=call["function"]["arguments"]
                )
                for call in llm_response["tool_calls"]
            ]
        return []
```

### 3. LLM Integration Layer

#### Ollama Client
```python
class OllamaClient:
    def __init__(self, model="llama3.1:8b"):
        self.model = model
        self.session = None
        self.context_window = 4096
        
    async def generate_with_tools(self, prompt: str, tools: List[Tool]) -> Response:
        """Generate response with function calling capability"""
        formatted_tools = self.format_tools_for_ollama(tools)
        
        response = await self.api_call({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": formatted_tools,
            "stream": False
        })
        
        return self.parse_response(response)
```

### 4. MCP Client Layer

#### Server Manager
```python
class MCPServerManager:
    def __init__(self):
        self.servers = {}
        self.health_checks = {}
        
    async def start_server(self, name: str, config: ServerConfig):
        """Start and register an MCP server"""
        server = MCPServer(name, config.command, config.env)
        await server.start()
        
        self.servers[name] = server
        self.health_checks[name] = asyncio.create_task(
            self.monitor_server_health(server)
        )
    
    async def monitor_server_health(self, server: MCPServer):
        """Monitor server health and restart if needed"""
        while True:
            try:
                await server.ping()
                await asyncio.sleep(30)
            except Exception:
                logger.warning(f"Server {server.name} is unhealthy, restarting...")
                await self.restart_server(server.name)
```

### 5. Security Architecture

#### Permission System
```python
class PermissionManager:
    def __init__(self):
        self.permissions = self.load_permissions()
        self.audit_log = AuditLogger()
    
    async def check_permission(self, action: str, resource: str) -> bool:
        """Check if action on resource is permitted"""
        permission_key = f"{action}:{resource}"
        
        # Check explicit permissions
        if permission_key in self.permissions.get("allow", []):
            self.audit_log.log_action(action, resource, "ALLOWED")
            return True
            
        # Check deny list
        if permission_key in self.permissions.get("deny", []):
            self.audit_log.log_action(action, resource, "DENIED")
            return False
            
        # Default to safe mode
        return await self.prompt_user_permission(action, resource)
```

#### Safe Mode Implementation
```python
class SafeMode:
    SAFE_OPERATIONS = {
        "filesystem": ["read_file", "list_directory"],
        "system": ["get_system_info", "get_processes"],
        "desktop": ["take_screenshot"]
    }
    
    def is_operation_safe(self, server: str, operation: str) -> bool:
        return operation in self.SAFE_OPERATIONS.get(server, [])
    
    async def execute_with_safety(self, server: str, operation: str, args: dict):
        if not self.is_operation_safe(server, operation):
            confirmation = await self.request_user_confirmation(
                f"Execute {operation} on {server}?"
            )
            if not confirmation:
                raise PermissionDeniedError("User denied operation")
        
        return await self.mcp_client.call_tool(server, operation, args)
```

## Data Flow

### 1. User Request Processing
```
User Input → Intent Analysis → Task Planning → Execution Plan → LLM Processing
```

### 2. Function Call Execution
```
LLM Response → Function Call Parsing → Permission Check → MCP Server Call → Result Processing
```

### 3. Error Handling
```
Error Detection → Classification → Recovery Strategy → User Notification → State Recovery
```

## Configuration Management

### Main Configuration Structure
```yaml
# config/agent_config.yaml
agent:
  model: "llama3.1:8b"
  max_context: 4096
  temperature: 0.7
  safe_mode: true

servers:
  filesystem:
    enabled: true
    allowed_paths:
      - "/home/vic/Documents"
      - "/home/vic/Downloads"
    
  system:
    enabled: true
    safe_mode: true
    allowed_commands:
      - "ls"
      - "ps"
      - "top"
    
  desktop:
    enabled: false  # Requires explicit enabling
    screenshot_dir: "/tmp/screenshots"

security:
  audit_logging: true
  require_confirmation: true
  rate_limits:
    filesystem: 100  # operations per minute
    system: 50
    desktop: 20

ui:
  interface: "cli"  # cli, web, api
  log_level: "INFO"
  show_internal_logs: false
```

## Deployment Architecture

### Development Setup
```
Local Machine:
├── Ollama Service (port 11434)
├── MCP Servers (stdio)
├── Agent Core (Python)
└── CLI Interface
```

### Production Setup (Future)
```
Local Machine:
├── Ollama Service
├── MCP Servers (stdio/unix sockets)
├── Agent Core (systemd service)
├── Web UI (nginx)
└── API Gateway (authentication)
```

## Monitoring and Observability

### Metrics Collection
- **Performance**: Response times, token generation speed
- **Usage**: Function calls per minute, popular operations
- **Health**: Server uptime, error rates
- **Security**: Failed permission checks, suspicious activities

### Logging Strategy
```python
# Structured logging
{
    "timestamp": "2025-07-10T21:30:00Z",
    "level": "INFO",
    "component": "mcp_client",
    "action": "call_tool",
    "server": "filesystem",
    "tool": "read_file",
    "args": {"path": "/home/vic/test.txt"},
    "duration_ms": 15,
    "success": true
}
```

## Scalability Considerations

### Current Limitations
- Single-threaded LLM inference
- Local-only operation
- Limited by system resources

### Future Enhancements
- Multi-model support
- Distributed MCP servers
- Cloud integration options
- Plugin architecture for custom capabilities

This architecture provides a solid foundation for a local AI agent while maintaining security, extensibility, and performance.