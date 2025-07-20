"""
Ytili AI Agent Service
Main service class for managing AI conversations and providing intelligent assistance
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator
import structlog
import asyncio

from .openrouter_client import openrouter_client
from .rag_service import rag_service
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

        # --- In-memory fallback storage (activated if Supabase is unavailable) ---
        # Keyed by session_id
        self._memory_conversations: Dict[str, Dict[str, Any]] = {}
        # Keyed by session_id -> list of message dicts {role, content}
        self._memory_messages: Dict[str, List[Dict[str, str]]] = {}
        # Flag toggled to True once any Supabase operation fails. All subsequent
        # conversation and message operations use the in-memory fallback to avoid
        # repeated network errors.
        self._memory_enabled: bool = False
    
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
- Use the provided context from the knowledge base to give accurate information
- If context is provided, reference it in your response

Remember: You're helping save lives through intelligent donation matching.

IMPORTANT: If relevant context is provided below, use it to enhance your response with accurate, verified information."""
    
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

IMPORTANT: If relevant medical context is provided below from verified sources, use it to enhance your response with accurate information. Always cite the source when using provided context.

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
        user_id: str,  # Changed from int to str
        conversation_type: ConversationType,
        initial_message: Optional[str] = None,
        context_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Start a new AI conversation session"""
        try:
            session_id = str(uuid.uuid4())

            # Handle user_id - create anonymous user if needed
            if user_id == "anonymous":
                # Create or get anonymous user
                db_user_id = await self._get_or_create_anonymous_user()
            else:
                try:
                    # Try to parse as UUID, if it fails, generate a new one
                    uuid.UUID(user_id)
                    # Check if user exists, if not create anonymous user
                    user_exists = await self._check_user_exists(user_id)
                    if user_exists:
                        db_user_id = user_id
                    else:
                        logger.warning(f"User {user_id} not found, using anonymous user")
                        db_user_id = await self._get_or_create_anonymous_user()
                except ValueError:
                    # If user_id is not a valid UUID, use anonymous user
                    logger.warning(f"Invalid UUID format for user_id: {user_id}, using anonymous user")
                    db_user_id = await self._get_or_create_anonymous_user()

            # Create conversation record in Supabase
            conversation_data = {
                "user_id": db_user_id,
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

            # Try persisting the conversation in Supabase. If this fails (e.g. the
            # database is unreachable in local/offline environments) fall back to
            # an in-memory conversation store so that the rest of the chat flow
            # continues to work gracefully.
            try:
                result = self.supabase.table("ai_conversations").insert(conversation_data).execute()

                if not result.data:
                    raise Exception("Failed to create conversation record")

                conversation_id = result.data[0]["id"]
            except Exception as supabase_error:
                # Activate memory fallback and store conversation locally
                logger.warning(
                    "Supabase unavailable – falling back to in-memory storage for conversations",
                    error=str(supabase_error)
                )
                self._memory_enabled = True
                conversation_id = None  # Not available when using memory
                self._memory_conversations[session_id] = conversation_data.copy()

            # Add initial user message if provided
            if initial_message:
                await self._save_message(
                    conversation_id or session_id,  # Accept either int ID or session_id string in memory mode
                    "user",
                    initial_message
                )
            
            logger.info(
                "Conversation started",
                user_id=db_user_id,
                session_id=session_id,
                type=conversation_type.value,
                storage="memory" if self._memory_enabled else "supabase"
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "conversation_type": conversation_type.value
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
            # ------------------------------------------------------------------
            # Retrieve conversation, supporting both Supabase and in-memory modes
            # ------------------------------------------------------------------

            if self._memory_enabled:
                conversation = self._memory_conversations.get(session_id)
                if not conversation:
                    return {"success": False, "error": "Conversation not found"}

                # In memory mode we use session_id as identifier instead of an int
                conversation_id = session_id  # type: ignore[assignment]
                conversation_type = ConversationType(conversation["conversation_type"])
            else:
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

            # Enhance context with comprehensive database queries
            if self._memory_enabled:
                enhanced_context = None
            else:
                # Use new comprehensive database query service
                from .database_query_service import database_query_service
                enhanced_context, _ = await database_query_service.query_comprehensive_context(
                    user_message, conversation_type.value
                )
                
                # Fallback to original RAG if no comprehensive context found
                if not enhanced_context:
                    enhanced_context, _ = await rag_service.enhance_conversation_context(
                        conversation_id, user_message, conversation_type.value
                    )

            # Prepare user message with enhanced context
            user_content = user_message
            if enhanced_context:
                user_content = f"""User Question: {user_message}

Relevant Context from Knowledge Base:
{enhanced_context}

