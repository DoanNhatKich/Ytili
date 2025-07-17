#!/usr/bin/env python3
"""
Development server runner for Ytili backend
Automatically detects environment and runs on appropriate host
"""
import os
import sys
import uvicorn
from app.core.config import settings

def main():
    """Run the development server"""
    
    # Determine host based on environment
    if settings.ENVIRONMENT == "development":
        host = "127.0.0.1"  # localhost for development
        print("🔧 Running in DEVELOPMENT mode on localhost")
    else:
        host = "0.0.0.0"  # all interfaces for production
        print("🚀 Running in PRODUCTION mode on all interfaces")
    
    print(f"📍 Server will be available at: http://{host}:8000")
    print(f"📚 API Documentation: http://{host}:8000/docs")
    print(f"🔍 Alternative docs: http://{host}:8000/redoc")
    print("-" * 60)
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
