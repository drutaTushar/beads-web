"""FastAPI application for beads issue tracker web interface."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

try:
    from importlib.resources import files
except ImportError:
    # Fallback for older Python versions
    files = None


def get_package_dir():
    """Get the package directory for static files and templates."""
    try:
        # Try using importlib.resources first (Python 3.9+)
        package_files = files('beads_web')
        return str(package_files)
    except (ImportError, AttributeError):
        # Fallback to __file__ method
        return os.path.dirname(__file__)


def find_beads_issues_file():
    """Find .beads/issues.jsonl starting from current directory and moving up."""
    current_dir = Path.cwd()
    
    # Look in current directory and parent directories
    for path in [current_dir] + list(current_dir.parents):
        beads_file = path / ".beads" / "issues.jsonl"
        if beads_file.exists():
            return str(beads_file)
    
    # If not found, return the default path in current directory
    return ".beads/issues.jsonl"


app = FastAPI(title="Beads Web", description="Web interface for beads issue tracker")

# Get package directory for static files and templates
package_dir = get_package_dir()
static_dir = os.path.join(package_dir, "static")
templates_dir = os.path.join(package_dir, "templates")

# Mount static files and templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


def load_issues(issues_path: str = None) -> List[Dict[str, Any]]:
    """Load issues from JSONL file."""
    issues = []
    
    if issues_path is None:
        issues_path = find_beads_issues_file()
    
    issues_file = Path(issues_path)
    
    if not issues_file.exists():
        print(f"No issues file found at {issues_path}")
        return issues
    
    try:
        with open(issues_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    issue = json.loads(line)
                    issues.append(issue)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading issues: {e}")
    
    return issues


def filter_active_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out closed issues to focus on active work."""
    return [issue for issue in issues if issue.get("status") != "closed"]


def get_ready_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get issues that are ready to work on (no blocking dependencies)."""
    ready_issues = []
    
    for issue in issues:
        if issue.get("status") == "closed":
            continue
            
        # Check if issue has any blocking dependencies
        has_blocking_deps = False
        for dep in issue.get("dependencies", []):
            if dep.get("type") == "blocks":
                # Check if the blocking issue is still open
                blocking_id = dep.get("depends_on_id")
                for other_issue in issues:
                    if (other_issue["id"] == blocking_id and 
                        other_issue.get("status") != "closed"):
                        has_blocking_deps = True
                        break
        
        if not has_blocking_deps:
            ready_issues.append(issue)
    
    # Sort by priority (0 is highest)
    ready_issues.sort(key=lambda x: x.get("priority", 99))
    return ready_issues


def build_hierarchy(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build parent-child hierarchy from issues."""
    hierarchy = {"roots": [], "children": {}}
    
    # Find parent-child relationships
    for issue in issues:
        issue_id = issue["id"]
        hierarchy["children"][issue_id] = []
        
        for dep in issue.get("dependencies", []):
            if dep.get("type") == "parent-child":
                parent_id = dep.get("depends_on_id")
                if parent_id in hierarchy["children"]:
                    hierarchy["children"][parent_id].append(issue_id)
    
    # Find root issues (issues with no parents)
    for issue in issues:
        issue_id = issue["id"]
        is_root = True
        
        for other_issue in issues:
            for dep in other_issue.get("dependencies", []):
                if (dep.get("type") == "parent-child" and 
                    dep.get("depends_on_id") == issue_id):
                    is_root = False
                    break
            if not is_root:
                break
        
        if is_root:
            hierarchy["roots"].append(issue_id)
    
    return hierarchy


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with network graph and hierarchy views."""
    issues = load_issues()
    active_issues = filter_active_issues(issues)
    ready_issues = get_ready_issues(active_issues)
    hierarchy = build_hierarchy(active_issues)
    
    stats = {
        "total": len(issues),
        "open": len([i for i in issues if i.get("status") == "open"]),
        "in_progress": len([i for i in issues if i.get("status") == "in_progress"]),
        "blocked": len([i for i in issues if i.get("status") == "blocked"]),
        "closed": len([i for i in issues if i.get("status") == "closed"]),
        "ready": len(ready_issues)
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "issues": issues,  # Send ALL issues to frontend
        "active_issues": active_issues,  # Also send filtered active issues
        "ready_issues": ready_issues,
        "hierarchy": hierarchy,
        "stats": stats
    })


@app.get("/api/issues")
async def get_issues():
    """API endpoint to get all issues."""
    issues = load_issues()
    return {"issues": issues}


@app.get("/api/issues/active")
async def get_active_issues():
    """API endpoint to get active (non-closed) issues."""
    issues = load_issues()
    active_issues = filter_active_issues(issues)
    return {"issues": active_issues}


@app.get("/api/issues/ready")
async def get_ready_issues_api():
    """API endpoint to get ready-to-work issues."""
    issues = load_issues()
    active_issues = filter_active_issues(issues)
    ready_issues = get_ready_issues(active_issues)
    return {"issues": ready_issues}


@app.get("/api/hierarchy")
async def get_hierarchy():
    """API endpoint to get issue hierarchy."""
    issues = load_issues()
    active_issues = filter_active_issues(issues)
    hierarchy = build_hierarchy(active_issues)
    return hierarchy


def main():
    """Main entry point for the beads-web command."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()