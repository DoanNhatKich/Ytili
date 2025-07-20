"""
Donation API endpoints
"""
import hashlib
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from ..core.database import get_db
from ..api.deps import get_current_verified_user, get_current_hospital_user
from ..api.supabase_deps import get_current_user_supabase, get_current_verified_user_supabase
from ..models.user import User
from ..models.donation import DonationType, DonationStatus, PaymentStatus
from ..services.donation_service import DonationService
from ..core.supabase import get_supabase_service, Tables
from ..core.blockchain import blockchain_service

router = APIRouter()


def calculate_metadata_hash(donation_data: dict) -> str:
    """Calculate hash of donation metadata for blockchain integrity"""
    # Create a consistent string representation of the donation data
    metadata = {
        "title": donation_data.get("title", ""),
        "description": donation_data.get("description", ""),
        "donation_type": donation_data.get("donation_type", ""),
        "item_name": donation_data.get("item_name", ""),
        "quantity": donation_data.get("quantity", 0),
        "unit": donation_data.get("unit", ""),
        "amount": donation_data.get("amount", 0),
        "currency": donation_data.get("currency", "VND")
    }

    # Create deterministic JSON string
    metadata_str = json.dumps(metadata, sort_keys=True, separators=(',', ':'))

    # Calculate SHA-256 hash
    return hashlib.sha256(metadata_str.encode()).hexdigest()


class DonationCreate(BaseModel):
    """Schema for creating a donation"""
    donation_type: str  # Accept string instead of enum
    title: str
    description: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None  # Accept string for date
    batch_number: Optional[str] = None
    manufacturer: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "VND"
    pickup_address: Optional[str] = None


class DonationResponse(BaseModel):
    """Schema for donation response"""
    id: int
    donor_id: int
    recipient_id: Optional[int]
    donation_type: DonationType
    title: str
    description: Optional[str]
    status: DonationStatus
    payment_status: PaymentStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class DonationUpdate(BaseModel):
    """Schema for updating donation"""
    recipient_id: Optional[int] = None
    delivery_address: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


