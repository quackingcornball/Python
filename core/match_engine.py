"""
Match Engine - Core cricket match logic
"""

import uuid
from typing import Dict, Any, Optional, List, Tuple
from config import FORMATS
from utils.time_utils import get_current_timestamp
from .calculations import (
    calculate_run_rate,
    calculate_required_run_rate,
    calculate_strike_rate,
    calculate_economy,
    balls_to_overs,
    overs_to_balls,
    calculate_projected_score,
    calculate_remaining_balls
)


class MatchEngine:
    """Handles all cricket match logic"""
    
    @staticmethod
    def create_match(
        team_a: str,
        team_b: str,
        match_format: str,
        toss_winner: Optional[str] = None,
        toss_decision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new match"""
        match_id = str(uuid.uuid4())[:8]
        format_config = FORMATS.get(match_format, FORMATS["T20"])
        
        match = {
            "match_id": match_id,
            "teams": [team_a, team_b],
            "format": match_format,
            "total_overs": format_config["overs"],
            "total_innings": format_config["innings"],
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "status": "Upcoming",
            "current_innings": 0,
            "innings": [],
            "target": None,
            "result": None,
            "created_at": get_current_timestamp(),
            "last_updated": get_current_timestamp()
        }
        
        return match
    
    @staticmethod
    def create_innings(batting_team: str, bowling_team: str) -> Dict[str, Any]:
        """Create a new innings"""
        return {
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "runs": 0,
            "wickets": 0,
            "overs": 0.0,
            "balls": [],  # Ball-by-ball data
            "batsmen": [],  # Current and past batsmen
            "bowlers": [],  # Bowlers who have bowled
            "current_batsmen": [],  # IDs of current 2 batsmen
            "current_bowler": None,
            "extras": {"wides": 0, "no_balls": 0, "byes": 0, "leg_byes": 0},
            "fall_of_wickets": [],
            "is_completed": False,
            "declared": False
        }
    
    @staticmethod
    def start_match(match: Dict[str, Any]) -> Dict[str, Any]:
        """Start a match"""
        if match["status"] != "Upcoming":
            return match
        
        match["status"] = "Live"
        
        # Create first innings
        teams = match["teams"]
        first_batting = teams[0]  # Default, should be based on toss
        first_bowling = teams[1]
        
        if match.get("toss_winner") and match.get("toss_decision"):
            if match["toss_decision"] == "bat":
                first_batting = match["toss_winner"]
                first_bowling = teams[1] if match["toss_winner"] == teams[0] else teams[0]
            else:
                first_bowling = match["toss_winner"]
                first_batting = teams[1] if match["toss_winner"] == teams[0] else teams[0]
        
        first_innings = MatchEngine.create_innings(first_batting, first_bowling)
        match["innings"].append(first_innings)
        match["current_innings"] = 0
        match["last_updated"] = get_current_timestamp()
        
        return match
    
    @staticmethod
    def add_batsman(innings: Dict[str, Any], name: str) -> str:
        """Add a new batsman to the innings"""
        batsman_id = str(uuid.uuid4())[:8]
        batsman = {
            "id": batsman_id,
            "name": name,
            "runs": 0,
            "balls": 0,
            "fours": 0,
            "sixes": 0,
            "is_out": False,
            "dismissal": None,
            "on_strike": len(innings["current_batsmen"]) == 0
        }
        innings["batsmen"].append(batsman)
        
        if len(innings["current_batsmen"]) < 2:
            innings["current_batsmen"].append(batsman_id)
        
        return batsman_id
    
    @staticmethod
    def add_bowler(innings: Dict[str, Any], name: str) -> str:
        """Add a new bowler or get existing"""
        # Check if bowler already exists
        for bowler in innings["bowlers"]:
            if bowler["name"] == name:
                innings["current_bowler"] = bowler["id"]
                return bowler["id"]
        
        bowler_id = str(uuid.uuid4())[:8]
        bowler = {
            "id": bowler_id,
            "name": name,
            "overs": 0.0,
            "balls": 0,
            "maidens": 0,
            "runs": 0,
            "wickets": 0
        }
        innings["bowlers"].append(bowler)
        innings["current_bowler"] = bowler_id
        
        return bowler_id
    
    @staticmethod
    def get_current_batsman(innings: Dict[str, Any], on_strike: bool = True) -> Optional[Dict[str, Any]]:
        """Get current batsman on strike or non-striker"""
        for batsman in innings["batsmen"]:
            if batsman["id"] in innings["current_batsmen"]:
                if batsman.get("on_strike", False) == on_strike:
                    return batsman
        return None
    
    @staticmethod
    def get_current_bowler(innings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current bowler"""
        if not innings["current_bowler"]:
            return None
        for bowler in innings["bowlers"]:
            if bowler["id"] == innings["current_bowler"]:
                return bowler
        return None
    
    @staticmethod
    def record_ball(
        match: Dict[str, Any],
        runs: int = 0,
        is_boundary: bool = False,
        is_six: bool = False,
        is_wicket: bool = False,
        dismissal_type: Optional[str] = None,
        extra_type: Optional[str] = None,
        extra_runs: int = 0
    ) -> Dict[str, Any]:
        """Record a ball in the current innings"""
        innings = match["innings"][match["current_innings"]]
        
        if innings["is_completed"]:
            return match
        
        # Get current players
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not striker or not bowler:
            return match
        
        # Calculate over number
        current_balls = overs_to_balls(innings["overs"])
        over_number = current_balls // 6
        ball_in_over = current_balls % 6
        
        # Create ball record
        ball = {
            "over": over_number,
            "ball": ball_in_over + 1,
            "batsman": striker["name"],
            "bowler": bowler["name"],
            "runs": runs,
            "extras": extra_runs,
            "extra_type": extra_type,
            "is_wicket": is_wicket,
            "dismissal": dismissal_type,
            "is_boundary": is_boundary or runs == 4,
            "is_six": is_six or runs == 6
        }
        innings["balls"].append(ball)
        
        # Update innings totals
        total_runs = runs + extra_runs
        innings["runs"] += total_runs
        
        # Update extras
        if extra_type:
            if extra_type == "WD":
                innings["extras"]["wides"] += 1 + extra_runs
            elif extra_type == "NB":
                innings["extras"]["no_balls"] += 1
                innings["runs"] += 1  # No ball is always 1 extra run
            elif extra_type == "BYE":
                innings["extras"]["byes"] += extra_runs if extra_runs > 0 else 1
            elif extra_type == "LB":
                innings["extras"]["leg_byes"] += extra_runs if extra_runs > 0 else 1
        
        # Update batsman (only for non-wide deliveries)
        # For byes and leg byes, batsman faces the ball but doesn't score the runs
        if extra_type != "WD":
            striker["balls"] += 1
            # Batsman only gets runs credited for non-bye extras
            if extra_type not in ["BYE", "LB"]:
                striker["runs"] += runs
                if runs == 4:
                    striker["fours"] += 1
                elif runs == 6:
                    striker["sixes"] += 1
        
        # Update bowler (only for legal deliveries that count)
        if extra_type not in ["WD", "NB"]:
            bowler["balls"] += 1
            if bowler["balls"] >= 6:
                bowler["overs"] = balls_to_overs(bowler["balls"])
        
        bowler["runs"] += total_runs
        
        # Handle wicket
        if is_wicket:
            innings["wickets"] += 1
            striker["is_out"] = True
            striker["dismissal"] = dismissal_type
            bowler["wickets"] += 1
            
            # Record fall of wicket
            innings["fall_of_wickets"].append({
                "wicket": innings["wickets"],
                "runs": innings["runs"],
                "overs": innings["overs"],
                "batsman": striker["name"]
            })
            
            # Remove batsman from current
            innings["current_batsmen"].remove(striker["id"])
        
        # Update overs (only for legal deliveries)
        if extra_type not in ["WD", "NB"]:
            current_balls += 1
            innings["overs"] = balls_to_overs(current_balls)
            
            # Rotate strike for odd runs
            if runs % 2 == 1:
                MatchEngine._rotate_strike(innings)
            
            # End of over
            if current_balls % 6 == 0:
                MatchEngine._rotate_strike(innings)  # Change of ends
        
        # Check innings completion
        MatchEngine._check_innings_completion(match)
        
        match["last_updated"] = get_current_timestamp()
        return match
    
    @staticmethod
    def _rotate_strike(innings: Dict[str, Any]) -> None:
        """Rotate strike between batsmen"""
        for batsman in innings["batsmen"]:
            if batsman["id"] in innings["current_batsmen"]:
                batsman["on_strike"] = not batsman.get("on_strike", False)
    
    @staticmethod
    def _check_innings_completion(match: Dict[str, Any]) -> None:
        """Check if current innings is complete"""
        innings = match["innings"][match["current_innings"]]
        total_overs = match.get("total_overs")
        
        # All out
        if innings["wickets"] >= 10:
            innings["is_completed"] = True
        
        # Overs completed (for limited overs)
        if total_overs and innings["overs"] >= total_overs:
            innings["is_completed"] = True
        
        # Target achieved (2nd innings)
        if match["current_innings"] > 0 and match.get("target"):
            if innings["runs"] >= match["target"]:
                innings["is_completed"] = True
                MatchEngine._complete_match(match)
        
        # Start next innings if needed
        if innings["is_completed"] and match["current_innings"] < match["total_innings"] - 1:
            MatchEngine._start_next_innings(match)
    
    @staticmethod
    def _start_next_innings(match: Dict[str, Any]) -> None:
        """Start the next innings"""
        current = match["innings"][match["current_innings"]]
        
        # Set target for chasing team
        if match["current_innings"] == 0:
            match["target"] = current["runs"] + 1
        
        # Create new innings (swap teams)
        new_innings = MatchEngine.create_innings(
            batting_team=current["bowling_team"],
            bowling_team=current["batting_team"]
        )
        match["innings"].append(new_innings)
        match["current_innings"] += 1
    
    @staticmethod
    def _complete_match(match: Dict[str, Any]) -> None:
        """Complete the match and determine result"""
        match["status"] = "Completed"
        
        if len(match["innings"]) >= 2:
            first_innings = match["innings"][0]
            second_innings = match["innings"][1]
            
            if second_innings["runs"] >= match.get("target", 0):
                wickets_remaining = 10 - second_innings["wickets"]
                match["result"] = f"{second_innings['batting_team']} won by {wickets_remaining} wickets"
            else:
                runs_diff = first_innings["runs"] - second_innings["runs"]
                match["result"] = f"{first_innings['batting_team']} won by {runs_diff} runs"
    
    @staticmethod
    def undo_last_ball(match: Dict[str, Any]) -> Dict[str, Any]:
        """Undo the last ball"""
        innings = match["innings"][match["current_innings"]]
        
        if not innings["balls"]:
            return match
        
        # This is a simplified undo - a full implementation would restore all state
        last_ball = innings["balls"].pop()
        
        # Reverse runs
        total_runs = last_ball["runs"] + last_ball.get("extras", 0)
        innings["runs"] -= total_runs
        
        # Reverse overs if it was a legal delivery
        if last_ball.get("extra_type") not in ["WD", "NB"]:
            current_balls = overs_to_balls(innings["overs"])
            current_balls -= 1
            innings["overs"] = balls_to_overs(max(0, current_balls))
        
        match["last_updated"] = get_current_timestamp()
        return match
    
    @staticmethod
    def declare_innings(match: Dict[str, Any]) -> Dict[str, Any]:
        """Declare the current innings (Test matches only)"""
        if match["format"] != "TEST":
            return match
        
        innings = match["innings"][match["current_innings"]]
        innings["is_completed"] = True
        innings["declared"] = True
        
        MatchEngine._start_next_innings(match)
        match["last_updated"] = get_current_timestamp()
        
        return match
    
    @staticmethod
    def get_match_summary(match: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the match state"""
        if not match.get("innings"):
            return {
                "score": "0/0",
                "overs": "0.0",
                "run_rate": 0.0,
                "target": None,
                "required_rr": None,
                "projected": None,
                "remaining_balls": None
            }
        
        innings = match["innings"][match["current_innings"]]
        runs = innings["runs"]
        wickets = innings["wickets"]
        overs = innings["overs"]
        
        run_rate = calculate_run_rate(runs, overs)
        
        summary = {
            "score": f"{runs}/{wickets}",
            "overs": f"{overs}",
            "run_rate": run_rate,
            "target": match.get("target"),
            "required_rr": None,
            "projected": None,
            "remaining_balls": None
        }
        
        total_overs = match.get("total_overs")
        
        if total_overs:
            remaining_overs = total_overs - overs
            summary["remaining_balls"] = calculate_remaining_balls(overs, total_overs)
            summary["projected"] = calculate_projected_score(runs, overs, total_overs)
            
            if match.get("target"):
                summary["required_rr"] = calculate_required_run_rate(
                    match["target"], runs, remaining_overs
                )
        
        return summary
