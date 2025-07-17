#!/usr/bin/env python3
"""
Minimal server to test if FastAPI works
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Ytili Test Server")

@app.get("/")
async def root():
    return {"message": "Ytili server is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ytili-backend"}

@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "API is working", "version": "1.0.0"}

if __name__ == "__main__":
    print("🚀 Starting Minimal Ytili Server...")
    print("📍 Server: http://127.0.0.1:8000")
    print("📚 Docs: http://127.0.0.1:8000/docs")
    print("-" * 40)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
