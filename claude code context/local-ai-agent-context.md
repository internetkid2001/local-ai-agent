# Local AI Agent with MCP Integration - Complete Development Context

## Project Overview

A sophisticated local AI agent system that orchestrates between local LLMs (via Ollama) and advanced AI services (Claude Code, Google CLI) through Model Context Protocol (MCP) servers. The system provides intelligent computer automation with visual context awareness through periodic screenshots.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                       │
│                    (CLI / Web UI / API)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                    Agent Orchestration Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Task Router │  │ Context Mgr  │  │ Decision Engine        │ │
│  │             │  │              │  │ (Local LLM + Advanced) │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                       MCP Server Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │Filesystem│  │ System   │  │ Desktop  │  │ Advanced AI    │ │
│  │ Server   │  │ Control  │  │Automation│  │ Bridge Server  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Request** → Agent receives natural language command
2. **Context Gathering** → Screenshot capture, system state, file context
3. **Task Analysis** → Local LLM determines complexity and required tools
4. **Execution Strategy**:
   - Simple tasks → Local LLM with MCP servers
   - Complex tasks → Route to Claude Code or Google CLI with context
5. **Action Execution** → MCP servers perform operations
6. **Result Verification** → Screenshot comparison, output validation
7. **User Feedback** → Results presented with explanations

## Detailed Component Specifications

### 1. Agent Orchestration Layer

#### Task Router (`src/agent/task_router.py`)
```python
class TaskRouter:
    """
    Analyzes incoming tasks and routes them to appropriate handlers
    
    Capabilities:
    - Natural language understanding via local LLM
    - Complexity scoring (0-100)
    - Tool requirement analysis
    - Context requirement determination
    """
    
    def analyze_task(self, task: str) -> TaskAnalysis:
        # Returns: complexity_score, required_tools, context_needs
        pass
    
    def route_task(self, analysis: TaskAnalysis) -> ExecutionPlan:
        # Determines: local_execution vs advanced_ai_execution
        pass
```

#### Context Manager (`src/agent/context_manager.py`)
```python
class ContextManager:
    """
    Manages all contextual information for task execution
    
    Features:
    - Screenshot buffer (last N screenshots)
    - System state tracking
    - File system context
    - Task history and outcomes
    - Active window/application tracking
    """
    
    def gather_context(self, context_type: ContextType) -> Context:
        pass
    
    def prepare_for_advanced_ai(self, task: str) -> EnhancedContext:
        # Prepares rich context for Claude Code/Google CLI
        pass
```

#### Decision Engine (`src/agent/decision_engine.py`)
```python
class DecisionEngine:
    """
    Hybrid decision-making system
    
    Local decisions:
    - File operations
    - System queries
    - Simple automation
    
    Advanced AI delegation:
    - Code generation/debugging
    - Complex multi-step workflows
    - Visual understanding tasks
    - Research and analysis
    """
```

### 2. MCP Server Specifications

#### Advanced AI Bridge Server (`mcp-servers/ai_bridge/`)
```python
class AdvancedAIBridgeServer:
    """
    MCP server that interfaces with Claude Code and Google CLI
    
    Capabilities:
    - Execute Claude Code commands with context
    - Run Google CLI operations
    - Stream results back to local agent
    - Handle authentication and rate limiting
    """
    
    tools = [
        {
            "name": "claude_code_execute",
            "description": "Execute complex coding task via Claude Code",
            "parameters": {
                "task": "string",
                "context": "object",
                "files": "array",
                "screenshots": "array"
            }
        },
        {
            "name": "google_cli_search",
            "description": "Perform advanced search via Google CLI",
            "parameters": {
                "query": "string",
                "context": "object"
            }
        }
    ]
```

