#!/usr/bin/env python3
"""Development server with live reload for both backend and frontend"""

import subprocess
import sys
import signal
import os
from pathlib import Path

def run_dev_servers():
    """Run both backend and frontend development servers"""
    processes = []
    
    try:
        # Start backend with reload
        print("🚀 Starting FastAPI backend with reload...")
        backend_proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "aitrac.main:app",
            "--host", "127.0.0.1",
            "--port", "8080", 
            "--reload"
        ], cwd=Path.cwd())
        processes.append(backend_proc)
        
        # Start frontend dev server
        print("🎨 Starting React frontend with Vite...")
        frontend_proc = subprocess.Popen([
            "npm", "run", "dev"
        ], cwd=Path.cwd() / "frontend")
        processes.append(frontend_proc)
        
        print("\n✅ Development servers started!")
        print("📍 Backend API: http://localhost:8080/api/docs")
        print("📍 Frontend: http://localhost:5173")
        print("📍 Full app: http://localhost:5173 (with API proxy)")
        print("\nPress Ctrl+C to stop all servers\n")
        
        # Wait for processes
        for proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping development servers...")
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("✅ All servers stopped")

if __name__ == "__main__":
    # Ensure we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
        
    # Ensure virtual environment is activated
    if not os.environ.get("VIRTUAL_ENV"):
        print("❌ Please activate the virtual environment first:")
        print("   source .venv/bin/activate")
        sys.exit(1)
    
    run_dev_servers()