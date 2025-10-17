"""Database migration handling with automatic upgrade on startup"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

def get_database_url() -> str:
    """Get database URL for current project"""
    return "sqlite:///.aitrac/database.db"

def get_migration_config() -> Config:
    """Get Alembic configuration"""
    # Get the aitrac package root directory
    # This file is in aitrac/storage/, so we go up one level to get to aitrac/
    package_root = Path(__file__).parent.parent

    # Look for alembic.ini and migrations in the aitrac package directory
    alembic_ini = package_root / "alembic.ini"
    migrations_dir = package_root / "migrations"

    if not alembic_ini.exists():
        raise FileNotFoundError(
            f"alembic.ini not found at {alembic_ini}. "
            "This indicates an incomplete installation. "
            "Please reinstall aitrac."
        )

    if not migrations_dir.exists():
        raise FileNotFoundError(
            f"migrations directory not found at {migrations_dir}. "
            "This indicates an incomplete installation. "
            "Please reinstall aitrac."
        )

    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())
    return alembic_cfg

def needs_migration() -> bool:
    """Check if database needs migration"""
    db_path = Path(".aitrac/database.db")
    if not db_path.exists():
        return True  # New database needs initial migration
    
    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            
            script_dir = ScriptDirectory.from_config(get_migration_config())
            head_rev = script_dir.get_current_head()
            
            return current_rev != head_rev
    except Exception as e:
        print(f"Error checking migration status: {e}")
        return True  # Assume migration needed if we can't check

def backup_database() -> Optional[Path]:
    """Create backup before migration"""
    db_path = Path(".aitrac/database.db")
    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.with_name(f"database.db.backup.{timestamp}")
        try:
            shutil.copy2(db_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
            return None
    return None

def run_migrations():
    """Run any pending migrations"""
    alembic_cfg = get_migration_config()
    command.upgrade(alembic_cfg, "head")

def get_project_config() -> dict:
    """Get project configuration from .aitrac/config.json"""
    config_file = Path(".aitrac/config.json")
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read config: {e}")
    
    # Return default config
    return {
        "project_prefix": "at",
        "source_id": "local"
    }

def save_project_config(config: dict):
    """Save project configuration to .aitrac/config.json"""
    config_file = Path(".aitrac/config.json")
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

def initialize_database():
    """Initialize database on first run or run migrations on upgrade"""
    # Ensure .aitrac directory exists
    aitrac_dir = Path(".aitrac")
    aitrac_dir.mkdir(exist_ok=True)
    
    # Ensure config exists
    config = get_project_config()
    save_project_config(config)
    
    db_path = Path(".aitrac/database.db")
    
    if not db_path.exists():
        # Fresh installation - create latest schema
        print("Initializing new aitrac database...")
        run_migrations()
        print("Database initialized successfully!")
    elif needs_migration():
        # Existing database - migrate
        print("Database migration required...")
        backup_path = backup_database()
        try:
            run_migrations()
            if backup_path:
                print(f"Migration successful! Backup created at: {backup_path}")
            else:
                print("Migration successful!")
        except Exception as e:
            print(f"Migration failed: {e}")
            if backup_path:
                print(f"Database backup available at: {backup_path}")
                print("You can restore the backup manually if needed.")
            raise
    else:
        print("Database is up to date")

async def initialize_database_async():
    """Async wrapper for database initialization"""
    initialize_database()