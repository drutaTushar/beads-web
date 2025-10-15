"""Tests for markdown parser"""

import pytest
from aitrac.storage.markdown_parser import MarkdownParser, ParsedIssue
from aitrac.models import IssueType


class TestMarkdownParser:
    """Test cases for MarkdownParser"""
    
    def test_basic_issue_parsing(self):
        """Test parsing basic issue structure"""
        markdown = """
# Issues Structure
- [epic1] My Epic Title, t=Epic, p=0
- [task1] Simple Task
- [bug1] Bug Fix, t=Bug, p=1, assignee=john
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert len(result.issues) == 3
        
        epic = next(issue for issue in result.issues if issue.logical_id == "epic1")
        assert epic.title == "My Epic Title"
        assert epic.issue_type == IssueType.EPIC
        assert epic.priority == 0
        
        task = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task.title == "Simple Task"
        assert task.issue_type == IssueType.TASK  # default
        assert task.priority == 2  # default
        
        bug = next(issue for issue in result.issues if issue.logical_id == "bug1")
        assert bug.title == "Bug Fix"
        assert bug.issue_type == IssueType.BUG
        assert bug.priority == 1
        assert bug.assignee == "john"
    
    def test_hierarchical_structure(self):
        """Test parsing hierarchical issue structure"""
        markdown = """
# Issues Structure
- [epic1] Epic One, t=Epic
    - [feature1] Feature One, t=Feature
        - [task1] Task One
        - [task2] Task Two
    - [task3] Direct Epic Task
- [epic2] Epic Two, t=Epic
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert len(result.issues) == 6
        
        # Check parent relationships
        feature1 = next(issue for issue in result.issues if issue.logical_id == "feature1")
        assert feature1.parent_logical_id == "epic1"
        assert feature1.depth == 1
        
        task1 = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task1.parent_logical_id == "feature1"
        assert task1.depth == 2
        
        task3 = next(issue for issue in result.issues if issue.logical_id == "task3")
        assert task3.parent_logical_id == "epic1"
        assert task3.depth == 1
        
        epic2 = next(issue for issue in result.issues if issue.logical_id == "epic2")
        assert epic2.parent_logical_id is None
        assert epic2.depth == 0
    
    def test_dependencies_parsing(self):
        """Test parsing explicit dependencies"""
        markdown = """
# Issues Structure
- [epic1] Epic One, t=Epic
- [epic2] Epic Two, t=Epic, deps=[epic1]
- [task1] Task One, deps=[epic1,epic2]
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        
        epic2 = next(issue for issue in result.issues if issue.logical_id == "epic2")
        assert epic2.dependencies == ["epic1"]
        
        task1 = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task1.dependencies == ["epic1", "epic2"]
    
    def test_detailed_content_parsing(self):
        """Test parsing detailed content sections"""
        markdown = """
# Issues Structure
- [epic1] Epic One, t=Epic
- [task1] Task One

# Detailed Content
## epic1
### description
This is the epic description.
It can have multiple lines.

### design
Epic design details here.

### acceptance_criteria
- [ ] Criteria one
- [ ] Criteria two

### notes
Some working notes.

## task1
### description
Task description here.
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        
        epic1 = next(issue for issue in result.issues if issue.logical_id == "epic1")
        assert "This is the epic description." in epic1.description
        assert "It can have multiple lines." in epic1.description
        assert epic1.design == "Epic design details here."
        assert "- [ ] Criteria one" in epic1.acceptance_criteria
        assert epic1.notes == "Some working notes."
        
        task1 = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task1.description == "Task description here."
        assert task1.design == ""  # Not specified
    
    def test_parameter_validation(self):
        """Test parameter parsing and validation"""
        markdown = """
# Issues Structure
- [test1] Test Issue, t=InvalidType, p=10, est=invalid
- [test2] Test Issue 2, t=Task, p=2, est=120
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid  # Should not fail, just warnings
        assert len(result.warnings) >= 2  # Invalid type and invalid estimate
        
        test1 = next(issue for issue in result.issues if issue.logical_id == "test1")
        assert test1.issue_type == IssueType.TASK  # Fallback to default
        assert test1.priority == 2  # Fallback to default
        assert test1.estimated_minutes is None  # Invalid estimate ignored
        
        test2 = next(issue for issue in result.issues if issue.logical_id == "test2")
        assert test2.estimated_minutes == 120
    
    def test_duplicate_logical_ids(self):
        """Test handling of duplicate logical IDs"""
        markdown = """
# Issues Structure
- [task1] First Task
- [task1] Duplicate Task
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert not result.is_valid
        assert any("Duplicate logical ID" in error for error in result.errors)
    
    def test_invalid_dependency_references(self):
        """Test validation of dependency references"""
        markdown = """
# Issues Structure
- [task1] Task One, deps=[nonexistent]
- [task2] Task Two, deps=[task1,another_nonexistent]
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert not result.is_valid
        assert len(result.errors) == 2  # Two invalid references
        assert any("depends on unknown issue 'nonexistent'" in error for error in result.errors)
        assert any("depends on unknown issue 'another_nonexistent'" in error for error in result.errors)
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        markdown = """
# Issues Structure
- [task1] Task One, deps=[task2]
- [task2] Task Two, deps=[task3]
- [task3] Task Three, deps=[task1]
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert not result.is_valid
        assert any("Circular dependency detected" in error for error in result.errors)
    
    def test_type_hierarchy_validation(self):
        """Test parent-child type hierarchy validation"""
        markdown = """
# Issues Structure
- [task1] Task One, t=Task
    - [epic1] Epic Under Task, t=Epic
- [epic2] Valid Epic, t=Epic
    - [feature1] Valid Feature, t=Feature
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert not result.is_valid
        assert any("Invalid type hierarchy" in error for error in result.errors)
        assert any("task" in error and "epic" in error for error in result.errors)
    
    def test_empty_sections(self):
        """Test handling of empty or missing sections"""
        markdown = """
