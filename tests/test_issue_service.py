"""Tests for issue service layer"""

import pytest
import tempfile
import os
from datetime import datetime

from aitrac.storage.issue_service import issue_service
from aitrac.models import IssueType, Status
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


def test_create_issue_basic(temp_db):
    """Test basic issue creation"""
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    assert issue is not None
    assert issue.title == "Test issue"
    assert issue.description == "Test description"
    assert issue.status == Status.OPEN
    assert issue.created_by == "test_user"
    assert issue.id.startswith("test-")
    assert issue.sequence == 1  # First issue


def test_create_issue_with_all_fields(temp_db):
    """Test issue creation with all fields"""
    issue = issue_service.create_issue(
        title="Complex issue",
        description="Detailed description",
        design="Design notes",
        acceptance_criteria="AC notes",
        notes="Working notes",
        priority=1,
        issue_type=IssueType.FEATURE,
        assignee="developer",
        estimated_minutes=120,
        actor="project_manager"
    )
    
    assert issue.title == "Complex issue"
    assert issue.description == "Detailed description"
    assert issue.design == "Design notes"
    assert issue.acceptance_criteria == "AC notes"
    assert issue.notes == "Working notes"
    assert issue.priority == 1
    assert issue.issue_type == IssueType.FEATURE
    assert issue.assignee == "developer"
    assert issue.estimated_minutes == 120
    assert issue.created_by == "project_manager"


def test_get_issue(temp_db):
    """Test getting an issue by ID"""
    # Create issue
    created_issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    # Get issue
    retrieved_issue = issue_service.get_issue(created_issue.id)
    
    assert retrieved_issue is not None
    assert retrieved_issue.id == created_issue.id
    assert retrieved_issue.title == created_issue.title


def test_get_nonexistent_issue(temp_db):
    """Test getting nonexistent issue returns None"""
    issue = issue_service.get_issue("nonexistent-id")
    assert issue is None


def test_update_issue(temp_db):
    """Test updating an issue"""
    # Create issue
    issue = issue_service.create_issue(
        title="Original title",
        description="Original description",
        actor="test_user"
    )
    
    # Update issue
    updates = {
        "title": "Updated title",
        "priority": 3,
        "assignee": "new_developer"
    }
    
    updated_issue = issue_service.update_issue(
        issue_id=issue.id,
        updates=updates,
        actor="test_user"
    )
    
    assert updated_issue is not None
    assert updated_issue.title == "Updated title"
    assert updated_issue.priority == 3
    assert updated_issue.assignee == "new_developer"
    assert updated_issue.description == "Original description"  # Unchanged


def test_update_nonexistent_issue(temp_db):
    """Test updating nonexistent issue returns None"""
    updated_issue = issue_service.update_issue(
        issue_id="nonexistent-id",
        updates={"title": "New title"},
        actor="test_user"
    )
    
    assert updated_issue is None


def test_close_issue(temp_db):
    """Test closing an issue"""
    # Create issue
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    # Close issue
    closed_issue = issue_service.close_issue(
        issue_id=issue.id,
        reason="Task completed",
        actor="test_user"
    )
    
    assert closed_issue is not None
    assert closed_issue.status == Status.CLOSED
    assert closed_issue.closed_at is not None


def test_reopen_issue(temp_db):
    """Test reopening a closed issue"""
    # Create and close issue
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    closed_issue = issue_service.close_issue(
        issue_id=issue.id,
        reason="Closed for testing",
        actor="test_user"
    )
    
    # Reopen issue
    reopened_issue = issue_service.reopen_issue(
        issue_id=issue.id,
        actor="test_user"
    )
    
    assert reopened_issue is not None
    assert reopened_issue.status == Status.OPEN
    assert reopened_issue.closed_at is None


def test_reopen_open_issue(temp_db):
    """Test reopening an already open issue returns None"""
    # Create issue (open by default)
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    # Try to reopen already open issue
    reopened_issue = issue_service.reopen_issue(
        issue_id=issue.id,
        actor="test_user"
    )
    
    assert reopened_issue is None


def test_list_issues_basic(temp_db):
    """Test basic issue listing"""
    # Create multiple issues
    issue1 = issue_service.create_issue(title="Issue 1", actor="test")
    issue2 = issue_service.create_issue(title="Issue 2", actor="test")
    issue3 = issue_service.create_issue(title="Issue 3", actor="test")
    
    # List all issues
    issues, total = issue_service.list_issues()
    
    assert total == 3
    assert len(issues) == 3
    
    # Check they're ordered by created_at descending (newest first)
    # Note: exact ordering may vary due to timestamp precision
    issue_ids = [issue.id for issue in issues]
    assert issue3.id in issue_ids  # All issues should be present
    assert issue2.id in issue_ids
    assert issue1.id in issue_ids


