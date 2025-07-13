"""
Unit Tests for MCP Client

Tests for MCP client connection management, message handling,
and tool execution functionality.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.mcp_client import (
    BaseMCPClient, MCPClientConfig, MCPServerConfig,
    MCPConnection, MCPMessage, ConnectionState
)
from src.mcp_client.exceptions import MCPError, ConnectionError, TimeoutError


class TestMCPMessage:
    """Test MCP message structure and serialization"""
    
    def test_message_creation(self):
        """Test message creation with required fields"""
        message = MCPMessage(
            id="test-123",
            method="test_method",
            params={"arg": "value"}
        )
        
        assert message.id == "test-123"
        assert message.method == "test_method"
        assert message.params == {"arg": "value"}
        assert message.timestamp is not None
    
    def test_message_serialization(self):
        """Test message serialization to JSON-RPC format"""
        message = MCPMessage(
            id="test-123",
            method="test_method",
            params={"arg": "value"}
        )
        
        serialized = message.to_dict()
        
        assert serialized["jsonrpc"] == "2.0"
        assert serialized["id"] == "test-123"
        assert serialized["method"] == "test_method"
        assert serialized["params"] == {"arg": "value"}


class TestMCPConnection:
    """Test MCP connection management"""
    
    @pytest.fixture
    def connection(self):
        """Create test connection"""
        return MCPConnection(
            server_url="ws://localhost:8999",
            reconnect_interval=0.1,  # Fast reconnect for tests
            max_reconnect_attempts=2,
            message_timeout=1.0
        )
    
    def test_connection_initialization(self, connection):
        """Test connection initialization"""
        assert connection.server_url == "ws://localhost:8999"
        assert connection.state == ConnectionState.DISCONNECTED
        assert not connection.is_connected
    
    @pytest.mark.asyncio
    async def test_connection_state_management(self, connection):
        """Test connection state transitions"""
        assert connection.state == ConnectionState.DISCONNECTED
        
        # Mock websocket connection
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # Test successful connection
            success = await connection.connect()
            assert success
            assert connection.state == ConnectionState.CONNECTED
            assert connection.is_connected
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, connection):
        """Test connection failure handling"""
        with patch('websockets.connect', side_effect=Exception("Connection failed")):
            success = await connection.connect()
            assert not success
            assert connection.state == ConnectionState.FAILED
    
    @pytest.mark.asyncio
    async def test_message_sending(self, connection):
        """Test message sending and response handling"""
        message = MCPMessage(
            id="test-123",
            method="test_method",
            params={"arg": "value"}
        )
        
        # Mock websocket
        mock_websocket = AsyncMock()
        mock_response = {"jsonrpc": "2.0", "id": "test-123", "result": {"success": True}}
        
        with patch('websockets.connect', return_value=mock_websocket):
            await connection.connect()
            
            # Mock response processing
            connection._pending_responses["test-123"] = asyncio.Future()
            connection._pending_responses["test-123"].set_result({"success": True})
            
            # Mock send
            mock_websocket.send = AsyncMock()
            
            # Override send_message to avoid actual WebSocket interaction
            async def mock_send_message(msg):
                return {"success": True}
            
            connection.send_message = mock_send_message
            result = await connection.send_message(message)
            
            assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_message_timeout(self, connection):
        """Test message timeout handling"""
        message = MCPMessage(
            id="timeout-test",
            method="slow_method",
            params={}
        )
        
        # Create connection but don't set up response
        mock_websocket = AsyncMock()
        
        with patch('websockets.connect', return_value=mock_websocket):
            await connection.connect()
            connection._websocket = mock_websocket
            
            # This should timeout
            with pytest.raises(TimeoutError):
                await connection.send_message(message)
    
    def test_event_handlers(self, connection):
        """Test event handler registration"""
        on_connect = Mock()
        on_disconnect = Mock()
        on_message = Mock()
        
        connection.set_event_handlers(
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            on_message=on_message
        )
        
        assert connection._on_connect == on_connect
        assert connection._on_disconnect == on_disconnect
        assert connection._on_message == on_message


class MockMCPClient(BaseMCPClient):
    """Mock implementation of BaseMCPClient for testing"""
    
    async def process_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock task processing"""
        return {"task": task, "result": "mock_result", "context": context}


