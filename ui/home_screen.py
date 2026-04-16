"""
Home Screen - Multi-match list view
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any, List
from config import COLORS, FONTS, PADDING, SPACING, SYNC_INTERVAL
from core.data_manager import DataManager
from utils.time_utils import format_time_ago, get_seconds_since
from .components import StyledButton, MatchCard, CardFrame, LiveIndicator


class HomeScreen(tk.Frame):
    """Home screen showing list of all matches"""
    
    def __init__(
        self,
        parent,
        data_manager: DataManager,
        is_admin: bool = False,
        on_view_match: Optional[Callable] = None,
        on_edit_match: Optional[Callable] = None,
        on_create_match: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLORS['background'], **kwargs)
        
        self.data_manager = data_manager
        self.is_admin = is_admin
        self.on_view_match = on_view_match
        self.on_edit_match = on_edit_match
        self.on_create_match = on_create_match
        
        self.filter_var = tk.StringVar(value="All")
        self.match_cards: List[MatchCard] = []
        
        self._create_ui()
        self._start_sync()
    
    def _create_ui(self):
        """Create the UI components"""
        # Header
        header = tk.Frame(self, bg=COLORS['card_bg'], padx=PADDING + 4, pady=PADDING)
        header.pack(fill='x')
        
        title = tk.Label(
            header,
            text="Live Matches",
            font=FONTS['title'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        title.pack(side='left')
        
        # Admin controls
        if self.is_admin:
            admin_frame = tk.Frame(header, bg=COLORS['card_bg'])
            admin_frame.pack(side='right')
            
            create_btn = StyledButton(
                admin_frame,
                text="+ Create Match",
                variant='primary',
                command=self.on_create_match
            )
            create_btn.pack(side='right')
        
        # Live indicator
        self.live_indicator = LiveIndicator(header)
        self.live_indicator.pack(side='right', padx=(0, SPACING + 4))
        
        # Filter bar
        filter_frame = tk.Frame(self, bg=COLORS['background'], padx=PADDING + 4, pady=SPACING)
        filter_frame.pack(fill='x')
        
        filter_label = tk.Label(
            filter_frame,
            text="Filter:",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary']
        )
        filter_label.pack(side='left', padx=(0, SPACING // 2))
        
        for status in ["All", "Live", "Upcoming", "Completed"]:
            rb = tk.Radiobutton(
                filter_frame,
                text=status,
                variable=self.filter_var,
                value=status,
                font=FONTS['body'],
                bg=COLORS['background'],
                fg=COLORS['text_primary'],
                selectcolor=COLORS['background'],
                activebackground=COLORS['background'],
                command=self._refresh_matches
            )
            rb.pack(side='left', padx=(SPACING // 2, SPACING // 2))
        
        # Scrollable match list
        self.list_container = tk.Frame(self, bg=COLORS['background'])
        self.list_container.pack(fill='both', expand=True, padx=PADDING + 4, pady=PADDING)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(
            self.list_container,
            bg=COLORS['background'],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            self.list_container,
            orient='vertical',
            command=self.canvas.yview
        )
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS['background'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Initial load
        self._refresh_matches()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _refresh_matches(self):
        """Refresh the match list"""
        # Clear existing cards
        for card in self.match_cards:
            card.destroy()
        self.match_cards = []
        
        # Get matches
        matches = self.data_manager.get_all_matches()
        filter_status = self.filter_var.get()
        
        # Filter matches
        filtered_matches = []
        for match_id, match_data in matches.items():
            if filter_status == "All" or match_data.get("status") == filter_status:
                filtered_matches.append({"match_id": match_id, **match_data})
        
        # Sort by status priority (Live first, then Upcoming, then Completed)
        status_priority = {"Live": 0, "Upcoming": 1, "Completed": 2}
        filtered_matches.sort(key=lambda m: status_priority.get(m.get("status", "Upcoming"), 1))
        
        # Create match cards
        if not filtered_matches:
            no_matches_label = tk.Label(
                self.scrollable_frame,
                text="No matches found",
                font=FONTS['body'],
                bg=COLORS['background'],
                fg=COLORS['text_secondary']
            )
            no_matches_label.pack(pady=PADDING * 2)
            self.match_cards.append(no_matches_label)
        else:
            for match in filtered_matches:
                # Get current innings data
                innings = match.get("innings", [])
                current_innings = match.get("current_innings", 0)
                
                score = "0/0"
                overs = "0.0"
                
                if innings and len(innings) > current_innings:
                    current = innings[current_innings]
                    score = f"{current.get('runs', 0)}/{current.get('wickets', 0)}"
                    overs = str(current.get('overs', 0.0))
                
                card = MatchCard(
                    self.scrollable_frame,
                    match_id=match["match_id"],
                    team_a=match.get("teams", ["Team A", "Team B"])[0],
                    team_b=match.get("teams", ["Team A", "Team B"])[1],
                    format_type=match.get("format", "T20"),
                    score=score,
                    overs=overs,
                    status=match.get("status", "Upcoming"),
                    on_view=self.on_view_match,
                    on_edit=self.on_edit_match if self.is_admin else None,
                    is_admin=self.is_admin
                )
                card.pack(fill='x', pady=(0, SPACING + 4))
                self.match_cards.append(card)
        
        # Update scroll region
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _start_sync(self):
        """Start the sync loop for viewer mode"""
        self._sync()
    
    def _sync(self):
        """Check for updates and refresh if needed"""
        last_updated = self.data_manager.get_last_updated()
        seconds_since = get_seconds_since(last_updated)
        
        if self.data_manager.has_changed():
            self._refresh_matches()
        
        # Update live indicator
        if seconds_since == float('inf') or seconds_since > 60:
            self.live_indicator.set_warning("No data")
        elif seconds_since > 5:
            self.live_indicator.set_warning(f"Stale ({int(seconds_since)}s)")
        else:
            self.live_indicator.set_live(True, format_time_ago(last_updated))
        
        # Schedule next sync
        self.after(SYNC_INTERVAL, self._sync)
    
    def refresh(self):
        """Public method to force refresh"""
        self._refresh_matches()
