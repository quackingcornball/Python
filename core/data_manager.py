"""
Data Manager - handles reading and writing match data
"""

import os
from typing import Dict, Any, Optional, List
from utils.file_utils import safe_write_json, read_json, ensure_directory
from utils.time_utils import get_current_timestamp


class DataManager:
    """Manages match data persistence"""
    
    def __init__(self, data_file: str = "data/matches.json"):
        self.data_file = data_file
        self._last_timestamp: Optional[str] = None
        self._ensure_data_file()
    
    def _ensure_data_file(self) -> None:
        """Ensure data file and directory exist"""
        ensure_directory(self.data_file)
        if not os.path.exists(self.data_file):
            self._save_data({
                "matches": {},
                "last_updated": get_current_timestamp()
            })
    
    def _load_data(self) -> Dict[str, Any]:
        """Load all data from file"""
        data = read_json(self.data_file)
        if data is None:
            return {"matches": {}, "last_updated": get_current_timestamp()}
        return data
    
    def _save_data(self, data: Dict[str, Any]) -> bool:
        """Save all data to file with timestamp"""
        data["last_updated"] = get_current_timestamp()
        return safe_write_json(self.data_file, data)
    
    def get_all_matches(self) -> Dict[str, Dict[str, Any]]:
        """Get all matches"""
        data = self._load_data()
        return data.get("matches", {})
    
    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID"""
        matches = self.get_all_matches()
        return matches.get(match_id)
    
    def save_match(self, match_id: str, match_data: Dict[str, Any]) -> bool:
        """Save a match (create or update)"""
        data = self._load_data()
        match_data["last_updated"] = get_current_timestamp()
        data["matches"][match_id] = match_data
        return self._save_data(data)
    
    def delete_match(self, match_id: str) -> bool:
        """Delete a match"""
        data = self._load_data()
        if match_id in data.get("matches", {}):
            del data["matches"][match_id]
            return self._save_data(data)
        return False
    
    def get_last_updated(self) -> str:
        """Get the last updated timestamp"""
        data = self._load_data()
        return data.get("last_updated", "")
    
    def has_changed(self) -> bool:
        """Check if data has changed since last check"""
        current_timestamp = self.get_last_updated()
        if current_timestamp != self._last_timestamp:
            self._last_timestamp = current_timestamp
            return True
        return False
    
    def get_matches_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get matches filtered by status"""
        matches = self.get_all_matches()
        return [
            {"match_id": mid, **mdata}
            for mid, mdata in matches.items()
            if mdata.get("status") == status
        ]
    
    def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get all live matches"""
        return self.get_matches_by_status("Live")
    
    def get_completed_matches(self) -> List[Dict[str, Any]]:
        """Get all completed matches"""
        return self.get_matches_by_status("Completed")
    
    def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Get all upcoming matches"""
        return self.get_matches_by_status("Upcoming")
