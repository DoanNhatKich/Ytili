"""
AI Agent models for Ytili platform
Handles AI conversations, recommendations, emergency requests, and analytics
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Numeric, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class ConversationType(PyEnum):
    """Types of AI conversations"""
    DONATION_ADVISORY = "donation_advisory"
    MEDICAL_INFO = "medical_info"
    CAMPAIGN_HELP = "campaign_help"
    EMERGENCY_REQUEST = "emergency_request"
    GENERAL_SUPPORT = "general_support"


class ConversationStatus(PyEnum):
    """Status of AI conversations"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ARCHIVED = "archived"


class RecommendationType(PyEnum):
    """Types of AI recommendations"""
    DONATION_MATCH = "donation_match"
    CAMPAIGN_SUGGESTION = "campaign_suggestion"
    HOSPITAL_PRIORITY = "hospital_priority"
    EMERGENCY_ROUTING = "emergency_routing"
    FRAUD_ALERT = "fraud_alert"


class EmergencyPriority(PyEnum):
    """Emergency request priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIConversation(Base):
    """AI conversation sessions with users"""
    __tablename__ = "ai_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User and session info
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Conversation details
    conversation_type = Column(Enum(ConversationType), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    title = Column(String(255))  # Auto-generated conversation title
    
    # Context and metadata
    context_data = Column(JSON)  # User context, preferences, history
    conversation_metadata = Column(JSON)  # AI model info, settings, etc.
    
    # Performance metrics
    total_messages = Column(Integer, default=0)
    avg_response_time = Column(Float)  # Average AI response time in seconds
    user_satisfaction_score = Column(Float)  # 1-5 rating if provided
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")
    recommendations = relationship("AIRecommendation", back_populates="conversation")
    
    def __repr__(self):
        return f"<AIConversation {self.session_id} - {self.conversation_type.value}>"


class AIMessage(Base):
    """Individual messages in AI conversations"""
    __tablename__ = "ai_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False)
    
    # Message details
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # AI model information
    model_used = Column(String(100))  # qwen/qwen-2.5-72b-instruct
    tokens_used = Column(Integer)
    response_time = Column(Float)  # Response time in seconds
    
    # Message metadata
    message_metadata = Column(JSON)  # Additional data like attachments, actions
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")
    
    def __repr__(self):
        return f"<AIMessage {self.role} in conversation {self.conversation_id}>"


class AIRecommendation(Base):
    """AI-generated recommendations and suggestions"""
    __tablename__ = "ai_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Associated entities
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"))
    
    # Recommendation details
    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Recommendation data
    recommendation_data = Column(JSON)  # Structured recommendation details
    confidence_score = Column(Float)  # AI confidence in recommendation (0-1)
    
    # User interaction
    is_viewed = Column(Boolean, default=False)
    is_accepted = Column(Boolean, default=False)
    user_feedback = Column(Text)  # User feedback on recommendation
    
    # Effectiveness tracking
    was_successful = Column(Boolean)  # Whether recommendation led to desired outcome
    success_metrics = Column(JSON)  # Metrics for measuring success
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    viewed_at = Column(DateTime(timezone=True))
    acted_upon_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User")
    conversation = relationship("AIConversation", back_populates="recommendations")
    
    def __repr__(self):
        return f"<AIRecommendation {self.recommendation_type.value} for User {self.user_id}>"


class EmergencyRequest(Base):
    """Emergency medical requests processed by AI"""
    __tablename__ = "emergency_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Requester information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"))
    
    # Emergency details
    priority = Column(Enum(EmergencyPriority), nullable=False)
    medical_condition = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Location and logistics
    location = Column(Text)  # Address or coordinates
    contact_phone = Column(String(20))
    
    # AI analysis
    ai_assessment = Column(JSON)  # AI's analysis of the emergency
    recommended_actions = Column(JSON)  # AI-suggested response actions
    
    # Response tracking
    is_responded = Column(Boolean, default=False)
    response_time_minutes = Column(Integer)  # Time to first response
    assigned_hospital_id = Column(Integer, ForeignKey("users.id"))  # Hospital assigned
    
    # Status and resolution
    status = Column(String(50), default="pending")  # pending, assigned, in_progress, resolved
    resolution_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    conversation = relationship("AIConversation")
    assigned_hospital = relationship("User", foreign_keys=[assigned_hospital_id])
    
    def __repr__(self):
        return f"<EmergencyRequest {self.priority.value} - {self.medical_condition}>"


class AIAnalytics(Base):
    """Analytics and metrics for AI Agent performance"""
    __tablename__ = "ai_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time period
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # hourly, daily, weekly, monthly
    
    # Conversation metrics
    total_conversations = Column(Integer, default=0)
    avg_conversation_length = Column(Float)  # Average messages per conversation
    avg_response_time = Column(Float)  # Average AI response time
    
    # User satisfaction
    avg_satisfaction_score = Column(Float)
    total_feedback_count = Column(Integer, default=0)
    
    # Recommendation metrics
    total_recommendations = Column(Integer, default=0)
    recommendation_acceptance_rate = Column(Float)
    recommendation_success_rate = Column(Float)
    
    # Emergency response metrics
    total_emergency_requests = Column(Integer, default=0)
    avg_emergency_response_time = Column(Float)  # In minutes
    emergency_resolution_rate = Column(Float)
    
    # Model performance
    total_tokens_used = Column(Integer, default=0)
    total_api_calls = Column(Integer, default=0)
    api_error_rate = Column(Float)
    
    # Cost tracking
    estimated_cost = Column(Numeric(10, 4))  # Estimated API costs
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AIAnalytics {self.date} - {self.period_type}>"


class MedicalKnowledgeBase(Base):
    """Medical knowledge base for AI Agent"""
    __tablename__ = "medical_knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Medical entity details
    entity_type = Column(String(50), nullable=False)  # condition, treatment, drug, procedure
    name = Column(String(255), nullable=False, index=True)
    vietnamese_name = Column(String(255), index=True)
    
    # Classification
    category = Column(String(100))
    subcategory = Column(String(100))
    specialty = Column(String(100))  # Medical specialty
    
    # Knowledge content
    description = Column(Text)
    symptoms = Column(JSON)  # Array of symptoms
    treatments = Column(JSON)  # Array of treatment options
    medications = Column(JSON)  # Related medications
    
    # Relationships and interactions
    related_conditions = Column(JSON)  # Related medical conditions
    contraindications = Column(JSON)  # What to avoid
    drug_interactions = Column(JSON)  # Drug interaction warnings
    
    # Emergency information
    is_emergency_condition = Column(Boolean, default=False)
    emergency_actions = Column(JSON)  # Emergency response actions
    
    # AI training data
    keywords = Column(JSON)  # Keywords for AI matching
    synonyms = Column(JSON)  # Alternative names/terms
    
    # Metadata
    source = Column(String(255))  # Source of information
    last_verified = Column(DateTime(timezone=True))
    confidence_level = Column(Float)  # Confidence in information accuracy
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<MedicalKnowledgeBase {self.entity_type} - {self.name}>"
