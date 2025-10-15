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
            
            # Determine child_order for parent-child dependencies
            child_order = 0
            if dependency_type == DependencyType.PARENT_CHILD:
                # Get the highest order for existing children of this parent
                max_order = session.query(Dependency.child_order).filter(
                    and_(
                        Dependency.depends_on_id == depends_on_id,
                        Dependency.type == DependencyType.PARENT_CHILD
                    )
                ).order_by(desc(Dependency.child_order)).first()
                
                child_order = (max_order[0] + 1) if max_order else 0
            
            # Create dependency
            dependency = Dependency(
                issue_id=issue_id,
                depends_on_id=depends_on_id,
                type=dependency_type,
                child_order=child_order,
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
            
            # Get issue details
            with get_db_session() as session:
                issue = session.query(Issue).filter(Issue.id == current_id).first()
                if issue:
                    # Extract values while session is active
                    title = issue.title
                    status = issue.status.value
                    priority = issue.priority
                    issue_type = issue.issue_type.value
                    session.expunge(issue)
                else:
                    title = f"Issue {current_id}"
                    status = "unknown"
                    priority = 2
                    issue_type = "task"
            
            dependencies = self.get_dependencies(current_id)
            tree = {
                "issue_id": current_id,
                "id": current_id,  # Add id field for compatibility
                "title": title,
                "status": status,
                "priority": priority,
                "issue_type": issue_type,
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
    
    def get_ready_work(self, limit: int = 50) -> List[Issue]:
        """Get ready work - issues that can be started (Ready() algorithm)
        
        An issue is ready if:
        1. It is open (not closed)
        2. All its blocking dependencies are closed/completed
        3. All its parent issues are also not blocked
        """
        
        with get_db_session() as session:
            from .issue_service import issue_service
            
            # Get all open issues
            open_issues = (
                session.query(Issue)
                .filter(Issue.status.in_(["open", "in_progress"]))
                .all()
            )
            
            ready_issues = []
            
            for issue in open_issues:
                if self._is_issue_ready(session, issue):
                    ready_issues.append(issue)
                    if len(ready_issues) >= limit:
                        break
            
            # Sort by priority (0 highest, 4 lowest)
            ready_issues.sort(key=lambda x: x.priority)
            
            # Expunge to make accessible outside session
            for issue in ready_issues:
                session.expunge(issue)
            
            return ready_issues
    
    def _is_issue_ready(self, session: Session, issue: Issue) -> bool:
        """Check if an issue is ready to start"""
        
        # Get all dependencies for this issue
        dependencies = (
            session.query(Dependency)
            .filter(Dependency.issue_id == issue.id)
            .all()
        )
        
        for dep in dependencies:
            # Get the dependent issue
            dependent_issue = (
                session.query(Issue)
                .filter(Issue.id == dep.depends_on_id)
                .first()
            )
            
            if not dependent_issue:
                continue
                
            # If dependency is not closed, this issue is not ready
            if dependent_issue.status != "closed":
                return False
                
            # For parent-child relationships, check recursively that parent is not blocked
            if dep.type == DependencyType.PARENT_CHILD:
                if not self._is_issue_ready(session, dependent_issue):
                    return False
        
        return True

    def get_eligible_parents(self, issue_id: str) -> List[Issue]:
        """Get issues that can be parents of this issue with hierarchy validation"""
        
        with get_db_session() as session:
            current_issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not current_issue:
                return []
            
            # Get all issues except current one and its descendants
            all_issues = (
                session.query(Issue)
                .filter(Issue.id != issue_id)
                .all()
            )
            
            eligible_parents = []
            
            for potential_parent in all_issues:
                # Check if this would create a cycle
                if self._would_create_cycle(session, potential_parent.id, issue_id):
                    continue
                
                # Check if potential parent already has a parent (prevent deep nesting)
                existing_parent = session.query(Dependency).filter(
                    and_(
                        Dependency.issue_id == potential_parent.id,
                        Dependency.type == DependencyType.PARENT_CHILD
                    )
                ).first()
                
                # Skip if potential parent already has a parent and it's not the current issue
                if existing_parent and existing_parent.depends_on_id != issue_id:
                    continue
                
                # Apply issue type hierarchy rules
                if self._is_valid_parent_child_type(potential_parent.issue_type, current_issue.issue_type):
                    eligible_parents.append(potential_parent)
            
            # Expunge to make accessible outside session
            for issue in eligible_parents:
                session.expunge(issue)
            
            return eligible_parents

    def get_eligible_children(self, issue_id: str) -> List[Issue]:
        """Get issues that can be children of this issue with hierarchy validation"""
        
        with get_db_session() as session:
            current_issue = session.query(Issue).filter(Issue.id == issue_id).first()
            if not current_issue:
                return []
            
            # Get all issues except current one
            all_issues = (
                session.query(Issue)
                .filter(Issue.id != issue_id)
                .all()
            )
            
            eligible_children = []
            
            for potential_child in all_issues:
                # Check if this issue already has a parent
                existing_parent = session.query(Dependency).filter(
                    and_(
                        Dependency.issue_id == potential_child.id,
                        Dependency.type == DependencyType.PARENT_CHILD
                    )
                ).first()
                
                # Skip if already has a parent and it's not the current issue
                if existing_parent and existing_parent.depends_on_id != issue_id:
                    continue
                
                # Check if this would create a cycle
                if self._would_create_cycle(session, issue_id, potential_child.id):
                    continue
                
                # Apply issue type hierarchy rules
                if self._is_valid_parent_child_type(current_issue.issue_type, potential_child.issue_type):
                    eligible_children.append(potential_child)
            
            # Expunge to make accessible outside session
            for issue in eligible_children:
                session.expunge(issue)
            
            return eligible_children

    def _is_valid_parent_child_type(self, parent_type, child_type) -> bool:
        """Check if parent-child type combination is valid based on hierarchy rules"""
        
        # Convert to string values if they're enum objects
        if hasattr(parent_type, 'value'):
            parent_type = parent_type.value
        if hasattr(child_type, 'value'):
            child_type = child_type.value
        
        parent_type = parent_type.lower()
        child_type = child_type.lower()
        
        # Define hierarchy rules
        valid_combinations = {
            'epic': ['feature', 'task', 'bug', 'chore'],
            'feature': ['task', 'feature'],
            'task': ['task', 'chore'],
            'bug': ['task'],
            'chore': ['task', 'chore']
        }
        
        return child_type in valid_combinations.get(parent_type, [])

    def reorder_children(self, parent_id: str, ordered_child_ids: List[str], actor: str = "system") -> bool:
        """Reorder children of a parent issue"""
        
        with get_db_session() as session:
            # Verify parent exists
            parent = session.query(Issue).filter(Issue.id == parent_id).first()
            if not parent:
                return False
            
            # Get all existing child dependencies
            existing_children = session.query(Dependency).filter(
                and_(
                    Dependency.depends_on_id == parent_id,
                    Dependency.type == DependencyType.PARENT_CHILD
                )
            ).all()
            
            # Create a map of existing children
            existing_map = {dep.issue_id: dep for dep in existing_children}
            
            # Update the order
            for index, child_id in enumerate(ordered_child_ids):
                if child_id in existing_map:
                    existing_map[child_id].child_order = index
            
            session.commit()
            return True

    def get_children_ordered(self, parent_id: str) -> List[Dependency]:
        """Get children dependencies ordered by child_order"""
        
        with get_db_session() as session:
            children = (
                session.query(Dependency)
                .filter(
                    and_(
                        Dependency.depends_on_id == parent_id,
                        Dependency.type == DependencyType.PARENT_CHILD
                    )
                )
                .order_by(Dependency.child_order, Dependency.created_at)
                .all()
            )
            
            # Expunge to make accessible outside session
            for dep in children:
                session.expunge(dep)
            
            return children


# Global service instance
dependency_service = DependencyService()