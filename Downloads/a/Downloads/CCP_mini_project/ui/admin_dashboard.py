"""
Admin Dashboard - Match creation and management with batting order support
FIXED: Vertical stacking layout, max 11 players, no match reset on roster interaction
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
        
        # Note: Toss is now selected when "Start Match" is clicked
        # This follows proper cricket flow - toss happens right before the match
        toss_note_frame = tk.Frame(form, bg=COLORS['card_bg'])
        toss_note_frame.pack(fill='x', pady=(0, SPACING + 4))
        
        tk.Label(
            toss_note_frame,
            text="Note: Toss will be selected when starting the match",
            font=FONTS['small'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        ).pack(anchor='w')
        
        # Hidden variables for toss (populated by popup when starting)
        self.toss_var = tk.StringVar()
        self.decision_var = tk.StringVar(value="bat")
        # Team name change traces for roster titles
        self.team_a_var.trace_add('write', lambda *args: self._update_roster_titles())
        self.team_b_var.trace_add('write', lambda *args: self._update_roster_titles())
        
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
        """Create roster section for a team - FULL WIDTH VERTICAL"""
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
        """Create batting order section for a team - FULL WIDTH VERTICAL"""
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
        """Handle match selection from list - DOES NOT reinitialize match"""
        selection = self.match_listbox.curselection()
        if selection:
            idx = selection[0]
            new_match_id = self.match_ids[idx]
            
            # Only reload if selecting a different match
            if new_match_id != self.selected_match_id:
                self.selected_match_id = new_match_id
                self._load_match_to_form(self.selected_match_id)
        else:
            self.selected_match_id = None
            self._reset_form()
        
        self._update_button_states()
    
    def _load_match_to_form(self, match_id: str):
        """Load match data into the form - IN-PLACE, no reinitialization"""
        match = self.data_manager.get_match(match_id)
        if not match:
            return
        
        teams = match.get('teams', ['', ''])
        self.team_a_var.set(teams[0] if len(teams) > 0 else '')
        self.team_b_var.set(teams[1] if len(teams) > 1 else '')
        self.format_var.set(match.get('format', 'T20'))
        # Toss is now set when starting the match, not during creation
        
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
        """Remove player from batting order
        
        IMPORTANT: During a live match, only allow removal of players who have NOT yet batted.
        """
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
        
        # Check if match is live and this team is currently batting
        if match.get('status') in ['Live', 'Super Over']:
            innings_list = match.get('innings', [])
            current_idx = match.get('current_innings', 0)
            
            if innings_list and current_idx < len(innings_list):
                current_innings = innings_list[current_idx]
                
                if current_innings.get('batting_team') == team_name:
                    batting_state = current_innings.get('current_batting_state', {})
                    next_batsman_idx = batting_state.get('next_batsman_index', 2)
                    
                    if idx < next_batsman_idx:
                        messagebox.showwarning(
                            "Cannot Remove",
                            f"Cannot remove players who have already batted or are currently at the crease."
                        )
                        return
        
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
        """Move player up or down in batting order
        
        IMPORTANT: During a live match, only allow editing of players who have NOT yet batted.
        Players who are currently batting (striker/non-striker) or have already batted cannot be moved.
        """
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
        
        # Check if match is live and this team is currently batting
        if match.get('status') in ['Live', 'Super Over']:
            innings_list = match.get('innings', [])
            current_idx = match.get('current_innings', 0)
            
            if innings_list and current_idx < len(innings_list):
                current_innings = innings_list[current_idx]
                
                # Only restrict if this team is currently batting
                if current_innings.get('batting_team') == team_name:
                    batting_state = current_innings.get('current_batting_state', {})
                    next_batsman_idx = batting_state.get('next_batsman_index', 2)
                    
                    # Players at positions 0 to next_batsman_idx-1 have already batted or are batting
                    # Only allow moving players at positions >= next_batsman_idx
                    if idx < next_batsman_idx or new_idx < next_batsman_idx:
                        messagebox.showwarning(
                            "Cannot Move",
                            f"Cannot move players who have already batted or are currently at the crease.\n"
                            f"Only players at positions {next_batsman_idx + 1} and below can be reordered."
                        )
                        return
        
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
        """Create or update a match (toss is set when starting)"""
        team_a = self.team_a_var.get().strip()
        team_b = self.team_b_var.get().strip()
        format_type = self.format_var.get()
        
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
                # Toss is set when starting the match, not during creation/editing
                
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
            # Create new match (toss is set when starting)
            match = MatchEngine.create_match(
                team_a=team_a,
                team_b=team_b,
                match_format=format_type
            )
            
            self.data_manager.save_match(match['match_id'], match)
            self.selected_match_id = match['match_id']
            messagebox.showinfo("Success", f"Match created! ID: {match['match_id']}\n\nNow add players to rosters and set batting orders.")
        
        self._refresh_match_list()
        self._update_roster_titles()
        self._update_button_states()
    
    def _start_match(self):
        """Start the selected match - shows toss popup first"""
        if not self.selected_match_id:
            return
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        if match.get('status') != 'Upcoming':
            messagebox.showwarning("Error", "Only upcoming matches can be started.")
            return
        
        # Validate match can start
        can_start, error = MatchEngine.validate_match_can_start(match)
        if not can_start:
            messagebox.showerror("Cannot Start Match", error)
            return
        
        # Show toss popup
        toss_result = self._show_toss_popup(match)
        if toss_result is None:
            # User cancelled
            return
        
        toss_winner, toss_decision = toss_result
        
        # Store toss in REQUIRED format
        match['toss'] = {
            'winner': toss_winner,
            'decision': toss_decision
        }
        # Also store in legacy format for backward compatibility
        match['toss_winner'] = toss_winner
        match['toss_decision'] = toss_decision
        
        # Start match
        match, error = MatchEngine.start_match(match)
        if error:
            messagebox.showerror("Error", error)
            return
        
        self.data_manager.save_match(self.selected_match_id, match)
        
        messagebox.showinfo("Success", f"Match started!\n\n{toss_winner} won the toss and elected to {toss_decision}.")
        self._refresh_match_list()
        self._update_button_states()
        
        # Navigate to match editing
        if self.on_edit_match:
            self.on_edit_match(self.selected_match_id)
    
    def _show_toss_popup(self, match: Dict[str, Any]) -> Optional[tuple]:
        """Show toss popup dialog with TWO mandatory steps:
        
        STEP 1: Select toss winner (Team A or Team B)
        STEP 2: Select decision (Bat or Bowl)
        
        Returns (toss_winner, toss_decision) tuple or None if cancelled
        The popup will NOT close until BOTH selections are made.
        """
        teams = match.get('teams', ['Team A', 'Team B'])
        
        # Create popup dialog
        dialog = tk.Toplevel(self)
        dialog.title("Toss")
        dialog.geometry("380x320")
        dialog.configure(bg=COLORS['background'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 190
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 160
        dialog.geometry(f"+{x}+{y}")
        
        result = [None]  # Use list to store result in closure
        
        form_frame = tk.Frame(dialog, bg=COLORS['background'])
        form_frame.pack(fill='both', expand=True, padx=PADDING, pady=PADDING)
        
        # STEP 1: Who won the toss?
        tk.Label(
            form_frame,
            text="STEP 1: Who won the toss?",
            font=FONTS['heading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING))
        
        # Use empty string as initial value to force explicit selection
        toss_winner_var = tk.StringVar(value="")
        
        toss_winner_frame = tk.Frame(form_frame, bg=COLORS['background'])
        toss_winner_frame.pack(fill='x', pady=(0, SPACING * 2))
        
        for team in teams:
            btn = tk.Radiobutton(
                toss_winner_frame,
                text=team,
                variable=toss_winner_var,
                value=team,
                font=FONTS['body'],
                bg=COLORS['background'],
                fg=COLORS['text_primary'],
                selectcolor=COLORS['primary'],
                activebackground=COLORS['background'],
                indicatoron=0,
                width=15,
                padx=10,
                pady=8
            )
            btn.pack(side='left', padx=(0, SPACING // 2))
        
        # STEP 2: Decision (Bat or Bowl) - MANDATORY
        tk.Label(
            form_frame,
            text="STEP 2: Choose bat or bowl",
            font=FONTS['heading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING))
        
        # Use empty string to force explicit selection
        decision_var = tk.StringVar(value="")
        
        decision_frame = tk.Frame(form_frame, bg=COLORS['background'])
        decision_frame.pack(fill='x', pady=(0, SPACING))
        
        for decision, label in [("bat", "Bat First"), ("bowl", "Bowl First")]:
            btn = tk.Radiobutton(
                decision_frame,
                text=label,
                variable=decision_var,
                value=decision,
                font=FONTS['body'],
                bg=COLORS['background'],
                fg=COLORS['text_primary'],
                selectcolor=COLORS['primary'],
                activebackground=COLORS['background'],
                indicatoron=0,
                width=12,
                padx=10,
                pady=8
            )
            btn.pack(side='left', padx=(0, SPACING // 2))
        
        # Error label for validation messages
        error_label = tk.Label(
            form_frame,
            text="",
            font=FONTS['small'],
            bg=COLORS['background'],
            fg=COLORS['danger']
        )
        error_label.pack(anchor='w', pady=(SPACING, 0))
        
        def confirm():
            # VALIDATION: Both selections are MANDATORY
            winner = toss_winner_var.get()
            decision = decision_var.get()
            
            if not winner:
                error_label.config(text="Please select who won the toss")
                return
            
            if not decision:
                error_label.config(text="Please choose bat or bowl")
                return
            
            # Both selections made - proceed
            result[0] = (winner, decision)
            dialog.destroy()
        
        def cancel():
            result[0] = None
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['background'])
        btn_frame.pack(fill='x', pady=(SPACING, 0))
        
        StyledButton(btn_frame, text="Cancel", variant='secondary', command=cancel).pack(side='left')
        StyledButton(btn_frame, text="Start Match", variant='primary', command=confirm).pack(side='right')
        
        dialog.wait_window()
        
        return result[0]
    
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
