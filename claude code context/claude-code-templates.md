# Claude Code Development Templates & Clarifications

## 1. Initial Project Setup Template

### First Message to Claude Code (Session 1.1)

```markdown
I need you to develop a Local AI Agent with MCP Integration. Here are your resources:

1. CONTEXT DOCUMENT: [Paste the complete context document]
2. DEVELOPMENT PLAN: [Paste the development plan]

Please start with Session 1.1: Project Setup & Basic MCP Client

First, initialize the project:
- Create the directory structure as specified
- Set up git repository
- Create initial documentation files
- Begin with the basic MCP client implementation

Update progress files as you work. Commit every 30-45 minutes with the format: [PHASE-1] Component: Description

Let me know when you need to switch to a new chat instance (around 70% token usage).
```

## 2. Progress Tracking Templates

### COMPLETION_STATUS.md Template

```markdown
# Local AI Agent - Overall Completion Status

Last Updated: [DATE TIME]
Current Phase: 1
Current Session: 1.1
Overall Progress: 5%

## Phase 1: Foundation
- [ ] Session 1.1: Project Setup & Basic MCP Client
  - [x] Project structure created
  - [x] Git repository initialized
  - [ ] Basic MCP client connection
  - [ ] Configuration system
  - [ ] Logging framework
  - [ ] Initial tests
- [ ] Session 1.2: Ollama Integration
  - [ ] Ollama client wrapper
  - [ ] Function calling support
  - [ ] Prompt templates
  - [ ] Context window management
  - [ ] Streaming responses
- [ ] Session 1.3: File System MCP Server
  - [ ] Filesystem server implementation
  - [ ] Security sandboxing
  - [ ] File operation tools
  - [ ] Search functionality
  - [ ] Error handling

## Phase 2: Core Agent Intelligence
[List all sessions with checkboxes]

## Phase 3: Advanced AI Integration
[List all sessions with checkboxes]

## Phase 4: User Interface & Polish
[List all sessions with checkboxes]

## Test Coverage
- Unit Tests: 0%
- Integration Tests: 0%
- Total Coverage: 0%

## Critical Decisions Made
1. [Date] - Decision about X
2. [Date] - Choice of Y over Z
```

### ARCHITECTURE_DECISIONS.md Template

```markdown
# Architecture Decision Records

## ADR-001: MCP Client Architecture
**Date**: [DATE]
**Status**: Accepted

### Context
We need a robust MCP client that can handle multiple server connections.

### Decision
Implement an async-first architecture using Python's asyncio with connection pooling.

### Consequences
- **Positive**: Better performance, handles concurrent operations
- **Negative**: More complex error handling
- **Neutral**: Requires Python 3.8+

### Implementation Notes
- Base class in `src/mcp_client/base_client.py`
- Connection pooling in `src/mcp_client/connection_pool.py`

---

## ADR-002: Screenshot Storage Strategy
**Date**: [DATE]
**Status**: Proposed

### Context
Need to store screenshots efficiently without consuming too much disk space.

### Options Considered
1. Raw PNG files - Simple but large
2. WebP compression - Good quality/size ratio
3. In-memory only - Fast but limited history

### Decision
[To be made]

### Consequences
[To be documented after decision]
```

## 3. Testing Strategy Templates

### Test Structure for Each Component

```python
# tests/test_[component].py template

import pytest
from unittest.mock import Mock, patch
import asyncio

class Test[ComponentName]:
    """
    Test suite for [Component]
    
    Coverage targets:
    - Happy path scenarios
    - Error conditions
    - Edge cases
    - Integration points
    """
    
    @pytest.fixture
    def component(self):
        """Create component instance for testing"""
        # Setup code here
        pass
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies"""
        # Mock setup here
        pass
    
    # Unit Tests
    def test_initialization(self, component):
        """Test component initializes correctly"""
        assert component is not None
        # Add specific initialization checks
    
    def test_basic_functionality(self, component):
        """Test core functionality works"""
        # Test implementation
        pass
    
    # Error Handling Tests  
    def test_handles_connection_error(self, component, mock_dependencies):
        """Test graceful handling of connection errors"""
        # Test error scenarios
        pass
    
    # Integration Tests (marked for separate run)
    @pytest.mark.integration
    async def test_real_connection(self):
        """Test with real dependencies (not mocked)"""
        # Real integration test
        pass
```

