"""
AI Agent API endpoints for Ytili platform
Provides REST API for AI chat, donation advice, and emergency requests
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import json
import structlog

from ..ai_agent.chatbot import ytili_chatbot
from ..ai_agent.donation_advisor import donation_advisor
from ..ai_agent.emergency_handler import emergency_handler
from ..ai_agent.openrouter_client import openrouter_client
from ..api.supabase_deps import get_current_user_compat, get_current_user_optional
from ..models.user import User

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models for request/response
class ChatStartRequest(BaseModel):
    conversation_type: str = Field(default="general_support", description="Type of conversation")
    initial_message: Optional[str] = Field(None, description="Initial message to start conversation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    message: str = Field(..., description="User message")
    stream: bool = Field(default=False, description="Whether to stream the response")


class EmergencyRequest(BaseModel):
    description: str = Field(..., description="Emergency description")
    location: Optional[str] = Field(None, description="User location")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")


class ConversationFeedback(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    satisfaction_score: Optional[float] = Field(None, ge=1, le=5, description="Satisfaction rating 1-5")
    feedback: Optional[str] = Field(None, description="User feedback text")


class DonationAdviceRequest(BaseModel):
    budget_amount: Optional[float] = Field(None, description="Available budget")
    budget_range: Optional[str] = Field(None, description="Budget range (low/medium/high/premium)")
    medical_interests: Optional[List[str]] = Field(None, description="Medical specialties of interest")
    location_preference: Optional[str] = Field(None, description="Preferred location for donations")


@router.post("/chat/start")
async def start_chat(
    request: ChatStartRequest,
    current_user = Depends(get_current_user_optional)  # Make auth optional
) -> Dict[str, Any]:
    """
    Start a new AI chat session
    """
    try:
        # Use anonymous user if not authenticated
        user_id = current_user.id if current_user else "anonymous"
        
        result = await ytili_chatbot.start_chat(
            user_id=user_id,
            conversation_type=request.conversation_type,
            initial_message=request.initial_message,
            context=request.context
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info(
            "Chat session started",
            user_id=user_id,
            session_id=result["session_id"],
            conversation_type=request.conversation_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to start chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/message")
async def send_message(
    request: ChatMessageRequest,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Send a message in an existing chat session
    
    Args:
        request: Chat message request data
        current_user: Current authenticated user
        
    Returns:
        AI response or stream
    """
    try:
        if request.stream:
            # Return streaming response
            async def generate_stream():
                async for chunk in ytili_chatbot.send_message(
                    session_id=request.session_id,
                    message=request.message,
                    stream=True
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # Return regular response
            result = await ytili_chatbot.send_message(
                session_id=request.session_id,
                message=request.message,
                stream=False
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get chat history for a session
    
    Args:
        session_id: Chat session ID
        limit: Maximum number of messages to return
        current_user: Current authenticated user
        
    Returns:
        Chat history
    """
    try:
        result = await ytili_chatbot.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # Verify user owns this conversation
        if result["conversation"]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/end")
async def end_chat(
    request: ConversationFeedback,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    End a chat session with optional feedback
    
    Args:
        request: Conversation feedback data
        current_user: Current authenticated user
        
    Returns:
        Success status
    """
    try:
        result = await ytili_chatbot.end_conversation(
            session_id=request.session_id,
            user_feedback=request.feedback,
            satisfaction_score=request.satisfaction_score
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to end chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/donation-advice")
async def get_donation_advice(
    request: DonationAdviceRequest,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get personalized donation recommendations
    
    Args:
        request: Donation advice request data
        current_user: Current authenticated user
        
    Returns:
        Donation recommendations
    """
    try:
        # Create a temporary context for donation advice
        context = {
            "budget_amount": request.budget_amount,
            "budget_range": request.budget_range,
            "medical_interests": request.medical_interests or [],
            "location_preference": request.location_preference
        }
        
        # Generate recommendations using donation advisor
        budget_info = {
            "amount": request.budget_amount,
            "range": request.budget_range
        }
        
        user_context = {
            "user_id": current_user.id,
            "location": {"province": request.location_preference}
        }
        
        recommendations = await donation_advisor._recommend_campaigns(
            budget_info, request.medical_interests or [], user_context
        )
        
        # Add amount recommendations
        amount_recs = donation_advisor._recommend_donation_amounts(
            budget_info, user_context
        )
        recommendations.extend(amount_recs)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "user_context": user_context
        }
        
    except Exception as e:
        logger.error(f"Failed to get donation advice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency")
async def create_emergency_request(
    request: EmergencyRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Create an emergency medical request
    
    Args:
        request: Emergency request data
        background_tasks: Background task handler
        current_user: Current authenticated user
        
    Returns:
        Emergency request result
    """
    try:
        # Start emergency conversation
        chat_result = await ytili_chatbot.start_chat(
            user_id=current_user.id,
            conversation_type="emergency_request",
            initial_message=request.description
        )
        
        if not chat_result["success"]:
            raise HTTPException(status_code=400, detail=chat_result["error"])
        
        # Process emergency request
        emergency_result = await emergency_handler.process_emergency_request(
            user_id=current_user.id,
            session_id=chat_result["session_id"],
            initial_message=request.description,
            location=request.location,
            contact_phone=request.contact_phone
        )
        
        if not emergency_result["success"]:
            raise HTTPException(status_code=400, detail=emergency_result["error"])
        
        logger.warning(
            "Emergency request created",
            user_id=current_user.id,
            emergency_id=emergency_result["emergency_id"],
            priority=emergency_result["priority"]
        )
        
        return {
            "success": True,
            "emergency_id": emergency_result["emergency_id"],
            "session_id": chat_result["session_id"],
            "priority": emergency_result["priority"],
            "estimated_response_time": emergency_result["estimated_response_time"],
            "recommended_actions": emergency_result["recommended_actions"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create emergency request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emergency/{emergency_id}/status")
async def get_emergency_status(
    emergency_id: int,
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get status of an emergency request
    
    Args:
        emergency_id: Emergency request ID
        current_user: Current authenticated user
        
    Returns:
        Emergency status
    """
    try:
        result = await emergency_handler.get_emergency_status(emergency_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # Verify user owns this emergency request
        if result["emergency"]["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get emergency status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health_check() -> Dict[str, Any]:
    """
    Health check for AI Agent services
    
    Returns:
        Health status of AI services
    """
    try:
        # Check OpenRouter API health
        openrouter_health = await openrouter_client.health_check()
        
        return {
            "status": "healthy",
            "services": {
                "openrouter": openrouter_health,
                "chatbot": {"status": "healthy"},
                "donation_advisor": {"status": "healthy"},
                "emergency_handler": {"status": "healthy"}
            },
            "timestamp": "now()"
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "now()"
        }


@router.get("/analytics")
async def get_ai_analytics(
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get AI analytics for the current user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User's AI interaction analytics
    """
    try:
        # Get user's conversation history
        conversations = ytili_chatbot.ai_agent.supabase.table("ai_conversations").select("*").eq("user_id", current_user.id).execute()
        
        # Get user's recommendations
        recommendations = ytili_chatbot.ai_agent.supabase.table("ai_recommendations").select("*").eq("user_id", current_user.id).execute()
        
        # Calculate analytics
        total_conversations = len(conversations.data) if conversations.data else 0
        total_recommendations = len(recommendations.data) if recommendations.data else 0
        
        # Count by conversation type
        conversation_types = {}
        if conversations.data:
            for conv in conversations.data:
                conv_type = conv["conversation_type"]
                conversation_types[conv_type] = conversation_types.get(conv_type, 0) + 1
        
        return {
            "success": True,
            "analytics": {
                "total_conversations": total_conversations,
                "total_recommendations": total_recommendations,
                "conversation_types": conversation_types,
                "avg_satisfaction": None  # Would calculate from feedback
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
