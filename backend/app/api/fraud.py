"""
Fraud detection API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.database import get_db
from ..api.deps import get_current_admin_user
from ..models.user import User
from ..services.fraud_detection_service import FraudDetectionService

router = APIRouter()


class SuspiciousActivityResponse(BaseModel):
    """Schema for suspicious activity response"""
    type: str
    severity: str
    description: str
    detected_at: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_type: Optional[str] = None
    donation_id: Optional[int] = None
    transaction_id: Optional[int] = None


class FraudRiskResponse(BaseModel):
    """Schema for fraud risk response"""
    user_id: int
    risk_score: float
    risk_level: str
    factors: List[str]


@router.get("/scan", response_model=List[dict])
async def scan_for_suspicious_activity(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Scan for suspicious activity (admin only)"""
    
    fraud_service = FraudDetectionService(db)
    
    suspicious_activities = await fraud_service.scan_for_suspicious_activity()
    
    return suspicious_activities


@router.get("/user/{user_id}/risk", response_model=FraudRiskResponse)
async def get_user_fraud_risk(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get fraud risk score for a user (admin only)"""
    
    fraud_service = FraudDetectionService(db)
    
    risk_assessment = await fraud_service.get_fraud_risk_score(user_id)
    
    return risk_assessment


@router.get("/dashboard")
async def get_fraud_dashboard(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get fraud dashboard data (admin only)"""
    
    fraud_service = FraudDetectionService(db)
    
    # Get suspicious activities
    suspicious_activities = await fraud_service.scan_for_suspicious_activity()
    
    # Count by severity
    severity_counts = {
        "high": 0,
        "medium": 0,
        "low": 0
    }
    
    for activity in suspicious_activities:
        severity = activity.get("severity", "low")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Count by type
    type_counts = {}
    for activity in suspicious_activities:
        activity_type = activity.get("type", "unknown")
        type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
    
    # Get high-risk users
    from sqlalchemy import select, func
    from ..models.user import User
    
    high_risk_users = []
    
    # Get users with suspicious activities
    user_ids = set()
    for activity in suspicious_activities:
        if "user_id" in activity:
            user_ids.add(activity["user_id"])
    
    # Get risk scores for these users
    for user_id in user_ids:
        risk_assessment = await fraud_service.get_fraud_risk_score(user_id)
        if risk_assessment["risk_level"] == "high":
            # Get user details
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                high_risk_users.append({
                    "user_id": user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "user_type": user.user_type.value,
                    "risk_score": risk_assessment["risk_score"],
                    "risk_factors": risk_assessment["factors"]
                })
    
    return {
        "total_suspicious_activities": len(suspicious_activities),
        "severity_counts": severity_counts,
        "type_counts": type_counts,
        "high_risk_users": high_risk_users,
        "recent_activities": suspicious_activities[:10]  # Return 10 most recent
    }
