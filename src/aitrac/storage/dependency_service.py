"""Dependency service layer for business logic"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime
import json

from ..models import Issue, Dependency, Event, DependencyType, EventType, Status
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
            if self._would_create_cycle(session, issue_id, depends_on_id, dependency_type):
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
    
    def find_blocking_path(self, issue_id: str) -> List[Dict[str, Any]]:
        """Find the shortest path to an open blocking dependency"""
        
        print(f"[WHY_BLOCKED] Finding blocking path for issue {issue_id}")
        
        with get_db_session() as session:
            visited = set()
            queue = [(issue_id, [])]
            
            while queue:
                current_id, path = queue.pop(0)
                print(f"[WHY_BLOCKED] Processing {current_id}, path so far: {[p['id'] for p in path]}")
                
                if current_id in visited:
                    print(f"[WHY_BLOCKED] Already visited {current_id}, skipping")
                    continue
                visited.add(current_id)
                
                # Get current issue status
                issue = session.query(Issue).filter(Issue.id == current_id).first()
                if not issue:
                    print(f"[WHY_BLOCKED] Issue {current_id} not found")
                    continue
                
                print(f"[WHY_BLOCKED] Issue {current_id} ({issue.title}) status: {issue.status}")
                
                # If this issue is open and we're not at the root, we found a blocker
                if issue.status == Status.OPEN and path:
                    # Create issue object for this blocking issue
                    current_issue_obj = {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status.value,
                        "issue_type": issue.issue_type.value
                    }
                    blocking_path = path + [current_issue_obj]
                    print(f"[WHY_BLOCKED] Found blocking path: {[p['id'] for p in blocking_path]}")
                    return blocking_path
                
                # If this issue is closed, continue exploring dependencies
                if issue.status == Status.CLOSED:
                    print(f"[WHY_BLOCKED] Issue {current_id} is closed, skipping dependencies")
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
                
                print(f"[WHY_BLOCKED] Issue {current_id} has {len(dependencies)} dependencies")
                
                for dep in dependencies:
                    print(f"[WHY_BLOCKED] Dependency: {current_id} -> {dep.depends_on_id} (type: {dep.type.value})")
                    if dep.depends_on_id not in visited:
                        # Create issue object for path tracking
                        current_issue_obj = {
                            "id": issue.id,
                            "title": issue.title,
                            "status": issue.status.value,
                            "issue_type": issue.issue_type.value
                        }
                        queue.append((dep.depends_on_id, path + [current_issue_obj]))
                    else:
                        print(f"[WHY_BLOCKED] {dep.depends_on_id} already visited")
            
            print(f"[WHY_BLOCKED] No blocking path found for {issue_id}")
            return []  # No blocking path found
    
    def _would_create_cycle(self, session: Session, from_id: str, to_id: str, dependency_type: DependencyType = None) -> bool:
        """Check if adding a dependency would create a circular dependency"""
        
        # If no dependency type specified, check all types
        if dependency_type is None:
            dependency_types_to_check = [DependencyType.BLOCKS, DependencyType.PARENT_CHILD, DependencyType.RELATED]
        else:
            # For parent-child relationships, only check parent-child cycles
            # For blocking relationships, only check blocking cycles  
            dependency_types_to_check = [dependency_type]
        
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
            
            # Get dependencies of current issue for the specific types we're checking
            dependencies = (
                session.query(Dependency)
                .filter(
                    and_(
                        Dependency.issue_id == current_id,
                        Dependency.type.in_(dependency_types_to_check)
                    )
                )
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
        2. All its BLOCKING dependencies are closed (BLOCKS type)
        3. If it has children, all children must be closed (can't complete parent with open children)
        4. Parent-child relationships don't block starting work (children can work under open parents)
        
        This allows proper hierarchical work where tasks can start under open epics/features.
        """
        
        with get_db_session() as session:
            from .issue_service import issue_service
            
            print(f"[READY_WORK] Starting ready work analysis with limit={limit}")
            
            # First, let's see what statuses exist in the database
            all_issues = session.query(Issue).all()
            print(f"[READY_WORK] Total issues in database: {len(all_issues)}")
            status_counts = {}
            for issue in all_issues:
                status = issue.status.value if hasattr(issue.status, 'value') else str(issue.status)
                status_counts[status] = status_counts.get(status, 0) + 1
                print(f"[READY_WORK] Issue {issue.id}: status={status} (type: {type(issue.status)})")
            print(f"[READY_WORK] Status distribution: {status_counts}")
            
            # Get all open issues using Status enum values
            from ..models.base import Status
            open_issues = (
                session.query(Issue)
                .filter(Issue.status.in_([Status.OPEN, Status.IN_PROGRESS]))
                .all()
            )
            
            print(f"[READY_WORK] Found {len(open_issues)} open issues")
            for issue in open_issues:
                print(f"[READY_WORK] Open issue: {issue.id} - {issue.title} ({issue.status}, type={issue.issue_type.value}, priority={issue.priority})")
            
            ready_issues = []
            
            for issue in open_issues:
                print(f"[READY_WORK] Checking if issue {issue.id} ({issue.title}) is ready...")
                is_ready = self._is_issue_ready(session, issue)
                print(f"[READY_WORK] Issue {issue.id} ready status: {is_ready}")
                
                if is_ready:
                    ready_issues.append(issue)
                    print(f"[READY_WORK] Added {issue.id} to ready list (current count: {len(ready_issues)})")
                    if len(ready_issues) >= limit:
                        print(f"[READY_WORK] Reached limit of {limit}, stopping")
                        break
            
            print(f"[READY_WORK] Final ready issues count: {len(ready_issues)}")
            
            # Sort by priority (0 highest, 4 lowest)
            ready_issues.sort(key=lambda x: x.priority)
            
            # Expunge to make accessible outside session
            for issue in ready_issues:
                session.expunge(issue)
            
            return ready_issues
    
    def _is_issue_ready(self, session: Session, issue: Issue) -> bool:
        """Check if an issue is ready to start
        
        An issue is ready if:
        1. It has no children (leaf node) OR all its children are closed
        2. All its BLOCKING dependencies are closed
        3. Parent-child relationships don't block readiness (children can work under open parents)
        """
        
        print(f"  [READY_CHECK] Analyzing issue {issue.id} ({issue.title})")
        
        # First check: If this issue has children, it's only ready if all children are closed
        # (You can't complete a parent until all children are done)
        children = (
            session.query(Dependency)
            .filter(
                and_(
                    Dependency.depends_on_id == issue.id,
                    Dependency.type == DependencyType.PARENT_CHILD
                )
            )
            .all()
        )
        
        print(f"  [READY_CHECK] Issue {issue.id} has {len(children)} children")
        
        for child_dep in children:
            child_issue = (
                session.query(Issue)
                .filter(Issue.id == child_dep.issue_id)
                .first()
            )
            if child_issue:
                print(f"  [READY_CHECK] Child {child_issue.id} ({child_issue.title}) status: {child_issue.status}")
                if child_issue.status != Status.CLOSED:
                    print(f"  [READY_CHECK] BLOCKED: Issue {issue.id} has open child {child_issue.id}")
                    return False  # Can't complete parent while children are open
        
        # Second check: All BLOCKING dependencies must be closed
        blocking_dependencies = (
            session.query(Dependency)
            .filter(
                and_(
                    Dependency.issue_id == issue.id,
                    Dependency.type == DependencyType.BLOCKS
                )
            )
            .all()
        )
        
        print(f"  [READY_CHECK] Issue {issue.id} has {len(blocking_dependencies)} blocking dependencies")
        
        for dep in blocking_dependencies:
            blocking_issue = (
                session.query(Issue)
                .filter(Issue.id == dep.depends_on_id)
                .first()
            )
            
            if blocking_issue:
                print(f"  [READY_CHECK] Blocking dependency {blocking_issue.id} ({blocking_issue.title}) status: {blocking_issue.status}")
                if blocking_issue.status != Status.CLOSED:
                    print(f"  [READY_CHECK] BLOCKED: Issue {issue.id} blocked by open dependency {blocking_issue.id}")
                    return False  # Blocked by open dependency
        
        # Check parent-child relationships (for info only - these don't block)
        parent_dependencies = (
            session.query(Dependency)
            .filter(
                and_(
                    Dependency.issue_id == issue.id,
                    Dependency.type == DependencyType.PARENT_CHILD
                )
            )
            .all()
        )
        
        print(f"  [READY_CHECK] Issue {issue.id} has {len(parent_dependencies)} parent relationships")
        for dep in parent_dependencies:
            parent_issue = (
                session.query(Issue)
                .filter(Issue.id == dep.depends_on_id)
                .first()
            )
            if parent_issue:
                print(f"  [READY_CHECK] Parent {parent_issue.id} ({parent_issue.title}) status: {parent_issue.status} (doesn't block)")
        
        print(f"  [READY_CHECK] Issue {issue.id} is READY")
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
                if self._would_create_cycle(session, potential_parent.id, issue_id, DependencyType.PARENT_CHILD):
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
                
                # Check if this would create a cycle (only check parent-child cycles)
                if self._would_create_cycle(session, issue_id, potential_child.id, DependencyType.PARENT_CHILD):
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