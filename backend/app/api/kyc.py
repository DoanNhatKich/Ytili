"""
KYC verification API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from ..core.database import get_db
from ..api.deps import get_current_verified_user, get_current_admin_user
from ..models.user import User, KYCDocument
from ..services.kyc_service import KYCService
from ..core.config import settings

router = APIRouter()


class KYCDocumentResponse(BaseModel):
    """Schema for KYC document response"""
    id: int
    user_id: int
    document_type: str
    original_filename: str
    is_verified: bool
    verified_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class KYCVerificationRequest(BaseModel):
    """Schema for KYC verification"""
    is_verified: bool
    rejection_reason: Optional[str] = None


@router.post("/upload", response_model=KYCDocumentResponse)
async def upload_kyc_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload KYC document for verification"""
    
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file extension
    allowed_extensions = settings.ALLOWED_EXTENSIONS
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Validate document type
    valid_document_types = [
        "national_id", "medical_license", "business_license", "tax_certificate"
    ]
    if document_type not in valid_document_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Valid types: {', '.join(valid_document_types)}"
        )
    
    # Process document
    kyc_service = KYCService(db)
    
    try:
        kyc_document = await kyc_service.process_document(
            user_id=current_user.id,
            document_type=document_type,
            file_content=file_content,
            original_filename=file.filename
        )
        
        return kyc_document
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/my-documents", response_model=List[KYCDocumentResponse])
async def get_my_kyc_documents(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's KYC documents"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(KYCDocument).where(KYCDocument.user_id == current_user.id)
    )
    documents = result.scalars().all()
    
    return documents


@router.get("/pending", response_model=List[KYCDocumentResponse])
async def get_pending_kyc_documents(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending KYC documents for admin review"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(KYCDocument).where(KYCDocument.is_verified == False)
    )
    documents = result.scalars().all()
    
    return documents


@router.get("/{document_id}", response_model=dict)
async def get_kyc_document_details(
    document_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get KYC document details including extracted data"""
    from sqlalchemy import select
    import json
    
    result = await db.execute(
        select(KYCDocument).where(KYCDocument.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Parse extracted data
    extracted_data = {}
    if document.extracted_data:
        try:
            extracted_data = json.loads(document.extracted_data)
        except json.JSONDecodeError:
            extracted_data = {"error": "Failed to parse extracted data"}
    
    return {
        "id": document.id,
        "user_id": document.user_id,
        "document_type": document.document_type,
        "original_filename": document.original_filename,
        "is_verified": document.is_verified,
        "verified_at": document.verified_at,
        "rejection_reason": document.rejection_reason,
        "created_at": document.created_at,
        "extracted_data": extracted_data
    }


@router.post("/{document_id}/verify")
async def verify_kyc_document(
    document_id: int,
    verification_data: KYCVerificationRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify or reject a KYC document"""
    kyc_service = KYCService(db)
    
    success = await kyc_service.verify_document(
        document_id=document_id,
        verified_by=current_user.id,
        is_verified=verification_data.is_verified,
        rejection_reason=verification_data.rejection_reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    status_text = "verified" if verification_data.is_verified else "rejected"
    return {"message": f"Document {status_text} successfully"}


@router.get("/user/{user_id}/documents", response_model=List[KYCDocumentResponse])
async def get_user_kyc_documents(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get KYC documents for a specific user (admin only)"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(KYCDocument).where(KYCDocument.user_id == user_id)
    )
    documents = result.scalars().all()
    
    return documents