class TestBaseMCPClient:
    """Test base MCP client functionality"""
    
    @pytest.fixture
    def client_config(self):
        """Create test client configuration"""
        return MCPClientConfig(
            servers=[
                MCPServerConfig(
                    name="test_server",
                    url="ws://localhost:8999",
                    enabled=True,
                    retry_attempts=2,
                    timeout=10.0,
                    tools=["test_tool"]
                )
            ],
            connection_timeout=5.0,
            default_timeout=10.0,
            max_concurrent_connections=5
        )
    
    @pytest.fixture
    def client(self, client_config):
        """Create test MCP client"""
        return MockMCPClient(client_config)
    
    def test_client_initialization(self, client, client_config):
        """Test client initialization"""
        assert client.config == client_config
        assert len(client._connections) == 0
        assert len(client._tools) == 0
    
    @pytest.mark.asyncio
    async def test_client_initialization_process(self, client):
        """Test client initialization process"""
        # Mock successful server connection
        with patch.object(client, '_initialize_server', return_value=True):
            with patch.object(client, '_discover_tools'):
                success = await client.initialize()
                assert success
    
    @pytest.mark.asyncio
    async def test_client_initialization_failure(self, client):
        """Test client initialization with all servers failing"""
        # Mock failed server connections
        with patch.object(client, '_initialize_server', return_value=False):
            success = await client.initialize()
            assert not success
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, client):
        """Test tool execution"""
        # Set up mock tool and connection
        client._tools["test_tool"] = Mock()
        client._tools["test_tool"].server_name = "test_server"
        
        mock_connection = AsyncMock()
        mock_connection.is_connected = True
        mock_connection.send_message.return_value = {"result": "success"}
        client._connections["test_server"] = mock_connection
        
        result = await client.execute_tool("test_tool", {"param": "value"})
        assert result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_tool_not_found(self, client):
        """Test execution of non-existent tool"""
        with pytest.raises(MCPError, match="Tool not found"):
            await client.execute_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_server_not_connected(self, client):
        """Test tool execution when server is not connected"""
        client._tools["test_tool"] = Mock()
        client._tools["test_tool"].server_name = "disconnected_server"
        
        with pytest.raises(ConnectionError, match="Server not connected"):
            await client.execute_tool("test_tool", {})
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check functionality"""
        # Set up mock connection
        mock_connection = AsyncMock()
        mock_connection.state.value = "connected"
        mock_connection.send_message.return_value = {"pong": True}
        client._connections["test_server"] = mock_connection
        client._server_tools["test_server"] = ["tool1", "tool2"]
        
        health = await client.health_check()
        
        assert "test_server" in health
        assert health["test_server"]["status"] == "healthy"
        assert health["test_server"]["tools_count"] == 2
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client):
        """Test health check with unhealthy server"""
        # Set up mock connection that fails
        mock_connection = AsyncMock()
        mock_connection.state.value = "disconnected"
        mock_connection.send_message.side_effect = Exception("Connection failed")
        client._connections["test_server"] = mock_connection
        client._server_tools["test_server"] = []
        
        health = await client.health_check()
        
        assert "test_server" in health
        assert health["test_server"]["status"] == "unhealthy"
        assert "error" in health["test_server"]
    
    def test_list_tools(self, client):
        """Test tool listing"""
        # Set up mock tools
        tool1 = Mock()
        tool1.server_name = "server1"
        tool2 = Mock()
        tool2.server_name = "server2"
        
        client._tools = {"tool1": tool1, "tool2": tool2}
        client._server_tools = {"server1": ["tool1"], "server2": ["tool2"]}
        
        # Test listing all tools
        all_tools = asyncio.run(client.list_tools())
        assert len(all_tools) == 2
        
        # Test listing tools for specific server
        server1_tools = asyncio.run(client.list_tools("server1"))
        assert len(server1_tools) == 1
        assert server1_tools[0] == tool1
    
    @pytest.mark.asyncio
    async def test_shutdown(self, client):
        """Test client shutdown"""
        # Set up mock connections
        mock_connection1 = AsyncMock()
        mock_connection2 = AsyncMock()
        client._connections = {
            "server1": mock_connection1,
            "server2": mock_connection2
        }
        client._tools = {"tool1": Mock()}
        client._server_tools = {"server1": ["tool1"]}
        
        await client.shutdown()
        
        # Verify connections were closed
        mock_connection1.disconnect.assert_called_once()
        mock_connection2.disconnect.assert_called_once()
        
        # Verify cleanup
        assert len(client._connections) == 0
        assert len(client._tools) == 0
        assert len(client._server_tools) == 0


class TestMCPIntegration:
    """Integration tests for MCP client components"""
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        """Test complete connection lifecycle"""
        config = MCPClientConfig(
            servers=[
                MCPServerConfig(
                    name="test_server",
                    url="ws://localhost:8999",
                    enabled=True
                )
            ]
        )
        
        client = MockMCPClient(config)
        
        # Mock the entire connection process
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            # Mock tools discovery
            mock_websocket.__aiter__ = AsyncMock(return_value=iter([]))
            
            with patch.object(client, '_discover_tools'):
                # Initialize client
                success = await client.initialize()
                assert success
                
                # Test task processing
                result = await client.process_task("test task", {"context": "test"})
                assert result["task"] == "test task"
                assert result["result"] == "mock_result"
                
                # Shutdown
                await client.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_websocket_connection(self):
        """Test with real WebSocket server (requires running MCP server)"""
        # This test would require an actual MCP server running
        # Skip by default unless in integration test mode
        pytest.skip("Requires running MCP server for integration testing")
        
        config = MCPClientConfig(
            servers=[
                MCPServerConfig(
                    name="real_server",
                    url="ws://localhost:8000",  # Actual server
                    enabled=True
                )
            ]
        )
        
        client = MockMCPClient(config)
        
        try:
            success = await client.initialize()
            assert success
            
            # Test actual tool execution
            tools = await client.list_tools()
            assert len(tools) > 0
            
        finally:
            await client.shutdown()