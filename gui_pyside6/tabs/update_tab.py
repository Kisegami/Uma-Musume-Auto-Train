"""
Update Tab for PySide6 GUI
Handles automatic update settings and manual updates.
"""

import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal, Slot

from ..styles import COLORS


class UpdateSignaler(QObject):
    """Signal emitter for thread-safe update status"""
    status_signal = Signal(str, str)  # message, status_type


class UpdateTab(QScrollArea):
    """Update configuration tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.updating = False
        self.update_available = False
        
        # Signal emitter for thread-safe GUI updates
        self.signaler = UpdateSignaler()
        self.signaler.status_signal.connect(self._on_status_signal)
        
        self._create_ui()
        self.load_config()
        self._refresh_commit_info()
    
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
        
        self.auto_update = QCheckBox("Auto Update on Launch")
        self.auto_update.stateChanged.connect(
            lambda v: self._update_config("update", "auto_update", v == Qt.Checked)
        )
        update_layout.addWidget(self.auto_update, 0, 0, 1, 2)
        
        self.install_deps = QCheckBox("Auto Install Dependencies")
        self.install_deps.stateChanged.connect(
            lambda v: self._update_config("update", "install_dependencies", v == Qt.Checked)
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
        
        # Manual Update
        manual_group = QGroupBox("Manual Update")
        manual_layout = QVBoxLayout(manual_group)
        manual_layout.setSpacing(12)
        
        # Commit info
        self.commit_label = QLabel("")
        self.commit_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        manual_layout.addWidget(self.commit_label)
        
        # Status label
        self.status_label = QLabel("Click 'Check for Updates' to check for available updates.")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_label.setWordWrap(True)
        manual_layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.check_btn = QPushButton("Check for Updates")
        self.check_btn.clicked.connect(self._check_updates)
        btn_layout.addWidget(self.check_btn)
        
        self.update_btn = QPushButton("Update Now")
        self.update_btn.setObjectName("primary")
        self.update_btn.setEnabled(False)  # Initially disabled
        self.update_btn.clicked.connect(self._update_now)
        btn_layout.addWidget(self.update_btn)
        
        btn_layout.addStretch()
        manual_layout.addLayout(btn_layout)
        
        layout.addWidget(manual_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def load_config(self):
        """Load config values"""
        config = self.main_window.get_config()
        
        update = config.get("update", {})
        self.auto_update.setChecked(update.get("auto_update", False))
        self.install_deps.setChecked(update.get("install_dependencies", True))
        self.branch_combo.setCurrentText(update.get("branch", "main"))
    
    def _update_config(self, parent, key, value):
        """Update config value and save"""
        self.main_window.update_nested_config_value(parent, key, value)
        self.main_window.save_config()
    
    def _refresh_commit_info(self):
        """Refresh current commit information"""
        try:
            from utils.git_manager import GitManager
            
            git_manager = GitManager()
            if git_manager.is_git_repo():
                commit = git_manager.get_current_commit(short=True)
                commit_info = git_manager.get_commit_info()
                
                if commit:
                    text = f"Current commit: {commit}"
                    if commit_info and 'message' in commit_info:
                        msg = commit_info['message'][:50]
                        text += f" - {msg}"
                    self.commit_label.setText(text)
                else:
                    self.commit_label.setText("Could not get commit information")
            else:
                self.commit_label.setText("Not a git repository")
        except Exception as e:
            self.commit_label.setText(f"Git info unavailable: {str(e)[:30]}")
    
    @Slot(str, str)
    def _on_status_signal(self, message, status_type):
        """Handle status update from thread"""
        color_map = {
            'info': COLORS['text_secondary'],
            'success': COLORS['accent_green'],
            'error': COLORS['accent_red'],
            'warning': COLORS['accent_orange']
        }
        color = color_map.get(status_type, COLORS['text_secondary'])
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)
        
        # Enable update button if update available
        if status_type == 'success' and 'available' in message.lower():
            self.update_btn.setEnabled(True)
            self.update_available = True
        
        # Reset buttons when done
        if 'complete' in message.lower() or 'error' in message.lower():
            self.check_btn.setEnabled(True)
            self.update_btn.setEnabled(self.update_available)
            self.updating = False
            self._refresh_commit_info()
    
    def _check_updates(self):
        """Check for available updates"""
        if self.updating:
            return
        
        self.check_btn.setEnabled(False)
        self.status_label.setText("Checking for updates...")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.main_window.add_log("Checking for updates...")
        
        def check_thread():
            try:
                from utils.updater import Updater
                
                branch = self.branch_combo.currentText()
                config = self.main_window.get_config()
                remote = config.get("update", {}).get("remote", "origin")
                
                updater = Updater(branch=branch, remote=remote)
                
                if not updater.git_manager.test_git():
                    self.signaler.status_signal.emit("Git is not available", "error")
                    return
                
                available = updater.check_update()
                
                if available:
                    self.signaler.status_signal.emit("Update available!", "success")
                else:
                    self.signaler.status_signal.emit("Repository is up to date", "info")
                    
            except Exception as e:
                self.signaler.status_signal.emit(f"Error: {str(e)}", "error")
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def _update_now(self):
        """Perform the update"""
        if self.updating:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Update",
            "This will update the code and install dependencies.\n"
            "The application will need to be restarted.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.updating = True
        self.check_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.status_label.setText("Updating...")
        self.status_label.setStyleSheet(f"color: {COLORS['accent_orange']};")
        self.main_window.add_log("Starting update...")
        
        def update_thread():
            try:
                from utils.updater import Updater
                
                branch = self.branch_combo.currentText()
                config = self.main_window.get_config()
                remote = config.get("update", {}).get("remote", "origin")
                install_deps = self.install_deps.isChecked()
                
                updater = Updater(branch=branch, remote=remote)
                success = updater.update(install_dependencies=install_deps)
                
                if success:
                    self.signaler.status_signal.emit(
                        "Update complete! Please restart the application.", "success"
                    )
                else:
                    self.signaler.status_signal.emit(
                        "Update failed. Check logs for details.", "error"
                    )
                    
            except Exception as e:
                self.signaler.status_signal.emit(f"Error: {str(e)}", "error")
        
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()
