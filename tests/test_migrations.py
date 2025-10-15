"""Test database migration functionality"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, inspect

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aitrac.storage.migrations import (
    get_database_url, 
    needs_migration, 
    backup_database, 
    run_migrations,
    initialize_database,
    get_project_config,
    save_project_config
)
from aitrac.models import Issue, Dependency, Event, Label

class TestMigrationSystem:
    """Test the automatic migration system"""
    
    def test_get_database_url(self, temp_dir):
        """Test database URL generation"""
        with patch.object(Path, 'cwd', return_value=temp_dir):
            url = get_database_url()
            assert url == "sqlite:///.aitrac/database.db"
    
    def test_needs_migration_no_database(self, clean_aitrac_dir):
        """Test migration needed when no database exists"""
        assert needs_migration() == True
    
    def test_needs_migration_empty_database(self, empty_database):
        """Test migration needed for empty database file"""
        # Empty database file should need migration
        assert needs_migration() == True
    
    def test_project_config_defaults(self, clean_aitrac_dir):
        """Test default project configuration"""
        config = get_project_config()
        assert config["project_prefix"] == "at"
        assert config["source_id"] == "local"
    
    def test_project_config_save_load(self, clean_aitrac_dir):
        """Test saving and loading project configuration"""
        test_config = {
            "project_prefix": "test",
            "source_id": "test_repo"
        }
        
        save_project_config(test_config)
        loaded_config = get_project_config()
        
        assert loaded_config["project_prefix"] == "test"
        assert loaded_config["source_id"] == "test_repo"
    
    def test_backup_database_nonexistent(self, clean_aitrac_dir):
        """Test backup when database doesn't exist"""
        backup_path = backup_database()
        assert backup_path is None
    
    def test_backup_database_exists(self, empty_database):
        """Test backup when database exists"""
        # Write some content to the database
        with open(empty_database, "w") as f:
            f.write("test content")
        
        backup_path = backup_database()
        assert backup_path is not None
        assert backup_path.exists()
        assert "backup" in backup_path.name
        
        # Verify backup content
        with open(backup_path, "r") as f:
            assert f.read() == "test content"
    
    def test_initialize_database_fresh(self, clean_aitrac_dir):
        """Test database initialization from scratch"""
        # Ensure no .aitrac directory exists
        assert not clean_aitrac_dir.exists()
        
        # Initialize database
        initialize_database()
        
        # Check that directory and files were created
        assert clean_aitrac_dir.exists()
        assert (clean_aitrac_dir / "database.db").exists()
        assert (clean_aitrac_dir / "config.json").exists()
        
        # Verify database schema
        db_url = f"sqlite:///{clean_aitrac_dir}/database.db"
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
        for table in expected_tables:
            assert table in tables
        
        engine.dispose()
    
    def test_initialize_database_with_empty_file(self, empty_database):
        """Test database initialization with empty database file"""
        # Verify file exists but is empty
        assert empty_database.exists()
        assert empty_database.stat().st_size == 0
        
        # Initialize should apply migration
        initialize_database()
        
        # Verify database now has schema
        db_url = f"sqlite:///{empty_database}"
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
        for table in expected_tables:
            assert table in tables
        
        engine.dispose()
    
    def test_migration_creates_all_tables(self, clean_aitrac_dir):
        """Test that migration creates all expected tables with correct schema"""
        initialize_database()
        
        db_url = f"sqlite:///{clean_aitrac_dir}/database.db"
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Test issues table
        issues_columns = {col["name"]: col for col in inspector.get_columns("issues")}
        expected_issue_columns = [
            "id", "title", "description", "design", "acceptance_criteria", 
            "notes", "status", "priority", "issue_type", "assignee", 
            "estimated_minutes", "created_by", "sequence", "created_at", 
            "updated_at", "closed_at"
        ]
        for col in expected_issue_columns:
            assert col in issues_columns
        
        # Test dependencies table
        deps_columns = {col["name"]: col for col in inspector.get_columns("dependencies")}
        expected_dep_columns = ["issue_id", "depends_on_id", "type", "created_by", "created_at"]
        for col in expected_dep_columns:
            assert col in deps_columns
        
        # Test events table
        events_columns = {col["name"]: col for col in inspector.get_columns("events")}
        expected_event_columns = [
            "id", "issue_id", "event_type", "actor", "old_value", 
            "new_value", "comment", "created_at"
        ]
        for col in expected_event_columns:
            assert col in events_columns
        
        # Test labels table
        labels_columns = {col["name"]: col for col in inspector.get_columns("labels")}
        expected_label_columns = ["issue_id", "label", "created_by", "created_at"]
        for col in expected_label_columns:
            assert col in labels_columns
        
        engine.dispose()
    
    def test_migration_up_to_date(self, clean_aitrac_dir):
        """Test that already migrated database shows as up to date"""
        # Initialize database
        initialize_database()
        
        # Check that it's now up to date
        assert needs_migration() == False

class TestMigrationIntegration:
    """Integration tests for migration with server startup"""
    
    @pytest.mark.asyncio
    async def test_server_startup_migration(self, clean_aitrac_dir):
        """Test that server startup applies migrations correctly"""
        from aitrac.storage.database import initialize_database as async_init
        
        # Ensure no database exists
        assert not clean_aitrac_dir.exists()
        
        # Simulate server startup
        await async_init()
        
        # Verify database was created and migrated
        assert clean_aitrac_dir.exists()
        assert (clean_aitrac_dir / "database.db").exists()
        
        # Verify schema
        db_url = f"sqlite:///{clean_aitrac_dir}/database.db"
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
        for table in expected_tables:
            assert table in tables
        
        engine.dispose()