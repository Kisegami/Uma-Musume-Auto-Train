"""
Donation Tab for PySide6 GUI
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon

from ..styles import COLORS


class DonationTab(QScrollArea):
    """Donation tab"""
    
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
        
        # Support Group
        support_group = QGroupBox("Support the Developer")
        support_layout = QVBoxLayout(support_group)
        support_layout.setSpacing(16)
        
        info_label = QLabel(
            "If you find this bot helpful, please consider supporting the development!\n"
            "Your support helps keep the project alive and frequently updated."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        support_layout.addWidget(info_label)
        
        # Buy Me A Coffee button using QIcon for crisp rendering
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        
        bmac_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "bmac.png")
        
        self.coffee_btn = QPushButton()
        icon_size = QSize(280, 60)
        self.coffee_btn.setFixedSize(290, 70)
        if os.path.exists(bmac_path):
            pixmap = QPixmap(bmac_path).scaled(icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.coffee_btn.setIcon(QIcon(pixmap))
            self.coffee_btn.setIconSize(icon_size)
        self.coffee_btn.setCursor(Qt.PointingHandCursor)
        self.coffee_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 15);
                border-radius: 8px;
            }
        """)
        self.coffee_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.buymeacoffee.com/kisegami")))
        btn_layout.addWidget(self.coffee_btn)
        
        btn_layout.addStretch()
        support_layout.addLayout(btn_layout)
        
        layout.addWidget(support_group)
        layout.addStretch()
        self.setWidget(container)
