"""Test configuration and fixtures"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aitrac.models import Base
from aitrac.storage.database import get_db_session

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test isolation"""
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    yield Path(temp_dir)
    
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def clean_aitrac_dir(temp_dir):
    """Ensure clean .aitrac directory for each test"""
    aitrac_dir = temp_dir / ".aitrac"
    if aitrac_dir.exists():
        shutil.rmtree(aitrac_dir)
    return aitrac_dir

@pytest.fixture
def empty_database(temp_dir):
    """Create an empty SQLite database"""
    aitrac_dir = temp_dir / ".aitrac"
    aitrac_dir.mkdir(exist_ok=True)
    
    db_path = aitrac_dir / "database.db"
    # Create empty database file
    db_path.touch()
    
    return db_path

@pytest.fixture
def test_engine(temp_dir):
    """Create a test database engine"""
    aitrac_dir = temp_dir / ".aitrac"
    aitrac_dir.mkdir(exist_ok=True)
    
    db_url = f"sqlite:///{aitrac_dir}/database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    
    yield engine
    
    engine.dispose()

@pytest.fixture
def test_session(test_engine):
    """Create a test database session"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    # Clean up tables
    Base.metadata.drop_all(bind=test_engine)