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
        """Create the match view UI"""
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
        
        # Top section: Score + Controls side by side (different layout for admin vs viewer)
        top_section = tk.Frame(content, bg=COLORS['background'])
        top_section.pack(fill='x', pady=(0, SPACING))
        
        # Left side - Scoreboard and Ball Timeline
        left_panel = tk.Frame(top_section, bg=COLORS['background'])
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Scoreboard
        scoreboard_frame = CardFrame(left_panel, title="Scoreboard")
        scoreboard_frame.pack(fill='x', expand=not self.is_admin)
        
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
        
        # Right side - Controls (admin only)
        if self.is_admin:
            right_panel = tk.Frame(top_section, bg=COLORS['background'], width=480)
            right_panel.pack(side='right', fill='y', padx=(SPACING + 4, 0))
            right_panel.pack_propagate(False)
            self._create_admin_controls(right_panel)
        
        # Middle section: Scorecard (Batting & Bowling tables)
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
        
        # Tables side by side
        tables_frame = tk.Frame(scorecard_section, bg=COLORS['background'])
        tables_frame.pack(fill='x')
        
        # Batting table
        batting_container = tk.Frame(tables_frame, bg=COLORS['background'])
        batting_container.pack(side='left', fill='both', expand=True, padx=(0, SPACING // 2))
        
        batting_frame = CardFrame(batting_container, title="Batting")
        batting_frame.pack(fill='both', expand=True)
        
        self.batting_table = DataTable(
            batting_frame,
            columns=['Name', 'Runs', 'Balls', '4s', '6s', 'SR']
        )
        self.batting_table.pack(fill='both', expand=True, pady=(0, SPACING // 2))
        
        # Bowling table
        bowling_container = tk.Frame(tables_frame, bg=COLORS['background'])
        bowling_container.pack(side='right', fill='both', expand=True, padx=(SPACING // 2, 0))
        
        bowling_frame = CardFrame(bowling_container, title="Bowling")
        bowling_frame.pack(fill='both', expand=True)
        
        self.bowling_table = DataTable(
            bowling_frame,
            columns=['Name', 'Overs', 'Runs', 'Wickets', 'Econ']
        )
        self.bowling_table.pack(fill='both', expand=True, pady=(0, SPACING // 2))
        
        # Bottom section: Analysis charts (full width)
        analysis_section = tk.Frame(content, bg=COLORS['background'])
        analysis_section.pack(fill='both', expand=True, pady=(SPACING + 8, 0))
        
        self._create_charts(analysis_section)
    
    def _create_admin_controls(self, parent):
        """Create admin scoring controls"""
        # Team Roster Management
        roster_frame = CardFrame(parent, title="Team Roster")
        roster_frame.pack(fill='x')
        
        # Team selection and roster display
        self.roster_team_var = tk.StringVar()
        
        team_select_frame = tk.Frame(roster_frame, bg=COLORS['card_bg'])
        team_select_frame.pack(fill='x', pady=(0, SPACING))
        
        tk.Label(
            team_select_frame,
            text="Team:",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        ).pack(side='left')
        
        self.team_dropdown = ttk.Combobox(
            team_select_frame,
            textvariable=self.roster_team_var,
            state='readonly',
            width=20
        )
        self.team_dropdown.pack(side='left', padx=(SPACING // 2, 0))
        self.team_dropdown.bind('<<ComboboxSelected>>', self._on_team_selected)
        
        # Roster list with scrollbar
        roster_list_frame = tk.Frame(roster_frame, bg=COLORS['card_bg'])
        roster_list_frame.pack(fill='x', pady=(0, SPACING))
        
        self.roster_listbox = tk.Listbox(
            roster_list_frame,
            height=5,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        roster_scrollbar = ttk.Scrollbar(roster_list_frame, orient='vertical', command=self.roster_listbox.yview)
        self.roster_listbox.configure(yscrollcommand=roster_scrollbar.set)
        self.roster_listbox.pack(side='left', fill='x', expand=True)
        roster_scrollbar.pack(side='right', fill='y')
        
        # Add player to roster
        add_roster_frame = tk.Frame(roster_frame, bg=COLORS['card_bg'])
        add_roster_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        self.new_player_entry = tk.Entry(
            add_roster_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        self.new_player_entry.pack(side='left', fill='x', expand=True, padx=(0, SPACING // 2))
        self.new_player_entry.bind('<Return>', lambda e: self._add_to_roster())
        
        add_roster_btn = StyledButton(
            add_roster_frame,
            text="+ Add",
            variant='primary',
            command=self._add_to_roster
        )
        add_roster_btn.pack(side='right')
        
        # Scoring Controls
        controls_frame = CardFrame(parent, title="Scoring Controls")
        controls_frame.pack(fill='x', pady=(SPACING, 0))
        
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
        
        # Add players buttons - now uses roster selection
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
        
        for i, runs in enumerate(RUN_OPTIONS):
            btn = StyledButton(
                runs_frame,
                text=str(runs),
                variant='success' if runs in [4, 6] else 'secondary',
                command=lambda r=runs: self._record_runs(r),
                width=5
            )
            btn.pack(side='left', padx=(0, 6))
        
        # ===== EXTRAS SECTION =====
        extras_label_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        extras_label_frame.pack(fill='x', pady=(0, 4))
        tk.Label(
            extras_label_frame,
            text="Extras",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        ).pack(anchor='w')
        
        # Row 1: Basic extras
        extras_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        extras_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        # Map display name to internal code
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
                command=lambda c=code: self._record_extra(c),
                width=7
            )
            btn.pack(side='left', padx=(0, 6))
        
        # Row 2: Wide + Runs combinations
        wide_runs_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wide_runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        wide_combos = [("Wide +1", "WD", 1), ("Wide +2", "WD", 2), ("Wide +4", "WD", 4)]
        for label, extra_type, extra_runs in wide_combos:
            btn = StyledButton(
                wide_runs_frame,
                text=label,
                variant='warning',
                command=lambda e=extra_type, r=extra_runs: self._record_extra_with_runs(e, r),
                width=7
            )
            btn.pack(side='left', padx=(0, 6))
        
        # Row 3: No Ball + Runs combinations
        nb_runs_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        nb_runs_frame.pack(fill='x', pady=(0, SPACING))
        
        nb_combos = [("No Ball +1", "NB", 1), ("No Ball +4", "NB", 4), ("No Ball +6", "NB", 6)]
        for label, extra_type, extra_runs in nb_combos:
            btn = StyledButton(
                nb_runs_frame,
                text=label,
                variant='warning',
                command=lambda e=extra_type, r=extra_runs: self._record_extra_with_runs(e, r),
                width=9
            )
            btn.pack(side='left', padx=(0, 6))
        
        # ===== WICKET SECTION =====
        wicket_label_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_label_frame.pack(fill='x', pady=(0, 4))
        tk.Label(
            wicket_label_frame,
            text="Wicket",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        ).pack(anchor='w')
        
        # Row 1: Main wicket button
        wicket_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_frame.pack(fill='x', pady=(0, SPACING // 2))
        
        wicket_btn = StyledButton(
            wicket_frame,
            text="OUT!",
            variant='danger',
            command=lambda: self._record_wicket_with_runs(0)
        )
        wicket_btn.pack(side='left', padx=(0, 6))
        
        # Row 2: Wicket + Runs (run out scenarios)
        wicket_runs_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        wicket_runs_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        wicket_combos = [("Run Out +1", 1), ("Run Out +2", 2), ("Run Out +3", 3)]
        for label, runs in wicket_combos:
            btn = StyledButton(
                wicket_runs_frame,
                text=label,
                variant='danger',
                command=lambda r=runs: self._record_wicket_with_runs(r),
                width=9
            )
            btn.pack(side='left', padx=(0, 6))
        
        # Action buttons row 1
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
        
        # Action buttons row 2 - Edit stats
        edit_actions_frame = tk.Frame(controls_frame, bg=COLORS['card_bg'])
        edit_actions_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        edit_batsman_btn = StyledButton(
            edit_actions_frame,
            text="Edit Batsman Stats",
            variant='warning',
            command=self._edit_batsman_stats
        )
        edit_batsman_btn.pack(side='left')
        
        edit_bowler_btn = StyledButton(
            edit_actions_frame,
            text="Edit Bowler Stats",
            variant='warning',
            command=self._edit_bowler_stats
        )
        edit_bowler_btn.pack(side='left', padx=(SPACING // 2, 0))
        
        swap_strike_btn = StyledButton(
            edit_actions_frame,
            text="Swap Strike",
            variant='secondary',
            command=self._swap_strike
        )
        swap_strike_btn.pack(side='right')
    
    def _create_charts(self, parent):
        """Create charts section - full width at bottom"""
        charts_frame = CardFrame(parent, title="Match Analysis")
        charts_frame.pack(fill='both', expand=True)
        
        # Create matplotlib figure - wider for full width display
        self.fig = Figure(figsize=(12, 5), dpi=90)
        self.fig.patch.set_facecolor(COLORS['card_bg'])
        
        # Charts side by side (1 row, 2 columns)
        self.rr_ax = self.fig.add_subplot(121)
        self.rr_ax.set_title('Run Rate Progression', fontsize=13, pad=12, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        self.rpo_ax = self.fig.add_subplot(122)
        self.rpo_ax.set_title('Runs per Over', fontsize=13, pad=12, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        # Adjust layout for side-by-side
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
        
        # Update team dropdown for roster management (admin only)
        if self.is_admin and hasattr(self, 'team_dropdown'):
            current_values = list(self.team_dropdown['values'])
            if current_values != teams:
                self.team_dropdown['values'] = teams
                if not self.roster_team_var.get() and teams:
                    self.roster_team_var.set(teams[0])
                    self._on_team_selected()
        
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
                format_overs(overs_b),
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
            # Use integer over numbers for x-axis (1, 2, 3, etc.)
            overs_x = list(range(1, len(rr_data) + 1))
            self.rr_ax.plot(overs_x, rr_data, color=COLORS['primary'], linewidth=2.5, marker='o', markersize=5)
            self.rr_ax.fill_between(overs_x, rr_data, alpha=0.2, color=COLORS['primary'])
            self.rr_ax.set_xlabel('Over', fontsize=11, labelpad=8)
            self.rr_ax.set_ylabel('Run Rate', fontsize=11, labelpad=8)
            self.rr_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rr_ax.grid(True, alpha=0.3, linestyle='--')
            # Set x-axis to show only integers
            self.rr_ax.set_xticks(overs_x)
            self.rr_ax.set_xticklabels([str(o) for o in overs_x])
        
        self.rr_ax.set_title('Run Rate Progression', fontsize=13, pad=14, fontweight='bold')
        self.rr_ax.set_facecolor(COLORS['card_bg'])
        
        # Runs per over
        rpo_data = analysis.get('runs_per_over', [])
        if rpo_data:
            # Use integer over numbers for x-axis (1, 2, 3, etc.)
            overs_x = list(range(1, len(rpo_data) + 1))
            colors = [COLORS['runs'] if r >= 10 else COLORS['primary'] for r in rpo_data]
            self.rpo_ax.bar(overs_x, rpo_data, color=colors, edgecolor='none', width=0.7)
            self.rpo_ax.set_xlabel('Over', fontsize=11, labelpad=8)
            self.rpo_ax.set_ylabel('Runs', fontsize=11, labelpad=8)
            self.rpo_ax.tick_params(axis='both', labelsize=10, pad=4)
            self.rpo_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            # Set x-axis to show only integers
            self.rpo_ax.set_xticks(overs_x)
            self.rpo_ax.set_xticklabels([str(o) for o in overs_x])
            
            # Mark wickets
            wickets = analysis.get('wickets_timeline', [])
            for w in wickets:
                if w < len(overs_x):
                    self.rpo_ax.axvline(x=w + 1, color=COLORS['wickets'], linestyle='--', linewidth=2, alpha=0.8)
        
        self.rpo_ax.set_title('Runs per Over', fontsize=13, pad=14, fontweight='bold')
        self.rpo_ax.set_facecolor(COLORS['card_bg'])
        
        self.fig.tight_layout(pad=3.0, w_pad=4.0)
        self.canvas.draw()
    
    def _on_team_selected(self, event=None):
        """Handle team selection change"""
        if not self.match:
            return
        
        team_name = self.roster_team_var.get()
        roster = self.match.get('rosters', {}).get(team_name, [])
        
        self.roster_listbox.delete(0, tk.END)
        for player in roster:
            self.roster_listbox.insert(tk.END, player)
    
    def _add_to_roster(self):
        """Add a player to the selected team's roster"""
        if not self.match:
            return
        
        team_name = self.roster_team_var.get()
        player_name = self.new_player_entry.get().strip()
        
        if not team_name:
            messagebox.showwarning("Warning", "Please select a team first.")
            return
        
        if not player_name:
            return
        
        # Initialize rosters if not exists
        if 'rosters' not in self.match:
            self.match['rosters'] = {}
        
        if team_name not in self.match['rosters']:
            self.match['rosters'][team_name] = []
        
        # Add player if not already in roster
        if player_name not in self.match['rosters'][team_name]:
            self.match['rosters'][team_name].append(player_name)
            self.roster_listbox.insert(tk.END, player_name)
            self.new_player_entry.delete(0, tk.END)
            self._save_and_refresh()
        else:
            messagebox.showinfo("Info", f"{player_name} is already in the roster.")
    
    def _get_available_batsmen(self) -> List[str]:
        """Get list of batsmen from roster who haven't batted yet"""
        if not self.match:
            return []
        
        innings = self.match['innings'][self.match['current_innings']]
        batting_team = innings.get('batting_team', '')
        roster = self.match.get('rosters', {}).get(batting_team, [])
        
        # Get names of batsmen who have already batted
        batted = {b['name'] for b in innings.get('batsmen', [])}
        
        # Return available batsmen
        return [p for p in roster if p not in batted]
    
    def _get_available_bowlers(self) -> List[str]:
        """Get list of bowlers from roster"""
        if not self.match:
            return []
        
        innings = self.match['innings'][self.match['current_innings']]
        bowling_team = innings.get('bowling_team', '')
        roster = self.match.get('rosters', {}).get(bowling_team, [])
        
        return roster
    
    def _add_batsman(self):
        """Add a new batsman from roster or manually"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        available = self._get_available_batsmen()
        
        if available:
            # Show dialog to select from roster
            dialog = PlayerSelectDialog(
                self,
                title="Add Batsman",
                players=available,
                allow_custom=True
            )
            if dialog.result:
                MatchEngine.add_batsman(innings, dialog.result)
                self._save_and_refresh()
        else:
            # Fallback to manual entry
            name = simpledialog.askstring("Add Batsman", "Enter batsman name:")
            if name:
                MatchEngine.add_batsman(innings, name.strip())
                self._save_and_refresh()
    
    def _add_bowler(self):
        """Add or select bowler from roster"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        available = self._get_available_bowlers()
        
        if available:
            # Show dialog to select from roster
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
            # Fallback to manual entry
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
    
    def _record_extra_with_runs(self, extra_type: str, extra_runs: int):
        """Record an extra with specified additional runs (for quick buttons)"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        bowler = MatchEngine.get_current_bowler(innings)
        
        if not bowler:
            messagebox.showwarning("Warning", "Please add a bowler first.")
            return
        
        self.match = MatchEngine.record_ball(
            self.match,
            extra_type=extra_type,
            extra_runs=extra_runs
        )
        self._save_and_refresh()
    
    def _record_wicket_with_runs(self, runs: int):
        """Record a wicket with runs scored (e.g., run out while taking a run)"""
        if not self.match or not self._validate_players():
            return
        
        dismissal_types = ['Bowled', 'Caught', 'LBW', 'Run Out', 'Stumped', 'Hit Wicket']
        
        # For wickets with runs, default to Run Out
        default_dismissal = 'Run Out' if runs > 0 else 'Bowled'
        
        # Simple dialog for dismissal type
        dismissal = simpledialog.askstring(
            "Wicket",
            f"Dismissal type ({', '.join(dismissal_types)}):",
            initialvalue=default_dismissal
        )
        
        if dismissal:
            self.match = MatchEngine.record_ball(
                self.match,
                runs=runs,
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
    
    def _edit_batsman_stats(self):
        """Edit a batsman's stats (runs, balls, 4s, 6s)"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        batsmen = innings.get('batsmen', [])
        
        if not batsmen:
            messagebox.showwarning("Warning", "No batsmen in current innings.")
            return
        
        # Show dialog to select batsman
        batsman_names = [f"{b['name']} ({b['runs']}/{b['balls']})" for b in batsmen]
        dialog = PlayerSelectDialog(
            self,
            title="Select Batsman to Edit",
            players=batsman_names,
            allow_custom=False
        )
        
        if dialog.result:
            # Find the selected batsman
            idx = batsman_names.index(dialog.result)
            batsman = batsmen[idx]
            
            # Show edit dialog
            self._show_batsman_edit_dialog(batsman)
    
    def _show_batsman_edit_dialog(self, batsman: Dict[str, Any]):
        """Show dialog to edit batsman stats"""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Stats: {batsman['name']}")
        dialog.geometry("320x300")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 160
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        # Form fields
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Runs
        runs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(runs_frame, text="Runs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        runs_var = tk.StringVar(value=str(batsman.get('runs', 0)))
        runs_entry = tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=10)
        runs_entry.pack(side='left')
        
        # Balls
        balls_frame = tk.Frame(form_frame, bg=COLORS['background'])
        balls_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(balls_frame, text="Balls:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        balls_var = tk.StringVar(value=str(batsman.get('balls', 0)))
        balls_entry = tk.Entry(balls_frame, textvariable=balls_var, font=FONTS['body'], width=10)
        balls_entry.pack(side='left')
        
        # Fours
        fours_frame = tk.Frame(form_frame, bg=COLORS['background'])
        fours_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(fours_frame, text="Fours:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        fours_var = tk.StringVar(value=str(batsman.get('fours', 0)))
        fours_entry = tk.Entry(fours_frame, textvariable=fours_var, font=FONTS['body'], width=10)
        fours_entry.pack(side='left')
        
        # Sixes
        sixes_frame = tk.Frame(form_frame, bg=COLORS['background'])
        sixes_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(sixes_frame, text="Sixes:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        sixes_var = tk.StringVar(value=str(batsman.get('sixes', 0)))
        sixes_entry = tk.Entry(sixes_frame, textvariable=sixes_var, font=FONTS['body'], width=10)
        sixes_entry.pack(side='left')
        
        def save_changes():
            try:
                batsman['runs'] = int(runs_var.get())
                batsman['balls'] = int(balls_var.get())
                batsman['fours'] = int(fours_var.get())
                batsman['sixes'] = int(sixes_var.get())
                
                # Update innings total (recalculate from all batsmen + extras)
                innings = self.match['innings'][self.match['current_innings']]
                total_runs = sum(b.get('runs', 0) for b in innings.get('batsmen', []))
                extras = innings.get('extras', {})
                total_extras = sum(extras.values())
                innings['runs'] = total_runs + total_extras
                
                self._save_and_refresh()
                dialog.destroy()
                messagebox.showinfo("Success", f"Updated stats for {batsman['name']}")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers.")
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        cancel_btn = StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy)
        cancel_btn.pack(side='left')
        
        save_btn = StyledButton(btn_frame, text="Save", variant='primary', command=save_changes)
        save_btn.pack(side='right')
        
        dialog.wait_window()
    
    def _edit_bowler_stats(self):
        """Edit a bowler's stats (overs, runs, wickets)"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        bowlers = innings.get('bowlers', [])
        
        if not bowlers:
            messagebox.showwarning("Warning", "No bowlers in current innings.")
            return
        
        # Show dialog to select bowler
        bowler_names = [f"{b['name']} ({b.get('overs', 0)}-{b.get('runs', 0)}-{b.get('wickets', 0)})" for b in bowlers]
        dialog = PlayerSelectDialog(
            self,
            title="Select Bowler to Edit",
            players=bowler_names,
            allow_custom=False
        )
        
        if dialog.result:
            # Find the selected bowler
            idx = bowler_names.index(dialog.result)
            bowler = bowlers[idx]
            
            # Show edit dialog
            self._show_bowler_edit_dialog(bowler)
    
    def _show_bowler_edit_dialog(self, bowler: Dict[str, Any]):
        """Show dialog to edit bowler stats"""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Stats: {bowler['name']}")
        dialog.geometry("320x280")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 160
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 140
        dialog.geometry(f"+{x}+{y}")
        
        # Form fields
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # Overs (as decimal, e.g., 4.3 = 4 overs 3 balls)
        overs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        overs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(overs_frame, text="Overs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        overs_var = tk.StringVar(value=str(bowler.get('overs', 0.0)))
        overs_entry = tk.Entry(overs_frame, textvariable=overs_var, font=FONTS['body'], width=10)
        overs_entry.pack(side='left')
        tk.Label(overs_frame, text="(e.g., 4.3)", font=FONTS['small'], bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side='left', padx=(SPACING // 2, 0))
        
        # Runs
        runs_frame = tk.Frame(form_frame, bg=COLORS['background'])
        runs_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(runs_frame, text="Runs:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        runs_var = tk.StringVar(value=str(bowler.get('runs', 0)))
        runs_entry = tk.Entry(runs_frame, textvariable=runs_var, font=FONTS['body'], width=10)
        runs_entry.pack(side='left')
        
        # Wickets
        wickets_frame = tk.Frame(form_frame, bg=COLORS['background'])
        wickets_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(wickets_frame, text="Wickets:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        wickets_var = tk.StringVar(value=str(bowler.get('wickets', 0)))
        wickets_entry = tk.Entry(wickets_frame, textvariable=wickets_var, font=FONTS['body'], width=10)
        wickets_entry.pack(side='left')
        
        # Maidens
        maidens_frame = tk.Frame(form_frame, bg=COLORS['background'])
        maidens_frame.pack(fill='x', pady=(0, SPACING // 2))
        tk.Label(maidens_frame, text="Maidens:", font=FONTS['body'], bg=COLORS['background'], fg=COLORS['text_primary'], width=10, anchor='w').pack(side='left')
        maidens_var = tk.StringVar(value=str(bowler.get('maidens', 0)))
        maidens_entry = tk.Entry(maidens_frame, textvariable=maidens_var, font=FONTS['body'], width=10)
        maidens_entry.pack(side='left')
        
        def save_changes():
            try:
                bowler['overs'] = float(overs_var.get())
                bowler['runs'] = int(runs_var.get())
                bowler['wickets'] = int(wickets_var.get())
                bowler['maidens'] = int(maidens_var.get())
                
                self._save_and_refresh()
                dialog.destroy()
                messagebox.showinfo("Success", f"Updated stats for {bowler['name']}")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers.")
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        cancel_btn = StyledButton(btn_frame, text="Cancel", variant='secondary', command=dialog.destroy)
        cancel_btn.pack(side='left')
        
        save_btn = StyledButton(btn_frame, text="Save", variant='primary', command=save_changes)
        save_btn.pack(side='right')
        
        dialog.wait_window()
    
    def _swap_strike(self):
        """Manually swap the strike between batsmen"""
        if not self.match:
            return
        
        innings = self.match['innings'][self.match['current_innings']]
        current_batsmen = innings.get('current_batsmen', [])
        
        if len(current_batsmen) < 2:
            messagebox.showwarning("Warning", "Need 2 batsmen at the crease to swap strike.")
            return
        
        # Swap strike
        for batsman in innings.get('batsmen', []):
            if batsman['id'] in current_batsmen:
                batsman['on_strike'] = not batsman.get('on_strike', False)
        
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
