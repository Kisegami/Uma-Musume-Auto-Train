"""
Others Tab for PySide6 GUI
Contains debug and miscellaneous settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QGroupBox, 
    QFrame, QScrollArea, QLineEdit, QPushButton, QMessageBox, QSpinBox
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
            lambda v: self._update_and_save("debug_mode", v == Qt.CheckState.Checked.value)
        )
        debug_layout.addWidget(self.debug_mode)
        
        self.stop_on_failure = QCheckBox("Stop Bot on Event Detection Failure")
        self.stop_on_failure.stateChanged.connect(
            lambda v: self._update_and_save("stop_on_event_detection_failure", v == Qt.CheckState.Checked.value)
        )
        debug_layout.addWidget(self.stop_on_failure)
        
        desc = QLabel("When enabled, bot stops if event name cannot be detected.\nWhen disabled, bot chooses top option as fallback.")
        desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        debug_layout.addWidget(desc)
        
        layout.addWidget(debug_group)
        
        # API Settings
        api_group = QGroupBox("API Settings (uma_viewer)")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(12)
        
        self.api_enabled = QCheckBox("Enable API Mode")
        self.api_enabled.stateChanged.connect(self._on_api_enabled_changed)
        api_layout.addWidget(self.api_enabled)
        
        api_desc = QLabel("Use uma_viewer packet data for faster game state detection.\nReplaces OCR for status, training, events, and skills.\nFalls back to OCR when API is unavailable.")
        api_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        api_layout.addWidget(api_desc)
        
        # Base URL row
        api_url_row = QHBoxLayout()
        api_url_label = QLabel("Base URL:")
        api_url_label.setFixedWidth(100)
        self.api_base_url = QLineEdit()
        self.api_base_url.setPlaceholderText("http://localhost:8123")
        self.api_base_url.editingFinished.connect(self._save_api_url)
        api_url_row.addWidget(api_url_label)
        api_url_row.addWidget(self.api_base_url)
        api_layout.addLayout(api_url_row)
        
        # Timeout row
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
        api_layout.addLayout(api_timeout_row)
        
        # Test connection button
        api_btn_row = QHBoxLayout()
        self.test_api_btn = QPushButton("Test Connection")
        self.test_api_btn.setFixedWidth(140)
        self.test_api_btn.clicked.connect(self._test_api_connection)
        api_btn_row.addWidget(self.test_api_btn)
        api_btn_row.addStretch()
        api_layout.addLayout(api_btn_row)
        
        layout.addWidget(api_group)
        
        # Discord Webhook Settings
        webhook_group = QGroupBox("Discord Webhook Settings")
        webhook_layout = QVBoxLayout(webhook_group)
        webhook_layout.setSpacing(12)
        
        self.webhook_enabled = QCheckBox("Enable Discord Webhook")
        self.webhook_enabled.stateChanged.connect(self._on_webhook_enabled_changed)
        webhook_layout.addWidget(self.webhook_enabled)
        
        # Webhook URL row
        url_row = QHBoxLayout()
        url_label = QLabel("Webhook URL:")
        url_label.setFixedWidth(100)
        self.webhook_url = QLineEdit()
        self.webhook_url.setPlaceholderText("https://discord.com/api/webhooks/...")
        self.webhook_url.editingFinished.connect(self._save_webhook_url)
        url_row.addWidget(url_label)
        url_row.addWidget(self.webhook_url)
        webhook_layout.addLayout(url_row)
        
        self.notify_on_complete = QCheckBox("Notify on Run Complete")
        self.notify_on_complete.stateChanged.connect(self._on_notify_complete_changed)
        webhook_layout.addWidget(self.notify_on_complete)
        
        # Test button
        btn_row = QHBoxLayout()
        self.test_webhook_btn = QPushButton("Test Webhook")
        self.test_webhook_btn.setFixedWidth(120)
        self.test_webhook_btn.clicked.connect(self._test_webhook)
        btn_row.addWidget(self.test_webhook_btn)
        btn_row.addStretch()
        webhook_layout.addLayout(btn_row)
        
        webhook_desc = QLabel("Send run completion notifications to a Discord channel via webhook.")
        webhook_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        webhook_layout.addWidget(webhook_desc)
        
        layout.addWidget(webhook_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        self.debug_mode.setChecked(config.get("debug_mode", False))
        self.stop_on_failure.setChecked(config.get("stop_on_event_detection_failure", False))
        
        # Load API settings
        api_config = config.get("api", {})
        self.api_enabled.setChecked(api_config.get("enabled", False))
        self.api_base_url.setText(api_config.get("base_url", "http://localhost:8123"))
        self.api_timeout.setValue(api_config.get("timeout", 2))
        
        # Load webhook settings
        webhook_config = config.get("discord_webhook", {})
        self.webhook_enabled.setChecked(webhook_config.get("enabled", False))
        self.webhook_url.setText(webhook_config.get("webhook_url", ""))
        self.notify_on_complete.setChecked(webhook_config.get("notify_on_run_complete", True))
    
    def _update_and_save(self, key, value):
        """Update config value and save"""
        self.main_window.update_config_value(key, value)
        self.main_window.save_config()
    
    # ── API config helpers ────────────────────────────────────────────────
    
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
        self.main_window.update_config_value("api", api_config)
        self.main_window.save_config()
    
    def _on_api_enabled_changed(self, state):
        """Handle API enabled checkbox change"""
        api_config = self._get_api_config()
        api_config["enabled"] = state == Qt.CheckState.Checked.value
        self._save_api_config(api_config)
    
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
                    f"✅ Connected to {url}\n\nServer is running but waiting for game data.\n(Start a career game to populate data)"
                )
            else:
                # Show a summary of the data
                year = data.get('year', 'N/A')
                mood = data.get('mood', {}).get('name', 'N/A')
                stats = data.get('stats', {})
                stats_str = ', '.join(f"{k.upper()}: {v}" for k, v in stats.items()) if stats else 'N/A'
                QMessageBox.information(
                    self, "API Test",
                    f"✅ Connected to {url}\n\n"
                    f"Year: {year}\nMood: {mood}\nStats: {stats_str}"
                )
        except requests.ConnectionError:
            QMessageBox.warning(
                self, "API Test",
                f"❌ Cannot connect to {url}\n\nMake sure uma_viewer is running."
            )
        except requests.Timeout:
            QMessageBox.warning(
                self, "API Test",
                f"❌ Connection timed out ({timeout}s)\n\nCheck the URL and try increasing the timeout."
            )
        except Exception as e:
            QMessageBox.critical(self, "API Test", f"❌ Error: {str(e)}")
    
    # ── Webhook config helpers ─────────────────────────────────────────────
    
    def _get_webhook_config(self):
        """Get current webhook config dict"""
        config = self.main_window.get_config()
        return config.get("discord_webhook", {
            "enabled": False,
            "webhook_url": "",
            "notify_on_run_complete": True
        })
    
    def _save_webhook_config(self, webhook_config):
        """Save webhook config"""
        self.main_window.update_config_value("discord_webhook", webhook_config)
        self.main_window.save_config()
    
    def _on_webhook_enabled_changed(self, state):
        """Handle webhook enabled checkbox change"""
        webhook_config = self._get_webhook_config()
        webhook_config["enabled"] = state == Qt.CheckState.Checked.value
        self._save_webhook_config(webhook_config)
    
    def _save_webhook_url(self):
        """Save webhook URL"""
        webhook_config = self._get_webhook_config()
        webhook_config["webhook_url"] = self.webhook_url.text().strip()
        self._save_webhook_config(webhook_config)
    
    def _on_notify_complete_changed(self, state):
        """Handle notify on complete checkbox change"""
        webhook_config = self._get_webhook_config()
        webhook_config["notify_on_run_complete"] = state == Qt.CheckState.Checked.value
        self._save_webhook_config(webhook_config)
    
    def _test_webhook(self):
        """Test webhook by sending a test message"""
        url = self.webhook_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Test Webhook", "Please enter a webhook URL first.")
            return
        
        try:
            from utils.discord_webhook import send_test_webhook
            # Try to take a screenshot for the test
            try:
                from utils.screenshot import take_screenshot
                screenshot = take_screenshot()
            except Exception as e:
                print(f"Failed to take screenshot for test: {e}")
                screenshot = None
                
            success, message = send_test_webhook(url, screenshot=screenshot)
            
            if success:
                QMessageBox.information(self, "Test Webhook", f"✅ {message}")
            else:
                QMessageBox.warning(self, "Test Webhook", f"❌ {message}")
        except ImportError:
            QMessageBox.critical(self, "Test Webhook", "Discord webhook module not found.")
        except Exception as e:
            QMessageBox.critical(self, "Test Webhook", f"Error: {str(e)}")
