"""
Cricket calculations using numpy and pandas
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple


def calculate_run_rate(runs: int, overs: float) -> float:
    """Calculate current run rate"""
    if overs <= 0:
        return 0.0
    return round(runs / overs, 2)


def calculate_required_run_rate(target: int, current_runs: int, remaining_overs: float) -> float:
    """Calculate required run rate to achieve target"""
    runs_needed = target - current_runs
    if remaining_overs <= 0 or runs_needed <= 0:
        return 0.0
    return round(runs_needed / remaining_overs, 2)


def calculate_strike_rate(runs: int, balls: int) -> float:
    """Calculate batsman strike rate"""
    if balls <= 0:
        return 0.0
    return round((runs / balls) * 100, 2)


def calculate_economy(runs: int, overs: float) -> float:
    """Calculate bowler economy rate"""
    if overs <= 0:
        return 0.0
    return round(runs / overs, 2)


def overs_to_balls(overs: float) -> int:
    """Convert overs (e.g., 5.3) to total balls"""
    whole_overs = int(overs)
    balls_in_partial = round((overs - whole_overs) * 10)
    return whole_overs * 6 + balls_in_partial


def balls_to_overs(balls: int) -> float:
    """Convert total balls to overs format (e.g., 33 -> 5.3)"""
    whole_overs = balls // 6
    remaining_balls = balls % 6
    return float(f"{whole_overs}.{remaining_balls}")


def calculate_projected_score(current_runs: int, current_overs: float, total_overs: int) -> int:
    """Calculate projected score based on current run rate"""
    if current_overs <= 0:
        return current_runs
    
    run_rate = current_runs / current_overs
    projected = int(run_rate * total_overs)
    return projected


def calculate_remaining_balls(current_overs: float, total_overs: int) -> int:
    """Calculate remaining balls in innings"""
    current_balls = overs_to_balls(current_overs)
    total_balls = total_overs * 6
    return max(0, total_balls - current_balls)


def create_batting_dataframe(batsmen: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create pandas DataFrame for batting statistics"""
    if not batsmen:
        return pd.DataFrame(columns=['Name', 'Runs', 'Balls', '4s', '6s', 'SR'])
    
    data = []
    for batsman in batsmen:
        sr = calculate_strike_rate(batsman.get('runs', 0), batsman.get('balls', 0))
        data.append({
            'Name': batsman.get('name', 'Unknown'),
            'Runs': batsman.get('runs', 0),
            'Balls': batsman.get('balls', 0),
            '4s': batsman.get('fours', 0),
            '6s': batsman.get('sixes', 0),
            'SR': sr
        })
    
    return pd.DataFrame(data)


def create_bowling_dataframe(bowlers: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create pandas DataFrame for bowling statistics"""
    if not bowlers:
        return pd.DataFrame(columns=['Name', 'Overs', 'Runs', 'Wickets', 'Econ'])
    
    data = []
    for bowler in bowlers:
        overs = bowler.get('overs', 0.0)
        runs = bowler.get('runs', 0)
        econ = calculate_economy(runs, overs)
        data.append({
            'Name': bowler.get('name', 'Unknown'),
            'Overs': overs,
            'Runs': runs,
            'Wickets': bowler.get('wickets', 0),
            'Econ': econ
        })
    
    return pd.DataFrame(data)


def analyze_innings(balls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze innings ball-by-ball data"""
    if not balls:
        return {
            'runs_per_over': [],
            'cumulative_runs': [],
            'wickets_timeline': [],
            'run_rate_progression': []
        }
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(balls)
    
    # Group by over
    if 'over' not in df.columns:
        return {
            'runs_per_over': [],
            'cumulative_runs': [],
            'wickets_timeline': [],
            'run_rate_progression': []
        }
    
    runs_per_over = df.groupby('over')['runs'].sum().tolist()
    cumulative_runs = np.cumsum(runs_per_over).tolist()
    
    # Wickets timeline
    wickets_df = df[df['is_wicket'] == True] if 'is_wicket' in df.columns else pd.DataFrame()
    wickets_timeline = wickets_df['over'].tolist() if not wickets_df.empty else []
    
    # Run rate progression
    run_rate_progression = []
    cumulative = 0
    for i, runs in enumerate(runs_per_over):
        cumulative += runs
        rr = cumulative / (i + 1)
        run_rate_progression.append(round(rr, 2))
    
    return {
        'runs_per_over': runs_per_over,
        'cumulative_runs': cumulative_runs,
        'wickets_timeline': wickets_timeline,
        'run_rate_progression': run_rate_progression
    }


def get_partnership_stats(balls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate partnership statistics"""
    partnerships = []
    current_partnership = {'runs': 0, 'balls': 0, 'batsmen': []}
    
    for ball in balls:
        if ball.get('is_wicket'):
            if current_partnership['runs'] > 0 or current_partnership['balls'] > 0:
                partnerships.append(current_partnership.copy())
            current_partnership = {'runs': 0, 'balls': 0, 'batsmen': []}
        else:
            current_partnership['runs'] += ball.get('runs', 0)
            current_partnership['balls'] += 1
    
    # Add current partnership if ongoing
    if current_partnership['runs'] > 0 or current_partnership['balls'] > 0:
        partnerships.append(current_partnership)
    
    return partnerships
