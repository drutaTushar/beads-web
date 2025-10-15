"""Work management API endpoints"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/ready")
async def get_ready_work():
    """Get ready work (Ready() algorithm)"""
    return {"ready_issues": [], "message": "Ready work endpoint - placeholder"}

@router.get("/blocked")
async def get_blocked_issues():
    """Get blocked issues"""
    return {"blocked_issues": [], "message": "Blocked issues endpoint - placeholder"}

@router.get("/issues/{issue_id}/why-blocked")
async def why_blocked(issue_id: str):
    """Why blocked analysis for issue"""
    return {"issue_id": issue_id, "blocking_chain": [], "message": "Why blocked endpoint - placeholder"}

@router.post("/import/markdown")
async def import_markdown():
    """Import issues from markdown"""
    return {"imported_count": 0, "message": "Markdown import endpoint - placeholder"}