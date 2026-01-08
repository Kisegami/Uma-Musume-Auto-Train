"""
Update Tab for PySide6 GUI
Handles automatic update settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class UpdateTab(QScrollArea):
    """Update configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create update tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Update Settings
        update_group = QGroupBox("Update Settings")
        update_layout = QGridLayout(update_group)
        update_layout.setSpacing(12)
        
        self.auto_update = QCheckBox("Auto Update")
        self.auto_update.stateChanged.connect(
            lambda v: self._update("update", "auto_update", v == Qt.Checked)
        )
        update_layout.addWidget(self.auto_update, 0, 0, 1, 2)
        
        self.install_deps = QCheckBox("Install Dependencies")
        self.install_deps.stateChanged.connect(
            lambda v: self._update("update", "install_dependencies", v == Qt.Checked)
        )
        update_layout.addWidget(self.install_deps, 1, 0, 1, 2)
        
        update_layout.addWidget(QLabel("Branch:"), 2, 0)
        self.branch_combo = QComboBox()
        self.branch_combo.addItems(["main", "dev", "stable"])
        self.branch_combo.setEditable(True)
        self.branch_combo.currentTextChanged.connect(
            lambda v: self._update("update", "branch", v)
        )
        update_layout.addWidget(self.branch_combo, 2, 1)
        
        layout.addWidget(update_group)
        
        # Manual Update
        manual_group = QGroupBox("Manual Update")
        manual_layout = QVBoxLayout(manual_group)
        manual_layout.setSpacing(12)
        
        self.status_label = QLabel("Click 'Check for Updates' to check for available updates.")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_label.setWordWrap(True)
        manual_layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        
        check_btn = QPushButton("Check for Updates")
        check_btn.clicked.connect(self._check_updates)
        btn_layout.addWidget(check_btn)
        
        update_btn = QPushButton("Update Now")
        update_btn.setObjectName("primary")
        update_btn.clicked.connect(self._update_now)
        btn_layout.addWidget(update_btn)
        
        btn_layout.addStretch()
        manual_layout.addLayout(btn_layout)
        
        layout.addWidget(manual_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        update = config.get("update", {})
        self.auto_update.setChecked(update.get("auto_update", True))
        self.install_deps.setChecked(update.get("install_dependencies", True))
        self.branch_combo.setCurrentText(update.get("branch", "main"))
    
    def _update(self, parent, key, value):
        self.main_window.update_nested_config_value(parent, key, value)
    
    def _check_updates(self):
        """Check for updates"""
        self.status_label.setText("Checking for updates...")
        self.main_window.add_log("Checking for updates...")
        # TODO: Implement actual update check
        self.status_label.setText("Update check not yet implemented.")
    
    def _update_now(self):
        """Update now"""
        self.status_label.setText("Update not yet implemented.")
        self.main_window.add_log("Update functionality not yet implemented.")
