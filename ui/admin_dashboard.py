"""
Admin Dashboard - Match creation and management
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Optional, Dict, Any, List
from config import COLORS, FONTS, PADDING, SPACING, FORMATS
from core.data_manager import DataManager
from core.match_engine import MatchEngine
from .components import StyledButton, CardFrame, StatusBadge, ScrollableFrame


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
        """Create the dashboard UI"""
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
        
        # Main content - scrollable
        scroll_container = ScrollableFrame(self, bg=COLORS['background'])
        scroll_container.pack(fill='both', expand=True)
        content = scroll_container.get_frame()
        content.configure(padx=PADDING, pady=PADDING)
        
        # Top section - Match list and Match editor side by side
        top_section = tk.Frame(content, bg=COLORS['background'])
        top_section.pack(fill='x', pady=(0, SPACING))
        
        # Left panel - Match list
        left_panel = CardFrame(top_section, title="Matches")
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Match list with scrollbar
        match_list_frame = tk.Frame(left_panel, bg=COLORS['card_bg'])
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
            height=10
        )
        match_scrollbar = ttk.Scrollbar(match_list_frame, orient='vertical', command=self.match_listbox.yview)
        self.match_listbox.configure(yscrollcommand=match_scrollbar.set)
        
        self.match_listbox.pack(side='left', fill='both', expand=True)
        match_scrollbar.pack(side='right', fill='y')
        self.match_listbox.bind('<<ListboxSelect>>', self._on_match_select)
        
        # Right panel - Match editor
        right_panel = CardFrame(top_section, title="Match Editor")
        right_panel.pack(side='right', fill='both', expand=True, padx=(SPACING, 0))
        
        # Create match form
        self._create_match_form(right_panel)
        
        # Bottom section - Roster Management (only shown when a match is selected)
        self.roster_section = tk.Frame(content, bg=COLORS['background'])
        self.roster_section.pack(fill='x', pady=(SPACING, 0))
        
        self._create_roster_management(self.roster_section)
    
    def _create_match_form(self, parent):
        """Create the match creation/editing form"""
        form = tk.Frame(parent, bg=COLORS['card_bg'])
        form.pack(fill='both', expand=True, pady=(SPACING // 2, 0))
        
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
    
    def _create_roster_management(self, parent):
        """Create the roster management section"""
        roster_label = tk.Label(
            parent,
            text="Team Roster Management",
            font=FONTS['heading'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        roster_label.pack(anchor='w', pady=(0, SPACING))
        
        # Container for both teams
        teams_container = tk.Frame(parent, bg=COLORS['background'])
        teams_container.pack(fill='x')
        
        # Team A Roster
        team_a_card = CardFrame(teams_container, title="Team A Roster")
        team_a_card.pack(side='left', fill='both', expand=True, padx=(0, SPACING // 2))
        
        self.team_a_roster_frame = tk.Frame(team_a_card, bg=COLORS['card_bg'])
        self.team_a_roster_frame.pack(fill='both', expand=True)
        
        # Team A roster list
        self.team_a_listbox = tk.Listbox(
            self.team_a_roster_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            height=8
        )
        team_a_scrollbar = ttk.Scrollbar(self.team_a_roster_frame, orient='vertical', command=self.team_a_listbox.yview)
        self.team_a_listbox.configure(yscrollcommand=team_a_scrollbar.set)
        self.team_a_listbox.pack(side='left', fill='both', expand=True)
        team_a_scrollbar.pack(side='right', fill='y')
        
        # Team A buttons
        team_a_btn_frame = tk.Frame(team_a_card, bg=COLORS['card_bg'])
        team_a_btn_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        self.team_a_entry = tk.Entry(
            team_a_btn_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        self.team_a_entry.pack(side='left', fill='x', expand=True, padx=(0, SPACING // 2), ipady=2)
        self.team_a_entry.bind('<Return>', lambda e: self._add_player_to_roster('A'))
        
        add_a_btn = StyledButton(
            team_a_btn_frame,
            text="Add",
            variant='primary',
            command=lambda: self._add_player_to_roster('A')
        )
        add_a_btn.pack(side='left', padx=(0, SPACING // 4))
        
        edit_a_btn = StyledButton(
            team_a_btn_frame,
            text="Edit",
            variant='secondary',
            command=lambda: self._edit_player_in_roster('A')
        )
        edit_a_btn.pack(side='left', padx=(0, SPACING // 4))
        
        remove_a_btn = StyledButton(
            team_a_btn_frame,
            text="Remove",
            variant='danger',
            command=lambda: self._remove_player_from_roster('A')
        )
        remove_a_btn.pack(side='left')
        
        # Team B Roster
        team_b_card = CardFrame(teams_container, title="Team B Roster")
        team_b_card.pack(side='right', fill='both', expand=True, padx=(SPACING // 2, 0))
        
        self.team_b_roster_frame = tk.Frame(team_b_card, bg=COLORS['card_bg'])
        self.team_b_roster_frame.pack(fill='both', expand=True)
        
        # Team B roster list
        self.team_b_listbox = tk.Listbox(
            self.team_b_roster_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            selectmode='single',
            highlightthickness=1,
            highlightbackground=COLORS['border'],
            height=8
        )
        team_b_scrollbar = ttk.Scrollbar(self.team_b_roster_frame, orient='vertical', command=self.team_b_listbox.yview)
        self.team_b_listbox.configure(yscrollcommand=team_b_scrollbar.set)
        self.team_b_listbox.pack(side='left', fill='both', expand=True)
        team_b_scrollbar.pack(side='right', fill='y')
        
        # Team B buttons
        team_b_btn_frame = tk.Frame(team_b_card, bg=COLORS['card_bg'])
        team_b_btn_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        self.team_b_entry = tk.Entry(
            team_b_btn_frame,
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'],
            highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        self.team_b_entry.pack(side='left', fill='x', expand=True, padx=(0, SPACING // 2), ipady=2)
        self.team_b_entry.bind('<Return>', lambda e: self._add_player_to_roster('B'))
        
        add_b_btn = StyledButton(
            team_b_btn_frame,
            text="Add",
            variant='primary',
            command=lambda: self._add_player_to_roster('B')
        )
        add_b_btn.pack(side='left', padx=(0, SPACING // 4))
        
        edit_b_btn = StyledButton(
            team_b_btn_frame,
            text="Edit",
            variant='secondary',
            command=lambda: self._edit_player_in_roster('B')
        )
        edit_b_btn.pack(side='left', padx=(0, SPACING // 4))
        
        remove_b_btn = StyledButton(
            team_b_btn_frame,
            text="Remove",
            variant='danger',
            command=lambda: self._remove_player_from_roster('B')
        )
        remove_b_btn.pack(side='left')
    
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
        # Find the CardFrame widgets and update their titles
        team_a_name = self.team_a_var.get() or "Team A"
        team_b_name = self.team_b_var.get() or "Team B"
        
        # Update title labels in the roster section
        for widget in self.roster_section.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, CardFrame):
                        # Check the title and update
                        title_text = child.title_label.cget('text')
                        if 'Team A' in title_text or title_text == team_a_name + " Roster":
                            child.title_label.configure(text=f"{team_a_name} Roster")
                        elif 'Team B' in title_text or title_text == team_b_name + " Roster":
                            child.title_label.configure(text=f"{team_b_name} Roster")
    
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
                    state='normal' if status == 'Live' else 'disabled'
                )
            else:
                self._reset_form()
        else:
            self.create_btn.configure(text="Create Match")
            self.start_btn.configure(state='disabled')
            self.delete_btn.configure(state='disabled')
            self.edit_live_btn.configure(state='disabled')
    
    def _refresh_match_list(self):
        """Refresh the match listbox"""
        self.match_listbox.delete(0, tk.END)
        
        matches = self.data_manager.get_all_matches()
        self.match_ids = []
        
        for match_id, match_data in matches.items():
            teams = match_data.get('teams', ['?', '?'])
            status = match_data.get('status', 'Upcoming')
            display = f"[{status}] {teams[0]} vs {teams[1]}"
            self.match_listbox.insert(tk.END, display)
            self.match_ids.append(match_id)
    
    def _on_match_select(self, event):
        """Handle match selection from list"""
        selection = self.match_listbox.curselection()
        if selection:
            idx = selection[0]
            self.selected_match_id = self.match_ids[idx]
            self._load_match_to_form(self.selected_match_id)
        else:
            self.selected_match_id = None
            self._reset_form()
        
        self._update_button_states()
    
    def _load_match_to_form(self, match_id: str):
        """Load match data into the form"""
        match = self.data_manager.get_match(match_id)
        if not match:
            return
        
        teams = match.get('teams', ['', ''])
        self.team_a_var.set(teams[0] if len(teams) > 0 else '')
        self.team_b_var.set(teams[1] if len(teams) > 1 else '')
        self.format_var.set(match.get('format', 'T20'))
        self.toss_var.set(match.get('toss_winner', ''))
        self.decision_var.set(match.get('toss_decision', 'bat'))
        
        # Load rosters
        self._load_rosters(match)
    
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
        
        # Clear rosters
        self.team_a_listbox.delete(0, tk.END)
        self.team_b_listbox.delete(0, tk.END)
        self._update_roster_titles()
    
    def _load_rosters(self, match: Dict[str, Any]):
        """Load rosters from match data into the listboxes"""
        teams = match.get('teams', ['Team A', 'Team B'])
        rosters = match.get('rosters', {})
        
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
        
        # Update titles
        self._update_roster_titles()
    
    def _add_player_to_roster(self, team: str):
        """Add a player to the specified team's roster"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        entry = self.team_a_entry if team == 'A' else self.team_b_entry
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
        
        # Add player if not already in roster
        if player_name not in match['rosters'][team_name]:
            match['rosters'][team_name].append(player_name)
            listbox.insert(tk.END, player_name)
            entry.delete(0, tk.END)
            self.data_manager.save_match(self.selected_match_id, match)
        else:
            messagebox.showinfo("Info", f"{player_name} is already in the roster.")
    
    def _edit_player_in_roster(self, team: str):
        """Edit a player's name in the roster"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        listbox = self.team_a_listbox if team == 'A' else self.team_b_listbox
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Warning", "Please select a player to edit.")
            return
        
        idx = selection[0]
        old_name = listbox.get(idx)
        
        new_name = simpledialog.askstring(
            "Edit Player",
            "Enter new name:",
            initialvalue=old_name
        )
        
        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            
            match = self.data_manager.get_match(self.selected_match_id)
            if not match:
                return
            
            teams = match.get('teams', ['Team A', 'Team B'])
            team_name = teams[0] if team == 'A' else teams[1]
            
            if 'rosters' in match and team_name in match['rosters']:
                roster = match['rosters'][team_name]
                if old_name in roster:
                    roster_idx = roster.index(old_name)
                    roster[roster_idx] = new_name
                    
                    listbox.delete(idx)
                    listbox.insert(idx, new_name)
                    
                    self.data_manager.save_match(self.selected_match_id, match)
    
    def _remove_player_from_roster(self, team: str):
        """Remove a player from the roster"""
        if not self.selected_match_id:
            messagebox.showwarning("Warning", "Please select a match first.")
            return
        
        listbox = self.team_a_listbox if team == 'A' else self.team_b_listbox
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
                    self.data_manager.save_match(self.selected_match_id, match)
    
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
            # Update existing match
            match = self.data_manager.get_match(self.selected_match_id)
            if match:
                match['teams'] = [team_a, team_b]
                match['format'] = format_type
                match['total_overs'] = FORMATS[format_type]['overs']
                match['total_innings'] = FORMATS[format_type]['innings']
                match['toss_winner'] = toss_winner
                match['toss_decision'] = toss_decision
                
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
            messagebox.showinfo("Success", f"Match created! ID: {match['match_id']}")
        
        self._refresh_match_list()
        self._reset_form()
    
    def _start_match(self):
        """Start the selected match"""
        if not self.selected_match_id:
            return
        
        match = self.data_manager.get_match(self.selected_match_id)
        if not match:
            return
        
        if match.get('status') != 'Upcoming':
            messagebox.showwarning("Error", "Only upcoming matches can be started.")
            return
        
        match = MatchEngine.start_match(match)
        self.data_manager.save_match(self.selected_match_id, match)
        
        messagebox.showinfo("Success", "Match started!")
        self._refresh_match_list()
        self._update_button_states()
        
        # Navigate to match editing
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
