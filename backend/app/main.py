"""
Ytili Backend Main Application
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

from .core.config import settings
from .api import auth, donations, kyc, catalog, matching, payments, transparency, fraud, supabase_auth, vietqr_payments, blockchain, tokens, websocket, governance, fundraising
# from .api import ai_agent  # Temporarily disabled for testing
from .core.database import engine, Base, AsyncSessionLocal

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI Agent for Transparent Medical Donations Platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.ytili.com"]
)

# CORS middleware
# Get CORS origins
cors_origins = [origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Ytili Backend API", version=settings.VERSION)

    # Note: Using Supabase instead of local PostgreSQL
    # Database tables are managed through Supabase dashboard
    logger.info("Using Supabase for database operations")

    # Initialize blockchain service
    try:
        from .core.blockchain import blockchain_service
        logger.info("Blockchain service initialized")
    except Exception as e:
        logger.warning(f"Blockchain service initialization failed: {e}")

    logger.info("Application startup completed successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Ytili Backend API")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ytili-backend",
        "version": settings.VERSION,
        "performance_optimizations": "enabled"
    }


@app.get("/performance")
async def performance_check():
    """Performance monitoring endpoint"""
    import time
    from .core.supabase import get_supabase_service

    start_time = time.time()

    try:
        # Test database connection speed
        supabase = get_supabase_service()
        db_start = time.time()
        result = supabase.table("users").select("id").limit(1).execute()
        db_time = time.time() - db_start

        total_time = time.time() - start_time

        return {
            "status": "healthy",
            "database_response_time": f"{db_time:.3f}s",
            "total_response_time": f"{total_time:.3f}s",
            "database_connected": bool(result),
            "optimizations": {
                "performance_logging": "enabled",
                "database_indexes": "enabled",
                "query_optimization": "enabled"
            }
        }
    except Exception as e:
        total_time = time.time() - start_time
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "status": "degraded",
                "error": str(e),
                "total_response_time": f"{total_time:.3f}s"
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Ytili - AI Agent for Transparent Medical Donations",
        "version": settings.VERSION,
        "docs": "/docs",
        "api": settings.API_V1_STR
    }


# Include API routers
# Using Supabase-based authentication instead of old SQLAlchemy auth
app.include_router(
    supabase_auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"]
)

app.include_router(
    donations.router,
    prefix=f"{settings.API_V1_STR}/donations",
    tags=["donations"]
)

app.include_router(
    kyc.router,
    prefix=f"{settings.API_V1_STR}/kyc",
    tags=["kyc"]
)

app.include_router(
    catalog.router,
    prefix=f"{settings.API_V1_STR}/catalog",
    tags=["catalog"]
)

app.include_router(
    matching.router,
    prefix=f"{settings.API_V1_STR}/matching",
    tags=["matching"]
)

app.include_router(
    payments.router,
    prefix=f"{settings.API_V1_STR}/payments",
    tags=["payments"]
)

app.include_router(
    transparency.router,
    prefix=f"{settings.API_V1_STR}/transparency",
    tags=["transparency"]
)

app.include_router(
    fraud.router,
    prefix=f"{settings.API_V1_STR}/fraud",
    tags=["fraud"]
)

# Supabase auth router is now mounted at /auth above

app.include_router(
    vietqr_payments.router,
    prefix=f"{settings.API_V1_STR}/vietqr-payments",
    tags=["vietqr-payments"]
)

app.include_router(
    blockchain.router,
    prefix=f"{settings.API_V1_STR}/blockchain",
    tags=["blockchain"]
)

app.include_router(
    tokens.router,
    prefix=f"{settings.API_V1_STR}/tokens",
    tags=["tokens"]
)

app.include_router(
    websocket.router,
    prefix=f"{settings.API_V1_STR}/ws",
    tags=["websocket"]
)

app.include_router(
    governance.router,
    prefix=f"{settings.API_V1_STR}/governance",
    tags=["governance"]
)

app.include_router(
    fundraising.router,
    prefix=f"{settings.API_V1_STR}/fundraising",
    tags=["fundraising"]
)

# Temporarily disabled for testing
# app.include_router(
#     ai_agent.router,
#     prefix=f"{settings.API_V1_STR}/ai-agent",
#     tags=["ai-agent"]
# )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"detail": "Endpoint not found"}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error("Internal server error", exc_info=exc)
    return {"detail": "Internal server error"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
