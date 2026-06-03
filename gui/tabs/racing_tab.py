"""
Racing Tab for PySide6 GUI
Contains allowed grades, tracks, distances, strategy, and custom race settings.
Matches original GUI exactly.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QGridLayout, QFrame, QScrollArea, QCheckBox, QPushButton
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class RacingTab(QScrollArea):
    """Racing configuration tab - matches original GUI"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self.allowed_grades_vars = {}
        self.allowed_tracks_vars = {}
        self.allowed_distances_vars = {}
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create racing tab UI matching original"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== Racing Settings Section ====================
        settings_group = QGroupBox("Racing Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(12)
        
        # Allowed Grades
        grades_widget = QWidget()
        grades_layout = QVBoxLayout(grades_widget)
        grades_layout.setContentsMargins(0, 0, 0, 0)
        grades_layout.setSpacing(4)
        grades_layout.addWidget(QLabel("Allowed Grades:"))
        
        grades_row = QHBoxLayout()
        for grade in ['G1', 'G2', 'G3', 'OP', 'Pre-OP']:
            cb = QCheckBox(grade)
            cb.stateChanged.connect(self._save_racing)
            self.allowed_grades_vars[grade] = cb
            grades_row.addWidget(cb)
        grades_row.addStretch()
        grades_layout.addLayout(grades_row)
        settings_layout.addWidget(grades_widget)
        
        # Allowed Tracks
        tracks_widget = QWidget()
        tracks_layout = QVBoxLayout(tracks_widget)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        tracks_layout.setSpacing(4)
        tracks_layout.addWidget(QLabel("Allowed Tracks:"))
        
        tracks_row = QHBoxLayout()
        for track in ['Turf', 'Dirt']:
            cb = QCheckBox(track)
            cb.stateChanged.connect(self._save_racing)
            self.allowed_tracks_vars[track] = cb
            tracks_row.addWidget(cb)
        tracks_row.addStretch()
        tracks_layout.addLayout(tracks_row)
        settings_layout.addWidget(tracks_widget)
        
        # Allowed Distances
        dist_widget = QWidget()
        dist_layout = QVBoxLayout(dist_widget)
        dist_layout.setContentsMargins(0, 0, 0, 0)
        dist_layout.setSpacing(4)
        dist_layout.addWidget(QLabel("Allowed Distances:"))
        
        dist_row = QHBoxLayout()
        for dist in ['Sprint', 'Mile', 'Medium', 'Long']:
            cb = QCheckBox(dist)
            cb.stateChanged.connect(self._save_racing)
            self.allowed_distances_vars[dist] = cb
            dist_row.addWidget(cb)
        dist_row.addStretch()
        dist_layout.addLayout(dist_row)
        settings_layout.addWidget(dist_widget)
        
        # Strategy
        strategy_widget = QWidget()
        strategy_layout = QHBoxLayout(strategy_widget)
        strategy_layout.setContentsMargins(0, 0, 0, 0)
        strategy_layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(['FRONT', 'PACE', 'LATE', 'END'])
        self.strategy_combo.currentTextChanged.connect(self._save_racing)
        strategy_layout.addWidget(self.strategy_combo)
        strategy_layout.addStretch()
        settings_layout.addWidget(strategy_widget)
        
        # Race Retry
        self.retry_race = QCheckBox("Race Retry using Clock")
        self.retry_race.stateChanged.connect(self._on_retry_race_changed)
        settings_layout.addWidget(self.retry_race)
        
        # Buy clock using Carats (dependent on retry_race)
        self.buy_clock_carats = QCheckBox("Buy clock using Carats")
        self.buy_clock_carats.stateChanged.connect(self._save_racing)
        self.buy_clock_carats.setVisible(False)
        settings_layout.addWidget(self.buy_clock_carats)
        
        # Stop bot on race fail (visible when retry_race is unchecked)
        self.stop_on_race_fail = QCheckBox("Stop bot on race fail")
        self.stop_on_race_fail.stateChanged.connect(self._save_racing)
        self.stop_on_race_fail.setVisible(True)
        settings_layout.addWidget(self.stop_on_race_fail)
        
        layout.addWidget(settings_group)
        
        # ==================== Custom Race Section ====================
        custom_group = QGroupBox("Custom Race Settings")
        custom_layout = QVBoxLayout(custom_group)
        custom_layout.setSpacing(12)
        
        # Do Custom Races checkbox
        self.do_custom_race = QCheckBox("Do Custom Races")
        self.do_custom_race.stateChanged.connect(self._toggle_custom_settings)
        custom_layout.addWidget(self.do_custom_race)

        custom_method_widget = QWidget()
        custom_method_layout = QHBoxLayout(custom_method_widget)
        custom_method_layout.setContentsMargins(0, 0, 0, 0)
        custom_method_layout.addWidget(QLabel("Custom Race Method:"))
        self.custom_race_method_combo = QComboBox()
        self.custom_race_method_combo.addItem("OCR", "ocr")
        self.custom_race_method_combo.addItem("Template Matching", "template_matching")
        self.custom_race_method_combo.currentIndexChanged.connect(self._save_racing)
        custom_method_layout.addWidget(self.custom_race_method_combo)
        custom_method_layout.addStretch()
        custom_layout.addWidget(custom_method_widget)
        self.custom_method_widget = custom_method_widget
        
        # Custom race file container (hidden when disabled)
        self.custom_file_widget = QWidget()
        custom_file_layout = QHBoxLayout(self.custom_file_widget)
        custom_file_layout.setContentsMargins(0, 0, 0, 0)
        
        custom_file_layout.addWidget(QLabel("Custom Race File:"))
        self.custom_file_combo = QComboBox()
        self.custom_file_combo.setMinimumWidth(200)
        self._load_custom_race_templates()
        self.custom_file_combo.currentTextChanged.connect(self._save_racing)
        custom_file_layout.addWidget(self.custom_file_combo)
        
        add_btn = QPushButton("Add New")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_template)
        custom_file_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_template)
        custom_file_layout.addWidget(remove_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("accent")
        edit_btn.clicked.connect(self._edit_template)
        custom_file_layout.addWidget(edit_btn)
        
        custom_file_layout.addStretch()
        custom_layout.addWidget(self.custom_file_widget)
        
        layout.addWidget(custom_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _toggle_custom_settings(self):
        """Toggle custom race file settings visibility"""
        self.custom_file_widget.setVisible(self.do_custom_race.isChecked())
        self.custom_method_widget.setVisible(self.do_custom_race.isChecked())
        self._save_racing()
    
    def _on_retry_race_changed(self, state):
        """Handle retry race checkbox and dependent checkboxes"""
        is_checked = state == Qt.CheckState.Checked.value
        self.buy_clock_carats.setVisible(is_checked)
        self.stop_on_race_fail.setVisible(not is_checked)
        if not is_checked:
            self.buy_clock_carats.setChecked(False)
        else:
            self.stop_on_race_fail.setChecked(False)
        self._save_racing()
    
    def _load_custom_race_templates(self):
        """Load available custom race templates"""
        import os
        import glob
        self.custom_file_combo.clear()
        template_dir = os.path.join("template", "races")
        if os.path.exists(template_dir):
            files = glob.glob(os.path.join(template_dir, "*.json"))
            for f in sorted(files):
                self.custom_file_combo.addItem(os.path.basename(f))
        if self.custom_file_combo.count() == 0:
            self.custom_file_combo.addItem("custom_races.json")
    
    def load_config(self):
        """Load config values into UI"""
        self._loading = True
        config = self.main_window.get_config()
        racing = config.get("racing", {})
        
        # Allowed grades - block signals
        for grade, cb in self.allowed_grades_vars.items():
            cb.blockSignals(True)
            cb.setChecked(grade in racing.get("allowed_grades", []))
            cb.blockSignals(False)
        
        # Allowed tracks - block signals
        for track, cb in self.allowed_tracks_vars.items():
            cb.blockSignals(True)
            cb.setChecked(track in racing.get("allowed_tracks", []))
            cb.blockSignals(False)
        
        # Allowed distances - block signals
        for dist, cb in self.allowed_distances_vars.items():
            cb.blockSignals(True)
            cb.setChecked(dist in racing.get("allowed_distances", []))
            cb.blockSignals(False)
        
        # Strategy
        self.strategy_combo.blockSignals(True)
        self.strategy_combo.setCurrentText(racing.get("strategy", "FRONT"))
        self.strategy_combo.blockSignals(False)
        
        # Race retry
        self.retry_race.blockSignals(True)
        self.retry_race.setChecked(racing.get("retry_race", True))
        self.retry_race.blockSignals(False)
        
        # Buy clock carats
        self.buy_clock_carats.blockSignals(True)
        self.buy_clock_carats.setChecked(racing.get("buy_clock_carats", False))
        self.buy_clock_carats.setVisible(self.retry_race.isChecked())
        self.buy_clock_carats.blockSignals(False)
        
        # Stop on race fail
        self.stop_on_race_fail.blockSignals(True)
        self.stop_on_race_fail.setChecked(racing.get("stop_on_race_fail", True))
        self.stop_on_race_fail.setVisible(not self.retry_race.isChecked())
        self.stop_on_race_fail.blockSignals(False)
        
        # Custom race
        self.do_custom_race.blockSignals(True)
        self.do_custom_race.setChecked(racing.get("do_custom_race", True))
        self.do_custom_race.blockSignals(False)
        self.custom_file_widget.setVisible(self.do_custom_race.isChecked())
        self.custom_method_widget.setVisible(self.do_custom_race.isChecked())

        # Custom race method
        self.custom_race_method_combo.blockSignals(True)
        custom_race_method = racing.get("custom_race_search_method", "ocr")
        idx = self.custom_race_method_combo.findData(custom_race_method)
        self.custom_race_method_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.custom_race_method_combo.blockSignals(False)
        
        # Custom file
        custom_file = racing.get("custom_race_file", "custom_races.json")
        if "/" in custom_file or "\\" in custom_file:
            custom_file = os.path.basename(custom_file)
        idx = self.custom_file_combo.findText(custom_file)
        if idx >= 0:
            self.custom_file_combo.setCurrentIndex(idx)
        
        self._loading = False
    
    def _save_racing(self):
        """Save racing settings"""
        if getattr(self, '_loading', False):
            return
        
        config = self.main_window.get_config()
        if "racing" not in config:
            config["racing"] = {}
        
        config["racing"]["allowed_grades"] = [g for g, cb in self.allowed_grades_vars.items() if cb.isChecked()]
        config["racing"]["allowed_tracks"] = [t for t, cb in self.allowed_tracks_vars.items() if cb.isChecked()]
        config["racing"]["allowed_distances"] = [d for d, cb in self.allowed_distances_vars.items() if cb.isChecked()]
        config["racing"]["strategy"] = self.strategy_combo.currentText()
        config["racing"]["retry_race"] = self.retry_race.isChecked()
        config["racing"]["buy_clock_carats"] = self.buy_clock_carats.isChecked()
        config["racing"]["stop_on_race_fail"] = self.stop_on_race_fail.isChecked()
        config["racing"]["do_custom_race"] = self.do_custom_race.isChecked()
        config["racing"]["custom_race_file"] = f"template/races/{self.custom_file_combo.currentText()}"
        config["racing"]["custom_race_search_method"] = self.custom_race_method_combo.currentData() or "ocr"
        
        self.main_window.save_config()
    
    def _add_template(self):
        """Add new custom race template"""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Template", "Enter template name:")
        if ok and name.strip():
            import os
            import json
            safe_name = name.strip()
            if not safe_name.endswith(".json"):
                safe_name += ".json"
            path = os.path.join("template", "races", safe_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump({}, f)
            self._load_custom_race_templates()
            idx = self.custom_file_combo.findText(safe_name)
            if idx >= 0:
                self.custom_file_combo.setCurrentIndex(idx)
    
    def _remove_template(self):
        """Remove selected template"""
        from PySide6.QtWidgets import QMessageBox
        import os
        filename = self.custom_file_combo.currentText()
        if not filename:
            return
        reply = QMessageBox.question(self, "Confirm", f"Remove '{filename}'?")
        if reply == QMessageBox.Yes:
            path = os.path.join("template", "races", filename)
            if os.path.exists(path):
                os.remove(path)
            self._load_custom_race_templates()
    
    def _edit_template(self):
        """Edit selected template"""
        filename = self.custom_file_combo.currentText()
        if not filename:
            return
        
        race_file = os.path.join("template", "races", filename)
        
        from .custom_race_window import CustomRaceWindow
        dialog = CustomRaceWindow(self, race_file)
        dialog.exec()


import os
