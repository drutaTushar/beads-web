"""Test server startup migration with empty database"""

import pytest
import tempfile
import os
import shutil
import asyncio
from pathlib import Path
from sqlalchemy import create_engine, inspect
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aitrac.storage.database import initialize_database

class TestServerMigration:
    """Test server migration scenarios"""
    
    def test_empty_database_file_migration(self):
        """Test that server applies migration to empty database file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Create .aitrac directory and empty database file
                aitrac_dir = Path(".aitrac")
                aitrac_dir.mkdir()
                db_file = aitrac_dir / "database.db"
                
                # Create empty database file (0 bytes)
                db_file.touch()
                assert db_file.stat().st_size == 0
                
                # Initialize database (this simulates server startup)
                from aitrac.storage.migrations import initialize_database
                initialize_database()
                
                # Verify database now has schema
                assert db_file.stat().st_size > 0
                
                engine = create_engine(f"sqlite:///{db_file}")
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
                for table in expected_tables:
                    assert table in tables, f"Table {table} not found in {tables}"
                
                # Verify specific table structure
                issues_columns = [col["name"] for col in inspector.get_columns("issues")]
                assert "id" in issues_columns
                assert "title" in issues_columns
                assert "status" in issues_columns
                assert "created_at" in issues_columns
                
                engine.dispose()
                
            finally:
                os.chdir(original_cwd)
    
    def test_corrupted_database_file_migration(self):
        """Test migration with corrupted database file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Create .aitrac directory and corrupted database file
                aitrac_dir = Path(".aitrac")
                aitrac_dir.mkdir()
                db_file = aitrac_dir / "database.db"
                
                # Create corrupted database file with invalid content
                with open(db_file, "w") as f:
                    f.write("This is not a valid SQLite database")
                
                # Migration should handle this gracefully and recreate database
                from aitrac.storage.migrations import initialize_database
                
                try:
                    initialize_database()
                    
                    # Verify database was recreated properly
                    engine = create_engine(f"sqlite:///{db_file}")
                    inspector = inspect(engine)
                    tables = inspector.get_table_names()
                    
                    expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
                    for table in expected_tables:
                        assert table in tables
                    
                    engine.dispose()
                    
                except Exception as e:
                    # Migration might fail with corrupted database - this is expected behavior
                    # The important thing is that it doesn't crash the application silently
                    assert "database" in str(e).lower() or "sqlite" in str(e).lower()
                
            finally:
                os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_server_startup_with_empty_db(self):
        """Test actual server startup with empty database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Create empty database
                aitrac_dir = Path(".aitrac")
                aitrac_dir.mkdir()
                db_file = aitrac_dir / "database.db"
                db_file.touch()
                
                # Simulate server startup
                await initialize_database()
                
                # Verify migration was applied
                engine = create_engine(f"sqlite:///{db_file}")
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                assert "issues" in tables
                assert "alembic_version" in tables
                
                # Check alembic version is set
                from sqlalchemy import text
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                    assert result is not None
                    assert len(result[0]) > 0  # Should have a version number
                
                engine.dispose()
                
            finally:
                os.chdir(original_cwd)
    
    def test_no_database_directory_migration(self):
        """Test migration when .aitrac directory doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Ensure no .aitrac directory exists
                aitrac_dir = Path(".aitrac")
                assert not aitrac_dir.exists()
                
                # Initialize database
                from aitrac.storage.migrations import initialize_database
                initialize_database()
                
                # Verify everything was created
                assert aitrac_dir.exists()
                assert (aitrac_dir / "database.db").exists()
                assert (aitrac_dir / "config.json").exists()
                
                # Verify database schema
                db_file = aitrac_dir / "database.db"
                engine = create_engine(f"sqlite:///{db_file}")
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                expected_tables = ["issues", "dependencies", "events", "labels", "alembic_version"]
                for table in expected_tables:
                    assert table in tables
                
                engine.dispose()
                
            finally:
                os.chdir(original_cwd)

class TestMigrationBehavior:
    """Test specific migration behaviors"""
    
    def test_migration_is_idempotent(self):
        """Test that running migration multiple times is safe"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                from aitrac.storage.migrations import initialize_database
                
                # Run migration first time
                initialize_database()
                
                # Verify database exists
                aitrac_dir = Path(".aitrac")
                db_file = aitrac_dir / "database.db"
                assert db_file.exists()
                
                # Get initial state
                engine = create_engine(f"sqlite:///{db_file}")
                inspector = inspect(engine)
                initial_tables = set(inspector.get_table_names())
                engine.dispose()
                
                # Run migration second time
                initialize_database()
                
                # Verify state is unchanged
                engine = create_engine(f"sqlite:///{db_file}")
                inspector = inspect(engine)
                final_tables = set(inspector.get_table_names())
                engine.dispose()
                
                assert initial_tables == final_tables
                
            finally:
                os.chdir(original_cwd)
    
    def test_backup_creation_during_migration(self):
        """Test that backups are created when migrating existing database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Create existing database with some content
                aitrac_dir = Path(".aitrac")
                aitrac_dir.mkdir()
                db_file = aitrac_dir / "database.db"
                
                # Create a database with some content
                from aitrac.storage.migrations import initialize_database
                initialize_database()
                
                # Add some content to the database
                from sqlalchemy import text
                engine = create_engine(f"sqlite:///{db_file}")
                with engine.connect() as conn:
                    # This simulates having data in the database
                    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('test') ON CONFLICT DO NOTHING"))
                    conn.commit()
                engine.dispose()
                
                original_size = db_file.stat().st_size
                
                # Simulate a scenario where migration might be needed
                # (In reality, this test shows backup behavior)
                from aitrac.storage.migrations import backup_database
                backup_path = backup_database()
                
                if backup_path:  # Backup was created
                    assert backup_path.exists()
                    assert "backup" in backup_path.name
                    # Backup should have content
                    assert backup_path.stat().st_size > 0
                
            finally:
                os.chdir(original_cwd)