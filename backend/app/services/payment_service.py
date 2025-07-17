"""
Payment processing service - VietQR focused
No Stripe dependencies
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.donation import Donation, PaymentStatus
from ..services.donation_service import DonationService


class PaymentService:
    """Service for payment processing - VietQR focused"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.donation_service = DonationService(db)
    
    async def create_vietqr_payment(
        self,
        donation_id: int,
        amount: float,
        description: str
    ) -> Dict[str, Any]:
        """Create a VietQR payment"""
        
        try:
            # Get donation details
            donation = await self.donation_service.get_donation_by_id(donation_id)
            if not donation:
                raise ValueError("Donation not found")
            
            # This would integrate with VietQR API
            # For now, return a mock response
            payment_reference = f"YTILI_{donation_id}_{hash(str(donation_id))}"
            
            return {
                "payment_reference": payment_reference,
                "qr_code": "mock_qr_code_data",
                "amount": amount,
                "description": description,
                "status": "pending",
                "donation_id": donation_id
            }
            
        except Exception as e:
            raise Exception(f"VietQR payment creation failed: {str(e)}")
    
    async def verify_payment(
        self,
        payment_reference: str,
        donation_id: int
    ) -> bool:
        """Verify payment and update donation status"""
        
        try:
            # This would verify with VietQR API or bank
            # For now, simulate successful verification
            
            # Update donation payment status
            await self.donation_service.update_payment_status(
                donation_id=donation_id,
                payment_status=PaymentStatus.COMPLETED,
                actor_id=1,  # System actor
                actor_type="system",
                description="VietQR payment verified",
                metadata={
                    "payment_reference": payment_reference,
                    "verification_method": "vietqr"
                }
            )
            return True
            
        except Exception as e:
            raise Exception(f"Payment verification failed: {str(e)}")
    
    async def get_payment_status(self, payment_reference: str) -> Dict[str, Any]:
        """Get payment status from VietQR system"""
        
        try:
            # This would check with VietQR API
            # For now, return mock status
            return {
                "payment_reference": payment_reference,
                "status": "completed",
                "verified_at": "2024-01-15T10:00:00Z"
            }
            
        except Exception as e:
            raise Exception(f"Payment status check failed: {str(e)}")
    
    async def cancel_payment(self, payment_reference: str) -> bool:
        """Cancel a pending payment"""
        
        try:
            # This would cancel with VietQR API
            # For now, simulate successful cancellation
            return True
            
        except Exception as e:
            raise Exception(f"Payment cancellation failed: {str(e)}")
    
    async def get_supported_banks(self) -> list:
        """Get list of supported banks for VietQR"""
        
        # Mock bank list - would come from VietQR API
        return [
            {
                "id": "970415",
                "name": "Vietinbank",
                "code": "VTB",
                "logo": "https://api.vietqr.io/img/VTB.png"
            },
            {
                "id": "970422", 
                "name": "MB Bank",
                "code": "MB",
                "logo": "https://api.vietqr.io/img/MB.png"
            }
        ]
