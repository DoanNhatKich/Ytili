"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from .config import settings

# Sync database setup
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database setup for FastAPI
# Handle both direct connection and transaction pooler URLs
import urllib.parse

database_url = settings.DATABASE_URL
if database_url and not database_url.startswith("postgresql+asyncpg://"):
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://")

# Handle special characters in password by URL encoding if needed
try:
    # Test if URL is parseable
    parsed = urllib.parse.urlparse(database_url)
    if not parsed.hostname:
        raise ValueError("Invalid database URL")
except Exception as e:
    print(f"Database URL parsing error: {e}")
    # If parsing fails, it might be due to special characters in password

async_engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for all models
Base = declarative_base()


# Dependency for FastAPI
async def get_db():
    """Get database session for FastAPI dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
