"""
Support Card Event Editor Window for PySide6 GUI - Enhanced Version
Shows support card events with search, styled choice buttons, and result preview.
Sorted by CardSlug with row numbers and vertical choice buttons.
"""

import json
import os
import qtawesome as qta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QWidget, QFrame, QMessageBox, QCompleter
)
from PySide6.QtCore import Qt, QTimer, QStringListModel, QSize
from PySide6.QtGui import QPixmap, QStandardItemModel, QStandardItem, QIcon

from ..styles import COLORS, MAIN_STYLESHEET

# Path to support card images
SUPPORT_IMAGES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "supports")


class SupportEventWindow(QDialog):
    """Support card event choice editor with enhanced styling"""
    
    def __init__(self, parent, template_name, template_path=None):
        super().__init__(parent)
        self.template_name = template_name
        self.template_path = template_path or os.path.join(
            "template", "Events", "Supports", f"SupportCards_{template_name}.json"
        )
        self.all_events = []  # List of merged events {EventName, CardSlug, EventOptions}
        self.event_lookup = {}  # Display string -> (EventName, CardSlug)
        self.custom_choices = []  # List of {EventName, CardSlug, SelectedOption}
        self.event_widgets = {}  # unique_key -> widget info
        self.row_widgets_ordered = []  # Ordered list of (unique_key, row_widget) for numbering
        
        self.setWindowTitle(f"Support Card Events - {template_name}")
        self.setMinimumSize(950, 750)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._load_all_events()
        self._load_template()
        self._create_ui()
    
    def _load_all_events(self):
        """Load all support card events and merge options for same event"""
        try:
            with open('assets/events/support_card.json', 'r', encoding='utf-8') as f:
                raw_events = json.load(f)
            
            # Merge events with same EventName + CardSlug
            events_dict = {}  # key: (EventName, CardSlug) -> merged options
            
            for evt in raw_events:
                event_name = evt.get("EventName", "")
                card_slug = evt.get("CardSlug", "")
                opts = evt.get("EventOptions", {})
                
                key = (event_name, card_slug)
                if key not in events_dict:
                    events_dict[key] = {
                        "EventName": event_name,
                        "CardSlug": card_slug,
                        "EventOptions": {}
                    }
                
                # Merge options
                for opt_name, opt_result in opts.items():
                    if opt_name.strip():
                        events_dict[key]["EventOptions"][opt_name] = opt_result
            
            # Convert to list and filter events with options
            self.all_events = [
                evt for evt in events_dict.values()
                if evt["EventOptions"]
            ]
            
            # Build lookup for completer
            self.event_lookup = {}
            for evt in self.all_events:
                event_name = evt["EventName"]
                card_slug = evt["CardSlug"]
                # Create display string
                slug_display = card_slug[:25] + "..." if len(card_slug) > 25 else card_slug
                display = f"{event_name}  [{slug_display}]" if card_slug else event_name
                self.event_lookup[display] = (event_name, card_slug)
            
            # Build unique cards list
            self.unique_cards = sorted(list(set(evt["CardSlug"] for evt in self.all_events if evt.get("CardSlug"))))
            
        except Exception as e:
            print(f"Error loading events: {e}")
            self.all_events = []
            self.event_lookup = {}
            self.unique_cards = []
    
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
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon('fa5s.id-card', color=COLORS['accent_primary']).pixmap(QSize(24, 24)))
        header.addWidget(title_icon)
        title = QLabel(f"Support Events - {self.template_name}")
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
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 8, 12, 8)
        add_layout.setSpacing(12)
        
        # 1. Add Support Card row
        card_layout = QHBoxLayout()
        card_layout_label = QLabel("Add Support Card:")
        card_layout_label.setFixedWidth(130)
        card_layout.addWidget(card_layout_label)
        
        self.card_search_entry = QLineEdit()
        self.card_search_entry.setPlaceholderText("Type to search support cards...")
        self.card_search_entry.setMinimumWidth(500)
        self.card_search_entry.returnPressed.connect(self._add_card_events_from_completer)
        card_layout.addWidget(self.card_search_entry)
        
        # Setup completer for support cards with icons
        self.card_completer_model = QStandardItemModel()
        for card_slug in self.unique_cards:
            item = QStandardItem(card_slug)
            image_path = os.path.join(SUPPORT_IMAGES_PATH, f"{card_slug}.png")
            if os.path.exists(image_path):
                # Use QIcon for the item
                item.setIcon(QIcon(image_path))
            self.card_completer_model.appendRow(item)
            
        self.card_completer = QCompleter(self.card_completer_model, self)
        self.card_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.card_completer.setFilterMode(Qt.MatchContains)
        self.card_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.card_completer.setMaxVisibleItems(10)
        self.card_completer.activated.connect(self._on_card_completer_activated)
        
        # Style the completer popup to show icons nicely
        card_popup = self.card_completer.popup()
        card_popup.setIconSize(QSize(40, 40))
        card_popup.setStyleSheet(f"""
            QListView {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['accent_primary']};
                border-radius: 8px;
                padding: 4px;
                outline: none;
                color: {COLORS['text_primary']};
            }}
            QListView::item {{
                padding: 4px;
                border-radius: 4px;
            }}
            QListView::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QListView::item:selected {{
                background-color: {COLORS['accent_primary']};
                color: white;
            }}
        """)
        
        self.card_search_entry.setCompleter(self.card_completer)
        
        add_card_btn = QPushButton(" Add Card Events")
        add_card_btn.setIcon(qta.icon('fa5s.layer-group', color='white'))
        add_card_btn.setIconSize(QSize(16, 16))
        add_card_btn.setStyleSheet(f"""
            background-color: {COLORS['accent_blue']};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
        """)
        add_card_btn.clicked.connect(self._add_card_events_from_completer)
        card_layout.addWidget(add_card_btn)
        add_layout.addLayout(card_layout)
        
        # 2. Add Event row
        event_layout = QHBoxLayout()
        event_layout_label = QLabel("Add Single Event:")
        event_layout_label.setFixedWidth(130)
        event_layout.addWidget(event_layout_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Type to search events...")
        self.search_entry.setMinimumWidth(500)
        self.search_entry.returnPressed.connect(self._add_event_from_completer)
        event_layout.addWidget(self.search_entry)
        
        # Setup completer with all event display strings
        display_strings = sorted(self.event_lookup.keys(), key=lambda x: (self.event_lookup[x][1], x))
        self.completer_model = QStringListModel(display_strings)
        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setMaxVisibleItems(15)
        self.completer.activated.connect(self._on_completer_activated)
        
        # Style the completer popup
        popup = self.completer.popup()
        popup.setStyleSheet(f"""
            QListView {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['accent_primary']};
                border-radius: 8px;
                padding: 4px;
                outline: none;
                color: {COLORS['text_primary']};
            }}
            QListView::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QListView::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QListView::item:selected {{
                background-color: {COLORS['accent_primary']};
                color: white;
            }}
        """)
        
        self.search_entry.setCompleter(self.completer)
        
        add_btn = QPushButton(" Add Event")
        add_btn.setIcon(qta.icon('fa5s.plus-circle', color='white'))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.setStyleSheet(f"""
            background-color: {COLORS['accent_red']};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
        """)
        add_btn.clicked.connect(self._add_event_from_completer)
        event_layout.addWidget(add_btn)
        add_layout.addLayout(event_layout)
        
        layout.addWidget(add_frame)
        
        # Info
        info = QLabel("Click a choice button to select it. Results are shown on the right.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(info)
        
        # Column headers
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_input']};
            border-radius: 8px;
            padding: 4px;
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)
        
        # No. header
        no_header = QLabel("No.")
        no_header.setFixedWidth(35)
        no_header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        header_layout.addWidget(no_header)
        
        # Source header
        source_header = QLabel("Source")
        source_header.setFixedWidth(80)
        source_header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        header_layout.addWidget(source_header)
        
        # Event name header
        name_header = QLabel("Event Name")
        name_header.setMinimumWidth(180)
        name_header.setMaximumWidth(200)
        name_header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        header_layout.addWidget(name_header)
        
        # Choices header
        choices_header = QLabel("Choices")
        choices_header.setFixedWidth(160)
        choices_header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        header_layout.addWidget(choices_header)
        
        # Arrow spacer
        arrow_spacer = QLabel("")
        arrow_spacer.setFixedWidth(30)
        header_layout.addWidget(arrow_spacer)
        
        # Result header
        result_header = QLabel("Result Preview")
        result_header.setFixedWidth(200)
        result_header.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        header_layout.addWidget(result_header)
        
        # Spacer for delete button
        header_layout.addSpacing(35)
        
        layout.addWidget(header_frame)
        
        # Scrollable events area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.scroll_widget = QWidget()
        self.events_layout = QVBoxLayout(self.scroll_widget)
        self.events_layout.setSpacing(8)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        
        # Load existing choices (sorted by CardSlug)
        self._refresh_event_list()
        
        self.events_layout.addStretch()
        scroll.setWidget(self.scroll_widget)
        self.scroll = scroll
        layout.addWidget(scroll)
        
        # Deck Preview section
        deck_label = QLabel("Deck Preview:")
        deck_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: bold; margin-top: 8px;")
        layout.addWidget(deck_label)
        
        # Horizontal scroll area for card thumbnails
        self.deck_scroll = QScrollArea()
        self.deck_scroll.setWidgetResizable(True)
        self.deck_scroll.setFixedHeight(100)
        self.deck_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.deck_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.deck_scroll.setStyleSheet("background-color: #2a2a2a; border-radius: 8px;")
        
        self.deck_container = QWidget()
        self.deck_container.setStyleSheet("background: transparent;")
        self.deck_layout = QHBoxLayout(self.deck_container)
        self.deck_layout.setContentsMargins(8, 8, 8, 8)
        self.deck_layout.setSpacing(8)
        self.deck_layout.addStretch()
        self.deck_scroll.setWidget(self.deck_container)
        
        layout.addWidget(self.deck_scroll)

        self._update_deck_preview()
        
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
    
    def _update_deck_preview(self):
        """Update the deck preview with unique support cards from current choices"""
        # Clear existing
        while self.deck_layout.count():
            item = self.deck_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Get unique card slugs from current choices
        current_deck_slugs = []
        seen = set()
        for c in self.custom_choices:
            slug = c.get("CardSlug")
            if slug and slug not in seen:
                seen.add(slug)
                current_deck_slugs.append(slug)
                
        # Sort them by slug
        current_deck_slugs.sort()
        
        if not current_deck_slugs:
            empty_label = QLabel("No support cards added yet.")
            empty_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
            self.deck_layout.addWidget(empty_label)
            self.deck_layout.addStretch()
            return
            
        for card_slug in current_deck_slugs:
            card_widget = QLabel()
            card_widget.setToolTip(card_slug)
            
            image_path = os.path.join(SUPPORT_IMAGES_PATH, f"{card_slug}.png")
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                    card_widget.setPixmap(scaled)
                else:
                    card_widget.setText(card_slug[:10])
            else:
                card_widget.setText(card_slug[:10])
                card_widget.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 8px; background: #3a3a3a; border-radius: 4px;")
                
            self.deck_layout.addWidget(card_widget)
            
        self.deck_layout.addStretch()

    def _on_card_completer_activated(self, text):
        """Handle card completer selection"""
        self._add_card_events(text)
        
    def _add_card_events_from_completer(self):
        """Add events for card from search entry text"""
        text = self.card_search_entry.text().strip()
        if not text:
            return
        
        # Find exact match
        if text in self.unique_cards:
            self._add_card_events(text)
            return
            
        # Try partial match (case-insensitive)
        for card_slug in self.unique_cards:
            if text.lower() in card_slug.lower():
                self._add_card_events(card_slug)
                return
                
        QMessageBox.warning(self, "Not Found", f"Support Card '{text}' not found.")
        
    def _add_card_events(self, card_slug):
        """Add all events for a given support card"""
        events_added = 0
        
        for evt in self.all_events:
            if evt.get("CardSlug") == card_slug:
                event_name = evt.get("EventName")
                unique_key = f"{event_name}|{card_slug}"
                
                # Check if it's already added
                exists = False
                for choice in self.custom_choices:
                    if choice.get("EventName") == event_name and choice.get("CardSlug") == card_slug:
                        exists = True
                        break
                        
                if not exists:
                    self.custom_choices.append({
                        "EventName": event_name,
                        "CardSlug": card_slug,
                        "SelectedOption": ""
                    })
                    events_added += 1
                    
        if events_added > 0:
            self._resort_and_rebuild()
            self._update_count()
            self.card_search_entry.clear()
            QMessageBox.information(
                self, 
                "Success", 
                f"Added {events_added} event(s) for '{card_slug}'."
            )
        else:
            QMessageBox.information(
                self, 
                "Already Present", 
                f"All events for '{card_slug}' are already added."
            )

    def _on_completer_activated(self, text):
        """Handle completer selection"""
        if text in self.event_lookup:
            event_name, card_slug = self.event_lookup[text]
            self._add_event_by_name(event_name, card_slug)
    
    def _add_event_from_completer(self):
        """Add event from search entry text"""
        text = self.search_entry.text().strip()
        if not text:
            return
        
        # Check if it's a display string from completer
        if text in self.event_lookup:
            event_name, card_slug = self.event_lookup[text]
            self._add_event_by_name(event_name, card_slug)
            return
        
        # Try to find event by name only
        for evt in self.all_events:
            if evt.get("EventName") == text:
                self._add_event_by_name(evt["EventName"], evt["CardSlug"])
                return
        
        # Try partial match
        for evt in self.all_events:
            if text.lower() in evt.get("EventName", "").lower():
                self._add_event_by_name(evt["EventName"], evt["CardSlug"])
                return
        
        QMessageBox.warning(self, "Not Found", f"Event '{text}' not found.\nPlease select from the dropdown list.")
    
    def _refresh_event_list(self):
        """Refresh events display sorted by CardSlug"""
        # Sort custom_choices by CardSlug
        self.custom_choices.sort(key=lambda x: (x.get("CardSlug", ""), x.get("EventName", "")))
        
        for choice in self.custom_choices:
            self._add_event_row(choice)
        
        self._update_row_numbers()
    
    def _find_event_data(self, event_name, card_slug):
        """Find merged event data by name and card_slug"""
        for evt in self.all_events:
            if evt.get("EventName") == event_name:
                if not card_slug or evt.get("CardSlug") == card_slug:
                    return evt
        return None
    
    def _add_event_row(self, choice_data):
        """Add an event row with horizontal choice buttons"""
        event_name = choice_data.get("EventName", "")
        card_slug = choice_data.get("CardSlug", "")
        selected_option = choice_data.get("SelectedOption", "")
        unique_key = f"{event_name}|{card_slug}"
        
        # Find merged event data
        event_data = self._find_event_data(event_name, card_slug)
        
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)
        row_layout.setSpacing(10)
        
        # Row number label
        row_num_label = QLabel("1")
        row_num_label.setFixedWidth(35)
        row_num_label.setAlignment(Qt.AlignCenter)
        row_num_label.setStyleSheet(f"""
            background-color: {COLORS['bg_input']};
            color: {COLORS['text_secondary']};
            padding: 4px;
            border-radius: 4px;
            font-weight: bold;
        """)
        row_layout.addWidget(row_num_label)
        
        # Source image
        source_img = QLabel()
        source_img.setFixedSize(80, 80)
        source_img.setAlignment(Qt.AlignCenter)
        source_img.setToolTip(card_slug)
        source_img.setStyleSheet(f"""
            background-color: {COLORS['accent_primary']};
            border-radius: 8px;
        """)
        
        # Try to load support card image
        image_path = os.path.join(SUPPORT_IMAGES_PATH, f"{card_slug}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            source_img.setPixmap(scaled_pixmap)
        else:
            # Fallback to text if image not found
            source_text = card_slug[:10] if len(card_slug) > 10 else card_slug or "?"
            source_img.setText(source_text)
            source_img.setStyleSheet(f"""
                background-color: {COLORS['accent_primary']};
                color: white;
                border-radius: 8px;
                font-size: 8px;
            """)
        
        row_layout.addWidget(source_img)
        
        # Event name
        name_label = QLabel(event_name)
        name_label.setWordWrap(True)
        name_label.setMinimumWidth(180)
        name_label.setMaximumWidth(200)
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(name_label)
        
        # Choices - Vertical layout with buttons
        choices_widget = QWidget()
        choices_layout = QVBoxLayout(choices_widget)
        choices_layout.setContentsMargins(0, 0, 0, 0)
        choices_layout.setSpacing(4)
        
        choice_buttons = {}
        if event_data:
            options = event_data.get("EventOptions", {})
            # Sort options: Top, Middle, Bottom, then others
            option_order = {"Top Option": 0, "Middle Option": 1, "Bottom Option": 2}
            sorted_options = sorted(
                [(k, v) for k, v in options.items() if k.strip()],
                key=lambda x: (option_order.get(x[0], 99), x[0])
            )
            
            # Create buttons for each option
            for i, (option_name, result) in enumerate(sorted_options):
                btn = QPushButton(option_name)
                btn.setFixedWidth(140)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setToolTip(result[:100] + "..." if len(result) > 100 else result)
                btn.clicked.connect(
                    lambda checked, uk=unique_key, on=option_name, res=result:
                    self._select_choice(uk, on, res)
                )
                choices_layout.addWidget(btn)
                choice_buttons[option_name] = btn
                
                if option_name == selected_option:
                    btn.setStyleSheet(f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;")
        
        choices_widget.setFixedWidth(160)
        row_layout.addWidget(choices_widget)
        
        # Arrow
        arrow_label = QLabel()
        arrow_label.setPixmap(qta.icon('fa5s.arrow-right', color=COLORS['text_secondary']).pixmap(QSize(16, 16)))
        arrow_label.setFixedWidth(30)
        arrow_label.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(arrow_label)
        
        # Result preview
        result_frame = QFrame()
        result_frame.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 8px;")
        result_frame.setFixedWidth(200)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(8, 4, 8, 4)
        
        result_label = QLabel("")
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        result_label.setMaximumHeight(70)
        if event_data and selected_option:
            options = event_data.get("EventOptions", {})
            if selected_option in options:
                result_text = options[selected_option].replace("\\r\\n", "\n").replace("\r\n", "\n").replace("\\n", "\n")
                if len(result_text) > 150:
                    result_text = result_text[:150] + "..."
                result_label.setText(result_text)
        result_layout.addWidget(result_label)
        row_layout.addWidget(result_frame)
        
        # Delete button with qtawesome icon
        del_btn = QPushButton()
        del_btn.setIcon(qta.icon('fa5s.trash-alt', color='white'))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(f"""
            background-color: {COLORS['accent_red']};
            border-radius: 14px;
        """)
        del_btn.clicked.connect(lambda: self._remove_event(unique_key, row))
        row_layout.addWidget(del_btn)
        
        # Insert before stretch
        self.events_layout.insertWidget(self.events_layout.count() - 1, row)
        
        self.event_widgets[unique_key] = {
            'row': row,
            'buttons': choice_buttons,
            'result': result_label,
            'event_data': event_data,
            'row_num_label': row_num_label
        }
        self.row_widgets_ordered.append((unique_key, row))
    
    def _update_row_numbers(self):
        """Update all row numbers after add/remove"""
        for i, (unique_key, _) in enumerate(self.row_widgets_ordered):
            if unique_key in self.event_widgets:
                self.event_widgets[unique_key]['row_num_label'].setText(str(i + 1))
    
    def _select_choice(self, unique_key, option_name, result):
        """Select a choice - only one can be selected at a time"""
        if unique_key not in self.event_widgets:
            return
        
        widgets = self.event_widgets[unique_key]
        
        # Reset ALL buttons to default style (explicit reset)
        default_btn_style = f"""
            background-color: {COLORS['bg_input']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: normal;
        """
        for btn in widgets['buttons'].values():
            btn.setStyleSheet(default_btn_style)
        
        # Highlight ONLY the selected button
        if option_name in widgets['buttons']:
            widgets['buttons'][option_name].setStyleSheet(
                f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold; border-radius: 8px; padding: 8px 16px;"
            )
        
        # Update result (truncated for smaller column)
        result_text = result.replace("\\r\\n", "\n").replace("\r\n", "\n").replace("\\n", "\n")
        if len(result_text) > 150:
            result_text = result_text[:150] + "..."
        widgets['result'].setText(result_text)
        
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
    
    def _add_event_by_name(self, event_name, card_slug):
        """Add event by name and card_slug, handling duplicates"""
        unique_key = f"{event_name}|{card_slug}"
        
        # Check for duplicate
        if unique_key in self.event_widgets:
            # Find row number
            row_num = 1
            for i, (key, _) in enumerate(self.row_widgets_ordered):
                if key == unique_key:
                    row_num = i + 1
                    break
            
            # Scroll to existing row
            row_widget = self.event_widgets[unique_key]['row']
            self.scroll.ensureWidgetVisible(row_widget, 50, 50)
            
            # Flash highlight
            original_style = row_widget.styleSheet()
            row_widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['accent_orange']};
                    border-radius: 10px;
                    border: 2px solid {COLORS['accent_orange']};
                }}
            """)
            QTimer.singleShot(800, lambda: row_widget.setStyleSheet(original_style))
            
            QMessageBox.information(
                self, 
                "Duplicate Event", 
                f"This event already exists at Row #{row_num}.\nScrolled to the existing entry."
            )
            self.search_entry.clear()
            return
        
        # Find event data
        event = self._find_event_data(event_name, card_slug)
        
        if not event:
            QMessageBox.warning(self, "Not Found", f"Event '{event_name}' not found.")
            return
        
        choice_data = {
            "EventName": event_name,
            "CardSlug": card_slug,
            "SelectedOption": ""
        }
        self.custom_choices.append(choice_data)
        
        # Re-sort and rebuild for proper ordering
        self._resort_and_rebuild()
        
        self.search_entry.clear()
        self._update_count()
        
        # Scroll to new row
        new_key = f"{event_name}|{card_slug}"
        if new_key in self.event_widgets:
            QTimer.singleShot(100, lambda: self.scroll.ensureWidgetVisible(
                self.event_widgets[new_key]['row'], 50, 50
            ))
    
    def _resort_and_rebuild(self):
        """Re-sort all events and rebuild the list"""
        # Sort custom_choices by CardSlug
        self.custom_choices.sort(key=lambda x: (x.get("CardSlug", ""), x.get("EventName", "")))
        
        # Clear existing widgets
        for unique_key in list(self.event_widgets.keys()):
            if 'row' in self.event_widgets[unique_key]:
                self.event_widgets[unique_key]['row'].deleteLater()
        
        self.event_widgets.clear()
        self.row_widgets_ordered.clear()
        
        # Rebuild
        for choice in self.custom_choices:
            self._add_event_row(choice)
        
        self._update_row_numbers()
        if hasattr(self, 'deck_layout'):
            self._update_deck_preview()
    
    def _remove_event(self, unique_key, row_widget):
        """Remove an event"""
        event_name, card_slug = unique_key.split("|", 1)
        self.custom_choices = [
            c for c in self.custom_choices 
            if not (c.get("EventName") == event_name and c.get("CardSlug") == card_slug)
        ]
        
        if unique_key in self.event_widgets:
            del self.event_widgets[unique_key]
        
        # Remove from ordered list
        self.row_widgets_ordered = [(k, w) for k, w in self.row_widgets_ordered if k != unique_key]
        
        row_widget.deleteLater()
        self._update_row_numbers()
        self._update_count()
        if hasattr(self, 'deck_layout'):
            self._update_deck_preview()
    
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