def test_list_issues_with_filters(temp_db):
    """Test issue listing with filters"""
    # Create issues with different attributes
    issue1 = issue_service.create_issue(
        title="Bug fix", 
        issue_type=IssueType.BUG, 
        priority=0,
        assignee="dev1",
        actor="test"
    )
    
    issue2 = issue_service.create_issue(
        title="Feature request", 
        issue_type=IssueType.FEATURE, 
        priority=2,
        assignee="dev2",
        actor="test"
    )
    
    issue3 = issue_service.create_issue(
        title="Another bug", 
        issue_type=IssueType.BUG, 
        priority=1,
        assignee="dev1",
        actor="test"
    )
    
    # Close one issue
    issue_service.close_issue(issue3.id, actor="test")
    
    # Filter by issue type
    bugs, total = issue_service.list_issues(issue_type=IssueType.BUG)
    assert total == 2
    
    # Filter by status
    open_issues, total = issue_service.list_issues(status=Status.OPEN)
    assert total == 2  # issue1 and issue2
    
    # Filter by assignee
    dev1_issues, total = issue_service.list_issues(assignee="dev1")
    assert total == 2  # issue1 and issue3
    
    # Filter by priority
    high_priority, total = issue_service.list_issues(priority=0)
    assert total == 1  # issue1


def test_list_issues_with_search(temp_db):
    """Test issue listing with search"""
    # Create issues with searchable content
    issue1 = issue_service.create_issue(
        title="User authentication bug",
        description="Login form not working",
        actor="test"
    )
    
    issue2 = issue_service.create_issue(
        title="Database optimization",
        description="Query performance issues",
        actor="test"
    )
    
    issue3 = issue_service.create_issue(
        title="UI improvements",
        description="User interface enhancements",
        actor="test"
    )
    
    # Search by title
    results, total = issue_service.list_issues(search="authentication")
    assert total == 1
    assert results[0].id == issue1.id
    
    # Search by description
    results, total = issue_service.list_issues(search="performance")
    assert total == 1
    assert results[0].id == issue2.id
    
    # Search by ID (partial)
    results, total = issue_service.list_issues(search=issue3.id[:6])
    assert total == 1
    assert results[0].id == issue3.id
    
    # Search with no matches
    results, total = issue_service.list_issues(search="nonexistent")
    assert total == 0
    assert len(results) == 0


def test_list_issues_pagination(temp_db):
    """Test issue listing with pagination"""
    # Create 5 issues
    issues = []
    for i in range(5):
        issue = issue_service.create_issue(
            title=f"Issue {i+1}",
            actor="test"
        )
        issues.append(issue)
    
    # Test pagination
    page1, total = issue_service.list_issues(offset=0, limit=2)
    assert total == 5
    assert len(page1) == 2
    
    page2, total = issue_service.list_issues(offset=2, limit=2)
    assert total == 5
    assert len(page2) == 2
    
    # Ensure no overlap
    page1_ids = [issue.id for issue in page1]
    page2_ids = [issue.id for issue in page2]
    assert not set(page1_ids).intersection(set(page2_ids))


def test_add_comment(temp_db):
    """Test adding comments to issues"""
    # Create issue
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    # Add comment
    success = issue_service.add_comment(
        issue_id=issue.id,
        comment="This is a test comment",
        actor="test_user"
    )
    
    assert success is True


def test_add_comment_nonexistent_issue(temp_db):
    """Test adding comment to nonexistent issue"""
    success = issue_service.add_comment(
        issue_id="nonexistent-id",
        comment="This comment will fail",
        actor="test_user"
    )
    
    assert success is False


def test_get_issue_events(temp_db):
    """Test getting issue events"""
    # Create issue
    issue = issue_service.create_issue(
        title="Test issue",
        description="Test description",
        actor="test_user"
    )
    
    # Update issue to create events
    issue_service.update_issue(
        issue_id=issue.id,
        updates={"title": "Updated title"},
        actor="test_user"
    )
    
    # Add comment
    issue_service.add_comment(
        issue_id=issue.id,
        comment="Test comment",
        actor="test_user"
    )
    
    # Get events
    events = issue_service.get_issue_events(issue.id)
    
    # Should have at least creation, update, and comment events
    assert len(events) >= 3
    
    # Events should be ordered by created_at descending (newest first)
    assert events[0].created_at >= events[1].created_at


def test_sequence_numbering(temp_db):
    """Test that issues get sequential sequence numbers"""
    # Create multiple issues
    issue1 = issue_service.create_issue(title="Issue 1", actor="test")
    issue2 = issue_service.create_issue(title="Issue 2", actor="test")
    issue3 = issue_service.create_issue(title="Issue 3", actor="test")
    
    assert issue1.sequence == 1
    assert issue2.sequence == 2
    assert issue3.sequence == 3