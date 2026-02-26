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
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCompleter

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
        self.uma_slug_map = self._build_uma_slug_map()
        self.support_templates = self._load_support_templates()
        
        self._create_ui()
        self.load_config()
    
    def _load_uma_data(self):
        """Load Uma data from JSON"""
        try:
            with open('assets/events/uma_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _build_uma_slug_map(self):
        """Build a mapping from UmaName to UmaSlug"""
        slug_map = {}
        for uma in self.uma_data:
            name = uma.get("UmaName", "")
            slug = uma.get("UmaSlug", "")
            if name and slug:
                slug_map[name] = slug
        return slug_map
    
    def _load_support_templates(self):
        """Load support card templates"""
        templates = []
        template_dir = os.path.join("template", "Events", "Supports")
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
        
        # Main content layout (image on left, controls on right)
        uma_content_layout = QHBoxLayout()
        uma_content_layout.setSpacing(16)
        
        # Uma character image
        self.uma_image_label = QLabel()
        self.uma_image_label.setFixedSize(80, 80)
        self.uma_image_label.setStyleSheet(f"""
            background-color: {COLORS['bg_card']};
            border-radius: 8px;
            border: 2px solid {COLORS['border']};
        """)
        self.uma_image_label.setAlignment(Qt.AlignCenter)
        self.uma_image_label.setScaledContents(False)
        uma_content_layout.addWidget(self.uma_image_label)
        
        # Right side controls
        uma_controls_layout = QVBoxLayout()
        uma_controls_layout.setSpacing(8)
        
        uma_row = QHBoxLayout()
        uma_row.addWidget(QLabel("Uma Name:"))
        
        # Searchable combo - no prediction, filter on type, full list on click
        self.uma_combo = QComboBox()
        self.uma_combo.setEditable(True)
        self.uma_combo.setInsertPolicy(QComboBox.NoInsert)
        self.uma_combo.addItems(self.uma_names)
        self.uma_combo.setMinimumWidth(250)
        self.uma_combo.setStyleSheet(f"""
            QComboBox QAbstractItemView {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['bg_card']};
                selection-background-color: {COLORS['accent_primary']};
                selection-color: white;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}
        """)
        # Use completer for filtering (no inline completion)
        completer = QCompleter(self.uma_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.uma_combo.setCompleter(completer)
        self.uma_combo.currentTextChanged.connect(self._save_uma_selection)
        self.uma_combo.currentTextChanged.connect(self._update_uma_image)
        uma_row.addWidget(self.uma_combo)
        
        uma_edit_btn = QPushButton("Edit Custom Choices")
        uma_edit_btn.setObjectName("accent")
        uma_edit_btn.clicked.connect(self._open_uma_event_window)
        uma_row.addWidget(uma_edit_btn)
        
        uma_row.addStretch()
        uma_controls_layout.addLayout(uma_row)
        
        info = QLabel("Select a specific Uma to edit their event choices. 'All' cannot be edited.")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        uma_controls_layout.addWidget(info)
        
        uma_content_layout.addLayout(uma_controls_layout)
        uma_content_layout.addStretch()
        uma_layout.addLayout(uma_content_layout)
        
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
        self.template_combo.currentTextChanged.connect(self._save_template_selection)
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
        
        # Deck Preview section
        preview_label = QLabel("Deck Preview:")
        preview_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: bold; margin-top: 8px;")
        support_layout.addWidget(preview_label)
        
        # Horizontal scroll area for card thumbnails
        self.deck_scroll = QScrollArea()
        self.deck_scroll.setWidgetResizable(True)
        self.deck_scroll.setFixedHeight(100)
        self.deck_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.deck_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.deck_scroll.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")
        
        self.deck_container = QWidget()
        self.deck_layout = QHBoxLayout(self.deck_container)
        self.deck_layout.setContentsMargins(8, 8, 8, 8)
        self.deck_layout.setSpacing(8)
        self.deck_layout.addStretch()
        self.deck_scroll.setWidget(self.deck_container)
        
        support_layout.addWidget(self.deck_scroll)
        
        # Connect template change to preview update
        self.template_combo.currentTextChanged.connect(self._update_deck_preview)
        
        layout.addWidget(support_group)
        
        layout.addStretch()
        self.setWidget(container)
        
        # Initial preview update
        self._update_deck_preview()
    
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
        # Update preview after editing
        self._update_deck_preview()
    
    def _update_deck_preview(self):
        """Update deck preview with card images from selected template"""
        # Clear existing preview
        while self.deck_layout.count() > 0:
            item = self.deck_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        template_name = self.template_combo.currentText()
        if not template_name or template_name == "(No templates)":
            no_template = QLabel("No template selected")
            no_template.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.deck_layout.addWidget(no_template)
            self.deck_layout.addStretch()
            return
        
        # Load template file
        template_path = os.path.join("template", "events", "Supports", f"SupportCards_{template_name}.json")
        if not os.path.exists(template_path):
            no_file = QLabel(f"Template file not found")
            no_file.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.deck_layout.addWidget(no_file)
            self.deck_layout.addStretch()
            return
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
        except Exception:
            self.deck_layout.addWidget(QLabel("Failed to load template"))
            self.deck_layout.addStretch()
            return
        
        # Extract unique CardSlugs
        card_slugs = []
        seen = set()
        for choice in template_data.get("CustomChoices", []):
            slug = choice.get("CardSlug", "")
            if slug and slug not in seen:
                card_slugs.append(slug)
                seen.add(slug)
        
        if not card_slugs:
            no_cards = QLabel("No cards in template")
            no_cards.setStyleSheet(f"color: {COLORS['text_muted']};")
            self.deck_layout.addWidget(no_cards)
            self.deck_layout.addStretch()
            return
        
        # Load and display card images
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "supports")
        for slug in card_slugs:
            img_path = os.path.join(assets_dir, f"{slug}.png")
            
            card_widget = QLabel()
            card_widget.setToolTip(slug)
            
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                    card_widget.setPixmap(scaled)
                else:
                    card_widget.setText(slug.split('-')[-1][:10])
            else:
                # Show text fallback with card name
                card_widget.setText(slug.split('-')[-1][:10])
                card_widget.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 8px; background: #3a3a3a; border-radius: 4px;")
            
            self.deck_layout.addWidget(card_widget)
        
        self.deck_layout.addStretch()
    
    def _save_uma_selection(self, uma_name):
        """Save selected Uma name to config"""
        if uma_name and uma_name in self.uma_names:
            self.main_window.update_nested_config_value("events", "uma_event_file", uma_name)
            self.main_window.save_config()
    
    def _update_uma_image(self, uma_name=None):
        """Update the Uma character image based on selection"""
        if uma_name is None:
            uma_name = self.uma_combo.currentText()
        
        # Default placeholder if no Uma selected or "All"
        if not uma_name or uma_name == "All" or uma_name not in self.uma_slug_map:
            self.uma_image_label.clear()
            self.uma_image_label.setText("?")
            self.uma_image_label.setStyleSheet(f"""
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                border: 2px solid {COLORS['border']};
                color: {COLORS['text_muted']};
                font-size: 24px;
                font-weight: bold;
            """)
            return
        
        # Get the slug for this Uma
        slug = self.uma_slug_map.get(uma_name, "")
        if not slug:
            return
        
        # Look for character image
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "characters")
        img_path = os.path.join(assets_dir, f"{slug}.png")
        
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                # Scale to fit the label while maintaining aspect ratio
                scaled = pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.uma_image_label.setPixmap(scaled)
                self.uma_image_label.setStyleSheet(f"""
                    background-color: {COLORS['bg_card']};
                    border-radius: 8px;
                    border: 2px solid {COLORS['accent_primary']};
                """)
                return
        
        # Fallback: show first letter of Uma name
        self.uma_image_label.clear()
        self.uma_image_label.setText(uma_name[0] if uma_name else "?")
        self.uma_image_label.setStyleSheet(f"""
            background-color: {COLORS['bg_card']};
            border-radius: 8px;
            border: 2px solid {COLORS['border']};
            color: {COLORS['text_secondary']};
            font-size: 24px;
            font-weight: bold;
        """)
    
    def _save_template_selection(self, template_name):
        """Save selected template to config"""
        if template_name and template_name != "(No templates)":
            self.main_window.update_nested_config_value("events", "support_card_template", template_name)
            self.main_window.save_config()
            self._update_deck_preview()
    
    def load_config(self):
        """Load saved selections from config"""
        config = self.main_window.get_config()
        events = config.get("events", {})
        
        # Load uma selection
        uma_name = events.get("uma_event_file", "All")
        if uma_name in self.uma_names:
            self.uma_combo.setCurrentText(uma_name)
        
        # Update Uma image
        self._update_uma_image()
        
        # Load template selection
        template = events.get("support_card_template", "")
        if template and template in self.support_templates:
            self.template_combo.setCurrentText(template)

