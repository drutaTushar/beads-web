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
    # Find project root (where alembic.ini is located)
    current_dir = Path(__file__).parent
    project_root = current_dir
    
    # Walk up to find alembic.ini
    while project_root.parent != project_root:
        alembic_ini = project_root / "alembic.ini"
        if alembic_ini.exists():
            break
        project_root = project_root.parent
    
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))
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