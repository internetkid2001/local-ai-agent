"""
MCP Connection Management

Handles individual connections to MCP servers with async support,
retry logic, and connection state management.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import asyncio
import json
import time
import websockets
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
import logging

from .exceptions import ConnectionError, TimeoutError, ProtocolError

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class MCPMessage:
    """MCP message structure"""
    id: str
    method: str
    params: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
            "params": self.params
        }


class MCPConnection:
    """
    Manages a single MCP server connection.
    
    Features:
    - Async WebSocket communication
    - Automatic reconnection with exponential backoff
    - Message queuing during disconnections
    - Timeout handling
    - Connection health monitoring
    """
    
    def __init__(
        self,
        server_url: str,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 5,
        message_timeout: float = 30.0
    ):
        """
        Initialize MCP connection.
        
        Args:
            server_url: WebSocket URL of MCP server
            reconnect_interval: Base interval for reconnection attempts
            max_reconnect_attempts: Maximum number of reconnection attempts
            message_timeout: Timeout for individual messages
        """
        self.server_url = server_url
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.message_timeout = message_timeout
        
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_count = 0
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._connection_lock = asyncio.Lock()
        
        # Event handlers
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._on_message: Optional[Callable] = None
    
    @property
    def state(self) -> ConnectionState:
        """Get current connection state"""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self._state == ConnectionState.CONNECTED
    
    async def connect(self) -> bool:
        """
        Establish connection to MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self._state == ConnectionState.CONNECTED:
                return True
            
            self._state = ConnectionState.CONNECTING
            logger.info(f"Connecting to MCP server: {self.server_url}")
            
            try:
                self._websocket = await asyncio.wait_for(
                    websockets.connect(self.server_url),
                    timeout=10.0
                )
                
                self._state = ConnectionState.CONNECTED
                self._reconnect_count = 0
                
                # Start message handler
                asyncio.create_task(self._handle_messages())
                
                # Process queued messages
                asyncio.create_task(self._process_message_queue())
                
                if self._on_connect:
                    await self._on_connect()
                
                logger.info(f"Successfully connected to {self.server_url}")
                return True
                
            except Exception as e:
                self._state = ConnectionState.FAILED
                logger.error(f"Failed to connect to {self.server_url}: {e}")
                return False
    
    async def disconnect(self):
        """Gracefully disconnect from MCP server"""
        async with self._connection_lock:
            if self._websocket and not self._websocket.closed:
                await self._websocket.close()
            
            self._state = ConnectionState.DISCONNECTED
            self._websocket = None
            
            # Cancel pending responses
            for future in self._pending_responses.values():
                if not future.done():
                    future.cancel()
            self._pending_responses.clear()
            
            if self._on_disconnect:
                await self._on_disconnect()
            
            logger.info(f"Disconnected from {self.server_url}")
    
    async def send_message(self, message: MCPMessage) -> Dict[str, Any]:
        """
        Send message to MCP server and await response.
        
        Args:
            message: MCP message to send
            
        Returns:
            Response from server
            
        Raises:
            ConnectionError: If not connected
            TimeoutError: If response timeout
        """
        if not self.is_connected:
            # Queue message for later if disconnected
            await self._message_queue.put(message)
            # Attempt reconnection
            if not await self._reconnect():
                raise ConnectionError("Failed to establish connection")
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[message.id] = response_future
        
        try:
            # Send message
            message_data = json.dumps(message.to_dict())
            await self._websocket.send(message_data)
            logger.debug(f"Sent message: {message.method} (ID: {message.id})")
            
            # Wait for response
            response = await asyncio.wait_for(
                response_future,
                timeout=self.message_timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending response
            self._pending_responses.pop(message.id, None)
            raise TimeoutError(f"Message timeout: {message.method}")
        
        except Exception as e:
            # Clean up pending response
            self._pending_responses.pop(message.id, None)
            raise ConnectionError(f"Failed to send message: {e}")
    
    async def _handle_messages(self):
        """Handle incoming messages from MCP server"""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._process_response(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP server connection closed")
            await self._handle_disconnect()
        
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            await self._handle_disconnect()
    
    async def _process_response(self, data: Dict[str, Any]):
        """Process response from MCP server"""
        logger.info(f"Processing response: {data}")
        message_id = data.get("id")
        
        if message_id and message_id in self._pending_responses:
            future = self._pending_responses.pop(message_id)
            
            if "error" in data:
                error = data["error"]
                future.set_exception(
                    ProtocolError(f"Server error: {error.get('message', 'Unknown')}")
                )
            else:
                future.set_result(data.get("result", {}))
        
        # Handle notifications (no ID)
        elif "method" in data and self._on_message:
            await self._on_message(data)
    
    async def _handle_disconnect(self):
        """Handle unexpected disconnection"""
        self._state = ConnectionState.DISCONNECTED
        
        if self._on_disconnect:
            await self._on_disconnect()
        
        # Attempt reconnection
        await self._reconnect()
    
    async def _reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        if self._reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for {self.server_url}")
            self._state = ConnectionState.FAILED
            return False
        
        self._state = ConnectionState.RECONNECTING
        self._reconnect_count += 1
        
        # Exponential backoff
        wait_time = self.reconnect_interval * (2 ** (self._reconnect_count - 1))
        logger.info(f"Reconnecting to {self.server_url} in {wait_time}s (attempt {self._reconnect_count})")
        
        await asyncio.sleep(wait_time)
        return await self.connect()
    
    async def _process_message_queue(self):
        """Process queued messages after reconnection"""
        while not self._message_queue.empty():
            try:
                message = await self._message_queue.get()
                await self.send_message(message)
            except Exception as e:
                logger.error(f"Failed to process queued message: {e}")
    
    def set_event_handlers(
        self,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_message: Optional[Callable] = None
    ):
        """Set event handlers for connection events"""
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_message = on_message