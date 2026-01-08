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
        
        instruction = QLabel("Click to swap positions (left = highest priority):")
        instruction.setStyleSheet(f"color: {COLORS['text_muted']};")
        priority_layout.addWidget(instruction)
        
        # Horizontal stat priority list
        self.priority_list = DraggableListWidget()
        self.priority_list.setFlow(QListWidget.LeftToRight)
        self.priority_list.setWrapping(False)
        self.priority_list.setFixedHeight(50)
        self.priority_list.setSpacing(4)
        self.priority_list.orderChanged.connect(self._on_priority_changed)
        self.priority_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; }}
            QListWidget::item {{
                background-color: {COLORS['accent_primary']};
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
                margin: 2px;
                min-width: 50px;
            }}
            QListWidget::item:selected {{ background-color: {COLORS['accent_green']}; }}
            QListWidget::item:hover:!selected {{ background-color: {COLORS['accent_blue']}; }}
        """)
        priority_layout.addWidget(self.priority_list)
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
        self.failure_spin = QSpinBox()
        self.failure_spin.setRange(0, 100)
        self.failure_spin.valueChanged.connect(self._save_training)
        settings_layout.addWidget(self.failure_spin, 1, 1)
        
        # Minimum Energy
        settings_layout.addWidget(QLabel("Minimum Energy:"), 2, 0)
        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(0, 100)
        self.energy_spin.valueChanged.connect(self._save_training)
        settings_layout.addWidget(self.energy_spin, 2, 1)
        
        # Do Race if no good training
        self.race_when_bad = QCheckBox("Do Race if no good training found")
        self.race_when_bad.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.race_when_bad, 3, 0, 1, 2)
        
        # ==================== Unity Mode Settings ====================
        self.unity_widget = QWidget()
        unity_layout = QVBoxLayout(self.unity_widget)
        unity_layout.setContentsMargins(0, 8, 0, 0)
        unity_layout.setSpacing(8)
        
        # Use dating instead of rest (Unity mode)
        self.use_dating = QCheckBox("Use dating instead of rest")
        self.use_dating.stateChanged.connect(self._save_training)
        unity_layout.addWidget(self.use_dating)
        
        # Spirit Burst Enabled Stats (Unity mode)
        spirit_widget = QWidget()
        spirit_layout = QVBoxLayout(spirit_widget)
        spirit_layout.setContentsMargins(0, 0, 0, 0)
        spirit_layout.setSpacing(4)
        spirit_layout.addWidget(QLabel("Spirit Burst Enabled Stats:"))
        
        spirit_row = QHBoxLayout()
        self.spirit_burst_vars = {}
        for stat in ['spd', 'sta', 'pwr', 'guts', 'wit']:
            cb = QCheckBox(stat.upper())
            cb.stateChanged.connect(self._save_training)
            self.spirit_burst_vars[stat] = cb
            spirit_row.addWidget(cb)
        spirit_row.addStretch()
        spirit_layout.addLayout(spirit_row)
        unity_layout.addWidget(spirit_widget)
        
        settings_layout.addWidget(self.unity_widget, 4, 0, 1, 2)
        
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
            
            spin = QDoubleSpinBox()
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
            
            spin = QSpinBox()
            spin.setRange(0, 2000)
            spin.setSingleStep(50)
            spin.valueChanged.connect(self._save_training)
            stat_layout.addWidget(spin)
            self.cap_spins[stat_key] = spin
            
            caps_layout.addWidget(stat_widget)
        
        layout.addWidget(caps_group)
        
        # ==================== Training Score (Collapsible) ====================
        self.score_btn = QPushButton("▶ Training Score Settings (Click to expand)")
        self.score_btn.setCheckable(True)
        self.score_btn.clicked.connect(self._toggle_score_section)
        layout.addWidget(self.score_btn)
        
        self.score_section = QWidget()
        score_section_layout = QGridLayout(self.score_section)
        score_section_layout.setSpacing(12)
        
        # Rainbow Support
        score_section_layout.addWidget(QLabel("Rainbow Support:"), 0, 0)
        self.rainbow_spin = QDoubleSpinBox()
        self.rainbow_spin.setRange(0, 5)
        self.rainbow_spin.setDecimals(2)
        score_section_layout.addWidget(self.rainbow_spin, 0, 1)
        
        # Low Bond Support
        score_section_layout.addWidget(QLabel("Low Bond (<4) Support:"), 1, 0)
        self.low_bond_spin = QDoubleSpinBox()
        self.low_bond_spin.setRange(0, 5)
        self.low_bond_spin.setDecimals(2)
        score_section_layout.addWidget(self.low_bond_spin, 1, 1)
        
        # High Bond Different Type
        score_section_layout.addWidget(QLabel("High Bond (>=4) Different Type:"), 2, 0)
        self.high_bond_spin = QDoubleSpinBox()
        self.high_bond_spin.setRange(0, 5)
        self.high_bond_spin.setDecimals(2)
        score_section_layout.addWidget(self.high_bond_spin, 2, 1)
        
        # Hint
        score_section_layout.addWidget(QLabel("Hint:"), 3, 0)
        self.hint_spin = QDoubleSpinBox()
        self.hint_spin.setRange(0, 5)
        self.hint_spin.setDecimals(2)
        score_section_layout.addWidget(self.hint_spin, 3, 1)
        
        self.score_section.hide()
        layout.addWidget(self.score_section)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _toggle_score_section(self):
        """Toggle training score section visibility"""
        if self.score_btn.isChecked():
            self.score_btn.setText("▼ Training Score Settings (Click to collapse)")
            self.score_section.show()
        else:
            self.score_btn.setText("▶ Training Score Settings (Click to expand)")
            self.score_section.hide()
    
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
        
        # Training score
        self.rainbow_spin.setValue(1.0)
        self.low_bond_spin.setValue(0.7)
        self.high_bond_spin.setValue(0.0)
        self.hint_spin.setValue(0.3)
        
        # Update Unity fields visibility based on mode
        self.update_unity_visibility()
        
        self._loading = False
    
    def update_unity_visibility(self):
        """Show/hide Unity-specific fields based on mode"""
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        self.unity_widget.setVisible(mode == "unity")
    
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
