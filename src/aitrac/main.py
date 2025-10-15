"""FastAPI application for AiTrac"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import mimetypes

# Ensure JS files are served with correct MIME type
mimetypes.add_type('application/javascript', '.js')

from aitrac.api.issues import router as issues_router
from aitrac.api.dependencies import router as dependencies_router
from aitrac.api.work import router as work_router

# Create FastAPI app
app = FastAPI(
    title="AiTrac API",
    description="AI Agent Issue Tracker with dependency-first workflow",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware for development (when frontend runs on different port)
# In production, the frontend is served from the same origin, so no CORS needed
import os
if os.getenv("AITRAC_ENV") == "development" or os.path.exists("frontend"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173", 
            "http://localhost:3000",  # Alternative React dev server port
            "http://127.0.0.1:3000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(issues_router, prefix="/api/issues", tags=["issues"])
app.include_router(dependencies_router, prefix="/api/issues", tags=["dependencies"])
app.include_router(work_router, prefix="/api/work", tags=["work"])

# Static files (React build)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_spa():
    """Serve React SPA"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        # Development fallback
        return {"message": "AiTrac API", "docs": "/api/docs"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "aitrac-api"}

@app.on_event("startup")
async def startup_event():
    """Initialize database and run migrations on startup"""
    from aitrac.storage.database import initialize_database
    await initialize_database()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)