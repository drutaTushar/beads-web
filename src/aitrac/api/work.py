"""Work management API endpoints"""

from fastapi import APIRouter, Query
from typing import List

from ..storage.dependency_service import dependency_service
from .schemas import IssueResponse

router = APIRouter()

@router.get("/ready", response_model=List[IssueResponse])
async def get_ready_work(limit: int = Query(50, ge=1, le=100, description="Maximum number of ready issues to return")):
    """Get ready work (Ready() algorithm)
    
    Returns issues that can be started immediately:
    - Open issues with all dependencies closed
    - Recursive dependency resolution for parent-child relationships
    - Sorted by priority (0 highest, 4 lowest)
    """
    print(f"[READY_WORK_API] Starting ready work query with limit={limit}")
    ready_issues = dependency_service.get_ready_work(limit=limit)
    print(f"[READY_WORK_API] Found {len(ready_issues)} ready issues")
    for issue in ready_issues:
        print(f"[READY_WORK_API] Ready issue: {issue.id} - {issue.title} ({issue.status})")
    return [IssueResponse.from_orm(issue) for issue in ready_issues]

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