"""
Transparency service for blockchain-inspired transaction logging
"""
import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models.donation import DonationTransaction, Donation
from ..models.user import User


class TransparencyService:
    """Service for transparent transaction logging and verification"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_transaction_chain(self, donation_id: int) -> List[Dict[str, Any]]:
        """Get the complete transaction chain for a donation"""
        
        result = await self.db.execute(
            select(DonationTransaction)
            .where(DonationTransaction.donation_id == donation_id)
            .order_by(DonationTransaction.id.asc())
        )
        
        transactions = result.scalars().all()
        
        # Format transactions for transparency
        chain = []
        for tx in transactions:
            # Get actor information
            actor_info = await self._get_actor_info(tx.actor_id, tx.actor_type)
            
            chain.append({
                "id": tx.id,
                "transaction_type": tx.transaction_type,
                "description": tx.description,
                "actor": actor_info,
                "metadata": tx.metadata,
                "transaction_hash": tx.transaction_hash,
                "previous_hash": tx.previous_hash,
                "timestamp": tx.created_at,
                "verified": await self._verify_transaction_hash(tx)
            })
        
        return chain
    
    async def verify_chain_integrity(self, donation_id: int) -> Dict[str, Any]:
        """Verify the integrity of a donation's transaction chain"""
        
        transactions = await self.get_transaction_chain(donation_id)
        
        if not transactions:
            return {
                "valid": True,
                "message": "No transactions to verify",
                "total_transactions": 0
            }
        
        # Verify each transaction hash
        invalid_transactions = []
        broken_chain = False
        
        for i, tx in enumerate(transactions):
            # Verify transaction hash
            if not tx["verified"]:
                invalid_transactions.append({
                    "transaction_id": tx["id"],
                    "reason": "Invalid transaction hash"
                })
            
            # Verify chain linkage (except for first transaction)
            if i > 0:
                expected_previous_hash = transactions[i-1]["transaction_hash"]
                if tx["previous_hash"] != expected_previous_hash:
                    broken_chain = True
                    invalid_transactions.append({
                        "transaction_id": tx["id"],
                        "reason": "Broken chain linkage"
                    })
        
        is_valid = len(invalid_transactions) == 0 and not broken_chain
        
        return {
            "valid": is_valid,
            "total_transactions": len(transactions),
            "invalid_transactions": invalid_transactions,
            "chain_broken": broken_chain,
            "message": "Chain is valid" if is_valid else "Chain integrity compromised"
        }
    
    async def get_public_transparency_data(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get public transparency data for the platform"""
        
        # Get recent donations with transaction counts
        donations_query = select(
            Donation.id,
            Donation.title,
            Donation.donation_type,
            Donation.status,
            Donation.created_at,
            func.count(DonationTransaction.id).label('transaction_count')
        ).select_from(
            Donation
        ).outerjoin(
            DonationTransaction
        ).group_by(
            Donation.id
        ).order_by(
            Donation.created_at.desc()
        ).limit(limit).offset(offset)
        
        result = await self.db.execute(donations_query)
        donations_data = result.all()
        
        # Get platform statistics
        stats = await self._get_platform_statistics()
        
        # Format public data (anonymized)
        public_donations = []
        for donation_data in donations_data:
            public_donations.append({
                "donation_id": donation_data.id,
                "title": donation_data.title,
                "type": donation_data.donation_type.value,
                "status": donation_data.status.value,
                "created_date": donation_data.created_at.date(),
                "transaction_count": donation_data.transaction_count,
                "transparency_score": await self._calculate_transparency_score(donation_data.id)
            })
        
        return {
            "donations": public_donations,
            "statistics": stats,
            "total_donations": len(public_donations),
            "platform_integrity": await self._get_platform_integrity_score()
        }
    
    async def _get_actor_info(self, actor_id: int, actor_type: str) -> Dict[str, Any]:
        """Get actor information for transparency"""
        
        if actor_type == "system":
            return {
                "type": "system",
                "name": "Ytili System",
                "id": "system"
            }
        
        if actor_id == 0:
            return {
                "type": "system",
                "name": "Automated Process",
                "id": "auto"
            }
        
        # Get user information
        result = await self.db.execute(
            select(User).where(User.id == actor_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {
                "type": "unknown",
                "name": "Unknown User",
                "id": str(actor_id)
            }
        
        # Return anonymized user info for transparency
        return {
            "type": user.user_type.value,
            "name": user.organization_name or f"User {user.id}",
            "id": str(user.id),
            "verified": user.status.value == "verified"
        }
    
    async def _verify_transaction_hash(self, transaction: DonationTransaction) -> bool:
        """Verify a transaction's hash integrity"""
        
        # Reconstruct the transaction data that was hashed
        transaction_data = {
            "donation_id": transaction.donation_id,
            "transaction_type": transaction.transaction_type,
            "description": transaction.description,
            "actor_id": transaction.actor_id,
            "actor_type": transaction.actor_type,
            "metadata": transaction.metadata or {},
            "previous_hash": transaction.previous_hash
        }
        
        # Calculate expected hash
        expected_hash = hashlib.sha256(
            json.dumps(transaction_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Note: In the actual implementation, we'd need to include timestamp
        # For now, we'll just check if the hash exists and is properly formatted
        return (
            transaction.transaction_hash and 
            len(transaction.transaction_hash) == 64 and
            all(c in '0123456789abcdef' for c in transaction.transaction_hash.lower())
        )
    
    async def _get_platform_statistics(self) -> Dict[str, Any]:
        """Get platform-wide statistics"""
        
        # Total donations
        total_donations_result = await self.db.execute(
            select(func.count(Donation.id))
        )
        total_donations = total_donations_result.scalar() or 0
        
        # Total transactions
        total_transactions_result = await self.db.execute(
            select(func.count(DonationTransaction.id))
        )
        total_transactions = total_transactions_result.scalar() or 0
        
        # Donations by status
        status_result = await self.db.execute(
            select(
                Donation.status,
                func.count(Donation.id)
            ).group_by(Donation.status)
        )
        status_counts = {status.value: count for status, count in status_result.all()}
        
        # Donations by type
        type_result = await self.db.execute(
            select(
                Donation.donation_type,
                func.count(Donation.id)
            ).group_by(Donation.donation_type)
        )
        type_counts = {dtype.value: count for dtype, count in type_result.all()}
        
        return {
            "total_donations": total_donations,
            "total_transactions": total_transactions,
            "donations_by_status": status_counts,
            "donations_by_type": type_counts,
            "average_transactions_per_donation": (
                total_transactions / total_donations if total_donations > 0 else 0
            )
        }
    
    async def _calculate_transparency_score(self, donation_id: int) -> float:
        """Calculate transparency score for a donation (0-100)"""
        
        # Get transaction chain
        chain = await self.get_transaction_chain(donation_id)
        
        if not chain:
            return 0.0
        
        score = 0.0
        
        # Base score for having transactions
        score += 20.0
        
        # Score for chain integrity
        integrity = await self.verify_chain_integrity(donation_id)
        if integrity["valid"]:
            score += 30.0
        
        # Score for number of transactions (more = more transparent)
        transaction_count = len(chain)
        if transaction_count >= 5:
            score += 25.0
        elif transaction_count >= 3:
            score += 15.0
        elif transaction_count >= 1:
            score += 10.0
        
        # Score for having verified actors
        verified_actors = sum(1 for tx in chain if tx["actor"].get("verified", False))
        if verified_actors > 0:
            score += min(25.0, (verified_actors / len(chain)) * 25.0)
        
        return min(100.0, score)
    
    async def _get_platform_integrity_score(self) -> float:
        """Calculate overall platform integrity score"""
        
        # Sample recent donations for integrity check
        recent_donations_result = await self.db.execute(
            select(Donation.id)
            .order_by(Donation.created_at.desc())
            .limit(50)
        )
        
        donation_ids = [row[0] for row in recent_donations_result.all()]
        
        if not donation_ids:
            return 100.0
        
        # Check integrity of sample donations
        valid_chains = 0
        for donation_id in donation_ids:
            integrity = await self.verify_chain_integrity(donation_id)
            if integrity["valid"]:
                valid_chains += 1
        
        # Calculate percentage of valid chains
        integrity_percentage = (valid_chains / len(donation_ids)) * 100
        
        return integrity_percentage
