"""
Authentication API endpoints
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from ..core.supabase import get_supabase_service
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
    user_data: UserRegister
) -> Any:
    """Register a new user"""
    
    supabase = get_supabase_service()

    # Check if user already exists
    result = supabase.table("users").select("id").eq("email", user_data.email).execute()
    if result.data:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    # Insert user into Supabase
    insert_result = supabase.table("users").insert({
        "email": user_data.email,
        "hashed_password": hashed_password,
        "full_name": user_data.full_name,
        "user_type": user_data.user_type.value,
        "phone": user_data.phone,
        "organization_name": user_data.organization_name,
        "license_number": user_data.license_number,
        "address": user_data.address,
        "city": user_data.city,
        "province": user_data.province,
        "status": UserStatus.PENDING.value
    }).execute()

    if not insert_result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    db_user_id = insert_result.data[0]["id"]

    # Create user points record
    supabase.table("user_points").insert({
        "user_id": db_user_id
    }).execute()
    
    # Create email verification token
    verification_token = create_verification_token(user_data.email)
    
    return {
        "message": "User registered successfully",
        "user_id": db_user_id,
        "verification_token": verification_token,
        "status": "pending_verification"
    }


@router.post("/login", response_model=UserLogin)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """User login"""
    
    supabase = get_supabase_service()

    # Get user by email
    result = supabase.table("users").select("*").eq("email", form_data.username).maybe_single().execute()

    user = result.data
    
    if (not user) or (not verify_password(form_data.password, user["hashed_password"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["id"], expires_delta=access_token_expires
    )
    
    # Update last login
    supabase.table("users").update({"last_login": "now()"}).eq("id", user["id"]).execute()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "user_type": user["user_type"],
            "status": user["status"],
            "is_verified": user["status"] == UserStatus.VERIFIED.value
        }
    }


@router.post("/verify-email")
async def verify_email(
    token: str
) -> Any:
    """Verify user email"""
    
    email = verify_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )
    
    supabase = get_supabase_service()

    # Get user and update verification status
    result = supabase.table("users").select("*").eq("email", email).maybe_single().execute()
    user = result.data
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    update_fields = {
        "is_email_verified": True
    }

    # Auto-verify individual users, others need KYC
    if user["user_type"] == UserType.INDIVIDUAL.value:
        update_fields["status"] = UserStatus.VERIFIED.value

    supabase.table("users").update(update_fields).eq("id", user["id"]).execute()
    
    return {
        "message": "Email verified successfully",
        "status": update_fields.get("status", user["status"])
    }
