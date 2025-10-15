"""Issue ID generation with collision detection"""

import random
import string
from .migrations import get_project_config
from .database import get_db_session
from ..models import Issue

def generate_random_string(length: int = 4) -> str:
    """Generate random alphanumeric string"""
    # Use lowercase letters and numbers for readability
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def issue_exists(issue_id: str) -> bool:
    """Check if issue ID already exists"""
    try:
        with get_db_session() as session:
            return session.query(Issue).filter(Issue.id == issue_id).first() is not None
    except Exception:
        # If we can't check (e.g., database not initialized), assume it doesn't exist
        return False

def generate_issue_id() -> str:
    """Generate unique issue ID with collision detection"""
    config = get_project_config()
    prefix = config.get("project_prefix", "at")
    
    # Try up to 10 times to generate a unique ID
    for _ in range(10):
        random_suffix = generate_random_string(4)
        candidate_id = f"{prefix}-{random_suffix}"
        
        if not issue_exists(candidate_id):
            return candidate_id
    
    # If we still have collisions after 10 tries, use a longer suffix
    random_suffix = generate_random_string(8)
    candidate_id = f"{prefix}-{random_suffix}"
    
    # This should be extremely unlikely to collide
    if issue_exists(candidate_id):
        # Last resort: add timestamp
        import time
        timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
        candidate_id = f"{prefix}-{random_suffix}-{timestamp}"
    
    return candidate_id

def get_next_sequence_number() -> int:
    """Get next sequence number for collision resolution"""
    try:
        with get_db_session() as session:
            max_seq = session.query(Issue.sequence).order_by(Issue.sequence.desc()).first()
            if max_seq and max_seq[0] is not None:
                return max_seq[0] + 1
            return 1
    except Exception:
        # If we can't check, start from 1
        return 1