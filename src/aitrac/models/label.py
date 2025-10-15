"""Label model for issue tagging"""

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class Label(Base):
    """Label model for issue tagging"""
    
    __tablename__ = "labels"
    
    # Composite primary key
    issue_id = Column(String(50), ForeignKey("issues.id"), primary_key=True)
    label = Column(String(100), primary_key=True)
    
    # Metadata
    created_by = Column(String(100), nullable=False, default="local")
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Relationship
    issue = relationship("Issue", backref="labels")
    
    # Ensure no duplicate labels per issue
    __table_args__ = (
        UniqueConstraint('issue_id', 'label', name='unique_issue_label'),
    )
    
    def __repr__(self):
        return f"<Label(issue='{self.issue_id}', label='{self.label}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "issue_id": self.issue_id,
            "label": self.label,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }