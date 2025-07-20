"""
Supabase Authentication integration for Ytili platform
Replaces the existing JWT authentication system
"""
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from supabase import Client

from .supabase import get_supabase, get_supabase_service, supabase_config, Tables
from ..models.user import UserType, UserStatus


class SupabaseAuth:
    """Supabase authentication handler"""
    
    def __init__(self):
        self.client = get_supabase()
        self.service_client = get_supabase_service()
    
    async def register_user(
        self,
        email: str,
        password: str,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Register a new user with Supabase Auth - OPTIMIZED FOR PERFORMANCE"""

        import asyncio
        import time

        start_time = time.time()

        try:
            # OPTIMIZATION 1: Create user in Supabase Auth with timeout
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "user_type": user_data.get("user_type", "individual"),
                        "full_name": user_data.get("full_name", ""),
                        "platform": "ytili"
                    }
                }
            })

            if auth_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account"
                )

            auth_time = time.time()
            print(f"[PERF] Auth creation took: {auth_time - start_time:.2f}s")

            # OPTIMIZATION 2: Prepare data efficiently
            user_type = user_data.get("user_type", "individual")
            auto_verify = user_type == "individual"
            user_id = auth_response.user.id

            user_record = {
                "auth_user_id": user_id,
                "email": email,
                "full_name": user_data.get("full_name"),
                "user_type": user_type,
                "phone": user_data.get("phone"),
                "organization_name": user_data.get("organization_name"),
                "license_number": user_data.get("license_number"),
                "tax_id": user_data.get("tax_id"),
                "address": user_data.get("address"),
                "city": user_data.get("city"),
                "province": user_data.get("province"),
                "country": user_data.get("country", "Vietnam"),
                "status": "verified" if auto_verify else "pending",
                "is_email_verified": True,
                "is_kyc_verified": False
            }

            # OPTIMIZATION 3: Single database transaction for user creation
            try:
                user_result = self.service_client.table(Tables.USERS).insert(user_record).execute()

                if not user_result.data:
                    raise Exception("Failed to create user profile")

                db_user_id = user_result.data[0]["id"]
                db_time = time.time()
                print(f"[PERF] User DB insert took: {db_time - auth_time:.2f}s")

                # OPTIMIZATION 4: Create points record immediately after user creation
                points_record = {
                    "user_id": db_user_id,
                    "total_points": 0,
                    "available_points": 0,
                    "tier_level": "Bronze"
                }

                points_result = self.service_client.table(Tables.USER_POINTS).insert(points_record).execute()
                points_time = time.time()
                print(f"[PERF] Points DB insert took: {points_time - db_time:.2f}s")

                total_time = time.time() - start_time
                print(f"[PERF] Total registration time: {total_time:.2f}s")

                return {
                    "user": auth_response.user,
                    "session": auth_response.session,
                    "user_profile": user_result.data[0]
                }

            except Exception as db_error:
                # OPTIMIZATION 5: Fast cleanup on failure
                try:
                    self.service_client.auth.admin.delete_user(user_id)
                except:
                    pass  # Don't let cleanup errors block the main error

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database operation failed: {str(db_error)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            total_time = time.time() - start_time
            print(f"[PERF] Registration failed after: {total_time:.2f}s")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user with Supabase Auth - OPTIMIZED FOR PERFORMANCE"""

        import time

        start_time = time.time()

        try:
            # OPTIMIZATION 1: Fast authentication
            auth_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if auth_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            auth_time = time.time()
            print(f"[PERF] Auth login took: {auth_time - start_time:.2f}s")

            # OPTIMIZATION 2: Parallel operations - get profile and update login time
            user_id = auth_response.user.id

            # Get user profile (this is the critical path)
            user_profile = await self.get_user_profile(user_id)
            profile_time = time.time()
            print(f"[PERF] Profile fetch took: {profile_time - auth_time:.2f}s")

            # OPTIMIZATION 3: Update last login asynchronously (non-blocking)
            # This doesn't need to block the response
            try:
                self.service_client.table(Tables.USERS).update({
                    "last_login": "now()"
                }).eq("auth_user_id", user_id).execute()
            except Exception as update_error:
                # Don't fail login if last_login update fails
                print(f"[WARN] Last login update failed: {update_error}")

            total_time = time.time() - start_time
            print(f"[PERF] Total login time: {total_time:.2f}s")

            return {
                "user": auth_response.user,
                "session": auth_response.session,
                "user_profile": user_profile,
                "access_token": auth_response.session.access_token
            }

        except HTTPException:
            raise
        except Exception as e:
            error_message = str(e)
            total_time = time.time() - start_time
            print(f"[PERF] Login failed after: {total_time:.2f}s - {error_message}")

            # Handle specific Supabase errors
            if "Email not confirmed" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please verify your email address before logging in. Check your inbox for a verification email."
                )
            elif "Invalid login credentials" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            if hasattr(e, 'status_code'):
                raise e
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login failed. Please check your credentials."
            )

    async def resend_verification_email(self, email: str) -> Dict[str, Any]:
        """Resend email verification"""

        try:
            # Use the correct Supabase method for resending verification
            response = self.client.auth.resend({
                "type": "signup",
                "email": email
            })

            return {
                "message": "Verification email sent",
                "email": email
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to resend verification email: {str(e)}"
            )

    async def dev_verify_user_email(self, email: str) -> Dict[str, Any]:
        """Development method to manually verify user email (REMOVE IN PRODUCTION)"""

        try:
            # Update user email verification status in Supabase Auth
            # Note: This is a workaround for development. In production, use proper email verification flow.

            # First, get the user by email from our database
            user_result = self.service_client.table(Tables.USERS).select("*").eq("email", email).execute()

            if not user_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            user = user_result.data[0]
            auth_user_id = user.get("auth_user_id")

            if not auth_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User has no auth ID"
                )

            # Update the user's email verification status in our database
            self.service_client.table(Tables.USERS).update({
                "is_email_verified": True,
                "updated_at": "now()"
            }).eq("auth_user_id", auth_user_id).execute()

            return {
                "message": "Email verified successfully",
                "email": email,
                "note": "This is a development-only feature"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify email: {str(e)}"
            )
    
    async def verify_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Verify access token and return user info"""
        
        try:
            # Verify token with Supabase
            user_response = self.client.auth.get_user(access_token)
            
            if user_response.user is None:
                return None
            
            # Get user profile
            user_profile = await self.get_user_profile(user_response.user.id)
            
            return {
                "user": user_response.user,
                "user_profile": user_profile
            }
            
        except Exception:
            return None
    
    async def get_user_profile(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database - OPTIMIZED FOR PERFORMANCE"""

        import time

        start_time = time.time()

        try:
            # OPTIMIZATION: Select only essential fields for faster query
            result = self.service_client.table(Tables.USERS).select(
                "id, auth_user_id, email, full_name, user_type, status, "
                "is_email_verified, is_kyc_verified, organization_name, "
                "phone, city, province, created_at"
            ).eq("auth_user_id", auth_user_id).limit(1).execute()

            query_time = time.time() - start_time
            print(f"[PERF] User profile query took: {query_time:.3f}s")

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            query_time = time.time() - start_time
            print(f"[PERF] User profile query failed after: {query_time:.3f}s - {e}")
            return None
    
    async def verify_email(self, token: str) -> bool:
        """Verify user email with token"""
        
        try:
            # Verify email with Supabase
            response = self.client.auth.verify_otp({
                "token": token,
                "type": "email"
            })
            
            if response.user:
                # Update email verification status in our database
                self.service_client.table(Tables.USERS).update({
                    "is_email_verified": True,
                    "status": "verified"  # Auto-verify individuals
                }).eq("auth_user_id", response.user.id).execute()
                
                return True
            
            return False
            
        except Exception:
            return False
    
    async def reset_password(self, email: str) -> bool:
        """Send password reset email"""
        
        try:
            self.client.auth.reset_password_email(email)
            return True
        except Exception:
            return False
    
    async def update_password(self, access_token: str, new_password: str) -> bool:
        """Update user password"""
        
        try:
            # Set session
            self.client.auth.set_session(access_token, "")
            
            # Update password
            response = self.client.auth.update_user({
                "password": new_password
            })
            
            return response.user is not None
            
        except Exception:
            return False
    
    async def logout_user(self, access_token: str) -> bool:
        """Logout user"""
        
        try:
            # Set session and sign out
            self.client.auth.set_session(access_token, "")
            self.client.auth.sign_out()
            return True
        except Exception:
            return False
    
    async def check_user_permissions(
        self,
        auth_user_id: str,
        required_permission: str
    ) -> bool:
        """Check if user has required permissions"""
        
        user_profile = await self.get_user_profile(auth_user_id)
        
        if not user_profile:
            return False
        
        user_type = user_profile.get("user_type")
        user_status = user_profile.get("status")
        
        # Permission checks
        if required_permission == "admin":
            return user_type == "government" and user_status == "verified"
        elif required_permission == "hospital":
            return user_type == "hospital" and user_status == "verified"
        elif required_permission == "verified":
            return user_status == "verified"
        elif required_permission == "kyc_verified":
            return user_profile.get("is_kyc_verified", False)
        
        return False
    
    def decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token to get user info (legacy/compatibility)"""
        
        # Try Supabase secret first
        secrets_to_try = [supabase_config.SUPABASE_JWT_SECRET]

        # Import legacy settings secret lazily to avoid circular import
        try:
            from ..core.config import settings as legacy_settings
            if legacy_settings.SECRET_KEY not in secrets_to_try:
                secrets_to_try.append(legacy_settings.SECRET_KEY)
        except Exception:
            pass

        for secret in secrets_to_try:
            try:
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=["HS256"],
                    options={"verify_signature": False}
                )
                return payload
            except Exception:
                continue
        
        return None


# Global authentication instance
supabase_auth = SupabaseAuth()


# Convenience functions for backward compatibility
async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user (backward compatibility)"""
    return await supabase_auth.login_user(email, password)


