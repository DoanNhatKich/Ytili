"""
Donation service for business logic
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import hashlib
import json
import time

from ..models.donation import (
    Donation, DonationTransaction, MedicationCatalog,
    DonationType, DonationStatus, PaymentStatus
)


class DonationService:
    """Service for donation-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_donation(
        self,
        donor_id: int,
        donation_type: DonationType,
        title: str,
        **kwargs
    ) -> Donation:
        """Create a new donation"""
        donation = Donation(
            donor_id=donor_id,
            donation_type=donation_type,
            title=title,
            **kwargs
        )
        
        self.db.add(donation)
        await self.db.commit()
        await self.db.refresh(donation)
        
        # Create initial transaction record
        await self.create_transaction(
            donation_id=donation.id,
            transaction_type="created",
            description=f"Donation created by user {donor_id}",
            actor_id=donor_id,
            actor_type="donor",
            metadata={"donation_type": donation_type.value}
        )
        
        return donation
    
    async def get_donation_by_id(self, donation_id: int) -> Optional[Donation]:
        """Get donation by ID"""
        result = await self.db.execute(
            select(Donation)
            .options(selectinload(Donation.transactions))
            .where(Donation.id == donation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_donations_by_donor(self, donor_id: int) -> List[Donation]:
        """Get all donations by a donor"""
        result = await self.db.execute(
            select(Donation).where(Donation.donor_id == donor_id)
        )
        return result.scalars().all()
    
    async def get_donations_by_recipient(self, recipient_id: int) -> List[Donation]:
        """Get all donations for a recipient"""
        result = await self.db.execute(
            select(Donation).where(Donation.recipient_id == recipient_id)
        )
        return result.scalars().all()
    
    async def update_donation_status(
        self,
        donation_id: int,
        status: DonationStatus,
        actor_id: int,
        actor_type: str,
        description: str = None
    ) -> bool:
        """Update donation status"""
        result = await self.db.execute(
            update(Donation)
            .where(Donation.id == donation_id)
            .values(status=status)
        )
        await self.db.commit()
        
        # Create transaction record for status change
        if result.rowcount > 0:
            await self.create_transaction(
                donation_id=donation_id,
                transaction_type=f"status_changed_to_{status.value}",
                description=description or f"Status changed to {status.value}",
                actor_id=actor_id,
                actor_type=actor_type,
                metadata={"new_status": status.value}
            )
        
        return result.rowcount > 0
    
    async def update_payment_status(
        self,
        donation_id: int,
        payment_status: PaymentStatus,
        actor_id: int,
        actor_type: str,
        description: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Update payment status"""
        result = await self.db.execute(
            update(Donation)
            .where(Donation.id == donation_id)
            .values(payment_status=payment_status)
        )
        await self.db.commit()
        
        # Create transaction record for payment status change
        if result.rowcount > 0:
            await self.create_transaction(
                donation_id=donation_id,
                transaction_type=f"payment_status_changed_to_{payment_status.value}",
                description=description or f"Payment status changed to {payment_status.value}",
                actor_id=actor_id,
                actor_type=actor_type,
                metadata=metadata or {"new_payment_status": payment_status.value}
            )
        
        return result.rowcount > 0
    
    async def create_transaction(
        self,
        donation_id: int,
        transaction_type: str,
        description: str,
        actor_id: int,
        actor_type: str,
        metadata: Dict[str, Any] = None
    ) -> DonationTransaction:
        """Create a transaction record for transparency"""
        # Get the previous transaction for this donation
        result = await self.db.execute(
            select(DonationTransaction)
            .where(DonationTransaction.donation_id == donation_id)
            .order_by(DonationTransaction.id.desc())
            .limit(1)
        )
        previous_transaction = result.scalar_one_or_none()
        previous_hash = previous_transaction.transaction_hash if previous_transaction else "0" * 64
        
        # Create a hash for this transaction
        transaction_data = {
            "donation_id": donation_id,
            "transaction_type": transaction_type,
            "description": description,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "previous_hash": previous_hash
        }
        
        transaction_hash = hashlib.sha256(
            json.dumps(transaction_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Create the transaction record
        transaction = DonationTransaction(
            donation_id=donation_id,
            transaction_type=transaction_type,
            description=description,
            actor_id=actor_id,
            actor_type=actor_type,
            metadata=metadata,
            transaction_hash=transaction_hash,
            previous_hash=previous_hash
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def get_medication_catalog(self, search_term: str = None) -> List[MedicationCatalog]:
        """Get medication catalog items, optionally filtered by search term"""
        query = select(MedicationCatalog)
        
        if search_term:
            query = query.where(
                MedicationCatalog.name.ilike(f"%{search_term}%") |
                MedicationCatalog.generic_name.ilike(f"%{search_term}%")
            )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_medication_by_id(self, medication_id: int) -> Optional[MedicationCatalog]:
        """Get medication by ID"""
        result = await self.db.execute(
            select(MedicationCatalog).where(MedicationCatalog.id == medication_id)
        )
        return result.scalar_one_or_none()
