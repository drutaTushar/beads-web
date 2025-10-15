"""Database initialization and migration handling"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator

from .migrations import initialize_database_async, get_database_url
from ..models import Base

# Global database engine and session factory
engine = None
SessionLocal = None

def get_engine():
    """Get database engine"""
    global engine
    if engine is None:
        engine = create_engine(
            get_database_url(),
            connect_args={"check_same_thread": False}  # SQLite specific
        )
    return engine

def get_session_factory():
    """Get session factory"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal

@contextmanager
def get_db_session() -> Generator:
    """Get database session with automatic cleanup"""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def reset_database_globals():
    """Reset global database engine and session factory for testing"""
    global engine, SessionLocal
    if engine:
        engine.dispose()
    engine = None
    SessionLocal = None

async def initialize_database():
    """Initialize database on startup with automatic migrations"""
    await initialize_database_async()