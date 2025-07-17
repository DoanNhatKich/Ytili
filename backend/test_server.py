#!/usr/bin/env python3
"""
Test server to verify Ytili backend is working
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("🚀 Starting Ytili Test Server...")
    print("📍 Server will be available at: http://127.0.0.1:8000")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    print("🤖 AI Agent endpoints: http://127.0.0.1:8000/api/v1/ai-agent/")
    print("-" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=True
    )