@router.post("/")
async def create_donation(
    donation_data: DonationCreate,
    current_user: dict = Depends(get_current_verified_user_supabase)
):
    """Create a new donation - Blockchain-first approach"""

    try:
        supabase = get_supabase_service()

        # Prepare donation data for Supabase
        donation_dict = donation_data.dict(exclude_unset=True)
        donation_dict['donor_id'] = current_user['id']
        donation_dict['status'] = 'pending'

        # Validate donation_type
        valid_types = ['medication', 'medical_supply', 'food', 'cash']
        if donation_dict['donation_type'] not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid donation type. Must be one of: {valid_types}"
            )

        # Handle expiry_date if provided
        if donation_dict.get('expiry_date'):
            try:
                from datetime import datetime
                # If it's already a string in ISO format, keep it
                if isinstance(donation_dict['expiry_date'], str):
                    # Validate the date format
                    datetime.fromisoformat(donation_dict['expiry_date'])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid expiry_date format. Use YYYY-MM-DD"
                )

        # Generate unique donation ID and metadata hash
        import uuid
        donation_id = str(uuid.uuid4())
        metadata_hash = calculate_metadata_hash(donation_dict)

        # Map donation type to integer for blockchain
        type_mapping = {
            'medication': 1,
            'medical_supply': 2,
            'food': 3,
            'cash': 4
        }

        # STEP 1: Record on blockchain FIRST
        blockchain_tx = await blockchain_service.record_donation_on_blockchain(
            donation_id=donation_id,
            donor_id=current_user['id'],
            donation_type=type_mapping[donation_dict['donation_type']],
            title=donation_dict['title'],
            description=donation_dict.get('description', ''),
            amount=int((donation_dict.get('amount', 0) or 0) * 100),  # Convert to cents
            item_name=donation_dict.get('item_name', ''),
            quantity=donation_dict.get('quantity', 0) or 0,
            unit=donation_dict.get('unit', ''),
            metadata_hash=metadata_hash
        )

        if not blockchain_tx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record donation on blockchain. Transaction aborted."
            )

        # STEP 2: Add blockchain tracking fields to donation data
        donation_dict['id'] = donation_id
        donation_dict['blockchain_status'] = 'confirmed'
        donation_dict['blockchain_tx_hash'] = blockchain_tx
        donation_dict['metadata_hash'] = metadata_hash
        
        # Import datetime at module level to avoid local variable error
        from datetime import datetime
        
        # Try to add blockchain_recorded_at, but handle schema mismatch gracefully
        try:
            donation_dict['blockchain_recorded_at'] = datetime.utcnow().isoformat()
        except Exception as e:
            print(f"Warning: blockchain_recorded_at field may not exist in schema: {e}")
            # Remove the field if it causes issues
            donation_dict.pop('blockchain_recorded_at', None)

        # STEP 3: Insert into Supabase database with error handling
        try:
            result = supabase.table(Tables.DONATIONS).insert(donation_dict).execute()
        except Exception as db_error:
            # Handle various schema mismatches gracefully
            error_msg = str(db_error)
            print(f"Database insert error: {error_msg}")
            
            # List of potentially missing columns
            problematic_fields = ['blockchain_recorded_at', 'blockchain_status', 'blockchain_tx_hash', 'metadata_hash']
            
            # Try removing problematic fields one by one
            donation_dict_fallback = donation_dict.copy()
            for field in problematic_fields:
                if field in error_msg or 'schema cache' in error_msg:
                    donation_dict_fallback.pop(field, None)
                    print(f"Removed {field} from donation data due to schema mismatch")
            
            # Retry with cleaned data
            try:
                result = supabase.table(Tables.DONATIONS).insert(donation_dict_fallback).execute()
                print("Successfully inserted donation with fallback schema")
            except Exception as fallback_error:
                print(f"Fallback insert also failed: {fallback_error}")
                raise db_error

        if not result.data:
            # If database insert fails, we should ideally revert blockchain transaction
            # For now, we'll log the error and continue
            print(f"Warning: Database insert failed but blockchain transaction {blockchain_tx} succeeded")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create donation in database"
            )

        donation = result.data[0]

        # STEP 4: Record blockchain transaction in tracking table
        try:
            supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).insert({
                "donation_id": donation_id,
                "blockchain_hash": blockchain_tx,
                "status": "confirmed",
                "network_id": "ytili_saga"
            }).execute()
        except Exception as e:
            print(f"Warning: Failed to record blockchain transaction tracking: {e}")

        return {
            "id": donation.get("id"),
            "title": donation.get("title"),
            "description": donation.get("description"),
            "donation_type": donation.get("donation_type"),
            "status": donation.get("status"),
            "created_at": donation.get("created_at"),
            "updated_at": donation.get("updated_at"),
            "donor_id": donation.get("donor_id"),
            "recipient_id": donation.get("recipient_id"),
            "amount": donation.get("amount"),
            "currency": donation.get("currency"),
            "item_name": donation.get("item_name"),
            "quantity": donation.get("quantity"),
            "unit": donation.get("unit"),
            "expiry_date": donation.get("expiry_date"),
            "batch_number": donation.get("batch_number"),
            "manufacturer": donation.get("manufacturer"),
            "pickup_address": donation.get("pickup_address"),
            "urgency_level": donation.get("urgency_level", "normal"),
            "location": donation.get("location", ""),
            "blockchain_tx_hash": donation.get("blockchain_tx_hash"),
            "blockchain_status": donation.get("blockchain_status"),
            "metadata_hash": donation.get("metadata_hash")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create donation: {str(e)}"
        )


