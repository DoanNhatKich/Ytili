"""
Fundraising Campaign API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from datetime import datetime, timedelta

from ..api.supabase_deps import get_current_user_supabase, get_current_verified_user_supabase
from ..core.supabase import get_supabase_service, Tables

router = APIRouter()


class CampaignCreate(BaseModel):
    """Schema for creating a fundraising campaign"""
    title: str
    description: str
    category: str  # emergency_medical, children_health, surgery_treatment, hospital_equipment
    target_amount: float
    currency: str = "VND"
    end_date: str  # ISO format date
    beneficiary_name: str
    beneficiary_story: str
    medical_documents: Optional[List[str]] = []  # URLs to uploaded documents
    images: Optional[List[str]] = []  # URLs to uploaded images
    urgency_level: str = "normal"  # urgent, high, normal, low


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    title: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    end_date: Optional[str] = None
    beneficiary_story: Optional[str] = None
    images: Optional[List[str]] = None


class DonationToCampaign(BaseModel):
    """Schema for donating to a campaign"""
    amount: float
    currency: str = "VND"
    message: Optional[str] = None
    is_anonymous: bool = False


@router.post("/campaigns")
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: dict = Depends(get_current_verified_user_supabase)
):
    """Create a new fundraising campaign"""
    
    try:
        supabase = get_supabase_service()
        
        # Prepare campaign data
        campaign_dict = campaign_data.dict()
        campaign_dict['creator_id'] = current_user['id']
        campaign_dict['status'] = 'pending'  # pending, active, completed, cancelled
        campaign_dict['current_amount'] = 0.0
        campaign_dict['donor_count'] = 0
        campaign_dict['created_at'] = datetime.utcnow().isoformat()
        
        # Validate end_date
        try:
            end_date = datetime.fromisoformat(campaign_dict['end_date'])
            if end_date <= datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End date must be in the future"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
        
        # Insert into Supabase
        result = supabase.table(Tables.CAMPAIGNS).insert(campaign_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create campaign"
            )
        
        campaign = result.data[0]
        
        return {
            "id": campaign.get("id"),
            "title": campaign.get("title"),
            "description": campaign.get("description"),
            "category": campaign.get("category"),
            "target_amount": campaign.get("target_amount"),
            "current_amount": campaign.get("current_amount", 0),
            "status": campaign.get("status"),
            "created_at": campaign.get("created_at"),
            "end_date": campaign.get("end_date"),
            "creator_id": campaign.get("creator_id"),
            "urgency_level": campaign.get("urgency_level", "normal")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}"
        )


@router.get("/campaigns")
async def get_campaigns(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get fundraising campaigns with optional filtering"""
    
    try:
        supabase = get_supabase_service()
        
        # Build query
        query = supabase.table(Tables.CAMPAIGNS).select("*")
        
        if status:
            query = query.eq("status", status)
        
        if category:
            query = query.eq("category", category)
        
        # Order by urgency and creation date
        query = query.order("urgency_level", desc=True).order("created_at", desc=True)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        campaigns = []
        for campaign in result.data:
            # Calculate progress percentage
            progress = 0
            if campaign.get("target_amount", 0) > 0:
                progress = min(100, (campaign.get("current_amount", 0) / campaign.get("target_amount")) * 100)
            
            # Calculate days left
            days_left = 0
            if campaign.get("end_date"):
                try:
                    end_date = datetime.fromisoformat(campaign["end_date"])
                    days_left = max(0, (end_date - datetime.utcnow()).days)
                except:
                    pass
            
            campaigns.append({
                "id": campaign.get("id"),
                "title": campaign.get("title"),
                "description": campaign.get("description"),
                "category": campaign.get("category"),
                "target_amount": campaign.get("target_amount"),
                "current_amount": campaign.get("current_amount", 0),
                "progress_percentage": round(progress, 1),
                "donor_count": campaign.get("donor_count", 0),
                "days_left": days_left,
                "status": campaign.get("status"),
                "urgency_level": campaign.get("urgency_level", "normal"),
                "created_at": campaign.get("created_at"),
                "images": campaign.get("images", []),
                "beneficiary_name": campaign.get("beneficiary_name", "")
            })
        
        return campaigns
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaigns: {str(e)}"
        )


