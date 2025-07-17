"""
Ytili Chatbot Interface
High-level chatbot interface for different conversation types
"""
from typing import Dict, List, Optional, Any, AsyncGenerator
import structlog

from .agent_service import ytili_ai_agent
from .donation_advisor import donation_advisor
from .emergency_handler import emergency_handler
from ..models.ai_agent import ConversationType

logger = structlog.get_logger()


class YtiliChatbot:
    """
    High-level chatbot interface that routes conversations to appropriate handlers
    """
    
    def __init__(self):
        self.ai_agent = ytili_ai_agent
        self.donation_advisor = donation_advisor
        self.emergency_handler = emergency_handler
    
    async def start_chat(
        self,
        user_id: int,
        conversation_type: str = "general_support",
        initial_message: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Start a new chat session
        
        Args:
            user_id: ID of the user
            conversation_type: Type of conversation (donation_advisory, medical_info, etc.)
            initial_message: Optional initial message
            context: Additional context data
            
        Returns:
            Chat session information
        """
        try:
            # Convert string to enum
            conv_type = ConversationType(conversation_type)
            
            # Add user context if available
            if not context:
                context = {}
            
            # Get user information for context
            user_context = await self._get_user_context(user_id)
            context.update(user_context)
            
            # Start conversation with AI agent
            result = await self.ai_agent.start_conversation(
                user_id=user_id,
                conversation_type=conv_type,
                initial_message=initial_message,
                context_data=context
            )
            
            if result["success"]:
                # If it's an emergency, also trigger emergency handler
                if conv_type == ConversationType.EMERGENCY_REQUEST:
                    await self.emergency_handler.process_emergency_request(
                        user_id=user_id,
                        session_id=result["session_id"],
                        initial_message=initial_message or ""
                    )
                
                # Add welcome message based on conversation type
                welcome_message = self._get_welcome_message(conv_type)
                if welcome_message:
                    result["welcome_message"] = welcome_message
            
            return result
            
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid conversation type: {conversation_type}"
            }
        except Exception as e:
            logger.error(f"Failed to start chat: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message in an existing chat session
        
        Args:
            session_id: Chat session ID
            message: User message
            stream: Whether to stream the response
            
        Returns:
            AI response or stream generator
        """
        try:
            # Check if this is an emergency conversation
            conversation_type = await self._get_conversation_type(session_id)
            
            # For emergency conversations, also process with emergency handler
            if conversation_type == ConversationType.EMERGENCY_REQUEST:
                await self.emergency_handler.update_emergency_request(
                    session_id=session_id,
                    new_message=message
                )
            
            # Send message to AI agent
            response = await self.ai_agent.send_message(
                session_id=session_id,
                user_message=message,
                stream=stream
            )
            
            # If this is a donation advisory conversation, check for recommendations
            if (conversation_type == ConversationType.DONATION_ADVISORY and 
                response.get("success")):
                
                # Generate donation recommendations based on conversation
                recommendations = await self.donation_advisor.generate_recommendations(
                    session_id=session_id,
                    user_message=message,
                    ai_response=response.get("response", "")
                )
                
                if recommendations:
                    response["recommendations"] = recommendations
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to return
            
        Returns:
            Conversation history
        """
        try:
            # Get conversation info
            conversation_result = self.ai_agent.supabase.table("ai_conversations").select("*").eq("session_id", session_id).execute()
            
            if not conversation_result.data:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            conversation = conversation_result.data[0]
            
            # Get messages
            messages_result = self.ai_agent.supabase.table("ai_messages").select("*").eq("conversation_id", conversation["id"]).order("created_at").limit(limit).execute()
            
            return {
                "success": True,
                "conversation": conversation,
                "messages": messages_result.data
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def end_conversation(
        self,
        session_id: str,
        user_feedback: Optional[str] = None,
        satisfaction_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        End a conversation session
        
        Args:
            session_id: Chat session ID
            user_feedback: Optional user feedback
            satisfaction_score: User satisfaction rating (1-5)
            
        Returns:
            Success status
        """
        try:
            update_data = {
                "status": "completed",
                "completed_at": "now()",
                "updated_at": "now()"
            }
            
            if satisfaction_score:
                update_data["user_satisfaction_score"] = satisfaction_score
            
            result = self.ai_agent.supabase.table("ai_conversations").update(update_data).eq("session_id", session_id).execute()
            
            # Save feedback if provided
            if user_feedback and result.data:
                conversation_id = result.data[0]["id"]
                self.ai_agent.supabase.table("ai_messages").insert({
                    "conversation_id": conversation_id,
                    "role": "feedback",
                    "content": user_feedback,
                    "created_at": "now()"
                }).execute()
            
            return {
                "success": True,
                "message": "Conversation ended successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to end conversation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get user context information"""
        try:
            # Get user info from Supabase
            user_result = self.ai_agent.supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                return {}
            
            user = user_result.data[0]
            
            # Get user donation history
            donations_result = self.ai_agent.supabase.table("donations").select("*").eq("donor_id", user_id).limit(10).execute()
            
            # Get user points
            points_result = self.ai_agent.supabase.table("user_points").select("*").eq("user_id", user_id).execute()
            
            context = {
                "user_type": user.get("user_type"),
                "location": {
                    "city": user.get("city"),
                    "province": user.get("province")
                },
                "donation_history": len(donations_result.data) if donations_result.data else 0,
                "points": points_result.data[0] if points_result.data else None,
                "is_verified": user.get("is_kyc_verified", False)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get user context: {str(e)}")
            return {}
    
    async def _get_conversation_type(self, session_id: str) -> Optional[ConversationType]:
        """Get conversation type for a session"""
        try:
            result = self.ai_agent.supabase.table("ai_conversations").select("conversation_type").eq("session_id", session_id).execute()
            
            if result.data:
                return ConversationType(result.data[0]["conversation_type"])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation type: {str(e)}")
            return None
    
    def _get_welcome_message(self, conversation_type: ConversationType) -> Optional[str]:
        """Get welcome message for conversation type"""
        welcome_messages = {
            ConversationType.DONATION_ADVISORY: 
                "Xin chào! Tôi là Ytili AI Agent, sẵn sàng giúp bạn tìm hiểu về các cơ hội quyên góp y tế phù hợp. Hãy cho tôi biết ngân sách và sở thích của bạn để tôi có thể đưa ra gợi ý tốt nhất!",
            
            ConversationType.MEDICAL_INFO:
                "Xin chào! Tôi có thể cung cấp thông tin y tế tổng quát và hướng dẫn bạn đến các nguồn tài nguyên phù hợp. Lưu ý: Tôi không thể thay thế lời khuyên của bác sĩ chuyên nghiệp.",
            
            ConversationType.CAMPAIGN_HELP:
                "Xin chào! Tôi sẽ giúp bạn tạo và quản lý chiến dịch gây quỹ y tế hiệu quả. Hãy chia sẻ về tình huống y tế cần hỗ trợ để tôi có thể đưa ra lời khuyên tốt nhất!",
            
            ConversationType.EMERGENCY_REQUEST:
                "🚨 KHẨN CẤP: Tôi đã nhận được yêu cầu hỗ trợ y tế khẩn cấp của bạn. Vui lòng mô tả chi tiết tình huống để tôi có thể kết nối bạn với nguồn hỗ trợ phù hợp ngay lập tức.",
            
            ConversationType.GENERAL_SUPPORT:
                "Xin chào! Tôi là Ytili AI Agent, trợ lý thông minh của nền tảng quyên góp y tế Ytili. Tôi có thể giúp bạn điều hướng nền tảng, hiểu về quy trình quyên góp, và trả lời các câu hỏi về dịch vụ của chúng tôi."
        }
        
        return welcome_messages.get(conversation_type)


# Global chatbot instance
ytili_chatbot = YtiliChatbot()
