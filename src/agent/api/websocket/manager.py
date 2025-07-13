import json
import asyncio
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.tenant_connections: Dict[str, Set[str]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str, tenant_id: Optional[str] = None):
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        if tenant_id:
            if tenant_id not in self.tenant_connections:
                self.tenant_connections[tenant_id] = set()
            self.tenant_connections[tenant_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str, user_id: str, tenant_id: Optional[str] = None):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        if tenant_id and tenant_id in self.tenant_connections:
            self.tenant_connections[tenant_id].discard(connection_id)
            if not self.tenant_connections[tenant_id]:
                del self.tenant_connections[tenant_id]
        
        for topic in list(self.subscriptions.keys()):
            self.subscriptions[topic].discard(connection_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {str(e)}")
                await self._handle_connection_error(connection_id)
    
    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            tasks = []
            for connection_id in self.user_connections[user_id].copy():
                tasks.append(self.send_personal_message(message, connection_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_tenant(self, message: dict, tenant_id: str):
        if tenant_id in self.tenant_connections:
            tasks = []
            for connection_id in self.tenant_connections[tenant_id].copy():
                tasks.append(self.send_personal_message(message, connection_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_subscribers(self, message: dict, topic: str):
        if topic in self.subscriptions:
            tasks = []
            for connection_id in self.subscriptions[topic].copy():
                tasks.append(self.send_personal_message(message, connection_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def subscribe(self, connection_id: str, topic: str):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to {topic}")
    
    def unsubscribe(self, connection_id: str, topic: str):
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(connection_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        logger.info(f"Connection {connection_id} unsubscribed from {topic}")
    
    async def _handle_connection_error(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
    
    def get_connection_info(self) -> dict:
        return {
            "total_connections": len(self.active_connections),
            "users_connected": len(self.user_connections),
            "tenants_with_connections": len(self.tenant_connections),
            "active_subscriptions": len(self.subscriptions)
        }


class WebSocketEventHandler:
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.event_handlers = {
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "ping": self._handle_ping,
            "get_status": self._handle_get_status
        }
    
    async def handle_message(self, websocket: WebSocket, connection_id: str, message: dict):
        event_type = message.get("type")
        
        if event_type in self.event_handlers:
            try:
                await self.event_handlers[event_type](websocket, connection_id, message)
            except Exception as e:
                logger.error(f"Error handling {event_type} event: {str(e)}")
                await self._send_error(websocket, f"Error processing {event_type}: {str(e)}")
        else:
            await self._send_error(websocket, f"Unknown event type: {event_type}")
    
    async def _handle_subscribe(self, websocket: WebSocket, connection_id: str, message: dict):
        topic = message.get("topic")
        if not topic:
            await self._send_error(websocket, "Topic is required for subscription")
            return
        
        self.connection_manager.subscribe(connection_id, topic)
        await self._send_response(websocket, {
            "type": "subscription_confirmed",
            "topic": topic,
            "message": f"Subscribed to {topic}"
        })
    
    async def _handle_unsubscribe(self, websocket: WebSocket, connection_id: str, message: dict):
        topic = message.get("topic")
        if not topic:
            await self._send_error(websocket, "Topic is required for unsubscription")
            return
        
        self.connection_manager.unsubscribe(connection_id, topic)
        await self._send_response(websocket, {
            "type": "unsubscription_confirmed",
            "topic": topic,
            "message": f"Unsubscribed from {topic}"
        })
    
    async def _handle_ping(self, websocket: WebSocket, connection_id: str, message: dict):
        await self._send_response(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat(),
            "connection_id": connection_id
        })
    
    async def _handle_get_status(self, websocket: WebSocket, connection_id: str, message: dict):
        status = self.connection_manager.get_connection_info()
        await self._send_response(websocket, {
            "type": "status",
            "data": status
        })
    
    async def _send_response(self, websocket: WebSocket, response: dict):
        response["timestamp"] = datetime.utcnow().isoformat()
        await websocket.send_text(json.dumps(response))
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        await self._send_response(websocket, {
            "type": "error",
            "error": error_message
        })


class EventBroadcaster:
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def broadcast_agent_status_change(self, agent_id: str, status: str, tenant_id: Optional[str] = None):
        message = {
            "type": "agent_status_change",
            "data": {
                "agent_id": agent_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.connection_manager.broadcast_to_subscribers(message, f"agent:{agent_id}")
        await self.connection_manager.broadcast_to_subscribers(message, "agent_updates")
        
        if tenant_id:
            await self.connection_manager.send_to_tenant(message, tenant_id)
    
    async def broadcast_workflow_update(self, workflow_id: str, status: str, tenant_id: Optional[str] = None):
        message = {
            "type": "workflow_update",
            "data": {
                "workflow_id": workflow_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.connection_manager.broadcast_to_subscribers(message, f"workflow:{workflow_id}")
        await self.connection_manager.broadcast_to_subscribers(message, "workflow_updates")
        
        if tenant_id:
            await self.connection_manager.send_to_tenant(message, tenant_id)
    
    async def broadcast_execution_update(self, execution_id: str, agent_id: str, status: str, result: Any = None, tenant_id: Optional[str] = None):
        message = {
            "type": "execution_update",
            "data": {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "status": status,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.connection_manager.broadcast_to_subscribers(message, f"execution:{execution_id}")
        await self.connection_manager.broadcast_to_subscribers(message, f"agent:{agent_id}:executions")
        await self.connection_manager.broadcast_to_subscribers(message, "execution_updates")
        
        if tenant_id:
            await self.connection_manager.send_to_tenant(message, tenant_id)
    
    async def send_notification(self, user_id: str, notification_type: str, title: str, message: str, data: Optional[dict] = None):
        notification = {
            "type": "notification",
            "data": {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.connection_manager.send_to_user(notification, user_id)