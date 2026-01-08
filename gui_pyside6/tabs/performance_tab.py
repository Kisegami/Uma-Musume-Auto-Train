"""
Performance Tab for PySide6 GUI
Contains screenshot capture method settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class PerformanceTab(QScrollArea):
    """Performance configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create performance tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Capture Settings
        capture_group = QGroupBox("Screenshot Capture Settings")
        capture_layout = QGridLayout(capture_group)
        capture_layout.setSpacing(12)
        
        capture_layout.addWidget(QLabel("Capture Method:"), 0, 0)
        self.capture_combo = QComboBox()
        self.capture_combo.addItems(["auto", "adb", "nemu_ipc", "ldopengl"])
        self.capture_combo.currentTextChanged.connect(
            lambda v: self.main_window.update_config_value("capture_method", v)
        )
        capture_layout.addWidget(self.capture_combo, 0, 1)
        
        capture_layout.addWidget(QLabel("Screenshot Timeout:"), 1, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.valueChanged.connect(
            lambda v: self._update_adb("screenshot_timeout", v)
        )
        capture_layout.addWidget(self.timeout_spin, 1, 1)
        
        capture_layout.addWidget(QLabel("Input Delay:"), 2, 0)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 3)
        self.delay_spin.setDecimals(2)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.valueChanged.connect(
            lambda v: self._update_adb("input_delay", v)
        )
        capture_layout.addWidget(self.delay_spin, 2, 1)
        
        layout.addWidget(capture_group)
        
        # NEMU IPC Settings
        nemu_group = QGroupBox("MuMu Player Settings")
        nemu_layout = QGridLayout(nemu_group)
        nemu_layout.setSpacing(12)
        
        nemu_layout.addWidget(QLabel("NEMU Folder:"), 0, 0)
        self.nemu_folder = QLineEdit()
        self.nemu_folder.textChanged.connect(
            lambda v: self._update_nemu("nemu_folder", v)
        )
        nemu_layout.addWidget(self.nemu_folder, 0, 1)
        
        nemu_layout.addWidget(QLabel("Instance ID:"), 1, 0)
        self.nemu_instance = QSpinBox()
        self.nemu_instance.setRange(0, 10)
        self.nemu_instance.valueChanged.connect(
            lambda v: self._update_nemu("instance_id", v)
        )
        nemu_layout.addWidget(self.nemu_instance, 1, 1)
        
        layout.addWidget(nemu_group)
        
        # LDPlayer Settings
        ld_group = QGroupBox("LDPlayer Settings")
        ld_layout = QGridLayout(ld_group)
        ld_layout.setSpacing(12)
        
        ld_layout.addWidget(QLabel("LD Folder:"), 0, 0)
        self.ld_folder = QLineEdit()
        self.ld_folder.textChanged.connect(
            lambda v: self._update_ld("ld_folder", v)
        )
        ld_layout.addWidget(self.ld_folder, 0, 1)
        
        ld_layout.addWidget(QLabel("Instance ID:"), 1, 0)
        self.ld_instance = QSpinBox()
        self.ld_instance.setRange(0, 10)
        self.ld_instance.valueChanged.connect(
            lambda v: self._update_ld("instance_id", v)
        )
        ld_layout.addWidget(self.ld_instance, 1, 1)
        
        layout.addWidget(ld_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        self.capture_combo.setCurrentText(config.get("capture_method", "auto"))
        
        adb = config.get("adb_config", {})
        self.timeout_spin.setValue(adb.get("screenshot_timeout", 5))
        self.delay_spin.setValue(adb.get("input_delay", 0.5))
        
        nemu = config.get("nemu_ipc_config", {})
        self.nemu_folder.setText(nemu.get("nemu_folder", ""))
        self.nemu_instance.setValue(nemu.get("instance_id", 0))
        
        ld = config.get("ldopengl_config", {})
        self.ld_folder.setText(ld.get("ld_folder", ""))
        self.ld_instance.setValue(ld.get("instance_id", 0))
    
    def _update_adb(self, key, value):
        self.main_window.update_nested_config_value("adb_config", key, value)
    
    def _update_nemu(self, key, value):
        self.main_window.update_nested_config_value("nemu_ipc_config", key, value)
    
    def _update_ld(self, key, value):
        self.main_window.update_nested_config_value("ldopengl_config", key, value)
