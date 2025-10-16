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
    
    def get_issue_by_markdown_id(self, markdown_id: str) -> Optional[Issue]:
        """Get issue by markdown_id"""
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.markdown_id == markdown_id).first()
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
                # Ensure both old and new values are strings for event logging
                old_status_value = old_values['status'] if isinstance(old_values['status'], str) else old_values['status'].value
                new_status_value = updates['status'].value if hasattr(updates['status'], 'value') else str(updates['status'])
                
                self._log_event(
                    session=session,
                    issue_id=issue.id,
                    event_type=EventType.STATUS_CHANGED,
                    actor=actor,
                    old_value=old_status_value,
                    new_value=new_status_value
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
    
    def start_issue(self, issue_id: str, actor: str = "system") -> Optional[Issue]:
        """Start working on an issue (mark as in_progress)"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue or issue.status not in [Status.OPEN, Status.BLOCKED]:
                return None
            
            old_status = issue.status
            issue.status = Status.IN_PROGRESS
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log start event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.STATUS_CHANGED,
                actor=actor,
                old_value=old_status.value,
                new_value=Status.IN_PROGRESS.value
            )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def block_issue(self, issue_id: str, reason: str = "", actor: str = "system") -> Optional[Issue]:
        """Block an issue"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue or issue.status == Status.CLOSED:
                return None
            
            old_status = issue.status
            issue.status = Status.BLOCKED
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log block event with reason
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.STATUS_CHANGED,
                actor=actor,
                old_value=old_status.value,
                new_value=Status.BLOCKED.value,
                comment=f"Issue blocked: {reason}" if reason else "Issue blocked"
            )
            
            session.commit()
            session.refresh(issue)
            # Make issue accessible outside session
            session.expunge(issue)
            return issue
    
    def unblock_issue(self, issue_id: str, actor: str = "system") -> Optional[Issue]:
        """Unblock an issue (return to open status)"""
        
        with get_db_session() as session:
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue or issue.status != Status.BLOCKED:
                return None
            
            issue.status = Status.OPEN
            issue.updated_at = datetime.utcnow()
            
            session.flush()
            
            # Log unblock event
            self._log_event(
                session=session,
                issue_id=issue.id,
                event_type=EventType.STATUS_CHANGED,
                actor=actor,
                old_value=Status.BLOCKED.value,
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
    
    def delete_issue(self, issue_id: str, actor: str = "system") -> bool:
        """Delete an issue permanently
        
        Returns True if deleted successfully, False if issue not found.
        Raises ValueError if issue has children or dependencies.
        """
        
        with get_db_session() as session:
            # First check if issue exists
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                return False
            
            print(f"[DELETE_ISSUE] Attempting to delete issue {issue_id} ({issue.title})")
            
            # Check if issue has children (parent-child dependencies where this issue is the parent)
            from ..models import Dependency, DependencyType
            children = (
                session.query(Dependency)
                .filter(
                    and_(
                        Dependency.depends_on_id == issue_id,
                        Dependency.type == DependencyType.PARENT_CHILD
                    )
                )
                .all()
            )
            
            if children:
                child_ids = [dep.issue_id for dep in children]
                print(f"[DELETE_ISSUE] Issue {issue_id} has {len(children)} children: {child_ids}")
                raise ValueError(f"Cannot delete issue {issue_id}: it has {len(children)} child issues. Remove children first.")
            
            # Check if issue has any dependencies pointing to it
            dependents = (
                session.query(Dependency)
                .filter(Dependency.depends_on_id == issue_id)
                .all()
            )
            
            if dependents:
                dependent_ids = [dep.issue_id for dep in dependents]
                print(f"[DELETE_ISSUE] Issue {issue_id} has {len(dependents)} dependents: {dependent_ids}")
                raise ValueError(f"Cannot delete issue {issue_id}: {len(dependents)} other issues depend on it. Remove dependencies first.")
            
            # Delete all dependencies where this issue is the dependent
            dependencies_from_issue = (
                session.query(Dependency)
                .filter(Dependency.issue_id == issue_id)
                .all()
            )
            
            print(f"[DELETE_ISSUE] Deleting {len(dependencies_from_issue)} dependencies from issue {issue_id}")
            for dep in dependencies_from_issue:
                session.delete(dep)
            
            # Delete all events related to this issue
            events = session.query(Event).filter(Event.issue_id == issue_id).all()
            print(f"[DELETE_ISSUE] Deleting {len(events)} events for issue {issue_id}")
            for event in events:
                session.delete(event)
            
            # Finally delete the issue itself
            print(f"[DELETE_ISSUE] Deleting issue {issue_id}")
            session.delete(issue)
            
            # Log the deletion (note: this will be deleted with the issue, but good for audit trail)
            self._log_event(
                session, issue_id, EventType.CREATED, actor,  # Using CREATED as placeholder
                old_value=f"Issue '{issue.title}' deleted",
                comment="Issue permanently deleted"
            )
            
            session.commit()
            print(f"[DELETE_ISSUE] Successfully deleted issue {issue_id}")
            return True


# Global service instance
issue_service = IssueService()