#### Screenshot Context Server (`mcp-servers/screenshot_context/`)
```python
class ScreenshotContextServer:
    """
    Continuous screenshot capture and analysis
    
    Features:
    - Configurable capture interval (default: 5 seconds)
    - Intelligent change detection
    - OCR for text extraction
    - Window/region tracking
    - Compression and storage optimization
    """
    
    tools = [
        {
            "name": "capture_screenshot",
            "description": "Capture current screen state",
            "parameters": {
                "region": "optional[Rectangle]",
                "include_ocr": "boolean"
            }
        },
        {
            "name": "get_screen_changes",
            "description": "Get changes since last capture",
            "parameters": {
                "since_timestamp": "integer"
            }
        },
        {
            "name": "analyze_ui_element",
            "description": "Analyze specific UI element",
            "parameters": {
                "coordinates": "Point",
                "context_size": "integer"
            }
        }
    ]
```

### 3. Integration Patterns

#### Local LLM Integration
```python
class OllamaIntegration:
    """
    Handles all local LLM operations
    
    Models:
    - llama3.1:8b (primary)
    - mistral:7b (fallback)
    - codellama:7b (code-specific tasks)
    
    Features:
    - Function calling support
    - Streaming responses
    - Context window management (8K tokens)
    - Temperature adjustment based on task type
    """
```

#### Advanced AI Integration
```python
class AdvancedAIIntegration:
    """
    Manages connections to Claude Code and Google CLI
    
    Claude Code usage:
    - Complex code generation
    - Multi-file refactoring
    - Architecture design
    - Debugging with visual context
    
    Google CLI usage:
    - Research tasks
    - Data gathering
    - API interactions
    - Cloud operations
    """
```

### 4. Task Examples and Routing Logic

#### Task Complexity Matrix

| Task Type | Complexity | Routed To | Context Required |
|-----------|------------|-----------|------------------|
| "Create a new Python file" | Low (10) | Local LLM | File system |
| "Organize downloads by type" | Low (20) | Local LLM | File system |
| "Take screenshot of active window" | Low (15) | Local LLM | Desktop state |
| "Debug this Python error" | High (75) | Claude Code | Code + Screenshots |
| "Refactor this codebase" | High (85) | Claude Code | Multiple files + Structure |
| "Research best practices for X" | Medium (60) | Google CLI | Current context |
| "Create full-stack web app" | High (95) | Claude Code | Requirements + Context |
| "Analyze UI and suggest improvements" | High (80) | Claude Code | Screenshots + History |

### 5. Security and Safety Measures

```python
class SecurityManager:
    """
    Comprehensive security framework
    
    Features:
    - Permission levels (Read, Write, Execute, System)
    - Sandboxed file operations
    - Command whitelist/blacklist
    - Rate limiting per operation type
    - Audit logging with rollback capability
    - Human confirmation for destructive operations
    """
    
    SAFE_OPERATIONS = [
        "file_read", "list_directory", "take_screenshot",
        "get_system_info", "search_files"
    ]
    
    REQUIRE_CONFIRMATION = [
        "file_delete", "execute_command", "modify_system_file",
        "install_software", "modify_registry"
    ]
    
    FORBIDDEN_PATTERNS = [
        r"/etc/passwd", r"/etc/shadow", r"~/.ssh/",
        r"*.key", r"*.pem", r"*token*", r"*secret*"
    ]
```

### 6. Configuration Schema

```yaml
# config/agent_config.yaml
agent:
  name: "Local AI Assistant"
  version: "1.0.0"
  
llm:
  provider: "ollama"
  models:
    primary: "llama3.1:8b"
    code: "codellama:7b"
    fallback: "mistral:7b"
  
  context_window: 8192
  max_tokens: 2048
  temperature:
    creative: 0.8
    balanced: 0.5
    precise: 0.2

advanced_ai:
  claude_code:
    enabled: true
    api_key_env: "CLAUDE_CODE_API_KEY"
    max_context_size: 100000
    
  google_cli:
    enabled: true
    auth_path: "~/.config/google-cli/auth.json"
    
screenshot_context:
  enabled: true
  interval_seconds: 5
  max_buffer_size: 20
  compression: "webp"
  quality: 85
  
  regions:
    - name: "main_monitor"
      x: 0
      y: 0
      width: 1920
      height: 1080
      
security:
  sandbox_enabled: true
  require_confirmation: true
  allowed_paths:
    - "~/Documents"
    - "~/Downloads"
    - "~/Desktop"
    - "/tmp"
  
  forbidden_paths:
    - "/etc"
    - "/sys"
    - "/root"
    - "~/.ssh"
    
logging:
  level: "INFO"
  file: "~/.local/share/ai-agent/agent.log"
  max_size_mb: 100
  retention_days: 30
```

