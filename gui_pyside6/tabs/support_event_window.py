"""
Support Card Event Editor Window for PySide6 GUI - Enhanced Version
Shows support card events with search, styled choice buttons, and result preview.
"""

import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QWidget, QFrame, QMessageBox, QCompleter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import COLORS, MAIN_STYLESHEET


class SupportEventWindow(QDialog):
    """Support card event choice editor with enhanced styling"""
    
    def __init__(self, parent, template_name, template_path=None):
        super().__init__(parent)
        self.template_name = template_name
        self.template_path = template_path or os.path.join(
            "template", "events", f"SupportCards_{template_name}.json"
        )
        self.all_events = []
        self.custom_choices = []  # List of {EventName, CardSlug, SelectedOption}
        self.event_widgets = {}
        
        self.setWindowTitle(f"Support Card Events - {template_name}")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._load_all_events()
        self._load_template()
        self._create_ui()
    
    def _load_all_events(self):
        """Load all support card events"""
        try:
            with open('assets/events/support_card.json', 'r', encoding='utf-8') as f:
                raw_events = json.load(f)
            
            self.all_events = []
            for evt in raw_events:
                opts = evt.get("EventOptions", {})
                if any(k.strip() for k in opts.keys()):
                    self.all_events.append(evt)
        except:
            self.all_events = []
    
    def _load_template(self):
        """Load existing template"""
        if os.path.exists(self.template_path):
            try:
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_choices = data.get("CustomChoices", [])
            except:
                self.custom_choices = []
    
    def _create_ui(self):
        """Create enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(f"🎴 Support Events - {self.template_name}")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        
        count_badge = QLabel(f"{len(self.custom_choices)} events")
        count_badge.setStyleSheet(f"""
            background-color: {COLORS['accent_blue']};
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
        """)
        self.count_badge = count_badge
        header.addWidget(count_badge)
        layout.addLayout(header)
        
        # Search/add section
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_card']};
            border-radius: 10px;
            padding: 8px;
        """)
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 8, 12, 8)
        
        add_layout.addWidget(QLabel("Add Event:"))
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Type to search events...")
        self.search_entry.setMinimumWidth(450)
        
        # Autocomplete
        event_names = list(set(e.get("EventName", "") for e in self.all_events))
        completer = QCompleter(sorted(event_names))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.search_entry.setCompleter(completer)
        add_layout.addWidget(self.search_entry)
        
        add_btn = QPushButton("+ Add Event")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_event)
        add_layout.addWidget(add_btn)
        layout.addWidget(add_frame)
        
        # Info
        info = QLabel("Click a choice button to select it. Results are shown on the right.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(info)
        
        # Scrollable events area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.scroll_widget = QWidget()
        self.events_layout = QVBoxLayout(self.scroll_widget)
        self.events_layout.setSpacing(10)
        
        # Load existing choices
        self._refresh_event_list()
        
        self.events_layout.addStretch()
        scroll.setWidget(self.scroll_widget)
        layout.addWidget(scroll)
        
        # Footer buttons
        footer = QHBoxLayout()
        footer.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Template")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_template)
        footer.addWidget(save_btn)
        
        layout.addLayout(footer)
    
    def _refresh_event_list(self):
        """Refresh events display"""
        for choice in self.custom_choices:
            self._add_event_row(choice)
    
    def _add_event_row(self, choice_data):
        """Add an event row"""
        event_name = choice_data.get("EventName", "")
        card_slug = choice_data.get("CardSlug", "")
        selected_option = choice_data.get("SelectedOption", "")
        unique_key = f"{event_name}|{card_slug}"
        
        # Find event data
        event_data = None
        for evt in self.all_events:
            if evt.get("EventName") == event_name:
                if not card_slug or evt.get("CardSlug") == card_slug:
                    event_data = evt
                    break
        
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
        row_layout.setSpacing(12)
        
        # Source badge
        source_badge = QLabel(card_slug[:20] + "..." if len(card_slug) > 20 else card_slug or "?")
        source_badge.setStyleSheet(f"""
            background-color: {COLORS['accent_primary']};
            color: white;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 10px;
        """)
        source_badge.setMaximumWidth(100)
        row_layout.addWidget(source_badge)
        
        # Event name
        name_label = QLabel(event_name)
        name_label.setWordWrap(True)
        name_label.setMinimumWidth(180)
        name_label.setMaximumWidth(220)
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(name_label)
        
        # Choices
        choices_widget = QWidget()
        choices_layout = QVBoxLayout(choices_widget)
        choices_layout.setContentsMargins(0, 0, 0, 0)
        choices_layout.setSpacing(4)
        
        choice_buttons = {}
        if event_data:
            options = event_data.get("EventOptions", {})
            for option_name, result in options.items():
                if option_name.strip():
                    btn = QPushButton(option_name)
                    btn.setMaximumWidth(150)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(
                        lambda checked, uk=unique_key, on=option_name, res=result:
                        self._select_choice(uk, on, res)
                    )
                    choices_layout.addWidget(btn)
                    choice_buttons[option_name] = btn
                    
                    if option_name == selected_option:
                        btn.setStyleSheet(f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;")
        
        row_layout.addWidget(choices_widget)
        
        # Arrow
        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        row_layout.addWidget(arrow)
        
        # Result
        result_frame = QFrame()
        result_frame.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 8px;")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(12, 8, 12, 8)
        
        result_label = QLabel("")
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        if event_data and selected_option:
            options = event_data.get("EventOptions", {})
            if selected_option in options:
                result_label.setText(options[selected_option].replace("\\r\\n", "\n").replace("\\n", "\n"))
        result_layout.addWidget(result_label)
        row_layout.addWidget(result_frame, stretch=1)
        
        # Delete button
        del_btn = QPushButton("×")
        del_btn.setFixedSize(32, 32)
        del_btn.setStyleSheet(f"""
            background-color: {COLORS['accent_red']};
            color: white;
            border-radius: 16px;
            font-weight: bold;
            font-size: 16px;
        """)
        del_btn.clicked.connect(lambda: self._remove_event(unique_key, row))
        row_layout.addWidget(del_btn)
        
        self.events_layout.insertWidget(self.events_layout.count() - 1, row)
        
        self.event_widgets[unique_key] = {
            'row': row,
            'buttons': choice_buttons,
            'result': result_label,
            'event_data': event_data
        }
    
    def _select_choice(self, unique_key, option_name, result):
        """Select a choice"""
        if unique_key not in self.event_widgets:
            return
        
        widgets = self.event_widgets[unique_key]
        
        # Reset buttons
        for btn in widgets['buttons'].values():
            btn.setStyleSheet("")
        
        # Highlight selected
        if option_name in widgets['buttons']:
            widgets['buttons'][option_name].setStyleSheet(
                f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;"
            )
        
        # Update result
        widgets['result'].setText(result.replace("\\r\\n", "\n").replace("\\n", "\n"))
        
        # Update custom_choices
        event_name, card_slug = unique_key.split("|", 1)
        for choice in self.custom_choices:
            if choice.get("EventName") == event_name and choice.get("CardSlug") == card_slug:
                choice["SelectedOption"] = option_name
                return
        
        self.custom_choices.append({
            "EventName": event_name,
            "CardSlug": card_slug,
            "SelectedOption": option_name
        })
    
    def _add_event(self):
        """Add event from search"""
        event_name = self.search_entry.text().strip()
        if not event_name:
            return
        
        # Find event
        event = None
        for e in self.all_events:
            if e.get("EventName") == event_name:
                event = e
                break
        
        if not event:
            QMessageBox.warning(self, "Not Found", f"Event '{event_name}' not found.")
            return
        
        card_slug = event.get("CardSlug", "")
        unique_key = f"{event_name}|{card_slug}"
        
        if unique_key in self.event_widgets:
            QMessageBox.information(self, "Duplicate", "This event is already in the list.")
            return
        
        choice_data = {
            "EventName": event_name,
            "CardSlug": card_slug,
            "SelectedOption": ""
        }
        self.custom_choices.append(choice_data)
        self._add_event_row(choice_data)
        self.search_entry.clear()
        self._update_count()
    
    def _remove_event(self, unique_key, row_widget):
        """Remove an event"""
        event_name, card_slug = unique_key.split("|", 1)
        self.custom_choices = [
            c for c in self.custom_choices 
            if not (c.get("EventName") == event_name and c.get("CardSlug") == card_slug)
        ]
        
        if unique_key in self.event_widgets:
            del self.event_widgets[unique_key]
        
        row_widget.deleteLater()
        self._update_count()
    
    def _update_count(self):
        """Update event count"""
        self.count_badge.setText(f"{len(self.custom_choices)} events")
    
    def _save_template(self):
        """Save template"""
        try:
            os.makedirs(os.path.dirname(self.template_path), exist_ok=True)
            
            data = {
                "TemplateName": self.template_name,
                "CustomChoices": self.custom_choices
            }
            
            with open(self.template_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"✓ Saved {len(self.custom_choices)} events to {os.path.basename(self.template_path)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
