"""
Others Tab for PySide6 GUI
Contains debug and miscellaneous settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QGroupBox, 
    QFrame, QScrollArea, QLineEdit, QPushButton, QMessageBox
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
            lambda v: self._update_and_save("debug_mode", v == Qt.Checked)
        )
        debug_layout.addWidget(self.debug_mode)
        
        self.stop_on_failure = QCheckBox("Stop Bot on Event Detection Failure")
        self.stop_on_failure.stateChanged.connect(
            lambda v: self._update_and_save("stop_on_event_detection_failure", v == Qt.Checked)
        )
        debug_layout.addWidget(self.stop_on_failure)
        
        desc = QLabel("When enabled, bot stops if event name cannot be detected.\nWhen disabled, bot chooses top option as fallback.")
        desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-left: 25px;")
        debug_layout.addWidget(desc)
        
        layout.addWidget(debug_group)
        
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
        
        # Load webhook settings
        webhook_config = config.get("discord_webhook", {})
        self.webhook_enabled.setChecked(webhook_config.get("enabled", False))
        self.webhook_url.setText(webhook_config.get("webhook_url", ""))
        self.notify_on_complete.setChecked(webhook_config.get("notify_on_run_complete", True))
    
    def _update_and_save(self, key, value):
        """Update config value and save"""
        self.main_window.update_config_value(key, value)
        self.main_window.save_config()
    
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
        webhook_config["enabled"] = state == Qt.Checked
        self._save_webhook_config(webhook_config)
    
    def _save_webhook_url(self):
        """Save webhook URL"""
        webhook_config = self._get_webhook_config()
        webhook_config["webhook_url"] = self.webhook_url.text().strip()
        self._save_webhook_config(webhook_config)
    
    def _on_notify_complete_changed(self, state):
        """Handle notify on complete checkbox change"""
        webhook_config = self._get_webhook_config()
        webhook_config["notify_on_run_complete"] = state == Qt.Checked
        self._save_webhook_config(webhook_config)
    
    def _test_webhook(self):
        """Test webhook by sending a test message"""
        url = self.webhook_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Test Webhook", "Please enter a webhook URL first.")
            return
        
        try:
            from utils.discord_webhook import send_test_webhook
            success, message = send_test_webhook(url)
            
            if success:
                QMessageBox.information(self, "Test Webhook", f"✅ {message}")
            else:
                QMessageBox.warning(self, "Test Webhook", f"❌ {message}")
        except ImportError:
            QMessageBox.critical(self, "Test Webhook", "Discord webhook module not found.")
        except Exception as e:
            QMessageBox.critical(self, "Test Webhook", f"Error: {str(e)}")
