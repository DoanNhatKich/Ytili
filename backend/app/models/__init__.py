# Ytili Database Models Package

# Import all models for SQLAlchemy to recognize them
from .user import User, UserType, UserStatus, KYCDocument, UserPoints
from .donation import (
    Donation, DonationType, DonationStatus, PaymentStatus,
    DonationTransaction, MedicationCatalog
)
from .ai_agent import (
    AIConversation, ConversationType, ConversationStatus,
    AIMessage, AIRecommendation, RecommendationType,
    EmergencyRequest, EmergencyPriority, AIAnalytics,
    MedicalKnowledgeBase
)

__all__ = [
    # User models
    "User", "UserType", "UserStatus", "KYCDocument", "UserPoints",

    # Donation models
    "Donation", "DonationType", "DonationStatus", "PaymentStatus",
    "DonationTransaction", "MedicationCatalog",

    # AI Agent models
    "AIConversation", "ConversationType", "ConversationStatus",
    "AIMessage", "AIRecommendation", "RecommendationType",
    "EmergencyRequest", "EmergencyPriority", "AIAnalytics",
    "MedicalKnowledgeBase"
]
