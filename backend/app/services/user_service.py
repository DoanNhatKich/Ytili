"""
User service for business logic
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ..models.user import User, UserType, UserStatus, UserPoints, KYCDocument
from ..core.security import get_password_hash, verify_password


class UserService:
    """Service for user-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.points))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        user_type: UserType,
        **kwargs
    ) -> User:
        """Create a new user"""
        hashed_password = get_password_hash(password)
        
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            user_type=user_type,
            **kwargs
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Create user points record
        user_points = UserPoints(user_id=user.id)
        self.db.add(user_points)
        await self.db.commit()
        
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def update_user_status(self, user_id: int, status: UserStatus) -> bool:
        """Update user verification status"""
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=status)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def verify_email(self, email: str) -> bool:
        """Mark user email as verified"""
        result = await self.db.execute(
            update(User)
            .where(User.email == email)
            .values(is_email_verified=True)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def get_users_by_type(self, user_type: UserType) -> List[User]:
        """Get all users of a specific type"""
        result = await self.db.execute(
            select(User).where(User.user_type == user_type)
        )
        return result.scalars().all()
    
    async def get_pending_verifications(self) -> List[User]:
        """Get users pending verification"""
        result = await self.db.execute(
            select(User)
            .where(User.status == UserStatus.PENDING)
            .where(User.user_type.in_([UserType.HOSPITAL, UserType.ORGANIZATION]))
        )
        return result.scalars().all()
    
    async def add_kyc_document(
        self,
        user_id: int,
        document_type: str,
        file_path: str,
        original_filename: str,
        extracted_data: Optional[str] = None
    ) -> KYCDocument:
        """Add KYC document for user"""
        document = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            file_path=file_path,
            original_filename=original_filename,
            extracted_data=extracted_data
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def verify_kyc_document(
        self,
        document_id: int,
        verified_by: int,
        is_verified: bool,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """Verify or reject KYC document"""
        from sqlalchemy.sql import func
        
        values = {
            "is_verified": is_verified,
            "verified_by": verified_by,
            "verified_at": func.now() if is_verified else None,
            "rejection_reason": rejection_reason
        }
        
        result = await self.db.execute(
            update(KYCDocument)
            .where(KYCDocument.id == document_id)
            .values(**values)
        )
        await self.db.commit()
        
        # If all documents are verified, update user status
        if is_verified:
            await self._check_and_update_user_verification(document_id)
        
        return result.rowcount > 0
    
    async def _check_and_update_user_verification(self, document_id: int):
        """Check if all user documents are verified and update status"""
        # Get the document and user
        result = await self.db.execute(
            select(KYCDocument).where(KYCDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return
        
        # Check if all user's documents are verified
        result = await self.db.execute(
            select(KYCDocument)
            .where(KYCDocument.user_id == document.user_id)
            .where(KYCDocument.is_verified == False)
        )
        unverified_docs = result.scalars().all()
        
        # If no unverified documents, mark user as verified
        if not unverified_docs:
            await self.db.execute(
                update(User)
                .where(User.id == document.user_id)
                .values(
                    status=UserStatus.VERIFIED,
                    is_kyc_verified=True
                )
            )
            await self.db.commit()
