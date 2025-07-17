"""
Authentication API endpoints
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from ..core.database import get_db
from ..core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    create_verification_token,
    verify_verification_token
)
from ..models.user import User, UserType, UserStatus, UserPoints
from ..core.config import settings

router = APIRouter()


class UserRegister(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str
    full_name: str
    user_type: UserType
    phone: str = None
    organization_name: str = None
    license_number: str = None
    address: str = None
    city: str = None
    province: str = None


class UserLogin(BaseModel):
    """User login response"""
    access_token: str
    token_type: str
    user: dict


class Token(BaseModel):
    """Token response"""
    access_token: str
    token_type: str


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user"""
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        user_type=user_data.user_type,
        phone=user_data.phone,
        organization_name=user_data.organization_name,
        license_number=user_data.license_number,
        address=user_data.address,
        city=user_data.city,
        province=user_data.province,
        status=UserStatus.PENDING
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Create user points record
    user_points = UserPoints(user_id=db_user.id)
    db.add(user_points)
    await db.commit()
    
    # Create email verification token
    verification_token = create_verification_token(user_data.email)
    
    return {
        "message": "User registered successfully",
        "user_id": db_user.id,
        "verification_token": verification_token,
        "status": "pending_verification"
    }


@router.post("/login", response_model=UserLogin)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """User login"""
    
    # Get user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login = func.now()
    await db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type.value,
            "status": user.status.value,
            "is_verified": user.status == UserStatus.VERIFIED
        }
    }


@router.post("/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Verify user email"""
    
    email = verify_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )
    
    # Get user and update verification status
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    user.is_email_verified = True
    
    # Auto-verify individual users, others need KYC
    if user.user_type == UserType.INDIVIDUAL:
        user.status = UserStatus.VERIFIED
    
    await db.commit()
    
    return {
        "message": "Email verified successfully",
        "status": user.status.value
    }
