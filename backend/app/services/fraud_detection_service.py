"""
Fraud detection service for Ytili platform
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta

from ..models.donation import Donation, DonationTransaction, DonationStatus
from ..models.user import User, UserStatus


class FraudDetectionService:
    """Service for detecting potential fraud in donations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def scan_for_suspicious_activity(self) -> List[Dict[str, Any]]:
        """Scan for suspicious activity across the platform"""
        
        suspicious_activities = []
        
        # Check for suspicious users
        suspicious_users = await self._detect_suspicious_users()
        suspicious_activities.extend(suspicious_users)
        
        # Check for suspicious donations
        suspicious_donations = await self._detect_suspicious_donations()
        suspicious_activities.extend(suspicious_donations)
        
        # Check for suspicious transactions
        suspicious_transactions = await self._detect_suspicious_transactions()
        suspicious_activities.extend(suspicious_transactions)
        
        return suspicious_activities
    
    async def _detect_suspicious_users(self) -> List[Dict[str, Any]]:
        """Detect suspicious user activity"""
        
        suspicious_users = []
        
        # 1. Users with high donation creation rate
        high_donation_users = await self._detect_high_donation_rate_users()
        suspicious_users.extend(high_donation_users)
        
        # 2. Users with suspicious verification patterns
        verification_issues = await self._detect_verification_issues()
        suspicious_users.extend(verification_issues)
        
        # 3. Users with multiple failed payments
        payment_issues = await self._detect_payment_issues()
        suspicious_users.extend(payment_issues)
        
        return suspicious_users
    
    async def _detect_high_donation_rate_users(self) -> List[Dict[str, Any]]:
        """Detect users creating donations at an unusually high rate"""
        
        # Define thresholds
        time_window = datetime.now() - timedelta(days=1)
        threshold = 10  # More than 10 donations in 24 hours is suspicious
        
        # Count donations per user in the time window
        result = await self.db.execute(
            select(
                Donation.donor_id,
                func.count(Donation.id).label('donation_count')
            )
            .where(Donation.created_at >= time_window)
            .group_by(Donation.donor_id)
            .having(func.count(Donation.id) > threshold)
        )
        
        high_rate_users = result.all()
        
        # Format results
        suspicious_activities = []
        for user_id, donation_count in high_rate_users:
            # Get user details
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                suspicious_activities.append({
                    "type": "high_donation_rate",
                    "severity": "medium",
                    "user_id": user_id,
                    "user_email": user.email,
                    "user_type": user.user_type.value,
                    "donation_count": donation_count,
                    "time_window": "24 hours",
                    "threshold": threshold,
                    "detected_at": datetime.now(),
                    "description": f"User created {donation_count} donations in 24 hours (threshold: {threshold})"
                })
        
        return suspicious_activities
    
    async def _detect_verification_issues(self) -> List[Dict[str, Any]]:
        """Detect users with suspicious verification patterns"""
        
        # Define thresholds
        failed_verification_threshold = 3  # More than 3 failed verifications is suspicious
        
        # Find users with multiple rejected KYC documents
        from ..models.user import KYCDocument
        
        result = await self.db.execute(
            select(
                KYCDocument.user_id,
                func.count(KYCDocument.id).label('rejected_count')
            )
            .where(
                and_(
                    KYCDocument.is_verified == False,
                    KYCDocument.rejection_reason.isnot(None)
                )
            )
            .group_by(KYCDocument.user_id)
            .having(func.count(KYCDocument.id) >= failed_verification_threshold)
        )
        
        suspicious_users = result.all()
        
        # Format results
        suspicious_activities = []
        for user_id, rejected_count in suspicious_users:
            # Get user details
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                suspicious_activities.append({
                    "type": "verification_issues",
                    "severity": "high",
                    "user_id": user_id,
                    "user_email": user.email,
                    "user_type": user.user_type.value,
                    "rejected_count": rejected_count,
                    "threshold": failed_verification_threshold,
                    "detected_at": datetime.now(),
                    "description": f"User has {rejected_count} rejected KYC documents (threshold: {failed_verification_threshold})"
                })
        
        return suspicious_activities
    
    async def _detect_payment_issues(self) -> List[Dict[str, Any]]:
        """Detect users with multiple failed payments"""
        
        # Define thresholds
        failed_payment_threshold = 3  # More than 3 failed payments is suspicious
        
        # Find donations with failed payments
        from ..models.donation import PaymentStatus
        
        result = await self.db.execute(
            select(
                Donation.donor_id,
                func.count(Donation.id).label('failed_count')
            )
            .where(Donation.payment_status == PaymentStatus.FAILED)
            .group_by(Donation.donor_id)
            .having(func.count(Donation.id) >= failed_payment_threshold)
        )
        
        suspicious_users = result.all()
        
        # Format results
        suspicious_activities = []
        for user_id, failed_count in suspicious_users:
            # Get user details
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                suspicious_activities.append({
                    "type": "payment_issues",
                    "severity": "medium",
                    "user_id": user_id,
                    "user_email": user.email,
                    "user_type": user.user_type.value,
                    "failed_count": failed_count,
                    "threshold": failed_payment_threshold,
                    "detected_at": datetime.now(),
                    "description": f"User has {failed_count} failed payments (threshold: {failed_payment_threshold})"
                })
        
        return suspicious_activities
    
    async def _detect_suspicious_donations(self) -> List[Dict[str, Any]]:
        """Detect suspicious donation patterns"""
        
        suspicious_donations = []
        
        # 1. Donations with unusual amounts
        unusual_amounts = await self._detect_unusual_amounts()
        suspicious_donations.extend(unusual_amounts)
        
        # 2. Donations with near-expiry medications
        near_expiry = await self._detect_near_expiry_donations()
        suspicious_donations.extend(near_expiry)
        
        # 3. Donations with suspicious status changes
        status_issues = await self._detect_status_change_issues()
        suspicious_donations.extend(status_issues)
        
        return suspicious_donations
    
    async def _detect_unusual_amounts(self) -> List[Dict[str, Any]]:
        """Detect donations with unusual amounts"""
        
        # Define thresholds
        high_amount_threshold = 10000000  # 10 million VND
        
        # Find cash donations with unusually high amounts
        result = await self.db.execute(
            select(Donation)
            .where(
                and_(
                    Donation.donation_type == "cash",
                    Donation.amount >= high_amount_threshold
                )
            )
        )
        
        high_amount_donations = result.scalars().all()
        
        # Format results
        suspicious_activities = []
        for donation in high_amount_donations:
            suspicious_activities.append({
                "type": "unusual_amount",
                "severity": "low",
                "donation_id": donation.id,
                "donor_id": donation.donor_id,
                "amount": float(donation.amount),
                "threshold": high_amount_threshold,
                "detected_at": datetime.now(),
                "description": f"Donation amount ({donation.amount} VND) exceeds threshold ({high_amount_threshold} VND)"
            })
        
        return suspicious_activities
    
    async def _detect_near_expiry_donations(self) -> List[Dict[str, Any]]:
        """Detect donations with medications close to expiry"""
        
        # Define thresholds
        expiry_threshold = datetime.now() + timedelta(days=30)  # Less than 30 days to expiry
        
        # Find donations with near-expiry medications
        result = await self.db.execute(
            select(Donation)
            .where(
                and_(
                    Donation.donation_type.in_(["medication", "food"]),
                    Donation.expiry_date.isnot(None),
                    Donation.expiry_date <= expiry_threshold
                )
            )
        )
        
        near_expiry_donations = result.scalars().all()
        
        # Format results
        suspicious_activities = []
        for donation in near_expiry_donations:
            days_to_expiry = (donation.expiry_date - datetime.now()).days
            
            suspicious_activities.append({
                "type": "near_expiry",
                "severity": "medium" if days_to_expiry < 15 else "low",
                "donation_id": donation.id,
                "donor_id": donation.donor_id,
                "expiry_date": donation.expiry_date,
                "days_to_expiry": days_to_expiry,
                "threshold": 30,
                "detected_at": datetime.now(),
                "description": f"Donation expires in {days_to_expiry} days (threshold: 30 days)"
            })
        
        return suspicious_activities
    
    async def _detect_status_change_issues(self) -> List[Dict[str, Any]]:
        """Detect donations with suspicious status changes"""
        
        # Define thresholds
        time_window = datetime.now() - timedelta(hours=24)
        status_change_threshold = 3  # More than 3 status changes in 24 hours is suspicious
        
        # Find donations with frequent status changes
        result = await self.db.execute(
            select(
                DonationTransaction.donation_id,
                func.count(DonationTransaction.id).label('change_count')
            )
            .where(
                and_(
                    DonationTransaction.transaction_type.like("status_changed_to_%"),
                    DonationTransaction.created_at >= time_window
                )
            )
            .group_by(DonationTransaction.donation_id)
            .having(func.count(DonationTransaction.id) >= status_change_threshold)
        )
        
        suspicious_donations = result.all()
        
        # Format results
        suspicious_activities = []
        for donation_id, change_count in suspicious_donations:
            # Get donation details
            donation_result = await self.db.execute(
                select(Donation).where(Donation.id == donation_id)
            )
            donation = donation_result.scalar_one_or_none()
            
            if donation:
                suspicious_activities.append({
                    "type": "frequent_status_changes",
                    "severity": "medium",
                    "donation_id": donation_id,
                    "donor_id": donation.donor_id,
                    "change_count": change_count,
                    "threshold": status_change_threshold,
                    "time_window": "24 hours",
                    "detected_at": datetime.now(),
                    "description": f"Donation status changed {change_count} times in 24 hours (threshold: {status_change_threshold})"
                })
        
        return suspicious_activities
    
    async def _detect_suspicious_transactions(self) -> List[Dict[str, Any]]:
        """Detect suspicious transaction patterns"""
        
        suspicious_transactions = []
        
        # 1. Transactions with hash inconsistencies
        hash_issues = await self._detect_hash_inconsistencies()
        suspicious_transactions.extend(hash_issues)
        
        return suspicious_transactions
    
    async def _detect_hash_inconsistencies(self) -> List[Dict[str, Any]]:
        """Detect transactions with hash inconsistencies"""
        
        # This would normally involve complex chain validation
        # For now, we'll implement a simplified version
        
        # Get all transactions
        result = await self.db.execute(
            select(DonationTransaction)
            .order_by(DonationTransaction.donation_id, DonationTransaction.id)
        )
        
        transactions = result.scalars().all()
        
        # Group by donation
        donation_transactions = {}
        for tx in transactions:
            if tx.donation_id not in donation_transactions:
                donation_transactions[tx.donation_id] = []
            donation_transactions[tx.donation_id].append(tx)
        
        # Check chain integrity for each donation
        suspicious_activities = []
        for donation_id, tx_chain in donation_transactions.items():
            for i in range(1, len(tx_chain)):
                current_tx = tx_chain[i]
                previous_tx = tx_chain[i-1]
                
                # Check if previous hash matches
                if current_tx.previous_hash != previous_tx.transaction_hash:
                    suspicious_activities.append({
                        "type": "hash_inconsistency",
                        "severity": "high",
                        "donation_id": donation_id,
                        "transaction_id": current_tx.id,
                        "previous_transaction_id": previous_tx.id,
                        "expected_hash": previous_tx.transaction_hash,
                        "actual_hash": current_tx.previous_hash,
                        "detected_at": datetime.now(),
                        "description": "Transaction hash chain broken - possible tampering"
                    })
        
        return suspicious_activities
    
    async def get_fraud_risk_score(self, user_id: int) -> Dict[str, Any]:
        """Calculate fraud risk score for a user (0-100)"""
        
        # Get user details
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {
                "user_id": user_id,
                "risk_score": 0,
                "risk_level": "unknown",
                "factors": ["User not found"]
            }
        
        # Start with base score
        risk_score = 0
        risk_factors = []
        
        # 1. Account age
        account_age_days = (datetime.now() - user.created_at).days
        if account_age_days < 7:
            risk_score += 20
            risk_factors.append(f"New account ({account_age_days} days old)")
        elif account_age_days < 30:
            risk_score += 10
            risk_factors.append(f"Recent account ({account_age_days} days old)")
        
        # 2. Verification status
        if user.status != UserStatus.VERIFIED:
            risk_score += 25
            risk_factors.append("Account not fully verified")
        
        if not user.is_email_verified:
            risk_score += 15
            risk_factors.append("Email not verified")
        
        if not user.is_kyc_verified and user.user_type.value in ["hospital", "organization"]:
            risk_score += 20
            risk_factors.append("KYC not verified for organization account")
        
        # 3. Donation patterns
        donation_count_result = await self.db.execute(
            select(func.count(Donation.id))
            .where(Donation.donor_id == user_id)
        )
        donation_count = donation_count_result.scalar() or 0
        
        if donation_count == 0:
            risk_score += 5
            risk_factors.append("No donation history")
        
        # 4. Failed payments
        failed_payments_result = await self.db.execute(
            select(func.count(Donation.id))
            .where(
                and_(
                    Donation.donor_id == user_id,
                    Donation.payment_status == "failed"
                )
            )
        )
        failed_payments = failed_payments_result.scalar() or 0
        
        if failed_payments > 0:
            risk_score += min(failed_payments * 10, 30)
            risk_factors.append(f"{failed_payments} failed payment(s)")
        
        # 5. Rejected KYC documents
        from ..models.user import KYCDocument
        
        rejected_docs_result = await self.db.execute(
            select(func.count(KYCDocument.id))
            .where(
                and_(
                    KYCDocument.user_id == user_id,
                    KYCDocument.is_verified == False,
                    KYCDocument.rejection_reason.isnot(None)
                )
            )
        )
        rejected_docs = rejected_docs_result.scalar() or 0
        
        if rejected_docs > 0:
            risk_score += min(rejected_docs * 15, 45)
            risk_factors.append(f"{rejected_docs} rejected KYC document(s)")
        
        # Cap risk score at 100
        risk_score = min(risk_score, 100)
        
        # Determine risk level
        risk_level = "low"
        if risk_score >= 75:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        
        return {
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": risk_factors
        }
