import json
import uuid
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status, Query
from fastapi.routing import APIWebSocketRoute
import logging

from .manager import ConnectionManager, WebSocketEventHandler, EventBroadcaster
from ...enterprise.auth import JWTManager

logger = logging.getLogger(__name__)


class WebSocketEndpoint:
    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
        self.connection_manager = ConnectionManager()
        self.event_handler = WebSocketEventHandler(self.connection_manager)
        self.broadcaster = EventBroadcaster(self.connection_manager)
    
    async def authenticate_websocket(self, websocket: WebSocket, token: Optional[str]) -> tuple:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
            raise HTTPException(status_code=status.WS_1008_POLICY_VIOLATION, detail="Authentication required")
        
        try:
            payload = self.jwt_manager.verify_token(token)
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            
            if not user_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                raise HTTPException(status_code=status.WS_1008_POLICY_VIOLATION, detail="Invalid token")
            
            return user_id, tenant_id
        
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            raise HTTPException(status_code=status.WS_1008_POLICY_VIOLATION, detail="Authentication failed")
    
    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: Optional[str] = Query(None, description="JWT authentication token")
    ):
        connection_id = str(uuid.uuid4())
        user_id = None
        tenant_id = None
        
        try:
            user_id, tenant_id = await self.authenticate_websocket(websocket, token)
            
            await self.connection_manager.connect(websocket, connection_id, user_id, tenant_id)
            
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "message": "WebSocket connection established successfully"
            }))
            
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    await self.event_handler.handle_message(websocket, connection_id, message)
                
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "Invalid JSON format"
                    }))
                
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {str(e)}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Error processing message: {str(e)}"
                    }))
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        
        finally:
            if user_id:
                self.connection_manager.disconnect(connection_id, user_id, tenant_id)


def create_websocket_route(jwt_manager: JWTManager) -> APIWebSocketRoute:
    ws_endpoint = WebSocketEndpoint(jwt_manager)
    
    route = APIWebSocketRoute(
        "/ws",
        ws_endpoint.websocket_endpoint,
        name="websocket"
    )
    
    return route, ws_endpoint