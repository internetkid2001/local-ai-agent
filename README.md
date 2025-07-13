# Local AI Agent with MCP Integration

A locally running AI agent that can interact with your computer through Model Context Protocol (MCP) servers to help manage files, automate tasks, and provide intelligent assistance.

## System Specifications
- **CPU**: AMD Ryzen 7 3700X (8 cores, 16 threads, 3.6-4.4 GHz)
- **RAM**: 31.28 GB (27 GB available)
- **GPU**: AMD Radeon RX 6600 XT (~8GB VRAM)
- **OS**: Linux (Ubuntu-based)

## Project Structure

```
local-ai-agent/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── setup.sh                 # Installation script
├── src/                     # Main application code
│   ├── agent/               # AI agent implementation
│   ├── mcp_client/          # MCP client integration
│   ├── ui/                  # User interface
│   └── utils/               # Utility functions
├── mcp-servers/             # Custom MCP server implementations
│   ├── filesystem/          # File management server
│   ├── system/              # System control server
│   └── desktop/             # Desktop automation server
├── config/                  # Configuration files
│   ├── agent_config.yaml    # Agent settings
│   └── mcp_servers.json     # MCP server configurations
├── docs/                    # Documentation and references
│   ├── mcp-reference.md     # MCP protocol documentation
│   ├── ollama-setup.md      # Local LLM setup guide
│   ├── architecture.md      # System architecture
│   └── api-examples/        # Code examples and tutorials
└── examples/                # Working examples
    ├── basic_agent.py       # Simple agent implementation
    ├── file_manager.py      # File management examples
    └── automation_tasks.py  # Task automation examples
```

## Key Components

### 1. Local Language Model
- **Primary**: Llama 3.1 8B via Ollama
- **Alternative**: Mistral 7B, CodeLlama 7B
- **Interface**: Ollama REST API

### 2. MCP Servers
- **File System**: Read/write files, directory operations, search
- **System Control**: Execute commands, process management, monitoring
- **Desktop Automation**: GUI interaction, screenshots, window management

### 3. Agent Framework
- **Core**: Python-based agent with function calling
- **LLM Integration**: Ollama API client
- **MCP Integration**: Custom MCP client implementation
- **UI**: Command-line interface with optional web UI

## Features

### File Management
- Organize files by type, date, or custom criteria
- Search files by content, metadata, or patterns
- Automated backup and synchronization
- Duplicate file detection and cleanup

### System Automation
- Monitor system resources and performance
- Automated software installation and updates
- Process management and cleanup
- Log analysis and reporting

### Desktop Integration
- Screenshot analysis and OCR
- Window management and automation
- Keyboard/mouse automation for repetitive tasks
- Application launching and control

## Installation

1. **Install Ollama and download models**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3.1:8b
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure MCP servers**:
   ```bash
   ./setup.sh
   ```

4. **Run the agent**:
   ```bash
   python src/main.py
   ```

## Security Considerations

- **Sandboxing**: Limited file system access by default
- **Permission System**: Explicit approval for sensitive operations
- **Audit Logging**: All actions logged with timestamps
- **Rate Limiting**: Prevents runaway automation
- **Safe Mode**: Restricted operations for initial testing

## Development Roadmap

### Phase 1: Core Infrastructure
- [x] Project setup and documentation
- [ ] Basic MCP client implementation
- [ ] Ollama integration
- [ ] Simple file operations

### Phase 2: Agent Implementation
- [ ] Core agent logic with function calling
- [ ] Natural language command parsing
- [ ] Error handling and recovery
- [ ] Basic UI implementation

### Phase 3: Advanced Features
- [ ] Desktop automation capabilities
- [ ] System monitoring and alerts
- [ ] Task scheduling and automation
- [ ] Web-based management interface

### Phase 4: Optimization
- [ ] Performance tuning
- [ ] Advanced security features
- [ ] Plugin system for extensibility
- [ ] Documentation and tutorials

## Contributing

This is a personal project, but contributions and suggestions are welcome. Please see the documentation for development guidelines.

## License

MIT License - See LICENSE file for details.
