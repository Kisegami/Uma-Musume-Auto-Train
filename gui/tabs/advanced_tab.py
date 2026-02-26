"""
Advanced Tab for PySide6 GUI
Manages debug, update, capture, and emulator settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QGridLayout, 
    QFrame, QScrollArea, QLineEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class AdvancedTab(QScrollArea):
    """Advanced configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create advanced tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Capture Settings
        capture_group = QGroupBox("Capture Settings")
        capture_layout = QGridLayout(capture_group)
        capture_layout.setSpacing(12)
        
        capture_layout.addWidget(QLabel("Capture Method:"), 0, 0)
        self.capture_combo = QComboBox()
        self.capture_combo.addItems(["auto", "adb", "nemu_ipc", "ldopengl"])
        self.capture_combo.currentTextChanged.connect(
            lambda v: (self.main_window.update_config_value("capture_method", v), self.main_window.save_config())
        )
        capture_layout.addWidget(self.capture_combo, 0, 1)
        
        capture_layout.addWidget(QLabel("Emulator Type:"), 1, 0)
        self.emulator_combo = QComboBox()
        self.emulator_combo.addItem("")  # Empty = auto-detect
        emulator_types = getattr(self.main_window, 'detected_emulator_types', [])
        self.emulator_combo.addItems(emulator_types)
        self.emulator_combo.currentTextChanged.connect(
            lambda v: (self.main_window.update_config_value("emulator_type", v), self.main_window.save_config())
        )
        capture_layout.addWidget(self.emulator_combo, 1, 1)
        
        layout.addWidget(capture_group)
        
        # ADB Settings
        adb_group = QGroupBox("ADB Settings")
        adb_layout = QGridLayout(adb_group)
        adb_layout.setSpacing(12)
        
        adb_layout.addWidget(QLabel("Device Address:"), 0, 0)
        self.device_addr = QLineEdit()
        self.device_addr.setPlaceholderText("auto or IP:port")
        self.device_addr.textChanged.connect(
            lambda v: self._update_config("adb_config", "device_address", v)
        )
        adb_layout.addWidget(self.device_addr, 0, 1)
        
        adb_layout.addWidget(QLabel("ADB Path:"), 1, 0)
        self.adb_path = QLineEdit()
        self.adb_path.setPlaceholderText("adb")
        self.adb_path.textChanged.connect(
            lambda v: self._update_config("adb_config", "adb_path", v)
        )
        adb_layout.addWidget(self.adb_path, 1, 1)
        
        adb_layout.addWidget(QLabel("Screenshot Timeout:"), 2, 0)
        self.screenshot_timeout = QSpinBox()
        self.screenshot_timeout.setRange(1, 60)
        self.screenshot_timeout.valueChanged.connect(
            lambda v: self._update_config("adb_config", "screenshot_timeout", v)
        )
        adb_layout.addWidget(self.screenshot_timeout, 2, 1)
        
        adb_layout.addWidget(QLabel("Input Delay:"), 3, 0)
        self.input_delay = QDoubleSpinBox()
        self.input_delay.setRange(0, 5)
        self.input_delay.setDecimals(2)
        self.input_delay.setSingleStep(0.1)
        self.input_delay.valueChanged.connect(
            lambda v: self._update_config("adb_config", "input_delay", v)
        )
        adb_layout.addWidget(self.input_delay, 3, 1)
        
        layout.addWidget(adb_group)
        
        # Debug Settings
        debug_group = QGroupBox("Debug Settings")
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setSpacing(12)
        
        self.debug_mode = QCheckBox("Debug Mode")
        self.debug_mode.stateChanged.connect(
            lambda v: (self.main_window.update_config_value("debug_mode", v == Qt.CheckState.Checked.value), self.main_window.save_config())
        )
        debug_layout.addWidget(self.debug_mode)
        
        self.stop_on_failure = QCheckBox("Stop on Event Detection Failure")
        self.stop_on_failure.stateChanged.connect(
            lambda v: (self.main_window.update_config_value("stop_on_event_detection_failure", v == Qt.CheckState.Checked.value), self.main_window.save_config())
        )
        debug_layout.addWidget(self.stop_on_failure)
        
        layout.addWidget(debug_group)
        
        # Update Settings
        update_group = QGroupBox("Update Settings")
        update_layout = QGridLayout(update_group)
        update_layout.setSpacing(12)
        
        self.auto_update = QCheckBox("Auto Update")
        self.auto_update.stateChanged.connect(
            lambda v: self._update_config("update", "auto_update", v == Qt.CheckState.Checked.value)
        )
        update_layout.addWidget(self.auto_update, 0, 0, 1, 2)
        
        self.install_deps = QCheckBox("Install Dependencies")
        self.install_deps.stateChanged.connect(
            lambda v: self._update_config("update", "install_dependencies", v == Qt.CheckState.Checked.value)
        )
        update_layout.addWidget(self.install_deps, 1, 0, 1, 2)
        
        update_layout.addWidget(QLabel("Branch:"), 2, 0)
        self.branch_combo = QComboBox()
        self.branch_combo.addItems(["main", "dev", "stable"])
        self.branch_combo.setEditable(True)
        self.branch_combo.currentTextChanged.connect(
            lambda v: self._update_config("update", "branch", v)
        )
        update_layout.addWidget(self.branch_combo, 2, 1)
        
        layout.addWidget(update_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        # Capture
        self.capture_combo.setCurrentText(config.get("capture_method", "auto"))
        self.emulator_combo.setCurrentText(config.get("emulator_type", ""))
        
        # ADB
        adb = config.get("adb_config", {})
        self.device_addr.setText(adb.get("device_address", "auto"))
        self.adb_path.setText(adb.get("adb_path", "adb"))
        self.screenshot_timeout.setValue(adb.get("screenshot_timeout", 5))
        self.input_delay.setValue(adb.get("input_delay", 0.5))
        
        # Debug
        self.debug_mode.setChecked(config.get("debug_mode", False))
        self.stop_on_failure.setChecked(config.get("stop_on_event_detection_failure", False))
        
        # Update
        update = config.get("update", {})
        self.auto_update.setChecked(update.get("auto_update", True))
        self.install_deps.setChecked(update.get("install_dependencies", True))
        self.branch_combo.setCurrentText(update.get("branch", "main"))
    
    def _update_config(self, parent, key, value):
        """Update config value"""
        self.main_window.update_nested_config_value(parent, key, value)
        self.main_window.save_config()
