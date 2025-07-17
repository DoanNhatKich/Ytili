"""
WebSocket Manager for Real-time Notifications
Handles WebSocket connections and real-time updates for Ytili platform
"""
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Store room subscriptions (for group notifications)
        self.room_subscriptions: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        # Add connection
        self.active_connections[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            **(metadata or {})
        }
        
        logger.info("WebSocket connected", user_id=user_id, total_connections=len(self.connection_metadata))
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to Ytili real-time notifications",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            # Remove from user connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from room subscriptions
            for room_connections in self.room_subscriptions.values():
                room_connections.discard(websocket)
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info("WebSocket disconnected", user_id=user_id, total_connections=len(self.connection_metadata))
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error("Failed to send personal message", error=str(e))
            self.disconnect(websocket)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error("Failed to send message to user", user_id=user_id, error=str(e))
                    disconnected_connections.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected_connections:
                self.disconnect(websocket)
    
    async def send_to_room(self, message: Dict[str, Any], room: str):
        """Send a message to all connections in a room"""
        if room in self.room_subscriptions:
            disconnected_connections = []
            
            for websocket in self.room_subscriptions[room].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error("Failed to send message to room", room=room, error=str(e))
                    disconnected_connections.append(websocket)
            
            # Clean up disconnected connections
            for websocket in disconnected_connections:
                self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send a message to all connected users"""
        disconnected_connections = []
        
        for websocket in list(self.connection_metadata.keys()):
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error("Failed to broadcast message", error=str(e))
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket)
    
    def subscribe_to_room(self, websocket: WebSocket, room: str):
        """Subscribe a connection to a room"""
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()
        
        self.room_subscriptions[room].add(websocket)
        logger.info("Subscribed to room", room=room, user_id=self.connection_metadata.get(websocket, {}).get("user_id"))
    
    def unsubscribe_from_room(self, websocket: WebSocket, room: str):
        """Unsubscribe a connection from a room"""
        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(websocket)
            if not self.room_subscriptions[room]:
                del self.room_subscriptions[room]
    
    def get_user_connections(self, user_id: str) -> Set[WebSocket]:
        """Get all connections for a user"""
        return self.active_connections.get(user_id, set())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_metadata)
    
    def get_user_count(self) -> int:
        """Get total number of connected users"""
        return len(self.active_connections)
    
    async def ping_all_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected_connections = []
        
        for websocket in list(self.connection_metadata.keys()):
            try:
                await websocket.ping()
                self.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
            except Exception as e:
                logger.error("Failed to ping connection", error=str(e))
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket)


class NotificationManager:
    """Manages different types of notifications"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def send_donation_update(self, user_id: str, donation_id: str, status: str, details: Dict[str, Any]):
        """Send donation status update notification"""
        message = {
            "type": "donation_update",
            "donation_id": donation_id,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(message, user_id)
        logger.info("Sent donation update", user_id=user_id, donation_id=donation_id, status=status)
    
    async def send_payment_update(self, user_id: str, payment_reference: str, status: str, details: Dict[str, Any]):
        """Send payment status update notification"""
        message = {
            "type": "payment_update",
            "payment_reference": payment_reference,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(message, user_id)
        logger.info("Sent payment update", user_id=user_id, payment_reference=payment_reference, status=status)
    
    async def send_matching_notification(self, user_id: str, donation_id: str, hospital_name: str, details: Dict[str, Any]):
        """Send donation matching notification"""
        message = {
            "type": "donation_matched",
            "donation_id": donation_id,
            "hospital_name": hospital_name,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(message, user_id)
        logger.info("Sent matching notification", user_id=user_id, donation_id=donation_id, hospital_name=hospital_name)
    
    async def send_emergency_alert(self, room: str, alert_type: str, message: str, details: Dict[str, Any]):
        """Send emergency alert to a room"""
        alert_message = {
            "type": "emergency_alert",
            "alert_type": alert_type,
            "message": message,
            "details": details,
            "priority": "high",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_room(alert_message, room)
        logger.warning("Sent emergency alert", room=room, alert_type=alert_type)
    
    async def send_system_notification(self, message: str, notification_type: str = "info", target_users: Optional[List[str]] = None):
        """Send system-wide notification"""
        notification = {
            "type": "system_notification",
            "notification_type": notification_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if target_users:
            for user_id in target_users:
                await self.connection_manager.send_to_user(notification, user_id)
        else:
            await self.connection_manager.broadcast(notification)
        
        logger.info("Sent system notification", notification_type=notification_type, target_users=target_users)
    
    async def send_points_update(self, user_id: str, points_earned: int, total_points: int, reason: str):
        """Send points update notification"""
        message = {
            "type": "points_update",
            "points_earned": points_earned,
            "total_points": total_points,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_to_user(message, user_id)
        logger.info("Sent points update", user_id=user_id, points_earned=points_earned, reason=reason)


# Global instances
connection_manager = ConnectionManager()
notification_manager = NotificationManager(connection_manager)


# Background task to keep connections alive
async def keep_connections_alive():
    """Background task to ping connections periodically"""
    while True:
        await asyncio.sleep(30)  # Ping every 30 seconds
        await connection_manager.ping_all_connections()


# Utility functions
async def notify_donation_status_change(user_id: str, donation_id: str, old_status: str, new_status: str, details: Dict[str, Any] = None):
    """Utility function to notify donation status changes"""
    await notification_manager.send_donation_update(
        user_id=user_id,
        donation_id=donation_id,
        status=new_status,
        details={
            "old_status": old_status,
            "new_status": new_status,
            **(details or {})
        }
    )


async def notify_payment_status_change(user_id: str, payment_reference: str, old_status: str, new_status: str, details: Dict[str, Any] = None):
    """Utility function to notify payment status changes"""
    await notification_manager.send_payment_update(
        user_id=user_id,
        payment_reference=payment_reference,
        status=new_status,
        details={
            "old_status": old_status,
            "new_status": new_status,
            **(details or {})
        }
    )
