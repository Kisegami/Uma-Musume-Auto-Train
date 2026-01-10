"""
Training Tab for PySide6 GUI
Contains stats priority, training settings, stat caps, and training score configuration.
Matches original GUI exactly.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from ..styles import COLORS
from ..icon_helper import get_icon


class NoScrollSpinBox(QSpinBox):
    """SpinBox that ignores scroll wheel events"""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """DoubleSpinBox that ignores scroll wheel events"""
    def wheelEvent(self, event):
        event.ignore()


class DraggableListWidget(QListWidget):
    """Horizontal list widget with drag-drop reordering"""
    orderChanged = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.model().rowsMoved.connect(self._on_order_changed)
    
    def _on_order_changed(self):
        items = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        self.orderChanged.emit(items)


class TrainingTab(QScrollArea):
    """Training configuration tab - matches original GUI"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create training tab UI matching original"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== Stats Priority Section ====================
        priority_group = QGroupBox("Stats Priority")
        priority_layout = QVBoxLayout(priority_group)
        
        instruction = QLabel("Drag and drop to reorder (left = highest priority):")
        instruction.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: normal;")
        instruction.setAlignment(Qt.AlignCenter)
        priority_layout.addWidget(instruction)
        
        # Container to center the stat boxes
        priority_container = QHBoxLayout()
        priority_container.setAlignment(Qt.AlignCenter)
        
        # Horizontal stat priority list
        self.priority_list = DraggableListWidget()
        self.priority_list.setFlow(QListWidget.LeftToRight)
        self.priority_list.setWrapping(False)
        self.priority_list.setFixedHeight(60)
        self.priority_list.setSpacing(8)
        self.priority_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.priority_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.priority_list.orderChanged.connect(self._on_priority_changed)
        self.priority_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: transparent; 
                border: none; 
                outline: none;
            }}
            QListWidget::item {{
                background-color: {COLORS['accent_primary']};
                color: white;
                border-radius: 10px;
                padding: 10px 16px;
                margin: 2px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {COLORS['accent_primary']};
            }}
            QListWidget::item:selected {{ 
                background-color: {COLORS['accent_green']}; 
                border: 2px solid white;
            }}
            QListWidget::item:hover:!selected {{ 
                background-color: {COLORS['accent_blue']}; 
                border: 2px solid {COLORS['accent_blue']};
            }}
        """)
        self.priority_list.setFixedWidth(550)
        priority_container.addWidget(self.priority_list)
        
        priority_layout.addLayout(priority_container)
        layout.addWidget(priority_group)
        
        # ==================== Training Settings Section ====================
        settings_group = QGroupBox("Training Settings")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(12)
        
        # Minimum Mood
        settings_layout.addWidget(QLabel("Minimum Mood:"), 0, 0)
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(["GREAT", "GOOD", "NORMAL", "BAD", "AWFUL"])
        self.mood_combo.currentTextChanged.connect(self._save_training)
        settings_layout.addWidget(self.mood_combo, 0, 1)
        
        # Maximum Failure Rate
        settings_layout.addWidget(QLabel("Maximum Failure Rate:"), 1, 0)
        self.failure_spin = NoScrollSpinBox()
        self.failure_spin.setRange(0, 100)
        self.failure_spin.valueChanged.connect(self._save_training)
        settings_layout.addWidget(self.failure_spin, 1, 1)
        
        # Minimum Energy
        settings_layout.addWidget(QLabel("Minimum Energy:"), 2, 0)
        self.energy_spin = NoScrollSpinBox()
        self.energy_spin.setRange(0, 100)
        self.energy_spin.valueChanged.connect(self._save_training)
        settings_layout.addWidget(self.energy_spin, 2, 1)
        
        # Do Race if no good training
        self.race_when_bad = QCheckBox("Do Race if no good training found")
        self.race_when_bad.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.race_when_bad, 3, 0, 1, 2)
        
        # Use dating instead of rest (works for both URA and Unity)
        self.use_dating = QCheckBox("Use dating instead of rest")
        self.use_dating.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.use_dating, 4, 0, 1, 2)
        
        # ==================== Unity Mode Settings ====================
        self.unity_widget = QWidget()
        unity_layout = QVBoxLayout(self.unity_widget)
        unity_layout.setContentsMargins(0, 12, 0, 0)
        unity_layout.setSpacing(12)
        
        # Spirit Burst Enabled Stats (Unity mode only)
        spirit_label = QLabel("Spirit Burst Enabled Stats:")
        spirit_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        unity_layout.addWidget(spirit_label)
        
        spirit_row = QHBoxLayout()
        spirit_row.setSpacing(24)
        self.spirit_burst_vars = {}
        for stat in ['spd', 'sta', 'pwr', 'guts', 'wit']:
            cb = QCheckBox(stat.upper())
            cb.setStyleSheet("QCheckBox { spacing: 8px; }")
            cb.stateChanged.connect(self._save_training)
            self.spirit_burst_vars[stat] = cb
            spirit_row.addWidget(cb)
        spirit_row.addStretch()
        unity_layout.addLayout(spirit_row)
        
        settings_layout.addWidget(self.unity_widget, 5, 0, 1, 2)
        
        layout.addWidget(settings_group)
        
        # ==================== Min Training Score Section ====================
        score_group = QGroupBox("Minimum Training Score (per stat)")
        score_layout = QHBoxLayout(score_group)
        score_layout.setSpacing(8)
        
        self.score_spins = {}
        stats = [("spd", "SPD"), ("sta", "STA"), ("pwr", "PWR"), ("guts", "GUTS"), ("wit", "WIT")]
        for stat_key, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
            stat_layout.addWidget(lbl)
            
            spin = NoScrollDoubleSpinBox()
            spin.setRange(0, 10)
            spin.setSingleStep(0.1)
            spin.setDecimals(1)
            spin.valueChanged.connect(self._save_training)
            stat_layout.addWidget(spin)
            self.score_spins[stat_key] = spin
            
            score_layout.addWidget(stat_widget)
        
        layout.addWidget(score_group)
        
        # ==================== Stat Caps Section ====================
        caps_group = QGroupBox("Stat Caps")
        caps_layout = QHBoxLayout(caps_group)
        caps_layout.setSpacing(8)
        
        self.cap_spins = {}
        for stat_key, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_muted']};")
            stat_layout.addWidget(lbl)
            
            spin = NoScrollSpinBox()
            spin.setRange(0, 2000)
            spin.setSingleStep(50)
            spin.valueChanged.connect(self._save_training)
            stat_layout.addWidget(spin)
            self.cap_spins[stat_key] = spin
            
            caps_layout.addWidget(stat_widget)
        
        layout.addWidget(caps_group)
        
        # ==================== Training Score (Collapsible) ====================
        self.score_btn = QPushButton("  Training Score Settings (Click to expand)")
        self.score_btn.setIcon(get_icon('expand'))
        self.score_btn.setCheckable(True)
        self.score_btn.clicked.connect(self._toggle_score_section)
        layout.addWidget(self.score_btn)
        
        self.score_section = QWidget()
        self.score_section_layout = QGridLayout(self.score_section)
        self.score_section_layout.setSpacing(12)
        
        # Common training score fields (always shown)
        # Rainbow Support
        self.score_section_layout.addWidget(QLabel("Rainbow Support:"), 0, 0)
        self.rainbow_spin = NoScrollDoubleSpinBox()
        self.rainbow_spin.setRange(0, 5)
        self.rainbow_spin.setDecimals(2)
        self.rainbow_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.rainbow_spin, 0, 1)
        
        # Low Bond Support
        self.score_section_layout.addWidget(QLabel("Low Bond (<4) Support:"), 1, 0)
        self.low_bond_spin = NoScrollDoubleSpinBox()
        self.low_bond_spin.setRange(0, 5)
        self.low_bond_spin.setDecimals(2)
        self.low_bond_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.low_bond_spin, 1, 1)
        
        # High Bond Different Type
        self.score_section_layout.addWidget(QLabel("High Bond (>=4) Different Type:"), 2, 0)
        self.high_bond_spin = NoScrollDoubleSpinBox()
        self.high_bond_spin.setRange(0, 5)
        self.high_bond_spin.setDecimals(2)
        self.high_bond_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.high_bond_spin, 2, 1)
        
        # Hint
        self.score_section_layout.addWidget(QLabel("Hint:"), 3, 0)
        self.hint_spin = NoScrollDoubleSpinBox()
        self.hint_spin.setRange(0, 5)
        self.hint_spin.setDecimals(2)
        self.hint_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.hint_spin, 3, 1)
        
        # Unity-specific training score fields (will be shown/hidden based on mode)
        self.unity_score_label1 = QLabel("Spirit Training:")
        self.score_section_layout.addWidget(self.unity_score_label1, 4, 0)
        self.spirit_training_spin = NoScrollDoubleSpinBox()
        self.spirit_training_spin.setRange(0, 5)
        self.spirit_training_spin.setDecimals(2)
        self.spirit_training_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_training_spin, 4, 1)
        
        self.unity_score_label2 = QLabel("Spirit Burst:")
        self.score_section_layout.addWidget(self.unity_score_label2, 5, 0)
        self.spirit_burst_spin = NoScrollDoubleSpinBox()
        self.spirit_burst_spin.setRange(0, 5)
        self.spirit_burst_spin.setDecimals(2)
        self.spirit_burst_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_burst_spin, 5, 1)
        
        self.unity_score_label3 = QLabel("Spirit Training Extra:")
        self.score_section_layout.addWidget(self.unity_score_label3, 6, 0)
        self.spirit_training_extra_spin = NoScrollDoubleSpinBox()
        self.spirit_training_extra_spin.setRange(0, 5)
        self.spirit_training_extra_spin.setDecimals(2)
        self.spirit_training_extra_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_training_extra_spin, 6, 1)
        
        self.score_section.hide()
        layout.addWidget(self.score_section)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _toggle_score_section(self):
        """Toggle training score section visibility"""
        if self.score_btn.isChecked():
            self.score_btn.setText("  Training Score Settings (Click to collapse)")
            self.score_btn.setIcon(get_icon('collapse'))
            self.score_section.show()
        else:
            self.score_btn.setText("  Training Score Settings (Click to expand)")
            self.score_btn.setIcon(get_icon('expand'))
            self.score_section.hide()
    
    def _update_unity_score_visibility(self):
        """Show/hide Unity-specific training score fields based on mode"""
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        is_unity = mode == "unity"
        
        # Unity-specific training score fields
        self.unity_score_label1.setVisible(is_unity)
        self.spirit_training_spin.setVisible(is_unity)
        self.unity_score_label2.setVisible(is_unity)
        self.spirit_burst_spin.setVisible(is_unity)
        self.unity_score_label3.setVisible(is_unity)
        self.spirit_training_extra_spin.setVisible(is_unity)
    
    def load_config(self):
        """Load config values into UI"""
        # Block signals during load to prevent save callbacks
        self._loading = True
        
        config = self.main_window.get_config()
        training = config.get("training", {})
        
        # Priority stats
        priority = training.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])
        self.priority_list.clear()
        stat_display = {"spd": "SPD", "sta": "STA", "pwr": "PWR", "guts": "GUTS", "wit": "WIT"}
        for stat in priority:
            if stat in stat_display:
                item = QListWidgetItem(stat_display[stat])
                item.setData(Qt.UserRole, stat)
                item.setTextAlignment(Qt.AlignCenter)
                self.priority_list.addItem(item)
        
        # Settings - block signals
        self.mood_combo.blockSignals(True)
        self.mood_combo.setCurrentText(training.get("minimum_mood", "GREAT"))
        self.mood_combo.blockSignals(False)
        
        self.failure_spin.blockSignals(True)
        self.failure_spin.setValue(training.get("maximum_failure", 15))
        self.failure_spin.blockSignals(False)
        
        self.energy_spin.blockSignals(True)
        self.energy_spin.setValue(training.get("min_energy", 30))
        self.energy_spin.blockSignals(False)
        
        self.race_when_bad.blockSignals(True)
        self.race_when_bad.setChecked(training.get("do_race_when_bad_training", False))
        self.race_when_bad.blockSignals(False)
        
        # Unity mode fields
        dating_config = config.get("dating", {})
        self.use_dating.blockSignals(True)
        self.use_dating.setChecked(dating_config.get("use_dating_instead_of_rest", False))
        self.use_dating.blockSignals(False)
        
        spirit_burst_stats = training.get("spirit_burst_enabled_stats", [])
        for stat, cb in self.spirit_burst_vars.items():
            cb.blockSignals(True)
            cb.setChecked(stat in spirit_burst_stats)
            cb.blockSignals(False)
        
        # Min scores
        min_score = training.get("min_score", {})
        if isinstance(min_score, (int, float)):
            for spin in self.score_spins.values():
                spin.blockSignals(True)
                spin.setValue(float(min_score))
                spin.blockSignals(False)
        else:
            for stat, spin in self.score_spins.items():
                spin.blockSignals(True)
                spin.setValue(min_score.get(stat, 1.0))
                spin.blockSignals(False)
        
        # Stat caps
        stat_caps = training.get("stat_caps", {})
        for stat, spin in self.cap_spins.items():
            spin.blockSignals(True)
            spin.setValue(stat_caps.get(stat, 600))
            spin.blockSignals(False)
        
        # Load training score from JSON file
        self._load_training_score_config()
        
        # Update Unity fields visibility based on mode
        self.update_unity_visibility()
        self._update_unity_score_visibility()
        
        self._loading = False
    
    def update_unity_visibility(self):
        """Show/hide Unity-specific fields based on mode"""
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        self.unity_widget.setVisible(mode == "unity")
        self._update_unity_score_visibility()
    
    def _on_priority_changed(self, order):
        """Handle priority order change"""
        if not getattr(self, '_loading', False):
            self._save_training()
    
    def _save_training(self):
        """Save training settings"""
        if getattr(self, '_loading', False):
            return
            
        config = self.main_window.get_config()
        if "training" not in config:
            config["training"] = {}
        
        # Priority
        priority = []
        for i in range(self.priority_list.count()):
            item = self.priority_list.item(i)
            if item:
                priority.append(item.data(Qt.UserRole))
        if priority:
            config["training"]["priority_stat"] = priority
        
        # Settings
        config["training"]["minimum_mood"] = self.mood_combo.currentText()
        config["training"]["maximum_failure"] = self.failure_spin.value()
        config["training"]["min_energy"] = self.energy_spin.value()
        config["training"]["do_race_when_bad_training"] = self.race_when_bad.isChecked()
        
        # Unity mode fields
        if "dating" not in config:
            config["dating"] = {}
        config["dating"]["use_dating_instead_of_rest"] = self.use_dating.isChecked()
        
        config["training"]["spirit_burst_enabled_stats"] = [
            stat for stat, cb in self.spirit_burst_vars.items() if cb.isChecked()
        ]
        
        # Min scores
        config["training"]["min_score"] = {stat: spin.value() for stat, spin in self.score_spins.items()}
        
        # Stat caps
        config["training"]["stat_caps"] = {stat: spin.value() for stat, spin in self.cap_spins.items()}
        
        # Actually save to file
        self.main_window.save_config()
    
    def _load_training_score_config(self):
        """Load training score settings from JSON file"""
        import json
        import os
        
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        filename = "training_score_unity.json" if mode == "unity" else "training_score.json"
        
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    score_config = json.load(f)
            else:
                score_config = {}
        except Exception:
            score_config = {}
        
        # Load common score settings
        self.rainbow_spin.blockSignals(True)
        self.rainbow_spin.setValue(score_config.get("rainbow_support", 1.0))
        self.rainbow_spin.blockSignals(False)
        
        self.low_bond_spin.blockSignals(True)
        self.low_bond_spin.setValue(score_config.get("low_bond_support", 0.7))
        self.low_bond_spin.blockSignals(False)
        
        self.high_bond_spin.blockSignals(True)
        self.high_bond_spin.setValue(score_config.get("high_bond_support", 0.0))
        self.high_bond_spin.blockSignals(False)
        
        self.hint_spin.blockSignals(True)
        self.hint_spin.setValue(score_config.get("hint", 0.3))
        self.hint_spin.blockSignals(False)
        
        # Load Unity-specific score settings
        self.spirit_training_spin.blockSignals(True)
        self.spirit_training_spin.setValue(score_config.get("spirit_training", 0.4))
        self.spirit_training_spin.blockSignals(False)
        
        self.spirit_burst_spin.blockSignals(True)
        self.spirit_burst_spin.setValue(score_config.get("spirit_burst", 1.0))
        self.spirit_burst_spin.blockSignals(False)
        
        self.spirit_training_extra_spin.blockSignals(True)
        self.spirit_training_extra_spin.setValue(score_config.get("spirit_training_extra", 0.2))
        self.spirit_training_extra_spin.blockSignals(False)
    
    def _save_training_score_config(self):
        """Save training score settings to JSON file"""
        import json
        import os
        
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        filename = "training_score_unity.json" if mode == "unity" else "training_score.json"
        
        score_config = {
            "rainbow_support": self.rainbow_spin.value(),
            "low_bond_support": self.low_bond_spin.value(),
            "high_bond_support": self.high_bond_spin.value(),
            "hint": self.hint_spin.value(),
        }
        
        # Add Unity-specific settings for unity mode
        if mode == "unity":
            score_config["spirit_training"] = self.spirit_training_spin.value()
            score_config["spirit_burst"] = self.spirit_burst_spin.value()
            score_config["spirit_training_extra"] = self.spirit_training_extra_spin.value()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(score_config, f, indent=4)
        except Exception as e:
            print(f"Failed to save training score config: {e}")
    
    def _on_training_score_change(self):
        """Handle training score changes - save to JSON file"""
        if not getattr(self, '_loading', False):
            self._save_training_score_config()

