"""Issues API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from ..storage.issue_service import issue_service
from ..models import Status, IssueType
from .schemas import (
    IssueCreate, 
    IssueUpdate, 
    IssueResponse, 
    IssueListResponse,
    CommentCreate,
    EventResponse,
    SuccessResponse
)

router = APIRouter()

@router.get("/", response_model=IssueListResponse)
async def list_issues(
    status: Optional[str] = Query(None, description="Filter by status"),
    issue_type: Optional[str] = Query(None, description="Filter by issue type"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    priority: Optional[int] = Query(None, ge=0, le=4, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search in title, description, or ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit")
):
    """List issues with filtering and pagination"""
    
    # Convert string filters to enums
    status_filter = None
    if status:
        try:
            status_filter = Status(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    issue_type_filter = None
    if issue_type:
        try:
            issue_type_filter = IssueType(issue_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid issue type: {issue_type}")
    
    issues, total = issue_service.list_issues(
        status=status_filter,
        issue_type=issue_type_filter,
        assignee=assignee,
        priority=priority,
        search=search,
        offset=offset,
        limit=limit
    )
    
    return IssueListResponse(
        issues=[IssueResponse.from_orm(issue) for issue in issues],
        total=total,
        offset=offset,
        limit=limit
    )

@router.get("/hierarchical")
async def get_hierarchical_issues():
    """Get issues organized in hierarchical structure"""
    from ..storage.dependency_service import dependency_service
    from ..storage.database import get_db_session
    from ..models.issue import Issue
    from ..models.dependency import Dependency, DependencyType
    from sqlalchemy.orm import joinedload
    
    with get_db_session() as session:
        # Get all issues with their children
        all_issues = session.query(Issue).all()
        
        # Get all parent-child relationships
        parent_child_deps = session.query(Dependency).filter(
            Dependency.type == DependencyType.PARENT_CHILD
        ).all()
        
        # Create mappings
        issue_map = {issue.id: issue for issue in all_issues}
        children_map = {}  # parent_id -> [child_issues]
        parent_map = {}    # child_id -> parent_id
        
        for dep in parent_child_deps:
            parent_id = dep.depends_on_id  # Parent
            child_id = dep.issue_id        # Child
            
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(issue_map[child_id])
            parent_map[child_id] = parent_id
        
        # Find root issues (epics and issues without parents)
        root_issues = []
        standalone_issues = []
        
        for issue in all_issues:
            if issue.id not in parent_map:  # No parent
                if issue.issue_type.value == 'epic':
                    root_issues.append(issue)
                else:
                    # Check if it has children
                    if issue.id in children_map:
                        root_issues.append(issue)
                    else:
                        standalone_issues.append(issue)
        
        # Build hierarchical structure
        def build_issue_tree(issue):
            children = children_map.get(issue.id, [])
            # Sort children by child_order if available, then by creation time
            children.sort(key=lambda x: (
                next((dep.child_order for dep in parent_child_deps if dep.issue_id == x.id), 999),
                x.created_at
            ))
            
            # Calculate status summary for children
            status_counts = {}
            for child in children:
                status = child.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "id": issue.id,
                "title": issue.title,
                "description": issue.description,
                "status": issue.status.value,
                "priority": issue.priority,
                "issue_type": issue.issue_type.value,
                "assignee": issue.assignee,
                "estimated_minutes": issue.estimated_minutes,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "children": [build_issue_tree(child) for child in children],
                "children_status_summary": status_counts
            }
        
        # Build the hierarchical structure
        hierarchical_issues = [build_issue_tree(issue) for issue in root_issues]
        standalone_issue_data = [
            {
                "id": issue.id,
                "title": issue.title,
                "description": issue.description,
                "status": issue.status.value,
                "priority": issue.priority,
                "issue_type": issue.issue_type.value,
                "assignee": issue.assignee,
                "estimated_minutes": issue.estimated_minutes,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "children": [],
                "children_status_summary": {}
            }
            for issue in standalone_issues
        ]
        
        # Expunge all objects to avoid DetachedInstanceError
        for issue in all_issues:
            session.expunge(issue)
        for dep in parent_child_deps:
            session.expunge(dep)
        
        return {
            "hierarchical_issues": hierarchical_issues,
            "standalone_issues": standalone_issue_data,
            "total_hierarchical": len(hierarchical_issues),
            "total_standalone": len(standalone_issues)
        }

@router.post("/", response_model=IssueResponse, status_code=201)
async def create_issue(issue_data: IssueCreate):
    """Create a new issue"""
    
    try:
        # Validate parent if provided
        if issue_data.parent_id:
            # Import dependency service here to avoid circular imports
            from ..storage.dependency_service import dependency_service
            
            # Check if parent exists
            parent_issue = issue_service.get_issue(issue_data.parent_id)
            if not parent_issue:
                raise HTTPException(status_code=400, detail=f"Parent issue {issue_data.parent_id} not found")
            
            # Create the issue first
            issue = issue_service.create_issue(
                title=issue_data.title,
                description=issue_data.description or "",
                design=issue_data.design or "",
                acceptance_criteria=issue_data.acceptance_criteria or "",
                notes=issue_data.notes or "",
                priority=issue_data.priority,
                issue_type=IssueType(issue_data.issue_type.value),
                assignee=issue_data.assignee,
                estimated_minutes=issue_data.estimated_minutes,
                actor="api"
            )
            
            # Then add the parent-child relationship
            try:
                from ..models import DependencyType
                dependency_service.add_dependency(
                    issue_id=issue.id,  # Child depends on parent
                    depends_on_id=issue_data.parent_id,  # Parent
                    dependency_type=DependencyType.PARENT_CHILD,
                    actor="api"
                )
            except ValueError as e:
                # If dependency creation fails, we might want to delete the issue
                # For now, just return the issue without the relationship and log error
                pass
                
            return IssueResponse.from_orm(issue)
        else:
            # Create issue without parent
            issue = issue_service.create_issue(
                title=issue_data.title,
                description=issue_data.description or "",
                design=issue_data.design or "",
                acceptance_criteria=issue_data.acceptance_criteria or "",
                notes=issue_data.notes or "",
                priority=issue_data.priority,
                issue_type=IssueType(issue_data.issue_type.value),
                assignee=issue_data.assignee,
                estimated_minutes=issue_data.estimated_minutes,
                actor="api"
            )
            return IssueResponse.from_orm(issue)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")

@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(issue_id: str):
    """Get issue by ID"""
    
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    return IssueResponse.from_orm(issue)

@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(issue_id: str, issue_data: IssueUpdate):
    """Update issue"""
    
    # Check if issue exists
    existing_issue = issue_service.get_issue(issue_id)
    if not existing_issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    # Build updates dictionary (only include non-None fields)
    updates = {}
    for field, value in issue_data.dict(exclude_unset=True).items():
        if value is not None:
            # Convert enum values
            if field == "status":
                updates[field] = Status(value)
            elif field == "issue_type":
                updates[field] = IssueType(value)
            else:
                updates[field] = value
    
    if not updates:
        return IssueResponse.from_orm(existing_issue)
    
    try:
        updated_issue = issue_service.update_issue(issue_id, updates, actor="api")
        return IssueResponse.from_orm(updated_issue)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update issue: {str(e)}")

@router.delete("/{issue_id}", response_model=SuccessResponse)
async def close_issue(
    issue_id: str, 
    reason: str = Query("", description="Reason for closing the issue")
):
    """Close issue"""
    
    issue = issue_service.close_issue(issue_id, reason=reason, actor="api")
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    return SuccessResponse(
        message=f"Issue {issue_id} closed successfully",
        id=issue_id
    )

@router.post("/{issue_id}/reopen", response_model=IssueResponse)
async def reopen_issue(issue_id: str):
    """Reopen a closed issue"""
    
    issue = issue_service.reopen_issue(issue_id, actor="api")
    if not issue:
        raise HTTPException(
            status_code=400, 
            detail=f"Issue {issue_id} not found or not closed"
        )
    
    return IssueResponse.from_orm(issue)

@router.post("/{issue_id}/start", response_model=IssueResponse)
async def start_issue(issue_id: str):
    """Start working on an issue (mark as in_progress)"""
    
    issue = issue_service.start_issue(issue_id, actor="api")
    if not issue:
        raise HTTPException(
            status_code=400, 
            detail=f"Issue {issue_id} not found or cannot be started"
        )
    
    return IssueResponse.from_orm(issue)

@router.post("/{issue_id}/block", response_model=IssueResponse)
async def block_issue(issue_id: str, reason: str = Query("", description="Reason for blocking the issue")):
    """Block an issue"""
    
    issue = issue_service.block_issue(issue_id, reason=reason, actor="api")
    if not issue:
        raise HTTPException(
            status_code=400, 
            detail=f"Issue {issue_id} not found or cannot be blocked"
        )
    
    return IssueResponse.from_orm(issue)

@router.post("/{issue_id}/unblock", response_model=IssueResponse)
async def unblock_issue(issue_id: str):
    """Unblock an issue (return to open status)"""
    
    issue = issue_service.unblock_issue(issue_id, actor="api")
    if not issue:
        raise HTTPException(
            status_code=400, 
            detail=f"Issue {issue_id} not found or not blocked"
        )
    
    return IssueResponse.from_orm(issue)

@router.post("/{issue_id}/comments", response_model=SuccessResponse, status_code=201)
async def add_comment(issue_id: str, comment_data: CommentCreate):
    """Add comment to issue"""
    
    success = issue_service.add_comment(
        issue_id=issue_id,
        comment=comment_data.comment,
        actor="api"
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    return SuccessResponse(
        message="Comment added successfully",
        id=issue_id
    )

@router.get("/{issue_id}/events", response_model=List[EventResponse])
async def get_issue_events(
    issue_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events to return")
):
    """Get events/history for an issue"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    events = issue_service.get_issue_events(issue_id, limit=limit)
    return [EventResponse.from_orm(event) for event in events]

