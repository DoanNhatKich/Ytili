"""
WebSocket API endpoints for real-time notifications
Handles WebSocket connections and real-time communication
"""
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.websocket import connection_manager, notification_manager
from ..core.supabase import get_supabase_service, Tables
from ..api.supabase_deps import get_current_user_supabase_ws, get_current_user_supabase
import structlog

logger = structlog.get_logger()
router = APIRouter()


class NotificationRequest(BaseModel):
    """Schema for sending notifications via API"""
    user_id: str
    notification_type: str
    message: str
    details: Optional[Dict[str, Any]] = None


class BroadcastRequest(BaseModel):
    """Schema for broadcasting messages"""
    message: str
    notification_type: str = "info"
    target_users: Optional[list] = None


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Main WebSocket endpoint for real-time notifications"""
    
    user_id = None
    
    try:
        # Authenticate user if token provided
        if token:
            try:
                # Verify token and get user info
                supabase = get_supabase_service()
                user_response = supabase.auth.get_user(token)
                
                if user_response.user:
                    user_id = user_response.user.id
                else:
                    # Allow anonymous connections with limited functionality
                    user_id = f"anonymous_{websocket.client.host}_{id(websocket)}"
            except Exception as e:
                logger.warning("WebSocket authentication failed", error=str(e))
                user_id = f"anonymous_{websocket.client.host}_{id(websocket)}"
        else:
            user_id = f"anonymous_{websocket.client.host}_{id(websocket)}"
        
        # Connect to WebSocket manager
        await connection_manager.connect(websocket, user_id, {
            "client_ip": websocket.client.host,
            "authenticated": token is not None
        })
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(websocket, user_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                logger.error("WebSocket message handling error", error=str(e))
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Message processing failed"
                }, websocket)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
    finally:
        connection_manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages from clients"""
    
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }, websocket)
    
    elif message_type == "subscribe":
        # Subscribe to a room/channel
        room = message.get("room")
        if room:
            connection_manager.subscribe_to_room(websocket, room)
            await connection_manager.send_personal_message({
                "type": "subscribed",
                "room": room,
                "message": f"Subscribed to {room}"
            }, websocket)
    
    elif message_type == "unsubscribe":
        # Unsubscribe from a room/channel
        room = message.get("room")
        if room:
            connection_manager.unsubscribe_from_room(websocket, room)
            await connection_manager.send_personal_message({
                "type": "unsubscribed",
                "room": room,
                "message": f"Unsubscribed from {room}"
            }, websocket)
    
    elif message_type == "get_status":
        # Get connection status
        await connection_manager.send_personal_message({
            "type": "status",
            "user_id": user_id,
            "connected_at": connection_manager.connection_metadata.get(websocket, {}).get("connected_at"),
            "total_connections": connection_manager.get_connection_count(),
            "total_users": connection_manager.get_user_count()
        }, websocket)
    
    elif message_type == "donation_status_request":
        # Request donation status update
        donation_id = message.get("donation_id")
        if donation_id:
            await handle_donation_status_request(websocket, user_id, donation_id)
    
    elif message_type == "payment_status_request":
        # Request payment status update
        payment_reference = message.get("payment_reference")
        if payment_reference:
            await handle_payment_status_request(websocket, user_id, payment_reference)
    
    else:
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, websocket)


async def handle_donation_status_request(websocket: WebSocket, user_id: str, donation_id: str):
    """Handle donation status request"""
    try:
        supabase = get_supabase_service()
        
        # Get donation details
        donation_response = supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()
        
        if donation_response.data:
            donation = donation_response.data[0]
            
            await connection_manager.send_personal_message({
                "type": "donation_status",
                "donation_id": donation_id,
                "status": donation.get("status"),
                "details": {
                    "medication_name": donation.get("medication_name"),
                    "quantity": donation.get("quantity"),
                    "created_at": donation.get("created_at"),
                    "updated_at": donation.get("updated_at")
                }
            }, websocket)
        else:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Donation not found"
            }, websocket)
    
    except Exception as e:
        logger.error("Failed to get donation status", error=str(e))
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Failed to get donation status"
        }, websocket)


async def handle_payment_status_request(websocket: WebSocket, user_id: str, payment_reference: str):
    """Handle payment status request"""
    try:
        supabase = get_supabase_service()
        
        # Get payment details
        payment_response = supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq("payment_reference", payment_reference).execute()
        
        if payment_response.data:
            payment = payment_response.data[0]
            
            await connection_manager.send_personal_message({
                "type": "payment_status",
                "payment_reference": payment_reference,
                "status": payment.get("status"),
                "details": {
                    "amount": payment.get("amount"),
                    "currency": payment.get("currency"),
                    "created_at": payment.get("created_at"),
                    "expires_at": payment.get("expires_at")
                }
            }, websocket)
        else:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Payment not found"
            }, websocket)
    
    except Exception as e:
        logger.error("Failed to get payment status", error=str(e))
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Failed to get payment status"
        }, websocket)


# Temporarily commented out to fix import issues
# @router.post("/notify")
# async def send_notification(
#     notification: NotificationRequest,
#     current_user: Dict[str, Any] = Depends(get_current_user_supabase)
# ):
#     """Send notification to a specific user (API endpoint)"""
#
#     try:
#         # Check if user has permission to send notifications
#         # For now, allow all authenticated users
#
#         await notification_manager.send_system_notification(
#             message=notification.message,
#             notification_type=notification.notification_type,
#             target_users=[notification.user_id]
#         )
#
#         return {
#             "success": True,
#             "message": "Notification sent successfully"
#         }
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to send notification: {str(e)}"
#         )


# @router.post("/broadcast")
# async def broadcast_notification(
#     broadcast: BroadcastRequest,
#     current_user: Dict[str, Any] = Depends(get_current_user_supabase)
# ):
#     """Broadcast notification to all users or specific users (API endpoint)"""
#
#     try:
#         # Check if user has admin permissions
#         user_role = current_user.get("user_metadata", {}).get("role", "user")
#
#         if user_role not in ["admin", "moderator"]:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Insufficient permissions to broadcast notifications"
#             )
#
#         await notification_manager.send_system_notification(
#             message=broadcast.message,
#             notification_type=broadcast.notification_type,
#             target_users=broadcast.target_users
#         )
#
#         return {
#             "success": True,
#             "message": "Broadcast sent successfully"
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to broadcast notification: {str(e)}"
#         )


# @router.get("/stats")
# async def get_websocket_stats(
#     current_user: Dict[str, Any] = Depends(get_current_user_supabase)
# ):
#     """Get WebSocket connection statistics"""
#
#     return {
#         "total_connections": connection_manager.get_connection_count(),
#         "total_users": connection_manager.get_user_count(),
#         "rooms": list(connection_manager.room_subscriptions.keys()),
#         "room_counts": {
#             room: len(connections)
#             for room, connections in connection_manager.room_subscriptions.items()
#         }
#     }


# @router.post("/test")
# async def test_notification(
#     current_user: Dict[str, Any] = Depends(get_current_user_supabase)
# ):
#     """Test notification endpoint for development"""
#
#     user_id = current_user.get("id")
#
#     await notification_manager.send_system_notification(
#         message="This is a test notification from Ytili!",
#         notification_type="info",
#         target_users=[user_id]
#     )
#
#     return {
#         "success": True,
#         "message": "Test notification sent",
#         "user_id": user_id
#     }
