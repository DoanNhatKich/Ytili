"""
Supabase-based dependencies for API endpoints
New authentication system using Supabase Auth
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.supabase_auth import supabase_auth
from ..core.supabase import get_supabase_service, Tables

security = HTTPBearer()


async def get_current_user_supabase(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user from Supabase"""
    
    # Verify the token with Supabase
    user_data = await supabase_auth.verify_token(credentials.credentials)
    
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user_data.get("user_profile") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_data["user_profile"]


async def get_current_verified_user_supabase(
    current_user: Dict[str, Any] = Depends(get_current_user_supabase)
) -> Dict[str, Any]:
    """Get current verified user"""
    
    if current_user.get("status") != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not verified"
        )
    
    return current_user


async def get_current_admin_user_supabase(
    current_user: Dict[str, Any] = Depends(get_current_verified_user_supabase)
) -> Dict[str, Any]:
    """Get current admin user (government type)"""
    
    if current_user.get("user_type") != "government":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def get_current_hospital_user_supabase(
    current_user: Dict[str, Any] = Depends(get_current_verified_user_supabase)
) -> Dict[str, Any]:
    """Get current hospital user"""
    
    if current_user.get("user_type") != "hospital":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hospital access required"
        )
    
    return current_user


async def get_optional_current_user_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise None"""
    
    if credentials is None:
        return None
    
    try:
        return await get_current_user_supabase(credentials)
    except HTTPException:
        return None


# Backward compatibility wrapper
class UserCompat:
    """Compatibility wrapper for user objects to maintain existing API"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self._data = user_data
    
    @property
    def id(self) -> str:
        return self._data.get("id")
    
    @property
    def email(self) -> str:
        return self._data.get("email")
    
    @property
    def full_name(self) -> str:
        return self._data.get("full_name")
    
    @property
    def user_type(self):
        class UserTypeCompat:
            def __init__(self, value):
                self.value = value
        return UserTypeCompat(self._data.get("user_type"))
    
    @property
    def status(self):
        class StatusCompat:
            def __init__(self, value):
                self.value = value
        return StatusCompat(self._data.get("status"))
    
    @property
    def organization_name(self) -> Optional[str]:
        return self._data.get("organization_name")
    
    @property
    def city(self) -> Optional[str]:
        return self._data.get("city")
    
    @property
    def province(self) -> Optional[str]:
        return self._data.get("province")
    
    @property
    def is_email_verified(self) -> bool:
        return self._data.get("is_email_verified", False)
    
    @property
    def is_kyc_verified(self) -> bool:
        return self._data.get("is_kyc_verified", False)
    
    def __getattr__(self, name):
        return self._data.get(name)


async def get_current_user_compat(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserCompat:
    """Get current user with backward compatibility"""
    user_data = await get_current_user_supabase(credentials)
    return UserCompat(user_data)


async def get_current_verified_user_compat(
    current_user: Dict[str, Any] = Depends(get_current_verified_user_supabase)
) -> UserCompat:
    """Get current verified user with backward compatibility"""
    return UserCompat(current_user)


async def get_current_admin_user_compat(
    current_user: Dict[str, Any] = Depends(get_current_admin_user_supabase)
) -> UserCompat:
    """Get current admin user with backward compatibility"""
    return UserCompat(current_user)


async def get_current_hospital_user_compat(
    current_user: Dict[str, Any] = Depends(get_current_hospital_user_supabase)
) -> UserCompat:
    """Get current hospital user with backward compatibility"""
    return UserCompat(current_user)


async def get_current_user_supabase_ws(token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get current user for WebSocket connections"""

    if not token:
        return None

    try:
        # Verify JWT token with Supabase
        user_data = await supabase_auth.verify_token(token)

        if not user_data:
            return None

        # Get additional user info from database
        supabase = get_supabase_service()
        user_response = supabase.table(Tables.USERS).select("*").eq("id", user_data["id"]).execute()

        if user_response.data:
            # Merge auth data with user profile data
            user_profile = user_response.data[0]
            return {
                **user_data,
                **user_profile
            }

        return user_data

    except Exception:
        return None
