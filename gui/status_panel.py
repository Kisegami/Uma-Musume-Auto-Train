"""
Status Panel for PySide6 GUI
Compact training status display.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QProgressBar, QGridLayout
)
from PySide6.QtCore import Qt

from .styles import COLORS


STAT_KEYS = ("spd", "sta", "pwr", "guts", "wit")
MODE_VISUAL_STAT_CAPS = {
    "trackblazer": {"spd": 1400, "sta": 2100, "pwr": 1400, "guts": 1400, "wit": 1700},
    "unity": {"spd": 1500, "sta": 1500, "pwr": 1500, "guts": 1500, "wit": 2000},
    "ura": {"spd": 1600, "sta": 1600, "pwr": 1600, "guts": 1600, "wit": 1600},
}


class StatusPanel(QFrame):
    """Compact status panel"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("card")
        self.setMaximumHeight(200)
        self._current_max_stats = {}
        
        self._create_ui()
    
    def _create_ui(self):
        """Create status UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Title row
        header = QHBoxLayout()
        title = QLabel("Status")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # Info grid: Year (wider), Energy, Mood (Turn removed)
        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        
        # Mood colors mapping
        self.mood_colors = {
            "GREAT": "#ec4899",    # Pink
            "GOOD": "#f97316",     # Orange
            "NORMAL": "#eab308",   # Yellow
            "BAD": "#3b82f6",      # Blue
            "AWFUL": "#a855f7"     # Purple
        }
        
        # Year takes 2 columns for more space
        self.year_val = self._add_info_item(info_grid, "Year", "Unknown Year", 0, 0, colspan=2)
        self.energy_val = self._add_info_item(info_grid, "Energy", "Unknown", 0, 2)
        self.mood_val = self._add_info_item(info_grid, "Mood", "GREAT", 0, 3)
        
        # Initialize mood with pink color for GREAT
        self.mood_val.setStyleSheet(f"color: {self.mood_colors['GREAT']}; font-size: 14px; font-weight: bold;")
        
        layout.addLayout(info_grid)
        
        # Stat bars (compact)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)
        
        self.stat_bars = {}
        stats = [("spd", "SPD", "#3b82f6"), ("sta", "STA", "#ef4444"),
                 ("pwr", "PWR", "#eab308"), ("guts", "GUT", "#ec4899"),
                 ("wit", "WIT", "#22c55e")]
        
        for i, (key, label, color) in enumerate(stats):
            lbl = QLabel(label)
            lbl.setFixedWidth(35)
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            stats_grid.addWidget(lbl, i, 0)
            
            bar = QProgressBar()
            bar.setRange(0, self._get_default_visual_cap(key))
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat("%v")
            bar.setFixedHeight(16)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: {COLORS['bg_input']}; border: none; border-radius: 3px; font-size: 10px; }}
                QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}
            """)
            stats_grid.addWidget(bar, i, 1)
            self.stat_bars[key] = bar
        
        layout.addLayout(stats_grid)

    def _get_default_visual_cap(self, stat_key):
        config = self.main_window.get_config() if hasattr(self.main_window, "get_config") else {}
        mode = config.get("mode", "ura")
        return MODE_VISUAL_STAT_CAPS.get(mode, MODE_VISUAL_STAT_CAPS["ura"]).get(stat_key, 1600)

    def _normalize_max_stats(self, max_stats):
        if not isinstance(max_stats, dict):
            return {}

        normalized = {}
        for key in STAT_KEYS:
            try:
                value = int(max_stats.get(key, 0))
            except (TypeError, ValueError):
                continue
            if value > 0:
                normalized[key] = value
        return normalized

    def _update_stat_bar_ranges(self, max_stats=None):
        normalized_max_stats = self._normalize_max_stats(max_stats)
        if normalized_max_stats:
            self._current_max_stats = normalized_max_stats
        else:
            config = self.main_window.get_config() if hasattr(self.main_window, "get_config") else {}
            if not config.get("api", {}).get("enabled", False):
                self._current_max_stats = {}

        for key, bar in self.stat_bars.items():
            visual_cap = self._current_max_stats.get(key) or self._get_default_visual_cap(key)
            if bar.maximum() != visual_cap:
                bar.setRange(0, visual_cap)
    
    def _add_info_item(self, grid, label, value, row, col, colspan=1):
        widget = QWidget()
        vl = QVBoxLayout(widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        vl.addWidget(lbl)
        
        val = QLabel(value)
        val.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        vl.addWidget(val)
        
        grid.addWidget(widget, row, col, 1, colspan)
        return val
    
    def update_status(self, year, energy, turn, mood, goal_met, stats, max_stats=None):
        """Update all values"""
        self._update_stat_bar_ranges(max_stats)
        self.year_val.setText(str(year))
        self.energy_val.setText(self._format_energy(energy))
        
        # Update mood with color
        mood_upper = mood.upper()
        self.mood_val.setText(mood_upper)
        mood_color = self.mood_colors.get(mood_upper, COLORS['text_primary'])
        self.mood_val.setStyleSheet(f"color: {mood_color}; font-size: 14px; font-weight: bold;")
        
        if stats:
            for key, val in stats.items():
                if key in self.stat_bars:
                    self.stat_bars[key].setValue(int(val))

    @staticmethod
    def _format_energy(energy):
        """Format OCR percentage or API current/max energy for display."""
        if isinstance(energy, dict):
            current = energy.get("current")
            maximum = energy.get("max")
            if current is not None and maximum is not None:
                return f"{current}/{maximum}"

        if isinstance(energy, str):
            return energy.strip() or "Unknown"

        if energy is None:
            return "Unknown"

        return f"{energy}%"
    
    def update_from_bot_data(self, status):
        """Update from bot controller data format (compatibility method)"""
        year = status.get('year', 'Unknown Year')
        energy = status.get('energy')
        turn = status.get('turn', 'Unknown')
        mood = status.get('mood', 'Unknown')
        goal_met = status.get('goal_met', False)
        stats = status.get('stats', {})
        max_stats = status.get('max_stats', {})
        
        self.update_status(year, energy, turn, mood, goal_met, stats, max_stats=max_stats)
