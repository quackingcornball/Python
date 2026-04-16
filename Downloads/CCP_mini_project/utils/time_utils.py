"""
Time utility functions
"""

from datetime import datetime


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string to datetime"""
    if not timestamp_str:
        return datetime.min
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        return datetime.min


def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as 'X seconds/minutes ago'"""
    if not timestamp_str:
        return "Never"
    
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        diff = datetime.now() - timestamp
        seconds = int(diff.total_seconds())
        
        if seconds < 0:
            return "Just now"
        elif seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        else:
            days = seconds // 86400
            return f"{days}d ago"
    except ValueError:
        return "Unknown"


def get_seconds_since(timestamp_str: str) -> float:
    """Get seconds elapsed since the given timestamp"""
    if not timestamp_str:
        return float('inf')
    
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        diff = datetime.now() - timestamp
        return diff.total_seconds()
    except ValueError:
        return float('inf')
