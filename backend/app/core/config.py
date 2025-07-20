"""
Ytili Backend Configuration
Core configuration settings for the Ytili platform
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings - Simple class using os.getenv"""

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Ytili - AI Agent for Transparent Medical Donations")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # API
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ytili")

    # Redis for Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # OpenRouter API (NO OpenAI allowed per ruleset)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "qwen/qwen3-235b-a22b:free")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    # AI Agent Configuration
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "4000"))
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    AI_MAX_CONTEXT_TOKENS: int = int(os.getenv("AI_MAX_CONTEXT_TOKENS", "8000"))
    MEDICAL_DISCLAIMER_ENABLED: bool = os.getenv("MEDICAL_DISCLAIMER_ENABLED", "true").lower() == "true"

    # Emergency Response Configuration
    EMERGENCY_RESPONSE_ENABLED: bool = os.getenv("EMERGENCY_RESPONSE_ENABLED", "true").lower() == "true"
    EMERGENCY_PHONE_NUMBER: str = os.getenv("EMERGENCY_PHONE_NUMBER", "115")  # Vietnam emergency number

    # OCR and Document Processing
    TESSERACT_PATH: Optional[str] = os.getenv("TESSERACT_PATH")  # Path to Tesseract OCR
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", "10485760"))  # 10MB

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_PUBLIC_KEY: str = os.getenv("SUPABASE_PUBLIC_KEY")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET")
    SUPABASE_AUTH_EXPIRY: int = int(os.getenv("SUPABASE_AUTH_EXPIRY", "3600"))

    # Blockchain Configuration (Saga)
    SAGA_RPC_URL: str = os.getenv("SAGA_RPC_URL", "https://ytili-2752546100676000-1.jsonrpc.sagarpc.io")
    SAGA_CHAIN_ID: str = os.getenv("SAGA_CHAIN_ID", "ytili_2752546100676000-1")
    SAGA_PRIVATE_KEY: str = os.getenv("SAGA_PRIVATE_KEY")

    # VietQR Configuration
    VIETQR_API_URL: str = os.getenv("VIETQR_API_URL", "https://api.vietqr.io/v2")
    VIETQR_CLIENT_ID: Optional[str] = os.getenv("VIETQR_CLIENT_ID")
    VIETQR_API_KEY: Optional[str] = os.getenv("VIETQR_API_KEY")

    # Smart Contract Addresses (Deployed on Saga)
    YTILI_TOKEN_ADDRESS: str = os.getenv("YTILI_TOKEN_ADDRESS")
    DONATION_REGISTRY_ADDRESS: str = os.getenv("DONATION_REGISTRY_ADDRESS")
    TRANSPARENCY_VERIFIER_ADDRESS: str = os.getenv("TRANSPARENCY_VERIFIER_ADDRESS")
    YTILI_GOVERNANCE_ADDRESS: str = os.getenv("YTILI_GOVERNANCE_ADDRESS")
    
    # Security
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_FOLDER: str = "uploads"
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf"]
    
    # Email (for notifications)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
    SMTP_TLS: Optional[bool] = os.getenv("SMTP_TLS", "true").lower() == "true" if os.getenv("SMTP_TLS") else None
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[str] = os.getenv("EMAILS_FROM_EMAIL")
    
    # Development/Production mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # CORS
    BACKEND_CORS_ORIGINS: str = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:5000,http://127.0.0.1:5000")

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as list"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    



# Global settings instance
settings = Settings
