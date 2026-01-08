"""
Choice Editor Window for PySide6 GUI - Enhanced Version
Edits Good_choices/Bad_choices in event_priority.json with modern styling.
"""

import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QFrame,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import COLORS, MAIN_STYLESHEET


class ChoiceEditorWindow(QDialog):
    """Enhanced editor for Good/Bad event choices"""
    
    def __init__(self, parent, choice_type="Good"):
        """choice_type: "Good" or "Bad" """
        super().__init__(parent)
        self.choice_type = choice_type
        self.choice_key = f"{choice_type}_choices"
        self.event_file = "event_priority.json"
        self.choices = []
        
        self.setWindowTitle(f"Edit {choice_type} Choices")
        self.setMinimumSize(550, 500)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._load_choices()
        self._create_ui()
    
    def _load_choices(self):
        """Load existing choices"""
        if os.path.exists(self.event_file):
            try:
                with open(self.event_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.choices = data.get(self.choice_key, [])
            except:
                self.choices = []
    
    def _create_ui(self):
        """Create enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Color based on type
        primary_color = COLORS['accent_green'] if self.choice_type == "Good" else COLORS['accent_red']
        icon = "✓" if self.choice_type == "Good" else "✗"
        
        # Header
        header = QHBoxLayout()
        title = QLabel(f"{icon} Edit {self.choice_type} Choices")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {primary_color};")
        header.addWidget(title)
        header.addStretch()
        
        count_badge = QLabel(f"{len(self.choices)} items")
        count_badge.setStyleSheet(f"""
            background-color: {primary_color};
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
        """)
        self.count_badge = count_badge
        header.addWidget(count_badge)
        layout.addLayout(header)
        
        # Add choice section
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_card']};
            border-radius: 10px;
            padding: 8px;
        """)
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 8, 12, 8)
        
        self.choice_entry = QLineEdit()
        self.choice_entry.setPlaceholderText("Enter choice keyword...")
        self.choice_entry.returnPressed.connect(self._add_choice)
        add_layout.addWidget(self.choice_entry)
        
        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_choice)
        add_layout.addWidget(add_btn)
        layout.addWidget(add_frame)
        
        # Info text
        info = QLabel(f"Keywords that match {self.choice_type.lower()} event choices. Drag to reorder.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(info)
        
        # Choices list
        self.choice_list = QListWidget()
        self.choice_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.choice_list.setDefaultDropAction(Qt.MoveAction)
        self.choice_list.setSpacing(4)
        self.choice_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {primary_color};
                border-radius: 10px;
                padding: 10px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-radius: 8px;
                background-color: {COLORS['bg_input']};
                margin: 3px 0;
            }}
            QListWidget::item:selected {{
                background-color: {primary_color};
                color: white;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        
        for choice in self.choices:
            item = QListWidgetItem(choice)
            font = QFont()
            font.setPointSize(11)
            item.setFont(font)
            self.choice_list.addItem(item)
        
        layout.addWidget(self.choice_list)
        
        # Move/remove buttons
        btn_row = QHBoxLayout()
        
        move_up_btn = QPushButton("↑ Up")
        move_up_btn.clicked.connect(lambda: self._move_choice(-1))
        btn_row.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("↓ Down")
        move_down_btn.clicked.connect(lambda: self._move_choice(1))
        btn_row.addWidget(move_down_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_choice)
        btn_row.addWidget(remove_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # Save/cancel buttons
        footer = QHBoxLayout()
        footer.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_choices)
        footer.addWidget(save_btn)
        
        layout.addLayout(footer)
    
    def _add_choice(self):
        """Add new choice"""
        text = self.choice_entry.text().strip()
        if not text:
            return
        
        # Check duplicate
        for i in range(self.choice_list.count()):
            if self.choice_list.item(i).text().lower() == text.lower():
                QMessageBox.information(self, "Duplicate", f"'{text}' is already in the list.")
                return
        
        item = QListWidgetItem(text)
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.choice_list.addItem(item)
        self.choice_entry.clear()
        self._update_count()
    
    def _remove_choice(self):
        """Remove selected choice"""
        row = self.choice_list.currentRow()
        if row >= 0:
            self.choice_list.takeItem(row)
            self._update_count()
    
    def _move_choice(self, direction):
        """Move choice up or down"""
        row = self.choice_list.currentRow()
        if row < 0:
            return
        
        new_row = row + direction
        if 0 <= new_row < self.choice_list.count():
            item = self.choice_list.takeItem(row)
            self.choice_list.insertItem(new_row, item)
            self.choice_list.setCurrentRow(new_row)
    
    def _update_count(self):
        """Update item count"""
        self.count_badge.setText(f"{self.choice_list.count()} items")
    
    def _save_choices(self):
        """Save choices to event_priority.json"""
        try:
            # Gather choices from list
            choices = []
            for i in range(self.choice_list.count()):
                choices.append(self.choice_list.item(i).text())
            
            # Load existing data
            data = {}
            if os.path.exists(self.event_file):
                with open(self.event_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Update choices
            data[self.choice_key] = choices
            
            with open(self.event_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"✓ Saved {len(choices)} {self.choice_type.lower()} choices!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
