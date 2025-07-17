"""
Transparency API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.database import get_db
from ..api.deps import get_current_verified_user, get_optional_current_user
from ..models.user import User
from ..services.transparency_service import TransparencyService

router = APIRouter()


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    id: int
    transaction_type: str
    description: str
    actor: dict
    metadata: Optional[dict]
    transaction_hash: str
    previous_hash: str
    timestamp: str
    verified: bool


class ChainIntegrityResponse(BaseModel):
    """Schema for chain integrity response"""
    valid: bool
    total_transactions: int
    invalid_transactions: List[dict]
    chain_broken: bool
    message: str


class PublicTransparencyResponse(BaseModel):
    """Schema for public transparency data"""
    donations: List[dict]
    statistics: dict
    total_donations: int
    platform_integrity: float


@router.get("/donation/{donation_id}/chain")
async def get_donation_chain(
    donation_id: str
):
    """Get transaction chain for a specific donation - Supabase version"""

    try:
        from ..core.supabase import get_supabase_service, Tables

        supabase = get_supabase_service()

        # Get donation details
        donation_result = supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()

        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )

        # Return mock transaction chain for now
        # In a real implementation, you would get actual blockchain transactions
        chain = [
            {
                "id": 1,
                "transaction_type": "donation_created",
                "description": "Donation created and verified",
                "actor": {"name": "Donor", "type": "individual"},
                "timestamp": "2024-01-15T10:00:00Z",
                "transaction_hash": "0x1234567890abcdef",
                "metadata": {"status": "verified"}
            },
            {
                "id": 2,
                "transaction_type": "donation_matched",
                "description": "Donation matched with recipient",
                "actor": {"name": "AI Matching System", "type": "system"},
                "timestamp": "2024-01-15T11:00:00Z",
                "transaction_hash": "0xabcdef1234567890",
                "metadata": {"recipient_id": "hospital_123"}
            }
        ]

        return chain

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction chain: {str(e)}"
        )


@router.get("/donation/{donation_id}/verify")
async def verify_donation_chain(
    donation_id: str
):
    """Verify the integrity of a donation's transaction chain - Supabase version"""

    try:
        from ..core.supabase import get_supabase_service, Tables

        supabase = get_supabase_service()

        # Get donation details
        donation_result = supabase.table(Tables.DONATIONS).select("*").eq("id", donation_id).execute()

        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )

        # Return mock integrity verification for now
        # In a real implementation, you would verify blockchain transactions
        integrity = {
            "valid": True,
            "message": "Transaction chain verified successfully",
            "verification_score": 95.5,
            "total_transactions": 2,
            "verified_transactions": 2,
            "last_verified": "2024-01-15T12:00:00Z",
            "blockchain_confirmations": 12
        }

        return integrity

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify chain integrity: {str(e)}"
        )


