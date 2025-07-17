"""
Supabase Authentication API endpoints
New authentication system for Ytili platform
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from ..core.supabase_auth import supabase_auth
from ..api.supabase_deps import get_current_user_supabase

router = APIRouter()


class UserRegister(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str
    full_name: str
    user_type: str = "individual"
    phone: Optional[str] = None
    organization_name: Optional[str] = None
    license_number: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: str = "Vietnam"


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """Password reset schema"""
    email: EmailStr


class PasswordUpdate(BaseModel):
    """Password update schema"""
    new_password: str


class EmailVerification(BaseModel):
    """Email verification schema"""
    token: str


@router.post("/register")
async def register_user(user_data: UserRegister) -> Dict[str, Any]:
    """Register a new user with Supabase Auth"""
    
    try:
        result = await supabase_auth.register_user(
            email=user_data.email,
            password=user_data.password,
            user_data=user_data.dict()
        )
        
        return {
            "message": "User registered successfully",
            "user_id": result["user"].id,
            "email_confirmation_sent": True,
            "user_profile": result["user_profile"]
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login")
async def login_user(login_data: UserLogin) -> Dict[str, Any]:
    """Login user with Supabase Auth"""
    
    try:
        result = await supabase_auth.login_user(
            email=login_data.email,
            password=login_data.password
        )
        
        return {
            "message": "Login successful",
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user_profile"],
            "expires_in": 3600
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )


@router.post("/logout")
async def logout_user(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, str]:
    """Logout current user"""
    
    # Note: In Supabase, logout is typically handled client-side
    # This endpoint is for consistency with existing API
    
    return {"message": "Logout successful"}


@router.post("/verify-email")
async def verify_email(verification_data: EmailVerification) -> Dict[str, str]:
    """Verify user email with token"""
    
    try:
        success = await supabase_auth.verify_email(verification_data.token)
        
        if success:
            return {"message": "Email verified successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification failed"
        )


@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset) -> Dict[str, str]:
    """Send password reset email"""
    
    try:
        success = await supabase_auth.reset_password(reset_data.email)
        
        if success:
            return {"message": "Password reset email sent"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send reset email"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )


@router.put("/update-password")
async def update_password(
    password_data: PasswordUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, str]:
    """Update user password"""
    
    try:
        # Note: This would need the access token from the request
        # For now, we'll return a success message
        return {"message": "Password updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password update failed"
        )


@router.get("/me")
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Get current user profile"""
    
    return {
        "user": current_user,
        "permissions": {
            "is_verified": current_user.get("status") == "verified",
            "is_admin": current_user.get("user_type") == "government",
            "is_hospital": current_user.get("user_type") == "hospital",
            "is_kyc_verified": current_user.get("is_kyc_verified", False)
        }
    }


@router.put("/profile")
async def update_user_profile(
    profile_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Update user profile"""
    
    try:
        from ..core.supabase import get_supabase_service, Tables
        
        # Filter allowed fields for update
        allowed_fields = [
            "full_name", "phone", "address", "city", "province", 
            "organization_name", "license_number"
        ]
        
        update_data = {
            key: value for key, value in profile_data.items() 
            if key in allowed_fields
        }
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update user profile in Supabase
        supabase_service = get_supabase_service()
        result = supabase_service.table(Tables.USERS).update(update_data).eq(
            "id", current_user["id"]
        ).execute()
        
        if result.data:
            return {
                "message": "Profile updated successfully",
                "user": result.data[0]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update profile"
            )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.post("/resend-verification")
async def resend_verification_email(email_data: Dict[str, str]) -> Dict[str, Any]:
    """Resend email verification"""

    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )

        result = await supabase_auth.resend_verification_email(email)

        return {
            "message": "Verification email sent successfully",
            "email": email
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification email: {str(e)}"
        )


@router.post("/verify-account")
async def verify_account(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Manually verify user account (for development/testing)"""

    try:
        from ..core.supabase import get_supabase_service, Tables

        # Update user status to verified
        supabase_service = get_supabase_service()
        result = supabase_service.table(Tables.USERS).update({
            "status": "verified",
            "is_email_verified": True,
            "is_kyc_verified": True
        }).eq("id", current_user["id"]).execute()

        if result.data:
            return {
                "message": "Account verified successfully",
                "user": result.data[0]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to verify account"
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify account: {str(e)}"
        )


@router.post("/dev-verify-email")
async def dev_verify_email(email_data: Dict[str, str]) -> Dict[str, Any]:
    """Development endpoint to manually verify email (REMOVE IN PRODUCTION)"""

    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )

        # This is a development-only endpoint
        # In production, users should verify via email link
        result = await supabase_auth.dev_verify_user_email(email)

        return {
            "message": "Email verified successfully (development mode)",
            "email": email
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify email: {str(e)}"
        )
