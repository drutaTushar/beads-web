"""Tests for dependency service layer"""

import pytest
import tempfile
import os
from pathlib import Path

from aitrac.storage.dependency_service import dependency_service
from aitrac.storage.issue_service import issue_service
from aitrac.models import DependencyType, IssueType, Status
from aitrac.storage.migrations import initialize_database
from aitrac.storage.database import reset_database_globals


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        # Create .aitrac directory and config
        os.makedirs(".aitrac", exist_ok=True)
        with open(".aitrac/config.json", "w") as f:
            f.write('{"project_prefix": "test", "source_id": "local"}')
        
        # Initialize database
        initialize_database()
        
        try:
            yield temp_dir
        finally:
            os.chdir(old_cwd)
            reset_database_globals()


@pytest.fixture
def sample_issues(temp_db):
    """Create sample issues for testing"""
    # Create three issues for testing dependencies
    issue1 = issue_service.create_issue(
        title="Design system",
        description="Create design mockups",
        issue_type=IssueType.TASK,
        actor="test"
    )
    
    issue2 = issue_service.create_issue(
        title="Implement frontend",
        description="Build React components",
        issue_type=IssueType.FEATURE,
        actor="test"
    )
    
    issue3 = issue_service.create_issue(
        title="Write tests",
        description="Add unit tests",
        issue_type=IssueType.TASK,
        actor="test"
    )
    
    return issue1, issue2, issue3


def test_add_dependency_success(sample_issues):
    """Test successfully adding a dependency"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependency: issue2 depends on issue1
    dependency = dependency_service.add_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    assert dependency is not None
    assert dependency.issue_id == issue2.id
    assert dependency.depends_on_id == issue1.id
    assert dependency.type == DependencyType.BLOCKS
    assert dependency.created_by == "test"


def test_add_dependency_nonexistent_issue(sample_issues):
    """Test adding dependency with nonexistent issue"""
    issue1, issue2, issue3 = sample_issues
    
    # Try to add dependency with nonexistent issue
    dependency = dependency_service.add_dependency(
        issue_id="nonexistent",
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    assert dependency is None


def test_add_duplicate_dependency(sample_issues):
    """Test adding duplicate dependency returns existing one"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependency
    dep1 = dependency_service.add_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    # Add same dependency again
    dep2 = dependency_service.add_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    assert dep1.issue_id == dep2.issue_id
    assert dep1.depends_on_id == dep2.depends_on_id
    assert dep1.type == dep2.type


def test_circular_dependency_detection(sample_issues):
    """Test circular dependency detection"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependency: issue2 depends on issue1
    dependency_service.add_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    # Try to add circular dependency: issue1 depends on issue2
    with pytest.raises(ValueError, match="circular dependency"):
        dependency_service.add_dependency(
            issue_id=issue1.id,
            depends_on_id=issue2.id,
            dependency_type=DependencyType.BLOCKS,
            actor="test"
        )


def test_complex_circular_dependency(sample_issues):
    """Test detection of complex circular dependencies"""
    issue1, issue2, issue3 = sample_issues
    
    # Create chain: issue3 -> issue2 -> issue1
    dependency_service.add_dependency(issue3.id, issue2.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    
    # Try to create cycle: issue1 -> issue3
    with pytest.raises(ValueError, match="circular dependency"):
        dependency_service.add_dependency(issue1.id, issue3.id, DependencyType.BLOCKS, "test")


def test_get_dependencies(sample_issues):
    """Test getting dependencies for an issue"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependencies: issue3 depends on both issue1 and issue2
    dependency_service.add_dependency(issue3.id, issue1.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue3.id, issue2.id, DependencyType.RELATED, "test")
    
    dependencies = dependency_service.get_dependencies(issue3.id)
    
    assert len(dependencies) == 2
    dep_ids = [dep.depends_on_id for dep in dependencies]
    assert issue1.id in dep_ids
    assert issue2.id in dep_ids


