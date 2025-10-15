"""Issue service layer for business logic"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import json

from ..models import Issue, Event, Status, IssueType, EventType
from .id_generator import generate_issue_id, get_next_sequence_number
from .database import get_db_session


class IssueService:
    """Service class for issue operations"""
    
    def create_issue(
        self, 
        title: str,
        description: str = "",
        design: str = "",
        acceptance_criteria: str = "",
        notes: str = "",
        priority: int = 2,
        issue_type: IssueType = IssueType.TASK,
        assignee: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        actor: str = "system"
    ) -> Issue:
        """Create a new issue"""
        
        with get_db_session() as session:
            # Generate unique ID and sequence
            issue_id = generate_issue_id()
            sequence = get_next_sequence_number()
            
            # Create issue
            issue = Issue(
                id=issue_id,
                title=title,
                description=description,
                design=design,
                acceptance_criteria=acceptance_criteria,
                notes=notes,
                status=Status.OPEN,
                priority=priority,
                issue_type=issue_type,
                assignee=assignee,
                estimated_minutes=estimated_minutes,
                created_by=actor,
                sequence=sequence
            )
            
            session.add(issue)
            session.flush()  # Get the issue ID
            
            # Log creation event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.CREATED,
                actor=actor,
                new_value=json.dumps(issue.to_dict())
            )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get issue by ID"""
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if issue:
                session.expunge(issue)
            return issue
    
    def list_issues(
        self, 
        status: Optional[Status] = None,
        issue_type: Optional[IssueType] = None,
        assignee: Optional[str] = None,
        priority: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> tuple[List[Issue], int]:
        """List issues with filtering and pagination"""
        
        with get_db_session() as session:
            query = session.query(Issue)
            
            # Apply filters
            if status:
                query = query.filter(Issue.status == status)
            if issue_type:
                query = query.filter(Issue.issue_type == issue_type)
            if assignee:
                query = query.filter(Issue.assignee == assignee)
            if priority is not None:
                query = query.filter(Issue.priority == priority)
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        Issue.title.ilike(search_pattern),
                        Issue.description.ilike(search_pattern),
                        Issue.id.ilike(search_pattern)
                    )
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            issues = query.order_by(desc(Issue.created_at)).offset(offset).limit(limit).all()
            
            # Expunge issues to make them accessible outside session
            for issue in issues:
                session.expunge(issue)
            
            return issues, total
    
    def update_issue(
        self, 
        issue_id: str, 
        updates: Dict[str, Any], 
        actor: str = "system"
    ) -> Optional[Issue]:
        """Update an issue"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                return None
            
            # Store old values for audit
            old_values = issue.to_dict()
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(issue, field) and value is not None:
                    setattr(issue, field, value)
            
            # Update timestamp
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log update event
            new_values = issue.to_dict()
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.UPDATED,
                actor=actor,
                old_value=json.dumps(old_values),
                new_value=json.dumps(new_values)
            )
            
            # Log status change if status was updated
            if 'status' in updates and updates['status'] != old_values['status']:
                self._log_event(
                    session=session,
                    issue_id=issue.id,
                    event_type=EventType.STATUS_CHANGED,
                    actor=actor,
                    old_value=old_values['status'],
                    new_value=updates['status']
                )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def close_issue(self, issue_id: str, reason: str = "", actor: str = "system") -> Optional[Issue]:
        """Close an issue"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                return None
            
            old_status = issue.status
            issue.status = Status.CLOSED
            issue.closed_at = datetime.utcnow()
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log close event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.CLOSED,
                actor=actor,
                old_value=old_status.value if old_status else None,
                new_value=Status.CLOSED.value,
                comment=reason if reason else None
            )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def reopen_issue(self, issue_id: str, actor: str = "system") -> Optional[Issue]:
        """Reopen a closed issue"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue or issue.status != Status.CLOSED:
                return None
            
            issue.status = Status.OPEN
            issue.closed_at = None
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log reopen event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.REOPENED,
                actor=actor,
                old_value=Status.CLOSED.value,
                new_value=Status.OPEN.value
            )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def add_comment(self, issue_id: str, comment: str, actor: str = "system") -> bool:
        """Add a comment to an issue"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                return False
            
            # Log comment event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.COMMENTED,
                actor=actor,
                comment=comment
            )
            
            session.commit()
            return True
    
    def get_issue_events(self, issue_id: str, limit: int = 50) -> List[Event]:
        """Get events for an issue"""
        
        with get_db_session() as session:
            events = (
                session.query(Event)
                .filter(Event.issue_id == issue_id)
                .order_by(desc(Event.created_at))
                .limit(limit)
                .all()
            )
            
            # Make events accessible outside session
            for event in events:
                session.expunge(event)
            
            return events
    
    def _log_event(
        self,
        session: Session,
        issue_id: str,
        event_type: EventType,
        actor: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        comment: Optional[str] = None
    ):
        """Log an event (internal method)"""
        
        event = Event(
            issue_id=issue_id,
            event_type=event_type,
            actor=actor,
            old_value=old_value,
            new_value=new_value,
            comment=comment
        )
        session.add(event)


# Global service instance
issue_service = IssueService()