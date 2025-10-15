"""Dependency service layer for business logic"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import json

from ..models import Issue, Dependency, Event, DependencyType, EventType
from .database import get_db_session


class DependencyService:
    """Service class for dependency operations"""
    
    def add_dependency(
        self, 
        issue_id: str, 
        depends_on_id: str, 
        dependency_type: DependencyType = DependencyType.BLOCKS,
        actor: str = "system"
    ) -> Optional[Dependency]:
        """Add a dependency between two issues"""
        
        with get_db_session() as session:
            # Check if both issues exist
            issue = session.query(Issue).filter(Issue.id == issue_id).first()
            depends_on_issue = session.query(Issue).filter(Issue.id == depends_on_id).first()
            
            if not issue or not depends_on_issue:
                return None
            
            # Check if dependency already exists
            existing = session.query(Dependency).filter(
                and_(
                    Dependency.issue_id == issue_id,
                    Dependency.depends_on_id == depends_on_id,
                    Dependency.type == dependency_type
                )
            ).first()
            
            if existing:
                session.expunge(existing)
                return existing
            
            # Check for circular dependencies
            if self._would_create_cycle(session, issue_id, depends_on_id):
                raise ValueError(f"Adding dependency would create a circular dependency")
            
            # Create dependency
            dependency = Dependency(
                issue_id=issue_id,
                depends_on_id=depends_on_id,
                type=dependency_type,
                created_by=actor
            )
            
            session.add(dependency)
            session.flush()
            
            # Log dependency event
            self._log_dependency_event(
                session=session,
                issue_id=issue_id,
                event_type=EventType.DEPENDENCY_ADDED,
                actor=actor,
                dependency_id=depends_on_id,
                dependency_type=dependency_type
            )
            
            session.commit()
            session.refresh(dependency)
            session.expunge(dependency)
            return dependency
    
    def remove_dependency(
        self, 
        issue_id: str, 
        depends_on_id: str, 
        dependency_type: Optional[DependencyType] = None,
        actor: str = "system"
    ) -> bool:
        """Remove a dependency between two issues"""
        
        with get_db_session() as session:
            query = session.query(Dependency).filter(
                and_(
                    Dependency.issue_id == issue_id,
                    Dependency.depends_on_id == depends_on_id
                )
            )
            
            if dependency_type:
                query = query.filter(Dependency.type == dependency_type)
            
            dependency = query.first()
            if not dependency:
                return False
            
            # Log dependency removal event
            self._log_dependency_event(
                session=session,
                issue_id=issue_id,
                event_type=EventType.DEPENDENCY_REMOVED,
                actor=actor,
                dependency_id=depends_on_id,
                dependency_type=dependency.type
            )
            
            session.delete(dependency)
            session.commit()
            return True
    
    def get_dependencies(self, issue_id: str) -> List[Dependency]:
        """Get all dependencies for an issue (what this issue depends on)"""
        
        with get_db_session() as session:
            dependencies = (
                session.query(Dependency)
                .filter(Dependency.issue_id == issue_id)
                .order_by(Dependency.created_at)
                .all()
            )
            
            # Expunge to make accessible outside session
            for dep in dependencies:
                session.expunge(dep)
            
            return dependencies
    
    def get_dependents(self, issue_id: str) -> List[Dependency]:
        """Get all dependents of an issue (what depends on this issue)"""
        
        with get_db_session() as session:
            dependents = (
                session.query(Dependency)
                .filter(Dependency.depends_on_id == issue_id)
                .order_by(Dependency.created_at)
                .all()
            )
            
            # Expunge to make accessible outside session
            for dep in dependents:
                session.expunge(dep)
            
            return dependents
    
    def get_dependency_tree(self, issue_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """Get the full dependency tree for an issue"""
        
        def build_tree(current_id: str, depth: int = 0, visited: Optional[set] = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()
            
            if depth >= max_depth or current_id in visited:
                return {"issue_id": current_id, "dependencies": [], "circular": current_id in visited}
            
            visited.add(current_id)
            
            dependencies = self.get_dependencies(current_id)
            tree = {
                "issue_id": current_id,
                "dependencies": [],
                "circular": False
            }
            
            for dep in dependencies:
                subtree = build_tree(dep.depends_on_id, depth + 1, visited.copy())
                subtree["type"] = dep.type.value
                tree["dependencies"].append(subtree)
            
            return tree
        
        return build_tree(issue_id)
    
    def find_blocking_path(self, issue_id: str) -> List[str]:
        """Find the shortest path to an open blocking dependency"""
        
        with get_db_session() as session:
            visited = set()
            queue = [(issue_id, [])]
            
            while queue:
                current_id, path = queue.pop(0)
                
                if current_id in visited:
                    continue
                visited.add(current_id)
                
                # Get current issue status
                issue = session.query(Issue).filter(Issue.id == current_id).first()
                if not issue:
                    continue
                
                # If this issue is open and we're not at the root, we found a blocker
                if issue.status.value == "open" and path:
                    return path + [current_id]
                
                # If this issue is closed, continue exploring dependencies
                if issue.status.value == "closed":
                    continue
                
                # Get dependencies and add to queue
                dependencies = (
                    session.query(Dependency)
                    .filter(
                        and_(
                            Dependency.issue_id == current_id,
                            Dependency.type.in_([DependencyType.BLOCKS, DependencyType.PARENT_CHILD])
                        )
                    )
                    .all()
                )
                
                for dep in dependencies:
                    if dep.depends_on_id not in visited:
                        queue.append((dep.depends_on_id, path + [current_id]))
            
            return []  # No blocking path found
    
    def _would_create_cycle(self, session: Session, from_id: str, to_id: str) -> bool:
        """Check if adding a dependency would create a circular dependency"""
        
        # Start from to_id and see if we can reach from_id
        visited = set()
        queue = [to_id]
        
        while queue:
            current_id = queue.pop(0)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_id == from_id:
                return True
            
            # Get all dependencies of current issue
            dependencies = (
                session.query(Dependency)
                .filter(Dependency.issue_id == current_id)
                .all()
            )
            
            for dep in dependencies:
                if dep.depends_on_id not in visited:
                    queue.append(dep.depends_on_id)
        
        return False
    
    def _log_dependency_event(
        self,
        session: Session,
        issue_id: str,
        event_type: EventType,
        actor: str,
        dependency_id: str,
        dependency_type: DependencyType
    ):
        """Log a dependency-related event"""
        
        event_data = {
            "dependency_id": dependency_id,
            "dependency_type": dependency_type.value
        }
        
        event = Event(
            issue_id=issue_id,
            event_type=event_type,
            actor=actor,
            new_value=json.dumps(event_data)
        )
        session.add(event)


# Global service instance
dependency_service = DependencyService()