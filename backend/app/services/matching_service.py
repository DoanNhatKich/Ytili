"""
Donation matching service
Intelligent matching of donations to hospital needs
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta

from ..models.donation import Donation, DonationType, DonationStatus
from ..models.user import User, UserType


class MatchingService:
    """Service for intelligent donation matching"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_matching_recipients(
        self,
        donation: Donation,
        max_distance_km: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Find potential recipients for a donation"""
        
        # Get hospitals that could receive this donation
        hospitals = await self._get_eligible_hospitals(donation)
        
        # Score and rank hospitals based on various factors
        scored_hospitals = []
        for hospital in hospitals:
            score = await self._calculate_match_score(donation, hospital)
            scored_hospitals.append({
                "hospital": hospital,
                "score": score,
                "reasons": await self._get_match_reasons(donation, hospital)
            })
        
        # Sort by score (highest first)
        scored_hospitals.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_hospitals[:10]  # Return top 10 matches
    
    async def _get_eligible_hospitals(self, donation: Donation) -> List[User]:
        """Get hospitals eligible to receive this donation"""
        query = select(User).where(
            and_(
                User.user_type == UserType.HOSPITAL,
                User.status.in_(["verified"]),
                User.is_kyc_verified == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _calculate_match_score(self, donation: Donation, hospital: User) -> float:
        """Calculate match score between donation and hospital"""
        score = 0.0
        
        # Base score for verified hospital
        score += 10.0
        
        # Location proximity (placeholder - would use actual coordinates)
        if donation.pickup_address and hospital.address:
            # Simplified location matching
            if self._addresses_in_same_city(donation.pickup_address, hospital.address):
                score += 20.0
            elif self._addresses_in_same_province(donation.pickup_address, hospital.address):
                score += 10.0
        
        # Hospital capacity and needs (placeholder)
        # In real implementation, this would check:
        # - Current inventory levels
        # - Historical consumption patterns
        # - Urgent needs requests
        score += await self._get_hospital_need_score(donation, hospital)
        
        # Donation type preference
        if donation.donation_type == DonationType.MEDICATION:
            score += 15.0  # Medications are always in high demand
        elif donation.donation_type == DonationType.MEDICAL_SUPPLY:
            score += 12.0
        elif donation.donation_type == DonationType.FOOD:
            score += 8.0
        
        # Expiry date urgency
        if donation.expiry_date:
            days_to_expiry = (donation.expiry_date - datetime.now()).days
            if days_to_expiry < 30:
                score += 25.0  # Urgent - near expiry
            elif days_to_expiry < 90:
                score += 15.0  # Moderate urgency
            else:
                score += 5.0   # Low urgency
        
        # Hospital reputation and history
        score += await self._get_hospital_reputation_score(hospital)
        
        return score
    
    async def _get_hospital_need_score(self, donation: Donation, hospital: User) -> float:
        """Calculate hospital's need score for this donation"""
        # Placeholder implementation
        # In real system, this would analyze:
        # - Current inventory levels
        # - Patient load
        # - Seasonal demands
        # - Emergency situations
        
        base_need = 10.0
        
        # Check if hospital has received similar donations recently
        recent_donations = await self._get_recent_donations_to_hospital(
            hospital.id, donation.donation_type
        )
        
        if len(recent_donations) == 0:
            base_need += 15.0  # High need if no recent donations
        elif len(recent_donations) < 3:
            base_need += 10.0  # Moderate need
        else:
            base_need += 5.0   # Lower need if well-supplied
        
        return base_need
    
    async def _get_recent_donations_to_hospital(
        self,
        hospital_id: int,
        donation_type: DonationType,
        days: int = 30
    ) -> List[Donation]:
        """Get recent donations to a hospital"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = await self.db.execute(
            select(Donation).where(
                and_(
                    Donation.recipient_id == hospital_id,
                    Donation.donation_type == donation_type,
                    Donation.created_at >= cutoff_date,
                    Donation.status.in_([
                        DonationStatus.COMPLETED,
                        DonationStatus.DELIVERED
                    ])
                )
            )
        )
        
        return result.scalars().all()
    
    async def _get_hospital_reputation_score(self, hospital: User) -> float:
        """Calculate hospital reputation score"""
        # Placeholder implementation
        # In real system, this would consider:
        # - Donation completion rate
        # - Feedback from donors
        # - Proper usage of donated items
        # - Transparency in reporting
        
        base_reputation = 5.0
        
        # Check completion rate of received donations
        total_donations = await self._count_hospital_donations(hospital.id)
        completed_donations = await self._count_hospital_completed_donations(hospital.id)
        
        if total_donations > 0:
            completion_rate = completed_donations / total_donations
            base_reputation += completion_rate * 10.0
        
        return base_reputation
    
    async def _count_hospital_donations(self, hospital_id: int) -> int:
        """Count total donations received by hospital"""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.count(Donation.id)).where(
                Donation.recipient_id == hospital_id
            )
        )
        
        return result.scalar() or 0
    
    async def _count_hospital_completed_donations(self, hospital_id: int) -> int:
        """Count completed donations by hospital"""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.count(Donation.id)).where(
                and_(
                    Donation.recipient_id == hospital_id,
                    Donation.status == DonationStatus.COMPLETED
                )
            )
        )
        
        return result.scalar() or 0
    
    def _addresses_in_same_city(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are in the same city (simplified)"""
        # Simplified implementation - in real system would use geocoding
        return "Ho Chi Minh" in addr1 and "Ho Chi Minh" in addr2
    
    def _addresses_in_same_province(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are in the same province (simplified)"""
        # Simplified implementation
        provinces = ["Ho Chi Minh", "Hanoi", "Da Nang", "Can Tho"]
        for province in provinces:
            if province in addr1 and province in addr2:
                return True
        return False
    
    async def _get_match_reasons(self, donation: Donation, hospital: User) -> List[str]:
        """Get reasons why this hospital is a good match"""
        reasons = []
        
        # Location-based reasons
        if donation.pickup_address and hospital.address:
            if self._addresses_in_same_city(donation.pickup_address, hospital.address):
                reasons.append("Same city - faster delivery")
            elif self._addresses_in_same_province(donation.pickup_address, hospital.address):
                reasons.append("Same province - regional delivery")
        
        # Need-based reasons
        recent_donations = await self._get_recent_donations_to_hospital(
            hospital.id, donation.donation_type
        )
        
        if len(recent_donations) == 0:
            reasons.append("High need - no recent similar donations")
        elif len(recent_donations) < 3:
            reasons.append("Moderate need - limited recent donations")
        
        # Urgency reasons
        if donation.expiry_date:
            days_to_expiry = (donation.expiry_date - datetime.now()).days
            if days_to_expiry < 30:
                reasons.append("Urgent - donation expires soon")
        
        # Hospital quality reasons
        completion_rate = await self._get_hospital_completion_rate(hospital.id)
        if completion_rate > 0.8:
            reasons.append("Reliable hospital - high completion rate")
        
        return reasons
    
    async def _get_hospital_completion_rate(self, hospital_id: int) -> float:
        """Get hospital's donation completion rate"""
        total = await self._count_hospital_donations(hospital_id)
        completed = await self._count_hospital_completed_donations(hospital_id)
        
        if total == 0:
            return 0.0
        
        return completed / total
