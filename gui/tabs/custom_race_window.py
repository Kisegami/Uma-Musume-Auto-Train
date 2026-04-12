"""
Custom Race Editor Window for PySide6 GUI.
Shows all racing periods with race selection dropdowns and per-race Glowstick toggles.
"""

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..styles import COLORS, MAIN_STYLESHEET


class CustomRaceWindow(QDialog):
    """Custom race schedule editor with period rows and filters."""

    def __init__(self, parent, race_file_path):
        super().__init__(parent)
        self.race_file = race_file_path
        self.all_races = {}
        self.period_order = []
        self.selections = {}
        self.row_widgets = {}

        self.setWindowTitle("Custom Race List")
        self.setMinimumSize(1180, 750)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._load_races()
        self._create_ui()

    def _normalize_selection(self, value):
        if isinstance(value, dict):
            return {
                "race": value.get("race", ""),
                "use_glowstick": bool(value.get("use_glowstick", False)),
            }
        if isinstance(value, str):
            return {"race": value, "use_glowstick": False}
        return {"race": "", "use_glowstick": False}

    def _load_races(self):
        try:
            with open("assets/races/clean_race_data.json", "r", encoding="utf-8") as f:
                self.all_races = json.load(f)
                self.period_order = list(self.all_races.keys())
        except Exception as e:
            print(f"Failed to load race data: {e}")
            self.all_races = {}
            self.period_order = []

        if os.path.exists(self.race_file):
            try:
                with open(self.race_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.selections = {period: self._normalize_selection(value) for period, value in raw.items()}
            except Exception:
                self.selections = {}

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Custom Race Schedule")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        header.addWidget(title)
        count_label = QLabel(f"{len(self.period_order)} periods available")
        count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header.addStretch()
        header.addWidget(count_label)
        layout.addLayout(header)

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

        grades_row = QHBoxLayout()
        grades_row.addWidget(QLabel("Grades:"))
        grades_row.addSpacing(20)
        self.grade_checks = {}
        grade_colors = {"G1": "#4A90D9", "G2": "#FF69B4", "G3": "#4CAF50", "OP": "#FFD700", "Pre-OP": "#FFD700"}
        for grade in ["G1", "G2", "G3", "OP", "Pre-OP"]:
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

        surface_row = QHBoxLayout()
        surface_row.addWidget(QLabel("Surface:"))
        surface_row.addSpacing(20)
        self.track_checks = {}
        for track in ["Turf", "Dirt"]:
            cb = QCheckBox(track)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_change)
            self.track_checks[track] = cb
            surface_row.addWidget(cb)
        surface_row.addStretch()
        filter_layout.addLayout(surface_row)

        distance_row = QHBoxLayout()
        distance_row.addWidget(QLabel("Distance:"))
        distance_row.addSpacing(20)
        self.dist_checks = {}
        for dist in ["Sprint", "Mile", "Medium", "Long"]:
            cb = QCheckBox(dist)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_change)
            self.dist_checks[dist] = cb
            distance_row.addWidget(cb)
        distance_row.addStretch()
        filter_layout.addLayout(distance_row)

        layout.addWidget(filter_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_widget = QWidget()
        self.periods_layout = QVBoxLayout(scroll_widget)
        self.periods_layout.setSpacing(6)
        self.periods_layout.setContentsMargins(0, 0, 0, 0)
        self._build_period_rows()
        self.periods_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        button_row = QHBoxLayout()
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        button_row.addWidget(clear_btn)
        button_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_races)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

    def _build_period_rows(self):
        while self.periods_layout.count() > 0:
            item = self.periods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.row_widgets = {}
        for period in self.period_order:
            self.periods_layout.addWidget(self._create_period_row(period))

    def _create_period_row(self, period):
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

        period_label = QLabel(period)
        period_label.setMinimumWidth(200)
        period_label.setMaximumWidth(200)
        period_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(period_label)

        combo = QComboBox()
        combo.setMinimumWidth(280)
        combo.setMaximumWidth(280)
        self._populate_race_combo(combo, period)

        current_selection = self.selections.get(period, {"race": "", "use_glowstick": False})
        if current_selection["race"]:
            idx = combo.findText(current_selection["race"])
            if idx >= 0:
                combo.setCurrentIndex(idx)

        combo.currentTextChanged.connect(lambda text, p=period: self._on_race_changed(p, text))
        row_layout.addWidget(combo)

        glowstick_checkbox = QCheckBox("Use Glowstick")
        glowstick_checkbox.setChecked(bool(current_selection["use_glowstick"]))
        glowstick_checkbox.stateChanged.connect(lambda _state, p=period: self._on_glowstick_changed(p))
        row_layout.addWidget(glowstick_checkbox)

        details_frame = QFrame()
        details_frame.setStyleSheet(f"background-color: {COLORS['bg_input']}; border-radius: 6px; padding: 4px;")
        details_layout = QHBoxLayout(details_frame)
        details_layout.setContentsMargins(8, 4, 8, 4)
        details_layout.setSpacing(16)

        detail_labels = {}
        for key, width in [("grade", 50), ("surface", 50), ("distance_type", 70), ("distance_meters", 60), ("racetrack", 80), ("fans", 60)]:
            label = QLabel("")
            label.setMinimumWidth(width)
            label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            details_layout.addWidget(label)
            detail_labels[key] = label

        details_layout.addStretch()
        row_layout.addWidget(details_frame, stretch=1)

        self.row_widgets[period] = {
            "combo": combo,
            "glowstick": glowstick_checkbox,
            "details": detail_labels,
        }
        self._update_row_details(period)
        return row

    def _populate_race_combo(self, combo, period):
        combo.clear()
        combo.addItem("")

        races = self.all_races.get(period, {})
        options = []
        grade_rank = {"G1": 5, "G2": 4, "G3": 3, "OP": 2, "Pre-OP": 1}
        for name, race_data in races.items():
            if isinstance(race_data, dict) and self._race_passes_filter(race_data):
                options.append((name, grade_rank.get(race_data.get("grade", ""), 0)))

        options.sort(key=lambda item: (-item[1], item[0]))
        for name, _rank in options:
            combo.addItem(name)

    def _race_passes_filter(self, race_data):
        grade = race_data.get("grade", "")
        surface = race_data.get("surface", "")
        distance_type = race_data.get("distance_type", "")

        if grade in self.grade_checks and not self.grade_checks[grade].isChecked():
            return False
        if surface in self.track_checks and not self.track_checks[surface].isChecked():
            return False
        if distance_type in self.dist_checks and not self.dist_checks[distance_type].isChecked():
            return False
        return True

    def _on_filter_change(self):
        for period, widgets in self.row_widgets.items():
            combo = widgets["combo"]
            current = combo.currentText()
            self._populate_race_combo(combo, period)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _ensure_selection(self, period):
        self.selections.setdefault(period, {"race": "", "use_glowstick": False})
        return self.selections[period]

    def _on_race_changed(self, period, race_name):
        selection = self._ensure_selection(period)
        selection["race"] = race_name if race_name else ""
        self._update_row_details(period)

    def _on_glowstick_changed(self, period):
        selection = self._ensure_selection(period)
        selection["use_glowstick"] = self.row_widgets[period]["glowstick"].isChecked()

    def _update_row_details(self, period):
        widgets = self.row_widgets.get(period)
        if widgets is None:
            return

        race_name = widgets["combo"].currentText()
        details = widgets["details"]
        if not race_name:
            for label in details.values():
                label.setText("")
            return

        race_data = self.all_races.get(period, {}).get(race_name, {})
        details["grade"].setText(race_data.get("grade", ""))
        details["surface"].setText(race_data.get("surface", ""))
        details["distance_type"].setText(race_data.get("distance_type", ""))
        meters = race_data.get("distance_meters", "")
        details["distance_meters"].setText(f"{meters}m" if meters else "")
        details["racetrack"].setText(race_data.get("racetrack", ""))
        fans = race_data.get("fans", "")
        details["fans"].setText(f"Fans {fans}" if fans else "")

        grade = race_data.get("grade", "")
        grade_colors = {"G1": "#4A90D9", "G2": "#FF69B4", "G3": "#4CAF50", "OP": "#FFD700", "Pre-OP": "#FFD700"}
        if grade in grade_colors:
            details["grade"].setStyleSheet(f"color: {grade_colors[grade]}; font-weight: bold;")
        else:
            details["grade"].setStyleSheet(f"color: {COLORS['text_secondary']};")

    def _clear_all(self):
        self.selections = {}
        for widgets in self.row_widgets.values():
            widgets["combo"].setCurrentIndex(0)
            widgets["glowstick"].setChecked(False)

    def _save_races(self):
        try:
            to_save = {}
            for period, selection in self.selections.items():
                race_name = selection.get("race", "")
                if not race_name:
                    continue
                to_save[period] = {
                    "race": race_name,
                    "use_glowstick": bool(selection.get("use_glowstick", False)),
                }

            os.makedirs(os.path.dirname(self.race_file), exist_ok=True)
            with open(self.race_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, "Saved", f"Saved {len(to_save)} race selections to {os.path.basename(self.race_file)}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
