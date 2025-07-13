# Filesystem MCP Server

A secure Model Context Protocol (MCP) server implementation for file system operations with comprehensive sandboxing, search functionality, and security controls.

## Features

### Core Operations
- **File Operations**: Read, write, copy, move, delete files
- **Directory Operations**: Create, list, navigate directories
- **Search**: Pattern-based file search and content search
- **Metadata**: File information, permissions, timestamps

### Security Features
- **Sandboxing**: All operations restricted to configured sandbox directory
- **Path Validation**: Prevents directory traversal attacks
- **File Type Filtering**: Configurable allowed/denied file extensions
- **Size Limits**: Configurable maximum file size limits
- **Read-Only Mode**: Optional read-only operation mode

### Advanced Features
- **Content Search**: Search within file contents with line matching
- **Recursive Operations**: Recursive directory listing and search
- **Hash Generation**: MD5 and SHA256 hashes for file integrity
- **MIME Type Detection**: Automatic content type detection

## Quick Start

### 1. Install Dependencies
```bash
pip install websockets PyYAML
```

### 2. Configure Server
Edit `config.yaml` to set your sandbox directory and security settings:

```yaml
filesystem:
  sandbox_root: "/path/to/your/sandbox"
  allowed_paths:
    - "/path/to/your/sandbox"
  max_file_size: 52428800  # 50MB
  read_only: false
```

### 3. Start Server
```bash
python3 start_server.py --config config.yaml
```

The server will start on `ws://localhost:8765` by default.

### 4. Test Installation
```bash
python3 test_filesystem.py
```

## Configuration

### Server Configuration
```yaml
server:
  host: "localhost"     # WebSocket host
  port: 8765           # WebSocket port

filesystem:
  sandbox_root: "/tmp/mcp_sandbox"    # Root directory for all operations
  allowed_paths:                      # Additional allowed paths
    - "/tmp/mcp_sandbox/documents"
    - "/tmp/mcp_sandbox/workspace"
  
  # Security settings
  max_file_size: 52428800             # 50MB file size limit
  max_search_results: 1000            # Maximum search results
  read_only: false                    # Read-only mode
  
  # File type restrictions
  allowed_extensions: []              # Empty = all allowed (except denied)
  denied_extensions:                  # Blocked file extensions
    - ".exe"
    - ".bat"
    - ".cmd"
```

### Command Line Options
```bash
python3 start_server.py \
  --config config.yaml \
  --host localhost \
  --port 8765 \
  --sandbox /custom/sandbox/path
```

## Available Tools

### File Operations

#### `read_file`
Read contents of a file.
```json
{
  "name": "read_file",
  "arguments": {
    "path": "/sandbox/file.txt",
    "encoding": "utf-8"
  }
}
```

#### `write_file`
Write content to a file.
```json
{
  "name": "write_file",
  "arguments": {
    "path": "/sandbox/new_file.txt",
    "content": "Hello, World!",
    "create_dirs": true
  }
}
```

#### `copy_file`
Copy a file or directory.
```json
{
  "name": "copy_file",
  "arguments": {
    "source": "/sandbox/source.txt",
    "destination": "/sandbox/backup.txt",
    "overwrite": false
  }
}
```

#### `move_file`
Move/rename a file or directory.
```json
{
  "name": "move_file",
  "arguments": {
    "source": "/sandbox/old_name.txt",
    "destination": "/sandbox/new_name.txt"
  }
}
```

#### `delete_file`
Delete a file or directory.
```json
{
  "name": "delete_file",
  "arguments": {
    "path": "/sandbox/unwanted.txt",
    "recursive": false
  }
}
```

### Directory Operations

#### `list_directory`
List contents of a directory.
```json
{
  "name": "list_directory",
  "arguments": {
    "path": "/sandbox",
    "recursive": false,
    "include_hidden": false
  }
}
```

#### `create_directory`
Create a directory.
```json
{
  "name": "create_directory",
  "arguments": {
    "path": "/sandbox/new_folder",
    "parents": true
  }
}
```

### Information and Search

#### `get_file_info`
Get detailed file/directory metadata.
```json
{
  "name": "get_file_info",
  "arguments": {
    "path": "/sandbox/file.txt"
  }
}
```

#### `search_files`
Search for files and directories.
```json
{
  "name": "search_files",
  "arguments": {
    "path": "/sandbox",
    "pattern": "*.py",
    "content_search": "function",
    "case_sensitive": false,
    "max_results": 100
  }
}
```

## Security Model

### Sandboxing
- All file operations are restricted to the configured `sandbox_root` directory
- Path traversal attempts (e.g., `../../../etc/passwd`) are blocked
- Symbolic links outside the sandbox are not followed

### File Type Filtering
- Configure `allowed_extensions` for whitelist approach
- Configure `denied_extensions` for blacklist approach (default includes executable types)
- Extensions are checked on write operations

### Size Limits
- `max_file_size` prevents writing oversized files
- `max_search_results` limits search result sets

### Read-Only Mode
- When enabled, all write operations (create, write, delete, move, copy) are blocked
- Useful for read-only analysis environments

## Integration with Local AI Agent

The filesystem MCP server integrates with the Local AI Agent project to provide secure file system access for AI operations:

1. **Task Execution**: AI agents can read configuration files, logs, and data files
2. **Code Generation**: Agents can write generated code to specific directories
3. **Data Processing**: Process and analyze files within the sandbox
4. **Documentation**: Generate and update documentation files

### Example Integration
```python
from src.mcp_client.client import MCPClient

# Connect to filesystem MCP server
client = MCPClient(config)
await client.initialize()

# Read a configuration file
result = await client.execute_tool("read_file", {
    "path": "/sandbox/config.yaml"
})

# Write generated code
await client.execute_tool("write_file", {
    "path": "/sandbox/generated/script.py",
    "content": generated_code,
    "create_dirs": True
})
```

## Testing

### Core Functionality Test
```bash
python3 test_filesystem.py
```

### WebSocket Integration Test
```bash
# Terminal 1: Start server
python3 start_server.py

# Terminal 2: Run client test
python3 test_client.py
```

## Development

### Project Structure
```
filesystem/
├── server.py              # Main MCP server implementation
├── start_server.py        # Server startup script
├── config.yaml           # Default configuration
├── test_filesystem.py    # Core functionality tests
├── test_client.py        # WebSocket client tests
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Adding New Tools
1. Add tool definition to `_define_tools()` method
2. Implement `_handle_{tool_name}()` method
3. Add security validation as needed
4. Update tests and documentation

## Error Handling

The server provides detailed error responses:

- **Security Errors**: Path outside sandbox, forbidden file types
- **File System Errors**: File not found, permission denied, disk full
- **Validation Errors**: Invalid parameters, missing required fields
- **Protocol Errors**: Invalid JSON, unknown methods

## Performance Considerations

- File operations are asynchronous to prevent blocking
- Search operations have configurable result limits
- Large files are read in chunks where possible
- Memory usage is minimized for file operations

## License

Part of the Local AI Agent project. See main project LICENSE for details.