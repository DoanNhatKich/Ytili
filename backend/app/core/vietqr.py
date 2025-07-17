"""
VietQR Payment Integration for Ytili platform
Handles QR code generation and payment verification for Vietnamese banking
"""
import asyncio
import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from .config import settings
from .supabase import get_supabase_service, Tables


class VietQRService:
    """Service for VietQR payment integration"""
    
    def __init__(self):
        self.api_url = settings.VIETQR_API_URL
        self.client_id = settings.VIETQR_CLIENT_ID
        self.api_key = settings.VIETQR_API_KEY
        self.supabase = get_supabase_service()
        
        # Default bank configuration (can be made configurable)
        self.default_bank = {
            "bank_id": "970415",  # Vietinbank
            "account_number": "113366668888",  # Example account
            "account_name": "YTILI PLATFORM"
        }
    
    async def generate_payment_qr(
        self,
        donation_id: str,
        amount: float,
        description: str,
        expires_in_minutes: int = 30
    ) -> Dict[str, Any]:
        """Generate VietQR payment QR code"""
        
        try:
            # Create unique payment reference
            payment_reference = f"YTILI_{donation_id}_{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
            
            # Prepare QR data
            qr_data = {
                "accountNo": self.default_bank["account_number"],
                "accountName": self.default_bank["account_name"],
                "acqId": self.default_bank["bank_id"],
                "amount": int(amount),  # VietQR expects amount in VND
                "addInfo": f"{description} - Ref: {payment_reference}",
                "format": "text",
                "template": "compact"
            }
            
            # Generate QR code via VietQR API
            qr_response = await self._call_vietqr_api("/generate", qr_data)
            
            if not qr_response or "data" not in qr_response:
                raise HTTPException(status_code=500, detail="Failed to generate QR code")
            
            qr_code_data = qr_response["data"]["qrCode"]
            qr_data_url = qr_response["data"]["qrDataURL"]
            
            # Store payment record in Supabase
            payment_record = {
                "donation_id": donation_id,
                "qr_code_id": payment_reference,
                "bank_id": self.default_bank["bank_id"],
                "account_number": self.default_bank["account_number"],
                "account_name": self.default_bank["account_name"],
                "amount": amount,
                "currency": "VND",
                "content": f"{description} - Ref: {payment_reference}",
                "qr_data_url": qr_data_url,
                "qr_code": qr_code_data,
                "status": "pending",
                "payment_reference": payment_reference,
                "expires_at": expires_at.isoformat()
            }
            
            result = self.supabase.table(Tables.VIETQR_PAYMENTS).insert(payment_record).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to store payment record")
            
            return {
                "payment_id": result.data[0]["id"],
                "payment_reference": payment_reference,
                "qr_code": qr_code_data,
                "qr_data_url": qr_data_url,
                "amount": amount,
                "currency": "VND",
                "bank_info": {
                    "bank_id": self.default_bank["bank_id"],
                    "account_number": self.default_bank["account_number"],
                    "account_name": self.default_bank["account_name"]
                },
                "expires_at": expires_at.isoformat(),
                "instructions": {
                    "vi": "Quét mã QR để thanh toán qua ứng dụng ngân hàng của bạn",
                    "en": "Scan QR code to pay via your banking app"
                }
            }
            
        except Exception as e:
            print(f"Error generating VietQR payment: {e}")
            raise HTTPException(status_code=500, detail=f"Payment generation failed: {str(e)}")
    
    async def verify_payment(
        self,
        payment_reference: str,
        bank_transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify payment status"""
        
        try:
            # Get payment record from database
            result = self.supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
                "payment_reference", payment_reference
            ).execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Payment not found")
            
            payment = result.data[0]
            
            # Check if payment is already verified
            if payment["status"] == "paid":
                return {
                    "status": "paid",
                    "payment_reference": payment_reference,
                    "verified_at": payment["paid_at"],
                    "bank_transaction_id": payment["bank_transaction_id"]
                }
            
            # Check if payment has expired
            expires_at = datetime.fromisoformat(payment["expires_at"].replace('Z', '+00:00'))
            if datetime.utcnow() > expires_at.replace(tzinfo=None):
                # Update status to expired
                self.supabase.table(Tables.VIETQR_PAYMENTS).update({
                    "status": "expired"
                }).eq("id", payment["id"]).execute()
                
                return {
                    "status": "expired",
                    "payment_reference": payment_reference,
                    "expired_at": expires_at.isoformat()
                }
            
            # In a real implementation, you would check with the bank's API
            # For now, we'll simulate payment verification
            if bank_transaction_id:
                # Mark as paid
                paid_at = datetime.utcnow()
                self.supabase.table(Tables.VIETQR_PAYMENTS).update({
                    "status": "paid",
                    "bank_transaction_id": bank_transaction_id,
                    "paid_at": paid_at.isoformat()
                }).eq("id", payment["id"]).execute()
                
                return {
                    "status": "paid",
                    "payment_reference": payment_reference,
                    "verified_at": paid_at.isoformat(),
                    "bank_transaction_id": bank_transaction_id
                }
            
            return {
                "status": "pending",
                "payment_reference": payment_reference,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            print(f"Error verifying payment: {e}")
            raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")
    
    async def get_payment_status(self, payment_reference: str) -> Dict[str, Any]:
        """Get payment status by reference"""
        
        try:
            result = self.supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
                "payment_reference", payment_reference
            ).execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Payment not found")
            
            payment = result.data[0]
            
            return {
                "payment_reference": payment_reference,
                "status": payment["status"],
                "amount": payment["amount"],
                "currency": payment["currency"],
                "created_at": payment["created_at"],
                "expires_at": payment["expires_at"],
                "paid_at": payment.get("paid_at"),
                "bank_transaction_id": payment.get("bank_transaction_id")
            }
            
        except Exception as e:
            print(f"Error getting payment status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get payment status: {str(e)}")
    
    async def cancel_payment(self, payment_reference: str) -> Dict[str, Any]:
        """Cancel a pending payment"""
        
        try:
            # Get payment record
            result = self.supabase.table(Tables.VIETQR_PAYMENTS).select("*").eq(
                "payment_reference", payment_reference
            ).execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Payment not found")
            
            payment = result.data[0]
            
            if payment["status"] != "pending":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot cancel payment with status: {payment['status']}"
                )
            
            # Update status to cancelled
            self.supabase.table(Tables.VIETQR_PAYMENTS).update({
                "status": "cancelled"
            }).eq("id", payment["id"]).execute()
            
            return {
                "payment_reference": payment_reference,
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error cancelling payment: {e}")
            raise HTTPException(status_code=500, detail=f"Payment cancellation failed: {str(e)}")
    
    async def get_bank_list(self) -> List[Dict[str, Any]]:
        """Get list of supported banks"""
        
        try:
            response = await self._call_vietqr_api("/banks", {})
            
            if response and "data" in response:
                return response["data"]
            
            # Fallback bank list
            return [
                {
                    "id": "970415",
                    "name": "Vietinbank",
                    "code": "VTB",
                    "bin": "970415",
                    "shortName": "Vietinbank",
                    "logo": "https://api.vietqr.io/img/VTB.png",
                    "transferSupported": 1,
                    "lookupSupported": 1
                },
                {
                    "id": "970422",
                    "name": "MB Bank",
                    "code": "MB",
                    "bin": "970422",
                    "shortName": "MB Bank",
                    "logo": "https://api.vietqr.io/img/MB.png",
                    "transferSupported": 1,
                    "lookupSupported": 1
                }
            ]
            
        except Exception as e:
            print(f"Error getting bank list: {e}")
            return []
    
    async def _call_vietqr_api(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API call to VietQR service"""
        
        try:
            url = f"{self.api_url}{endpoint}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add authentication if configured
            if self.client_id and self.api_key:
                headers["x-client-id"] = self.client_id
                headers["x-api-key"] = self.api_key
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"VietQR API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error calling VietQR API: {e}")
            return None


# Global VietQR service instance
vietqr_service = VietQRService()


# Convenience functions
async def create_donation_payment(
    donation_id: str,
    amount: float,
    description: str
) -> Dict[str, Any]:
    """Create payment QR for donation"""
    return await vietqr_service.generate_payment_qr(donation_id, amount, description)


async def verify_donation_payment(
    payment_reference: str,
    bank_transaction_id: Optional[str] = None
) -> Dict[str, Any]:
    """Verify donation payment"""
    return await vietqr_service.verify_payment(payment_reference, bank_transaction_id)


async def get_donation_payment_status(payment_reference: str) -> Dict[str, Any]:
    """Get donation payment status"""
    return await vietqr_service.get_payment_status(payment_reference)


async def cancel_donation_payment(payment_reference: str) -> Dict[str, Any]:
    """Cancel donation payment"""
    return await vietqr_service.cancel_payment(payment_reference)
