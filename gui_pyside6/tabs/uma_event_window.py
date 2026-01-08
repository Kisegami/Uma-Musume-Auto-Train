"""
Uma Event Editor Window for PySide6 GUI - Enhanced Version
Shows Uma events with choice buttons, result preview, and modern styling.
"""

import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QWidget, QFrame, QGridLayout, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import COLORS, MAIN_STYLESHEET


class UmaEventWindow(QDialog):
    """Uma event choice editor with enhanced styling"""
    
    def __init__(self, parent, uma_name, uma_info):
        super().__init__(parent)
        self.uma_name = uma_name
        self.uma_slug = uma_info.get("UmaSlug", "")
        self.uma_events = uma_info.get("UmaEvents", [])
        self.custom_choices = {}
        self.choice_buttons = {}
        self.result_labels = {}
        
        self.setWindowTitle(f"Uma Event Choices - {uma_name}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._load_existing_choices()
        self._create_ui()
    
    def _load_existing_choices(self):
        """Load existing custom choices from file"""
        safe_name = self.uma_name.replace("/", "-").replace("\\", "-").replace(":", "-")
        filepath = os.path.join("template", "events", f"Events_{safe_name}.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_choices = data.get("CustomChoices", {})
            except:
                pass
    
    def _create_ui(self):
        """Create enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(f"🐴 Custom Choices for {self.uma_name}")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        
        selected_count = len(self.custom_choices)
        count_badge = QLabel(f"{selected_count} selected")
        count_badge.setStyleSheet(f"""
            background-color: {COLORS['accent_primary']};
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
        """)
        self.count_badge = count_badge
        header.addWidget(count_badge)
        layout.addLayout(header)
        
        # Info
        info = QLabel("Click on a choice to select it. The result will be shown on the right.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(info)
        
        # Scrollable events area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_widget = QWidget()
        self.events_layout = QVBoxLayout(scroll_widget)
        self.events_layout.setSpacing(10)
        
        # Group and filter events
        events_grouped = {}
        for event in self.uma_events:
            event_name = event.get("EventName", "Unknown")
            if event_name not in events_grouped:
                events_grouped[event_name] = []
            
            event_options = event.get("EventOptions", {})
            for option_key, result in event_options.items():
                if option_key.strip():
                    events_grouped[event_name].append({
                        "option": option_key,
                        "result": result
                    })
        
        # Filter out events without choices
        events_grouped = {k: v for k, v in events_grouped.items() if v}
        
        # Create rows
        for event_name, options in events_grouped.items():
            row = self._create_event_row(event_name, options)
            self.events_layout.addWidget(row)
        
        self.events_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Footer buttons
        footer = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        footer.addWidget(clear_btn)
        
        footer.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Choices")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_choices)
        footer.addWidget(save_btn)
        
        layout.addLayout(footer)
    
    def _create_event_row(self, event_name, options):
        """Create enhanced event row"""
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(16)
        
        # Event name
        name_label = QLabel(event_name)
        name_label.setWordWrap(True)
        name_label.setMinimumWidth(200)
        name_label.setMaximumWidth(250)
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(name_label, stretch=0)
        
        # Choices buttons frame
        choices_widget = QWidget()
        choices_layout = QVBoxLayout(choices_widget)
        choices_layout.setContentsMargins(0, 0, 0, 0)
        choices_layout.setSpacing(6)
        
        self.choice_buttons[event_name] = {}
        option_results = {opt["option"]: opt["result"] for opt in options}
        
        for opt in options:
            option_name = opt["option"]
            btn = QPushButton(option_name)
            btn.setMinimumWidth(150)
            btn.setMaximumWidth(180)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, en=event_name, on=option_name, ores=option_results: 
                self._select_choice(en, on, ores)
            )
            choices_layout.addWidget(btn)
            self.choice_buttons[event_name][option_name] = btn
        
        row_layout.addWidget(choices_widget, stretch=0)
        
        # Arrow indicator
        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        row_layout.addWidget(arrow)
        
        # Result label with better styling
        result_frame = QFrame()
        result_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_input']};
            border-radius: 8px;
            padding: 8px;
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(12, 8, 12, 8)
        
        result_label = QLabel("")
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        result_label.setMinimumHeight(50)
        result_layout.addWidget(result_label)
        
        row_layout.addWidget(result_frame, stretch=1)
        self.result_labels[event_name] = result_label
        
        # Highlight existing selection
        if event_name in self.custom_choices:
            selected = self.custom_choices[event_name]
            if selected in self.choice_buttons[event_name]:
                self.choice_buttons[event_name][selected].setStyleSheet(
                    f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;"
                )
                if selected in option_results:
                    result_label.setText(option_results[selected].replace("\\r\\n", "\n").replace("\\n", "\n"))
        
        return row
    
    def _select_choice(self, event_name, option_name, option_results):
        """Select a choice"""
        # Reset all buttons
        for btn in self.choice_buttons[event_name].values():
            btn.setStyleSheet("")
        
        # Highlight selected
        self.choice_buttons[event_name][option_name].setStyleSheet(
            f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;"
        )
        
        # Update result
        result_text = option_results.get(option_name, "")
        self.result_labels[event_name].setText(result_text.replace("\\r\\n", "\n").replace("\\n", "\n"))
        
        # Store selection
        self.custom_choices[event_name] = option_name
        self._update_count()
    
    def _update_count(self):
        """Update selected count"""
        self.count_badge.setText(f"{len(self.custom_choices)} selected")
    
    def _clear_all(self):
        """Clear all selections"""
        for event_name, buttons in self.choice_buttons.items():
            for btn in buttons.values():
                btn.setStyleSheet("")
        
        for label in self.result_labels.values():
            label.setText("")
        
        self.custom_choices = {}
        self._update_count()
    
    def _save_choices(self):
        """Save custom choices"""
        try:
            os.makedirs(os.path.join("template", "events"), exist_ok=True)
            
            safe_name = self.uma_name.replace("/", "-").replace("\\", "-").replace(":", "-")
            filepath = os.path.join("template", "events", f"Events_{safe_name}.json")
            
            data = {
                "UmaName": self.uma_name,
                "UmaSlug": self.uma_slug,
                "CustomChoices": self.custom_choices
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Saved {len(self.custom_choices)} choices to {os.path.basename(filepath)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
