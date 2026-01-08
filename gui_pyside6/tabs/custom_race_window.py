"""
Custom Race Editor Window for PySide6 GUI
Shows all racing periods with race selection dropdowns and filters.
Uses clean_race_data.json for race data.
Enhanced PySide6 version with better styling and details.
"""

import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QWidget, QFrame, QGridLayout, QCheckBox, QGroupBox,
    QMessageBox, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import COLORS, MAIN_STYLESHEET


class CustomRaceWindow(QDialog):
    """Custom race schedule editor with period rows and filters"""
    
    def __init__(self, parent, race_file_path):
        super().__init__(parent)
        self.race_file = race_file_path
        self.all_races = {}
        self.period_order = []
        self.selections = {}
        self.row_widgets = {}
        
        self.setWindowTitle("Custom Race List")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._load_races()
        self._create_ui()
    
    def _load_races(self):
        """Load all races and current selections"""
        try:
            # Load all available races from clean_race_data.json
            with open('assets/races/clean_race_data.json', 'r', encoding='utf-8') as f:
                self.all_races = json.load(f)
                # Period order is the keys of the dict
                self.period_order = list(self.all_races.keys())
        except Exception as e:
            print(f"Failed to load race data: {e}")
            self.all_races = {}
            self.period_order = []
        
        # Load current selections
        if os.path.exists(self.race_file):
            try:
                with open(self.race_file, 'r', encoding='utf-8') as f:
                    self.selections = json.load(f)
            except:
                self.selections = {}
    
    def _create_ui(self):
        """Create UI with enhanced PySide6 features"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with title and count
        header = QHBoxLayout()
        title = QLabel("Custom Race Schedule")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        header.addWidget(title)
        
        count_label = QLabel(f"{len(self.period_order)} periods available")
        count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header.addStretch()
        header.addWidget(count_label)
        layout.addLayout(header)
        
        # Filters in a stylish group box
        filter_group = QGroupBox("Race Filters")
        filter_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {COLORS['accent_primary']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                color: {COLORS['accent_primary']};
            }}
        """)
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setSpacing(8)
        
        # Grade filter row with styled checkboxes
        grades_row = QHBoxLayout()
        grades_row.addWidget(QLabel("Grades:"))
        grades_row.addSpacing(20)
        self.grade_checks = {}
        grade_colors = {'G1': '#FFD700', 'G2': '#C0C0C0', 'G3': '#CD7F32', 'OP': '#90EE90', 'Pre-OP': '#87CEEB'}
        for grade in ['G1', 'G2', 'G3', 'OP', 'Pre-OP']:
            cb = QCheckBox(grade)
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    padding: 4px 8px;
                    border-radius: 4px;
                    background: {grade_colors.get(grade, '#666')};
                    color: #1a1a1a;
                    font-weight: bold;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                }}
            """)
            cb.stateChanged.connect(self._on_filter_change)
            self.grade_checks[grade] = cb
            grades_row.addWidget(cb)
        grades_row.addStretch()
        filter_layout.addLayout(grades_row)
        
        # Surface filter row
        surface_row = QHBoxLayout()
        surface_row.addWidget(QLabel("Surface:"))
        surface_row.addSpacing(20)
        self.track_checks = {}
        for track in ['Turf', 'Dirt']:
            cb = QCheckBox(track)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_change)
            self.track_checks[track] = cb
            surface_row.addWidget(cb)
        surface_row.addStretch()
        filter_layout.addLayout(surface_row)
        
        # Distance filter row
        dist_row = QHBoxLayout()
        dist_row.addWidget(QLabel("Distance:"))
        dist_row.addSpacing(20)
        self.dist_checks = {}
        for dist in ['Sprint', 'Mile', 'Medium', 'Long']:
            cb = QCheckBox(dist)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_change)
            self.dist_checks[dist] = cb
            dist_row.addWidget(cb)
        dist_row.addStretch()
        filter_layout.addLayout(dist_row)
        
        layout.addWidget(filter_group)
        
        # Scrollable periods area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
            }}
        """)
        
        scroll_widget = QWidget()
        self.periods_layout = QVBoxLayout(scroll_widget)
        self.periods_layout.setSpacing(6)
        self.periods_layout.setContentsMargins(0, 0, 0, 0)
        
        # Build period rows
        self._build_period_rows()
        
        self.periods_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Footer buttons
        btn_row = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)
        
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_races)
        btn_row.addWidget(save_btn)
        
        layout.addLayout(btn_row)
    
    def _build_period_rows(self):
        """Build rows for each period"""
        # Clear existing
        while self.periods_layout.count() > 0:
            item = self.periods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.row_widgets = {}
        
        for period in self.period_order:
            row_widget = self._create_period_row(period)
            self.periods_layout.addWidget(row_widget)
    
    def _create_period_row(self, period):
        """Create a row with period label, race dropdown, and details"""
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 8px;
            }}
            QFrame:hover {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)
        row_layout.setSpacing(12)
        
        # Period label (fixed width for alignment)
        period_label = QLabel(period)
        period_label.setMinimumWidth(200)
        period_label.setMaximumWidth(200)
        period_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(period_label)
        
        # Race dropdown
        combo = QComboBox()
        combo.setMinimumWidth(280)
        combo.setMaximumWidth(280)
        self._populate_race_combo(combo, period)
        
        # Set current selection
        current = self.selections.get(period, "")
        if current:
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        
        combo.currentTextChanged.connect(lambda text, p=period: self._on_race_changed(p, text))
        row_layout.addWidget(combo)
        
        # Details panel (expands to fill)
        details_frame = QFrame()
        details_frame.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 6px; padding: 4px;")
        details_layout = QHBoxLayout(details_frame)
        details_layout.setContentsMargins(8, 4, 8, 4)
        details_layout.setSpacing(16)
        
        detail_labels = {}
        for key, width in [('grade', 50), ('surface', 50), ('distance_type', 70), ('distance_meters', 60), ('racetrack', 80), ('fans', 60)]:
            lbl = QLabel("")
            lbl.setMinimumWidth(width)
            lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
            details_layout.addWidget(lbl)
            detail_labels[key] = lbl
        
        details_layout.addStretch()
        row_layout.addWidget(details_frame, stretch=1)
        
        self.row_widgets[period] = {
            'combo': combo,
            'details': detail_labels
        }
        
        # Update details for current selection
        self._update_row_details(period)
        
        return row
    
    def _populate_race_combo(self, combo, period):
        """Populate combo with filtered race options"""
        combo.clear()
        combo.addItem("")  # Empty option
        
        races = self.all_races.get(period, {})
        options = []
        
        grade_rank = {'G1': 5, 'G2': 4, 'G3': 3, 'OP': 2, 'Pre-OP': 1}
        
        for name, race_data in races.items():
            if isinstance(race_data, dict) and self._race_passes_filter(race_data):
                rank = grade_rank.get(race_data.get('grade', ''), 0)
                options.append((name, rank, race_data.get('grade', '')))
        
        # Sort by grade rank descending, then name
        options.sort(key=lambda x: (-x[1], x[0]))
        
        for name, _, grade in options:
            combo.addItem(name)
    
    def _race_passes_filter(self, race_data):
        """Check if race passes current filters"""
        grade = race_data.get('grade', '')
        surface = race_data.get('surface', '')
        dist_type = race_data.get('distance_type', '')
        
        if grade and grade in self.grade_checks and not self.grade_checks[grade].isChecked():
            return False
        if surface and surface in self.track_checks and not self.track_checks[surface].isChecked():
            return False
        if dist_type and dist_type in self.dist_checks and not self.dist_checks[dist_type].isChecked():
            return False
        
        return True
    
    def _on_filter_change(self):
        """Handle filter change - refresh all dropdowns"""
        for period, widgets in self.row_widgets.items():
            combo = widgets['combo']
            current = combo.currentText()
            self._populate_race_combo(combo, period)
            
            # Keep selection if valid
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentIndex(0)
    
    def _on_race_changed(self, period, race_name):
        """Handle race selection"""
        self.selections[period] = race_name if race_name else ""
        self._update_row_details(period)
    
    def _update_row_details(self, period):
        """Update details labels"""
        if period not in self.row_widgets:
            return
        
        widgets = self.row_widgets[period]
        details = widgets['details']
        race_name = widgets['combo'].currentText()
        
        if not race_name:
            for lbl in details.values():
                lbl.setText("")
            return
        
        # Find race data
        races = self.all_races.get(period, {})
        race_data = races.get(race_name, {})
        
        details['grade'].setText(race_data.get('grade', ''))
        details['surface'].setText(race_data.get('surface', ''))
        details['distance_type'].setText(race_data.get('distance_type', ''))
        meters = race_data.get('distance_meters', '')
        details['distance_meters'].setText(f"{meters}m" if meters else "")
        details['racetrack'].setText(race_data.get('racetrack', ''))
        fans = race_data.get('fans', '')
        details['fans'].setText(f"👥{fans}" if fans else "")
        
        # Color the grade
        grade = race_data.get('grade', '')
        grade_colors = {'G1': '#FFD700', 'G2': '#C0C0C0', 'G3': '#CD7F32', 'OP': '#90EE90', 'Pre-OP': '#87CEEB'}
        if grade in grade_colors:
            details['grade'].setStyleSheet(f"color: {grade_colors[grade]}; font-weight: bold;")
    
    def _clear_all(self):
        """Clear all selections"""
        for period, widgets in self.row_widgets.items():
            widgets['combo'].setCurrentIndex(0)
        self.selections = {}
    
    def _save_races(self):
        """Save race selections"""
        try:
            to_save = {k: v for k, v in self.selections.items() if v}
            
            os.makedirs(os.path.dirname(self.race_file), exist_ok=True)
            with open(self.race_file, 'w', encoding='utf-8') as f:
                json.dump(to_save, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Saved", f"Saved {len(to_save)} race selections to {os.path.basename(self.race_file)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
