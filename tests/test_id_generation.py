"""Test ID generation and collision detection"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aitrac.storage.id_generator import (
    generate_random_string,
    generate_issue_id,
    issue_exists,
    get_next_sequence_number
)
from aitrac.storage.migrations import save_project_config
from aitrac.models import Issue, Status, IssueType

class TestIdGeneration:
    """Test issue ID generation functionality"""
    
    def test_generate_random_string_default_length(self):
        """Test random string generation with default length"""
        result = generate_random_string()
        assert len(result) == 4
        assert result.isalnum()
        assert result.islower()
    
    def test_generate_random_string_custom_length(self):
        """Test random string generation with custom length"""
        result = generate_random_string(8)
        assert len(result) == 8
        assert result.isalnum()
        assert result.islower()
    
    def test_generate_random_string_uniqueness(self):
        """Test that random strings are different"""
        results = [generate_random_string() for _ in range(100)]
        # Should have mostly unique results (allow for rare collisions)
        assert len(set(results)) > 90
    
    def test_issue_exists_no_database(self, clean_aitrac_dir):
        """Test issue_exists when database doesn't exist"""
        assert issue_exists("test-1234") == False
    
    def test_issue_exists_with_database(self, test_session):
        """Test issue_exists with actual database"""
        # Create a test issue
        issue = Issue(
            id="test-1234",
            title="Test Issue",
            status=Status.OPEN,
            issue_type=IssueType.TASK,
            priority=1,
            sequence=1
        )
        test_session.add(issue)
        test_session.commit()
        
        # Mock the get_db_session to return our test session
        with patch('aitrac.storage.id_generator.get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = test_session
            
            assert issue_exists("test-1234") == True
            assert issue_exists("nonexistent-5678") == False
    
    def test_generate_issue_id_default_config(self, clean_aitrac_dir):
        """Test issue ID generation with default configuration"""
        with patch('aitrac.storage.id_generator.issue_exists', return_value=False):
            issue_id = generate_issue_id()
            
            assert issue_id.startswith("at-")
            assert len(issue_id) == 7  # "at-" + 4 chars
            parts = issue_id.split("-")
            assert len(parts) == 2
            assert parts[0] == "at"
            assert len(parts[1]) == 4
    
    def test_generate_issue_id_custom_config(self, clean_aitrac_dir):
        """Test issue ID generation with custom configuration"""
        # Set custom config
        save_project_config({
            "project_prefix": "custom",
            "source_id": "test"
        })
        
        with patch('aitrac.storage.id_generator.issue_exists', return_value=False):
            issue_id = generate_issue_id()
            
            assert issue_id.startswith("custom-")
            parts = issue_id.split("-")
            assert parts[0] == "custom"
            assert len(parts[1]) == 4
    
    def test_generate_issue_id_collision_retry(self, clean_aitrac_dir):
        """Test ID generation retries on collision"""
        collision_count = 0
        
        def mock_issue_exists(issue_id):
            nonlocal collision_count
            collision_count += 1
            # First 3 attempts return True (collision), then False
            return collision_count <= 3
        
        with patch('aitrac.storage.id_generator.issue_exists', side_effect=mock_issue_exists):
            issue_id = generate_issue_id()
            
            # Should have tried 4 times (3 collisions + 1 success)
            assert collision_count == 4
            assert issue_id.startswith("at-")
    
    def test_generate_issue_id_fallback_longer_suffix(self, clean_aitrac_dir):
        """Test ID generation falls back to longer suffix after many collisions"""
        def mock_issue_exists(issue_id):
            # Always return True for 4-char suffixes, False for 8-char
            parts = issue_id.split("-")
            return len(parts[1]) == 4
        
        with patch('aitrac.storage.id_generator.issue_exists', side_effect=mock_issue_exists):
            issue_id = generate_issue_id()
            
            # Should use 8-char suffix after many collisions
            parts = issue_id.split("-")
            assert parts[0] == "at"
            assert len(parts[1]) == 8
    
    def test_generate_issue_id_ultimate_fallback(self, clean_aitrac_dir):
        """Test ID generation ultimate fallback with timestamp"""
        with patch('aitrac.storage.id_generator.issue_exists', return_value=True):
            with patch('time.time', return_value=1234567890):
                issue_id = generate_issue_id()
                
                # Should include timestamp as fallback
                assert "7890" in issue_id  # Last 4 digits of timestamp
                parts = issue_id.split("-")
                assert len(parts) == 3  # prefix-random-timestamp
    
    def test_get_next_sequence_number_empty_db(self, clean_aitrac_dir):
        """Test sequence number generation with empty database"""
        with patch('aitrac.storage.id_generator.get_db_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.query.return_value.order_by.return_value.first.return_value = None
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            seq = get_next_sequence_number()
            assert seq == 1
    
    def test_get_next_sequence_number_with_existing(self, test_session):
        """Test sequence number generation with existing issues"""
        # Create test issues with sequence numbers
        for i, seq in enumerate([1, 3, 5], 1):
            issue = Issue(
                id=f"test-{i}",
                title=f"Test Issue {i}",
                status=Status.OPEN,
                issue_type=IssueType.TASK,
                priority=1,
                sequence=seq
            )
            test_session.add(issue)
        test_session.commit()
        
        with patch('aitrac.storage.id_generator.get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = test_session
            
            seq = get_next_sequence_number()
            assert seq == 6  # Max sequence (5) + 1

class TestIdGenerationIntegration:
    """Integration tests for ID generation"""
    
    def test_generate_unique_ids_bulk(self, clean_aitrac_dir):
        """Test generating many IDs to ensure uniqueness"""
        with patch('aitrac.storage.id_generator.issue_exists', return_value=False):
            ids = [generate_issue_id() for _ in range(1000)]
            
            # All IDs should be unique
            assert len(set(ids)) == 1000
            
            # All should follow the pattern
            for issue_id in ids:
                assert issue_id.startswith("at-")
                parts = issue_id.split("-")
                assert len(parts) == 2
                assert len(parts[1]) == 4
    
    def test_collision_detection_realistic(self, test_session):
        """Test collision detection with realistic database scenario"""
        # Create some existing issues
        existing_ids = ["at-abc1", "at-def2", "at-ghi3"]
        for i, issue_id in enumerate(existing_ids):
            issue = Issue(
                id=issue_id,
                title=f"Existing Issue {i}",
                status=Status.OPEN,
                issue_type=IssueType.TASK,
                priority=1,
                sequence=i + 1
            )
            test_session.add(issue)
        test_session.commit()
        
        with patch('aitrac.storage.id_generator.get_db_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = test_session
            
            # Generate new IDs - should avoid existing ones
            new_ids = [generate_issue_id() for _ in range(10)]
            
            # None of the new IDs should match existing ones
            for new_id in new_ids:
                assert new_id not in existing_ids
            
            # All new IDs should be unique
            assert len(set(new_ids)) == 10