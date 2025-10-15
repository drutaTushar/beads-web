"""Event model for audit trail"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base, EventType

class Event(Base):
    """Event model for complete audit trail"""
    
    __tablename__ = "events"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Issue reference
    issue_id = Column(String(50), ForeignKey("issues.id"), nullable=False)
    
    # Event details
    event_type = Column(Enum(EventType), nullable=False)
    actor = Column(String(100), nullable=False)  # who made the change
    
    # Change tracking
    old_value = Column(Text, nullable=True)  # before state (JSON)
    new_value = Column(Text, nullable=True)  # after state (JSON)
    comment = Column(Text, nullable=True)    # for comment events
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    # Relationship
    issue = relationship("Issue", backref="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, issue='{self.issue_id}', type='{self.event_type.value}', actor='{self.actor}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }