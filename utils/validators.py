"""
Input validation utilities
"""
import re
from pathlib import Path
from typing import Optional


def validate_story_format(story_text: str) -> tuple[bool, Optional[str]]:
    """
    Validate user story format
    
    Args:
        story_text: User story text
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not story_text or not story_text.strip():
        return False, "Story text cannot be empty"
    
    if len(story_text) < 50:
        return False, "Story text is too short (minimum 50 characters)"
    
    if len(story_text) > 10000:
        return False, "Story text is too long (maximum 10000 characters)"
    
    return True, None


def validate_file_upload(file_path: Path, allowed_extensions: list = None) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file
    
    Args:
        file_path: Path to uploaded file
        allowed_extensions: List of allowed file extensions (e.g., ['.txt', '.md'])
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = ['.txt', '.md', '.text']
    
    if not file_path.exists():
        return False, "File does not exist"
    
    if file_path.suffix.lower() not in allowed_extensions:
        return False, f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    # Check file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    if file_path.stat().st_size > max_size:
        return False, "File size exceeds maximum (5MB)"
    
    return True, None


def validate_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate file path to prevent path traversal attacks
    
    Args:
        path: File path to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for path traversal attempts
    if '..' in path or path.startswith('/'):
        return False, "Invalid path: path traversal not allowed"
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')', '{', '}']
    if any(char in path for char in dangerous_chars):
        return False, "Invalid path: contains dangerous characters"
    
    return True, None


def validate_execution_id(execution_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate execution ID format
    
    Args:
        execution_id: Execution identifier
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not execution_id:
        return False, "Execution ID cannot be empty"
    
    # Allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', execution_id):
        return False, "Execution ID contains invalid characters"
    
    if len(execution_id) > 100:
        return False, "Execution ID is too long (maximum 100 characters)"
    
    return True, None

