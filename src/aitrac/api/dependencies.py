"""Dependencies API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any

from ..storage.dependency_service import dependency_service
from ..storage.issue_service import issue_service
from ..models import DependencyType
from .schemas import (
    DependencyCreate,
    DependencyResponse,
    ChildIssueResponse,
    IssueResponse,
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


@router.post("/{issue_id}/children/{child_id}", response_model=DependencyResponse, status_code=201)
async def add_child(issue_id: str, child_id: str):
    """Add a child issue (convenience endpoint for parent-child dependency)
    
    Creates a parent-child dependency where the child_id issue depends on the issue_id issue.
    This represents the hierarchy where parent issues must be completed before children.
    """
    
    try:
        # Convert to parent-child dependency type
        dep_type = DependencyType.PARENT_CHILD
        
        dependency = dependency_service.add_dependency(
            issue_id=child_id,  # Child depends on parent
            depends_on_id=issue_id,  # Parent
            dependency_type=dep_type,
            actor="api"
        )
        
        if not dependency:
            raise HTTPException(
                status_code=404, 
                detail=f"Issue {issue_id} (parent) or {child_id} (child) not found"
            )
        
        return DependencyResponse.from_orm(dependency)
        
    except ValueError as e:
        if "circular dependency" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to add child: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add child: {str(e)}")


@router.post("/{issue_id}/blockers/{blocker_id}", response_model=DependencyResponse, status_code=201)
async def add_blocker(issue_id: str, blocker_id: str):
    """Add a blocker issue (convenience endpoint for blocking dependency)
    
    Creates a blocking dependency where the issue_id issue is blocked by the blocker_id issue.
    This represents cases where one issue cannot start until another is completed.
    """
    
    try:
        # Convert to blocking dependency type
        dep_type = DependencyType.BLOCKS
        
        dependency = dependency_service.add_dependency(
            issue_id=issue_id,  # Issue being blocked
            depends_on_id=blocker_id,  # Blocker
            dependency_type=dep_type,
            actor="api"
        )
        
        if not dependency:
            raise HTTPException(
                status_code=404, 
                detail=f"Issue {issue_id} or blocker {blocker_id} not found"
            )
        
        return DependencyResponse.from_orm(dependency)
        
    except ValueError as e:
        if "circular dependency" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to add blocker: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add blocker: {str(e)}")


@router.get("/{issue_id}/children", response_model=List[ChildIssueResponse])
async def get_children(issue_id: str):
    """Get all child issues (issues that depend on this issue with parent-child relationship) ordered by child_order"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    # Get children ordered by child_order
    children_deps = dependency_service.get_children_ordered(issue_id)
    
    # Get full issue details for each child
    children_with_details = []
    for dep in children_deps:
        child_issue = issue_service.get_issue(dep.issue_id)
        if child_issue:
            # Create combined response with dependency and issue info
            child_response = {
                "issue_id": dep.issue_id,
                "depends_on_id": dep.depends_on_id,
                "type": dep.type,
                "child_order": dep.child_order,
                "created_by": dep.created_by,
                "created_at": dep.created_at,
                "title": child_issue.title,
                "description": child_issue.description,
                "status": child_issue.status,
                "priority": child_issue.priority,
                "issue_type": child_issue.issue_type
            }
            children_with_details.append(ChildIssueResponse(**child_response))
    
    return children_with_details


@router.delete("/{issue_id}/children/{child_id}", response_model=SuccessResponse)
async def remove_child(issue_id: str, child_id: str):
    """Remove a child issue (convenience endpoint)"""
    
    success = dependency_service.remove_dependency(
        issue_id=child_id,  # Child was depending on parent
        depends_on_id=issue_id,  # Parent
        dependency_type=DependencyType.PARENT_CHILD,
        actor="api"
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail=f"Parent-child dependency from {issue_id} to {child_id} not found"
        )
    
    return SuccessResponse(
        message=f"Child relationship removed successfully",
        id=f"{issue_id}->{child_id}"
    )


@router.get("/{issue_id}/eligible-parents", response_model=List[IssueResponse])
async def get_eligible_parents(issue_id: str):
    """Get issues that can be parents of this issue with hierarchy validation"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    eligible_parents = dependency_service.get_eligible_parents(issue_id)
    return [IssueResponse.from_orm(parent) for parent in eligible_parents]


@router.get("/{issue_id}/eligible-children", response_model=List[IssueResponse])
async def get_eligible_children(issue_id: str):
    """Get issues that can be children of this issue with hierarchy validation"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    eligible_children = dependency_service.get_eligible_children(issue_id)
    return [IssueResponse.from_orm(child) for child in eligible_children]


@router.post("/{issue_id}/children/reorder", response_model=SuccessResponse)
async def reorder_children(issue_id: str, ordered_child_ids: List[str]):
    """Reorder children of a parent issue"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    success = dependency_service.reorder_children(
        parent_id=issue_id,
        ordered_child_ids=ordered_child_ids,
        actor="api"
    )
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to reorder children for issue {issue_id}"
        )
    
    return SuccessResponse(
        message=f"Children reordered successfully",
        id=issue_id
    )