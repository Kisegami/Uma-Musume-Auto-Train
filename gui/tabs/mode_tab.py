"""
Mode Tab for PySide6 GUI
Manages restart career and auto-start settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QGroupBox, QGridLayout, QFrame, QScrollArea
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class ModeTab(QScrollArea):
    """Mode/Restart configuration tab""" 
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create mode tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Game Mode
        mode_group = QGroupBox("Game Mode")
        mode_layout = QGridLayout(mode_group)
        mode_layout.setSpacing(12)
        
        mode_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["ura", "aoharu", "grand_live", "project_l'arc"])
        self.mode_combo.currentTextChanged.connect(
            lambda v: self.main_window.update_config_value("mode", v)
        )
        mode_layout.addWidget(self.mode_combo, 0, 1)
        
        layout.addWidget(mode_group)
        
        # Restart Career Group
        restart_group = QGroupBox("Restart Career")
        restart_layout = QGridLayout(restart_group)
        restart_layout.setSpacing(12)
        
        self.restart_enabled = QCheckBox("Enable Career Restart")
        self.restart_enabled.stateChanged.connect(
            lambda v: self._update_config("restart_career", "restart_enabled", v == Qt.CheckState.Checked.value)
        )
        restart_layout.addWidget(self.restart_enabled, 0, 0, 1, 2)
        
        restart_layout.addWidget(QLabel("Restart Times:"), 1, 0)
        self.restart_times = QSpinBox()
        self.restart_times.setRange(0, 100)
        self.restart_times.valueChanged.connect(
            lambda v: self._update_config("restart_career", "restart_times", v)
        )
        restart_layout.addWidget(self.restart_times, 1, 1)
        
        restart_layout.addWidget(QLabel("Total Fans Requirement:"), 2, 0)
        self.fans_req = QSpinBox()
        self.fans_req.setRange(0, 999999999)
        self.fans_req.setSingleStep(10000)
        self.fans_req.valueChanged.connect(
            lambda v: self._update_config("restart_career", "total_fans_requirement", v)
        )
        restart_layout.addWidget(self.fans_req, 2, 1)
        
        layout.addWidget(restart_group)
        
        # Auto Start Career Group
        auto_group = QGroupBox("Auto Start Career")
        auto_layout = QGridLayout(auto_group)
        auto_layout.setSpacing(12)
        
        self.include_guests = QCheckBox("Include Guests (Legacy)")
        self.include_guests.stateChanged.connect(
            lambda v: self._update_config("auto_start_career", "include_guests_legacy", v == Qt.CheckState.Checked.value)
        )
        auto_layout.addWidget(self.include_guests, 0, 0, 1, 2)
        
        auto_layout.addWidget(QLabel("Support Specialty:"), 1, 0)
        self.specialty_combo = QComboBox()
        self.specialty_combo.addItems(["SPD", "STA", "PWR", "GUTS", "WIT"])
        self.specialty_combo.currentTextChanged.connect(
            lambda v: self._update_config("auto_start_career", "support_speciality", v)
        )
        auto_layout.addWidget(self.specialty_combo, 1, 1)
        
        auto_layout.addWidget(QLabel("Support Rarity:"), 2, 0)
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["SSR", "SR", "R"])
        self.rarity_combo.currentTextChanged.connect(
            lambda v: self._update_config("auto_start_career", "support_rarity", v)
        )
        auto_layout.addWidget(self.rarity_combo, 2, 1)
        
        self.auto_charge = QCheckBox("Restore TP using TP Bottle")
        self.auto_charge.stateChanged.connect(self._on_auto_charge_changed)
        auto_layout.addWidget(self.auto_charge, 3, 0, 1, 2)
        
        self.auto_charge_carats = QCheckBox("Use Carats to restore TP (needs \"Restore TP using TP Bottle\")")
        self.auto_charge_carats.stateChanged.connect(
            lambda v: self._update_config("auto_start_career", "auto_charge_tp_carats", v == Qt.CheckState.Checked.value)
        )
        self.auto_charge_carats.setEnabled(False) # Default to false until config is loaded
        auto_layout.addWidget(self.auto_charge_carats, 4, 0, 1, 2)
        
        layout.addWidget(auto_group)
        
        # Dating Group
        dating_group = QGroupBox("Dating")
        dating_layout = QVBoxLayout(dating_group)
        
        self.use_dating = QCheckBox("Use Dating Instead of Rest")
        self.use_dating.stateChanged.connect(
            lambda v: self._update_config("dating", "use_dating_instead_of_rest", v == Qt.CheckState.Checked.value)
        )
        dating_layout.addWidget(self.use_dating)
        
        layout.addWidget(dating_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        # Mode
        self.mode_combo.setCurrentText(config.get("mode", "ura"))
        
        # Restart
        restart = config.get("restart_career", {})
        self.restart_enabled.setChecked(restart.get("restart_enabled", False))
        self.restart_times.setValue(restart.get("restart_times", 2))
        self.fans_req.setValue(restart.get("total_fans_requirement", 0))
        
        # Auto start
        auto_start = config.get("auto_start_career", {})
        self.include_guests.setChecked(auto_start.get("include_guests_legacy", False))
        self.specialty_combo.setCurrentText(auto_start.get("support_speciality", "STA"))
        self.rarity_combo.setCurrentText(auto_start.get("support_rarity", "SSR"))
        self.auto_charge.setChecked(auto_start.get("auto_charge_tp", True))
        self.auto_charge_carats.setChecked(auto_start.get("auto_charge_tp_carats", False))
        
        # Initial state for Carats checkbox based on TP bottle checkbox
        self.auto_charge_carats.setEnabled(self.auto_charge.isChecked())
        
        # Dating
        dating = config.get("dating", {})
        self.use_dating.setChecked(dating.get("use_dating_instead_of_rest", False))
    
    def _update_config(self, parent, key, value):
        """Update config value"""
        self.main_window.update_nested_config_value(parent, key, value)
        
    def _on_auto_charge_changed(self, state):
        """Handle auto charge config value and dependent checkboxes"""
        is_checked = state == Qt.CheckState.Checked.value
        self._update_config("auto_start_career", "auto_charge_tp", is_checked)
        self.auto_charge_carats.setEnabled(is_checked)
        if not is_checked:
            self.auto_charge_carats.setChecked(False)
