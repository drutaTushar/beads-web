"""Markdown parser for issue import"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from ..models import IssueType, Status


@dataclass
class ParsedIssue:
    """Represents a parsed issue from markdown"""
    logical_id: str
    title: str
    issue_type: IssueType = IssueType.TASK
    priority: int = 2
    assignee: Optional[str] = None
    estimated_minutes: Optional[int] = None
    dependencies: List[str] = None
    parent_logical_id: Optional[str] = None
    depth: int = 0
    
    # Detailed content fields
    description: str = ""
    design: str = ""
    acceptance_criteria: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ParseResult:
    """Result of markdown parsing"""
    issues: List[ParsedIssue]
    errors: List[str]
    warnings: List[str]
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class MarkdownParser:
    """Parser for markdown issue import format"""
    
    # Pattern to match issue lines: - [id] Title, t=Type, p=Priority, deps=[id1,id2]
    ISSUE_PATTERN = re.compile(r'^(\s*)-\s*\[([^\]]+)\]\s*([^,]+?)(?:,\s*(.+))?$')
    
    # Pattern to match detailed content sections: ## logical_id
    CONTENT_SECTION_PATTERN = re.compile(r'^##\s+([^\s]+)$')
    
    # Pattern to match content subsections: ### field_name
    CONTENT_SUBSECTION_PATTERN = re.compile(r'^###\s+([^\s]+)$')
    
    # Valid content fields
    VALID_CONTENT_FIELDS = {'description', 'design', 'acceptance_criteria', 'notes'}
    
    def __init__(self):
        self.issues: Dict[str, ParsedIssue] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse(self, markdown_content: str) -> ParseResult:
        """Parse markdown content and return parsed issues"""
        self.issues = {}
        self.errors = []
        self.warnings = []
        
        lines = markdown_content.split('\n')
        
        # Find section boundaries
        structure_start = self._find_section_start(lines, "Issues Structure")
        content_start = self._find_section_start(lines, "Detailed Content")
        
        if structure_start is None:
            self.errors.append("Missing '# Issues Structure' section")
            return ParseResult([], self.errors, self.warnings)
        
        # Parse issues structure
        structure_end = content_start if content_start else len(lines)
        self._parse_issues_structure(lines[structure_start:structure_end])
        
        # Parse detailed content if available
        if content_start is not None:
            self._parse_detailed_content(lines[content_start:])
        
        # Validate parsed issues
        self._validate_issues()
        
        return ParseResult(list(self.issues.values()), self.errors, self.warnings)
    
    def _find_section_start(self, lines: List[str], section_name: str) -> Optional[int]:
        """Find the start line of a section"""
        pattern = re.compile(f'^#\\s+{re.escape(section_name)}', re.IGNORECASE)
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                return i + 1  # Return line after the header
        return None
    
    def _parse_issues_structure(self, lines: List[str]) -> None:
        """Parse the issues structure section"""
        parent_stack: List[Tuple[str, int]] = []  # (logical_id, depth)
        
        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            
            match = self.ISSUE_PATTERN.match(line)
            if not match:
                # Skip non-issue lines silently (could be comments or empty lines)
                continue
            
            indent, logical_id, title, params_str = match.groups()
            # Calculate depth by counting leading spaces, each 4 spaces = 1 level
            depth = len(indent) // 4 if indent else 0
            
            # Validate logical ID
            if not logical_id or not logical_id.strip():
                self.errors.append(f"Line {line_num}: Empty logical ID")
                continue
            
            logical_id = logical_id.strip()
            if logical_id in self.issues:
                self.errors.append(f"Line {line_num}: Duplicate logical ID '{logical_id}'")
                continue
            
            # Clean up title
            title = title.strip()
            if not title:
                self.errors.append(f"Line {line_num}: Empty title for issue '{logical_id}'")
                continue
            
            # Parse parameters
            issue_type, priority, assignee, estimated_minutes, dependencies = self._parse_parameters(
                params_str, logical_id, line_num
            )
            
            # Determine parent from hierarchy
            parent_logical_id = None
            if depth > 0:
                # Find parent at the previous depth level
                while parent_stack and parent_stack[-1][1] >= depth:
                    parent_stack.pop()
                
                if parent_stack:
                    parent_logical_id = parent_stack[-1][0]
                else:
                    self.warnings.append(
                        f"Line {line_num}: Issue '{logical_id}' is indented but has no parent"
                    )
            
            # Create parsed issue
            parsed_issue = ParsedIssue(
                logical_id=logical_id,
                title=title,
                issue_type=issue_type,
                priority=priority,
                assignee=assignee,
                estimated_minutes=estimated_minutes,
                dependencies=dependencies,
                parent_logical_id=parent_logical_id,
                depth=depth
            )
            
            self.issues[logical_id] = parsed_issue
            
            # Update parent stack
            parent_stack.append((logical_id, depth))
    
    def _parse_parameters(self, params_str: Optional[str], logical_id: str, line_num: int) -> Tuple:
        """Parse issue parameters from the parameter string"""
        issue_type = IssueType.TASK
        priority = 2
        assignee = None
        estimated_minutes = None
        dependencies = []
        
        if not params_str:
            return issue_type, priority, assignee, estimated_minutes, dependencies
        
        # Smart split that handles deps=[a,b,c] format
        params = self._smart_split_parameters(params_str)
        
        for param in params:
            if '=' not in param:
                self.warnings.append(
                    f"Line {line_num}: Invalid parameter format '{param}' for issue '{logical_id}'"
                )
                continue
            
            key, value = param.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            try:
                if key == 't':
                    issue_type = self._parse_issue_type(value, logical_id, line_num)
                elif key == 'p':
                    priority = self._parse_priority(value, logical_id, line_num)
                elif key == 'assignee':
                    assignee = value if value else None
                elif key == 'est':
                    estimated_minutes = self._parse_estimate(value, logical_id, line_num)
                elif key == 'deps':
                    dependencies = self._parse_dependencies(value, logical_id, line_num)
                else:
                    self.warnings.append(
                        f"Line {line_num}: Unknown parameter '{key}' for issue '{logical_id}'"
                    )
            except Exception as e:
                self.errors.append(
                    f"Line {line_num}: Error parsing parameter '{key}' for issue '{logical_id}': {e}"
                )
        
        return issue_type, priority, assignee, estimated_minutes, dependencies
    
    def _smart_split_parameters(self, params_str: str) -> List[str]:
        """Split parameters by comma, but respect brackets for deps=[a,b,c] format"""
        params = []
        current_param = ""
        bracket_depth = 0
        
        for char in params_str:
            if char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                # Split here - we're not inside brackets
                if current_param.strip():
                    params.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        # Add the last parameter
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _parse_issue_type(self, value: str, logical_id: str, line_num: int) -> IssueType:
        """Parse issue type from string"""
        try:
            # Handle case-insensitive matching
            for issue_type in IssueType:
                if issue_type.value.lower() == value.lower():
                    return issue_type
            
            self.warnings.append(
                f"Line {line_num}: Invalid issue type '{value}' for issue '{logical_id}', using 'task'"
            )
            return IssueType.TASK
        except Exception:
            self.warnings.append(
                f"Line {line_num}: Error parsing issue type '{value}' for issue '{logical_id}', using 'task'"
            )
            return IssueType.TASK
    
    def _parse_priority(self, value: str, logical_id: str, line_num: int) -> int:
        """Parse priority from string"""
        try:
            priority = int(value)
            if 0 <= priority <= 4:
                return priority
            else:
                self.warnings.append(
                    f"Line {line_num}: Priority '{value}' out of range (0-4) for issue '{logical_id}', using 2"
                )
                return 2
        except ValueError:
            self.warnings.append(
                f"Line {line_num}: Invalid priority '{value}' for issue '{logical_id}', using 2"
            )
            return 2
    
    def _parse_estimate(self, value: str, logical_id: str, line_num: int) -> Optional[int]:
        """Parse time estimate from string"""
        try:
            estimate = int(value)
            if estimate > 0:
                return estimate
            else:
                self.warnings.append(
                    f"Line {line_num}: Invalid estimate '{value}' for issue '{logical_id}', ignoring"
                )
                return None
        except ValueError:
            self.warnings.append(
                f"Line {line_num}: Invalid estimate '{value}' for issue '{logical_id}', ignoring"
            )
            return None
    
    def _parse_dependencies(self, value: str, logical_id: str, line_num: int) -> List[str]:
        """Parse dependencies from string like [id1,id2,id3]"""
        if not value:
            return []
        
        # Remove brackets and split by comma
        value = value.strip()
        if value.startswith('[') and value.endswith(']'):
            value = value[1:-1]
        
        if not value:
            return []
        
        dependencies = [dep.strip() for dep in value.split(',')]
        dependencies = [dep for dep in dependencies if dep]  # Remove empty strings
        
        return dependencies
    
    def _parse_detailed_content(self, lines: List[str]) -> None:
        """Parse the detailed content section"""
        current_issue_id = None
        current_field = None
        content_lines = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()
            
            # Check for issue section header: ## logical_id
            section_match = self.CONTENT_SECTION_PATTERN.match(line)
            if section_match:
                # Save previous content if any
                if current_issue_id and current_field and content_lines:
                    self._save_content(current_issue_id, current_field, content_lines)
                
                current_issue_id = section_match.group(1)
                current_field = None
                content_lines = []
                
                if current_issue_id not in self.issues:
                    self.warnings.append(
                        f"Detailed content section for unknown issue '{current_issue_id}'"
                    )
                    current_issue_id = None
                continue
            
            # Check for field subsection header: ### field_name
            subsection_match = self.CONTENT_SUBSECTION_PATTERN.match(line)
            if subsection_match:
                # Save previous content if any
                if current_issue_id and current_field and content_lines:
                    self._save_content(current_issue_id, current_field, content_lines)
                
                current_field = subsection_match.group(1)
                content_lines = []
                
                if current_field not in self.VALID_CONTENT_FIELDS:
                    self.warnings.append(
                        f"Unknown content field '{current_field}' for issue '{current_issue_id}'"
                    )
                    current_field = None
                continue
            
            # Collect content lines
            if current_issue_id and current_field:
                content_lines.append(line)
        
        # Save final content
        if current_issue_id and current_field and content_lines:
            self._save_content(current_issue_id, current_field, content_lines)
    
    def _save_content(self, logical_id: str, field: str, lines: List[str]) -> None:
        """Save content to the appropriate field of the issue"""
        if logical_id not in self.issues:
            return
        
        # Join lines and strip trailing whitespace
        content = '\n'.join(lines).strip()
        
        issue = self.issues[logical_id]
        if field == 'description':
            issue.description = content
        elif field == 'design':
            issue.design = content
        elif field == 'acceptance_criteria':
            issue.acceptance_criteria = content
        elif field == 'notes':
            issue.notes = content
    
    def _validate_issues(self) -> None:
        """Validate parsed issues for consistency and correctness"""
        # Check dependency references
        for issue in self.issues.values():
            for dep_id in issue.dependencies:
                if dep_id not in self.issues:
                    self.errors.append(
                        f"Issue '{issue.logical_id}' depends on unknown issue '{dep_id}'"
                    )
        
        # Check for circular dependencies
        self._check_circular_dependencies()
        
        # Check type hierarchy rules for parent-child relationships
        self._validate_type_hierarchy()
    
    def _check_circular_dependencies(self) -> None:
        """Check for circular dependencies in the dependency graph"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(issue_id: str) -> bool:
            if issue_id in rec_stack:
                return True
            if issue_id in visited:
                return False
            
            visited.add(issue_id)
            rec_stack.add(issue_id)
            
            issue = self.issues.get(issue_id)
            if issue:
                for dep_id in issue.dependencies:
                    if dep_id in self.issues and has_cycle(dep_id):
                        return True
            
            rec_stack.remove(issue_id)
            return False
        
        for issue_id in self.issues:
            if issue_id not in visited:
                if has_cycle(issue_id):
                    self.errors.append(f"Circular dependency detected involving issue '{issue_id}'")
                    break
    
    def _validate_type_hierarchy(self) -> None:
        """Validate parent-child type relationships"""
        valid_combinations = {
            IssueType.EPIC: [IssueType.FEATURE, IssueType.TASK, IssueType.BUG, IssueType.CHORE],
            IssueType.FEATURE: [IssueType.TASK, IssueType.FEATURE],
            IssueType.TASK: [IssueType.TASK, IssueType.CHORE],
            IssueType.BUG: [IssueType.TASK],
            IssueType.CHORE: [IssueType.TASK, IssueType.CHORE]
        }
        
        for issue in self.issues.values():
            if issue.parent_logical_id:
                parent = self.issues.get(issue.parent_logical_id)
                if parent:
                    allowed_children = valid_combinations.get(parent.issue_type, [])
                    if issue.issue_type not in allowed_children:
                        self.errors.append(
                            f"Invalid type hierarchy: {parent.issue_type.value} '{parent.logical_id}' "
                            f"cannot have {issue.issue_type.value} '{issue.logical_id}' as child"
                        )