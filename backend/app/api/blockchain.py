"""
Blockchain API endpoints for Ytili platform
Handles blockchain transparency and verification
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from ..core.blockchain import blockchain_service
from ..core.supabase import get_supabase_service, Tables
from ..api.supabase_deps import get_current_user_supabase, get_current_admin_user_supabase

router = APIRouter()


class BlockchainRecordRequest(BaseModel):
    """Blockchain record request schema"""
    donation_id: str
    donation_type: int
    title: str
    description: str
    amount: int
    item_name: str
    quantity: int
    unit: str
    metadata_hash: str


@router.get("/transparency/{donation_id}")
async def get_donation_transparency(
    donation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Get transparency data for a donation"""
    
    try:
        # Verify user has access to this donation
        supabase = get_supabase_service()
        donation_result = supabase.table(Tables.DONATIONS).select("*").eq(
            "id", donation_id
        ).execute()
        
        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found"
            )
        
        donation = donation_result.data[0]
        
        # Check if user has access (donor, recipient, or admin)
        user_has_access = (
            donation["donor_id"] == current_user["id"] or
            donation.get("recipient_id") == current_user["id"] or
            current_user.get("user_type") == "government"
        )
        
        if not user_has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get transparency score from blockchain
        transparency_score = await blockchain_service.get_transparency_score(donation_id)
        
        # Verify donation chain
        verification_result = await blockchain_service.verify_donation_chain(donation_id)
        
        # Get blockchain transaction hash
        blockchain_tx = supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).select("*").eq(
            "donation_id", donation_id
        ).order("created_at", desc=True).limit(1).execute()
        
        blockchain_hash = None
        if blockchain_tx.data:
            blockchain_hash = blockchain_tx.data[0]["blockchain_hash"]
        
        return {
            "donationId": donation_id,
            "transparencyScore": transparency_score or 0,
            "isVerified": verification_result["is_valid"] if verification_result else False,
            "totalTransactions": verification_result["total_transactions"] if verification_result else 0,
            "brokenLinks": verification_result["broken_links"] if verification_result else 0,
            "invalidHashes": verification_result["invalid_hashes"] if verification_result else 0,
            "verifiedAt": verification_result["verified_at"] if verification_result else None,
            "blockchainHash": blockchain_hash
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transparency data: {str(e)}"
        )


@router.post("/record-donation")
async def record_donation_blockchain(
    record_request: BlockchainRecordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Record a donation on blockchain"""
    
    try:
        # Verify donation exists and user has access
        supabase = get_supabase_service()
        donation_result = supabase.table(Tables.DONATIONS).select("*").eq(
            "id", record_request.donation_id
        ).eq("donor_id", current_user["id"]).execute()
        
        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found or access denied"
            )
        
        # Record on blockchain
        blockchain_tx = await blockchain_service.record_donation_on_blockchain(
            donation_id=record_request.donation_id,
            donor_id=current_user["id"],
            donation_type=record_request.donation_type,
            title=record_request.title,
            description=record_request.description,
            amount=record_request.amount,
            item_name=record_request.item_name,
            quantity=record_request.quantity,
            unit=record_request.unit,
            metadata_hash=record_request.metadata_hash
        )
        
        if not blockchain_tx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record donation on blockchain"
            )
        
        # Store blockchain transaction hash
        supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).insert({
            "donation_id": record_request.donation_id,
            "blockchain_hash": blockchain_tx,
            "status": "confirmed",
            "network_id": "ytili_saga"
        }).execute()
        
        return {
            "success": True,
            "message": "Donation recorded on blockchain successfully",
            "blockchain_hash": blockchain_tx
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record donation on blockchain: {str(e)}"
        )


@router.post("/verify-chain/{donation_id}")
async def verify_donation_chain(
    donation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user_supabase)
) -> Dict[str, Any]:
    """Verify donation transaction chain (admin only)"""
    
    try:
        # Verify donation chain
        verification_result = await blockchain_service.verify_donation_chain(donation_id)
        
        if not verification_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify donation chain"
            )
        
        return {
            "success": True,
            "message": "Donation chain verified successfully",
            "data": verification_result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chain verification failed: {str(e)}"
        )


@router.get("/contracts/info")
async def get_contract_info() -> Dict[str, Any]:
    """Get smart contract information"""
    
    return {
        "contracts": {
            "donation_registry": {
                "address": "0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487",
                "name": "DonationRegistry",
                "description": "Records and tracks all donations"
            },
            "transparency_verifier": {
                "address": "0x4c25ECb2cB57A1188218499c0C20EDFB426385a0",
                "name": "TransparencyVerifier",
                "description": "Verifies transaction chain integrity"
            },
            "ytili_token": {
                "address": "0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7",
                "name": "YtiliToken",
                "description": "Platform reward and governance token"
            }
        },
        "network": {
            "name": "Saga Blockchain",
            "chain_id": "2752546100676000",
            "rpc_url": "https://ytili-2752546100676000-1.jsonrpc.sagarpc.io",
            "explorer_url": "https://explorer.saga.io"
        }
    }


@router.get("/stats")
async def get_blockchain_stats() -> Dict[str, Any]:
    """Get blockchain statistics"""
    
    try:
        supabase = get_supabase_service()
        
        # Get total blockchain transactions
        blockchain_txs = supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).select(
            "id", count="exact"
        ).execute()
        
        # Get verified donations
        verified_donations = supabase.table(Tables.DONATIONS).select(
            "id", count="exact"
        ).eq("status", "verified").execute()
        
        # Get total donations with blockchain records
        donations_on_chain = supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).select(
            "donation_id", count="exact"
        ).execute()
        
        return {
            "total_blockchain_transactions": blockchain_txs.count or 0,
            "verified_donations": verified_donations.count or 0,
            "donations_on_chain": donations_on_chain.count or 0,
            "transparency_enabled": True,
            "network_status": "active"
        }
        
    except Exception as e:
        return {
            "total_blockchain_transactions": 0,
            "verified_donations": 0,
            "donations_on_chain": 0,
            "transparency_enabled": False,
            "network_status": "error",
            "error": str(e)
        }


@router.get("/user/transactions")
async def get_user_blockchain_transactions(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """Get user's blockchain transactions"""
    
    try:
        supabase = get_supabase_service()
        
        # Get blockchain transactions for user's donations
        transactions = supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).select(
            "*, donations!inner(donor_id, title)"
        ).eq("donations.donor_id", current_user["id"]).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        return {
            "success": True,
            "data": transactions.data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(transactions.data)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blockchain transactions: {str(e)}"
        )