Please use the above context to provide a more accurate and helpful response."""

            # Add user message
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # Save user message (original message, not enhanced)
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
            if self._memory_enabled:
                # Retrieve messages from memory store using session_id string
                session_key = conversation_id if isinstance(conversation_id, str) else None
                return self._memory_messages.get(session_key, [])

            result = self.supabase.table("ai_messages").select("role, content").eq("conversation_id", conversation_id).order("created_at").execute()
            
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in result.data
            ]
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {str(e)}")
            self._memory_enabled = True
            # Fallback to memory if available
            session_key = conversation_id if isinstance(conversation_id, str) else None
            return self._memory_messages.get(session_key, [])
            return []
    
    async def _save_message(self, conversation_id: int, role: str, content: str, model_used: str = None, tokens_used: int = None, response_time: float = None):
        """Save message to database"""
        try:
            # If memory fallback is active, store messages in the in-memory dict
            if self._memory_enabled:
                session_key = conversation_id if isinstance(conversation_id, str) else None
                if session_key is None:
                    # Supabase conversation IDs are ints – we need to map them
                    # to a session_id for memory storage. Skip if not available.
                    logger.debug("Memory mode active but session key missing – skipping message save")
                    return None

                self._memory_messages.setdefault(session_key, []).append({
                    "role": role,
                    "content": content
                })
                return None

            # Prepare metadata if additional info provided
            metadata = {}
            if model_used:
                metadata["model_used"] = model_used
            if tokens_used:
                metadata["tokens_used"] = tokens_used
            if response_time:
                metadata["response_time"] = response_time
        
            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Only add metadata if the column exists
            if metadata:
                try:
                    # Test if metadata column exists by attempting to insert with it
                    test_data = message_data.copy()
                    test_data["metadata"] = metadata
                    result = self.supabase.table("ai_messages").insert(test_data).execute()
                except Exception as e:
                    if "metadata" in str(e):
                        # Metadata column doesn't exist, insert without it
                        result = self.supabase.table("ai_messages").insert(message_data).execute()
                    else:
                        raise e
            else:
                result = self.supabase.table("ai_messages").insert(message_data).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("Failed to save message", error=str(e))
            # Switch to memory mode for future operations
            self._memory_enabled = True
            return None
    
    async def _get_ai_response(self, conversation_id: int, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get AI response for conversation"""
        try:
            # Call OpenRouter API
            response = await openrouter_client.chat_completion(messages)
            
            if response["success"]:
                # Save AI response with correct parameters
                await self._save_message(
                    conversation_id,
                    "assistant",
                    response["response"],
                    response.get("model_used"),
                    response.get("tokens_used"),
                    response.get("response_time")
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

    async def _get_or_create_anonymous_user(self) -> str:
        """Get or create anonymous user for conversations"""
        try:
            # If memory mode already enabled just return a local id
            if self._memory_enabled:
                return "anon-local"

            # First, try to find a working user from existing conversations
            try:
                conv_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.supabase.table("ai_conversations").select("user_id").limit(1).execute()
                    ),
                    timeout=2.0
                )
            except Exception:
                raise Exception("Supabase timeout")

            if conv_result.data:
                working_user_id = conv_result.data[0]["user_id"]
                logger.info("Using working user ID from existing conversations", user_id=working_user_id)
                return working_user_id

            # Check if anonymous user exists
            result = self.supabase.table("users").select("id").eq("email", "anonymous@ytili.local").execute()

            if result.data:
                user_id = result.data[0]["id"]
                # Test if this user can be used for conversations
                try:
                    test_data = {
                        "user_id": user_id,
                        "session_id": "test-" + str(uuid.uuid4()),
                        "conversation_type": "general_support",
                        "status": "active",
                        "context_data": {},
                        "conversation_metadata": {},
                        "total_messages": 0
                    }
                    test_result = self.supabase.table("ai_conversations").insert(test_data).execute()
                    if test_result.data:
                        # Clean up test conversation
                        self.supabase.table("ai_conversations").delete().eq("id", test_result.data[0]["id"]).execute()
                        return user_id
                except Exception as test_error:
                    logger.warning(f"Anonymous user exists but cannot be used: {test_error}")

            # Try to find any working user
            try:
                result = self.supabase.table("users").select("id").limit(5).execute()
                for user in result.data:
                    try:
                        test_data = {
                            "user_id": user["id"],
                            "session_id": "test-" + str(uuid.uuid4()),
                            "conversation_type": "general_support",
                            "status": "active",
                            "context_data": {},
                            "conversation_metadata": {},
                            "total_messages": 0
                        }
                        test_result = self.supabase.table("ai_conversations").insert(test_data).execute()
                        if test_result.data:
                            # Clean up test conversation
                            self.supabase.table("ai_conversations").delete().eq("id", test_result.data[0]["id"]).execute()
                            logger.info("Found working user for conversations", user_id=user["id"])
                            return user["id"]
                    except:
                        continue
            except:
                pass

            # Last resort: raise error
            raise Exception("Cannot find any working user for conversation")

        except Exception as e:
            logger.error(f"Failed to get/create anonymous user: {str(e)}")
            # Enable memory mode and return local anonymous id
            self._memory_enabled = True
            anon_id = "anon-" + str(uuid.uuid4())
            self._memory_conversations.setdefault(anon_id, {})  # placeholder
            return anon_id

    async def _check_user_exists(self, user_id: str) -> bool:
        """Check if user exists in database"""
        try:
            if self._memory_enabled:
                return False
            result = self.supabase.table("users").select("id").eq("id", user_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to check user existence: {str(e)}")
            self._memory_enabled = True
            return False

    async def _get_conversation_type(self, session_id: str) -> Optional[ConversationType]:
        """Get conversation type for a session"""
        try:
            if self._memory_enabled:
                convo = self._memory_conversations.get(session_id)
                if convo:
                    return ConversationType(convo["conversation_type"])
                return None

            result = self.supabase.table("ai_conversations").select("conversation_type").eq("session_id", session_id).execute()
            
            if result.data:
                return ConversationType(result.data[0]["conversation_type"])
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation type: {str(e)}")
            self._memory_enabled = True
            convo = self._memory_conversations.get(session_id)
            if convo:
                return ConversationType(convo["conversation_type"])
            return None


# Global AI agent instance
ytili_ai_agent = YtiliAIAgent()
