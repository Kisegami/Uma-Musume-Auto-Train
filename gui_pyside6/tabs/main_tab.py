"""
Main Tab for PySide6 GUI
Contains ADB configuration and mode settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QGroupBox, QGridLayout, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class MainTab(QScrollArea):
    """Main configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create main tab UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Mode Configuration
        mode_group = QGroupBox("Mode Configuration")
        mode_layout = QGridLayout(mode_group)
        mode_layout.setSpacing(12)
        
        mode_layout.addWidget(QLabel("Game Mode:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["URA Finale", "Unity Cup"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        mode_layout.addWidget(self.mode_combo, 0, 1)
        
        layout.addWidget(mode_group)
        
        # ADB Configuration
        adb_group = QGroupBox("ADB Configuration")
        adb_layout = QGridLayout(adb_group)
        adb_layout.setSpacing(12)
        
        # Emulator Type
        adb_layout.addWidget(QLabel("Device/Emulator:"), 0, 0)
        self.emulator_combo = QComboBox()
        emulator_types = getattr(self.main_window, 'detected_emulator_types', [])
        self.emulator_combo.addItem("")
        self.emulator_combo.addItems(emulator_types)
        self.emulator_combo.addItem("Phone")
        self.emulator_combo.addItem("Other Emulator")
        self.emulator_combo.currentTextChanged.connect(self._on_emulator_change)
        adb_layout.addWidget(self.emulator_combo, 0, 1)
        
        # Device Address
        adb_layout.addWidget(QLabel("Device Address:"), 1, 0)
        self.device_addr = QLineEdit()
        self.device_addr.setPlaceholderText("127.0.0.1:7555 or auto")
        self.device_addr.textChanged.connect(
            lambda v: self._update_adb_config("device_address", v)
        )
        adb_layout.addWidget(self.device_addr, 1, 1)
        
        # ADB Path
        adb_layout.addWidget(QLabel("ADB Path:"), 2, 0)
        self.adb_path = QLineEdit()
        self.adb_path.setPlaceholderText("adb")
        self.adb_path.textChanged.connect(
            lambda v: self._update_adb_config("adb_path", v)
        )
        adb_layout.addWidget(self.adb_path, 2, 1)
        
        layout.addWidget(adb_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        self._loading = True
        config = self.main_window.get_config()
        
        # Mode
        self.mode_combo.blockSignals(True)
        mode = config.get("mode", "ura")
        mode_display = {"ura": "URA Finale", "unity": "Unity Cup"}.get(mode, "URA Finale")
        self.mode_combo.setCurrentText(mode_display)
        self.mode_combo.blockSignals(False)
        
        # Emulator
        self.emulator_combo.blockSignals(True)
        self.emulator_combo.setCurrentText(config.get("emulator_type", ""))
        self.emulator_combo.blockSignals(False)
        
        # ADB
        self.device_addr.blockSignals(True)
        self.adb_path.blockSignals(True)
        adb = config.get("adb_config", {})
        self.device_addr.setText(adb.get("device_address", "127.0.0.1:7555"))
        self.adb_path.setText(adb.get("adb_path", "adb"))
        self.device_addr.blockSignals(False)
        self.adb_path.blockSignals(False)
        
        self._loading = False
    
    def _on_mode_change(self, text):
        """Handle mode change"""
        if getattr(self, '_loading', False):
            return
        mode_map = {"URA Finale": "ura", "Unity Cup": "unity"}
        self.main_window.update_config_value("mode", mode_map.get(text, "ura"))
        self.main_window.save_config()
        
        # Update Unity fields visibility in training tab
        if hasattr(self.main_window, 'training_page'):
            self.main_window.training_page.update_unity_visibility()
    
    def _on_emulator_change(self, text):
        """Handle emulator type change"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("emulator_type", text)
        self.main_window.save_config()
        if text == "Phone":
            QMessageBox.information(
                self, "Phone Device",
                "When using Phone:\n• Auto address detection won't work\n• Manually enter ADB address\n• Resolution must be 1080x1920 (Portrait)"
            )
        elif text == "Other Emulator":
            QMessageBox.information(
                self, "Other Emulator",
                "When using Other Emulator:\n• Auto address detection won't work\n• Manually enter ADB address\n• Screenshot method will default to ADB"
            )
    
    def _update_adb_config(self, key, value):
        """Update ADB config"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_nested_config_value("adb_config", key, value)
        self.main_window.save_config()
