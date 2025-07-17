"""
VietQR Payment API endpoints for Ytili platform
Handles Vietnamese QR payment integration and blockchain recording
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ..core.vietqr import vietqr_service
from ..core.blockchain import blockchain_service
from ..core.supabase import get_supabase_service, Tables
from ..api.supabase_deps import get_current_user_supabase

router = APIRouter()


class VietQRPaymentRequest(BaseModel):
    """VietQR payment request schema"""
    donation_id: str = Field(..., description="Donation ID")
    amount: float = Field(..., gt=0, description="Payment amount in VND")
    description: str = Field(..., min_length=1, max_length=500, description="Payment description")
    expires_in_minutes: int = Field(30, ge=5, le=120, description="Payment expiry in minutes")


class PaymentVerification(BaseModel):
    """Payment verification schema"""
    payment_reference: str = Field(..., description="Payment reference ID")
    bank_transaction_id: Optional[str] = Field(None, description="Bank transaction ID")


@router.post("/create-qr")
async def create_vietqr_payment(
    payment_request: VietQRPaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Create a new VietQR payment QR code for donation"""
    
    try:
        # Verify donation exists and belongs to user
        supabase = get_supabase_service()
        donation_result = supabase.table(Tables.DONATIONS).select("*").eq(
            "id", payment_request.donation_id
        ).eq("donor_id", current_user["id"]).execute()
        
        if not donation_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Donation not found or access denied"
            )
        
        # Check if donation already has a pending payment
        existing_payment = supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
            "donation_id", payment_request.donation_id
        ).eq("status", "pending").execute()
        
        if existing_payment.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Donation already has a pending payment"
            )
        
        # Generate payment QR
        payment_data = await vietqr_service.generate_payment_qr(
            donation_id=payment_request.donation_id,
            amount=payment_request.amount,
            description=payment_request.description,
            expires_in_minutes=payment_request.expires_in_minutes
        )
        
        return {
            "success": True,
            "message": "VietQR payment QR code generated successfully",
            "data": payment_data
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VietQR payment: {str(e)}"
        )


@router.post("/verify")
async def verify_vietqr_payment(
    verification: PaymentVerification,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Verify VietQR payment status and update donation"""
    
    try:
        # Verify payment
        payment_result = await vietqr_service.verify_payment(
            payment_reference=verification.payment_reference,
            bank_transaction_id=verification.bank_transaction_id
        )
        
        if payment_result["status"] == "paid":
            # Get payment record to find donation
            supabase = get_supabase_service()
            payment_record = supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
                "payment_reference", verification.payment_reference
            ).execute()
            
            if payment_record.data:
                donation_id = payment_record.data[0]["donation_id"]
                
                # Update donation status to verified
                supabase.table(Tables.DONATIONS).update({
                    "payment_status": "completed",
                    "status": "verified"
                }).eq("id", donation_id).execute()
                
                # Record on blockchain
                try:
                    blockchain_tx = await blockchain_service.update_donation_status_on_blockchain(
                        donation_id=donation_id,
                        new_status=1,  # VERIFIED
                        actor_id=current_user["id"],
                        actor_type="donor",
                        description="VietQR payment verified and donation confirmed"
                    )
                    
                    if blockchain_tx:
                        # Store blockchain transaction hash
                        supabase.table(Tables.BLOCKCHAIN_TRANSACTIONS).insert({
                            "donation_id": donation_id,
                            "blockchain_hash": blockchain_tx,
                            "status": "confirmed",
                            "network_id": "ytili_saga"
                        }).execute()
                        
                except Exception as blockchain_error:
                    print(f"Blockchain recording failed: {blockchain_error}")
                    # Continue even if blockchain fails
                
                # Mint reward tokens for donor
                try:
                    if current_user.get("wallet_address"):
                        reward_tx = await blockchain_service.mint_reward_tokens(
                            user_address=current_user["wallet_address"],
                            user_id=current_user["id"],
                            amount=100 * 10**18,  # 100 YTILI tokens
                            reason="vietqr_payment_verified"
                        )
                        
                        if reward_tx:
                            print(f"Reward tokens minted: {reward_tx}")
                            
                except Exception as reward_error:
                    print(f"Reward minting failed: {reward_error}")
                    # Continue even if reward fails
        
        return {
            "success": True,
            "message": "VietQR payment verification completed",
            "data": payment_result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"VietQR payment verification failed: {str(e)}"
        )


@router.get("/status/{payment_reference}")
async def get_vietqr_payment_status(
    payment_reference: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Get VietQR payment status by reference"""
    
    try:
        # Verify user has access to this payment
        supabase = get_supabase_service()
        payment_record = supabase.table(Tables.VIETQR_PAYMENTS).select(
            "*, donations!inner(donor_id)"
        ).eq("payment_reference", payment_reference).execute()
        
        if not payment_record.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Check if user owns the donation
        if payment_record.data[0]["donations"]["donor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        payment_status = await vietqr_service.get_payment_status(payment_reference)
        
        return {
            "success": True,
            "data": payment_status
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get VietQR payment status: {str(e)}"
        )


@router.post("/cancel/{payment_reference}")
async def cancel_vietqr_payment(
    payment_reference: str,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Cancel a pending VietQR payment"""
    
    try:
        # Verify user has access to this payment
        supabase = get_supabase_service()
        payment_record = supabase.table(Tables.VIETQR_PAYMENTS).select(
            "*, donations!inner(donor_id)"
        ).eq("payment_reference", payment_reference).execute()
        
        if not payment_record.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Check if user owns the donation
        if payment_record.data[0]["donations"]["donor_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        cancel_result = await vietqr_service.cancel_payment(payment_reference)
        
        return {
            "success": True,
            "message": "VietQR payment cancelled successfully",
            "data": cancel_result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"VietQR payment cancellation failed: {str(e)}"
        )


@router.get("/banks")
async def get_supported_banks() -> Dict[str, Any]:
    """Get list of supported Vietnamese banks"""
    
    try:
        banks = await vietqr_service.get_bank_list()
        
        return {
            "success": True,
            "data": banks,
            "message": "Supported Vietnamese banks for VietQR payments"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bank list: {str(e)}"
        )


@router.get("/user/payments")
async def get_user_vietqr_payments(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase),
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """Get user's VietQR payment history"""
    
    try:
        supabase = get_supabase_service()
        
        # Get payments for user's donations
        payments = supabase.table(Tables.VIETQR_PAYMENTS).select(
            "*, donations!inner(donor_id, title)"
        ).eq("donations.donor_id", current_user["id"]).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        return {
            "success": True,
            "data": payments.data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(payments.data)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get VietQR payment history: {str(e)}"
        )
