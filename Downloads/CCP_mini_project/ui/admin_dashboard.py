"""
Admin Dashboard - Match creation and management with batting order support
FIXED: Vertical stacking layout, max 11 players, no match reset on roster interaction
FIXED: Proper toss popup, match starts immediately after toss
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Optional, Dict, Any, List
from config import COLORS, FONTS, PADDING, SPACING, FORMATS
from core.data_manager import DataManager
from core.match_engine import MatchEngine
from .components import StyledButton, CardFrame, StatusBadge, ScrollableFrame

# Maximum players per team
MAX_PLAYERS_PER_TEAM = 11


class TossDialog(tk.Toplevel):
    """
    Toss popup dialog with two steps:
    1. Select toss winner
    2. Select decision (bat/bowl)
    Match starts automatically after toss is completed.
    """
    
    def __init__(self, parent, team_a: str, team_b: str):
        super().__init__(parent)
        
        self.team_a = team_a
        self.team_b = team_b
        self.result = None  # Will be {"winner": team_name, "decision": "bat" or "bowl"}
        
        self.title("Toss")
        
        # Larger window size to ensure all content is visible
        window_width = 500
        window_height = 480
        
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(window_width, window_height)  # Set minimum size
        self.configure(bg=COLORS['background'])
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)  # Allow resizing if needed
        
        # Center the dialog on screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # State variables
        self.toss_winner = tk.StringVar(value="")
        self.toss_decision = tk.StringVar(value="")
        
        self._create_ui()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self.wait_window()
    
    def _create_ui(self):
        """Create the toss dialog UI with vertical layout"""
        main_frame = tk.Frame(self, bg=COLORS['background'], padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Toss",
            font=FONTS['heading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        title_label.pack(pady=(0, 20))
        
        # Step 1: Select toss winner
        step1_label = tk.Label(
            main_frame,
            text="Step 1: Who won the toss?",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        step1_label.pack(anchor='w', pady=(0, 10))
        
        winner_btn_frame = tk.Frame(main_frame, bg=COLORS['background'])
        winner_btn_frame.pack(fill='x', pady=(0, 25))
        
        self.team_a_btn = tk.Button(
            winner_btn_frame,
            text=self.team_a,
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            relief='solid',
            bd=1,
            padx=20,
            pady=12,
            cursor='hand2',
            command=lambda: self._select_winner(self.team_a)
        )
        self.team_a_btn.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        self.team_b_btn = tk.Button(
            winner_btn_frame,
            text=self.team_b,
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            relief='solid',
            bd=1,
            padx=20,
            pady=12,
            cursor='hand2',
            command=lambda: self._select_winner(self.team_b)
        )
        self.team_b_btn.pack(side='left', expand=True, fill='x', padx=(10, 0))
        
        # Step 2: Select decision
        step2_label = tk.Label(
            main_frame,
            text="Step 2: Elected to...",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        step2_label.pack(anchor='w', pady=(0, 10))
        
        decision_btn_frame = tk.Frame(main_frame, bg=COLORS['background'])
        decision_btn_frame.pack(fill='x', pady=(0, 25))
        
        self.bat_btn = tk.Button(
            decision_btn_frame,
            text="Bat",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary'],
            relief='solid',
            bd=1,
            padx=20,
            pady=12,
            cursor='hand2',
            state='disabled',
            command=lambda: self._select_decision("bat")
        )
        self.bat_btn.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        self.bowl_btn = tk.Button(
            decision_btn_frame,
            text="Bowl",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary'],
            relief='solid',
            bd=1,
            padx=20,
            pady=12,
            cursor='hand2',
            state='disabled',
            command=lambda: self._select_decision("bowl")
        )
        self.bowl_btn.pack(side='left', expand=True, fill='x', padx=(10, 0))
        
        # Status display
        self.status_label = tk.Label(
            main_frame,
            text="Please select the toss winner",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary'],
            wraplength=400
        )
        self.status_label.pack(pady=(10, 25))
        
        # Action buttons at bottom
        btn_frame = tk.Frame(main_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', side='bottom')
        
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            relief='solid',
            bd=1,
            padx=25,
            pady=10,
            cursor='hand2',
            command=self._on_cancel
        )
        cancel_btn.pack(side='left')
        
        self.start_btn = tk.Button(
            btn_frame,
            text="Start Match",
            font=FONTS['body'],
            bg=COLORS['success'],
            fg='white',
            relief='solid',
            bd=1,
            padx=25,
            pady=10,
            cursor='hand2',
            state='disabled',
            command=self._on_start
        )
        self.start_btn.pack(side='right')
    
    def _select_winner(self, team: str):
        """Handle toss winner selection"""
        self.toss_winner.set(team)
        
        # Update button styles - highlight selected team
        if team == self.team_a:
            self.team_a_btn.configure(bg=COLORS['primary'], fg='white', state='normal')
            self.team_b_btn.configure(bg=COLORS['card_bg'], fg=COLORS['text_primary'], state='normal')
        else:
            self.team_b_btn.configure(bg=COLORS['primary'], fg='white', state='normal')
            self.team_a_btn.configure(bg=COLORS['card_bg'], fg=COLORS['text_primary'], state='normal')
        
        # Enable decision buttons
        self.bat_btn.configure(state='normal', fg=COLORS['text_primary'])
        self.bowl_btn.configure(state='normal', fg=COLORS['text_primary'])
        
        # Reset decision button styles if re-selecting winner
        self.bat_btn.configure(bg=COLORS['card_bg'])
        self.bowl_btn.configure(bg=COLORS['card_bg'])
        self.toss_decision.set("")
        
        # Update status
        self.status_label.configure(text=f"{team} won the toss. Now select Bat or Bowl.")
        
        # Disable start button until decision is made
        self.start_btn.configure(state='disabled')
    
    def _select_decision(self, decision: str):
        """Handle toss decision selection"""
        self.toss_decision.set(decision)
        
        winner = self.toss_winner.get()
        other_team = self.team_b if winner == self.team_a else self.team_a
        
        # Update button styles - highlight selected decision
        if decision == "bat":
            self.bat_btn.configure(bg=COLORS['success'], fg='white')
            self.bowl_btn.configure(bg=COLORS['card_bg'], fg=COLORS['text_primary'])
            self.status_label.configure(
                text=f"{winner} won toss and elected to BAT.\n{other_team} will bowl first."
            )
        else:
            self.bowl_btn.configure(bg=COLORS['success'], fg='white')
            self.bat_btn.configure(bg=COLORS['card_bg'], fg=COLORS['text_primary'])
            self.status_label.configure(
                text=f"{winner} won toss and elected to BOWL.\n{other_team} will bat first."
            )
        
        # Enable start button
        self.start_btn.configure(state='normal', bg=COLORS['success'])
    
    def _on_start(self):
        """Handle start match button"""
        winner = self.toss_winner.get()
        decision = self.toss_decision.get()
        
        if not winner:
            messagebox.showwarning("Incomplete", "Please select the toss winner.", parent=self)
            return
        
        if not decision:
            messagebox.showwarning("Incomplete", "Please choose bat or bowl.", parent=self)
            return
        
        self.result = {
            "winner": winner,
            "decision": decision
        }
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel/close"""
        self.result = None
        self.destroy()


