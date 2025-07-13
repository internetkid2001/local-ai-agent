"""
Test Suite for Local AI Agent

Comprehensive test suite covering unit tests, integration tests,
and security validation for all components.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    'agent': {
        'name': 'Test AI Agent',
        'version': '1.0.0-test'
    },
    'llm': {
        'provider': 'mock',
        'host': 'http://localhost:11434',
        'models': {
            'primary': 'test:latest',
            'fallback': 'test:7b'
        },
        'timeout': 5.0
    },
    'mcp_servers': {
        'test_server': {
            'enabled': True,
            'url': 'ws://localhost:8999',
            'timeout': 10.0,
            'retry_attempts': 1
        }
    },
    'security': {
        'sandbox_enabled': True,
        'require_confirmation': False,  # Auto-approve in tests
        'allowed_paths': ['/tmp/ai-agent-test'],
        'forbidden_paths': ['/etc', '/sys'],
        'max_file_size_mb': 10
    },
    'logging': {
        'level': 'DEBUG',
        'file': '/tmp/ai-agent-test.log'
    }
}


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return TEST_CONFIG.copy()


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests"""
    workspace = tempfile.mkdtemp(prefix='ai-agent-test-')
    yield Path(workspace)
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test utilities
def create_test_files(directory: Path, files: Dict[str, str]) -> Dict[str, Path]:
    """
    Create test files in directory.
    
    Args:
        directory: Directory to create files in
        files: Dict mapping filename to content
        
    Returns:
        Dict mapping filename to Path object
    """
    created_files = {}
    for filename, content in files.items():
        file_path = directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created_files[filename] = file_path
    return created_files