@router.get("/live-tracking")
async def get_live_tracking_data(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get live tracking data for user's donations"""

    try:
        supabase = get_supabase_service()
        user_id = current_user.get("id")

        # Get user's donations with detailed tracking info
        donations_response = supabase.table(Tables.DONATIONS).select(
            "*, hospital_name:hospitals(name)"
        ).eq("donor_id", user_id).order("created_at", desc=True).execute()

        donations = []
        for donation in donations_response.data or []:
            # Get donation status history
            status_history = supabase.table(Tables.DONATION_STATUS_HISTORY).select("*").eq(
                "donation_id", donation["id"]
            ).order("created_at", desc=False).execute()

            # Process donation data
            donation_data = {
                "id": donation["id"],
                "medication_name": donation["medication_name"],
                "quantity": donation["quantity"],
                "status": donation["status"],
                "created_at": donation["created_at"],
                "hospital_name": donation.get("hospital_name", {}).get("name") if donation.get("hospital_name") else None,
                "status_history": status_history.data or [],
                "matched_at": None,
                "delivered_at": None,
                "completed_at": None
            }

            # Extract timestamps from status history
            for status_entry in status_history.data or []:
                if status_entry["status"] == "matched":
                    donation_data["matched_at"] = status_entry["created_at"]
                elif status_entry["status"] == "delivered":
                    donation_data["delivered_at"] = status_entry["created_at"]
                elif status_entry["status"] == "completed":
                    donation_data["completed_at"] = status_entry["created_at"]

            donations.append(donation_data)

        return {
            "success": True,
            "donations": donations
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live tracking data: {str(e)}"
        )


@router.get("/stats")
async def get_donation_stats(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
):
    """Get donation statistics for user"""

    try:
        supabase = get_supabase_service()
        user_id = current_user.get("id")

        # Get total donations
        total_donations = supabase.table(Tables.DONATIONS).select(
            "id", count="exact"
        ).eq("donor_id", user_id).execute()

        # Get active donations (pending, matched, delivered)
        active_donations = supabase.table(Tables.DONATIONS).select(
            "id", count="exact"
        ).eq("donor_id", user_id).in_(
            "status", ["pending", "matched", "delivered"]
        ).execute()

        # Get completed donations
        completed_donations = supabase.table(Tables.DONATIONS).select(
            "id", count="exact"
        ).eq("donor_id", user_id).eq("status", "completed").execute()

        # Calculate total impact (simplified - could be more sophisticated)
        total_impact = (completed_donations.count or 0) * 3  # Assume each donation helps 3 people on average

        return {
            "success": True,
            "stats": {
                "total_donations": total_donations.count or 0,
                "active_donations": active_donations.count or 0,
                "completed_donations": completed_donations.count or 0,
                "total_impact": total_impact
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get donation stats: {str(e)}"
        )


@router.get("/")
async def get_my_donations(
    current_user: dict = Depends(get_current_verified_user_supabase)
):
    """Get current user's donations - Supabase version"""

    try:
        supabase = get_supabase_service()
        user_id = current_user['id']

        # Get user's donations from Supabase
        result = supabase.table(Tables.DONATIONS).select("*").eq("donor_id", user_id).order("created_at", desc=True).execute()

        donations = []
        for donation in result.data or []:
            donations.append({
                "id": donation.get("id"),
                "title": donation.get("title", "Medical Donation"),
                "description": donation.get("description", ""),
                "donation_type": donation.get("donation_type", "medical"),
                "status": donation.get("status", "pending"),
                "created_at": donation.get("created_at"),
                "updated_at": donation.get("updated_at"),
                "donor_id": donation.get("donor_id"),
                "recipient_id": donation.get("recipient_id"),
                "amount": donation.get("amount", 0),
                "item_name": donation.get("item_name", ""),
                "quantity": donation.get("quantity", 1),
                "unit": donation.get("unit", ""),
                "expiry_date": donation.get("expiry_date"),
                "batch_number": donation.get("batch_number", ""),
                "manufacturer": donation.get("manufacturer", ""),
                "pickup_address": donation.get("pickup_address", "")
            })

        return donations

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get donations: {str(e)}"
        )


@router.get("/{donation_id}")
async def get_donation(
    donation_id: str
):
    """Get a specific donation - Supabase version"""

    try:
        supabase = get_supabase_service()

        # Get donation from Supabase
        result = supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )

        donation = result.data[0]

        # Return donation data
        return {
            "id": donation.get("id"),
            "title": donation.get("title", "Medical Donation"),
            "description": donation.get("description", ""),
            "donation_type": donation.get("donation_type", "medical"),
            "status": donation.get("status", "pending"),
            "created_at": donation.get("created_at"),
            "updated_at": donation.get("updated_at"),
            "donor_id": donation.get("donor_id"),
            "recipient_id": donation.get("recipient_id"),
            "amount": donation.get("amount", 0),
            "medication_name": donation.get("medication_name", ""),
            "quantity": donation.get("quantity", 1),
            "expiry_date": donation.get("expiry_date"),
            "location": donation.get("location", ""),
            "urgency_level": donation.get("urgency_level", "normal")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get donation: {str(e)}"
        )


@router.put("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: int,
    donation_update: DonationUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a donation"""
    donation_service = DonationService(db)
    
    donation = await donation_service.get_donation_by_id(donation_id)
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    # Check if user has permission to update
    if donation.donor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the donor can update this donation"
        )
    
    # Update donation fields
    update_data = donation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(donation, field, value)
    
    await db.commit()
    await db.refresh(donation)
    
    return donation


@router.post("/{donation_id}/accept")
async def accept_donation(
    donation_id: int,
    current_user: User = Depends(get_current_hospital_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept a donation (hospital only)"""
    donation_service = DonationService(db)
    
    donation = await donation_service.get_donation_by_id(donation_id)
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    if donation.status != DonationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only verified donations can be accepted"
        )
    
    # Update donation with recipient and status
    donation.recipient_id = current_user.id
    await donation_service.update_donation_status(
        donation_id=donation_id,
        status=DonationStatus.MATCHED,
        actor_id=current_user.id,
        actor_type="hospital",
        description=f"Donation accepted by {current_user.organization_name}"
    )
    
    return {"message": "Donation accepted successfully"}


@router.get("/catalog/medications")
async def get_medication_catalog(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get medication catalog"""
    donation_service = DonationService(db)
    
    medications = await donation_service.get_medication_catalog(search)
    return medications