@router.get("/campaigns/categories")
async def get_campaign_categories():
    """Get available campaign categories"""

    return {
        "categories": [
            {
                "id": "emergency_medical",
                "name": "Emergency Medical",
                "description": "Urgent medical treatments and surgeries",
                "icon": "fas fa-ambulance"
            },
            {
                "id": "children_health",
                "name": "Children's Health",
                "description": "Medical care for children and infants",
                "icon": "fas fa-child"
            },
            {
                "id": "surgery_treatment",
                "name": "Surgery & Treatment",
                "description": "Surgical procedures and specialized treatments",
                "icon": "fas fa-user-md"
            },
            {
                "id": "hospital_equipment",
                "name": "Hospital Equipment",
                "description": "Medical equipment and facility improvements",
                "icon": "fas fa-hospital"
            }
        ]
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get a specific campaign by ID"""

    try:
        supabase = get_supabase_service()

        # Get campaign
        result = supabase.table(Tables.CAMPAIGNS).select("*").eq("id", campaign_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        campaign = result.data[0]

        # Get recent donations to this campaign
        donations_result = supabase.table(Tables.CAMPAIGN_DONATIONS).select(
            "*, donor:users(full_name)"
        ).eq("campaign_id", campaign_id).order("created_at", desc=True).limit(10).execute()

        # Calculate progress
        progress = 0
        if campaign.get("target_amount", 0) > 0:
            progress = min(100, (campaign.get("current_amount", 0) / campaign.get("target_amount")) * 100)

        # Calculate days left
        days_left = 0
        if campaign.get("end_date"):
            try:
                end_date = datetime.fromisoformat(campaign["end_date"])
                days_left = max(0, (end_date - datetime.utcnow()).days)
            except:
                pass

        return {
            "id": campaign.get("id"),
            "title": campaign.get("title"),
            "description": campaign.get("description"),
            "category": campaign.get("category"),
            "target_amount": campaign.get("target_amount"),
            "current_amount": campaign.get("current_amount", 0),
            "progress_percentage": round(progress, 1),
            "donor_count": campaign.get("donor_count", 0),
            "days_left": days_left,
            "status": campaign.get("status"),
            "urgency_level": campaign.get("urgency_level", "normal"),
            "created_at": campaign.get("created_at"),
            "end_date": campaign.get("end_date"),
            "beneficiary_name": campaign.get("beneficiary_name", ""),
            "beneficiary_story": campaign.get("beneficiary_story", ""),
            "images": campaign.get("images", []),
            "medical_documents": campaign.get("medical_documents", []),
            "creator_id": campaign.get("creator_id"),
            "recent_donations": donations_result.data or []
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign: {str(e)}"
        )


@router.post("/campaigns/{campaign_id}/donate")
async def donate_to_campaign(
    campaign_id: str,
    donation_data: DonationToCampaign,
    current_user: dict = Depends(get_current_verified_user_supabase)
):
    """Donate to a specific campaign"""
    
    try:
        supabase = get_supabase_service()
        
        # Get campaign to verify it exists and is active
        campaign_result = supabase.table(Tables.CAMPAIGNS).select("*").eq("id", campaign_id).execute()
        
        if not campaign_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        campaign = campaign_result.data[0]
        
        if campaign.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign is not active"
            )
        
        # Create donation record
        donation_dict = {
            "campaign_id": campaign_id,
            "donor_id": current_user["id"],
            "amount": donation_data.amount,
            "currency": donation_data.currency,
            "message": donation_data.message,
            "is_anonymous": donation_data.is_anonymous,
            "status": "completed",  # For now, assume immediate completion
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert donation
        donation_result = supabase.table(Tables.CAMPAIGN_DONATIONS).insert(donation_dict).execute()
        
        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create donation"
            )
        
        # Update campaign totals
        new_amount = campaign.get("current_amount", 0) + donation_data.amount
        new_donor_count = campaign.get("donor_count", 0) + 1
        
        # Check if campaign is now completed
        new_status = campaign.get("status")
        if new_amount >= campaign.get("target_amount", 0):
            new_status = "completed"
        
        supabase.table(Tables.CAMPAIGNS).update({
            "current_amount": new_amount,
            "donor_count": new_donor_count,
            "status": new_status
        }).eq("id", campaign_id).execute()
        
        return {
            "message": "Donation successful",
            "donation_id": donation_result.data[0]["id"],
            "amount": donation_data.amount,
            "campaign_new_total": new_amount,
            "campaign_status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to donate to campaign: {str(e)}"
        )



