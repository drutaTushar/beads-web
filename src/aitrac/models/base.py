"""Base SQLAlchemy models and configuration"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from typing import Optional

Base = declarative_base()

class Status(enum.Enum):
    """Issue status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"

class IssueType(enum.Enum):
    """Issue type enumeration"""
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    CHORE = "chore"

class DependencyType(enum.Enum):
    """Dependency type enumeration"""
    BLOCKS = "blocks"
    RELATED = "related"
    PARENT_CHILD = "parent-child"

class EventType(enum.Enum):
    """Event type enumeration"""
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