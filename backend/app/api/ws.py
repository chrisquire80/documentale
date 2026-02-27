from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from uuid import UUID
import json
from jose import jwt, JWTError
from ..core.config import settings
from ..db import SessionLocal
from ..models.user import User
from sqlalchemy import select
import logging

router = APIRouter(prefix="/ws", tags=["websockets"])
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of active WebSocket connections
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WS. Active sessions: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: UUID):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WS.")

    async def send_personal_message(self, message: dict, user_id: UUID):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending WS message to {user_id}: {e}")

    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.error("Token non contiene 'sub'")
            await websocket.close(code=1008)
            return
    except JWTError as e:
        logger.error(f"Invalid WS token: {e}")
        await websocket.close(code=1008)
        return
        
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == user_id_str))
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"User email {user_id_str} non trovato")
            await websocket.close(code=1008)
            return
        user_id = user.id
    
    await manager.connect(websocket, user_id)
    try:
        while True:
            # We don't really expect clients to send messages right now, 
            # but we need to keep the connection open and listen for disconnects
            data = await websocket.receive_text()
            # Simple ping-pong could go here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Websocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