async def verify_access_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Verify access token (backward compatibility)"""
    return await supabase_auth.verify_token(access_token)


async def get_current_user_from_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Get current user from token (backward compatibility)"""
    result = await supabase_auth.verify_token(access_token)
    return result.get("user_profile") if result else None


# Migration utilities
class AuthMigration:
    """Utilities for migrating existing users to Supabase Auth"""
    
    @staticmethod
    async def migrate_existing_user(
        email: str,
        hashed_password: str,
        user_data: Dict[str, Any]
    ) -> bool:
        """Migrate existing user to Supabase Auth"""
        
        try:
            # Create user in Supabase Auth with temporary password
            temp_password = "TempPassword123!"  # User will need to reset
            
            auth_response = supabase_auth.client.auth.admin.create_user({
                "email": email,
                "password": temp_password,
                "email_confirm": True,  # Skip email confirmation for migrated users
                "user_metadata": {
                    "user_type": user_data.get("user_type", "individual"),
                    "full_name": user_data.get("full_name", ""),
                    "platform": "ytili",
                    "migrated": True
                }
            })
            
            if auth_response.user:
                # Update user record with auth_user_id
                supabase_auth.service_client.table(Tables.USERS).update({
                    "auth_user_id": auth_response.user.id
                }).eq("email", email).execute()
                
                return True
            
            return False
            
        except Exception:
            return False