### Testing Checklist for Claude Code

```markdown
# Testing Checklist for Each Component

## Unit Tests
- [ ] All public methods have tests
- [ ] Error conditions are tested
- [ ] Edge cases covered (empty input, None, etc.)
- [ ] Mocks used for external dependencies

## Integration Tests  
- [ ] Component interacts correctly with dependencies
- [ ] Real file system operations work (in temp directory)
- [ ] Network calls handled properly
- [ ] Timeout scenarios tested

## Performance Tests
- [ ] Large input handling
- [ ] Concurrent operation handling
- [ ] Memory usage stays reasonable
- [ ] Response times within targets

## Documentation Tests
- [ ] All examples in docstrings work
- [ ] README examples are accurate
- [ ] API documentation matches implementation
```

## 4. Code Organization Patterns

### Standard File Header Template

```python
"""
Module: [module_name]
Purpose: [Brief description]

This module implements [detailed description].

Key Classes:
    - ClassName: Brief description
    
Key Functions:
    - function_name: Brief description

Dependencies:
    - External: [list external packages]
    - Internal: [list internal modules]

Author: Claude Code
Date: [DATE]
Session: [X.Y]
"""

from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)
```

### Standard Class Template

```python
@dataclass
class ComponentConfig:
    """Configuration for Component"""
    param1: str
    param2: int = 10
    param3: Optional[Dict[str, Any]] = None

class Component(ABC):
    """
    Brief description of component.
    
    Longer description explaining purpose, design decisions,
    and important implementation notes.
    
    Attributes:
        config: Configuration object
        state: Current component state
        
    Example:
        >>> component = Component(config)
        >>> result = component.process(data)
    """
    
    def __init__(self, config: ComponentConfig):
        """
        Initialize component.
        
        Args:
            config: Configuration object
            
        Raises:
            ValueError: If config is invalid
        """
        self.config = config
        self._validate_config()
        self._state = self._initialize_state()
        logger.info(f"Initialized {self.__class__.__name__}")
    
    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if not self.config.param1:
            raise ValueError("param1 cannot be empty")
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data - must be implemented by subclasses."""
        pass
```

## 5. Git Workflow Clarifications

### Commit Message Examples

```bash
# Feature implementation
git commit -m "[PHASE-1] MCP Client: Add async connection handling with retry logic"

# Bug fix
git commit -m "[PHASE-1] MCP Client: Fix timeout error in connection pool"

# Tests
git commit -m "[PHASE-1] Tests: Add unit tests for MCP client connection"

# Documentation
git commit -m "[PHASE-1] Docs: Update architecture decisions for screenshot storage"

# Refactoring
git commit -m "[PHASE-2] Refactor: Extract task analysis logic into separate module"

# Work in progress (if needed to save state)
git commit -m "[PHASE-2] WIP: Partial implementation of context manager"
```

### Branch Management

```bash
# Development branches
dev-phase-1   # Active development for phase 1
dev-phase-2   # Created after phase 1 complete

# Feature branches (if needed for complex features)
feature/advanced-screenshot-analysis
feature/claude-code-integration

# Main branch
main          # Stable, tested code only
```

## 6. Error Handling Patterns

### Standard Error Handling Template

```python
class MCPError(Exception):
    """Base exception for MCP-related errors"""
    pass

class ConnectionError(MCPError):
    """Raised when MCP connection fails"""
    pass

class SecurityError(MCPError):
    """Raised when security policy is violated"""
    pass

def safe_operation(func):
    """Decorator for safe operation execution"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            logger.error(f"Timeout in {func.__name__}")
            raise ConnectionError(f"Operation timed out: {func.__name__}")
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            # Log detailed error but return sanitized message
            raise MCPError(f"Operation failed: {func.__name__}")
    return wrapper
```

