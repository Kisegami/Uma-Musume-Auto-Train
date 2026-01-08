"""
Log Panel for PySide6 GUI
Clean log display matching Alas/MAA style.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QTextEdit, QPushButton
)
from PySide6.QtCore import Qt

from .styles import COLORS


class LogPanel(QFrame):
    """Log panel with scrollable view"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("card")
        
        self._create_ui()
    
    def _create_ui(self):
        """Create log UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Log")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("flat")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(self.clear_logs)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
        """)
        layout.addWidget(self.log_text, stretch=1)
    
    def add_log(self, message, level="info"):
        """Add log entry"""
        time_str = datetime.now().strftime("%H:%M:%S")
        
        colors = {
            "info": COLORS['text_secondary'],
            "success": COLORS['accent_green'],
            "warning": COLORS['accent_orange'],
            "error": COLORS['accent_red'],
        }
        color = colors.get(level, COLORS['text_secondary'])
        
        html = f'<span style="color:{COLORS["text_muted"]}">[{time_str}]</span> <span style="color:{color}">{message}</span>'
        self.log_text.append(html)
        
        # Auto-scroll
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
    
    def clear_logs(self):
        """Clear logs"""
        self.log_text.clear()
    
    def update_bot_state(self, running):
        """Update based on bot state (no buttons here now)"""
        pass
