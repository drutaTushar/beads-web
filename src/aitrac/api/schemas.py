"""Pydantic schemas for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums for API
class StatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"

class IssueTypeEnum(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    CHORE = "chore"

class DependencyTypeEnum(str, Enum):
    BLOCKS = "blocks"
    RELATED = "related"
    PARENT_CHILD = "parent-child"

class EventTypeEnum(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"
    CLOSED = "closed"
    REOPENED = "reopened"
    DEPENDENCY_ADDED = "dependency_added"
    DEPENDENCY_REMOVED = "dependency_removed"
    LABEL_ADDED = "label_added"
    LABEL_REMOVED = "label_removed"

# Issue schemas
class IssueBase(BaseModel):
    title: str = Field(..., max_length=500, description="Issue title")
    description: Optional[str] = Field("", description="Problem statement (what/why)")
    design: Optional[str] = Field("", description="Solution design (how)")
    acceptance_criteria: Optional[str] = Field("", description="Definition of done")
    notes: Optional[str] = Field("", description="Working notes")
    priority: int = Field(2, ge=0, le=4, description="Priority: 0 (highest) to 4 (lowest)")
    issue_type: IssueTypeEnum = Field(IssueTypeEnum.TASK, description="Issue type")
    assignee: Optional[str] = Field(None, max_length=100, description="Assignee")
    estimated_minutes: Optional[int] = Field(None, ge=0, description="Estimated time in minutes")

class IssueCreate(IssueBase):
    """Schema for creating an issue"""
    parent_id: Optional[str] = Field(None, description="Parent issue ID for parent-child relationship")

class IssueUpdate(BaseModel):
    """Schema for updating an issue"""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    design: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[StatusEnum] = None
    priority: Optional[int] = Field(None, ge=0, le=4)
    issue_type: Optional[IssueTypeEnum] = None
    assignee: Optional[str] = Field(None, max_length=100)
    estimated_minutes: Optional[int] = Field(None, ge=0)

class IssueResponse(IssueBase):
    """Schema for issue responses"""
    id: str
    status: StatusEnum
    created_by: str
    sequence: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IssueListResponse(BaseModel):
    """Schema for issue list responses"""
    issues: List[IssueResponse]
    total: int
    offset: int
    limit: int

# Dependency schemas
class DependencyCreate(BaseModel):
    """Schema for creating a dependency"""
    depends_on_id: str = Field(..., description="ID of the issue this depends on")
    type: DependencyTypeEnum = Field(DependencyTypeEnum.BLOCKS, description="Dependency type")

class DependencyResponse(BaseModel):
    """Schema for dependency responses"""
    issue_id: str
    depends_on_id: str
    type: DependencyTypeEnum
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True

# Event schemas
class EventResponse(BaseModel):
    """Schema for event responses"""
    id: int
    issue_id: str
    event_type: EventTypeEnum
    actor: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    """Schema for creating comments"""
    comment: str = Field(..., min_length=1, description="Comment text")

# Label schemas
class LabelCreate(BaseModel):
    """Schema for creating labels"""
    label: str = Field(..., max_length=100, description="Label name")

class LabelResponse(BaseModel):
    """Schema for label responses"""
    issue_id: str
    label: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True

# Common response schemas
class SuccessResponse(BaseModel):
    """Schema for success responses"""
    message: str
    id: Optional[str] = None

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None

class ChildIssueResponse(BaseModel):
    """Schema for child issue responses with full issue details"""
    issue_id: str
    depends_on_id: str
    type: DependencyTypeEnum
    child_order: int
    created_by: str
    created_at: datetime
    # Issue details
    title: str
    description: Optional[str] = None
    status: StatusEnum
    priority: int
    issue_type: IssueTypeEnum
    
    class Config:
        from_attributes = True