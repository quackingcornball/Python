"""
Match Engine - Core cricket match logic with proper state-driven batting order management
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
    """Handles all cricket match logic with proper state management"""
    
    # Match status constants
    STATUS_NOT_STARTED = "Upcoming"
    STATUS_LIVE = "Live"
    STATUS_INNINGS_BREAK = "Innings Break"
    STATUS_COMPLETED = "Completed"
    STATUS_SUPER_OVER = "Super Over"
    
    @staticmethod
    def create_match(
        team_a: str,
        team_b: str,
        match_format: str,
        toss_winner: Optional[str] = None,
        toss_decision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new match with proper team structure"""
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
            "status": MatchEngine.STATUS_NOT_STARTED,
            "current_innings": 0,
            "innings": [],
            "target": None,
            "result": None,
            # Team rosters and batting orders
            "rosters": {
                team_a: [],
                team_b: []
            },
            "batting_orders": {
                team_a: [],
                team_b: []
            },
            # Super over tracking
            "super_over": None,
            "created_at": get_current_timestamp(),
            "last_updated": get_current_timestamp()
        }
        
        return match
    
    @staticmethod
    def validate_match_can_start(match: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that match can be started.
        Returns (can_start, error_message)
        
        STRICT RULES:
        - Each team MUST have EXACTLY 11 players in roster
        - Each team MUST have EXACTLY 11 players in batting order
        - Batting order must only contain roster players
        - No duplicates allowed in batting order
        """
        teams = match.get("teams", [])
        rosters = match.get("rosters", {})
        batting_orders = match.get("batting_orders", {})
        
        for team in teams:
            roster = rosters.get(team, [])
            batting_order = batting_orders.get(team, [])
            
            # Check EXACTLY 11 players in roster
            if len(roster) != 11:
                return False, f"{team} must have exactly 11 players in roster (currently {len(roster)})"
            
            # Check EXACTLY 11 players in batting order
            if len(batting_order) != 11:
                return False, f"{team} must have exactly 11 players in batting order (currently {len(batting_order)})"
            
            # Check for duplicates in batting order
            if len(batting_order) != len(set(batting_order)):
                return False, f"{team}'s batting order contains duplicate players"
            
            # Ensure batting order only contains roster players
            for player in batting_order:
                if player not in roster:
                    return False, f"Player '{player}' in {team}'s batting order is not in roster"
            
            # Ensure all roster players are in batting order
            for player in roster:
                if player not in batting_order:
                    return False, f"Player '{player}' from {team}'s roster is missing from batting order"
        
        return True, ""
    
    @staticmethod
    def create_innings(
        batting_team: str, 
        bowling_team: str, 
        batting_order: List[str],
        is_super_over: bool = False
    ) -> Dict[str, Any]:
        """Create a new innings with proper batting state management"""
        
        # Initialize striker and non-striker from batting order
        striker = batting_order[0] if len(batting_order) > 0 else None
        non_striker = batting_order[1] if len(batting_order) > 1 else None
        
        innings = {
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "runs": 0,
            "wickets": 0,
            "overs": 0.0,
            "balls": [],  # Ball-by-ball data
            "batsmen": [],  # All batsmen who have batted
            "bowlers": [],  # Bowlers who have bowled
            # CRITICAL: Batting state management
            "batting_order": batting_order.copy(),
            "current_batting_state": {
                "striker": None,  # Will be set when batsmen are added
                "non_striker": None,
                "next_batsman_index": 2  # Points to batting_order[2] (next to come in)
            },
            "current_bowler": None,
            "extras": {"wides": 0, "no_balls": 0, "byes": 0, "leg_byes": 0},
            "fall_of_wickets": [],
            "is_completed": False,
            "declared": False,
            "is_super_over": is_super_over,
            "max_wickets": 2 if is_super_over else 10,
            "max_overs": 1 if is_super_over else None  # Super over is 1 over (6 balls)
        }
        
        # Auto-add the first two batsmen from batting order
        if striker:
            batsman_id = MatchEngine._add_batsman_to_innings(innings, striker, on_strike=True)
            innings["current_batting_state"]["striker"] = batsman_id
        
        if non_striker:
            batsman_id = MatchEngine._add_batsman_to_innings(innings, non_striker, on_strike=False)
            innings["current_batting_state"]["non_striker"] = batsman_id
        
        return innings
    
    @staticmethod
    def _add_batsman_to_innings(innings: Dict[str, Any], name: str, on_strike: bool = False) -> str:
        """Internal method to add a batsman to the innings"""
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
            "on_strike": on_strike
        }
        innings["batsmen"].append(batsman)
        return batsman_id
    
    @staticmethod
    def start_match(match: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Start a match. Returns (match, error_message).
        If error_message is not empty, match was not started.
        """
        if match["status"] != MatchEngine.STATUS_NOT_STARTED:
            return match, "Match has already started"
        
        # Validate match can start
        can_start, error = MatchEngine.validate_match_can_start(match)
        if not can_start:
            return match, error
        
        match["status"] = MatchEngine.STATUS_LIVE
        
        # Determine batting team based on toss
        teams = match["teams"]
        first_batting = teams[0]  # Default
        first_bowling = teams[1]
        
        if match.get("toss_winner") and match.get("toss_decision"):
            if match["toss_decision"] == "bat":
                first_batting = match["toss_winner"]
                first_bowling = teams[1] if match["toss_winner"] == teams[0] else teams[0]
            else:
                first_bowling = match["toss_winner"]
                first_batting = teams[1] if match["toss_winner"] == teams[0] else teams[0]
        
        # Get batting order for first batting team
        batting_order = match.get("batting_orders", {}).get(first_batting, [])
        
        # Create first innings with batting order
        first_innings = MatchEngine.create_innings(first_batting, first_bowling, batting_order)
        match["innings"].append(first_innings)
        match["current_innings"] = 0
        match["last_updated"] = get_current_timestamp()
        
        return match, ""
    
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
    def get_batsman_by_id(innings: Dict[str, Any], batsman_id: str) -> Optional[Dict[str, Any]]:
        """Get batsman by ID"""
        for batsman in innings["batsmen"]:
            if batsman["id"] == batsman_id:
                return batsman
        return None
    
    @staticmethod
    def get_current_batsman(innings: Dict[str, Any], on_strike: bool = True) -> Optional[Dict[str, Any]]:
        """Get current batsman on strike or non-striker"""
        batting_state = innings.get("current_batting_state", {})
        
        if on_strike:
            striker_id = batting_state.get("striker")
            if striker_id:
                return MatchEngine.get_batsman_by_id(innings, striker_id)
        else:
            non_striker_id = batting_state.get("non_striker")
            if non_striker_id:
                return MatchEngine.get_batsman_by_id(innings, non_striker_id)
        
        return None
    
    @staticmethod
    def get_current_bowler(innings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current bowler"""
        if not innings.get("current_bowler"):
            return None
        for bowler in innings["bowlers"]:
            if bowler["id"] == innings["current_bowler"]:
                return bowler
        return None
    
    @staticmethod
    def _bring_next_batsman(innings: Dict[str, Any], replace_striker: bool = True) -> bool:
        """
        Bring in the next batsman from batting order.
        Returns True if successful, False if all out.
        """
        batting_state = innings["current_batting_state"]
        batting_order = innings.get("batting_order", [])
        next_index = batting_state.get("next_batsman_index", 2)
        
        # Check if there are more batsmen available
        if next_index >= len(batting_order):
            return False  # All out
        
        # Get next batsman name from batting order
        next_batsman_name = batting_order[next_index]
        
        # Add new batsman to innings
        new_batsman_id = MatchEngine._add_batsman_to_innings(
            innings, 
            next_batsman_name, 
            on_strike=replace_striker
        )
        
        # Update batting state
        if replace_striker:
            batting_state["striker"] = new_batsman_id
        else:
            batting_state["non_striker"] = new_batsman_id
        
        batting_state["next_batsman_index"] = next_index + 1
        
        return True
    
    @staticmethod
    def record_ball(
        match: Dict[str, Any],
        runs: int = 0,
        is_boundary: bool = False,
        is_six: bool = False,
        is_wicket: bool = False,
        dismissal_type: Optional[str] = None,
        extra_type: Optional[str] = None,
        extra_runs: int = 0,
        non_striker_out: bool = False  # For run out of non-striker
    ) -> Dict[str, Any]:
        """Record a ball in the current innings with proper state management"""
        innings = match["innings"][match["current_innings"]]
        
        if innings["is_completed"]:
            return match
        
        # Get current players
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        non_striker = MatchEngine.get_current_batsman(innings, on_strike=False)
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
            "is_six": is_six or runs == 6,
            "non_striker_out": non_striker_out
        }
        innings["balls"].append(ball)
        
        # Update innings totals based on proper cricket rules
        # WIDE: 1 penalty + any additional runs (ball does NOT count)
        # NO BALL: 1 penalty + runs scored (ball does NOT count)
        # BYE/LEG BYE: only runs scored (ball DOES count)
        # Normal: runs scored (ball DOES count)
        
        if extra_type == "WD":
            # Wide: 1 penalty run + additional runs (e.g., wide+4 = 5 total)
            total_runs = 1 + extra_runs
            innings["extras"]["wides"] += total_runs
        elif extra_type == "NB":
            # No Ball: 1 penalty run + runs scored by batsman
            total_runs = 1 + runs + extra_runs
            innings["extras"]["no_balls"] += 1
        elif extra_type == "BYE":
            # Bye: only runs scored, no penalty
            total_runs = extra_runs
            innings["extras"]["byes"] += extra_runs
        elif extra_type == "LB":
            # Leg Bye: only runs scored, no penalty
            total_runs = extra_runs
            innings["extras"]["leg_byes"] += extra_runs
        else:
            # Normal delivery
            total_runs = runs
        
        innings["runs"] += total_runs
        
        # Update batsman stats
        # Wide: batsman does NOT face the ball
        # No Ball: batsman DOES face the ball and gets runs
        # Bye/Leg Bye: batsman faces ball but runs don't count to batsman
        if extra_type == "WD":
            # Wide - batsman doesn't face it
            pass
        elif extra_type in ["BYE", "LB"]:
            # Byes/Leg Byes - batsman faces but doesn't score
            striker["balls"] += 1
        elif extra_type == "NB":
            # No Ball - batsman faces and scores runs
            striker["balls"] += 1
            striker["runs"] += runs + extra_runs  # Batsman gets runs off no ball
            if runs + extra_runs == 4:
                striker["fours"] += 1
            elif runs + extra_runs == 6:
                striker["sixes"] += 1
        else:
            # Normal delivery
            striker["balls"] += 1
            striker["runs"] += runs
            if runs == 4:
                striker["fours"] += 1
            elif runs == 6:
                striker["sixes"] += 1
        
        # Update bowler (only for legal deliveries)
        if extra_type not in ["WD", "NB"]:
            bowler["balls"] += 1
            if bowler["balls"] >= 6:
                bowler["overs"] = balls_to_overs(bowler["balls"])
        
        bowler["runs"] += total_runs
        
        # Handle wicket
        if is_wicket:
            innings["wickets"] += 1
            bowler["wickets"] += 1
            
            # Determine who is out
            if non_striker_out and non_striker:
                # Non-striker run out
                non_striker["is_out"] = True
                non_striker["dismissal"] = dismissal_type
                
                # Record fall of wicket
                innings["fall_of_wickets"].append({
                    "wicket": innings["wickets"],
                    "runs": innings["runs"],
                    "overs": innings["overs"],
                    "batsman": non_striker["name"]
                })
                
                # Bring in next batsman to replace non-striker
                max_wickets = innings.get("max_wickets", 10)
                if innings["wickets"] < max_wickets:
                    if not MatchEngine._bring_next_batsman(innings, replace_striker=False):
                        innings["is_completed"] = True
            else:
                # Striker is out
                striker["is_out"] = True
                striker["dismissal"] = dismissal_type
                
                # Record fall of wicket
                innings["fall_of_wickets"].append({
                    "wicket": innings["wickets"],
                    "runs": innings["runs"],
                    "overs": innings["overs"],
                    "batsman": striker["name"]
                })
                
                # Bring in next batsman to replace striker
                max_wickets = innings.get("max_wickets", 10)
                if innings["wickets"] < max_wickets:
                    if not MatchEngine._bring_next_batsman(innings, replace_striker=True):
                        innings["is_completed"] = True
        
        # Update overs (only for legal deliveries)
        if extra_type not in ["WD", "NB"]:
            current_balls += 1
            innings["overs"] = balls_to_overs(current_balls)
            
            # Rotate strike for odd runs (only if no wicket, or if wicket but runs scored)
            if not is_wicket and runs % 2 == 1:
                MatchEngine._rotate_strike(innings)
            
            # End of over - change of ends
            if current_balls % 6 == 0:
                MatchEngine._rotate_strike(innings)
        
        # Check innings completion
        MatchEngine._check_innings_completion(match)
        
        match["last_updated"] = get_current_timestamp()
        return match
    
    @staticmethod
    def _rotate_strike(innings: Dict[str, Any]) -> None:
        """Rotate strike between batsmen"""
        batting_state = innings.get("current_batting_state", {})
        
        # Swap striker and non-striker
        striker_id = batting_state.get("striker")
        non_striker_id = batting_state.get("non_striker")
        
        batting_state["striker"] = non_striker_id
        batting_state["non_striker"] = striker_id
        
        # Update on_strike flags
        for batsman in innings["batsmen"]:
            if batsman["id"] == non_striker_id:
                batsman["on_strike"] = True
            elif batsman["id"] == striker_id:
                batsman["on_strike"] = False
    
    @staticmethod
    def _check_innings_completion(match: Dict[str, Any]) -> None:
        """Check if current innings is complete"""
        innings = match["innings"][match["current_innings"]]
        total_overs = match.get("total_overs")
        max_wickets = innings.get("max_wickets", 10)
        max_overs = innings.get("max_overs") or total_overs
        
        # All out
        if innings["wickets"] >= max_wickets:
            innings["is_completed"] = True
        
        # Overs completed (for limited overs)
        if max_overs and innings["overs"] >= max_overs:
            innings["is_completed"] = True
        
        # Target achieved (2nd innings or super over)
        if match["current_innings"] > 0 and match.get("target"):
            if innings["runs"] >= match["target"]:
                innings["is_completed"] = True
                MatchEngine._complete_match(match)
                return
        
        # Start next innings if needed
        if innings["is_completed"]:
            if innings.get("is_super_over"):
                # Handle super over completion
                MatchEngine._handle_super_over_completion(match)
            elif match["current_innings"] < match["total_innings"] - 1:
                MatchEngine._start_next_innings(match)
            else:
                # Both innings complete
                MatchEngine._complete_match(match)
    
    @staticmethod
    def _start_next_innings(match: Dict[str, Any]) -> None:
        """Start the next innings"""
        current = match["innings"][match["current_innings"]]
        
        # Set target for chasing team
        if match["current_innings"] == 0:
            match["target"] = current["runs"] + 1
        
        # Swap teams
        new_batting_team = current["bowling_team"]
        new_bowling_team = current["batting_team"]
        
        # Get batting order for new batting team
        batting_order = match.get("batting_orders", {}).get(new_batting_team, [])
        
        # Create new innings
        new_innings = MatchEngine.create_innings(
            batting_team=new_batting_team,
            bowling_team=new_bowling_team,
            batting_order=batting_order
        )
        match["innings"].append(new_innings)
        match["current_innings"] += 1
        match["status"] = MatchEngine.STATUS_LIVE
    
    @staticmethod
    def _complete_match(match: Dict[str, Any]) -> None:
        """Complete the match and determine result"""
        if len(match["innings"]) < 2:
            return
        
        first_innings = match["innings"][0]
        second_innings = match["innings"][1]
        
        # Check for tie (super over needed)
        if second_innings["runs"] == first_innings["runs"] and second_innings["is_completed"]:
            # Scores are level - need super over
            match["status"] = MatchEngine.STATUS_SUPER_OVER
            MatchEngine._start_super_over(match)
            return
        
        match["status"] = MatchEngine.STATUS_COMPLETED
        
        if second_innings["runs"] >= match.get("target", 0):
            wickets_remaining = 10 - second_innings["wickets"]
            match["result"] = f"{second_innings['batting_team']} won by {wickets_remaining} wickets"
        else:
            runs_diff = first_innings["runs"] - second_innings["runs"]
            match["result"] = f"{first_innings['batting_team']} won by {runs_diff} runs"
    
    @staticmethod
    def _start_super_over(match: Dict[str, Any]) -> None:
        """Start a super over"""
        teams = match["teams"]
        
        # First team to bat in super over (team that batted second in main match)
        first_batting = match["innings"][1]["batting_team"]
        first_bowling = match["innings"][1]["bowling_team"]
        
        # Get batting orders (use first 2 batsmen for super over)
        first_batting_order = match.get("batting_orders", {}).get(first_batting, [])[:2]
        
        # Create super over innings
        super_over_1 = MatchEngine.create_innings(
            batting_team=first_batting,
            bowling_team=first_bowling,
            batting_order=first_batting_order,
            is_super_over=True
        )
        
        match["innings"].append(super_over_1)
        match["current_innings"] = len(match["innings"]) - 1
        match["super_over"] = {
            "team_a_innings": match["current_innings"],
            "team_a": first_batting,
            "team_b": first_bowling,
            "team_a_score": 0,
            "team_b_score": 0
        }
    
    @staticmethod
    def _handle_super_over_completion(match: Dict[str, Any]) -> None:
        """Handle super over innings completion"""
        super_over = match.get("super_over", {})
        current_innings = match["innings"][match["current_innings"]]
        
        if match["current_innings"] == super_over.get("team_a_innings"):
            # First super over innings completed - start second
            super_over["team_a_score"] = current_innings["runs"]
            match["target"] = current_innings["runs"] + 1
            
            # Start second team's super over
            second_batting = super_over["team_b"]
            second_bowling = super_over["team_a"]
            
            second_batting_order = match.get("batting_orders", {}).get(second_batting, [])[:2]
            
            super_over_2 = MatchEngine.create_innings(
                batting_team=second_batting,
                bowling_team=second_bowling,
                batting_order=second_batting_order,
                is_super_over=True
            )
            
            match["innings"].append(super_over_2)
            match["current_innings"] = len(match["innings"]) - 1
            super_over["team_b_innings"] = match["current_innings"]
        else:
            # Both super overs complete
            super_over["team_b_score"] = current_innings["runs"]
            
            team_a = super_over["team_a"]
            team_b = super_over["team_b"]
            team_a_score = super_over["team_a_score"]
            team_b_score = super_over["team_b_score"]
            
            if team_a_score == team_b_score:
                # Still tied - result is a draw
                match["status"] = MatchEngine.STATUS_COMPLETED
                match["result"] = "Match Tied (Super Over also tied)"
            elif team_b_score > team_a_score:
                match["status"] = MatchEngine.STATUS_COMPLETED
                match["result"] = f"{team_b} won in Super Over"
            else:
                match["status"] = MatchEngine.STATUS_COMPLETED
                match["result"] = f"{team_a} won in Super Over"
    
    @staticmethod
    def undo_last_ball(match: Dict[str, Any]) -> Dict[str, Any]:
        """Undo the last ball - simplified implementation"""
        innings = match["innings"][match["current_innings"]]
        
        if not innings["balls"]:
            return match
        
        last_ball = innings["balls"].pop()
        
        # Reverse runs
        total_runs = last_ball["runs"] + last_ball.get("extras", 0)
        innings["runs"] -= total_runs
        
        # Reverse wicket
        if last_ball.get("is_wicket"):
            innings["wickets"] -= 1
            if innings["fall_of_wickets"]:
                innings["fall_of_wickets"].pop()
            # Note: Full undo would need to restore the batsman, but this is complex
        
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
    def manually_add_batsman(innings: Dict[str, Any], name: str) -> str:
        """
        Manually add a batsman - for cases where batting order needs override.
        This should be used sparingly.
        """
        batsman_id = MatchEngine._add_batsman_to_innings(innings, name, on_strike=True)
        
        # Update batting state
        batting_state = innings.get("current_batting_state", {})
        if not batting_state.get("striker"):
            batting_state["striker"] = batsman_id
        elif not batting_state.get("non_striker"):
            batting_state["non_striker"] = batsman_id
            # Non-striker shouldn't be on strike
            for b in innings["batsmen"]:
                if b["id"] == batsman_id:
                    b["on_strike"] = False
        
        return batsman_id
    
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
                "remaining_balls": None,
                "batting_team": None,
                "bowling_team": None,
                "striker": None,
                "non_striker": None
            }
        
        innings = match["innings"][match["current_innings"]]
        runs = innings["runs"]
        wickets = innings["wickets"]
        overs = innings["overs"]
        
        run_rate = calculate_run_rate(runs, overs)
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        non_striker = MatchEngine.get_current_batsman(innings, on_strike=False)
        
        summary = {
            "score": f"{runs}/{wickets}",
            "overs": f"{overs}",
            "run_rate": run_rate,
            "target": match.get("target"),
            "required_rr": None,
            "projected": None,
            "remaining_balls": None,
            "batting_team": innings.get("batting_team"),
            "bowling_team": innings.get("bowling_team"),
            "striker": striker["name"] if striker else None,
            "non_striker": non_striker["name"] if non_striker else None
        }
        
        total_overs = innings.get("max_overs") or match.get("total_overs")
        
        if total_overs:
            remaining_overs = total_overs - overs
            summary["remaining_balls"] = calculate_remaining_balls(overs, total_overs)
            summary["projected"] = calculate_projected_score(runs, overs, total_overs)
            
            if match.get("target"):
                summary["required_rr"] = calculate_required_run_rate(
                    match["target"], runs, remaining_overs
                )
        
        return summary