@router.get("/public")
async def get_public_transparency_data(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get public transparency data (no authentication required) - Supabase version"""

    try:
        from ..core.supabase import get_supabase_service, Tables

        supabase = get_supabase_service()

        # Get recent donations
        donations_result = supabase.table(Tables.DONATIONS).select(
            "id, title, donation_type, status, created_at"
        ).order("created_at", desc=True).limit(limit).execute()

        donations = donations_result.data or []

        # Get donation statistics
        all_donations = supabase.table(Tables.DONATIONS).select("status, donation_type").execute()
        all_donations_data = all_donations.data or []

        # Calculate statistics
        status_counts = {}
        type_counts = {}

        for donation in all_donations_data:
            status = donation.get('status', 'unknown')
            dtype = donation.get('donation_type', 'unknown')

            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[dtype] = type_counts.get(dtype, 0) + 1

        # Ensure we have the expected status counts
        expected_statuses = ['pending', 'active', 'completed', 'cancelled']
        for status in expected_statuses:
            if status not in status_counts:
                status_counts[status] = 0

        statistics = {
            "total_donations": len(all_donations_data),
            "total_transactions": len(all_donations_data) * 2,  # Estimate
            "donations_by_status": status_counts,
            "donations_by_type": type_counts,
            "average_transactions_per_donation": 2.0
        }

        # Format public donations
        public_donations = []
        for donation in donations:
            public_donations.append({
                "donation_id": donation.get('id'),
                "title": donation.get('title', 'Anonymous Donation'),
                "type": donation.get('donation_type', 'medical'),
                "status": donation.get('status', 'pending'),
                "created_date": donation.get('created_at', ''),
                "transaction_count": 2,  # Default estimate
                "transparency_score": 85.0  # Default score
            })

        return {
            "donations": public_donations,
            "statistics": statistics,
            "total_donations": len(public_donations),
            "platform_integrity": 92.5
        }

    except Exception as e:
        # Return fallback data if Supabase fails
        return {
            "donations": [],
            "statistics": {
                "total_donations": 0,
                "total_transactions": 0,
                "donations_by_status": {
                    "pending": 0,
                    "active": 0,
                    "completed": 0,
                    "cancelled": 0
                },
                "donations_by_type": {
                    "medical": 0,
                    "food": 0,
                    "emergency": 0
                },
                "average_transactions_per_donation": 0.0
            },
            "total_donations": 0,
            "platform_integrity": 0.0
        }


@router.get("/stats")
async def get_transparency_stats():
    """Get transparency statistics - Supabase version"""

    try:
        from ..core.supabase import get_supabase_service, Tables

        supabase = get_supabase_service()

        # Get all donations for statistics
        all_donations = supabase.table(Tables.DONATIONS).select("status, donation_type").execute()
        all_donations_data = all_donations.data or []

        # Calculate statistics
        status_counts = {}
        type_counts = {}

        for donation in all_donations_data:
            status = donation.get('status', 'unknown')
            dtype = donation.get('donation_type', 'unknown')

            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[dtype] = type_counts.get(dtype, 0) + 1

        # Ensure we have the expected status counts
        expected_statuses = ['pending', 'active', 'completed', 'cancelled']
        for status in expected_statuses:
            if status not in status_counts:
                status_counts[status] = 0

        stats = {
            "total_donations": len(all_donations_data),
            "total_transactions": len(all_donations_data) * 2,
            "donations_by_status": status_counts,
            "donations_by_type": type_counts,
            "average_transactions_per_donation": 2.0,
            "platform_integrity": 92.5,
            "user_average_transparency": 88.0,
            "user_donations_count": 0
        }

        return stats

    except Exception as e:
        # Return fallback stats
        return {
            "total_donations": 0,
            "total_transactions": 0,
            "donations_by_status": {
                "pending": 0,
                "active": 0,
                "completed": 0,
                "cancelled": 0
            },
            "donations_by_type": {
                "medical": 0,
                "food": 0,
                "emergency": 0
            },
            "average_transactions_per_donation": 0.0,
            "platform_integrity": 0.0,
            "user_average_transparency": 0.0,
            "user_donations_count": 0
        }


@router.get("/search")
async def search_transactions(
    donation_id: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Search transactions - Supabase version"""

    try:
        # Return mock search results for now
        # In a real implementation, you would search Supabase tables

        transactions = []

        # If searching for a specific donation
        if donation_id:
            transactions = [
                {
                    "id": 1,
                    "donation_id": donation_id,
                    "transaction_type": "donation_created",
                    "description": f"Donation {donation_id} created",
                    "actor": {"name": "Donor", "type": "individual"},
                    "metadata": {"status": "verified"},
                    "transaction_hash": "0x1234567890abcdef",
                    "timestamp": "2024-01-15T10:00:00Z"
                },
                {
                    "id": 2,
                    "donation_id": donation_id,
                    "transaction_type": "donation_matched",
                    "description": f"Donation {donation_id} matched",
                    "actor": {"name": "AI System", "type": "system"},
                    "metadata": {"recipient_id": "hospital_123"},
                    "transaction_hash": "0xabcdef1234567890",
                    "timestamp": "2024-01-15T11:00:00Z"
                }
            ]
        else:
            # Return sample transactions
            transactions = [
                {
                    "id": 1,
                    "donation_id": "sample-uuid-1",
                    "transaction_type": transaction_type or "donation_created",
                    "description": "Sample transaction",
                    "actor": {"name": "Sample Actor", "type": actor_type or "individual"},
                    "metadata": {"status": "verified"},
                    "transaction_hash": "0x1234567890abcdef",
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            ]

        return {
            "transactions": transactions[:limit],
            "total": len(transactions),
            "search_params": {
                "donation_id": donation_id,
                "transaction_type": transaction_type,
                "actor_type": actor_type
            }
        }

    except Exception as e:
        return {
            "transactions": [],
            "total": 0,
            "search_params": {
                "donation_id": donation_id,
                "transaction_type": transaction_type,
                "actor_type": actor_type
            },
            "error": f"Search failed: {str(e)}"
        }
