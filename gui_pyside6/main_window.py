"""
Main Window for PySide6 GUI
Uma Musume Auto-Train Bot - Modern Sidebar Design with 9 tabs matching original GUI.
"""

import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QSplitter, QPushButton, QStackedWidget,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap

from .styles import MAIN_STYLESHEET, COLORS
from .icon_helper import get_icon
from .status_panel import StatusPanel
from .log_panel import LogPanel
from .bot_controller import BotController

# Import all 9 tabs matching original GUI
from .tabs.main_tab import MainTab
from .tabs.performance_tab import PerformanceTab
from .tabs.training_tab import TrainingTab
from .tabs.racing_tab import RacingTab
from .tabs.event_tab import EventTab
from .tabs.skill_tab import SkillTab
from .tabs.restart_tab import RestartTab
from .tabs.others_tab import OthersTab
from .tabs.update_tab import UpdateTab


class SidebarButton(QPushButton):
    """Custom sidebar navigation button"""
    
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarBtn")
        self.setCheckable(True)
        self.setText(f"  {text}")
        self.setFont(QFont("Segoe UI", 10, QFont.Bold))
        if icon_name:
            self.setIcon(get_icon(icon_name, "white"))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Uma Musume Auto-Train")
        self.setMinimumSize(1200, 700)
        self._set_responsive_size()
        
        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Bot state
        self.bot_running = False
        self.config_file = "config.json"
        self.config = {}
        
        # Load configuration
        self.load_config()
        
        # Detect emulator types
        self.detected_emulator_types = self._detect_emulators()
        
        # Create UI
        self._create_ui()
        
        # Initial log
        self.add_log("Uma Musume Auto-Train initialized")
        self.add_log(f"Config: {self.config_file}")
        
        # Add Qt compatibility layer for BotController
        # BotController expects root.after() like tkinter, so we provide it
        self.root = self  # BotController accesses self.main_window.root
        
        # Initialize bot controller (must be after GUI components are created)
        self.bot_controller = BotController(self)
        # Connect bot stopped signal to reset UI when bot auto-stops
        self.bot_controller.signaler.bot_stopped_signal.connect(self._on_bot_stopped)
    
    def _set_responsive_size(self):
        """Set responsive window size"""
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.75)
        height = int(screen.height() * 0.8)
        width = max(1200, min(width, 1600))
        height = max(750, min(height, 1000))
        self.resize(width, height)
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
    
    def _detect_emulators(self):
        """Detect available emulator types"""
        env_detect = os.environ.get("UMA_DETECTED_EMULATOR_TYPES")
        if env_detect:
            try:
                return json.loads(env_detect)
            except Exception:
                pass
        try:
            from utils.emulator_detect import list_emulator_types
            return list_emulator_types()
        except Exception:
            return []
    
    def _create_ui(self):
        """Create the main UI with sidebar"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ==================== Sidebar ====================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(2)
        
        # Logo at top of sidebar
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_pixmap = logo_pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        
        sidebar_layout.addSpacing(8)
        
        # App title in sidebar
        title_label = QLabel("UMAT v0.2")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px;")
        sidebar_layout.addWidget(title_label)
        
        # Author credit
        author_label = QLabel("By Kisegami ❤️")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        sidebar_layout.addWidget(author_label)
        
        # Status indicator
        self.status_label = QLabel("● Inactive")
        self.status_label.setObjectName("subtitle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        sidebar_layout.addWidget(self.status_label)
        
        sidebar_layout.addSpacing(16)
        
        # Navigation buttons - 9 tabs matching original GUI
        self.nav_buttons = []
        nav_items = [
            ("Main", "fa5s.cog"),
            ("Performance", "fa5s.chart-bar"),
            ("Training", "fa5s.running"),
            ("Racing", "fa5s.flag-checkered"),
            ("Event", "fa5s.calendar"),
            ("Skill", "fa5s.star"),
            ("Restart", "fa5s.redo"),
            ("Others", "fa5s.wrench"),
            ("Update", "fa5s.download"),
        ]
        
        for text, icon in nav_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda checked, t=text: self._on_nav_clicked(t))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((text, btn))
        
        sidebar_layout.addStretch()
        
        # Start/Stop button at bottom of sidebar
        self.start_btn = QPushButton("  Start Bot")
        self.start_btn.setIcon(get_icon('play', 'white'))
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._toggle_bot)
        sidebar_layout.addWidget(self.start_btn)
        
        main_layout.addWidget(sidebar)
        
        # ==================== Content Area ====================
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # Left: Stacked pages - 9 pages matching original
        self.page_stack = QStackedWidget()
        
        # Create all 9 pages
        self.main_page = MainTab(self)
        self.performance_page = PerformanceTab(self)
        self.training_page = TrainingTab(self)
        self.racing_page = RacingTab(self)
        self.event_page = EventTab(self)
        self.skill_page = SkillTab(self)
        self.restart_page = RestartTab(self)
        self.others_page = OthersTab(self)
        self.update_page = UpdateTab(self)
        
        self.page_stack.addWidget(self.main_page)
        self.page_stack.addWidget(self.performance_page)
        self.page_stack.addWidget(self.training_page)
        self.page_stack.addWidget(self.racing_page)
        self.page_stack.addWidget(self.event_page)
        self.page_stack.addWidget(self.skill_page)
        self.page_stack.addWidget(self.restart_page)
        self.page_stack.addWidget(self.others_page)
        self.page_stack.addWidget(self.update_page)
        
        content_layout.addWidget(self.page_stack, stretch=2)
        
        # Right: Status + Log panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        self.status_panel = StatusPanel(self)
        right_layout.addWidget(self.status_panel)
        
        self.log_panel = LogPanel(self)
        right_layout.addWidget(self.log_panel, stretch=1)
        
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addWidget(content_area, stretch=1)
        
        # Select first nav button
        self.nav_buttons[0][1].setChecked(True)
    
    def _on_nav_clicked(self, page_name):
        """Handle navigation button click"""
        page_map = {
            "Main": 0,
            "Performance": 1,
            "Training": 2,
            "Racing": 3,
            "Event": 4,
            "Skill": 5,
            "Restart": 6,
            "Others": 7,
            "Update": 8,
        }
        
        # Update button states
        for name, btn in self.nav_buttons:
            btn.setChecked(name == page_name)
        
        # Switch page
        if page_name in page_map:
            self.page_stack.setCurrentIndex(page_map[page_name])
    
    def _toggle_bot(self):
        """Toggle bot start/stop"""
        if self.bot_running:
            self.stop_bot()
        else:
            self.start_bot()
    
    # Config management
    def load_config(self):
        """Load configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            elif os.path.exists('config.example.json'):
                with open('config.example.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.save_config()
            else:
                self.config = self._get_default_config()
                self.save_config()
        except Exception as e:
            self.add_log(f"Error loading config: {e}", "error")
            self.config = self._get_default_config()
    
    def save_config(self):
        """Save configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log("Config saved")
        except Exception as e:
            self.add_log(f"Error: {e}", "error")
    
    def _get_default_config(self):
        """Default config"""
        return {
            "mode": "ura",
            "capture_method": "auto",
            "emulator_type": "",
            "adb_config": {"device_address": "127.0.0.1:7555", "adb_path": "adb", "screenshot_timeout": 5, "input_delay": 0.5},
            "training": {"priority_stat": ["spd", "sta", "wit", "pwr", "guts"], "minimum_mood": "GREAT", "maximum_failure": 15, "min_energy": 30},
            "racing": {"strategy": "FRONT", "retry_race": True},
            "skills": {"skill_point_cap": 400, "skill_purchase": "auto"},
            "debug_mode": False,
            "update": {"auto_update": True, "install_dependencies": True, "branch": "main"}
        }
    
    def get_config(self):
        return self.config
    
    def set_config(self, config):
        """Set config and save"""
        self.config = config
        self.save_config()
    
    def update_config_value(self, key, value):
        self.config[key] = value
    
    def update_nested_config_value(self, parent_key, child_key, value):
        if parent_key not in self.config:
            self.config[parent_key] = {}
        self.config[parent_key][child_key] = value
    
    # Bot control
    def start_bot(self):
        """Start bot"""
        self.add_log("start_bot() called", "info")
        if hasattr(self, 'bot_controller'):
            self.add_log("BotController exists, calling start_bot()", "info")
            try:
                self.bot_controller.start_bot()
                self.bot_running = True
                # Update UI
                self.start_btn.setText("  Stop Bot")
                self.start_btn.setIcon(get_icon('stop', 'white'))
                self.start_btn.setObjectName("danger")
                self.start_btn.setStyleSheet(f"background-color: {COLORS['accent_red']}; border: none; color: white;")
                self.status_label.setText("● Running")
                self.status_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                if hasattr(self, 'log_panel'):
                    self.log_panel.update_bot_state(True)
            except Exception as e:
                self.add_log(f"Error starting bot: {e}", "error")
                import traceback
                self.add_log(traceback.format_exc(), "error")
        else:
            self.add_log("BotController not found!", "error")
    
    def stop_bot(self):
        """Stop bot"""
        if hasattr(self, 'bot_controller'):
            self.bot_controller.stop_bot()
            self.bot_running = False
            # Update UI
            self.start_btn.setText("  Start Bot")
            self.start_btn.setIcon(get_icon('play', 'white'))
            self.start_btn.setObjectName("primary")
            self.start_btn.setStyleSheet(f"background-color: {COLORS['accent_green']}; border: none; color: white;")
            self.status_label.setText("● Inactive")
            self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            if hasattr(self, 'log_panel'):
                self.log_panel.update_bot_state(False)
        self.add_log("Bot stopped", "warning")
        if hasattr(self, 'log_panel'):
            self.log_panel.update_bot_state(False)
    
    def update_status(self, year, energy, turn, mood, goal_met, stats):
        """Update status panel"""
        if hasattr(self, 'status_panel'):
            self.status_panel.update_status(year, energy, turn, mood, goal_met, stats)
    
    def add_log(self, message, level="info"):
        """Add log message"""
        if hasattr(self, 'log_panel'):
            self.log_panel.add_log(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    def after(self, delay_ms, callback, *args):
        """Qt compatibility wrapper for tkinter's root.after() method"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(delay_ms, lambda: callback(*args))
    
    def closeEvent(self, event):
        """Handle close"""
        if self.bot_running:
            reply = QMessageBox.question(self, "Confirm Exit", "Bot is running. Stop and exit?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stop_bot()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def _on_bot_stopped(self):
        """Handle bot stopped signal - reset UI to stopped state"""
        self.bot_running = False
        # Update UI
        self.start_btn.setText("  Start Bot")
        self.start_btn.setIcon(get_icon('play', 'white'))
        self.start_btn.setObjectName("primary")
        self.start_btn.setStyleSheet(f"background-color: {COLORS['accent_green']}; border: none; color: white;")
        self.status_label.setText("● Inactive")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        if hasattr(self, 'log_panel'):
            self.log_panel.update_bot_state(False)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
