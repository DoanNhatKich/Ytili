"""
Payment processing API endpoints
"""
import stripe
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..core.database import get_db
from ..api.deps import get_current_verified_user
from ..models.user import User
from ..services.payment_service import PaymentService
from ..services.donation_service import DonationService
from ..core.config import settings

router = APIRouter()


class PaymentIntentRequest(BaseModel):
    """Schema for creating payment intent"""
    donation_id: int
    amount: int  # Amount in VND cents (e.g., 100000 = 1000 VND)
    currency: str = "vnd"


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response"""
    client_secret: str
    payment_intent_id: str
    amount: int
    currency: str


class PaymentConfirmRequest(BaseModel):
    """Schema for confirming payment"""
    payment_intent_id: str
    donation_id: int


@router.post("/create-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_request: PaymentIntentRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment intent for donation"""
    
    # Verify donation belongs to current user
    donation_service = DonationService(db)
    donation = await donation_service.get_donation_by_id(payment_request.donation_id)
    
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    if donation.donor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own donations"
        )
    
    # Create payment intent
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.create_payment_intent(
            donation_id=payment_request.donation_id,
            amount=payment_request.amount,
            currency=payment_request.currency,
            metadata={
                "user_id": str(current_user.id),
                "user_email": current_user.email
            }
        )
        
        return PaymentIntentResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/confirm")
async def confirm_payment(
    confirm_request: PaymentConfirmRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Confirm payment completion"""
    
    # Verify donation belongs to current user
    donation_service = DonationService(db)
    donation = await donation_service.get_donation_by_id(confirm_request.donation_id)
    
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )
    
    if donation.donor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only confirm payment for your own donations"
        )
    
    # Confirm payment
    payment_service = PaymentService(db)
    
    success = await payment_service.confirm_payment(
        payment_intent_id=confirm_request.payment_intent_id,
        donation_id=confirm_request.donation_id
    )
    
    if success:
        return {"message": "Payment confirmed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment confirmation failed"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Handle the event
    payment_service = PaymentService(db)
    
    try:
        await payment_service.handle_webhook(event)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/config")
async def get_payment_config():
    """Get payment configuration for frontend"""
    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "currency": "vnd",
        "country": "VN"
    }
