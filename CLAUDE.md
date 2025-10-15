
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AiTrac is a dependency-first issue tracking system designed for AI agents. It replaces the legacy `beads` tool with a modern Python-based solution featuring FastAPI backend, SQLite storage with Alembic migrations, and comprehensive dependency management.

**Key Design Principles:**
- **Dependency-First**: All issues interconnected through parent-child and blocking relationships
- **API-First**: Clean JSON APIs for agents, web interface for humans
- **Audit Trail**: Complete event sourcing for all changes
- **Agent-Friendly**: Designed for AI agents to query and manage work

## Development Commands

**Setup and Dependencies:**
```bash
# Install in development mode
uv pip install -e ".[dev]"

# Install just the package
uv pip install -e .
```

**Running the Application:**
```bash
# Initialize project (creates .aitrac/ directory and database)
aitrac init

# Start server (production)
aitrac serve --port 8080

# Start with auto-reload (development) 
aitrac serve --port 8080 --reload

# Start development environment
aitrac dev
```

**Testing:**
```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_dependency_service.py
pytest tests/test_issue_service.py  
pytest tests/test_api_integration.py

# Run single test function
pytest tests/test_dependency_service.py::test_circular_dependency_detection -v

# Run tests for specific components
pytest tests/test_migrations.py tests/test_id_generation.py tests/test_server_migration.py
```

**Code Quality:**
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

**Build and Distribution:**
```bash
# Build package
uv build

# Install from wheel
uv pip install dist/aitrac-0.1.0-py3-none-any.whl
```

## Architecture Overview

### Database Layer (`src/aitrac/storage/`)
- **SQLAlchemy Models**: Define core entities (Issue, Dependency, Event, Label)
- **Service Layer**: Business logic for issues and dependencies 
- **Migrations**: Alembic-based automatic database schema management
- **ID Generation**: Collision-resistant ID generation with configurable prefixes

### API Layer (`src/aitrac/api/`)
- **FastAPI Routes**: REST endpoints for issues and dependencies
- **Pydantic Schemas**: Request/response validation and serialization
- **Dependency Analysis**: "Why blocked?" analysis and dependency trees

### Core Models (`src/aitrac/models/`)
- **Issue**: Central entity with title, description, design, acceptance criteria
- **Dependency**: Relationships between issues (blocks, parent-child, related)
- **Event**: Audit trail for all changes with actor tracking
- **Base**: Shared SQLAlchemy configuration

### Database Management
- **Automatic Migrations**: Database schema updates on startup
- **Session Management**: Context managers with proper cleanup
- **Testing Isolation**: `reset_database_globals()` for test isolation

## Key Implementation Details

### Session Management
All database operations use `session.expunge()` to make objects accessible outside their session context, preventing `DetachedInstanceError`:

```python
session.commit()
session.refresh(issue)
session.expunge(issue)  # Critical for returning objects
return issue
```

### Test Architecture
- **Unit Tests**: Service layer testing with temporary databases
- **Integration Tests**: Full API testing with FastAPI TestClient
- **Database Reset**: Each test gets isolated database via `reset_database_globals()`

### Dependency Algorithms
- **Circular Detection**: Prevents dependency cycles during creation
- **Blocking Analysis**: `find_blocking_path()` finds shortest path to open blockers
- **Tree Building**: Recursive dependency tree construction

### Data Storage
- **Project Storage**: `.aitrac/` directory (like `.git/`)
- **Database**: `database.db` in project directory
- **Configuration**: `config.json` with project prefix and source ID

## Critical Testing Requirements

When making changes to database models or service layer:

1. **Always run the comprehensive test suite** - 49 tests covering:
   - 13 dependency service tests (circular detection, trees, blocking)
   - 17 issue service tests (CRUD, filtering, events)
   - 19 API integration tests (end-to-end workflows)

2. **Database changes require session.expunge()** calls in service methods that return objects

3. **Test isolation** - Use the `reset_database_globals()` function in test fixtures

4. **Dependency management** - All changes to dependency logic must pass circular dependency tests

## Technology Stack Context

- **UV**: Modern Python package manager and build tool
- **FastAPI**: Modern async web framework with automatic OpenAPI generation
- **SQLAlchemy 2.0**: Modern ORM with new syntax patterns
- **Alembic**: Database migration tool with automatic startup migrations
- **Pydantic**: Data validation and serialization (transitioning from v1 to v2 patterns)

The codebase uses modern Python practices with async/await where appropriate and comprehensive test coverage to ensure reliability for AI agent workflows.