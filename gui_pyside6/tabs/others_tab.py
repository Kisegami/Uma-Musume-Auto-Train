"""
Others Tab for PySide6 GUI
Contains debug and miscellaneous settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QGroupBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class OthersTab(QScrollArea):
    """Others/Debug configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create others tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Debug Settings
        debug_group = QGroupBox("Debug Settings")
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setSpacing(12)
        
        self.debug_mode = QCheckBox("Debug Mode")
        self.debug_mode.stateChanged.connect(
            lambda v: self.main_window.update_config_value("debug_mode", v == Qt.Checked)
        )
        debug_layout.addWidget(self.debug_mode)
        
        self.stop_on_failure = QCheckBox("Stop Bot on Event Detection Failure")
        self.stop_on_failure.stateChanged.connect(
            lambda v: self.main_window.update_config_value("stop_on_event_detection_failure", v == Qt.Checked)
        )
        debug_layout.addWidget(self.stop_on_failure)
        
        desc = QLabel("When enabled, bot stops if event name cannot be detected.\nWhen disabled, bot chooses top option as fallback.")
        desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        debug_layout.addWidget(desc)
        
        layout.addWidget(debug_group)
        
        # Dating Settings
        dating_group = QGroupBox("Dating")
        dating_layout = QVBoxLayout(dating_group)
        
        self.use_dating = QCheckBox("Use Dating Instead of Rest")
        self.use_dating.stateChanged.connect(
            lambda v: self._update_dating("use_dating_instead_of_rest", v == Qt.Checked)
        )
        dating_layout.addWidget(self.use_dating)
        
        layout.addWidget(dating_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        self.debug_mode.setChecked(config.get("debug_mode", False))
        self.stop_on_failure.setChecked(config.get("stop_on_event_detection_failure", False))
        
        dating = config.get("dating", {})
        self.use_dating.setChecked(dating.get("use_dating_instead_of_rest", False))
    
    def _update_dating(self, key, value):
        self.main_window.update_nested_config_value("dating", key, value)