def test_get_dependents(sample_issues):
    """Test getting dependents of an issue"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependencies: both issue2 and issue3 depend on issue1
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue3.id, issue1.id, DependencyType.PARENT_CHILD, "test")
    
    dependents = dependency_service.get_dependents(issue1.id)
    
    assert len(dependents) == 2
    dependent_ids = [dep.issue_id for dep in dependents]
    assert issue2.id in dependent_ids
    assert issue3.id in dependent_ids


def test_remove_dependency(sample_issues):
    """Test removing a dependency"""
    issue1, issue2, issue3 = sample_issues
    
    # Add dependency
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    
    # Verify it exists
    dependencies = dependency_service.get_dependencies(issue2.id)
    assert len(dependencies) == 1
    
    # Remove dependency
    success = dependency_service.remove_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    assert success is True
    
    # Verify it's gone
    dependencies = dependency_service.get_dependencies(issue2.id)
    assert len(dependencies) == 0


def test_remove_nonexistent_dependency(sample_issues):
    """Test removing nonexistent dependency"""
    issue1, issue2, issue3 = sample_issues
    
    success = dependency_service.remove_dependency(
        issue_id=issue2.id,
        depends_on_id=issue1.id,
        dependency_type=DependencyType.BLOCKS,
        actor="test"
    )
    
    assert success is False


def test_dependency_tree(sample_issues):
    """Test building dependency tree"""
    issue1, issue2, issue3 = sample_issues
    
    # Create chain: issue3 -> issue2 -> issue1
    dependency_service.add_dependency(issue3.id, issue2.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    
    tree = dependency_service.get_dependency_tree(issue3.id)
    
    assert tree["issue_id"] == issue3.id
    assert len(tree["dependencies"]) == 1
    assert tree["dependencies"][0]["issue_id"] == issue2.id
    assert tree["dependencies"][0]["type"] == "blocks"
    assert len(tree["dependencies"][0]["dependencies"]) == 1
    assert tree["dependencies"][0]["dependencies"][0]["issue_id"] == issue1.id


def test_find_blocking_path_no_block(sample_issues):
    """Test finding blocking path when not blocked"""
    issue1, issue2, issue3 = sample_issues
    
    # Close issue1 so nothing is blocking
    issue_service.close_issue(issue1.id, actor="test")
    
    # Add dependency: issue2 depends on issue1 (which is closed)
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    
    blocking_path = dependency_service.find_blocking_path(issue2.id)
    
    assert blocking_path == []  # No blocking path since issue1 is closed


def test_find_blocking_path_with_block(sample_issues):
    """Test finding blocking path when blocked"""
    issue1, issue2, issue3 = sample_issues
    
    # Create blocking chain: issue3 -> issue2 -> issue1 (all open)
    dependency_service.add_dependency(issue3.id, issue2.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    
    blocking_path = dependency_service.find_blocking_path(issue3.id)
    
    # Should find path to the first open blocker (issue2 in this case)
    assert len(blocking_path) >= 2
    assert blocking_path[0] == issue3.id
    assert issue2.id in blocking_path  # Should reach the first open blocker (issue2)


def test_dependency_types(sample_issues):
    """Test different dependency types"""
    issue1, issue2, issue3 = sample_issues
    
    # Add different types of dependencies
    dependency_service.add_dependency(issue2.id, issue1.id, DependencyType.BLOCKS, "test")
    dependency_service.add_dependency(issue3.id, issue1.id, DependencyType.RELATED, "test")
    dependency_service.add_dependency(issue3.id, issue2.id, DependencyType.PARENT_CHILD, "test")
    
    # Check issue2 dependencies
    deps2 = dependency_service.get_dependencies(issue2.id)
    assert len(deps2) == 1
    assert deps2[0].type == DependencyType.BLOCKS
    
    # Check issue3 dependencies
    deps3 = dependency_service.get_dependencies(issue3.id)
    assert len(deps3) == 2
    types = [dep.type for dep in deps3]
    assert DependencyType.RELATED in types
    assert DependencyType.PARENT_CHILD in types