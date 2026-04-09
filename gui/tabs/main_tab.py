"""
Main Tab for PySide6 GUI
Contains ADB configuration and mode settings.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QGroupBox, QGridLayout, QFrame, QScrollArea, QMessageBox,
    QSizePolicy, QCheckBox, QSpinBox, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

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
        mode_main_layout = QHBoxLayout(mode_group)
        mode_main_layout.setSpacing(16)
        mode_main_layout.setContentsMargins(12, 6, 12, 6)
        
        # Left side: Settings
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(6)
        
        # Game Mode row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(QLabel("Game Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["URA Finale", "Unity Cup"])
        self.mode_combo.setFixedWidth(140)
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        mode_row.addWidget(self.mode_combo)
        settings_layout.addLayout(mode_row)
        
        # Unity Team row (only visible when Unity mode selected)
        self.unity_team_row = QWidget()
        team_row_layout = QHBoxLayout(self.unity_team_row)
        team_row_layout.setContentsMargins(0, 0, 0, 0)
        team_row_layout.setSpacing(8)
        self.unity_team_label = QLabel("Unity Team:")
        team_row_layout.addWidget(self.unity_team_label)
        self.unity_team_combo = QComboBox()
        self.unity_team_combo.addItems([
            "Happy Hoppers", "Sunny Runners", "Carrot Pudding", 
            "Blue Bloom", "Team Carrot"
        ])
        self.unity_team_combo.setFixedWidth(140)
        self.unity_team_combo.currentTextChanged.connect(self._on_unity_team_change)
        team_row_layout.addWidget(self.unity_team_combo)
        settings_layout.addWidget(self.unity_team_row)
        
        # Wrap settings in container with top alignment
        settings_container = QWidget()
        settings_container.setLayout(settings_layout)
        mode_main_layout.addWidget(settings_container, alignment=Qt.AlignTop)
        mode_main_layout.addStretch()
        
        # Right side: Scenario Logo (aligned to top)
        self.scenario_logo = QLabel()
        mode_main_layout.addWidget(self.scenario_logo, alignment=Qt.AlignTop | Qt.AlignRight)
        
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

        # Other
        other_group = QGroupBox("API Mode (Experimental)")
        other_layout = QVBoxLayout(other_group)
        other_layout.setSpacing(12)

        self.api_enabled = QCheckBox("Turn on API Mode")
        self.api_enabled.stateChanged.connect(self._on_api_enabled_changed)
        other_layout.addWidget(self.api_enabled)

        self.api_settings_widget = QWidget()
        api_settings_layout = QVBoxLayout(self.api_settings_widget)
        api_settings_layout.setContentsMargins(0, 0, 0, 0)
        api_settings_layout.setSpacing(12)

        api_desc = QLabel(
            "Use Kise Uma Capture to read game status directly from network packets.\n"
            "This feature is experimental and depends on an external module.\n"
            "Check the Discord server for setup details and more information."
        )
        api_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        api_settings_layout.addWidget(api_desc)

        api_url_row = QHBoxLayout()
        api_url_label = QLabel("API Address:")
        api_url_label.setFixedWidth(100)
        self.api_base_url = QLineEdit()
        self.api_base_url.setPlaceholderText("http://localhost:8123")
        self.api_base_url.editingFinished.connect(self._save_api_url)
        api_url_row.addWidget(api_url_label)
        api_url_row.addWidget(self.api_base_url)
        api_settings_layout.addLayout(api_url_row)

        api_timeout_row = QHBoxLayout()
        api_timeout_label = QLabel("Timeout (s):")
        api_timeout_label.setFixedWidth(100)
        self.api_timeout = QSpinBox()
        self.api_timeout.setMinimum(1)
        self.api_timeout.setMaximum(30)
        self.api_timeout.setValue(2)
        self.api_timeout.setFixedWidth(80)
        self.api_timeout.valueChanged.connect(self._save_api_timeout)
        api_timeout_row.addWidget(api_timeout_label)
        api_timeout_row.addWidget(self.api_timeout)
        api_timeout_row.addStretch()
        api_settings_layout.addLayout(api_timeout_row)

        api_btn_row = QHBoxLayout()
        self.test_api_btn = QPushButton("Test Connection")
        self.test_api_btn.setFixedWidth(140)
        self.test_api_btn.clicked.connect(self._test_api_connection)
        api_btn_row.addWidget(self.test_api_btn)
        api_btn_row.addStretch()
        api_settings_layout.addLayout(api_btn_row)

        other_layout.addWidget(self.api_settings_widget)

        layout.addWidget(other_group)
        
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
        
        # Unity Team Name
        self.unity_team_combo.blockSignals(True)
        self.unity_team_combo.setCurrentText(config.get("unity_team_name", "Team Carrot"))
        self.unity_team_combo.blockSignals(False)
        
        # Set Unity Team visibility based on mode and update scenario logo
        is_unity = (mode == "unity")
        self.unity_team_row.setVisible(is_unity)
        self._update_scenario_logo(mode)
        
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

        # API
        self.api_enabled.blockSignals(True)
        self.api_base_url.blockSignals(True)
        self.api_timeout.blockSignals(True)
        api = config.get("api", {})
        self.api_enabled.setChecked(api.get("enabled", False))
        self.api_base_url.setText(api.get("base_url", "http://localhost:8123"))
        self.api_timeout.setValue(api.get("timeout", 2))
        self.api_enabled.blockSignals(False)
        self.api_base_url.blockSignals(False)
        self.api_timeout.blockSignals(False)
        self._update_api_settings_visibility(api.get("enabled", False))
        
        self._loading = False
    
    def _on_mode_change(self, text):
        """Handle mode change"""
        if getattr(self, '_loading', False):
            return
        mode_map = {"URA Finale": "ura", "Unity Cup": "unity"}
        mode = mode_map.get(text, "ura")
        self.main_window.update_config_value("mode", mode)
        self.main_window.save_config()
        
        # Toggle Unity Team visibility and update scenario logo
        is_unity = (mode == "unity")
        self.unity_team_row.setVisible(is_unity)
        self._update_scenario_logo(mode)
        
        # Update Unity fields visibility and reload training scores for new mode
        if hasattr(self.main_window, 'training_page'):
            self.main_window.training_page.update_unity_visibility()
            self.main_window.training_page._load_training_score_config()
    
    def _on_unity_team_change(self, text):
        """Handle Unity Team change"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("unity_team_name", text)
        self.main_window.save_config()
    
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

    def _get_api_config(self):
        """Get current API config dict"""
        config = self.main_window.get_config()
        return config.get("api", {
            "enabled": False,
            "base_url": "http://localhost:8123",
            "timeout": 2
        })

    def _save_api_config(self, api_config):
        """Save API config"""
        if getattr(self, '_loading', False):
            return
        self.main_window.update_config_value("api", api_config)
        self.main_window.save_config()

    def _on_api_enabled_changed(self, state):
        """Handle API enabled checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self._update_api_settings_visibility(enabled)
        api_config = self._get_api_config()
        api_config["enabled"] = enabled
        self._save_api_config(api_config)

    def _update_api_settings_visibility(self, visible):
        """Show or hide API settings based on enabled state"""
        self.api_settings_widget.setVisible(visible)

    def _save_api_url(self):
        """Save API base URL"""
        api_config = self._get_api_config()
        api_config["base_url"] = self.api_base_url.text().strip() or "http://localhost:8123"
        self._save_api_config(api_config)

    def _save_api_timeout(self, value):
        """Save API timeout"""
        api_config = self._get_api_config()
        api_config["timeout"] = value
        self._save_api_config(api_config)

    def _test_api_connection(self):
        """Test API connection by hitting the /status endpoint"""
        import requests

        url = self.api_base_url.text().strip() or "http://localhost:8123"
        timeout = self.api_timeout.value()
        try:
            resp = requests.get(f"{url}/status", timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("status") == "waiting":
                QMessageBox.information(
                    self, "API Test",
                    f"Connected to {url}\n\nServer is running but waiting for game data.\nStart a career run to populate data."
                )
            else:
                year = data.get('year', 'N/A')
                mood = data.get('mood', {}).get('name', 'N/A')
                stats = data.get('stats', {})
                stats_str = ', '.join(f"{k.upper()}: {v}" for k, v in stats.items()) if stats else 'N/A'
                QMessageBox.information(
                    self, "API Test",
                    f"Connected to {url}\n\n"
                    f"Year: {year}\nMood: {mood}\nStats: {stats_str}"
                )
        except requests.ConnectionError:
            QMessageBox.warning(
                self, "API Test",
                f"Cannot connect to {url}\n\nMake sure Kise Uma Capture is running."
            )
        except requests.Timeout:
            QMessageBox.warning(
                self, "API Test",
                f"Connection timed out ({timeout}s)\n\nCheck the URL and try increasing the timeout."
            )
        except Exception as e:
            QMessageBox.critical(self, "API Test", f"Error: {str(e)}")
    
    def _update_scenario_logo(self, mode):
        """Update the scenario logo based on the selected mode"""
        # Get assets directory path
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "scenario")
        
        if mode == "unity":
            logo_path = os.path.join(assets_dir, "Unity_Cup.png")
        else:
            logo_path = os.path.join(assets_dir, "Ura_Finale.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale to 200px height while keeping aspect ratio
            scaled_pixmap = pixmap.scaledToHeight(200, Qt.SmoothTransformation)
            self.scenario_logo.setPixmap(scaled_pixmap)
        else:
            self.scenario_logo.clear()
