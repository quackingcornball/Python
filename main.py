"""
Live Cricket Scoring System
Main Application Entry Point
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from config import WINDOW_WIDTH, WINDOW_HEIGHT, MIN_WIDTH, MIN_HEIGHT, WINDOW_TITLE, COLORS, FONTS, PADDING, SPACING, DATA_FILE
from core.data_manager import DataManager
from ui.home_screen import HomeScreen
from ui.admin_dashboard import AdminDashboard
from ui.match_view import MatchView
from ui.components import StyledButton, CardFrame


class CricketScoringApp:
    """Main application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.configure(bg=COLORS['background'])
        
        # Set minimum window size
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        
        # Fit window to screen
        self._fit_to_screen()
        
        # Initialize data manager
        self.data_manager = DataManager(DATA_FILE)
        
        # User mode
        self.is_admin = False
        
        # Current frame
        self.current_frame: Optional[tk.Frame] = None
        
        # Configure styles
        self._configure_styles()
        
        # Show startup screen
        self._show_startup_screen()
    
    def _fit_to_screen(self):
        """Fit window to screen size with proper margins"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (85% of screen, but respect min/max)
        width = min(WINDOW_WIDTH, int(screen_width * 0.85))
        height = min(WINDOW_HEIGHT, int(screen_height * 0.85))
        
        # Ensure minimum size
        width = max(width, MIN_WIDTH)
        height = max(height, MIN_HEIGHT)
        
        # Center the window on screen
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Ensure window is not positioned off-screen
        y = max(0, y - 30)  # Account for title bar
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure Treeview
        style.configure(
            "Treeview",
            background=COLORS['card_bg'],
            foreground=COLORS['text_primary'],
            fieldbackground=COLORS['card_bg'],
            font=FONTS['body']
        )
        style.configure(
            "Treeview.Heading",
            font=FONTS['subheading'],
            background=COLORS['background'],
            foreground=COLORS['text_primary']
        )
        
        # Configure Scrollbar
        style.configure(
            "TScrollbar",
            background=COLORS['background'],
            troughcolor=COLORS['card_bg']
        )
        
        # Configure Combobox
        style.configure(
            "TCombobox",
            font=FONTS['body']
        )
    
    def _clear_frame(self):
        """Clear the current frame"""
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
    
    def _show_startup_screen(self):
        """Show the startup/role selection screen"""
        self._clear_frame()
        
        self.current_frame = tk.Frame(self.root, bg=COLORS['background'])
        self.current_frame.pack(fill='both', expand=True)
        
        # Center container
        container = tk.Frame(self.current_frame, bg=COLORS['background'])
        container.place(relx=0.5, rely=0.5, anchor='center')
        
        # App title
        title_label = tk.Label(
            container,
            text="Live Cricket Scoring System",
            font=FONTS['title'],
            bg=COLORS['background'],
            fg=COLORS['text_primary']
        )
        title_label.pack(pady=(0, SPACING + 4))
        
        subtitle_label = tk.Label(
            container,
            text="ESPN-Style Cricket Scorer",
            font=FONTS['subheading'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary']
        )
        subtitle_label.pack(pady=(0, SPACING * 3))
        
        # Role selection card
        role_card = CardFrame(container, title="Select Your Role")
        role_card.pack(padx=PADDING * 2, ipadx=PADDING, ipady=SPACING // 2)
        
        # Description
        desc_frame = tk.Frame(role_card, bg=COLORS['card_bg'])
        desc_frame.pack(fill='x', pady=(SPACING // 2, SPACING * 2))
        
        admin_desc = tk.Label(
            desc_frame,
            text="Admin (Scorer): Create, edit, and delete matches, update live scores",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary'],
            wraplength=420
        )
        admin_desc.pack(anchor='w')
        
        viewer_desc = tk.Label(
            desc_frame,
            text="Viewer (Audience): View live matches in real-time (read-only)",
            font=FONTS['body'],
            bg=COLORS['card_bg'],
            fg=COLORS['text_secondary'],
            wraplength=420
        )
        viewer_desc.pack(anchor='w', pady=(SPACING, 0))
        
        # Buttons
        btn_frame = tk.Frame(role_card, bg=COLORS['card_bg'])
        btn_frame.pack(fill='x', pady=(SPACING, SPACING // 2))
        
        admin_btn = StyledButton(
            btn_frame,
            text="Enter as Admin",
            variant='primary',
            command=self._enter_as_admin
        )
        admin_btn.pack(side='left', expand=True, fill='x', padx=(0, SPACING // 2), ipady=4)
        
        viewer_btn = StyledButton(
            btn_frame,
            text="Enter as Viewer",
            variant='secondary',
            command=self._enter_as_viewer
        )
        viewer_btn.pack(side='left', expand=True, fill='x', padx=(SPACING // 2, 0), ipady=4)
        
        # Footer
        footer_label = tk.Label(
            container,
            text="Built with Python + Tkinter",
            font=FONTS['body'],
            bg=COLORS['background'],
            fg=COLORS['text_secondary']
        )
        footer_label.pack(pady=(SPACING * 2 + 4, 0))
    
    def _enter_as_admin(self):
        """Enter as admin user"""
        self.is_admin = True
        self._show_home_screen()
    
    def _enter_as_viewer(self):
        """Enter as viewer user"""
        self.is_admin = False
        self._show_home_screen()
    
    def _show_home_screen(self):
        """Show the home screen with match list"""
        self._clear_frame()
        
        self.current_frame = HomeScreen(
            self.root,
            data_manager=self.data_manager,
            is_admin=self.is_admin,
            on_view_match=self._view_match,
            on_edit_match=self._edit_match if self.is_admin else None,
            on_create_match=self._show_admin_dashboard if self.is_admin else None
        )
        self.current_frame.pack(fill='both', expand=True)
    
    def _show_admin_dashboard(self):
        """Show the admin dashboard"""
        self._clear_frame()
        
        self.current_frame = AdminDashboard(
            self.root,
            data_manager=self.data_manager,
            on_back=self._show_home_screen,
            on_edit_match=self._edit_match
        )
        self.current_frame.pack(fill='both', expand=True)
    
    def _view_match(self, match_id: str):
        """View a match (viewer mode)"""
        self._clear_frame()
        
        self.current_frame = MatchView(
            self.root,
            match_id=match_id,
            data_manager=self.data_manager,
            is_admin=False,
            on_back=self._show_home_screen
        )
        self.current_frame.pack(fill='both', expand=True)
    
    def _edit_match(self, match_id: str):
        """Edit a match (admin mode)"""
        self._clear_frame()
        
        self.current_frame = MatchView(
            self.root,
            match_id=match_id,
            data_manager=self.data_manager,
            is_admin=True,
            on_back=self._show_home_screen
        )
        self.current_frame.pack(fill='both', expand=True)
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = CricketScoringApp()
    app.run()


if __name__ == "__main__":
    main()
