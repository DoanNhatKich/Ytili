"""
Supabase configuration and client setup for Ytili platform
"""
import os
from typing import Optional
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SupabaseConfig:
    """Supabase configuration settings - Simple class using os.getenv"""

    # Supabase connection settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xhsuajatfcsmrebrlqhx.supabase.co")
    SUPABASE_PUBLIC_KEY: str = os.getenv("SUPABASE_PUBLIC_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhoc3VhamF0ZmNzbXJlYnJscWh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI1NzY0MjMsImV4cCI6MjA2ODE1MjQyM30.DpEfDd1GKF4lL-o2WvQuP-rXdEITqyWJs_P6ABCoH8A")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhoc3VhamF0ZmNzbXJlYnJscWh4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MjU3NjQyMywiZXhwIjoyMDY4MTUyNDIzfQ.adQqI0VWUd7-k-bj-OZFGN69L7iQ31DpOFIqnZezG7U")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "q6sdJqDjjQe1lI1B9ssBYIgNE6YvjikNIq3FOvXSLIznxZPw48MMBBMOvx7T7965xkNrv186gl3sgUcq/3uTEA==")
    SUPABASE_AUTH_EXPIRY: int = int(os.getenv("SUPABASE_AUTH_EXPIRY", "3600"))

    # Database settings
    SUPABASE_DB_SCHEMA: str = os.getenv("SUPABASE_DB_SCHEMA", "public")
    SUPABASE_REALTIME_ENABLED: bool = os.getenv("SUPABASE_REALTIME_ENABLED", "true").lower() == "true"


# Global Supabase configuration
supabase_config = SupabaseConfig


class SupabaseClient:
    """Supabase client wrapper for Ytili platform"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Get public Supabase client (for user operations) - OPTIMIZED"""
        if self._client is None:
            # Create client with basic configuration for now
            # TODO: Add timeout configuration when Supabase Python client supports it
            opts = ClientOptions()
            opts.schema = supabase_config.SUPABASE_DB_SCHEMA
            opts.headers = {"X-Client-Info": "ytili-backend"}
            opts.timeout = 5  # seconds, prevent long blocking
            self._client = create_client(
                supabase_config.SUPABASE_URL,
                supabase_config.SUPABASE_PUBLIC_KEY,
                options=opts
            )
        return self._client
    
    @property
    def service_client(self) -> Client:
        """Get service role Supabase client (for admin operations) - OPTIMIZED"""
        if self._service_client is None:
            # Create service client with basic configuration
            # TODO: Add timeout configuration when Supabase Python client supports it
            opts = ClientOptions()
            opts.schema = supabase_config.SUPABASE_DB_SCHEMA
            opts.headers = {"X-Client-Info": "ytili-backend-service"}
            opts.timeout = 5
            self._service_client = create_client(
                supabase_config.SUPABASE_URL,
                supabase_config.SUPABASE_SERVICE_KEY,
                options=opts
            )
        return self._service_client
    
    def get_user_client(self, access_token: str) -> Client:
        """Get authenticated user client with access token"""
        client = create_client(
            supabase_config.SUPABASE_URL,
            supabase_config.SUPABASE_PUBLIC_KEY
        )
        client.auth.set_session(access_token, "")
        return client


# Global Supabase client instance
supabase_client = SupabaseClient()


# Convenience functions for common operations
def get_supabase() -> Client:
    """Get the default Supabase client"""
    return supabase_client.client


def get_supabase_service() -> Client:
    """Get the service role Supabase client"""
    return supabase_client.service_client


def get_supabase_user(access_token: str) -> Client:
    """Get authenticated user Supabase client"""
    return supabase_client.get_user_client(access_token)


# Database table names (matching existing schema)
class Tables:
    """Supabase table names"""
    USERS = "users"
    USER_POINTS = "user_points"
    KYC_DOCUMENTS = "kyc_documents"
    DONATIONS = "donations"
    DONATION_TRANSACTIONS = "donation_transactions"
    MEDICATION_CATALOG = "medication_catalog"
    
    # New tables for enhanced features
    BLOCKCHAIN_TRANSACTIONS = "blockchain_transactions"
    VIETQR_PAYMENTS = "vietqr_payments"
    GOVERNANCE_PROPOSALS = "governance_proposals"
    GOVERNANCE_VOTES = "governance_votes"
    DONATION_STATUS_HISTORY = "donation_status_history"

    # Fundraising tables
    CAMPAIGNS = "campaigns"
    CAMPAIGN_DONATIONS = "campaign_donations"


# Database functions and RPC calls
class SupabaseRPC:
    """Supabase Remote Procedure Calls"""
    
    @staticmethod
    async def verify_user_permissions(client: Client, user_id: str, permission: str) -> bool:
        """Verify user has specific permission"""
        try:
            result = client.rpc('verify_user_permissions', {
                'user_id': user_id,
                'permission': permission
            }).execute()
            return result.data if result.data else False
        except Exception:
            return False
    
    @staticmethod
    async def get_donation_chain(client: Client, donation_id: int) -> list:
        """Get complete donation transaction chain"""
        try:
            result = client.rpc('get_donation_chain', {
                'donation_id': donation_id
            }).execute()
            return result.data if result.data else []
        except Exception:
            return []
    
    @staticmethod
    async def calculate_transparency_score(client: Client, donation_id: int) -> float:
        """Calculate transparency score for a donation"""
        try:
            result = client.rpc('calculate_transparency_score', {
                'donation_id': donation_id
            }).execute()
            return result.data if result.data else 0.0
        except Exception:
            return 0.0


# Error handling for Supabase operations
class SupabaseError(Exception):
    """Custom exception for Supabase operations"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def handle_supabase_error(error) -> SupabaseError:
    """Convert Supabase errors to custom exceptions"""
    if hasattr(error, 'message'):
        return SupabaseError(error.message, getattr(error, 'code', None))
    return SupabaseError(str(error))


# Migration utilities
class SupabaseMigration:
    """Utilities for migrating data to Supabase"""
    
    @staticmethod
    def create_user_metadata(user_type: str, is_verified: bool = False) -> dict:
        """Create user metadata for Supabase Auth"""
        return {
            "user_type": user_type,
            "is_verified": is_verified,
            "platform": "ytili",
            "created_via": "migration"
        }
    
    @staticmethod
    def format_datetime_for_supabase(dt) -> str:
        """Format datetime for Supabase insertion"""
        if dt is None:
            return None
        return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
