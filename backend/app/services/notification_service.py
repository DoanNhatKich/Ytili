"""
Notification service for real-time updates
Handles WebSocket notifications and status updates
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from ..core.websocket import notification_manager
from ..core.supabase import get_supabase_service, Tables

logger = structlog.get_logger()


class NotificationService:
    """Service for managing real-time notifications"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    async def notify_donation_status_change(
        self,
        donation_id: str,
        old_status: str,
        new_status: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Notify user about donation status change"""
        
        try:
            # Get donation details
            donation_response = self.supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()
            
            if not donation_response.data:
                logger.error("Donation not found for notification", donation_id=donation_id)
                return
            
            donation = donation_response.data[0]
            
            # Prepare notification details
            notification_details = {
                "donation_id": donation_id,
                "medication_name": donation.get("medication_name"),
                "quantity": donation.get("quantity"),
                "old_status": old_status,
                "new_status": new_status,
                "timestamp": datetime.utcnow().isoformat(),
                **(details or {})
            }
            
            # Send WebSocket notification
            await notification_manager.send_donation_update(
                user_id=user_id,
                donation_id=donation_id,
                status=new_status,
                details=notification_details
            )
            
            # Log notification
            logger.info(
                "Donation status notification sent",
                donation_id=donation_id,
                user_id=user_id,
                old_status=old_status,
                new_status=new_status
            )
            
        except Exception as e:
            logger.error("Failed to send donation status notification", error=str(e))
    
    async def notify_donation_matched(
        self,
        donation_id: str,
        user_id: str,
        hospital_id: str,
        hospital_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Notify user about donation matching"""
        
        try:
            # Prepare notification details
            notification_details = {
                "donation_id": donation_id,
                "hospital_id": hospital_id,
                "hospital_name": hospital_name,
                "matched_at": datetime.utcnow().isoformat(),
                **(details or {})
            }
            
            # Send WebSocket notification
            await notification_manager.send_matching_notification(
                user_id=user_id,
                donation_id=donation_id,
                hospital_name=hospital_name,
                details=notification_details
            )
            
            # Also send donation status update
            await self.notify_donation_status_change(
                donation_id=donation_id,
                old_status="pending",
                new_status="matched",
                user_id=user_id,
                details={"hospital_name": hospital_name}
            )
            
            logger.info(
                "Donation matching notification sent",
                donation_id=donation_id,
                user_id=user_id,
                hospital_name=hospital_name
            )
            
        except Exception as e:
            logger.error("Failed to send donation matching notification", error=str(e))
    
    async def notify_payment_status_change(
        self,
        payment_reference: str,
        old_status: str,
        new_status: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Notify user about payment status change"""
        
        try:
            # Get payment details
            payment_response = self.supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
                "payment_reference", payment_reference
            ).execute()
            
            if not payment_response.data:
                logger.error("Payment not found for notification", payment_reference=payment_reference)
                return
            
            payment = payment_response.data[0]
            
            # Prepare notification details
            notification_details = {
                "payment_reference": payment_reference,
                "amount": payment.get("amount"),
                "currency": payment.get("currency"),
                "donation_id": payment.get("donation_id"),
                "old_status": old_status,
                "new_status": new_status,
                "timestamp": datetime.utcnow().isoformat(),
                **(details or {})
            }
            
            # Send WebSocket notification
            await notification_manager.send_payment_update(
                user_id=user_id,
                payment_reference=payment_reference,
                status=new_status,
                details=notification_details
            )
            
            logger.info(
                "Payment status notification sent",
                payment_reference=payment_reference,
                user_id=user_id,
                old_status=old_status,
                new_status=new_status
            )
            
        except Exception as e:
            logger.error("Failed to send payment status notification", error=str(e))
    
    async def notify_points_earned(
        self,
        user_id: str,
        points_earned: int,
        total_points: int,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Notify user about points earned"""
        
        try:
            # Send WebSocket notification
            await notification_manager.send_points_update(
                user_id=user_id,
                points_earned=points_earned,
                total_points=total_points,
                reason=reason
            )
            
            logger.info(
                "Points earned notification sent",
                user_id=user_id,
                points_earned=points_earned,
                reason=reason
            )
            
        except Exception as e:
            logger.error("Failed to send points notification", error=str(e))
    
    async def notify_emergency_alert(
        self,
        alert_type: str,
        message: str,
        target_users: Optional[List[str]] = None,
        room: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Send emergency alert notification"""
        
        try:
            if room:
                # Send to room
                await notification_manager.send_emergency_alert(
                    room=room,
                    alert_type=alert_type,
                    message=message,
                    details=details or {}
                )
            elif target_users:
                # Send to specific users
                for user_id in target_users:
                    await notification_manager.send_system_notification(
                        message=message,
                        notification_type="error",
                        target_users=[user_id]
                    )
            else:
                # Broadcast to all users
                await notification_manager.send_system_notification(
                    message=message,
                    notification_type="error"
                )
            
            logger.warning(
                "Emergency alert sent",
                alert_type=alert_type,
                target_users=target_users,
                room=room
            )
            
        except Exception as e:
            logger.error("Failed to send emergency alert", error=str(e))
    
    async def notify_system_message(
        self,
        message: str,
        notification_type: str = "info",
        target_users: Optional[List[str]] = None
    ):
        """Send system-wide notification"""
        
        try:
            await notification_manager.send_system_notification(
                message=message,
                notification_type=notification_type,
                target_users=target_users
            )
            
            logger.info(
                "System notification sent",
                notification_type=notification_type,
                target_users=target_users
            )
            
        except Exception as e:
            logger.error("Failed to send system notification", error=str(e))
    
    async def create_status_history_entry(
        self,
        donation_id: str,
        status: str,
        actor_id: str,
        actor_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create donation status history entry"""
        
        try:
            # Insert status history record
            status_entry = {
                "donation_id": donation_id,
                "status": status,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "description": description,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(Tables.DONATION_STATUS_HISTORY).insert(status_entry).execute()
            
            if result.data:
                logger.info(
                    "Status history entry created",
                    donation_id=donation_id,
                    status=status,
                    actor_id=actor_id
                )
                return result.data[0]
            
        except Exception as e:
            logger.error("Failed to create status history entry", error=str(e))
            return None
    
    async def update_donation_status_with_notification(
        self,
        donation_id: str,
        new_status: str,
        actor_id: str,
        actor_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update donation status and send notifications"""
        
        try:
            # Get current donation
            donation_response = self.supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()
            
            if not donation_response.data:
                logger.error("Donation not found for status update", donation_id=donation_id)
                return False
            
            donation = donation_response.data[0]
            old_status = donation.get("status")
            user_id = donation.get("donor_id")
            
            # Update donation status
            update_result = self.supabase.table(Tables.DONATIONS).update({
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", donation_id).execute()
            
            if not update_result.data:
                logger.error("Failed to update donation status", donation_id=donation_id)
                return False
            
            # Create status history entry
            await self.create_status_history_entry(
                donation_id=donation_id,
                status=new_status,
                actor_id=actor_id,
                actor_type=actor_type,
                description=description,
                metadata=metadata
            )
            
            # Send notification
            await self.notify_donation_status_change(
                donation_id=donation_id,
                old_status=old_status,
                new_status=new_status,
                user_id=user_id,
                details=metadata
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update donation status with notification", error=str(e))
            return False


# Global notification service instance
notification_service = NotificationService()


# Convenience functions
async def notify_donation_status_change(donation_id: str, old_status: str, new_status: str, user_id: str, details: Optional[Dict[str, Any]] = None):
    """Convenience function for donation status notifications"""
    await notification_service.notify_donation_status_change(donation_id, old_status, new_status, user_id, details)


async def notify_payment_status_change(payment_reference: str, old_status: str, new_status: str, user_id: str, details: Optional[Dict[str, Any]] = None):
    """Convenience function for payment status notifications"""
    await notification_service.notify_payment_status_change(payment_reference, old_status, new_status, user_id, details)


async def notify_donation_matched(donation_id: str, user_id: str, hospital_id: str, hospital_name: str, details: Optional[Dict[str, Any]] = None):
    """Convenience function for donation matching notifications"""
    await notification_service.notify_donation_matched(donation_id, user_id, hospital_id, hospital_name, details)
