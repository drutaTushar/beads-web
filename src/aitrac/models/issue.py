"""Issue model"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from .base import Base, Status, IssueType

class Issue(Base):
    """Issue model with dependency support"""
    
    __tablename__ = "issues"
    
    # Primary fields
    id = Column(String(50), primary_key=True)  # e.g., "proj-a7k2"
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    design = Column(Text, default="")
    acceptance_criteria = Column(Text, default="")
    notes = Column(Text, default="")
    
    # Status and type
    status = Column(Enum(Status), nullable=False, default=Status.OPEN)
    priority = Column(Integer, nullable=False, default=2)  # 0 (highest) to 4 (lowest)
    issue_type = Column(Enum(IssueType), nullable=False, default=IssueType.TASK)
    
    # Optional fields
    assignee = Column(String(100), nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    
    # Metadata for sync collision resolution
    created_by = Column(String(100), nullable=False, default="local")  # source identifier
    sequence = Column(Integer, nullable=False)  # auto-increment for collision resolution
    markdown_id = Column(String(100), nullable=True)  # logical ID from markdown import
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Issue(id='{self.id}', title='{self.title[:50]}...', status='{self.status.value}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "design": self.design,
            "acceptance_criteria": self.acceptance_criteria,
            "notes": self.notes,
            "status": self.status.value,
            "priority": self.priority,
            "issue_type": self.issue_type.value,
            "assignee": self.assignee,
            "estimated_minutes": self.estimated_minutes,
            "created_by": self.created_by,
            "sequence": self.sequence,
            "markdown_id": self.markdown_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }