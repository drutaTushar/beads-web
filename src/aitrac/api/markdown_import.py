"""Markdown import API endpoints"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import traceback

from ..storage.markdown_parser import MarkdownParser
from ..storage.issue_service import issue_service
from ..storage.dependency_service import dependency_service
from ..models import DependencyType
from ..models.issue import Issue

router = APIRouter()


@router.post("/validate")
async def validate_markdown(request: Request) -> Dict[str, Any]:
    """Validate markdown content without importing"""
    try:
        # Read raw markdown content from request body
        markdown_content = await request.body()
        markdown_text = markdown_content.decode('utf-8')
        
        if not markdown_text.strip():
            raise HTTPException(status_code=400, detail="Empty markdown content")
        
        # Parse and validate
        parser = MarkdownParser()
        result = parser.parse(markdown_text)
        
        # Return validation results
        return {
            "valid": result.is_valid,
            "issues_count": len(result.issues),
            "errors": result.errors,
            "warnings": result.warnings,
            "issues_summary": [
                {
                    "logical_id": issue.logical_id,
                    "title": issue.title,
                    "type": issue.issue_type.value,
                    "priority": issue.priority,
                    "dependencies": issue.dependencies,
                    "parent": issue.parent_logical_id
                }
                for issue in result.issues
            ]
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 encoding")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/")
async def import_markdown(request: Request) -> Dict[str, Any]:
    """Import issues from markdown content with overwrite logic"""
    try:
        # Read raw markdown content from request body
        markdown_content = await request.body()
        markdown_text = markdown_content.decode('utf-8')
        
        if not markdown_text.strip():
            raise HTTPException(status_code=400, detail="Empty markdown content")
        
        # Parse and validate markdown
        parser = MarkdownParser()
        result = parser.parse(markdown_text)
        
        # Fail fast if there are any validation errors
        if not result.is_valid:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "Markdown validation failed",
                    "errors": result.errors,
                    "warnings": result.warnings
                }
            )
        
        # Import issues
        statistics = await _import_issues(result.issues)
        
        return {
            "success": True,
            "message": "Import completed successfully",
            "statistics": statistics,
            "warnings": result.warnings
        }
        
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 encoding")
    except Exception as e:
        # Log the full traceback for debugging
        error_details = traceback.format_exc()
        print(f"Import error: {error_details}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Import failed: {str(e)}"
        )


async def _import_issues(parsed_issues: list) -> Dict[str, int]:
    """Import parsed issues into the database with overwrite logic"""
    statistics = {
        "issues_created": 0,
        "issues_updated": 0,
        "dependencies_created": 0,
        "logical_ids_processed": len(parsed_issues)
    }
    
    # First pass: Create/update all issues
    logical_to_physical_mapping = {}
    
    for parsed_issue in parsed_issues:
        # Check if issue exists by markdown_id
        existing_issue = _find_existing_issue_by_markdown_id(parsed_issue.logical_id)
        
        if existing_issue:
            # Update existing issue (overwrite strategy)
            updated_issue = issue_service.update_issue(
                issue_id=existing_issue.id,
                updates={
                    "title": parsed_issue.title,
                    "description": parsed_issue.description,
                    "design": parsed_issue.design,
                    "acceptance_criteria": parsed_issue.acceptance_criteria,
                    "notes": parsed_issue.notes,
                    "priority": parsed_issue.priority,
                    "issue_type": parsed_issue.issue_type,
                    "assignee": parsed_issue.assignee,
                    "estimated_minutes": parsed_issue.estimated_minutes,
                    "markdown_id": parsed_issue.logical_id
                },
                actor="markdown_import"
            )
            logical_to_physical_mapping[parsed_issue.logical_id] = updated_issue.id
            statistics["issues_updated"] += 1
        else:
            # Create new issue
            new_issue = issue_service.create_issue(
                title=parsed_issue.title,
                description=parsed_issue.description,
                design=parsed_issue.design,
                acceptance_criteria=parsed_issue.acceptance_criteria,
                notes=parsed_issue.notes,
                priority=parsed_issue.priority,
                issue_type=parsed_issue.issue_type,
                assignee=parsed_issue.assignee,
                estimated_minutes=parsed_issue.estimated_minutes,
                actor="markdown_import"
            )
            
            # Update with markdown_id
            issue_service.update_issue(
                issue_id=new_issue.id,
                updates={"markdown_id": parsed_issue.logical_id},
                actor="markdown_import"
            )
            
            logical_to_physical_mapping[parsed_issue.logical_id] = new_issue.id
            statistics["issues_created"] += 1
    
    # Second pass: Create dependencies and parent-child relationships
    for parsed_issue in parsed_issues:
        issue_id = logical_to_physical_mapping[parsed_issue.logical_id]
        
        # Create parent-child relationship if parent exists
        if parsed_issue.parent_logical_id:
            parent_id = logical_to_physical_mapping.get(parsed_issue.parent_logical_id)
            if parent_id:
                try:
                    dependency_service.add_dependency(
                        issue_id=issue_id,
                        depends_on_id=parent_id,
                        dependency_type=DependencyType.PARENT_CHILD,
                        actor="markdown_import"
                    )
                    statistics["dependencies_created"] += 1
                except Exception as e:
                    print(f"Warning: Failed to create parent-child relationship "
                          f"{issue_id} -> {parent_id}: {e}")
        
        # Create explicit dependency relationships
        for dep_logical_id in parsed_issue.dependencies:
            dep_physical_id = logical_to_physical_mapping.get(dep_logical_id)
            if dep_physical_id and dep_physical_id != issue_id:
                try:
                    dependency_service.add_dependency(
                        issue_id=issue_id,
                        depends_on_id=dep_physical_id,
                        dependency_type=DependencyType.BLOCKS,
                        actor="markdown_import"
                    )
                    statistics["dependencies_created"] += 1
                except Exception as e:
                    print(f"Warning: Failed to create dependency "
                          f"{issue_id} -> {dep_physical_id}: {e}")
    
    return statistics


def _find_existing_issue_by_markdown_id(markdown_id: str) -> Issue:
    """Find existing issue by markdown_id"""
    from ..storage.database import get_db_session
    from sqlalchemy import and_
    
    with get_db_session() as session:
        issue = session.query(Issue).filter(
            Issue.markdown_id == markdown_id
        ).first()
        
        if issue:
            session.expunge(issue)
        
        return issue