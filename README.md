# Beads Web - Issue Tracker Visualization

A web interface for visualizing beads issue tracker data with interactive dependency graphs and hierarchical views.

## Features

- **Interactive Network Graph**: Visualize issues as nodes with dependencies as directed edges
- **Dependency Filtering**: Toggle between blocks-only view and all dependency types
- **Work Queue**: Ready-to-work issues sorted by priority  
- **Issue Details Panel**: Click any issue to see full details
- **Parent-Child Hierarchy**: Tree view for epic/task relationships
- **Search & Filter**: Find issues by title or ID
- **Desktop Optimized**: Designed for large screen workflows

## Quick Start

1. **Install dependencies:**
   ```bash
   uv pip install -e .
   ```

2. **Run the application:**
   ```bash
   python run.py
   ```

3. **Open in browser:**
   ```
   http://localhost:8000
   ```

## Data Source

The application reads issues from `../.beads/issues.jsonl` (relative to the beads-web directory). This file should contain one JSON object per line with beads issue data.

## Views

### Network Graph (Default)
- Issues displayed as colored nodes (status-based)
- Node size indicates priority (larger = higher priority)  
- Dependencies shown as arrows (red = blocks, blue = related, etc.)
- Click nodes to see details and highlight dependency chains
- Drag nodes to rearrange layout

### Hierarchy View
- Parent-child relationships shown as expandable tree
- Useful for epic -> task -> subtask structures
- Click nodes to select and see details

## Controls

- **Switch View**: Toggle between graph and hierarchy
- **Show All Dependencies**: Include related/discovered dependencies (default: blocks only)
- **Search**: Filter issues by title or ID
- **Work Queue**: Shows ready-to-work issues (no blocking dependencies)

## Development

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Format code
black src/

# Sort imports  
isort src/

# Run with auto-reload
python run.py
```

## API Endpoints

- `GET /` - Main web interface
- `GET /api/issues` - All issues JSON
- `GET /api/issues/active` - Active (non-closed) issues
- `GET /api/issues/ready` - Ready-to-work issues
- `GET /api/hierarchy` - Parent-child hierarchy structure


## For distribution to other machines:

**Build the package**

```
uv build
```

**Install from wheel (recommended for distribution)**

```
uv pip install dist/beads_web-0.1.0-py3-none-any.whl
```

**install from source**

```
uv pip install dist/beads_web-0.1.0.tar.gz
```

**For development/local installation:**

Install in editable mode

```
uv pip install -e .
```

**Running the application:**

After installation, run from anywhere: `beads-web`

The built packages in dist/ can be distributed to other machines. Recipients just need to run uv pip install beads_web-0.1.0-py3-none-any.whl and they'll have the beads-web command available system-wide.
