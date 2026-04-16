"""
Configuration settings for Cricket Scoring System
"""

# Window Settings
WINDOW_WIDTH = 1280  # Default width (will adapt to screen)
WINDOW_HEIGHT = 720  # Default height (will adapt to screen)
MIN_WIDTH = 1024     # Minimum window width
MIN_HEIGHT = 640     # Minimum window height
WINDOW_TITLE = "Live Cricket Scoring System"

# Layout Settings
PADDING = 24
SPACING = 20

# Colors (ESPN-inspired)
COLORS = {
    "primary": "#1a73e8",      # Blue - primary
    "secondary": "#5f6368",     # Gray - secondary text
    "background": "#f8f9fa",    # Light background
    "card_bg": "#ffffff",       # White card background
    "runs": "#34a853",          # Green - runs
    "wickets": "#ea4335",       # Red - wickets
    "extras": "#fbbc04",        # Orange/Yellow - extras
    "live": "#34a853",          # Green - live status
    "completed": "#5f6368",     # Gray - completed
    "upcoming": "#1a73e8",      # Blue - upcoming
    "text_primary": "#202124",  # Dark text
    "text_secondary": "#5f6368", # Secondary text
    "border": "#dadce0",        # Border color
    "warning": "#ff6b6b",       # Warning color
}

# Fonts
FONTS = {
    "title": ("Segoe UI", 28, "bold"),
    "heading": ("Segoe UI", 20, "bold"),
    "subheading": ("Segoe UI", 15, "bold"),
    "body": ("Segoe UI", 13),
    "small": ("Segoe UI", 11),
    "score": ("Segoe UI", 42, "bold"),
    "button": ("Segoe UI", 12, "bold"),
}

# Match Formats
FORMATS = {
    "T20": {"overs": 20, "innings": 2},
    "ODI": {"overs": 50, "innings": 2},
    "TEST": {"overs": None, "innings": 4},  # None = unlimited
}

# Data File Path
DATA_FILE = "data/matches.json"

# Sync Settings
SYNC_INTERVAL = 1000  # milliseconds (1 second)
STALE_THRESHOLD = 5000  # milliseconds (5 seconds) - show warning if delay exceeds this

# Run Options
RUN_OPTIONS = [0, 1, 2, 3, 4, 6]
EXTRA_OPTIONS = ["WD", "NB", "BYE", "LB"]