@router.delete("/{issue_id}/permanent", response_model=SuccessResponse)
async def delete_issue_permanent(issue_id: str):
    """Permanently delete an issue and all its data
    
    This is different from closing an issue. The issue will be completely removed
    from the database. This action cannot be undone.
    
    Requirements:
    - Issue must have no children
    - Issue must have no other issues depending on it
    """
    
    try:
        print(f"[DELETE_API] Attempting to permanently delete issue {issue_id}")
        
        success = issue_service.delete_issue(issue_id, actor="api")
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
        
        print(f"[DELETE_API] Successfully deleted issue {issue_id}")
        
        return SuccessResponse(
            message=f"Issue {issue_id} permanently deleted",
            id=issue_id
        )
        
    except ValueError as e:
        # This will be raised if issue has children or dependents
        print(f"[DELETE_API] Delete validation failed for {issue_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[DELETE_API] Unexpected error deleting {issue_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete issue: {str(e)}")

@router.post("/{issue_id}/events", response_model=SuccessResponse, status_code=201)
async def add_issue_event(issue_id: str, event_data: dict):
    """Add an event to an issue (primarily for comments)"""
    
    # Check if issue exists
    issue = issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    
    # Handle comment events
    if event_data.get("event_type") == "comment":
        comment = event_data.get("data", {}).get("comment")
        if not comment:
            raise HTTPException(status_code=400, detail="Comment data is required")
        
        success = issue_service.add_comment(
            issue_id=issue_id,
            comment=comment,
            actor="api"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add comment")
        
        return SuccessResponse(
            message="Comment added successfully",
            id=issue_id
        )
    
    # For other event types, return an error for now
    raise HTTPException(
        status_code=400, 
        detail=f"Unsupported event type: {event_data.get('event_type')}"
    )