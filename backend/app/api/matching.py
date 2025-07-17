"""
Donation matching API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.database import get_db
from ..api.deps import get_current_verified_user, get_current_hospital_user
from ..models.user import User
from ..models.donation import Donation, DonationStatus
from ..services.donation_service import DonationService
from ..services.matching_service import MatchingService

router = APIRouter()


class MatchResponse(BaseModel):
    """Schema for donation match response"""
    hospital_id: int
    hospital_name: str
    score: float
    reasons: List[str]
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True


class MatchRequest(BaseModel):
    """Schema for requesting matches"""
    donation_id: int
    max_distance_km: Optional[float] = 50.0


@router.post("/find", response_model=List[MatchResponse])
async def find_matches(
    match_request: MatchRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Find potential matches for a donation"""
    donation_service = DonationService(db)
    matching_service = MatchingService(db)
    
    # Get the donation
    donation = await donation_service.get_donation_by_id(match_request.donation_id)
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    # Check if user has permission to find matches
    if donation.donor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the donor can find matches for this donation"
        )
    
    # Check if donation is in a valid state for matching
    if donation.status != DonationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only verified donations can be matched"
        )
    
    # Find matches
    matches = await matching_service.find_matching_recipients(
        donation, match_request.max_distance_km
    )
    
    # Format response
    response = []
    for match in matches:
        hospital = match["hospital"]
        response.append(
            MatchResponse(
                hospital_id=hospital.id,
                hospital_name=hospital.organization_name or hospital.full_name,
                score=match["score"],
                reasons=match["reasons"],
                distance_km=0.0  # Placeholder - would calculate actual distance
            )
        )
    
    return response


@router.post("/{donation_id}/accept")
async def accept_match(
    donation_id: str
):
    """Accept a donation match (hospital only)"""
    donation_service = DonationService(db)
    
    # Get the donation
    donation = await donation_service.get_donation_by_id(donation_id)
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    # Check if donation is in a valid state for matching
    if donation.status != DonationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only verified donations can be matched"
        )
    
    # Update donation with recipient and status
    donation.recipient_id = current_user.id
    await donation_service.update_donation_status(
        donation_id=donation_id,
        status=DonationStatus.MATCHED,
        actor_id=current_user.id,
        actor_type="hospital",
        description=f"Donation matched with {current_user.organization_name or current_user.full_name}"
    )
    
    return {
        "message": "Donation match accepted successfully",
        "donation_id": donation_id,
        "hospital_id": current_user.id,
        "hospital_name": current_user.organization_name or current_user.full_name
    }


@router.get("/available", response_model=List[dict])
async def get_available_donations(
    current_user: User = Depends(get_current_hospital_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available donations for hospital to match with"""
    from sqlalchemy import select
    
    # Get verified donations without a recipient
    result = await db.execute(
        select(Donation)
        .where(
            Donation.status == DonationStatus.VERIFIED,
            Donation.recipient_id.is_(None)
        )
        .order_by(Donation.created_at.desc())
    )
    
    donations = result.scalars().all()
    
    # Format response
    response = []
    for donation in donations:
        # Get donor info
        donor_result = await db.execute(
            select(User).where(User.id == donation.donor_id)
        )
        donor = donor_result.scalar_one_or_none()
        
        response.append({
            "id": donation.id,
            "title": donation.title,
            "donation_type": donation.donation_type.value,
            "description": donation.description,
            "item_name": donation.item_name,
            "quantity": donation.quantity,
            "unit": donation.unit,
            "created_at": donation.created_at,
            "donor": {
                "id": donor.id,
                "name": donor.full_name,
                "city": donor.city,
                "province": donor.province
            } if donor else None
        })
    
    return response
