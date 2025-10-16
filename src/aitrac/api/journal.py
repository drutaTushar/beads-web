"""Journal API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import os
import json
import glob
from pathlib import Path

from ..storage.issue_service import issue_service
from .schemas import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalListResponse,
    SuccessResponse
)

router = APIRouter()

def get_journal_dir():
    """Get the journal directory path"""
    journal_dir = Path(".aitrac/journal/entries")
    journal_dir.mkdir(parents=True, exist_ok=True)
    return journal_dir

def generate_journal_id(timestamp: datetime) -> str:
    """Generate unique journal entry ID"""
    from ..storage.id_generator import generate_random_string
    date_str = timestamp.strftime("%Y-%m-%d-%H-%M")
    unique_id = generate_random_string(6)  # Short unique suffix
    return f"journal-{date_str}-{unique_id}"

@router.post("/entries", response_model=JournalEntryResponse)
async def create_journal_entry(entry: JournalEntryCreate):
    """Create a new journal entry"""
    
    # Generate entry ID and timestamp
    timestamp = datetime.utcnow()
    entry_id = generate_journal_id(timestamp)
    
    # Enrich with issue details
    enriched_issues = []
    for issue_id in entry.issue_ids:
        issue = issue_service.get_issue(issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail=f"Issue not found: {issue_id}")
        
        enriched_issues.append({
            "id": issue.id,
            "title": issue.title,
            "description": issue.description or ""
        })
    
    # Create journal entry
    journal_entry = {
        "id": entry_id,
        "title": entry.title,
        "summary": entry.summary,
        "timestamp": timestamp.isoformat(),
        "issues": enriched_issues,
        "files_modified": entry.files_modified
    }
    
    # Save to file
    journal_dir = get_journal_dir()
    entry_file = journal_dir / f"{entry_id}.json"
    
    try:
        with open(entry_file, 'w') as f:
            json.dump(journal_entry, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save journal entry: {str(e)}")
    
    return JournalEntryResponse(**journal_entry)

@router.get("/entries", response_model=JournalListResponse)
async def list_journal_entries(
    search: Optional[str] = Query(None, description="Search in title, summary, or issue details"),
    issue_id: Optional[str] = Query(None, description="Filter by specific issue ID"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Entries per page")
):
    """List journal entries with search and filtering"""
    
    journal_dir = get_journal_dir()
    
    # Load all entries
    all_entries = []
    entry_files = glob.glob(str(journal_dir / "*.json"))
    
    for entry_file in entry_files:
        try:
            with open(entry_file, 'r') as f:
                entry = json.load(f)
                all_entries.append(entry)
        except Exception as e:
            # Skip corrupted files
            continue
    
    # Sort by timestamp (newest first)
    all_entries.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Apply filters
    filtered_entries = []
    for entry in all_entries:
        # Issue ID filter
        if issue_id:
            if not any(issue['id'] == issue_id for issue in entry['issues']):
                continue
        
        # File path filter
        if file_path:
            if file_path not in entry['files_modified']:
                continue
        
        # Search filter
        if search:
            search_text = search.lower()
            searchable_content = [
                entry['title'].lower(),
                entry['summary'].lower(),
            ]
            
            # Add issue titles and descriptions to search
            for issue in entry['issues']:
                searchable_content.extend([
                    issue['title'].lower(),
                    issue['description'].lower()
                ])
            
            # Check if search term appears in any searchable content
            if not any(search_text in content for content in searchable_content):
                continue
        
        filtered_entries.append(entry)
    
    # Pagination
    total = len(filtered_entries)
    offset = (page - 1) * limit
    paginated_entries = filtered_entries[offset:offset + limit]
    
    # Convert to response models
    entries = [JournalEntryResponse(**entry) for entry in paginated_entries]
    
    return JournalListResponse(
        entries=entries,
        total=total,
        page=page,
        limit=limit,
        total_pages=(total + limit - 1) // limit
    )

@router.get("/entries/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(entry_id: str):
    """Get a specific journal entry"""
    
    journal_dir = get_journal_dir()
    entry_file = journal_dir / f"{entry_id}.json"
    
    if not entry_file.exists():
        raise HTTPException(status_code=404, detail=f"Journal entry not found: {entry_id}")
    
    try:
        with open(entry_file, 'r') as f:
            entry = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read journal entry: {str(e)}")
    
    return JournalEntryResponse(**entry)

@router.get("/entries/by-issue/{issue_id}", response_model=List[JournalEntryResponse])
async def get_journal_entries_by_issue(issue_id: str):
    """Get all journal entries that reference a specific issue"""
    
    journal_dir = get_journal_dir()
    
    # Load all entries
    matching_entries = []
    entry_files = glob.glob(str(journal_dir / "*.json"))
    
    for entry_file in entry_files:
        try:
            with open(entry_file, 'r') as f:
                entry = json.load(f)
                
                # Check if this entry references the issue
                if any(issue['id'] == issue_id for issue in entry['issues']):
                    matching_entries.append(entry)
        except Exception as e:
            # Skip corrupted files
            continue
    
    # Sort by timestamp (newest first)
    matching_entries.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Convert to response models
    entries = [JournalEntryResponse(**entry) for entry in matching_entries]
    
    return entries