## 7. Configuration Management

### Environment Setup Template (.env.example)

```bash
# Local AI Agent Environment Configuration

# LLM Settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=30

# Advanced AI Integration
CLAUDE_CODE_API_KEY=your_api_key_here
GOOGLE_CLI_AUTH_PATH=~/.config/google-cli/auth.json

# Security Settings
SANDBOX_ENABLED=true
REQUIRE_CONFIRMATION=true
MAX_FILE_SIZE_MB=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=~/.local/share/ai-agent/agent.log

# Screenshot Settings
SCREENSHOT_INTERVAL=5
SCREENSHOT_FORMAT=webp
SCREENSHOT_QUALITY=85

# Development Settings
DEBUG_MODE=false
TEST_MODE=false
```

### Configuration Validation

```python
class ConfigValidator:
    """Validate and sanitize configuration"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration and provide defaults.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration
            
        Raises:
            ValueError: If required config is missing
        """
        required = ['ollama_host', 'ollama_model']
        
        for key in required:
            if key not in config:
                raise ValueError(f"Missing required config: {key}")
        
        # Apply defaults
        defaults = {
            'ollama_timeout': 30,
            'screenshot_interval': 5,
            'log_level': 'INFO',
            'sandbox_enabled': True
        }
        
        for key, value in defaults.items():
            config.setdefault(key, value)
        
        return config
```

## 8. Session Handoff Checklist

### Before Ending a Claude Code Session

```markdown
## Session End Checklist

- [ ] All code changes committed and pushed
- [ ] Tests are passing (or failures documented)
- [ ] SESSION_NOTES.md updated with progress
- [ ] NEXT_STEPS.md created with clear instructions
- [ ] Any blocking issues documented
- [ ] Environment state captured (.env, dependencies)
- [ ] Current token usage noted

## Handoff Information to Include

1. **Exact stopping point**
   - File: `src/component/file.py`
   - Line: 147
   - Function: `process_task()`
   - What was being implemented: "Adding retry logic for failed connections"

2. **Context that matters**
   - "Decided to use exponential backoff for retries"
   - "OAuth token needs refresh after 1 hour"
   - "File watcher is using inotify on Linux"

3. **Known issues**
   - "Test test_connection_timeout is flaky"
   - "Need to handle Windows path separators"

4. **Next immediate action**
   - "Complete the retry logic implementation"
   - "Then test with actual MCP server"
   - "Update documentation for new retry behavior"
```

## 9. Performance Monitoring

### Performance Tracking Template

```python
# src/utils/performance.py

import time
import functools
import psutil
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Track performance metrics for operations"""
    
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure operation performance"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_delta = end_memory - start_memory
            
            self.metrics[operation_name] = {
                'duration': duration,
                'memory_delta': memory_delta,
                'timestamp': time.time()
            }
            
            logger.info(f"{operation_name}: {duration:.2f}s, {memory_delta:+.1f}MB")
```

## 10. Documentation Standards

### API Documentation Template

```markdown
# API Reference: [Component Name]

## Overview
Brief description of the component's purpose and role in the system.

## Quick Start
```python
from ai_agent import Component

# Basic usage
component = Component(config)
result = component.process(data)
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| param1 | str | required | Description of param1 |
| param2 | int | 10 | Description of param2 |

## Methods

### `process(data: Dict) -> Result`
Process input data and return results.

**Parameters:**
- `data`: Dictionary containing input data

**Returns:**
- `Result`: Processing results

**Raises:**
- `ValueError`: If data is invalid
- `ConnectionError`: If MCP server unreachable

**Example:**
```python
result = component.process({
    'task': 'analyze',
    'target': 'file.txt'
})
```

## Error Handling
Description of error scenarios and how to handle them.

## Performance Considerations
- Expected latency: < 100ms for simple operations
- Memory usage: ~50MB baseline
- Concurrent operations: Supports up to 10 simultaneous
```

These templates and clarifications should help Claude Code maintain consistency and quality throughout the development process. Would you like me to create any additional templates or clarify other aspects of the development process?