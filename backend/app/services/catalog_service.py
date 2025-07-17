"""
Medication and supply catalog service
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.sql import or_

from ..models.donation import MedicationCatalog


class CatalogService:
    """Service for medication and supply catalog operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_medications(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None,
        prescription_required: Optional[bool] = None
    ) -> List[MedicationCatalog]:
        """Get all medications with optional filtering"""
        query = select(MedicationCatalog)
        
        # Apply filters
        if category:
            query = query.where(MedicationCatalog.category == category)
        
        if prescription_required is not None:
            query = query.where(MedicationCatalog.is_prescription_required == prescription_required)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    MedicationCatalog.name.ilike(search_term),
                    MedicationCatalog.generic_name.ilike(search_term),
                    MedicationCatalog.therapeutic_class.ilike(search_term)
                )
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_medication_by_id(self, medication_id: int) -> Optional[MedicationCatalog]:
        """Get medication by ID"""
        result = await self.db.execute(
            select(MedicationCatalog).where(MedicationCatalog.id == medication_id)
        )
        return result.scalar_one_or_none()
    
    async def create_medication(self, medication_data: Dict[str, Any]) -> MedicationCatalog:
        """Create a new medication catalog entry"""
        medication = MedicationCatalog(**medication_data)
        
        self.db.add(medication)
        await self.db.commit()
        await self.db.refresh(medication)
        
        return medication
    
    async def update_medication(
        self,
        medication_id: int,
        medication_data: Dict[str, Any]
    ) -> Optional[MedicationCatalog]:
        """Update an existing medication catalog entry"""
        # Check if medication exists
        medication = await self.get_medication_by_id(medication_id)
        if not medication:
            return None
        
        # Update fields
        for field, value in medication_data.items():
            setattr(medication, field, value)
        
        await self.db.commit()
        await self.db.refresh(medication)
        
        return medication
    
    async def delete_medication(self, medication_id: int) -> bool:
        """Delete a medication catalog entry"""
        result = await self.db.execute(
            delete(MedicationCatalog).where(MedicationCatalog.id == medication_id)
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def get_categories(self) -> List[str]:
        """Get all unique medication categories"""
        result = await self.db.execute(
            select(MedicationCatalog.category).distinct()
        )
        return [category[0] for category in result.all()]
    
    async def get_therapeutic_classes(self) -> List[str]:
        """Get all unique therapeutic classes"""
        result = await self.db.execute(
            select(MedicationCatalog.therapeutic_class).distinct()
            .where(MedicationCatalog.therapeutic_class.isnot(None))
        )
        return [tc[0] for tc in result.all()]
    
    async def search_medications(self, query: str, limit: int = 10) -> List[MedicationCatalog]:
        """Search medications by name, generic name, or therapeutic class"""
        search_term = f"%{query}%"
        result = await self.db.execute(
            select(MedicationCatalog)
            .where(
                or_(
                    MedicationCatalog.name.ilike(search_term),
                    MedicationCatalog.generic_name.ilike(search_term),
                    MedicationCatalog.therapeutic_class.ilike(search_term)
                )
            )
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_donation_recommendations(
        self,
        budget: Optional[float] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[MedicationCatalog]:
        """Get recommended medications for donation based on budget and category"""
        # This is a placeholder for more sophisticated recommendation logic
        # In a real implementation, this would consider factors like:
        # - Current hospital needs
        # - Seasonal demand
        # - Medication shortages
        # - Historical donation patterns
        
        query = select(MedicationCatalog).where(MedicationCatalog.is_donation_allowed == True)
        
        if category:
            query = query.where(MedicationCatalog.category == category)
        
        # Order by priority (this would be a more complex algorithm in production)
        query = query.order_by(func.random()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
