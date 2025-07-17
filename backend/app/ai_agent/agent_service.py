"""
Ytili AI Agent Service
Main service class for managing AI conversations and providing intelligent assistance
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator
import structlog

from .openrouter_client import openrouter_client
from ..models.ai_agent import (
    AIConversation, AIMessage, ConversationType, 
    ConversationStatus, AIRecommendation, RecommendationType
)
from ..models.user import User
from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class YtiliAIAgent:
    """
    Main AI Agent service for Ytili platform
    Handles conversation management, context awareness, and intelligent responses
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self.system_prompts = {
            ConversationType.DONATION_ADVISORY: self._get_donation_advisory_prompt(),
            ConversationType.MEDICAL_INFO: self._get_medical_info_prompt(),
            ConversationType.CAMPAIGN_HELP: self._get_campaign_help_prompt(),
            ConversationType.EMERGENCY_REQUEST: self._get_emergency_request_prompt(),
            ConversationType.GENERAL_SUPPORT: self._get_general_support_prompt()
        }
    
    def _get_donation_advisory_prompt(self) -> str:
        """System prompt for donation advisory conversations"""
        return """You are Ytili AI Agent, an intelligent assistant for the Ytili medical donation platform in Vietnam. 

Your role is to help users make informed donation decisions by:
1. Understanding their budget and preferences
2. Matching them with relevant medical campaigns and hospitals in need
3. Providing transparent information about donation impact
4. Suggesting appropriate donation amounts and types (medication, medical supplies, cash)
5. Explaining the donation process and tracking

Key guidelines:
- Always prioritize transparency and user trust
- Provide specific, actionable recommendations
- Consider Vietnamese medical system context
- Explain how donations will be tracked on blockchain
- Be empathetic and supportive
- Ask clarifying questions to better understand user needs
- Suggest emergency cases when appropriate

Remember: You're helping save lives through intelligent donation matching."""
    
    def _get_medical_info_prompt(self) -> str:
        """System prompt for medical information conversations"""
        return """You are Ytili AI Agent providing medical information support for the Vietnamese healthcare context.

IMPORTANT DISCLAIMERS:
- You are NOT a doctor and cannot provide medical diagnosis or treatment advice
- Always recommend consulting qualified healthcare professionals
- Your role is to provide general health information and guide users to appropriate resources

You can help with:
1. General health information and education
2. Explaining common medical conditions and symptoms
3. Directing users to appropriate medical specialties
4. Information about medications and their general uses
5. Guidance on when to seek emergency medical care
6. Connecting users with relevant hospitals or clinics

Vietnamese medical context:
- Understand Vietnamese healthcare system structure
- Know major hospitals and medical centers
- Be aware of common health issues in Vietnam
- Respect cultural health practices and beliefs

Always end medical discussions with: "Please consult with a qualified healthcare professional for proper medical advice."
"""
    
    def _get_campaign_help_prompt(self) -> str:
        """System prompt for campaign assistance conversations"""
        return """You are Ytili AI Agent helping users create and manage medical fundraising campaigns.

Your expertise includes:
1. Campaign creation guidance and best practices
2. Writing compelling campaign descriptions
3. Setting realistic fundraising goals
4. Targeting the right audience
5. Optimizing campaign visibility and engagement
6. Providing fundraising strategy advice
7. Analyzing campaign performance

Campaign optimization tips:
- Use emotional storytelling while maintaining authenticity
- Include specific medical details and costs
- Add verification documents and hospital information
- Set clear milestones and updates
- Engage with donors through regular updates
- Leverage social media and community networks

Vietnamese fundraising context:
- Understand local donation patterns and preferences
- Know effective communication styles for Vietnamese audience
- Be aware of cultural sensitivities around medical issues
- Suggest appropriate local partnerships and endorsements

Help users create campaigns that build trust and achieve their medical funding goals."""
    
    def _get_emergency_request_prompt(self) -> str:
        """System prompt for emergency medical requests"""
        return """You are Ytili AI Agent handling EMERGENCY medical requests. This requires immediate, focused assistance.

EMERGENCY PROTOCOL:
1. Assess urgency level (Low/Medium/High/Critical)
2. Gather essential information quickly
3. Route to appropriate hospitals/resources immediately
4. Provide clear next steps
5. Follow up on response time

Critical information to collect:
- Medical condition/emergency type
- Current location
- Contact information
- Immediate medical needs
- Available transportation

Emergency categories:
- CRITICAL: Life-threatening (cardiac arrest, severe trauma, stroke)
- HIGH: Urgent medical attention needed (severe pain, breathing difficulty)
- MEDIUM: Important but not immediately life-threatening
- LOW: Can wait for regular medical appointment

For CRITICAL/HIGH emergencies:
- Immediately suggest calling emergency services (115 in Vietnam)
- Route to nearest appropriate hospital
- Connect with available medical volunteers
- Coordinate emergency medication/supply delivery

Response time targets:
- Critical: <5 minutes
- High: <15 minutes  
- Medium: <30 minutes
- Low: <2 hours

Stay calm, be efficient, and prioritize life-saving actions."""
    
    def _get_general_support_prompt(self) -> str:
        """System prompt for general support conversations"""
        return """You are Ytili AI Agent, the helpful assistant for the Ytili medical donation platform.

You can assist users with:
1. Platform navigation and features
2. Account management questions
3. Understanding donation processes
4. Explaining point/reward systems
5. Technical support for basic issues
6. General information about Ytili's mission and services

Platform knowledge:
- Ytili connects donors with hospitals and medical campaigns
- Uses blockchain for transparency and tracking
- Offers points/rewards for donations
- Supports multiple donation types (cash, medication, supplies)
- Serves Vietnamese healthcare community
- Integrates with VietQR for payments

Communication style:
- Friendly and approachable
- Clear and concise explanations
- Patient with user questions
- Proactive in offering help
- Culturally sensitive to Vietnamese context

If users need specialized help (medical advice, complex technical issues, legal questions), guide them to appropriate human support or external resources.

Your goal is to make the Ytili platform easy and enjoyable to use while building trust in our mission to improve healthcare access in Vietnam."""
    
    async def start_conversation(
        self,
        user_id: int,
        conversation_type: ConversationType,
        initial_message: Optional[str] = None,
        context_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Start a new AI conversation session
        
        Args:
            user_id: ID of the user starting the conversation
            conversation_type: Type of conversation
            initial_message: Optional initial user message
            context_data: Additional context information
            
        Returns:
            Conversation session information
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Create conversation record in Supabase
            conversation_data = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_type": conversation_type.value,
                "status": ConversationStatus.ACTIVE.value,
                "context_data": context_data or {},
                "conversation_metadata": {
                    "model": openrouter_client.primary_model,
                    "created_by": "ytili_ai_agent"
                },
                "total_messages": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("ai_conversations").insert(conversation_data).execute()
            
            if not result.data:
                raise Exception("Failed to create conversation record")
            
            conversation_id = result.data[0]["id"]
            
            # Prepare initial messages
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompts[conversation_type]
                }
            ]
            
            # Add initial user message if provided
            if initial_message:
                messages.append({
                    "role": "user", 
                    "content": initial_message
                })
                
                # Save user message
                await self._save_message(
                    conversation_id, "user", initial_message
                )
            
            logger.info(
                "Started AI conversation",
                session_id=session_id,
                user_id=user_id,
                conversation_type=conversation_type.value
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "conversation_type": conversation_type.value,
                "message": "Conversation started successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_message(
        self,
        session_id: str,
        user_message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message in an existing conversation
        
        Args:
            session_id: Conversation session ID
            user_message: User's message
            stream: Whether to stream the response
            
        Returns:
            AI response or error information
        """
        try:
            # Get conversation from database
            conversation_result = self.supabase.table("ai_conversations").select("*").eq("session_id", session_id).execute()
            
            if not conversation_result.data:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            conversation = conversation_result.data[0]
            conversation_id = conversation["id"]
            conversation_type = ConversationType(conversation["conversation_type"])
            
            # Get conversation history
            messages = await self._get_conversation_messages(conversation_id)
            
            # Add system prompt if not present
            if not messages or messages[0]["role"] != "system":
                messages.insert(0, {
                    "role": "system",
                    "content": self.system_prompts[conversation_type]
                })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Save user message
            await self._save_message(conversation_id, "user", user_message)
            
            # Get AI response
            if stream:
                return await self._stream_ai_response(conversation_id, messages)
            else:
                return await self._get_ai_response(conversation_id, messages)
                
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_conversation_messages(self, conversation_id: int) -> List[Dict[str, str]]:
        """Get conversation message history"""
        try:
            result = self.supabase.table("ai_messages").select("role, content").eq("conversation_id", conversation_id).order("created_at").execute()
            
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in result.data
            ]
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {str(e)}")
            return []
    
    async def _save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_time: Optional[float] = None
    ) -> bool:
        """Save a message to the database"""
        try:
            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "model_used": model_used,
                "tokens_used": tokens_used,
                "response_time": response_time,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("ai_messages").insert(message_data).execute()
            
            # Update conversation message count
            self.supabase.table("ai_conversations").update({
                "total_messages": self.supabase.rpc("increment_total_messages", {"conversation_id": conversation_id}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", conversation_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Failed to save message: {str(e)}")
            return False
    
    async def _get_ai_response(self, conversation_id: int, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get AI response for conversation"""
        try:
            # Call OpenRouter API
            response = await openrouter_client.chat_completion(messages)
            
            if response["success"]:
                # Save AI response
                await self._save_message(
                    conversation_id,
                    "assistant",
                    response["response"],
                    response["model_used"],
                    response["tokens_used"],
                    response["response_time"]
                )
                
                return {
                    "success": True,
                    "response": response["response"],
                    "model_used": response["model_used"],
                    "tokens_used": response["tokens_used"],
                    "response_time": response["response_time"]
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Failed to get AI response: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _stream_ai_response(self, conversation_id: int, messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream AI response for conversation"""
        try:
            full_response = ""
            
            async for chunk in openrouter_client._stream_completion(
                messages, 
                openrouter_client.primary_model, 
                0.7, 
                openrouter_client.max_response_tokens
            ):
                if chunk["success"] and not chunk["is_complete"]:
                    full_response += chunk["content"]
                    yield chunk
                elif chunk["is_complete"]:
                    # Save complete response
                    if chunk["success"]:
                        await self._save_message(
                            conversation_id,
                            "assistant", 
                            full_response,
                            chunk["model_used"],
                            None,  # Token count not available in streaming
                            chunk.get("response_time")
                        )
                    yield chunk
                    break
                else:
                    yield chunk
                    break
                    
        except Exception as e:
            logger.error(f"Failed to stream AI response: {str(e)}")
            yield {
                "success": False,
                "error": str(e),
                "is_complete": True
            }


# Global AI agent instance
ytili_ai_agent = YtiliAIAgent()
