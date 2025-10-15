"""Dependencies API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any

from ..storage.dependency_service import dependency_service
from ..storage.issue_service import issue_service
from ..models import DependencyType
from .schemas import (
    DependencyCreate,
    DependencyResponse,
    SuccessResponse
)

router = APIRouter()


@router.post("/{issue_id}/dependencies", response_model=DependencyResponse, status_code=201)
async def add_dependency(issue_id: str, dependency_data: DependencyCreate):
    """Add a dependency to an issue"""
    
    try:
        # Convert enum to model enum
        dep_type = DependencyType(dependency_data.type.value)
        
        dependency = dependency_service.add_dependency(
            issue_id=issue_id,
            depends_on_id=dependency_data.depends_on_id,
            dependency_type=dep_type,
            actor="api"
        )
        
        if not dependency:
            raise HTTPException(
                status_code=404, 
                detail=f"Issue {issue_id} or dependency target {dependency_data.depends_on_id} not found"
            )
        
        return DependencyResponse.from_orm(dependency)
        
    except ValueError as e:
        if "circular dependency" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid dependency type: {dependency_data.type.value}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add dependency: {str(e)}")


@router.delete("/{issue_id}/dependencies/{depends_on_id}", response_model=SuccessResponse)
async def remove_dependency(
    issue_id: str, 
    depends_on_id: str,
    dependency_type: Optional[str] = Query(None, description="Specific dependency type to remove")
):
    """Remove a dependency from an issue"""
    
    dep_type = None
    if dependency_type:
        try:
            dep_type = DependencyType(dependency_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid dependency type: {dependency_type}")
    
    success = dependency_service.remove_dependency(
        issue_id=issue_id,
        depends_on_id=depends_on_id,
        dependency_type=dep_type,
        actor="api"
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail=f"Dependency from {issue_id} to {depends_on_id} not found"
        )
    
    return SuccessResponse(
        message=f"Dependency removed successfully",
        id=f"{issue_id}->{depends_on_id}"
    )


@router.get("/{issue_id}/dependencies", response_model=List[DependencyResponse])
async def get_dependencies(issue_id: str):
    """Get all dependencies for an issue (what this issue depends on)"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    dependencies = dependency_service.get_dependencies(issue_id)
    return [DependencyResponse.from_orm(dep) for dep in dependencies]


@router.get("/{issue_id}/dependents", response_model=List[DependencyResponse])
async def get_dependents(issue_id: str):
    """Get all dependents of an issue (what depends on this issue)"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    dependents = dependency_service.get_dependents(issue_id)
    return [DependencyResponse.from_orm(dep) for dep in dependents]


@router.get("/{issue_id}/tree", response_model=Dict[str, Any])
async def get_dependency_tree(
    issue_id: str,
    max_depth: int = Query(10, ge=1, le=50, description="Maximum tree depth to traverse")
):
    """Get the full dependency tree for an issue"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    tree = dependency_service.get_dependency_tree(issue_id, max_depth=max_depth)
    return tree


@router.get("/{issue_id}/why-blocked", response_model=Dict[str, Any])
async def why_blocked(issue_id: str):
    """Analyze why an issue is blocked (find shortest path to open dependency)"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    blocking_path = dependency_service.find_blocking_path(issue_id)
    
    if not blocking_path:
        return {
            "blocked": False,
            "message": "Issue is not blocked by dependencies",
            "blocking_path": []
        }
    
    return {
        "blocked": True,
        "message": f"Issue is blocked by {len(blocking_path)} dependency chain",
        "blocking_path": blocking_path,
        "blocking_issue": blocking_path[-1] if blocking_path else None
    }