### 7. API Interfaces

#### REST API Endpoints
```python
# For web UI or external integrations
endpoints = {
    # Task execution
    "POST /api/task": "Submit a new task",
    "GET /api/task/{id}": "Get task status",
    "GET /api/tasks": "List all tasks",
    
    # Context management
    "GET /api/context/screenshot": "Get latest screenshot",
    "GET /api/context/system": "Get system information",
    "GET /api/context/files": "Get file context",
    
    # Configuration
    "GET /api/config": "Get current configuration",
    "PUT /api/config": "Update configuration",
    
    # Security
    "GET /api/permissions": "Get permission requests",
    "POST /api/permissions/{id}/approve": "Approve permission",
    "POST /api/permissions/{id}/deny": "Deny permission"
}
```

### 8. Development Priorities

#### Phase 1: Foundation (Week 1-2)
1. Basic MCP client implementation
2. Ollama integration with function calling
3. Simple file system operations
4. Basic screenshot capture

#### Phase 2: Intelligence (Week 3-4)
1. Task routing logic
2. Context management system
3. Local LLM decision making
4. Security framework

#### Phase 3: Advanced Integration (Week 5-6)
1. Claude Code MCP server
2. Google CLI MCP server
3. Advanced context preparation
4. Visual understanding integration

#### Phase 4: Polish (Week 7-8)
1. Web UI development
2. Performance optimization
3. Comprehensive testing
4. Documentation and examples

### 9. Testing Strategy

```python
# tests/test_scenarios.py
test_scenarios = [
    {
        "name": "Simple file organization",
        "input": "Organize my downloads folder by file type",
        "expected_routing": "local",
        "verify": ["folder_structure", "file_count"]
    },
    {
        "name": "Complex code generation",
        "input": "Create a React app with TypeScript and Tailwind",
        "expected_routing": "claude_code",
        "verify": ["project_structure", "dependencies", "config_files"]
    },
    {
        "name": "Visual UI analysis",
        "input": "Analyze this app UI and suggest improvements",
        "expected_routing": "claude_code",
        "context": ["screenshot", "app_info"],
        "verify": ["suggestions", "mockups"]
    }
]
```

### 10. Performance Considerations

- **Memory Management**: Limit screenshot buffer, compress images
- **CPU Optimization**: Offload heavy processing to background threads
- **GPU Utilization**: Use for OCR and image analysis where available
- **Response Time**: <100ms for routing, <2s for local tasks, <30s for advanced AI
- **Concurrent Operations**: Queue system for multiple requests

### 11. Error Handling

```python
class ErrorHandler:
    """
    Comprehensive error handling and recovery
    
    Strategies:
    - Automatic retry with exponential backoff
    - Fallback to simpler approach
    - Context preservation for debugging
    - User-friendly error messages
    - Automatic rollback for failed operations
    """
```

### 12. Extensibility

The system should support plugins for:
- Additional MCP servers
- Custom LLM providers
- New UI frameworks
- External tool integrations
- Custom automation workflows

## Implementation Notes

1. **Start Simple**: Begin with basic file operations and gradually add complexity
2. **Test Early**: Implement testing framework from the start
3. **Document Everything**: Inline documentation and API docs
4. **Security First**: Never compromise on security for features
5. **User Experience**: Clear feedback and progress indication
6. **Modular Design**: Each component should be independently testable

## Success Metrics

- Task success rate > 95% for simple operations
- User confirmation that advanced AI routing improves outcomes
- Response time within targets
- Zero security breaches
- Positive user feedback on ease of use