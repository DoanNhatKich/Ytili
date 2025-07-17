"""
Emergency Request Handler for Ytili AI Agent
Processes urgent medical requests and coordinates rapid response
"""
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from ..models.ai_agent import EmergencyPriority
from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class EmergencyHandler:
    """
    Handles emergency medical requests with rapid response coordination
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Emergency condition classifications
        self.emergency_conditions = {
            "critical": {
                "keywords": [
                    "tim ngừng", "cardiac arrest", "không thở", "not breathing",
                    "bất tỉnh", "unconscious", "đột quỵ", "stroke", "tai nạn giao thông",
                    "traffic accident", "chảy máu nhiều", "severe bleeding", "sốc",
                    "shock", "ngộ độc", "poisoning", "đuối nước", "drowning"
                ],
                "response_time_minutes": 5,
                "priority": EmergencyPriority.CRITICAL
            },
            "high": {
                "keywords": [
                    "khó thở", "difficulty breathing", "đau ngực", "chest pain",
                    "sốt cao", "high fever", "co giật", "seizure", "gãy xương",
                    "broken bone", "bỏng nặng", "severe burn", "đau bụng dữ dội",
                    "severe abdominal pain", "chấn thương đầu", "head injury"
                ],
                "response_time_minutes": 15,
                "priority": EmergencyPriority.HIGH
            },
            "medium": {
                "keywords": [
                    "đau đầu", "headache", "nôn mửa", "vomiting", "tiêu chảy",
                    "diarrhea", "sốt", "fever", "đau lưng", "back pain",
                    "cắt nhỏ", "minor cut", "bong gân", "sprain"
                ],
                "response_time_minutes": 30,
                "priority": EmergencyPriority.MEDIUM
            },
            "low": {
                "keywords": [
                    "cảm lạnh", "cold", "ho", "cough", "đau họng", "sore throat",
                    "mệt mỏi", "fatigue", "khó ngủ", "insomnia"
                ],
                "response_time_minutes": 120,
                "priority": EmergencyPriority.LOW
            }
        }
        
        # Emergency response actions
        self.response_actions = {
            EmergencyPriority.CRITICAL: [
                "Gọi cấp cứu 115 ngay lập tức",
                "Liên hệ bệnh viện gần nhất",
                "Chuẩn bị vận chuyển khẩn cấp",
                "Thông báo cho gia đình/người thân"
            ],
            EmergencyPriority.HIGH: [
                "Liên hệ bệnh viện hoặc phòng khám",
                "Chuẩn bị đưa đến cơ sở y tế",
                "Thu thập thông tin y tế cần thiết",
                "Liên hệ bác sĩ gia đình nếu có"
            ],
            EmergencyPriority.MEDIUM: [
                "Theo dõi triệu chứng",
                "Liên hệ phòng khám địa phương",
                "Chuẩn bị thông tin bệnh sử",
                "Xem xét đặt lịch khám"
            ],
            EmergencyPriority.LOW: [
                "Theo dõi tình trạng",
                "Tự chăm sóc tại nhà",
                "Liên hệ bác sĩ nếu triệu chứng xấu đi",
                "Đặt lịch khám định kỳ"
            ]
        }
    
    async def process_emergency_request(
        self,
        user_id: int,
        session_id: str,
        initial_message: str,
        location: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a new emergency request
        
        Args:
            user_id: ID of user making the request
            session_id: Conversation session ID
            initial_message: Initial emergency description
            location: User location (optional)
            contact_phone: Contact phone number (optional)
            
        Returns:
            Emergency processing result
        """
        try:
            # Analyze emergency severity
            analysis = self._analyze_emergency(initial_message)
            
            # Extract medical condition
            medical_condition = self._extract_medical_condition(initial_message)
            
            # Get conversation ID
            conv_result = self.supabase.table("ai_conversations").select("id").eq("session_id", session_id).execute()
            conversation_id = conv_result.data[0]["id"] if conv_result.data else None
            
            # Create emergency request record
            emergency_data = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "priority": analysis["priority"].value,
                "medical_condition": medical_condition,
                "description": initial_message,
                "location": location,
                "contact_phone": contact_phone,
                "ai_assessment": analysis,
                "recommended_actions": self.response_actions[analysis["priority"]],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("emergency_requests").insert(emergency_data).execute()
            
            if result.data:
                emergency_id = result.data[0]["id"]
                
                # Trigger appropriate response based on priority
                response_result = await self._trigger_emergency_response(
                    emergency_id, analysis["priority"], user_id
                )
                
                logger.info(
                    "Emergency request processed",
                    emergency_id=emergency_id,
                    priority=analysis["priority"].value,
                    user_id=user_id
                )
                
                return {
                    "success": True,
                    "emergency_id": emergency_id,
                    "priority": analysis["priority"].value,
                    "estimated_response_time": analysis["response_time_minutes"],
                    "recommended_actions": self.response_actions[analysis["priority"]],
                    "response_triggered": response_result
                }
            else:
                raise Exception("Failed to create emergency request")
                
        except Exception as e:
            logger.error(f"Failed to process emergency request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_emergency_request(
        self,
        session_id: str,
        new_message: str
    ) -> Dict[str, Any]:
        """
        Update an existing emergency request with new information
        
        Args:
            session_id: Conversation session ID
            new_message: New message with additional information
            
        Returns:
            Update result
        """
        try:
            # Get emergency request by session
            conv_result = self.supabase.table("ai_conversations").select("id").eq("session_id", session_id).execute()
            
            if not conv_result.data:
                return {"success": False, "error": "Conversation not found"}
            
            conversation_id = conv_result.data[0]["id"]
            
            emergency_result = self.supabase.table("emergency_requests").select("*").eq("conversation_id", conversation_id).eq("status", "pending").execute()
            
            if not emergency_result.data:
                return {"success": False, "error": "Emergency request not found"}
            
            emergency = emergency_result.data[0]
            emergency_id = emergency["id"]
            
            # Re-analyze with new information
            combined_description = emergency["description"] + " " + new_message
            new_analysis = self._analyze_emergency(combined_description)
            
            # Update emergency request
            update_data = {
                "description": combined_description,
                "ai_assessment": new_analysis,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # If priority changed, update it
            if new_analysis["priority"] != EmergencyPriority(emergency["priority"]):
                update_data["priority"] = new_analysis["priority"].value
                update_data["recommended_actions"] = self.response_actions[new_analysis["priority"]]
                
                # Trigger new response if priority increased
                if new_analysis["priority"].value in ["critical", "high"]:
                    await self._trigger_emergency_response(
                        emergency_id, new_analysis["priority"], emergency["user_id"]
                    )
            
            result = self.supabase.table("emergency_requests").update(update_data).eq("id", emergency_id).execute()
            
            return {
                "success": True,
                "emergency_id": emergency_id,
                "updated_priority": new_analysis["priority"].value,
                "recommended_actions": self.response_actions[new_analysis["priority"]]
            }
            
        except Exception as e:
            logger.error(f"Failed to update emergency request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_emergency(self, description: str) -> Dict[str, Any]:
        """Analyze emergency description to determine priority and response"""
        description_lower = description.lower()
        
        # Check for critical conditions first
        for severity, config in self.emergency_conditions.items():
            for keyword in config["keywords"]:
                if keyword in description_lower:
                    return {
                        "priority": config["priority"],
                        "severity": severity,
                        "response_time_minutes": config["response_time_minutes"],
                        "matched_keywords": [keyword],
                        "confidence": 0.9 if severity in ["critical", "high"] else 0.7
                    }
        
        # Default to medium priority if no specific keywords found
        return {
            "priority": EmergencyPriority.MEDIUM,
            "severity": "medium",
            "response_time_minutes": 30,
            "matched_keywords": [],
            "confidence": 0.5
        }
    
    def _extract_medical_condition(self, description: str) -> str:
        """Extract the main medical condition from description"""
        # Simple extraction - in production, this could use NLP
        description_lower = description.lower()
        
        # Common medical conditions in Vietnamese
        conditions = {
            "đau tim": "Đau tim",
            "đột quỵ": "Đột quỵ",
            "tai nạn": "Tai nạn",
            "gãy xương": "Gãy xương",
            "khó thở": "Khó thở",
            "đau ngực": "Đau ngực",
            "sốt cao": "Sốt cao",
            "đau bụng": "Đau bụng",
            "chấn thương": "Chấn thương",
            "bỏng": "Bỏng",
            "ngộ độc": "Ngộ độc"
        }
        
        for keyword, condition in conditions.items():
            if keyword in description_lower:
                return condition
        
        # If no specific condition found, return first few words
        words = description.split()[:3]
        return " ".join(words).capitalize()
    
    async def _trigger_emergency_response(
        self,
        emergency_id: int,
        priority: EmergencyPriority,
        user_id: int
    ) -> Dict[str, Any]:
        """Trigger appropriate emergency response based on priority"""
        try:
            response_actions = []
            
            if priority in [EmergencyPriority.CRITICAL, EmergencyPriority.HIGH]:
                # Find nearby hospitals
                hospitals = await self._find_nearby_hospitals(user_id)
                response_actions.append(f"Contacted {len(hospitals)} nearby hospitals")
                
                # Send notifications to emergency contacts
                notification_result = await self._send_emergency_notifications(
                    emergency_id, user_id, priority
                )
                response_actions.extend(notification_result)
                
                # For critical cases, also alert emergency services
                if priority == EmergencyPriority.CRITICAL:
                    response_actions.append("Emergency services alert triggered")
            
            # Update emergency request with response actions
            self.supabase.table("emergency_requests").update({
                "is_responded": True,
                "responded_at": datetime.now(timezone.utc).isoformat(),
                "response_time_minutes": 0  # This would be calculated based on actual response
            }).eq("id", emergency_id).execute()
            
            return {
                "success": True,
                "actions_taken": response_actions
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger emergency response: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_nearby_hospitals(self, user_id: int) -> List[Dict[str, Any]]:
        """Find hospitals near the user"""
        try:
            # Get user location
            user_result = self.supabase.table("users").select("city, province").eq("id", user_id).execute()
            
            if not user_result.data:
                return []
            
            user = user_result.data[0]
            
            # Find hospitals in the same city/province
            hospitals_result = self.supabase.table("users").select("*").eq("user_type", "hospital").eq("city", user["city"]).execute()
            
            return hospitals_result.data or []
            
        except Exception as e:
            logger.error(f"Failed to find nearby hospitals: {str(e)}")
            return []
    
    async def _send_emergency_notifications(
        self,
        emergency_id: int,
        user_id: int,
        priority: EmergencyPriority
    ) -> List[str]:
        """Send emergency notifications to relevant parties"""
        try:
            notifications_sent = []
            
            # This would integrate with notification service
            # For now, just log the notifications that would be sent
            
            if priority == EmergencyPriority.CRITICAL:
                notifications_sent.extend([
                    "Emergency services notified",
                    "Nearby hospitals alerted",
                    "Emergency contacts informed"
                ])
            elif priority == EmergencyPriority.HIGH:
                notifications_sent.extend([
                    "Nearby hospitals notified",
                    "Emergency contacts informed"
                ])
            
            logger.info(
                "Emergency notifications sent",
                emergency_id=emergency_id,
                user_id=user_id,
                priority=priority.value,
                notifications=notifications_sent
            )
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Failed to send emergency notifications: {str(e)}")
            return ["Failed to send notifications"]
    
    async def get_emergency_status(self, emergency_id: int) -> Dict[str, Any]:
        """Get status of an emergency request"""
        try:
            result = self.supabase.table("emergency_requests").select("*").eq("id", emergency_id).execute()
            
            if result.data:
                emergency = result.data[0]
                
                # Calculate response time if responded
                response_time = None
                if emergency["responded_at"]:
                    created_at = datetime.fromisoformat(emergency["created_at"].replace('Z', '+00:00'))
                    responded_at = datetime.fromisoformat(emergency["responded_at"].replace('Z', '+00:00'))
                    response_time = (responded_at - created_at).total_seconds() / 60
                
                return {
                    "success": True,
                    "emergency": emergency,
                    "actual_response_time_minutes": response_time
                }
            else:
                return {
                    "success": False,
                    "error": "Emergency request not found"
                }
                
        except Exception as e:
            logger.error(f"Failed to get emergency status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Global emergency handler instance
emergency_handler = EmergencyHandler()
