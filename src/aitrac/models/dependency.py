"""Dependency model"""

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base, DependencyType

class Dependency(Base):
    """Dependency relationship between issues"""
    
    __tablename__ = "dependencies"
    
    # Composite primary key
    issue_id = Column(String(50), ForeignKey("issues.id"), primary_key=True)
    depends_on_id = Column(String(50), ForeignKey("issues.id"), primary_key=True)
    
    # Dependency type
    type = Column(Enum(DependencyType), nullable=False, default=DependencyType.BLOCKS)
    
    # Child ordering (for parent-child dependencies)
    child_order = Column(Integer, nullable=False, default=0)
    
    # Metadata
    created_by = Column(String(100), nullable=False, default="local")
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Relationships
    issue = relationship("Issue", foreign_keys=[issue_id], backref="dependencies")
    depends_on = relationship("Issue", foreign_keys=[depends_on_id], backref="dependents")
    
    # Ensure no duplicate dependencies
    __table_args__ = (
        UniqueConstraint('issue_id', 'depends_on_id', name='unique_dependency'),
    )
    
    def __repr__(self):
        return f"<Dependency(issue='{self.issue_id}', depends_on='{self.depends_on_id}', type='{self.type.value}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "issue_id": self.issue_id,
            "depends_on_id": self.depends_on_id,
            "type": self.type.value,
            "child_order": self.child_order,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }