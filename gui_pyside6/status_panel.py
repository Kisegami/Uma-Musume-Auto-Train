"""
Status Panel for PySide6 GUI
Compact training status display.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QProgressBar, QGridLayout
)
from PySide6.QtCore import Qt

from .styles import COLORS


class StatusPanel(QFrame):
    """Compact status panel"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("card")
        self.setMaximumHeight(200)
        
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
        
        # Info grid: Year, Turn, Energy, Mood
        info_grid = QGridLayout()
        info_grid.setSpacing(16)
        
        self.year_val = self._add_info_item(info_grid, "Year", "1", 0, 0)
        self.turn_val = self._add_info_item(info_grid, "Turn", "1/78", 0, 1)
        self.energy_val = self._add_info_item(info_grid, "Energy", "100", 0, 2)
        self.mood_val = self._add_info_item(info_grid, "Mood", "GREAT", 0, 3)
        
        layout.addLayout(info_grid)
        
        # Stat bars (compact)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)
        
        self.stat_bars = {}
        stats = [("spd", "SPD", COLORS['accent_blue']), ("sta", "STA", COLORS['accent_green']),
                 ("pwr", "PWR", COLORS['accent_red']), ("guts", "GUT", COLORS['accent_orange']),
                 ("wit", "WIT", COLORS['accent_primary'])]
        
        for i, (key, label, color) in enumerate(stats):
            lbl = QLabel(label)
            lbl.setFixedWidth(35)
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            stats_grid.addWidget(lbl, i, 0)
            
            bar = QProgressBar()
            bar.setRange(0, 1200)
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
    
    def _add_info_item(self, grid, label, value, row, col):
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
        
        grid.addWidget(widget, row, col)
        return val
    
    def update_status(self, year, energy, turn, mood, goal_met, stats):
        """Update all values"""
        self.year_val.setText(str(year))
        self.turn_val.setText(f"{turn}/78")
        self.energy_val.setText(str(energy))
        self.mood_val.setText(mood)
        
        if stats:
            for key, val in stats.items():
                if key in self.stat_bars:
                    self.stat_bars[key].setValue(int(val))
