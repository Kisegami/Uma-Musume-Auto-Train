"""
Config Panel with Tabs for PySide6 GUI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QFrame
)
from PySide6.QtCore import Qt

from .styles import COLORS
from .tabs.training_tab import TrainingTab
from .tabs.racing_tab import RacingTab
from .tabs.skill_tab import SkillTab
from .tabs.event_tab import EventTab
from .tabs.mode_tab import ModeTab
from .tabs.advanced_tab import AdvancedTab


class ConfigPanel(QFrame):
    """Configuration panel with tabbed interface"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("card")
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the tabbed config panel"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # Create tabs
        self.training_tab = TrainingTab(self.main_window)
        self.racing_tab = RacingTab(self.main_window)
        self.skill_tab = SkillTab(self.main_window)
        self.event_tab = EventTab(self.main_window)
        self.mode_tab = ModeTab(self.main_window)
        self.advanced_tab = AdvancedTab(self.main_window)
        
        # Add tabs
        self.tab_widget.addTab(self.training_tab, "Training")
        self.tab_widget.addTab(self.racing_tab, "Racing")
        self.tab_widget.addTab(self.skill_tab, "Skills")
        self.tab_widget.addTab(self.event_tab, "Events")
        self.tab_widget.addTab(self.mode_tab, "Mode")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        layout.addWidget(self.tab_widget)
    
    def refresh_config(self):
        """Refresh all tabs with current config"""
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'load_config'):
                tab.load_config()
