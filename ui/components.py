"""
Reusable UI Components for Tkinter
ESPN-inspired design components
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List, Dict, Any
from config import COLORS, FONTS, PADDING, SPACING
from core.calculations import format_overs


class ScrollableFrame(tk.Frame):
    """A scrollable frame container"""
    
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', COLORS['background'])
        super().__init__(parent, bg=bg, **kwargs)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas resize to update inner frame width
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Pack widgets
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel
        self.scrollable_frame.bind('<Enter>', self._bind_mousewheel)
        self.scrollable_frame.bind('<Leave>', self._unbind_mousewheel)
    
    def _on_canvas_configure(self, event):
        """Update the inner frame width to match canvas width"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def _bind_mousewheel(self, event):
        """Bind mousewheel to scroll"""
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind_all('<Button-4>', self._on_mousewheel)
        self.canvas.bind_all('<Button-5>', self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        """Unbind mousewheel"""
        self.canvas.unbind_all('<MouseWheel>')
        self.canvas.unbind_all('<Button-4>')
        self.canvas.unbind_all('<Button-5>')
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scroll"""
        if event.num == 4:
            self.canvas.yview_scroll(-1, 'units')
        elif event.num == 5:
            self.canvas.yview_scroll(1, 'units')
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def get_frame(self):
        """Return the scrollable frame to add content to"""
        return self.scrollable_frame


class StyledFrame(tk.Frame):
    """A styled frame with card-like appearance"""
    
    def __init__(self, parent, **kwargs):
        bg = kwargs.pop('bg', COLORS['card_bg'])
        super().__init__(parent, bg=bg, **kwargs)
        self.configure(
            highlightbackground=COLORS['border'],
            highlightthickness=1
        )


class CardFrame(tk.Frame):
    """A card component with shadow-like border"""
    
    def __init__(self, parent, title: Optional[str] = None, **kwargs):
        bg = kwargs.pop('bg', COLORS['card_bg'])
        super().__init__(parent, bg=bg, padx=PADDING + 4, pady=PADDING, **kwargs)
        self.configure(
            highlightbackground=COLORS['border'],
            highlightthickness=1
        )
        
        if title:
            title_label = tk.Label(
                self,
                text=title,
                font=FONTS['heading'],
                bg=COLORS['card_bg'],
                fg=COLORS['text_primary'],
                anchor='w'
            )
            title_label.pack(fill='x', pady=(0, SPACING + 4))


class StyledButton(tk.Button):
    """A styled button with ESPN-like appearance"""
    
    def __init__(self, parent, variant: str = 'primary', **kwargs):
        self.variant = variant
        
        # Set colors based on variant
        if variant == 'primary':
            bg = COLORS['primary']
            fg = 'white'
            active_bg = '#1557b0'
        elif variant == 'success':
            bg = COLORS['runs']
            fg = 'white'
            active_bg = '#2d8a47'
        elif variant == 'danger':
            bg = COLORS['wickets']
            fg = 'white'
            active_bg = '#c5221f'
        elif variant == 'warning':
            bg = COLORS['extras']
            fg = COLORS['text_primary']
            active_bg = '#e5a900'
        else:  # secondary
            bg = COLORS['background']
            fg = COLORS['text_primary']
            active_bg = COLORS['border']
        
        super().__init__(
            parent,
            bg=bg,
            fg=fg,
            font=FONTS['button'],
            activebackground=active_bg,
            activeforeground=fg,
            relief='flat',
            cursor='hand2',
            padx=14,
            pady=8,
            **kwargs
        )


class ScoreDisplay(tk.Frame):
    """Large score display component"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['card_bg'], **kwargs)
        
        self.score_var = tk.StringVar(value="0/0")
        self.overs_var = tk.StringVar(value="0.0 overs")
        self.run_rate_var = tk.StringVar(value="RR: 0.00")
        
        # Score label
        self.score_label = tk.Label(
            self,
            textvariable=self.score_var,
            font=FONTS['score'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        self.score_label.pack(pady=(SPACING // 2, SPACING // 4))
        
        # Overs label
        self.overs_label = tk.Label(
            self,
            textvariable=self.overs_var,
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        self.overs_label.pack(pady=(0, SPACING // 4))
        
        # Run rate label
        self.rr_label = tk.Label(
            self,
            textvariable=self.run_rate_var,
            font=FONTS['subheading'],
            bg=COLORS['card_bg'],
            fg=COLORS['primary']
        )
        self.rr_label.pack(pady=(0, SPACING // 2))
    
    def update_score(self, runs: int, wickets: int, overs: float, run_rate: float):
        """Update the score display"""
        self.score_var.set(f"{runs}/{wickets}")
        self.overs_var.set(f"{format_overs(overs)} overs")
        self.run_rate_var.set(f"RR: {run_rate:.2f}")


class StatusBadge(tk.Label):
    """Status badge component"""
    
    def __init__(self, parent, status: str = "Upcoming", **kwargs):
        self.status = status
        colors = self._get_status_colors(status)
        
        super().__init__(
            parent,
            text=status,
            bg=colors['bg'],
            fg=colors['fg'],
            font=FONTS['small'],
            padx=8,
            pady=4,
            **kwargs
        )
    
    def _get_status_colors(self, status: str) -> Dict[str, str]:
        """Get colors for status"""
        if status == "Live":
            return {'bg': COLORS['live'], 'fg': 'white'}
        elif status == "Completed":
            return {'bg': COLORS['completed'], 'fg': 'white'}
        else:
            return {'bg': COLORS['upcoming'], 'fg': 'white'}
    
    def set_status(self, status: str):
        """Update status"""
        self.status = status
        colors = self._get_status_colors(status)
        self.configure(text=status, bg=colors['bg'], fg=colors['fg'])


class DataTable(tk.Frame):
    """Table component using Treeview"""
    
    def __init__(self, parent, columns: List[str], height: int = 8, **kwargs):
        super().__init__(parent, bg=COLORS['card_bg'], **kwargs)
        
        self.columns = columns
        
        # Create Treeview with configurable height
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            selectmode='browse',
            height=height
        )
        
        # Configure style
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background=COLORS['card_bg'],
            foreground=COLORS['text_primary'],
            fieldbackground=COLORS['card_bg'],
            font=FONTS['body'],
            rowheight=32
        )
        style.configure(
            "Custom.Treeview.Heading",
            font=FONTS['subheading'],
            background=COLORS['background'],
            foreground=COLORS['text_primary']
        )
        self.tree.configure(style="Custom.Treeview")
        
        # Set up columns with better widths
        column_widths = {
            'Name': 140,
            'Runs': 70,
            'Balls': 70,
            '4s': 50,
            '6s': 50,
            'SR': 80,
            'Overs': 80,
            'Wickets': 80,
            'Econ': 80,
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = column_widths.get(col, 90)
            self.tree.column(col, width=width, anchor='center', minwidth=50)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True, pady=(SPACING // 2, 0))
        scrollbar.pack(side='right', fill='y', pady=(SPACING // 2, 0))
    
    def clear(self):
        """Clear all data"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def add_row(self, values: List[Any]):
        """Add a row of data"""
        self.tree.insert('', 'end', values=values)
    
    def set_data(self, data: List[List[Any]]):
        """Set all data at once"""
        self.clear()
        for row in data:
            self.add_row(row)


class BallTimeline(tk.Frame):
    """Ball-by-ball timeline display"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['card_bg'], **kwargs)
        
        # Configure frame to have minimum height
        self.configure(height=80)
        self.pack_propagate(False)
        
        self.canvas = tk.Canvas(
            self,
            bg=COLORS['card_bg'],
            highlightthickness=0,
            height=80,
            width=600
        )
        self.canvas.pack(fill='both', expand=True, pady=(SPACING // 4, SPACING // 4))
        
        self.balls = []
        
        # Bind resize event to redraw
        self.canvas.bind('<Configure>', lambda e: self._redraw())
    
    def add_ball(self, runs: int, is_wicket: bool = False, extra_type: Optional[str] = None):
        """Add a ball to the timeline"""
        ball_data = {
            'runs': runs,
            'is_wicket': is_wicket,
            'extra_type': extra_type
        }
        self.balls.append(ball_data)
        self._redraw()
    
    def clear(self):
        """Clear the timeline"""
        self.balls = []
        self._redraw()
    
    def _redraw(self):
        """Redraw the timeline"""
        self.canvas.delete('all')
        
        # Get canvas dimensions
        canvas_height = self.canvas.winfo_height()
        if canvas_height < 10:  # Not yet rendered
            canvas_height = 80
        
        x = 20
        y = canvas_height // 2
        radius = 18
        ball_spacing = 12
        
        # Only show last 18 balls (3 overs)
        visible_balls = self.balls[-18:]
        
        # Draw "No balls yet" if empty
        if not visible_balls:
            self.canvas.create_text(
                100, y,
                text="No balls recorded yet",
                fill=COLORS['text_secondary'],
                font=FONTS['body'],
                anchor='w'
            )
            return
        
        for i, ball in enumerate(visible_balls):
            # Determine color
            if ball['is_wicket']:
                color = COLORS['wickets']
                text = 'W'
            elif ball['extra_type']:
                color = COLORS['extras']
                text = ball['extra_type'][:2]
            elif ball['runs'] in [4, 6]:
                color = COLORS['runs']
                text = str(ball['runs'])
            else:
                color = COLORS['primary']
                text = str(ball['runs'])
            
            # Draw circle with border for better visibility
            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=color,
                outline=COLORS['border'],
                width=1
            )
            
            # Draw text
            self.canvas.create_text(
                x, y,
                text=text,
                fill='white',
                font=FONTS['button']
            )
            
            x += radius * 2 + ball_spacing
            
            # Add over separator
            if (i + 1) % 6 == 0 and i < len(visible_balls) - 1:
                self.canvas.create_line(
                    x - 4, y - radius - 10,
                    x - 4, y + radius + 10,
                    fill=COLORS['border'],
                    width=2
                )
                x += 18


class LiveIndicator(tk.Frame):
    """Live sync indicator"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['card_bg'], **kwargs)
        
        self.indicator = tk.Label(
            self,
            text="●",
            fg=COLORS['live'],
            bg=COLORS['card_bg'],
            font=('Segoe UI', 14)
        )
        self.indicator.pack(side='left')
        
        self.status_label = tk.Label(
            self,
            text="Live",
            fg=COLORS['text_secondary'],
            bg=COLORS['card_bg'],
            font=FONTS['small']
        )
        self.status_label.pack(side='left', padx=(4, 0))
        
        self.last_update_label = tk.Label(
            self,
            text="",
            fg=COLORS['text_secondary'],
            bg=COLORS['card_bg'],
            font=FONTS['small']
        )
        self.last_update_label.pack(side='left', padx=(8, 0))
        
        self._blink_state = True
    
    def set_live(self, is_live: bool, last_update: str = ""):
        """Update live status"""
        if is_live:
            self.indicator.configure(fg=COLORS['live'])
            self.status_label.configure(text="Live")
        else:
            self.indicator.configure(fg=COLORS['completed'])
            self.status_label.configure(text="Synced")
        
        self.last_update_label.configure(text=last_update)
    
    def set_warning(self, message: str):
        """Show warning state"""
        self.indicator.configure(fg=COLORS['warning'])
        self.status_label.configure(text=message, fg=COLORS['warning'])
    
    def blink(self):
        """Toggle blink state for live indicator"""
        if self._blink_state:
            self.indicator.configure(fg=COLORS['live'])
        else:
            self.indicator.configure(fg=COLORS['background'])
        self._blink_state = not self._blink_state


class MatchCard(tk.Frame):
    """Match card for home screen list"""
    
    def __init__(
        self,
        parent,
        match_id: str,
        team_a: str,
        team_b: str,
        format_type: str,
        score: str,
        overs: str,
        status: str,
        on_view: Optional[Callable] = None,
        on_edit: Optional[Callable] = None,
        is_admin: bool = False,
        **kwargs
    ):
        super().__init__(
            parent,
            bg=COLORS['card_bg'],
            padx=PADDING + 4,
            pady=PADDING,
            **kwargs
        )
        self.configure(
            highlightbackground=COLORS['border'],
            highlightthickness=1
        )
        
        self.match_id = match_id
        
        # Header row with teams and status
        header = tk.Frame(self, bg=COLORS['card_bg'])
        header.pack(fill='x')
        
        teams_label = tk.Label(
            header,
            text=f"{team_a} vs {team_b}",
            font=FONTS['heading'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_primary']
        )
        teams_label.pack(side='left')
        
        status_badge = StatusBadge(header, status=status)
        status_badge.pack(side='right')
        
        # Info row
        info_frame = tk.Frame(self, bg=COLORS['card_bg'])
        info_frame.pack(fill='x', pady=(SPACING // 2, 0))
        
        format_label = tk.Label(
            info_frame,
            text=format_type,
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary']
        )
        format_label.pack(side='left')
        
        if status == "Live" or status == "Completed":
            score_label = tk.Label(
                info_frame,
                text=f"{score} ({overs} ov)",
                font=FONTS['subheading'],
                bg=COLORS['card_bg'],
                fg=COLORS['primary']
            )
            score_label.pack(side='right')
        
        # Action buttons
        actions_frame = tk.Frame(self, bg=COLORS['card_bg'])
        actions_frame.pack(fill='x', pady=(SPACING, 0))
        
        if is_admin and on_edit:
            edit_btn = StyledButton(
                actions_frame,
                text="Edit Match",
                variant='primary',
                command=lambda: on_edit(match_id)
            )
            edit_btn.pack(side='right', padx=(SPACING // 2, 0))
        
        if on_view:
            view_btn = StyledButton(
                actions_frame,
                text="View Match",
                variant='secondary',
                command=lambda: on_view(match_id)
            )
            view_btn.pack(side='right')
