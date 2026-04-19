"""
Match View - Core match scoring and viewing screen with proper layout and auto-managed batsmen
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
    calculate_remaining_balls,
    format_overs
)
from utils.time_utils import format_time_ago, get_seconds_since
from .components import (
    StyledButton, CardFrame, ScoreDisplay, StatusBadge,
    DataTable, BallTimeline, LiveIndicator, ScrollableFrame
)


class PlayerSelectDialog(tk.Toplevel):
    """Dialog to select a player from a list"""
    
    def __init__(self, parent, title: str, players: List[str], allow_custom: bool = False):
        super().__init__(parent)
        self.result = None
        
        self.title(title)
        self.geometry("300x400")
        self.configure(bg=COLORS['background'])
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 150
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 200
        self.geometry(f"+{x}+{y}")
        
        # Player list
        list_frame = tk.Frame(self, bg=COLORS['background'])
        list_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        tk.Label(
            list_frame,
            text="Select player:",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING))
        
        self.listbox = tk.Listbox(
            list_frame,
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            height=10
        )
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        for player in players:
            self.listbox.insert(tk.END, player)
        
        self.listbox.bind('<Double-1>', self._on_select)
        
        # Custom entry if allowed
        if allow_custom:
            custom_frame = tk.Frame(self, bg=COLORS['background'])
            custom_frame.pack(fill='x', padx=PADDING, pady=(0, PADDING))
            
            tk.Label(
                custom_frame,
                text="Or enter name:",
                font=FONTS['small'],
                bg=COLORS['background'],
                fg=COLORS['text_secondary']
            ).pack(anchor='w')
            
            self.custom_entry = tk.Entry(
                custom_frame,
                font=FONTS['body'],
                bg=COLORS['card_bg'],
                fg=COLORS['text_primary'],
                insertbackground=COLORS['text_primary'],
                highlightthickness=1,
                highlightbackground=COLORS['border']
            )
            self.custom_entry.pack(fill='x', pady=(SPACING // 2, 0))
        else:
            self.custom_entry = None
        
        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS['background'])
        btn_frame.pack(fill='x', padx=PADDING, pady=(0, PADDING))
        
        cancel_btn = StyledButton(btn_frame, text="Cancel", variant='secondary', command=self.destroy)
        cancel_btn.pack(side='left')
        
        select_btn = StyledButton(btn_frame, text="Select", variant='primary', command=self._on_select)
        select_btn.pack(side='right')
        
        self.wait_window()
    
    def _on_select(self, event=None):
        """Handle selection"""
        # Check custom entry first
        if self.custom_entry and self.custom_entry.get().strip():
            self.result = self.custom_entry.get().strip()
        elif self.listbox.curselection():
            idx = self.listbox.curselection()[0]
            self.result = self.listbox.get(idx)
        self.destroy()


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
        """Create the match view UI with improved layout"""
        # Header (fixed at top)
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
        
        # Main scrollable content area
        scroll_container = ScrollableFrame(self, bg=COLORS['background'])
        scroll_container.pack(fill='both', expand=True)
        content = scroll_container.get_frame()
        content.configure(padx=PADDING, pady=PADDING)
        
        # ===== SCOREBOARD (FULL WIDTH AT TOP) =====
        scoreboard_frame = CardFrame(content, title="Scoreboard")
        scoreboard_frame.pack(fill='x', pady=(0, SPACING))
        
        # Team info row
        self.team_info_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        self.team_info_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        self.batting_team_label = tk.Label(
            self.team_info_frame,
            text="Batting: -",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['runs']
        )
        self.batting_team_label.pack(side='left')
        
        self.bowling_team_label = tk.Label(
            self.team_info_frame,
            text="Bowling: -",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.bowling_team_label.pack(side='right')
        
        # Score display
        self.score_display = ScoreDisplay(scoreboard_frame)
        self.score_display.pack(pady=(SPACING // 2, SPACING))
        
        # Current batsmen display (CRITICAL - always show)
        batsmen_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        batsmen_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        self.striker_display = tk.Label(
            batsmen_frame,
            text="Striker: -",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        self.striker_display.pack(side='left')
        
        self.non_striker_display = tk.Label(
            batsmen_frame,
            text="Non-Striker: -",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.non_striker_display.pack(side='right')
        
        # Target info (for chasing)
        self.target_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        self.target_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        self.target_label = tk.Label(
            self.target_frame,
            text="",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['primary']
        )
        self.target_label.pack()
        
        # Extras breakdown
        extras_info_frame = tk.Frame(scoreboard_frame, bg=COLORS['card_bg'])
        extras_info_frame.pack(fill='x', pady=(SPACING // 4, SPACING // 2))
        
        self.extras_info_label = tk.Label(
            extras_info_frame,
            text="",
            font=FONTS['small'],
            bg=COLORS['card_bg'],
            fg=COLORS['extras']
        )
        self.extras_info_label.pack()
        
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
        
        # ===== BALL TIMELINE (FULL WIDTH, HORIZONTAL SCROLL) =====
        timeline_frame = CardFrame(content, title="Ball Timeline")
        timeline_frame.pack(fill='x', pady=(0, SPACING))
        
        self.ball_timeline = BallTimeline(timeline_frame)
        self.ball_timeline.pack(fill='x', pady=(SPACING // 4, SPACING // 4))
        
        # ===== MATCH CONTROLS (ADMIN ONLY, FULL WIDTH, NO SCROLL) =====
        if self.is_admin:
            self._create_admin_controls(content)
        
        # ===== SCORECARD (Batting & Bowling tables) - VERTICAL STACK =====
        scorecard_section = tk.Frame(content, bg=COLORS['background'])
        scorecard_section.pack(fill='x', pady=(SPACING, 0))
        
        scorecard_label = tk.Label(
            scorecard_section,
            text="Full Scorecard",
            font=FONTS['heading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        scorecard_label.pack(anchor='w', pady=(0, SPACING))
        
        # Batting table (FULL WIDTH)
        batting_frame = CardFrame(scorecard_section, title="Batting")
        batting_frame.pack(fill='x', pady=(0, SPACING))
        
        self.batting_table = DataTable(
            batting_frame,
            columns=['Name', 'Runs', 'Balls', '4s', '6s', 'SR']
        )
        self.batting_table.pack(fill='x', pady=(0, SPACING // 2))
        
        # Bowling table (FULL WIDTH)
        bowling_frame = CardFrame(scorecard_section, title="Bowling")
        bowling_frame.pack(fill='x', pady=(0, SPACING))
        
        self.bowling_table = DataTable(
            bowling_frame,
            columns=['Name', 'Overs', 'Runs', 'Wickets', 'Econ']
        )
        self.bowling_table.pack(fill='x', pady=(0, SPACING // 2))
        
        # ===== ANALYSIS CHARTS (FULL WIDTH) =====
        analysis_section = tk.Frame(content, bg=COLORS['background'])
        analysis_section.pack(fill='both', expand=True, pady=(SPACING + 8, 0))
        
        self._create_charts(analysis_section)
    
    def _create_admin_controls(self, parent):
        """Create admin scoring controls - FULL WIDTH, NO SCROLL"""
        controls_card = CardFrame(parent, title="Match Controls")
        controls_card.pack(fill='x', pady=(0, SPACING))
        
        controls_frame = tk.Frame(controls_card, bg=COLORS['card_bg'])
        controls_frame.pack(fill='x')
        
        # Current players display
        players_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        players_frame.pack(fill='x', pady=(0, SPACING))
        
        self.striker_label = tk.Label(
            players_frame,
            text="Striker: -",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['runs']
        )
        self.striker_label.pack(side='left')
        
        self.non_striker_label = tk.Label(
            players_frame,
            text="Non-Striker: -",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.non_striker_label.pack(side='left', padx=(SPACING, 0))
        
        self.bowler_label = tk.Label(
            players_frame,
            text="Bowler: -",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.bowler_label.pack(side='right')
        
        # Bowler selection (required before scoring)
        bowler_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        bowler_frame.pack(fill='x', pady=(0, SPACING))
        
        add_bowler_btn = StyledButton(
            bowler_frame,
            text="Select Bowler",
            variant='primary',
            command=self._select_bowler
        )
        add_bowler_btn.pack(side='left')
        
        swap_strike_btn = StyledButton(
            bowler_frame,
            text="Swap Strike",
            variant='secondary',
            command=self._swap_strike
        )
        swap_strike_btn.pack(side='right')
        
        # ===== RUNS SECTION =====
        runs_label_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        runs_label_frame.pack(fill='x', pady=(0, 4))
        tk.Label(
            runs_label_frame,
            text="Runs",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        ).pack(anchor='w')
        
        runs_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        runs_frame.pack(fill='x', pady=(0, SPACING))
        
        for runs in RUN_OPTIONS:
            btn = StyledButton(
                runs_frame,
                text=str(runs),
                variant='success' if runs in [4, 6] else 'secondary',
                command=lambda r=runs: self._record_runs(r),
                width=5
            )
            btn.pack(side='left', padx=(0, 6))
        
        # ===== EXTRAS SECTION =====
        # Now uses popup system for Wide, No Ball, Bye, Leg Bye
        extras_label_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        extras_label_frame.pack(fill='x', pady=(0, 4))
        tk.Label(
            extras_label_frame,
            text="Extras (click to enter runs)",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        ).pack(anchor='w')
        
        extras_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        extras_frame.pack(fill='x', pady=(0, SPACING))
        
        # Popup-based extra buttons
        extra_buttons = [
            ("Wide", "WD"),
            ("No Ball", "NB"),
            ("Bye", "BYE"),
            ("Leg Bye", "LB")
        ]
        for label, code in extra_buttons:
            btn = StyledButton(
                extras_frame,
                text=label,
                variant='warning',
                command=lambda c=code: self._show_extra_popup(c),
                width=8
            )
            btn.pack(side='left', padx=(0, 6))
        
        # ===== WICKET SECTION =====
        # Single OUT! button with popup for dismissal type
        wicket_label_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_label_frame.pack(fill='x', pady=(0, 4))
        tk.Label(
            wicket_label_frame,
            text="Wicket",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        ).pack(anchor='w')
        
        wicket_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        wicket_btn = StyledButton(
            wicket_frame,
            text="OUT!",
            variant='danger',
            command=self._show_wicket_popup,
            width=10
        )
        wicket_btn.pack(side='left', padx=(0, 6))
        
        # ===== ACTION BUTTONS =====
        actions_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        actions_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        undo_btn = StyledButton(
            actions_frame,
            text="Undo Last Ball",
            variant='secondary',
            command=self._undo_ball
        )
        undo_btn.pack(side='left')
        
        self.declare_btn = StyledButton(
            actions_frame,
            text="Declare",
            variant='primary',
            command=self._declare_innings
        )
        self.declare_btn.pack(side='right')
        
        # Edit stats buttons
        edit_actions_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        edit_actions_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        edit_batsman_btn = StyledButton(
            edit_actions_frame,
            text="Edit Batsman",
            variant='warning',
            command=self._edit_batsman_stats
        )
        edit_batsman_btn.pack(side='left')
        
        edit_bowler_btn = StyledButton(
            edit_actions_frame,
            text="Edit Bowler",
            variant='warning',
            command=self._edit_bowler_stats
        )
        edit_bowler_btn.pack(side='left', padx=(SPACING // 2, 0))
    
    def _create_charts(self, parent):
        """Create charts section"""
        charts_frame = CardFrame(parent, title="Match Analysis")
        charts_frame.pack(fill='both', expand=True)
        
        self.fig = Figure(figsize=(12, 5), dpi=90)
        self.fig.patch.set_facecolor(COLORS['card_bg'])
        
        self.rr_ax = self.fig.add_subplot(121)
        self.rr_ax.set_title('Run Rate Progression', fontsize=13, pad=12, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        self.rpo_ax = self.fig.add_subplot(122)
        self.rpo_ax.set_title('Runs per Over', fontsize=13, pad=12, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        self.fig.tight_layout(pad=3.0, w_pad=4.0)
        
        self.canvas = FigureCanvasTkAgg(self.fig, charts_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, pady=(SPACING // 2, SPACING))
    
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
            self.batting_team_label.configure(text="Batting: -")
            self.bowling_team_label.configure(text="Bowling: -")
            self.striker_display.configure(text="Striker: -")
            self.non_striker_display.configure(text="Non-Striker: -")
            return
        
        innings = innings_list[current_idx]
        runs = innings.get('runs', 0)
        wickets = innings.get('wickets', 0)
        overs = innings.get('overs', 0.0)
        
        # Calculate run rate
        run_rate = calculate_run_rate(runs, overs) if overs > 0 else 0.0
        
        # Update score display
        self.score_display.update_score(runs, wickets, overs, run_rate)
        
        # Update team indicators (CRITICAL)
        batting_team = innings.get('batting_team', '-')
        bowling_team = innings.get('bowling_team', '-')
        self.batting_team_label.configure(text=f"Batting: {batting_team}")
        self.bowling_team_label.configure(text=f"Bowling: {bowling_team}")
        
        # Update current batsmen display (CRITICAL)
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        non_striker = MatchEngine.get_current_batsman(innings, on_strike=False)
        
        striker_text = f"Striker: {striker['name']} ({striker['runs']})" if striker else "Striker: -"
        non_striker_text = f"Non-Striker: {non_striker['name']} ({non_striker['runs']})" if non_striker else "Non-Striker: -"
        
        self.striker_display.configure(text=striker_text)
        self.non_striker_display.configure(text=non_striker_text)
        
        # Update target info
        target = self.match.get('target')
        if target and current_idx > 0:
            runs_needed = target - runs
            self.target_label.configure(text=f"Target: {target} | Need: {runs_needed} runs")
            
            # Required run rate
            total_overs = innings.get('max_overs') or self.match.get('total_overs', 20)
            remaining_overs = max(0, total_overs - overs)
            required_rr = calculate_required_run_rate(target, runs, remaining_overs)
            self.insight_labels['required_rr'].configure(text=f"Req RR: {required_rr:.2f}")
        else:
            self.target_label.configure(text="")
            self.insight_labels['required_rr'].configure(text="")
        
        # Update extras breakdown
        extras = innings.get('extras', {})
        wides = extras.get('wides', 0)
        no_balls = extras.get('no_balls', 0)
        byes = extras.get('byes', 0)
        leg_byes = extras.get('leg_byes', 0)
        total_extras = wides + no_balls + byes + leg_byes
        
        if total_extras > 0:
            extras_text = f"Extras: {total_extras} (Wd {wides}, NB {no_balls}, B {byes}, LB {leg_byes})"
            self.extras_info_label.configure(text=extras_text)
        else:
            self.extras_info_label.configure(text="")
        
        # Update insights
        total_overs = innings.get('max_overs') or self.match.get('total_overs')
        if total_overs:
            projected = calculate_projected_score(runs, overs, total_overs)
            remaining = calculate_remaining_balls(overs, total_overs)
            
            self.insight_labels['projected'].configure(text=f"Projected: {projected}")
            self.insight_labels['remaining'].configure(text=f"Balls left: {remaining}")
        else:
            self.insight_labels['projected'].configure(text="")
            self.insight_labels['remaining'].configure(text="")
        
        # Update ball timeline with proper cricket notation
        self.ball_timeline.clear()
        for ball in innings.get('balls', []):
            self.ball_timeline.add_ball(
                runs=ball.get('runs', 0),
                is_wicket=ball.get('is_wicket', False),
                extra_type=ball.get('extra_type'),
                extra_runs=ball.get('extras', 0),
                dismissal_type=ball.get('dismissal')
            )
        
        # Update batting table
        batsmen = innings.get('batsmen', [])
        batting_state = innings.get('current_batting_state', {})
        batting_data = []
        for batsman in batsmen:
            balls = batsman.get('balls', 0)
            runs_b = batsman.get('runs', 0)
            sr = (runs_b / balls * 100) if balls > 0 else 0.0
            
            name = batsman.get('name', 'Unknown')
            batsman_id = batsman.get('id')
            
            # Mark current batsmen
            if batsman_id == batting_state.get('striker'):
                name += " *"  # On strike
            elif batsman_id == batting_state.get('non_striker'):
                name += " (ns)"  # Non-striker
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
                format_overs(overs_b),
                runs_b,
                bowler.get('wickets', 0),
                f"{econ:.1f}"
            ])
        self.bowling_table.set_data(bowling_data)
        
        # Update admin controls
        if self.is_admin:
            self.striker_label.configure(
                text=f"Striker: {striker['name'] if striker else '-'}"
            )
            
            self.non_striker_label.configure(
                text=f"Non-Striker: {non_striker['name'] if non_striker else '-'}"
            )
            
            bowler = MatchEngine.get_current_bowler(innings)
            self.bowler_label.configure(
                text=f"Bowler: {bowler['name'] if bowler else '- (SELECT BOWLER)'}"
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
        
        self.rr_ax.clear()
        self.rpo_ax.clear()
        
        rr_data = analysis.get('run_rate_progression', [])
        if rr_data:
            overs_x = list(range(1, len(rr_data) + 1))
            self.rr_ax.plot(overs_x, rr_data, color=COLORS['primary'], linewidth=2.5, marker='o', markersize=5)
            self.rr_ax.fill_between(overs_x, rr_data, alpha=0.2, color=COLORS['primary'])
            self.rr_ax.set_xlabel('Over', fontsize=11, labelpad=8)
            self.rr_ax.set_ylabel('Run Rate', fontsize=11, labelpad=8)
            self.rr_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rr_ax.grid(True, alpha=0.3, linestyle='--')
            self.rr_ax.set_xticks(overs_x)
            self.rr_ax.set_xticklabels([str(o) for o in overs_x])
        
        self.rr_ax.set_title('Run Rate Progression', fontsize=13, pad=14, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        rpo_data = analysis.get('runs_per_over', [])
        if rpo_data:
            overs_x = list(range(1, len(rpo_data) + 1))
            colors = [COLORS['runs'] if r >= 10 else COLORS['primary'] for r in rpo_data]
            self.rpo_ax.bar(overs_x, rpo_data, color=colors, edgecolor='none', width=0.7)
            self.rpo_ax.set_xlabel('Over', fontsize=11, labelpad=8)
            self.rpo_ax.set_ylabel('Runs', fontsize=11, labelpad=8)
            self.rpo_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rpo_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            self.rpo_ax.set_xticks(overs_x)
            self.rpo_ax.set_xticklabels([str(o) for o in overs_x])
            
            wickets = analysis.get('wickets_timeline', [])
            for w in wickets:
                if w < len(overs_x):
                    self.rpo_ax.axvline(x=w + 1, color=COLORS['wickets'], linestyle='--', linewidth=2, alpha=0.8)
        
        self.rpo_ax.set_title('Runs per Over', fontsize=13, pad=14, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        self.fig.tight_layout(pad=3.0, w_pad=4.0)
        self.canvas.draw()
    
    def _get_available_bowlers(self) -> List[str]:
        """Get list of bowlers from bowling team roster"""
        if not self.match:
            return []
        
        innings = self.match['innings'][self.match['current_innings']]
        bowling_team = innings.get('bowling_team', '')
        roster = self.match.get('rosters', {}).get(bowling_team, [])
        
        return roster
    
    def _select_bowler(self):
        """Select bowler from bowling team roster"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        available = self._get_available_bowlers()
        
        if available:
            dialog = PlayerSelectDialog(
                self,
                title="Select Bowler",
                players=available,
                allow_custom=True
            )
            if dialog.result:
                MatchEngine.add_bowler(innings, dialog.result)
                self._save_and_refresh()
        else:
            name = simpledialog.askstring("Add Bowler", "Enter bowler name:")
            if name:
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
    
    def _show_extra_popup(self, extra_type: str):
        """Show popup dialog for extras with runs input
        
        WIDE: total_runs = 1 (penalty) + runs_entered, ball does NOT count
        NO BALL: total_runs = 1 (penalty) + runs_entered, ball does NOT count
        BYE: total_runs = runs_entered, ball DOES count
        LEG BYE: total_runs = runs_entered, ball DOES count
        """
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not bowler:
            messagebox.showwarning("Warning", "Please select a bowler first.")
            return
        
        extra_labels = {
            'WD': 'Wide',
            'NB': 'No Ball',
            'BYE': 'Bye',
            'LB': 'Leg Bye'
        }
        extra_label = extra_labels.get(extra_type, extra_type)
        
        # Create popup dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Record {extra_label}")
        dialog.geometry("300x200")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")
        
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Explanation based on extra type
        if extra_type == 'WD':
            explanation = "Wide: 1 penalty run + additional runs\nBall does NOT count"
        elif extra_type == 'NB':
            explanation = "No Ball: 1 penalty run + runs scored\nBall does NOT count (FREE HIT next)"
        elif extra_type == 'BYE':
            explanation = "Bye: Runs scored without bat contact\nBall DOES count"
        else:  # LB
            explanation = "Leg Bye: Runs off batsman's body\nBall DOES count"
        
        tk.Label(
            form_frame,
            text=explanation,
            font=FONTS['small'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary'],
            justify='left'
        ).pack(anchor='w', pady=(0, SPACING))
        
        # Runs input
        runs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING))
        
        tk.Label(
            runs_frame,
            text="Runs scored:",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        runs_var = tk.StringVar(value="0")
        runs_entry = tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=6)
        runs_entry.pack(side='left')
        runs_entry.focus_set()
        runs_entry.select_range(0, tk.END)
        
        def confirm():
            try:
                runs = int(runs_var.get())
                if runs < 0:
                    messagebox.showerror("Error", "Runs cannot be negative")
                    return
                
                self.match = MatchEngine.record_ball(
                    self.match,
                    runs=0,  # Batsman runs are handled in extras
                    extra_type=extra_type,
                    extra_runs=runs
                )
                self._save_and_refresh()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy).pack(side='left')
        StyledButton(btn_frame, text="Record", variant='primary', command=confirm).pack(side='right')
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: confirm())
        
        dialog.wait_window()
    
    def _show_wicket_popup(self):
        """Show popup dialog for wickets with dismissal type and run out options
        
        Dismissal types: Bowled, Caught, LBW, Run Out, Stumped, Other
        For Run Out: asks for runs scored and who is out (striker/non-striker)
        """
        if not self.match or not self._validate_players():
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        non_striker = MatchEngine.get_current_batsman(innings, on_strike=False)
        
        # Create popup dialog
        dialog = tk.Toplevel(self)
        dialog.title("Record Wicket")
        dialog.geometry("350x320")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 175
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 160
        dialog.geometry(f"+{x}+{y}")
        
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Dismissal type selection
        tk.Label(
            form_frame,
            text="Dismissal Type:",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING // 2))
        
        dismissal_var = tk.StringVar(value="Bowled")
        dismissal_types = ['Bowled', 'Caught', 'LBW', 'Run Out', 'Stumped', 'Other']
        
        dismissal_frame = tk.Frame(form_frame, bg=COLORS['background'])
        dismissal_frame.pack(fill='x', pady=(0, SPACING))
        
        for dtype in dismissal_types:
            rb = tk.Radiobutton(
                dismissal_frame,
                text=dtype,
                variable=dismissal_var,
                value=dtype,
                font=FONTS['body'],
                bg=COLORS['background'],
                fg=COLORS['text_primary'],
                selectcolor=COLORS['background'],
                activebackground=COLORS['background'],
                command=lambda: update_run_out_options()
            )
            rb.pack(side='left', padx=(0, SPACING // 2))
        
        # Run Out specific options (initially hidden)
        run_out_frame = tk.Frame(form_frame, bg=COLORS['background'])
        
        # Runs scored for run out
        runs_frame = tk.Frame(run_out_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        tk.Label(
            runs_frame,
            text="Runs scored:",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        runs_var = tk.StringVar(value="0")
        runs_entry = tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=6)
        runs_entry.pack(side='left')
        
        # Who is out
        who_out_frame = tk.Frame(run_out_frame, bg=COLORS['background'])
        who_out_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        tk.Label(
            who_out_frame,
            text="Who is out?",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        who_out_var = tk.StringVar(value="striker")
        
        striker_name = striker['name'] if striker else "Striker"
        non_striker_name = non_striker['name'] if non_striker else "Non-Striker"
        
        tk.Radiobutton(
            who_out_frame,
            text=f"Striker ({striker_name})",
            variable=who_out_var,
            value="striker",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectcolor=COLORS['background'],
            activebackground=COLORS['background']
        ).pack(side='left')
        
        tk.Radiobutton(
            who_out_frame,
            text=f"Non-Striker ({non_striker_name})",
            variable=who_out_var,
            value="non_striker",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectcolor=COLORS['background'],
            activebackground=COLORS['background']
        ).pack(side='left')
        
        def update_run_out_options():
            if dismissal_var.get() == "Run Out":
                run_out_frame.pack(fill='x', pady=(0, SPACING))
            else:
                run_out_frame.pack_forget()
        
        def confirm():
            dismissal = dismissal_var.get()
            
            if dismissal == "Run Out":
                try:
                    runs = int(runs_var.get())
                    if runs < 0:
                        messagebox.showerror("Error", "Runs cannot be negative")
                        return
                    
                    non_striker_out = (who_out_var.get() == "non_striker")
                    
                    self.match = MatchEngine.record_ball(
                        self.match,
                        runs=runs,
                        is_wicket=True,
                        dismissal_type="Run Out",
                        non_striker_out=non_striker_out
                    )
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid number for runs")
                    return
            else:
                # Non-run-out dismissals: no runs, striker is out
                self.match = MatchEngine.record_ball(
                    self.match,
                    runs=0,
                    is_wicket=True,
                    dismissal_type=dismissal,
                    non_striker_out=False
                )
            
            self._save_and_refresh()
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0), side='bottom')
        
        StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy).pack(side='left')
        StyledButton(btn_frame, text="Record OUT", variant='danger', command=confirm).pack(side='right')
        
        dialog.wait_window()
    
    def _undo_ball(self):
        """Undo the last ball"""
        if not self.match:
            return
        
        if messagebox.askyesno("Confirm", "Undo the last ball?"):
            self.match = MatchEngine.undo_last_ball(self.match)
            self._save_and_refresh()
    
    def _declare_innings(self):
        """Declare the innings"""
        if not self.match:
            return
        
        if self.match.get('format') != 'TEST':
            messagebox.showwarning("Warning", "Declaration is only for Test matches.")
            return
        
        if messagebox.askyesno("Confirm", "Declare this innings?"):
            self.match = MatchEngine.declare_innings(self.match)
            self._save_and_refresh()
    
    def _swap_strike(self):
        """Swap strike between batsmen"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        batting_state = innings.get('current_batting_state', {})
        
        if not batting_state.get('striker') or not batting_state.get('non_striker'):
            messagebox.showwarning("Warning", "Need 2 batsmen at the crease.")
            return
        
        # Swap
        striker_id = batting_state['striker']
        non_striker_id = batting_state['non_striker']
        
        batting_state['striker'] = non_striker_id
        batting_state['non_striker'] = striker_id
        
        # Update on_strike flags
        for batsman in innings['batsmen']:
            if batsman['id'] == non_striker_id:
                batsman['on_strike'] = True
            elif batsman['id'] == striker_id:
                batsman['on_strike'] = False
        
        self._save_and_refresh()
    
    def _edit_batsman_stats(self):
        """Edit a batsman's stats"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        batsmen = innings.get('batsmen', [])
        
        if not batsmen:
            messagebox.showwarning("Warning", "No batsmen in current innings.")
            return
        
        batsman_names = [f"{b['name']} ({b['runs']}/{b['balls']})" for b in batsmen]
        dialog = PlayerSelectDialog(
            self,
            title="Select Batsman to Edit",
            players=batsman_names,
            allow_custom=False
        )
        
        if dialog.result:
            idx = batsman_names.index(dialog.result)
            batsman = batsmen[idx]
            self._show_batsman_edit_dialog(batsman)
    
    def _show_batsman_edit_dialog(self, batsman: Dict[str, Any]):
        """Show dialog to edit batsman stats"""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Stats: {batsman['name']}")
        dialog.geometry("320x300")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 160
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Runs
        runs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(runs_frame, text="Runs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        runs_var = tk.StringVar(value=str(batsman.get('runs', 0)))
        tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=10).pack(side='left')
        
        # Balls
        balls_frame = tk.Frame(form_frame, bg=COLORS['background'])
        balls_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(balls_frame, text="Balls:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        balls_var = tk.StringVar(value=str(batsman.get('balls', 0)))
        tk.Entry(balls_frame, textvariable=balls_var, font=FONTS['body'], width=10).pack(side='left')
        
        # Fours
        fours_frame = tk.Frame(form_frame, bg=COLORS['background'])
        fours_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(fours_frame, text="Fours:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        fours_var = tk.StringVar(value=str(batsman.get('fours', 0)))
        tk.Entry(fours_frame, textvariable=fours_var, font=FONTS['body'], width=10).pack(side='left')
        
        # Sixes
        sixes_frame = tk.Frame(form_frame, bg=COLORS['background'])
        sixes_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(sixes_frame, text="Sixes:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        sixes_var = tk.StringVar(value=str(batsman.get('sixes', 0)))
        tk.Entry(sixes_frame, textvariable=sixes_var, font=FONTS['body'], width=10).pack(side='left')
        
        def save_changes():
            try:
                batsman['runs'] = int(runs_var.get())
                batsman['balls'] = int(balls_var.get())
                batsman['fours'] = int(fours_var.get())
                batsman['sixes'] = int(sixes_var.get())
                
                innings = self.match['innings'][self.match['current_innings']]
                total_runs = sum(b.get('runs', 0) for b in innings.get('batsmen', []))
                extras = innings.get('extras', {})
                total_extras = sum(extras.values())
                innings['runs'] = total_runs + total_extras
                
                self._save_and_refresh()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers.")
        
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy).pack(side='left')
        StyledButton(btn_frame, text="Save", variant='primary', command=save_changes).pack(side='right')
        
        dialog.wait_window()
    
    def _edit_bowler_stats(self):
        """Edit a bowler's stats"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        bowlers = innings.get('bowlers', [])
        
        if not bowlers:
            messagebox.showwarning("Warning", "No bowlers in current innings.")
            return
        
        bowler_names = [f"{b['name']} ({b.get('overs', 0)}-{b.get('runs', 0)}-{b.get('wickets', 0)})" for b in bowlers]
        dialog = PlayerSelectDialog(
            self,
            title="Select Bowler to Edit",
            players=bowler_names,
            allow_custom=False
        )
        
        if dialog.result:
            idx = bowler_names.index(dialog.result)
            bowler = bowlers[idx]
            self._show_bowler_edit_dialog(bowler)
    
    def _show_bowler_edit_dialog(self, bowler: Dict[str, Any]):
        """Show dialog to edit bowler stats"""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Stats: {bowler['name']}")
        dialog.geometry("320x280")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 160
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 140
        dialog.geometry(f"+{x}+{y}")
        
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Overs
        overs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        overs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(overs_frame, text="Overs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        overs_var = tk.StringVar(value=str(bowler.get('overs', 0.0)))
        tk.Entry(overs_frame, textvariable=overs_var, font=FONTS['body'], width=10).pack(side='left')
        tk.Label(overs_frame, text="(e.g., 4.3)", font=FONTS['small'], bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side='left', padx=(SPACING // 2, 0))
        
        # Runs
        runs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(runs_frame, text="Runs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        runs_var = tk.StringVar(value=str(bowler.get('runs', 0)))
        tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=10).pack(side='left')
        
        # Wickets
        wickets_frame = tk.Frame(form_frame, bg=COLORS['background'])
        wickets_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(wickets_frame, text="Wickets:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        wickets_var = tk.StringVar(value=str(bowler.get('wickets', 0)))
        tk.Entry(wickets_frame, textvariable=wickets_var, font=FONTS['body'], width=10).pack(side='left')
        
        # Maidens
        maidens_frame = tk.Frame(form_frame, bg=COLORS['background'])
        maidens_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(maidens_frame, text="Maidens:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        maidens_var = tk.StringVar(value=str(bowler.get('maidens', 0)))
        tk.Entry(maidens_frame, textvariable=maidens_var, font=FONTS['body'], width=10).pack(side='left')
        
        def save_changes():
            try:
                bowler['overs'] = float(overs_var.get())
                bowler['runs'] = int(runs_var.get())
                bowler['wickets'] = int(wickets_var.get())
                bowler['maidens'] = int(maidens_var.get())
                
                self._save_and_refresh()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers.")
        
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy).pack(side='left')
        StyledButton(btn_frame, text="Save", variant='primary', command=save_changes).pack(side='right')
        
        dialog.wait_window()
    
    def _validate_players(self) -> bool:
        """Validate that required players are set"""
        if not self.match:
            return False
        
        innings = self.match['innings'][self.match['current_innings']]
        batting_state = innings.get('current_batting_state', {})
        
        striker = MatchEngine.get_current_batsman(innings, on_strike=True)
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not striker:
            messagebox.showwarning("Warning", "No striker at crease. Match may have ended.")
            return False
        
        if not batting_state.get('non_striker'):
            # This could be fine if all out, but let's warn
            max_wickets = innings.get('max_wickets', 10)
            if innings.get('wickets', 0) >= max_wickets - 1:
                pass  # Allow scoring with just striker (last wicket scenario)
            else:
                messagebox.showwarning("Warning", "No non-striker at crease.")
                return False
        
        if not bowler:
            messagebox.showwarning("Warning", "Please select a bowler first.")
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
        
        if seconds_since == float('inf') or seconds_since > 60:
            self.live_indicator.set_warning("No data")
        elif seconds_since > 5:
            self.live_indicator.set_warning(f"Stale ({int(seconds_since)}s)")
        else:
            self.live_indicator.set_live(True, format_time_ago(last_updated))
            self.live_indicator.blink()
        
        self.after(SYNC_INTERVAL, self._sync)
    
    def refresh(self):
        """Public method to force refresh"""
        self._load_match()
