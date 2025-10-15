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