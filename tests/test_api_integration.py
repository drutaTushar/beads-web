"""Integration tests for API endpoints"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from aitrac.main import app
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
def client(temp_db):
    """Create test client"""
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_issue_success(client):
    """Test successful issue creation"""
    issue_data = {
        "title": "Test issue",
        "description": "Test description",
        "issue_type": "feature",
        "priority": 1
    }
    
    response = client.post("/api/issues/", json=issue_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["title"] == "Test issue"
    assert data["description"] == "Test description"
    assert data["issue_type"] == "feature"
    assert data["priority"] == 1
    assert data["status"] == "open"
    assert data["id"].startswith("test-")


def test_create_issue_validation_error(client):
    """Test issue creation with validation error"""
    # Missing required title
    issue_data = {
        "description": "Test description"
    }
    
    response = client.post("/api/issues/", json=issue_data)
    assert response.status_code == 422


def test_get_issue_success(client):
    """Test getting an issue"""
    # Create issue first
    issue_data = {
        "title": "Test issue",
        "description": "Test description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Get the issue
    response = client.get(f"/api/issues/{created_issue['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == created_issue["id"]
    assert data["title"] == "Test issue"


def test_get_issue_not_found(client):
    """Test getting nonexistent issue"""
    response = client.get("/api/issues/nonexistent-id")
    assert response.status_code == 404


def test_update_issue_success(client):
    """Test updating an issue"""
    # Create issue first
    issue_data = {
        "title": "Original title",
        "description": "Original description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Update the issue
    update_data = {
        "title": "Updated title",
        "priority": 3
    }
    response = client.put(f"/api/issues/{created_issue['id']}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["priority"] == 3
    assert data["description"] == "Original description"  # Unchanged


def test_close_issue_success(client):
    """Test closing an issue"""
    # Create issue first
    issue_data = {
        "title": "Test issue",
        "description": "Test description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Close the issue
    response = client.delete(f"/api/issues/{created_issue['id']}?reason=Task completed")
    assert response.status_code == 200
    
    data = response.json()
    assert "closed successfully" in data["message"]


def test_reopen_issue_success(client):
    """Test reopening a closed issue"""
    # Create and close issue first
    issue_data = {
        "title": "Test issue",
        "description": "Test description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Close it
    client.delete(f"/api/issues/{created_issue['id']}")
    
    # Reopen it
    response = client.post(f"/api/issues/{created_issue['id']}/reopen")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "open"
    assert data["closed_at"] is None


def test_list_issues_success(client):
    """Test listing issues"""
    # Create multiple issues
    for i in range(3):
        issue_data = {
            "title": f"Test issue {i+1}",
            "description": f"Description {i+1}"
        }
        client.post("/api/issues/", json=issue_data)
    
    # List issues
    response = client.get("/api/issues/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 3
    assert len(data["issues"]) == 3
    assert data["offset"] == 0
    assert data["limit"] == 50


def test_list_issues_with_filters(client):
    """Test listing issues with filters"""
    # Create issues with different types
    bug_data = {
        "title": "Bug issue",
        "issue_type": "bug",
        "priority": 0
    }
    client.post("/api/issues/", json=bug_data)
    
    feature_data = {
        "title": "Feature issue",
        "issue_type": "feature",
        "priority": 2
    }
    client.post("/api/issues/", json=feature_data)
    
    # Filter by issue type
    response = client.get("/api/issues/?issue_type=bug")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["issues"][0]["issue_type"] == "bug"
    
    # Filter by priority
    response = client.get("/api/issues/?priority=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["issues"][0]["priority"] == 0


def test_add_comment_success(client):
    """Test adding a comment to an issue"""
    # Create issue first
    issue_data = {
        "title": "Test issue",
        "description": "Test description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Add comment
    comment_data = {
        "comment": "This is a test comment"
    }
    response = client.post(f"/api/issues/{created_issue['id']}/comments", json=comment_data)
    assert response.status_code == 201
    
    data = response.json()
    assert "Comment added successfully" in data["message"]


def test_get_issue_events(client):
    """Test getting issue events"""
    # Create issue first
    issue_data = {
        "title": "Test issue",
        "description": "Test description"
    }
    create_response = client.post("/api/issues/", json=issue_data)
    created_issue = create_response.json()
    
    # Add comment to create more events
    comment_data = {"comment": "Test comment"}
    client.post(f"/api/issues/{created_issue['id']}/comments", json=comment_data)
    
    # Get events
    response = client.get(f"/api/issues/{created_issue['id']}/events")
    assert response.status_code == 200
    
    events = response.json()
    assert len(events) >= 2  # At least creation and comment events


def test_add_dependency_success(client):
    """Test adding a dependency"""
    # Create two issues
    issue1_data = {"title": "Issue 1", "description": "First issue"}
    issue2_data = {"title": "Issue 2", "description": "Second issue"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency: issue2 depends on issue1
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    response = client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["issue_id"] == issue2["id"]
    assert data["depends_on_id"] == issue1["id"]
    assert data["type"] == "blocks"


def test_add_circular_dependency_error(client):
    """Test that circular dependencies are prevented"""
    # Create two issues
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency: issue2 depends on issue1
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    
    # Try to add circular dependency: issue1 depends on issue2
    circular_dependency = {
        "depends_on_id": issue2["id"],
        "type": "blocks"
    }
    response = client.post(f"/api/issues/{issue1['id']}/dependencies", json=circular_dependency)
    assert response.status_code == 400
    assert "circular dependency" in response.json()["detail"]


def test_get_dependencies(client):
    """Test getting dependencies for an issue"""
    # Create two issues and add dependency
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    
    # Get dependencies
    response = client.get(f"/api/issues/{issue2['id']}/dependencies")
    assert response.status_code == 200
    
    dependencies = response.json()
    assert len(dependencies) == 1
    assert dependencies[0]["depends_on_id"] == issue1["id"]


def test_get_dependents(client):
    """Test getting dependents of an issue"""
    # Create two issues and add dependency
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency: issue2 depends on issue1
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    
    # Get dependents of issue1
    response = client.get(f"/api/issues/{issue1['id']}/dependents")
    assert response.status_code == 200
    
    dependents = response.json()
    assert len(dependents) == 1
    assert dependents[0]["issue_id"] == issue2["id"]


def test_remove_dependency(client):
    """Test removing a dependency"""
    # Create two issues and add dependency
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    
    # Remove dependency
    response = client.delete(f"/api/issues/{issue2['id']}/dependencies/{issue1['id']}")
    assert response.status_code == 200
    
    # Verify it's gone
    response = client.get(f"/api/issues/{issue2['id']}/dependencies")
    dependencies = response.json()
    assert len(dependencies) == 0


def test_why_blocked_analysis(client):
    """Test why-blocked analysis"""
    # Create two issues and add dependency
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    
    # Add dependency: issue2 depends on issue1
    dependency_data = {
        "depends_on_id": issue1["id"],
        "type": "blocks"
    }
    client.post(f"/api/issues/{issue2['id']}/dependencies", json=dependency_data)
    
    # Check why-blocked for issue2
    response = client.get(f"/api/issues/{issue2['id']}/why-blocked")
    assert response.status_code == 200
    
    data = response.json()
    assert data["blocked"] is True
    assert issue1["id"] in data["blocking_path"]


def test_dependency_tree(client):
    """Test getting dependency tree"""
    # Create three issues in a chain
    issue1_data = {"title": "Issue 1"}
    issue2_data = {"title": "Issue 2"}
    issue3_data = {"title": "Issue 3"}
    
    response1 = client.post("/api/issues/", json=issue1_data)
    response2 = client.post("/api/issues/", json=issue2_data)
    response3 = client.post("/api/issues/", json=issue3_data)
    
    issue1 = response1.json()
    issue2 = response2.json()
    issue3 = response3.json()
    
    # Create chain: issue3 -> issue2 -> issue1
    client.post(f"/api/issues/{issue3['id']}/dependencies", json={
        "depends_on_id": issue2["id"], "type": "blocks"
    })
    client.post(f"/api/issues/{issue2['id']}/dependencies", json={
        "depends_on_id": issue1["id"], "type": "blocks"
    })
    
    # Get dependency tree for issue3
    response = client.get(f"/api/issues/{issue3['id']}/tree")
    assert response.status_code == 200
    
    tree = response.json()
    assert tree["issue_id"] == issue3["id"]
    assert len(tree["dependencies"]) == 1
    assert tree["dependencies"][0]["issue_id"] == issue2["id"]