# Issues Structure

# Detailed Content
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert len(result.issues) == 0
    
    def test_missing_issues_structure_section(self):
        """Test handling when Issues Structure section is missing"""
        markdown = """
# Some Other Section
- [task1] Task One

# Detailed Content
## task1
### description
Some description
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert not result.is_valid
        assert any("Missing '# Issues Structure' section" in error for error in result.errors)
    
    def test_content_for_unknown_issue(self):
        """Test warning when detailed content references unknown issue"""
        markdown = """
# Issues Structure
- [task1] Task One

# Detailed Content
## unknown_task
### description
This task doesn't exist in structure section.

## task1
### description
This is valid.
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert any("unknown issue 'unknown_task'" in warning for warning in result.warnings)
        
        task1 = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task1.description == "This is valid."
    
    def test_unknown_content_fields(self):
        """Test warning for unknown content fields"""
        markdown = """
# Issues Structure
- [task1] Task One

# Detailed Content
## task1
### unknown_field
This field is not supported.

### description
Valid description.
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert any("Unknown content field 'unknown_field'" in warning for warning in result.warnings)
        
        task1 = next(issue for issue in result.issues if issue.logical_id == "task1")
        assert task1.description == "Valid description."
    
    def test_complex_real_world_example(self):
        """Test parsing a complex real-world example"""
        markdown = """
# Issues Structure
- [platform] Platform Foundation, t=Epic, p=0
    - [auth] Authentication Service, t=Feature, p=0, deps=[platform]
        - [oauth] OAuth Implementation, t=Task, p=0, deps=[auth]
        - [jwt] JWT Token Management, t=Task, p=1, deps=[oauth]
    - [api] REST API Framework, t=Feature, p=1, deps=[platform]
        - [routes] API Routes, t=Task, p=0, deps=[api]
        - [validation] Input Validation, t=Task, p=1, deps=[routes]
    - [docs] Documentation, t=Chore, p=2, deps=[auth,api]

# Detailed Content
## platform
### description
Foundation epic for our new platform architecture.
This establishes core services and deployment infrastructure.

### acceptance_criteria
- [ ] Core services deployed
- [ ] CI/CD pipeline working
- [ ] Monitoring in place

## auth
### description
Complete authentication and authorization system.

### design
**Architecture:**
- OAuth2 with JWT tokens
- Multi-provider support
- Session management

### acceptance_criteria
- [ ] OAuth2 flow implemented
- [ ] JWT tokens working
- [ ] Multiple providers supported

## oauth
### description
Implement OAuth2 authentication flow.

### notes
Consider rate limiting for auth endpoints.
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        assert result.is_valid
        assert len(result.issues) == 8
        assert len(result.warnings) == 0
        
        # Verify structure
        platform = next(issue for issue in result.issues if issue.logical_id == "platform")
        assert platform.issue_type == IssueType.EPIC
        assert platform.parent_logical_id is None
        
        auth = next(issue for issue in result.issues if issue.logical_id == "auth")
        assert auth.parent_logical_id == "platform"
        assert auth.dependencies == ["platform"]
        
        oauth = next(issue for issue in result.issues if issue.logical_id == "oauth")
        assert oauth.parent_logical_id == "auth"
        assert oauth.dependencies == ["auth"]
        
        docs = next(issue for issue in result.issues if issue.logical_id == "docs")
        assert docs.dependencies == ["auth", "api"]
        assert docs.issue_type == IssueType.CHORE
        
        # Verify content
        assert "Foundation epic" in platform.description
        assert "OAuth2 with JWT tokens" in auth.design
        assert "rate limiting" in oauth.notes
    
    def test_edge_cases(self):
        """Test various edge cases"""
        markdown = """
# Issues Structure
- [empty_title] , t=Task
- [whitespace]     Whitespace Title     , t=Feature
- [special_chars] Title with "quotes" & symbols!, t=Bug
- [unicode] Unicode Title 🚀 测试, t=Chore

# Detailed Content
## empty_title
### description


### notes
Empty description above should be handled.

## unicode
### description
Unicode content works: 测试内容 🎉
        """
        
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        # Empty title should cause an error
        assert not result.is_valid
        assert any("Empty title" in error for error in result.errors)
        
        # Other issues should parse correctly
        whitespace = next((issue for issue in result.issues if issue.logical_id == "whitespace"), None)
        if whitespace:
            assert whitespace.title == "Whitespace Title"
        
        special = next((issue for issue in result.issues if issue.logical_id == "special_chars"), None)
        if special:
            assert "quotes" in special.title
            assert special.issue_type == IssueType.BUG
        
        unicode_issue = next((issue for issue in result.issues if issue.logical_id == "unicode"), None)
        if unicode_issue:
            assert "🚀" in unicode_issue.title
            assert "测试内容" in unicode_issue.description