class AdminDashboard(tk.Frame):
    """Admin dashboard for creating and managing matches"""
    
    def __init__(
        self,
        parent,
        data_manager: DataManager,
        on_back: Optional[Callable] = None,
        on_edit_match: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLORS['background'], **kwargs)
        
        self.data_manager = data_manager
        self.on_back = on_back
        self.on_edit_match = on_edit_match
        
        self.selected_match_id: Optional[str] = None
        
        self._create_ui()
        self._refresh_match_list()
    
    def _create_ui(self):
        """Create the dashboard UI - ALL VERTICAL STACKING"""
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
        
        title = tk.Label(
            header,
            text="Admin Dashboard",
            font=FONTS['title'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        title.pack(side='left', padx=(SPACING, 0))
        
        # Main content - scrollable, VERTICAL STACK ONLY
        scroll_container = ScrollableFrame(self, bg=COLORS['background'])
        scroll_container.pack(fill='both', expand=True)
        content = scroll_container.get_frame()
        content.configure(padx=PADDING, pady=PADDING)
        
        # ===== SECTION 1: MATCH LIST (FULL WIDTH) =====
        match_list_card = CardFrame(content, title="Matches")
        match_list_card.pack(fill='x', pady=(0, SPACING))
        
        match_list_frame = tk.Frame(match_list_card, bg=COLORS['card_bg'])
        match_list_frame.pack(fill='both', expand=True)
        
        self.match_listbox = tk.Listbox(
            match_list_frame,
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            selectbackground=COLORS['primary'],
            selectforeground='white',
            activestyle='none',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            relief='flat',
            height=8
        )
        match_scrollbar = ttk.Scrollbar(match_list_frame, orient='vertical', command=self.match_listbox.yview)
        self.match_listbox.configure(yscrollcommand=match_scrollbar.set)
        
        self.match_listbox.pack(side='left', fill='both', expand=True)
        match_scrollbar.pack(side='right', fill='y')
        self.match_listbox.bind('<<ListboxSelect>>', self._on_match_select)
        
        # ===== SECTION 2: MATCH EDITOR (FULL WIDTH) =====
        editor_card = CardFrame(content, title="Match Editor")
        editor_card.pack(fill='x', pady=(0, SPACING))
        
        self._create_match_form(editor_card)
        
        # ===== SECTION 3: TEAM A ROSTER (FULL WIDTH) =====
        self._create_team_roster_section(content, 'A')
        
        # ===== SECTION 4: TEAM A BATTING ORDER (FULL WIDTH) =====
        self._create_team_batting_order_section(content, 'A')
        
        # ===== SECTION 5: TEAM B ROSTER (FULL WIDTH) =====
        self._create_team_roster_section(content, 'B')
        
        # ===== SECTION 6: TEAM B BATTING ORDER (FULL WIDTH) =====
        self._create_team_batting_order_section(content, 'B')
    
    def _create_match_form(self, parent):
        """Create the match creation/editing form"""
        form = tk.Frame(parent, bg=COLORS['card_bg'])
        form.pack(fill='x', expand=True, pady=(SPACING // 2, 0))
        
        # Team A
        team_a_frame = tk.Frame(form, bg=COLORS['card_bg'])
        team_a_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            team_a_frame,
            text="Team A:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.team_a_var = tk.StringVar()
        self.team_a_entry = tk.Entry(
            team_a_frame,
            textvariable=self.team_a_var,
            font=FONTS['body'],
            width=28
        )
        self.team_a_entry.pack(side='left', fill='x', expand=True, ipady=4)
        
        # Team B
        team_b_frame = tk.Frame(form, bg=COLORS['card_bg'])
        team_b_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            team_b_frame,
            text="Team B:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.team_b_var = tk.StringVar()
        self.team_b_entry = tk.Entry(
            team_b_frame,
            textvariable=self.team_b_var,
            font=FONTS['body'],
            width=28
        )
        self.team_b_entry.pack(side='left', fill='x', expand=True, ipady=4)
        
        # Format
        format_frame = tk.Frame(form, bg=COLORS['card_bg'])
        format_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            format_frame,
            text="Format:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.format_var = tk.StringVar(value="T20")
        self.format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            values=list(FORMATS.keys()),
            state='readonly',
            font=FONTS['body'],
            width=26
        )
        self.format_combo.pack(side='left')
        
        # Toss winner
        toss_frame = tk.Frame(form, bg=COLORS['card_bg'])
        toss_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            toss_frame,
            text="Toss Winner:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.toss_var = tk.StringVar()
        self.toss_combo = ttk.Combobox(
            toss_frame,
            textvariable=self.toss_var,
            state='readonly',
            font=FONTS['body'],
            width=26
        )
        self.toss_combo.pack(side='left')
        
        # Toss decision
        decision_frame = tk.Frame(form, bg=COLORS['card_bg'])
        decision_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            decision_frame,
            text="Elected to:",
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary'],
            width=12,
            anchor='w'
        ).pack(side='left')
        
        self.decision_var = tk.StringVar(value="bat")
        tk.Radiobutton(
            decision_frame,
            text="Bat",
            variable=self.decision_var,
            value="bat",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            activebackground=COLORS['card_bg']
        ).pack(side='left', padx=(0, SPACING // 2))
        
        tk.Radiobutton(
            decision_frame,
            text="Bowl",
            variable=self.decision_var,
            value="bowl",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            activebackground=COLORS['card_bg']
        ).pack(side='left', padx=(SPACING // 2, 0))
        
        # Update toss options when teams change
        self.team_a_var.trace_add('write', self._update_toss_options)
        self.team_b_var.trace_add('write', self._update_toss_options)
        
        # Action buttons
        btn_frame = tk.Frame(form, bg=COLORS['card_bg'])
        btn_frame.pack(fill='x', pady=(SPACING * 2, SPACING // 2))
        
        self.create_btn = StyledButton(
            btn_frame,
            text="Create Match",
            variant='primary',
            command=self._create_match
        )
        self.create_btn.pack(side='left')
        
        self.start_btn = StyledButton(
            btn_frame,
            text="Start Match",
            variant='success',
            command=self._start_match
        )
        self.start_btn.pack(side='left', padx=(SPACING // 2, 0))
        
        self.delete_btn = StyledButton(
            btn_frame,
            text="Delete",
            variant='danger',
            command=self._delete_match
        )
        self.delete_btn.pack(side='left', padx=(SPACING // 2, 0))
        
        self.edit_live_btn = StyledButton(
            btn_frame,
            text="Edit Live",
            variant='warning',
            command=self._edit_live_match
        )
        self.edit_live_btn.pack(side='right')
        
        # Initially hide some buttons
        self._update_button_states()
    
    def _create_team_roster_section(self, parent, team_id: str):
        """
        Create roster section for a team - FULL WIDTH VERTICAL.
        
        IMPORTANT: Roster listboxes do NOT have <<ListboxSelect>> bindings
        that would cause navigation or match reloading. Clicking on roster
        items only selects them for add/remove operations.
        """
        # Store reference for title updates
        roster_card = CardFrame(parent, title=f"Team {team_id} Roster")
        roster_card.pack(fill='x', pady=(0, SPACING))
        
        if team_id == 'A':
            self.team_a_roster_card = roster_card
        else:
            self.team_b_roster_card = roster_card
        
        roster_frame = tk.Frame(roster_card, bg=COLORS['card_bg'])
        roster_frame.pack(fill='both', expand=True)
        
        # Roster list (only this can scroll)
        roster_listbox = tk.Listbox(
            roster_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            height=6
        )
        roster_scrollbar = ttk.Scrollbar(roster_frame, orient='vertical', command=roster_listbox.yview)
        roster_listbox.configure(yscrollcommand=roster_scrollbar.set)
        roster_listbox.pack(side='left', fill='both', expand=True)
        roster_scrollbar.pack(side='right', fill='y')
        
        if team_id == 'A':
            self.team_a_listbox = roster_listbox
        else:
            self.team_b_listbox = roster_listbox
        
        # Add player controls - below the list
        add_frame = tk.Frame(roster_card, bg=COLORS['card_bg'])
        add_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        player_entry = tk.Entry(
            add_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        player_entry.pack(side='left', fill='x', expand=True, padx=(0, SPACING // 2), ipady=2)
        player_entry.bind('<Return>', lambda e, t=team_id: self._add_player_to_roster(t))
        
        if team_id == 'A':
            self.team_a_player_entry = player_entry
        else:
            self.team_b_player_entry = player_entry
        
        add_btn = StyledButton(
            add_frame,
            text="Add",
            variant='primary',
            command=lambda: self._add_player_to_roster(team_id)
        )
        add_btn.pack(side='left', padx=(0, SPACING // 4))
        
        remove_btn = StyledButton(
            add_frame,
            text="Remove",
            variant='danger',
            command=lambda: self._remove_player_from_roster(team_id)
        )
        remove_btn.pack(side='left')
    
    def _create_team_batting_order_section(self, parent, team_id: str):
        """
        Create batting order section for a team - FULL WIDTH VERTICAL.
        
        IMPORTANT: Batting order listboxes do NOT have <<ListboxSelect>> bindings
        that would cause navigation or match reloading. Clicking on batting order
        items only selects them for move/remove operations.
        """
        order_card = CardFrame(parent, title=f"Team {team_id} Batting Order")
        order_card.pack(fill='x', pady=(0, SPACING))
        
        if team_id == 'A':
            self.team_a_order_card = order_card
        else:
            self.team_b_order_card = order_card
        
        order_frame = tk.Frame(order_card, bg=COLORS['card_bg'])
        order_frame.pack(fill='both', expand=True)
        
        # Batting order list (only this can scroll)
        order_listbox = tk.Listbox(
            order_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            height=6
        )
        order_scrollbar = ttk.Scrollbar(order_frame, orient='vertical', command=order_listbox.yview)
        order_listbox.configure(yscrollcommand=order_scrollbar.set)
        order_listbox.pack(side='left', fill='both', expand=True)
        order_scrollbar.pack(side='right', fill='y')
        
        if team_id == 'A':
            self.team_a_order_listbox = order_listbox
        else:
            self.team_b_order_listbox = order_listbox
        
        # Batting order controls - below the list
        order_btn_frame = tk.Frame(order_card, bg=COLORS['card_bg'])
        order_btn_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        add_to_order_btn = StyledButton(
            order_btn_frame,
            text="Add Selected",
            variant='primary',
            command=lambda: self._add_to_batting_order(team_id)
        )
        add_to_order_btn.pack(side='left', padx=(0, SPACING // 4))
        
        move_up_btn = StyledButton(
            order_btn_frame,
            text="Move Up",
            variant='secondary',
            command=lambda: self._move_in_batting_order(team_id, -1)
        )
        move_up_btn.pack(side='left', padx=(0, SPACING // 4))
        
        move_down_btn = StyledButton(
            order_btn_frame,
            text="Move Down",
            variant='secondary',
            command=lambda: self._move_in_batting_order(team_id, 1)
        )
        move_down_btn.pack(side='left', padx=(0, SPACING // 4))
        
        remove_from_order_btn = StyledButton(
            order_btn_frame,
            text="Remove",
            variant='danger',
            command=lambda: self._remove_from_batting_order(team_id)
        )
        remove_from_order_btn.pack(side='left')
        
        auto_order_btn = StyledButton(
            order_btn_frame,
            text="Auto (Roster Order)",
            variant='warning',
            command=lambda: self._auto_batting_order(team_id)
        )
        auto_order_btn.pack(side='right')
    
    def _update_toss_options(self, *args):
        """Update toss winner dropdown options"""
        teams = []
        if self.team_a_var.get():
            teams.append(self.team_a_var.get())
        if self.team_b_var.get():
            teams.append(self.team_b_var.get())
        self.toss_combo['values'] = teams
    
    def _update_roster_titles(self):
        """Update roster panel titles with team names"""
        team_a_name = self.team_a_var.get() or "Team A"
        team_b_name = self.team_b_var.get() or "Team B"
        
        if hasattr(self, 'team_a_roster_card') and self.team_a_roster_card.title_label:
            self.team_a_roster_card.title_label.configure(text=f"{team_a_name} Roster")
        if hasattr(self, 'team_b_roster_card') and self.team_b_roster_card.title_label:
            self.team_b_roster_card.title_label.configure(text=f"{team_b_name} Roster")
        if hasattr(self, 'team_a_order_card') and self.team_a_order_card.title_label:
            self.team_a_order_card.title_label.configure(text=f"{team_a_name} Batting Order")
        if hasattr(self, 'team_b_order_card') and self.team_b_order_card.title_label:
            self.team_b_order_card.title_label.configure(text=f"{team_b_name} Batting Order")
    
    def _update_button_states(self):
        """Update button visibility based on selected match"""
        if self.selected_match_id:
            match = self.data_manager.get_match(self.selected_match_id)
            if match:
                status = match.get('status', 'Upcoming')
                
                self.create_btn.configure(text="Save Changes")
                self.start_btn.configure(
                    state='normal' if status == 'Upcoming' else 'disabled'
                )
                self.delete_btn.configure(state='normal')
                self.edit_live_btn.configure(
                    state='normal' if status in ['Live', 'Super Over'] else 'disabled'
                )
            else:
                self._reset_form()
        else:
            self.create_btn.configure(text="Create Match")
            self.start_btn.configure(state='disabled')
            self.delete_btn.configure(state='disabled')
            self.edit_live_btn.configure(state='disabled')
    
    def _refresh_match_list(self):
        """Refresh the match listbox - does NOT change selection or reset form"""
        # Store current selection
        current_selection = self.match_listbox.curselection()
        current_match_id = self.selected_match_id
        
        self.match_listbox.delete(0, tk.END)
        
        matches = self.data_manager.get_all_matches()
        self.match_ids = []
        
        new_selection_idx = None
        for idx, (match_id, match_data) in enumerate(matches.items()):
            teams = match_data.get('teams', ['?', '?'])
            status = match_data.get('status', 'Upcoming')
            display = f"[{status}] {teams[0]} vs {teams[1]}"
            self.match_listbox.insert(tk.END, display)
            self.match_ids.append(match_id)
            
            # Track if we found the previously selected match
            if match_id == current_match_id:
                new_selection_idx = idx
        
        # Restore selection if the match still exists
        if new_selection_idx is not None:
            self.match_listbox.selection_set(new_selection_idx)
    
    def _on_match_select(self, event):
        """
        Handle match selection from list.
        IMPORTANT: Only triggers when a DIFFERENT match is selected.
        Does NOT reinitialize or reload match data unnecessarily.
        """
        selection = self.match_listbox.curselection()
        if selection:
            idx = selection[0]
            
            # Safety check for index bounds
            if idx >= len(self.match_ids):
                return
            
            new_match_id = self.match_ids[idx]
            
            # Only reload if selecting a DIFFERENT match
            # This prevents unnecessary reloads when clicking the same selection
            if new_match_id != self.selected_match_id:
                self.selected_match_id = new_match_id
                self._load_match_to_form(self.selected_match_id)
                self._update_button_states()
        # Note: We don't reset form on empty selection during normal operation
        # This preserves state when focus changes or when clicking between widgets
    
    def _load_match_to_form(self, match_id: str):
        """Load match data into the form - IN-PLACE, no reinitialization"""
        match = self.data_manager.get_match(match_id)
        if not match:
            return
        
        teams = match.get('teams', ['', ''])
        self.team_a_var.set(teams[0] if len(teams) > 0 else '')
        self.team_b_var.set(teams[1] if len(teams) > 1 else '')
        self.format_var.set(match.get('format', 'T20'))
        self.toss_var.set(match.get('toss_winner', ''))
        self.decision_var.set(match.get('toss_decision', 'bat'))
        
        # Load rosters and batting orders
        self._load_rosters_and_orders(match)
        self._update_roster_titles()
    
    def _reset_form(self):
        """Reset the form to empty state"""
        self.selected_match_id = None
        self.team_a_var.set('')
        self.team_b_var.set('')
        self.format_var.set('T20')
        self.toss_var.set('')
        self.decision_var.set('bat')
        self.match_listbox.selection_clear(0, tk.END)
        self._update_button_states()
        
        # Clear rosters and batting orders
        self.team_a_listbox.delete(0, tk.END)
        self.team_b_listbox.delete(0, tk.END)
        self.team_a_order_listbox.delete(0, tk.END)
        self.team_b_order_listbox.delete(0, tk.END)
        self._update_roster_titles()
    
    def _load_rosters_and_orders(self, match: Dict[str, Any]):
        """Load rosters and batting orders from match data"""
        teams = match.get('teams', ['Team A', 'Team B'])
        rosters = match.get('rosters', {})
        batting_orders = match.get('batting_orders', {})
        
        # Clear and load Team A roster
        self.team_a_listbox.delete(0, tk.END)
        team_a_roster = rosters.get(teams[0], []) if len(teams) > 0 else []
        for player in team_a_roster:
            self.team_a_listbox.insert(tk.END, player)
        
        # Clear and load Team B roster
        self.team_b_listbox.delete(0, tk.END)
        team_b_roster = rosters.get(teams[1], []) if len(teams) > 1 else []
        for player in team_b_roster:
            self.team_b_listbox.insert(tk.END, player)
        
        # Clear and load Team A batting order (numbered)
        self.team_a_order_listbox.delete(0, tk.END)
        team_a_order = batting_orders.get(teams[0], []) if len(teams) > 0 else []
        for i, player in enumerate(team_a_order):
            self.team_a_order_listbox.insert(tk.END, f"{i+1}. {player}")
        
        # Clear and load Team B batting order (numbered)
        self.team_b_order_listbox.delete(0, tk.END)
        team_b_order = batting_orders.get(teams[1], []) if len(teams) > 1 else []
        for i, player in enumerate(team_b_order):
            self.team_b_order_listbox.insert(tk.END, f"{i+1}. {player}")
    
    def _add_player_to_roster(self, team: str):
        """Add a player to the specified team's roster - MAX 11 ENFORCED"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select or create a match first.")
            return
        
        entry = self.team_a_player_entry if team == 'A' else self.team_b_player_entry
        listbox = self.team_a_listbox if team == 'A' else self.team_b_listbox
        
        player_name = entry.get().strip()
        if not player_name:
            return
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        teams = match.get('teams', ['Team A', 'Team B'])
        team_name = teams[0] if team == 'A' else teams[1]
        
        # Initialize rosters if not exists
        if 'rosters' not in match:
            match['rosters'] = {}
        if team_name not in match['rosters']:
            match['rosters'][team_name] = []
        
        # Check max 11 players limit
        if len(match['rosters'][team_name]) >= MAX_PLAYERS_PER_TEAM:
            messagebox.showerror("Error", f"Max {MAX_PLAYERS_PER_TEAM} players allowed per team.")
            return
        
        # Add player if not already in roster
        if player_name not in match['rosters'][team_name]:
            match['rosters'][team_name].append(player_name)
            listbox.insert(tk.END, player_name)
            entry.delete(0, tk.END)
            # Save IN-PLACE - does not reset match
            self.data_manager.save_match(self.selected_match_id, match)
        else:
            messagebox.showinfo("Info", f"{player_name} is already in the roster.")
    
    def _remove_player_from_roster(self, team: str):
        """Remove a player from the roster"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        listbox = self.team_a_listbox if team == 'A' else self.team_b_listbox
        order_listbox = self.team_a_order_listbox if team == 'A' else self.team_b_order_listbox
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to remove.")
            return
        
        idx = selection[0]
        player_name = listbox.get(idx)
        
        if messagebox.askyesno("Confirm", f"Remove {player_name} from roster?"):
            match = self.data_manager.get_match(self.selected_match_id)
            if not match:
                return
            
            teams = match.get('teams', ['Team A', 'Team B'])
            team_name = teams[0] if team == 'A' else teams[1]
            
            if 'rosters' in match and team_name in match['rosters']:
                if player_name in match['rosters'][team_name]:
                    match['rosters'][team_name].remove(player_name)
                    listbox.delete(idx)
                    
                    # Also remove from batting order if present
                    if 'batting_orders' in match and team_name in match['batting_orders']:
                        if player_name in match['batting_orders'][team_name]:
                            match['batting_orders'][team_name].remove(player_name)
                            # Refresh batting order display (numbered)
                            order_listbox.delete(0, tk.END)
                            for i, p in enumerate(match['batting_orders'][team_name]):
                                order_listbox.insert(tk.END, f"{i+1}. {p}")
                    
                    # Save IN-PLACE - does not reset match
                    self.data_manager.save_match(self.selected_match_id, match)
    
    def _add_to_batting_order(self, team: str):
        """Add selected roster player to batting order - MAX 11 ENFORCED"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        roster_listbox = self.team_a_listbox if team == 'A' else self.team_b_listbox
        order_listbox = self.team_a_order_listbox if team == 'A' else self.team_b_order_listbox
        
        selection = roster_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a player from roster.")
            return
        
        player_name = roster_listbox.get(selection[0])
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        teams = match.get('teams', ['Team A', 'Team B'])
        team_name = teams[0] if team == 'A' else teams[1]
        
        # Initialize batting orders if not exists
        if 'batting_orders' not in match:
            match['batting_orders'] = {}
        if team_name not in match['batting_orders']:
            match['batting_orders'][team_name] = []
        
        # Check batting order cannot exceed roster length
        roster = match.get('rosters', {}).get(team_name, [])
        if len(match['batting_orders'][team_name]) >= len(roster):
            messagebox.showwarning("Warning", "Batting order cannot exceed roster size.")
            return
        
        # Check max 11 players limit
        if len(match['batting_orders'][team_name]) >= MAX_PLAYERS_PER_TEAM:
            messagebox.showerror("Error", f"Max {MAX_PLAYERS_PER_TEAM} players in batting order.")
            return
        
        # Add to batting order if not already in
        if player_name not in match['batting_orders'][team_name]:
            match['batting_orders'][team_name].append(player_name)
            order_listbox.insert(tk.END, f"{order_listbox.size() + 1}. {player_name}")
            # Save IN-PLACE - does not reset match
            self.data_manager.save_match(self.selected_match_id, match)
        else:
            messagebox.showinfo("Info", f"{player_name} is already in batting order.")
    
    def _remove_from_batting_order(self, team: str):
        """Remove player from batting order"""
        if not self.selected_match_id:
            return
        
        order_listbox = self.team_a_order_listbox if team == 'A' else self.team_b_order_listbox
        selection = order_listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to remove from batting order.")
            return
        
        idx = selection[0]
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        teams = match.get('teams', ['Team A', 'Team B'])
        team_name = teams[0] if team == 'A' else teams[1]
        
        if 'batting_orders' in match and team_name in match['batting_orders']:
            if idx < len(match['batting_orders'][team_name]):
                match['batting_orders'][team_name].pop(idx)
                
                # Refresh display (numbered)
                order_listbox.delete(0, tk.END)
                for i, p in enumerate(match['batting_orders'][team_name]):
                    order_listbox.insert(tk.END, f"{i+1}. {p}")
                
                # Save IN-PLACE - does not reset match
                self.data_manager.save_match(self.selected_match_id, match)
    
    def _move_in_batting_order(self, team: str, direction: int):
        """Move player up or down in batting order"""
        if not self.selected_match_id:
            return
        
        order_listbox = self.team_a_order_listbox if team == 'A' else self.team_b_order_listbox
        selection = order_listbox.curselection()
        
        if not selection:
            return
        
        idx = selection[0]
        new_idx = idx + direction
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        teams = match.get('teams', ['Team A', 'Team B'])
        team_name = teams[0] if team == 'A' else teams[1]
        
        if 'batting_orders' in match and team_name in match['batting_orders']:
            order = match['batting_orders'][team_name]
            
            if 0 <= new_idx < len(order):
                # Swap positions
                order[idx], order[new_idx] = order[new_idx], order[idx]
                
                # Refresh display (numbered)
                order_listbox.delete(0, tk.END)
                for i, p in enumerate(order):
                    order_listbox.insert(tk.END, f"{i+1}. {p}")
                
                # Keep selection on moved item
                order_listbox.selection_set(new_idx)
                
                # Save IN-PLACE - does not reset match
                self.data_manager.save_match(self.selected_match_id, match)
    
    def _auto_batting_order(self, team: str):
        """Auto-set batting order from roster order"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        teams = match.get('teams', ['Team A', 'Team B'])
        team_name = teams[0] if team == 'A' else teams[1]
        
        roster = match.get('rosters', {}).get(team_name, [])
        
        if not roster:
            messagebox.showwarning("Warning", "Please add players to roster first.")
            return
        
        # Set batting order to roster order (max 11)
        if 'batting_orders' not in match:
            match['batting_orders'] = {}
        match['batting_orders'][team_name] = roster[:MAX_PLAYERS_PER_TEAM].copy()
        
        # Refresh display (numbered)
        order_listbox = self.team_a_order_listbox if team == 'A' else self.team_b_order_listbox
        order_listbox.delete(0, tk.END)
        for i, p in enumerate(match['batting_orders'][team_name]):
            order_listbox.insert(tk.END, f"{i+1}. {p}")
        
        # Save IN-PLACE - does not reset match
        self.data_manager.save_match(self.selected_match_id, match)
        messagebox.showinfo("Success", f"Batting order set to roster order for {team_name}.")
    
    def _create_match(self):
        """Create or update a match"""
        team_a = self.team_a_var.get().strip()
        team_b = self.team_b_var.get().strip()
        format_type = self.format_var.get()
        toss_winner = self.toss_var.get()
        toss_decision = self.decision_var.get()
        
        if not team_a or not team_b:
            messagebox.showwarning("Validation Error", "Please enter both team names.")
            return
        
        if self.selected_match_id:
            # Update existing match - IN-PLACE modification only
            match = self.data_manager.get_match(self.selected_match_id)
            if match:
                old_teams = match.get('teams', ['', ''])
                match['teams'] = [team_a, team_b]
                match['format'] = format_type
                match['total_overs'] = FORMATS[format_type]['overs']
                match['total_innings'] = FORMATS[format_type]['innings']
                match['toss_winner'] = toss_winner
                match['toss_decision'] = toss_decision
                
                # Update roster and batting order keys if team names changed
                if old_teams[0] != team_a and old_teams[0] in match.get('rosters', {}):
                    match['rosters'][team_a] = match['rosters'].pop(old_teams[0])
                if old_teams[1] != team_b and old_teams[1] in match.get('rosters', {}):
                    match['rosters'][team_b] = match['rosters'].pop(old_teams[1])
                if old_teams[0] != team_a and old_teams[0] in match.get('batting_orders', {}):
                    match['batting_orders'][team_a] = match['batting_orders'].pop(old_teams[0])
                if old_teams[1] != team_b and old_teams[1] in match.get('batting_orders', {}):
                    match['batting_orders'][team_b] = match['batting_orders'].pop(old_teams[1])
                
                self.data_manager.save_match(self.selected_match_id, match)
                messagebox.showinfo("Success", "Match updated successfully!")
        else:
            # Create new match
            match = MatchEngine.create_match(
                team_a=team_a,
                team_b=team_b,
                match_format=format_type,
                toss_winner=toss_winner,
                toss_decision=toss_decision
            )
            
            self.data_manager.save_match(match['match_id'], match)
            self.selected_match_id = match['match_id']
            messagebox.showinfo("Success", f"Match created! ID: {match['match_id']}\n\nNow add players to rosters and set batting orders.")
        
        self._refresh_match_list()
        self._update_roster_titles()
        self._update_button_states()
    
    def _start_match(self):
        """
        Start the selected match.
        Shows toss popup first, then starts match automatically after toss completion.
        """
        if not self.selected_match_id:
            return
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        if match.get('status') != 'Upcoming':
            messagebox.showwarning("Error", "Only upcoming matches can be started.")
            return
        
        # Validate match can start (rosters and batting orders)
        can_start, error = MatchEngine.validate_match_can_start(match)
        if not can_start:
            messagebox.showerror("Cannot Start Match", error)
            return
        
        # Get team names
        teams = match.get('teams', ['Team A', 'Team B'])
        team_a = teams[0] if len(teams) > 0 else 'Team A'
        team_b = teams[1] if len(teams) > 1 else 'Team B'
        
        # Show toss popup
        toss_dialog = TossDialog(self, team_a, team_b)
        
        # Check if toss was completed
        if not toss_dialog.result:
            # User cancelled toss - do not start match
            return
        
        # Update match with toss result
        toss_result = toss_dialog.result
        match['toss_winner'] = toss_result['winner']
        match['toss_decision'] = toss_result['decision']
        
        # Update form display
        self.toss_var.set(toss_result['winner'])
        self.decision_var.set(toss_result['decision'])
        
        # Start match IMMEDIATELY after toss
        match, error = MatchEngine.start_match(match)
        if error:
            messagebox.showerror("Error", error)
            return
        
        self.data_manager.save_match(self.selected_match_id, match)
        
        self._refresh_match_list()
        self._update_button_states()
        
        # Navigate DIRECTLY to match scoring (no confirmation dialog needed)
        if self.on_edit_match:
            self.on_edit_match(self.selected_match_id)
    
    def _delete_match(self):
        """Delete the selected match"""
        if not self.selected_match_id:
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this match?"):
            self.data_manager.delete_match(self.selected_match_id)
            self._refresh_match_list()
            self._reset_form()
    
    def _edit_live_match(self):
        """Navigate to live match editing"""
        if self.selected_match_id and self.on_edit_match:
            self.on_edit_match(self.selected_match_id)
    
    def refresh(self):
        """Public method to refresh the dashboard"""
        self._refresh_match_list()
