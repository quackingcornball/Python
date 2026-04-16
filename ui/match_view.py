"""
Match View - Core match scoring and viewing screen
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Optional, Dict, Any, List
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from config import COLORS, FONTS, PADDING, SPACING, RUN_OPTIONS, EXTRA_OPTIONS, SYNC_INTERVAL
from core.data_manager import DataManager
from core.match_engine import MatchEngine
from core.calculations import (
    create_batting_dataframe,
    create_bowling_dataframe,
    analyze_innings,
    calculate_run_rate,
    calculate_required_run_rate,
    calculate_projected_score,
    calculate_remaining_balls
)
from utils.time_utils import format_time_ago, get_seconds_since
from .components import (
    StyledButton, CardFrame, ScoreDisplay, StatusBadge,
    DataTable, BallTimeline, LiveIndicator
)


class MatchView(tk.Frame):
    """Match view for scoring (admin) or viewing (viewer)"""
    
    def __init__(
        self,
        parent,
        match_id: str,
        data_manager: DataManager,
        is_admin: bool = False,
        on_back: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLORS['background'], **kwargs)
        
        self.match_id = match_id
        self.data_manager = data_manager
        self.is_admin = is_admin
        self.on_back = on_back
        
        self.match: Optional[Dict[str, Any]] = None
        
        self._create_ui()
        self._load_match()
        self._start_sync()
    
    def _create_ui(self):
        """Create the match view UI"""
        # Header
        header = tk.Frame(self, bg=COLORS['card_bg'], padx=PADDING, pady=PADDING)
        header.pack(fill='x')
        
        if self.on_back:
            back_btn = StyledButton(
                header,
                text="< Back",
                variant='secondary',
                command=self.on_back
            )
            back_btn.pack(side='left')
        
        self.title_label = tk.Label(
            header,
            text="Match View",
            font=FONTS['heading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        self.title_label.pack(side='left', padx=(SPACING, 0))
        
        # Status badge
        self.status_badge = StatusBadge(header, status="Upcoming")
        self.status_badge.pack(side='left', padx=(SPACING, 0))
        
        # Live indicator
        self.live_indicator = LiveIndicator(header)
        self.live_indicator.pack(side='right')
        
        # Main content area
        content = tk.Frame(self, bg=COLORS['background'])
        content.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Left side - Scoreboard and tables
        left_panel = tk.Frame(content, bg=COLORS['background'])
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Scoreboard
        scoreboard_frame = CardFrame(left_panel, title="Scoreboard")
        scoreboard_frame.pack(fill='x')
        
        self.score_display = ScoreDisplay(scoreboard_frame)
        self.score_display.pack(pady=(SPACING // 2, SPACING))
        
        # Target info (for chasing)
        self.target_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        self.target_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        self.target_label = tk.Label(
            self.target_frame,
            text="",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.target_label.pack()
        
        # Insights
        insights_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        insights_frame.pack(fill='x', pady=(SPACING // 2, SPACING // 2))
        
        self.insight_labels = {}
        for key in ['projected', 'remaining', 'required_rr']:
            frame = tk.Frame(insights_frame, bg=COLORS['card_bg'])
            frame.pack(side='left', expand=True, padx=(SPACING // 2, SPACING // 2))
            
            label = tk.Label(
                frame,
                text="",
                font=FONTS['body'],
                bg=COLORS['card_bg'],
                fg=COLORS['text_secondary']
            )
            label.pack()
            self.insight_labels[key] = label
        
        # Ball timeline
        timeline_frame = CardFrame(left_panel, title="Ball Timeline")
        timeline_frame.pack(fill='x', pady=(SPACING + 4, 0))
        
        self.ball_timeline = BallTimeline(timeline_frame)
        self.ball_timeline.pack(fill='x', pady=(SPACING // 4, SPACING // 4))
        
        # Batting table
        batting_frame = CardFrame(left_panel, title="Batting")
        batting_frame.pack(fill='x', pady=(SPACING + 4, 0))
        
        self.batting_table = DataTable(
            batting_frame,
            columns=['Name', 'Runs', 'Balls', '4s', '6s', 'SR']
        )
        self.batting_table.pack(fill='both', expand=True, pady=(0, SPACING // 2))
        
        # Bowling table
        bowling_frame = CardFrame(left_panel, title="Bowling")
        bowling_frame.pack(fill='x', pady=(SPACING + 4, 0))
        
        self.bowling_table = DataTable(
            bowling_frame,
            columns=['Name', 'Overs', 'Runs', 'Wickets', 'Econ']
        )
        self.bowling_table.pack(fill='both', expand=True, pady=(0, SPACING // 2))
        
        # Right side - Controls (admin) or Charts (viewer)
        right_panel = tk.Frame(content, bg=COLORS['background'], width=420)
        right_panel.pack(side='right', fill='both', padx=(SPACING + 4, 0))
        right_panel.pack_propagate(False)
        
        if self.is_admin:
            self._create_admin_controls(right_panel)
        
        # Charts
        self._create_charts(right_panel)
    
    def _create_admin_controls(self, parent):
        """Create admin scoring controls"""
        controls_frame = CardFrame(parent, title="Scoring Controls")
        controls_frame.pack(fill='x')
        
        # Current players display
        players_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        players_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        self.striker_label = tk.Label(
            players_frame,
            text="Striker: -",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        self.striker_label.pack(anchor='w', pady=(0, 4))
        
        self.bowler_label = tk.Label(
            players_frame,
            text="Bowler: -",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.bowler_label.pack(anchor='w')
        
        # Add players buttons
        add_players_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        add_players_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        add_batsman_btn = StyledButton(
            add_players_frame,
            text="+ Batsman",
            variant='secondary',
            command=self._add_batsman
        )
        add_batsman_btn.pack(side='left')
        
        add_bowler_btn = StyledButton(
            add_players_frame,
            text="+ Bowler",
            variant='secondary',
            command=self._add_bowler
        )
        add_bowler_btn.pack(side='left', padx=(SPACING // 2, 0))
        
        # Run buttons
        runs_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        runs_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            runs_frame,
            text="Runs:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        ).pack(side='left', padx=(0, SPACING // 2))
        
        for runs in RUN_OPTIONS:
            btn = StyledButton(
                runs_frame,
                text=str(runs),
                variant='success' if runs in [4, 6] else 'secondary',
                command=lambda r=runs: self._record_runs(r)
            )
            btn.pack(side='left', padx=(6, 0))
        
        # Extras buttons
        extras_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        extras_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            extras_frame,
            text="Extras:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        ).pack(side='left', padx=(0, SPACING // 2))
        
        for extra in EXTRA_OPTIONS:
            btn = StyledButton(
                extras_frame,
                text=extra,
                variant='warning',
                command=lambda e=extra: self._record_extra(e)
            )
            btn.pack(side='left', padx=(6, 0))
        
        # Wicket button
        wicket_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        wicket_btn = StyledButton(
            wicket_frame,
            text="WICKET",
            variant='danger',
            command=self._record_wicket
        )
        wicket_btn.pack(fill='x', ipady=4)
        
        # Action buttons
        actions_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        actions_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        undo_btn = StyledButton(
            actions_frame,
            text="Undo",
            variant='secondary',
            command=self._undo_ball
        )
        undo_btn.pack(side='left')
        
        end_over_btn = StyledButton(
            actions_frame,
            text="End Over",
            variant='secondary',
            command=self._end_over
        )
        end_over_btn.pack(side='left', padx=(SPACING // 2, 0))
        
        self.declare_btn = StyledButton(
            actions_frame,
            text="Declare",
            variant='primary',
            command=self._declare_innings
        )
        self.declare_btn.pack(side='right')
    
    def _create_charts(self, parent):
        """Create charts section"""
        charts_frame = CardFrame(parent, title="Analysis")
        charts_frame.pack(fill='both', expand=True, pady=(SPACING, 0))
        
        # Create matplotlib figure with larger size
        self.fig = Figure(figsize=(5, 7), dpi=90)
        self.fig.patch.set_facecolor(COLORS['card_bg'])
        
        # Run rate chart with more spacing
        self.rr_ax = self.fig.add_subplot(211)
        self.rr_ax.set_title('Run Rate Progression', fontsize=12, pad=12, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        # Runs per over chart
        self.rpo_ax = self.fig.add_subplot(212)
        self.rpo_ax.set_title('Runs per Over', fontsize=12, pad=12, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        # Add more padding between subplots
        self.fig.tight_layout(pad=3.0, h_pad=4.0)
        
        self.canvas = FigureCanvasTkAgg(self.fig, charts_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, pady=(SPACING // 2, 0))
    
    def _load_match(self):
        """Load match data"""
        self.match = self.data_manager.get_match(self.match_id)
        if self.match:
            self._update_ui()
    
    def _update_ui(self):
        """Update all UI components with current match data"""
        if not self.match:
            return
        
        # Update title
        teams = self.match.get('teams', ['Team A', 'Team B'])
        self.title_label.configure(text=f"{teams[0]} vs {teams[1]}")
        
        # Update status
        status = self.match.get('status', 'Upcoming')
        self.status_badge.set_status(status)
        
        # Get current innings
        innings_list = self.match.get('innings', [])
        current_idx = self.match.get('current_innings', 0)
        
        if not innings_list or current_idx >= len(innings_list):
            # No innings yet
            self.score_display.update_score(0, 0, 0.0, 0.0)
            return
        
        innings = innings_list[current_idx]
        runs = innings.get('runs', 0)
        wickets = innings.get('wickets', 0)
        overs = innings.get('overs', 0.0)
        
        # Calculate run rate
        run_rate = calculate_run_rate(runs, overs) if overs > 0 else 0.0
        
        # Update score display
        self.score_display.update_score(runs, wickets, overs, run_rate)
        
        # Update target info
        target = self.match.get('target')
        if target and current_idx > 0:
            runs_needed = target - runs
            self.target_label.configure(text=f"Target: {target} | Need: {runs_needed} runs")
            
            # Required run rate
            total_overs = self.match.get('total_overs', 20)
            remaining_overs = max(0, total_overs - overs)
            required_rr = calculate_required_run_rate(target, runs, remaining_overs)
            self.insight_labels['required_rr'].configure(text=f"Req RR: {required_rr:.2f}")
        else:
            self.target_label.configure(text="")
            self.insight_labels['required_rr'].configure(text="")
        
        # Update insights
        total_overs = self.match.get('total_overs')
        if total_overs:
            projected = calculate_projected_score(runs, overs, total_overs)
            remaining = calculate_remaining_balls(overs, total_overs)
            
            self.insight_labels['projected'].configure(text=f"Projected: {projected}")
            self.insight_labels['remaining'].configure(text=f"Balls left: {remaining}")
        else:
            self.insight_labels['projected'].configure(text="")
            self.insight_labels['remaining'].configure(text="")
        
        # Update ball timeline
        self.ball_timeline.clear()
        for ball in innings.get('balls', []):
            self.ball_timeline.add_ball(
                runs=ball.get('runs', 0),
                is_wicket=ball.get('is_wicket', False),
                extra_type=ball.get('extra_type')
            )
        
        # Update batting table
        batsmen = innings.get('batsmen', [])
        batting_data = []
        for batsman in batsmen:
            balls = batsman.get('balls', 0)
            runs_b = batsman.get('runs', 0)
            sr = (runs_b / balls * 100) if balls > 0 else 0.0
            
            name = batsman.get('name', 'Unknown')
            if batsman['id'] in innings.get('current_batsmen', []):
                name += " *" if batsman.get('on_strike') else ""
            elif batsman.get('is_out'):
                name += " (out)"
            
            batting_data.append([
                name,
                runs_b,
                balls,
                batsman.get('fours', 0),
                batsman.get('sixes', 0),
                f"{sr:.1f}"
            ])
        self.batting_table.set_data(batting_data)
        
        # Update bowling table
        bowlers = innings.get('bowlers', [])
        bowling_data = []
        for bowler in bowlers:
            overs_b = bowler.get('overs', 0.0)
            runs_b = bowler.get('runs', 0)
            econ = (runs_b / overs_b) if overs_b > 0 else 0.0
            
            name = bowler.get('name', 'Unknown')
            if bowler['id'] == innings.get('current_bowler'):
                name += " *"
            
            bowling_data.append([
                name,
                overs_b,
                runs_b,
                bowler.get('wickets', 0),
                f"{econ:.1f}"
            ])
        self.bowling_table.set_data(bowling_data)
        
        # Update admin controls
        if self.is_admin:
            striker = MatchEngine.get_current_batsman(innings, on_strike=True)
            self.striker_label.configure(
                text=f"Striker: {striker['name'] if striker else '-'}"
            )
            
            bowler = MatchEngine.get_current_bowler(innings)
            self.bowler_label.configure(
                text=f"Bowler: {bowler['name'] if bowler else '-'}"
            )
            
            # Show/hide declare button
            if self.match.get('format') == 'TEST':
                self.declare_btn.pack(side='right')
            else:
                self.declare_btn.pack_forget()
        
        # Update charts
        self._update_charts(innings)
    
    def _update_charts(self, innings: Dict[str, Any]):
        """Update the charts"""
        analysis = analyze_innings(innings.get('balls', []))
        
        # Clear axes
        self.rr_ax.clear()
        self.rpo_ax.clear()
        
        # Run rate progression
        rr_data = analysis.get('run_rate_progression', [])
        if rr_data:
            overs_x = list(range(1, len(rr_data) + 1))
            self.rr_ax.plot(overs_x, rr_data, color=COLORS['primary'], linewidth=2.5, marker='o', markersize=5)
            self.rr_ax.fill_between(overs_x, rr_data, alpha=0.2, color=COLORS['primary'])
            self.rr_ax.set_xlabel('Overs', fontsize=11, labelpad=8)
            self.rr_ax.set_ylabel('Run Rate', fontsize=11, labelpad=8)
            self.rr_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rr_ax.grid(True, alpha=0.3, linestyle='--')
        
        self.rr_ax.set_title('Run Rate Progression', fontsize=13, pad=14, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        # Runs per over
        rpo_data = analysis.get('runs_per_over', [])
        if rpo_data:
            overs_x = list(range(1, len(rpo_data) + 1))
            colors = [COLORS['runs'] if r >= 10 else COLORS['primary'] for r in rpo_data]
            self.rpo_ax.bar(overs_x, rpo_data, color=colors, edgecolor='none', width=0.7)
            self.rpo_ax.set_xlabel('Overs', fontsize=11, labelpad=8)
            self.rpo_ax.set_ylabel('Runs', fontsize=11, labelpad=8)
            self.rpo_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rpo_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            # Mark wickets
            wickets = analysis.get('wickets_timeline', [])
            for w in wickets:
                if w < len(overs_x):
                    self.rpo_ax.axvline(x=w + 1, color=COLORS['wickets'], linestyle='--', linewidth=2, alpha=0.8)
        
        self.rpo_ax.set_title('Runs per Over', fontsize=13, pad=14, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        self.fig.tight_layout(pad=3.0, h_pad=4.0)
        self.canvas.draw()
    
    def _add_batsman(self):
        """Add a new batsman"""
        if not self.match:
            return
        
        name = simpledialog.askstring("Add Batsman", "Enter batsman name:")
        if name:
            innings = self.match['innings'][self.match['current_innings']]
            MatchEngine.add_batsman(innings, name.strip())
            self._save_and_refresh()
    
    def _add_bowler(self):
        """Add or select bowler"""
        if not self.match:
            return
        
        name = simpledialog.askstring("Add Bowler", "Enter bowler name:")
        if name:
            innings = self.match['innings'][self.match['current_innings']]
            MatchEngine.add_bowler(innings, name.strip())
            self._save_and_refresh()
    
    def _record_runs(self, runs: int):
        """Record runs scored"""
        if not self.match or not self._validate_players():
            return
        
        is_boundary = runs == 4
        is_six = runs == 6
        
        self.match = MatchEngine.record_ball(
            self.match,
            runs=runs,
            is_boundary=is_boundary,
            is_six=is_six
        )
        self._save_and_refresh()
    
    def _record_extra(self, extra_type: str):
        """Record an extra"""
        if not self.match:
            return
        
        # For wides and no balls, ask for additional runs
        extra_runs = 0
        if extra_type in ['WD', 'NB']:
            result = simpledialog.askinteger(
                "Additional Runs",
                f"Additional runs with {extra_type}:",
                initialvalue=0,
                minvalue=0,
                maxvalue=6
            )
            if result is not None:
                extra_runs = result
        
        innings = self.match['innings'][self.match['current_innings']]
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not striker and extra_type not in ['WD', 'NB']:
            messagebox.showwarning("Warning", "Please add batsmen first.")
            return
        
        if not bowler:
            messagebox.showwarning("Warning", "Please add a bowler first.")
            return
        
        self.match = MatchEngine.record_ball(
            self.match,
            extra_type=extra_type,
            extra_runs=extra_runs
        )
        self._save_and_refresh()
    
    def _record_wicket(self):
        """Record a wicket"""
        if not self.match or not self._validate_players():
            return
        
        dismissal_types = ['Bowled', 'Caught', 'LBW', 'Run Out', 'Stumped', 'Hit Wicket']
        
        # Simple dialog for dismissal type
        dismissal = simpledialog.askstring(
            "Wicket",
            f"Dismissal type ({', '.join(dismissal_types)}):",
            initialvalue="Bowled"
        )
        
        if dismissal:
            self.match = MatchEngine.record_ball(
                self.match,
                is_wicket=True,
                dismissal_type=dismissal
            )
            self._save_and_refresh()
    
    def _undo_ball(self):
        """Undo the last ball"""
        if not self.match:
            return
        
        if messagebox.askyesno("Confirm", "Undo the last ball?"):
            self.match = MatchEngine.undo_last_ball(self.match)
            self._save_and_refresh()
    
    def _end_over(self):
        """End the current over (for manual adjustment if needed)"""
        messagebox.showinfo("Info", "Overs are automatically tracked. Use Undo if needed.")
    
    def _declare_innings(self):
        """Declare the innings (Test match only)"""
        if not self.match:
            return
        
        if self.match.get('format') != 'TEST':
            messagebox.showwarning("Warning", "Declaration is only for Test matches.")
            return
        
        if messagebox.askyesno("Confirm", "Declare this innings?"):
            self.match = MatchEngine.declare_innings(self.match)
            self._save_and_refresh()
    
    def _validate_players(self) -> bool:
        """Validate that required players are set"""
        if not self.match:
            return False
        
        innings = self.match['innings'][self.match['current_innings']]
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not striker:
            messagebox.showwarning("Warning", "Please add batsmen first (need 2 at crease).")
            return False
        
        if len(innings.get('current_batsmen', [])) < 2:
            messagebox.showwarning("Warning", "Need 2 batsmen at the crease.")
            return False
        
        if not bowler:
            messagebox.showwarning("Warning", "Please add a bowler first.")
            return False
        
        return True
    
    def _save_and_refresh(self):
        """Save match and refresh UI"""
        if self.match:
            self.data_manager.save_match(self.match_id, self.match)
            self._update_ui()
    
    def _start_sync(self):
        """Start sync loop for viewer mode"""
        if not self.is_admin:
            self._sync()
    
    def _sync(self):
        """Check for updates"""
        last_updated = self.data_manager.get_last_updated()
        seconds_since = get_seconds_since(last_updated)
        
        if self.data_manager.has_changed():
            self._load_match()
        
        # Update live indicator
        if seconds_since == float('inf') or seconds_since > 60:
            self.live_indicator.set_warning("No data")
        elif seconds_since > 5:
            self.live_indicator.set_warning(f"Stale ({int(seconds_since)}s)")
        else:
            self.live_indicator.set_live(True, format_time_ago(last_updated))
            self.live_indicator.blink()
        
        # Schedule next sync
        self.after(SYNC_INTERVAL, self._sync)
    
    def refresh(self):
        """Public method to force refresh"""
        self._load_match()
