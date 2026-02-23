"""
Discord Tab for PySide6 GUI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from ..styles import COLORS


class DiscordTab(QScrollArea):
    """Discord tab"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
    
    def _create_ui(self):
        """Create UI"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Discord Group
        discord_group = QGroupBox("Join the Community")
        discord_layout = QVBoxLayout(discord_group)
        discord_layout.setSpacing(16)
        
        info_label = QLabel(
            "Join the UMAT Discord server for support, updates, and discussion!\n"
            "Get help from other users and stay up to date with the latest news."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        discord_layout.addWidget(info_label)
        
        # Discord button
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        
        self.discord_btn = QPushButton("  Join Discord Server")
        self.discord_btn.setFixedSize(250, 50)
        self.discord_btn.setCursor(Qt.PointingHandCursor)
        self.discord_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865F2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #4752C4;
            }
        """)
        self.discord_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("http://discord.gg/PhVmBtfsKp")))
        btn_layout.addWidget(self.discord_btn)
        
        btn_layout.addStretch()
        discord_layout.addLayout(btn_layout)
        
        layout.addWidget(discord_group)
        layout.addStretch()
        self.setWidget(container)
