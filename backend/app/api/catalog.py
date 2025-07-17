"""
Medication catalog API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from ..core.database import get_db
from ..api.deps import get_current_verified_user, get_current_admin_user
from ..models.user import User
from ..services.catalog_service import CatalogService

router = APIRouter()


class MedicationCatalogResponse(BaseModel):
    """Schema for medication catalog response"""
    id: int
    name: str
    generic_name: Optional[str]
    brand_names: Optional[List[str]]
    category: str
    subcategory: Optional[str]
    therapeutic_class: Optional[str]
    registration_number: Optional[str]
    is_prescription_required: bool
    is_controlled_substance: bool
    dosage_form: Optional[str]
    strength: Optional[str]
    packaging: Optional[str]
    indications: Optional[str]
    contraindications: Optional[str]
    side_effects: Optional[str]
    storage_conditions: Optional[str]
    min_expiry_months: int
    is_donation_allowed: bool
    donation_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MedicationCatalogCreate(BaseModel):
    """Schema for creating medication catalog entry"""
    name: str
    generic_name: Optional[str] = None
    brand_names: Optional[List[str]] = None
    category: str
    subcategory: Optional[str] = None
    therapeutic_class: Optional[str] = None
    registration_number: Optional[str] = None
    is_prescription_required: bool = False
    is_controlled_substance: bool = False
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    packaging: Optional[str] = None
    indications: Optional[str] = None
    contraindications: Optional[str] = None
    side_effects: Optional[str] = None
    storage_conditions: Optional[str] = None
    min_expiry_months: int = 6
    is_donation_allowed: bool = True
    donation_notes: Optional[str] = None


class MedicationCatalogUpdate(BaseModel):
    """Schema for updating medication catalog entry"""
    name: Optional[str] = None
    generic_name: Optional[str] = None
    brand_names: Optional[List[str]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    therapeutic_class: Optional[str] = None
    registration_number: Optional[str] = None
    is_prescription_required: Optional[bool] = None
    is_controlled_substance: Optional[bool] = None
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    packaging: Optional[str] = None
    indications: Optional[str] = None
    contraindications: Optional[str] = None
    side_effects: Optional[str] = None
    storage_conditions: Optional[str] = None
    min_expiry_months: Optional[int] = None
    is_donation_allowed: Optional[bool] = None
    donation_notes: Optional[str] = None


@router.get("/", response_model=List[MedicationCatalogResponse])
async def get_medications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    prescription_required: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get medications from catalog with optional filtering"""
    catalog_service = CatalogService(db)
    
    medications = await catalog_service.get_all_medications(
        skip=skip,
        limit=limit,
        category=category,
        search=search,
        prescription_required=prescription_required
    )
    
    return medications


@router.get("/search", response_model=List[MedicationCatalogResponse])
async def search_medications(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Search medications by name, generic name, or therapeutic class"""
    catalog_service = CatalogService(db)
    
    medications = await catalog_service.search_medications(q, limit)
    return medications


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all medication categories"""
    catalog_service = CatalogService(db)
    
    categories = await catalog_service.get_categories()
    return {"categories": categories}


@router.get("/therapeutic-classes")
async def get_therapeutic_classes(db: AsyncSession = Depends(get_db)):
    """Get all therapeutic classes"""
    catalog_service = CatalogService(db)
    
    classes = await catalog_service.get_therapeutic_classes()
    return {"therapeutic_classes": classes}


@router.get("/recommendations", response_model=List[MedicationCatalogResponse])
async def get_donation_recommendations(
    budget: Optional[float] = Query(None, ge=0),
    category: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recommended medications for donation"""
    catalog_service = CatalogService(db)
    
    recommendations = await catalog_service.get_donation_recommendations(
        budget=budget,
        category=category,
        limit=limit
    )
    
    return recommendations


@router.get("/{medication_id}", response_model=MedicationCatalogResponse)
async def get_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific medication by ID"""
    catalog_service = CatalogService(db)
    
    medication = await catalog_service.get_medication_by_id(medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    return medication


@router.post("/", response_model=MedicationCatalogResponse)
async def create_medication(
    medication_data: MedicationCatalogCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new medication catalog entry (admin only)"""
    catalog_service = CatalogService(db)
    
    medication = await catalog_service.create_medication(
        medication_data.dict()
    )
    
    return medication


@router.put("/{medication_id}", response_model=MedicationCatalogResponse)
async def update_medication(
    medication_id: int,
    medication_data: MedicationCatalogUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a medication catalog entry (admin only)"""
    catalog_service = CatalogService(db)
    
    medication = await catalog_service.update_medication(
        medication_id,
        medication_data.dict(exclude_unset=True)
    )
    
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    return medication


@router.delete("/{medication_id}")
async def delete_medication(
    medication_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a medication catalog entry (admin only)"""
    catalog_service = CatalogService(db)
    
    success = await catalog_service.delete_medication(medication_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )
    
    return {"message": "Medication deleted successfully"}
