"""
Event Tab for PySide6 GUI
Contains event choice management, Uma events, and support card events.
Matches original GUI exactly.
"""

import json
import os
import glob
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QFrame, QScrollArea, QMessageBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class EventTab(QScrollArea):
    """Event configuration tab - matches original GUI"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        # Load data
        self.uma_data = self._load_uma_data()
        self.uma_names = ["All"] + sorted([uma.get("UmaName", "") for uma in self.uma_data])
        self.support_templates = self._load_support_templates()
        
        self._create_ui()
    
    def _load_uma_data(self):
        """Load Uma data from JSON"""
        try:
            with open('assets/events/uma_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _load_support_templates(self):
        """Load support card templates"""
        templates = []
        template_dir = os.path.join("template", "events")
        if os.path.exists(template_dir):
            for filepath in glob.glob(os.path.join(template_dir, "SupportCards_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        templates.append(data.get("TemplateName", os.path.basename(filepath)))
                except Exception:
                    pass
        return templates
    
    def _create_ui(self):
        """Create event tab UI matching original"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== Event Choice Management ====================
        choice_group = QGroupBox("Event Choice Management")
        choice_layout = QVBoxLayout(choice_group)
        choice_layout.setSpacing(12)
        
        # Good Choices
        good_row = QHBoxLayout()
        good_row.addWidget(QLabel("Good Choices:"))
        good_row.addStretch()
        good_btn = QPushButton("Open List")
        good_btn.setObjectName("primary")
        good_btn.clicked.connect(lambda: self._open_choice_window("Good_choices"))
        good_row.addWidget(good_btn)
        choice_layout.addLayout(good_row)
        
        # Bad Choices
        bad_row = QHBoxLayout()
        bad_row.addWidget(QLabel("Bad Choices:"))
        bad_row.addStretch()
        bad_btn = QPushButton("Open List")
        bad_btn.setObjectName("danger")
        bad_btn.clicked.connect(lambda: self._open_choice_window("Bad_choices"))
        bad_row.addWidget(bad_btn)
        choice_layout.addLayout(bad_row)
        
        layout.addWidget(choice_group)
        
        # ==================== Uma Events Management ====================
        uma_group = QGroupBox("Uma Events Management")
        uma_layout = QVBoxLayout(uma_group)
        uma_layout.setSpacing(12)
        
        uma_row = QHBoxLayout()
        uma_row.addWidget(QLabel("Uma Name:"))
        
        # Searchable combo with filter
        self.uma_combo = QComboBox()
        self.uma_combo.setEditable(True)
        self.uma_combo.setInsertPolicy(QComboBox.NoInsert)
        self.uma_combo.addItems(self.uma_names)
        self.uma_combo.setMinimumWidth(250)
        self.uma_combo.lineEdit().textChanged.connect(self._filter_uma)
        uma_row.addWidget(self.uma_combo)
        
        uma_edit_btn = QPushButton("Edit Custom Choices")
        uma_edit_btn.setObjectName("accent")
        uma_edit_btn.clicked.connect(self._open_uma_event_window)
        uma_row.addWidget(uma_edit_btn)
        
        uma_row.addStretch()
        uma_layout.addLayout(uma_row)
        
        info = QLabel("Select a specific Uma to edit their event choices. 'All' cannot be edited.")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        uma_layout.addWidget(info)
        
        layout.addWidget(uma_group)
        
        # ==================== Support Cards Event Management ====================
        support_group = QGroupBox("Support Cards Event Management")
        support_layout = QVBoxLayout(support_group)
        support_layout.setSpacing(12)
        
        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("Template:"))
        
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(250)
        if self.support_templates:
            self.template_combo.addItems(self.support_templates)
        else:
            self.template_combo.addItem("(No templates)")
        template_row.addWidget(self.template_combo)
        template_row.addStretch()
        support_layout.addLayout(template_row)
        
        btn_row = QHBoxLayout()
        
        add_btn = QPushButton("Add New")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_template)
        btn_row.addWidget(add_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_template)
        btn_row.addWidget(delete_btn)
        
        edit_btn = QPushButton("Edit Custom Choices")
        edit_btn.setObjectName("accent")
        edit_btn.clicked.connect(self._open_support_event_window)
        btn_row.addWidget(edit_btn)
        
        btn_row.addStretch()
        support_layout.addLayout(btn_row)
        
        layout.addWidget(support_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _filter_uma(self, text):
        """Filter Uma combo based on typed text"""
        try:
            self.uma_combo.lineEdit().textChanged.disconnect(self._filter_uma)
        except:
            pass
        
        try:
            search = text.lower()
            cursor_pos = self.uma_combo.lineEdit().cursorPosition()
            
            if not search:
                filtered = self.uma_names
            else:
                filtered = [n for n in self.uma_names if search in n.lower()]
            
            self.uma_combo.clear()
            self.uma_combo.addItems(filtered if filtered else self.uma_names)
            self.uma_combo.setEditText(text)
            self.uma_combo.lineEdit().setCursorPosition(cursor_pos)
        finally:
            try:
                self.uma_combo.lineEdit().textChanged.connect(self._filter_uma)
            except:
                pass
    
    def _open_choice_window(self, choice_type):
        """Open good/bad choice window"""
        # Extract choice type - "Good_choices" -> "Good" or "Bad_choices" -> "Bad"
        ctype = "Good" if "Good" in choice_type else "Bad"
        
        from .choice_editor_window import ChoiceEditorWindow
        dialog = ChoiceEditorWindow(self, ctype)
        dialog.exec()
    
    def _open_uma_event_window(self):
        """Open Uma event window"""
        selected = self.uma_combo.currentText()
        if selected == "All" or not selected:
            QMessageBox.warning(self, "Warning", "Please select a specific Uma.")
            return
        
        # Find Uma data
        uma_info = None
        for uma in self.uma_data:
            if uma.get("UmaName") == selected:
                uma_info = uma
                break
        
        if not uma_info:
            QMessageBox.warning(self, "Warning", f"Could not find data for: {selected}")
            return
        
        from .uma_event_window import UmaEventWindow
        dialog = UmaEventWindow(self, selected, uma_info)
        dialog.exec()
    
    def _add_template(self):
        """Add new support template"""
        name, ok = QInputDialog.getText(self, "New Template", "Enter template name:")
        if ok and name.strip():
            self.support_templates.append(name.strip())
            self.template_combo.addItem(name.strip())
            self.template_combo.setCurrentText(name.strip())
    
    def _delete_template(self):
        """Delete selected template"""
        selected = self.template_combo.currentText()
        if selected == "(No templates)":
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete template '{selected}'?")
        if reply == QMessageBox.Yes:
            idx = self.template_combo.currentIndex()
            self.template_combo.removeItem(idx)
            if selected in self.support_templates:
                self.support_templates.remove(selected)
    
    def _open_support_event_window(self):
        """Open support event window"""
        selected = self.template_combo.currentText()
        if selected == "(No templates)":
            QMessageBox.warning(self, "Warning", "Please create a template first.")
            return
        
        from .support_event_window import SupportEventWindow
        dialog = SupportEventWindow(self, selected)
        dialog.exec()
