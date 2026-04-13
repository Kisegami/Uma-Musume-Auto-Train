import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from utils.core.input_trace import get_input_trace_path, reset_input_trace_log

from .icon_helper import get_icon
from .styles import COLORS


class InputLogWindow(QFrame):
    """Live window for timestamped bot input actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowTitle("Live Input Log")
        self.resize(760, 520)
        self.setObjectName("card")

        self._log_path = get_input_trace_path()
        self._last_position = 0

        self._create_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._poll_log_file)

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Live Input Log")
        title.setObjectName("sectionTitle")
        header.addWidget(title)

        self.path_label = QLabel(self._log_path)
        self.path_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        header.addWidget(self.path_label, stretch=1)

        clear_btn = QPushButton()
        clear_btn.setIcon(get_icon("delete"))
        clear_btn.setToolTip("Clear Input Log")
        clear_btn.setObjectName("flat")
        clear_btn.setFixedSize(32, 32)
        clear_btn.clicked.connect(self.clear_log)
        header.addWidget(clear_btn)

        refresh_btn = QPushButton()
        refresh_btn.setIcon(get_icon("refresh"))
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setObjectName("flat")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.clicked.connect(self._reload_all)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
            """
        )
        layout.addWidget(self.log_text, stretch=1)

    def showEvent(self, event):
        super().showEvent(event)
        self._reload_all()
        self._timer.start()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)

    def clear_log(self):
        reset_input_trace_log()
        self.log_text.clear()
        self._last_position = 0

    def _reload_all(self):
        self._last_position = 0
        self.log_text.clear()
        self._poll_log_file()

    def _poll_log_file(self):
        path = self._log_path
        if not os.path.exists(path):
            return

        try:
            file_size = os.path.getsize(path)
            if file_size < self._last_position:
                self._last_position = 0
                self.log_text.clear()

            with open(path, "r", encoding="utf-8") as f:
                f.seek(self._last_position)
                chunk = f.read()
                self._last_position = f.tell()

            if not chunk:
                return

            self.log_text.moveCursor(QTextCursor.End)
            self.log_text.insertPlainText(chunk)
            self.log_text.moveCursor(QTextCursor.End)
        except Exception:
            return
