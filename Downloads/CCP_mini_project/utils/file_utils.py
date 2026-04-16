"""
File utility functions for safe file operations
"""

import json
import os
import tempfile
import shutil
from typing import Any, Optional


def ensure_directory(file_path: str) -> None:
    """Ensure the directory for a file exists"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def safe_write_json(file_path: str, data: Any) -> bool:
    """
    Safely write JSON data to file using temp file approach
    to prevent data corruption
    """
    try:
        ensure_directory(file_path)
        
        # Write to temporary file first
        fd, temp_path = tempfile.mkstemp(suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Replace original file with temp file
            shutil.move(temp_path, file_path)
            return True
        except Exception:
            # Clean up temp file if something goes wrong
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False


def read_json(file_path: str) -> Optional[dict]:
    """Read JSON data from file"""
    try:
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {file_path}: {e}")
        return None


def file_exists(file_path: str) -> bool:
    """Check if a file exists"""
    return os.path.exists(file_path)


def get_file_modified_time(file_path: str) -> Optional[float]:
    """Get file modification time as timestamp"""
    try:
        if os.path.exists(file_path):
            return os.path.getmtime(file_path)
        return None
    except OSError:
        return None
