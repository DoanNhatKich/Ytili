#!/usr/bin/env python3
"""
Development server runner for Ytili platform
"""
import subprocess
import sys
import os
import time
import signal
from pathlib import Path


def run_backend():
    """Run the FastAPI backend server"""
    print("🚀 Starting Ytili Backend (FastAPI)...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Run the backend server
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])


def run_frontend():
    """Run the Flask frontend server"""
    print("🌐 Starting Ytili Frontend (Flask)...")
    
    # Change to frontend directory
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # Set environment variables
    env = os.environ.copy()
    env["FLASK_ENV"] = "development"
    env["FLASK_DEBUG"] = "1"
    
    # Run the frontend server
    return subprocess.Popen([
        sys.executable, "-m", "app.main"
    ], env=env)


def main():
    """Main function to run both servers"""
    print("=" * 60)
    print("🏥 YTILI - AI Agent for Transparent Medical Donations")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not (Path("backend").exists() and Path("frontend").exists()):
        print("❌ Error: Please run this script from the ytili project root directory")
        print("   Expected structure:")
        print("   ytili/")
        print("   ├── backend/")
        print("   ├── frontend/")
        print("   └── run_dev.py")
        sys.exit(1)
    
    # Start both servers
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        backend_process = run_backend()
        time.sleep(2)  # Give backend time to start
        
        # Start frontend
        frontend_process = run_frontend()
        time.sleep(2)  # Give frontend time to start
        
        print()
        print("✅ Both servers are starting up...")
        print()
        print("📍 URLs:")
        print("   🔧 Backend API:     http://localhost:8000")
        print("   📚 API Docs:        http://localhost:8000/docs")
        print("   🌐 Frontend:        http://localhost:5000")
        print("   📊 Transparency:    http://localhost:5000/transparency")
        print()
        print("💡 Tips:")
        print("   • Backend runs on port 8000 (FastAPI)")
        print("   • Frontend runs on port 5000 (Flask)")
        print("   • Both servers support hot reload")
        print("   • Press Ctrl+C to stop both servers")
        print()
        print("🔍 Monitoring logs...")
        print("-" * 60)
        
        # Wait for processes to complete
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend process stopped unexpectedly")
                break
            
            if frontend_process.poll() is not None:
                print("❌ Frontend process stopped unexpectedly")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
    
    finally:
        # Clean up processes
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        
        print("✅ All servers stopped")


if __name__ == "__main__":
    main()
