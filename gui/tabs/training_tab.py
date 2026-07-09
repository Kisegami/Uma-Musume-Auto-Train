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
    TRAINING_STAT_DISPLAY = [
        ("spd", "SPD"),
        ("sta", "STA"),
        ("pwr", "PWR"),
        ("guts", "GUTS"),
        ("wit", "WIT"),
    ]
    DEFAULT_DUEL_ALLOWED_TRAININGS = ["spd", "sta", "pwr", "guts", "wit"]
    DUEL_STAT_DISPLAY = [
        ("speed", "Speed"),
        ("stamina", "Stamina"),
        ("power", "Power"),
        ("guts", "Guts"),
        ("wits", "Wits"),
        ("energy", "Energy"),
    ]
    DEFAULT_DUEL_CHOICES = ["speed", "stamina", "power", "guts", "wits", "energy"]
    
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

        # ==================== Ura Duel Settings Section ====================
        self.duel_group = QGroupBox("Duel Setting")
        duel_layout = QVBoxLayout(self.duel_group)
        duel_layout.setSpacing(12)

        allowed_training_label = QLabel("Duel Allowed Training")
        allowed_training_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        duel_layout.addWidget(allowed_training_label)

        allowed_training_row = QHBoxLayout()
        allowed_training_row.setSpacing(18)
        self.duel_allowed_training_vars = {}
        for stat_key, label in self.TRAINING_STAT_DISPLAY:
            cb = QCheckBox(label)
            cb.setStyleSheet("QCheckBox { spacing: 8px; }")
            cb.stateChanged.connect(self._save_training)
            self.duel_allowed_training_vars[stat_key] = cb
            allowed_training_row.addWidget(cb)
        allowed_training_row.addStretch()
        duel_layout.addLayout(allowed_training_row)

        whitelist_label = QLabel("Duel Choices Whitelists")
        whitelist_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        duel_layout.addWidget(whitelist_label)

        whitelist_row = QHBoxLayout()
        whitelist_row.setSpacing(18)
        self.duel_choice_vars = {}
        for stat_key, label in self.DUEL_STAT_DISPLAY:
            cb = QCheckBox(label)
            cb.setStyleSheet("QCheckBox { spacing: 8px; }")
            cb.stateChanged.connect(self._on_duel_whitelist_changed)
            self.duel_choice_vars[stat_key] = cb
            whitelist_row.addWidget(cb)
        whitelist_row.addStretch()
        duel_layout.addLayout(whitelist_row)

        priority_label = QLabel("Duel Choices Priority")
        priority_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        duel_layout.addWidget(priority_label)

        duel_instruction = QLabel("Drag and drop chosen stats to reorder (left = highest priority):")
        duel_instruction.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: normal;")
        duel_instruction.setAlignment(Qt.AlignCenter)
        duel_layout.addWidget(duel_instruction)

        duel_priority_container = QHBoxLayout()
        duel_priority_container.setAlignment(Qt.AlignCenter)
        self.duel_priority_list = DraggableListWidget()
        self.duel_priority_list.setFlow(QListWidget.LeftToRight)
        self.duel_priority_list.setWrapping(False)
        self.duel_priority_list.setFixedHeight(60)
        self.duel_priority_list.setSpacing(8)
        self.duel_priority_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.duel_priority_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.duel_priority_list.orderChanged.connect(self._on_duel_priority_changed)
        self.duel_priority_list.setStyleSheet(f"""
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
        self.duel_priority_list.setFixedWidth(650)
        duel_priority_container.addWidget(self.duel_priority_list)
        duel_layout.addLayout(duel_priority_container)

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
        
        # Rest in June to save energy for summer
        self.rest_in_june = QCheckBox("Rest in June to save Energy for Summer")
        self.rest_in_june.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.rest_in_june, 5, 0, 1, 2)

        # Skip OCR-based criteria/goal-name checks
        self.skip_goal_check = QCheckBox("Skip criteria and goal-name check")
        self.skip_goal_check.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.skip_goal_check, 6, 0, 1, 2)

        # Skip infirmary redirect on the first turn of a fresh career
        self.skip_infirmary_check_on_new_turn = QCheckBox("Skip infirmary check on new turn")
        self.skip_infirmary_check_on_new_turn.stateChanged.connect(self._save_training)
        settings_layout.addWidget(self.skip_infirmary_check_on_new_turn, 7, 0, 1, 2)

        # Gambling Train - increase max failure for high score training
        self.gambling_train = QCheckBox("Gambling Train (increase max failure for high score)")
        self.gambling_train.stateChanged.connect(self._on_gambling_train_toggle)
        settings_layout.addWidget(self.gambling_train, 8, 0, 1, 2)
        
        # Gambling Train Settings (shown when enabled)
        self.gambling_settings_widget = QWidget()
        gambling_layout = QHBoxLayout(self.gambling_settings_widget)
        gambling_layout.setContentsMargins(20, 0, 0, 0)
        gambling_layout.setSpacing(8)
        
        gambling_layout.addWidget(QLabel("Increase max failure by"))
        self.gambling_failure_spin = NoScrollSpinBox()
        self.gambling_failure_spin.setRange(1, 50)
        self.gambling_failure_spin.setValue(5)
        self.gambling_failure_spin.setFixedWidth(60)
        self.gambling_failure_spin.valueChanged.connect(self._save_training)
        gambling_layout.addWidget(self.gambling_failure_spin)
        
        gambling_layout.addWidget(QLabel("% for each"))
        self.gambling_score_spin = NoScrollDoubleSpinBox()
        self.gambling_score_spin.setRange(0.1, 10.0)
        self.gambling_score_spin.setValue(1.0)
        self.gambling_score_spin.setSingleStep(0.1)
        self.gambling_score_spin.setDecimals(1)
        self.gambling_score_spin.setFixedWidth(60)
        self.gambling_score_spin.valueChanged.connect(self._save_training)
        gambling_layout.addWidget(self.gambling_score_spin)
        
        gambling_layout.addWidget(QLabel("score"))
        gambling_layout.addStretch()
        
        self.gambling_settings_widget.hide()
        settings_layout.addWidget(self.gambling_settings_widget, 9, 0, 1, 2)
        
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

        # Spirit Burst EX Enabled Stats (Unity mode only)
        spirit_ex_label = QLabel("Spirit Burst EX Enabled Stats:")
        spirit_ex_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        unity_layout.addWidget(spirit_ex_label)

        spirit_ex_row = QHBoxLayout()
        spirit_ex_row.setSpacing(24)
        self.spirit_burst_ex_vars = {}
        for stat in ['spd', 'sta', 'pwr', 'guts', 'wit']:
            cb = QCheckBox(stat.upper())
            cb.setStyleSheet("QCheckBox { spacing: 8px; }")
            cb.stateChanged.connect(self._save_training)
            self.spirit_burst_ex_vars[stat] = cb
            spirit_ex_row.addWidget(cb)
        spirit_ex_row.addStretch()
        unity_layout.addLayout(spirit_ex_row)
        
        settings_layout.addWidget(self.unity_widget, 10, 0, 1, 2)
        
        layout.addWidget(settings_group)
        layout.addWidget(self.duel_group)
        
        # ==================== Min Training Score Section ====================
        score_group = QGroupBox("Minimum Training Score (per stat)")
        score_layout = QHBoxLayout(score_group)
        score_layout.setSpacing(8)
        
        # Define stat-specific colors
        stat_colors = {
            "spd": "#87CEEB",   # Light Blue
            "sta": "#FF6B6B",   # Light Red
            "pwr": "#FFE066",   # Light Yellow
            "guts": "#FFB6C1",  # Light Pink
            "wit": "#90EE90"    # Light Green
        }
        
        self.score_spins = {}
        stats = [("spd", "SPD"), ("sta", "STA"), ("pwr", "PWR"), ("guts", "GUTS"), ("wit", "WIT")]
        for stat_key, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {stat_colors[stat_key]}; font-weight: bold;")
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
        caps_group_layout = QVBoxLayout(caps_group)
        caps_group_layout.setSpacing(8)

        self.soft_cap_enabled = QCheckBox("Enable Soft Cap")
        self.soft_cap_enabled.stateChanged.connect(self._on_soft_cap_toggle)
        caps_group_layout.addWidget(self.soft_cap_enabled)

        soft_cap_hint = QLabel("Soft cap is applied first. Once every tracked stat reaches its soft cap, training switches back to hard caps.")
        soft_cap_hint.setWordWrap(True)
        soft_cap_hint.setStyleSheet(f"color: {COLORS['text_muted']};")
        caps_group_layout.addWidget(soft_cap_hint)

        self.soft_cap_widget = QWidget()
        soft_caps_layout = QVBoxLayout(self.soft_cap_widget)
        soft_caps_layout.setContentsMargins(18, 0, 0, 0)
        soft_caps_layout.setSpacing(6)
        soft_caps_layout.addWidget(QLabel("Soft Caps"))

        soft_caps_row = QHBoxLayout()
        soft_caps_row.setSpacing(8)
        self.soft_cap_spins = {}
        for stat_key, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)

            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {stat_colors[stat_key]}; font-weight: bold;")
            stat_layout.addWidget(lbl)

            spin = NoScrollSpinBox()
            spin.setRange(0, 2000)
            spin.setSingleStep(50)
            spin.valueChanged.connect(self._save_training)
            stat_layout.addWidget(spin)
            self.soft_cap_spins[stat_key] = spin

            soft_caps_row.addWidget(stat_widget)
        soft_caps_layout.addLayout(soft_caps_row)
        caps_group_layout.addWidget(self.soft_cap_widget)

        hard_caps_label = QLabel("Hard Caps")
        hard_caps_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        caps_group_layout.addWidget(hard_caps_label)

        hard_caps_row = QHBoxLayout()
        hard_caps_row.setSpacing(8)
        self.cap_spins = {}
        for stat_key, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(4)

            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {stat_colors[stat_key]}; font-weight: bold;")
            stat_layout.addWidget(lbl)

            spin = NoScrollSpinBox()
            spin.setRange(0, 2000)
            spin.setSingleStep(50)
            spin.valueChanged.connect(self._save_training)
            stat_layout.addWidget(spin)
            self.cap_spins[stat_key] = spin

            hard_caps_row.addWidget(stat_widget)
        caps_group_layout.addLayout(hard_caps_row)
        
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
        
        # Friend Support (bond < 3)
        self.score_section_layout.addWidget(QLabel("Friend Support (bond < 3):"), 4, 0)
        self.friend_support_spin = NoScrollDoubleSpinBox()
        self.friend_support_spin.setRange(0, 5)
        self.friend_support_spin.setDecimals(2)
        self.friend_support_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.friend_support_spin, 4, 1)

        self.happy_meeks_duel_label = QLabel("Happy Meek's Duel:")
        self.score_section_layout.addWidget(self.happy_meeks_duel_label, 5, 0)
        self.happy_meeks_duel_spin = NoScrollDoubleSpinBox()
        self.happy_meeks_duel_spin.setRange(0, 5)
        self.happy_meeks_duel_spin.setDecimals(2)
        self.happy_meeks_duel_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.happy_meeks_duel_spin, 5, 1)
        
        # Unity-specific training score fields (will be shown/hidden based on mode)
        self.unity_score_label1 = QLabel("Spirit Training:")
        self.score_section_layout.addWidget(self.unity_score_label1, 6, 0)
        self.spirit_training_spin = NoScrollDoubleSpinBox()
        self.spirit_training_spin.setRange(0, 5)
        self.spirit_training_spin.setDecimals(2)
        self.spirit_training_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_training_spin, 6, 1)
        
        self.unity_score_label2 = QLabel("Spirit Burst:")
        self.score_section_layout.addWidget(self.unity_score_label2, 7, 0)
        self.spirit_burst_spin = NoScrollDoubleSpinBox()
        self.spirit_burst_spin.setRange(0, 5)
        self.spirit_burst_spin.setDecimals(2)
        self.spirit_burst_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_burst_spin, 7, 1)

        self.unity_score_label4 = QLabel("Spirit Burst Extreme:")
        self.score_section_layout.addWidget(self.unity_score_label4, 8, 0)
        self.spirit_burst_ex_spin = NoScrollDoubleSpinBox()
        self.spirit_burst_ex_spin.setRange(0, 5)
        self.spirit_burst_ex_spin.setDecimals(2)
        self.spirit_burst_ex_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_burst_ex_spin, 8, 1)
        
        self.unity_score_label3 = QLabel("Spirit Training Extra:")
        self.score_section_layout.addWidget(self.unity_score_label3, 9, 0)
        self.spirit_training_extra_spin = NoScrollDoubleSpinBox()
        self.spirit_training_extra_spin.setRange(0, 5)
        self.spirit_training_extra_spin.setDecimals(2)
        self.spirit_training_extra_spin.valueChanged.connect(self._on_training_score_change)
        self.score_section_layout.addWidget(self.spirit_training_extra_spin, 9, 1)
        
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
        is_ura = mode == "ura"

        self.happy_meeks_duel_label.setVisible(is_ura)
        self.happy_meeks_duel_spin.setVisible(is_ura)
        
        # Unity-specific training score fields
        self.unity_score_label1.setVisible(is_unity)
        self.spirit_training_spin.setVisible(is_unity)
        self.unity_score_label2.setVisible(is_unity)
        self.spirit_burst_spin.setVisible(is_unity)
        self.unity_score_label4.setVisible(is_unity)
        self.spirit_burst_ex_spin.setVisible(is_unity)
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
        
        # Rest in June
        self.rest_in_june.blockSignals(True)
        self.rest_in_june.setChecked(training.get("rest_in_june", False))
        self.rest_in_june.blockSignals(False)

        self.skip_goal_check.blockSignals(True)
        self.skip_goal_check.setChecked(training.get("skip_goal_check", False))
        self.skip_goal_check.blockSignals(False)

        self.skip_infirmary_check_on_new_turn.blockSignals(True)
        self.skip_infirmary_check_on_new_turn.setChecked(training.get("skip_infirmary_check_on_new_turn", False))
        self.skip_infirmary_check_on_new_turn.blockSignals(False)
        
        # Gambling Train
        self.gambling_train.blockSignals(True)
        self.gambling_train.setChecked(training.get("gambling_train_enabled", False))
        self.gambling_train.blockSignals(False)
        
        self.gambling_failure_spin.blockSignals(True)
        self.gambling_failure_spin.setValue(training.get("gambling_train_failure_increase", 5))
        self.gambling_failure_spin.blockSignals(False)
        
        self.gambling_score_spin.blockSignals(True)
        self.gambling_score_spin.setValue(training.get("gambling_train_score_per_increase", 1.0))
        self.gambling_score_spin.blockSignals(False)
        
        # Update gambling settings visibility
        self.gambling_settings_widget.setVisible(self.gambling_train.isChecked())

        duel_allowed_trainings = self._normalize_duel_allowed_trainings(
            training.get("duel_allowed_trainings", self.DEFAULT_DUEL_ALLOWED_TRAININGS)
        )
        for stat, cb in self.duel_allowed_training_vars.items():
            cb.blockSignals(True)
            cb.setChecked(stat in duel_allowed_trainings)
            cb.blockSignals(False)

        duel_choices = self._normalize_duel_choices(training.get("duel_choices", self.DEFAULT_DUEL_CHOICES))
        for stat, cb in self.duel_choice_vars.items():
            cb.blockSignals(True)
            cb.setChecked(stat in duel_choices)
            cb.blockSignals(False)
        self._sync_duel_priority_list(duel_choices)

        self.soft_cap_enabled.blockSignals(True)
        self.soft_cap_enabled.setChecked(training.get("soft_cap_enabled", False))
        self.soft_cap_enabled.blockSignals(False)
        
        spirit_burst_stats = training.get("spirit_burst_enabled_stats", [])
        for stat, cb in self.spirit_burst_vars.items():
            cb.blockSignals(True)
            cb.setChecked(stat in spirit_burst_stats)
            cb.blockSignals(False)

        spirit_burst_ex_stats = training.get("spirit_burst_ex_enabled_stats", [])
        for stat, cb in self.spirit_burst_ex_vars.items():
            cb.blockSignals(True)
            cb.setChecked(stat in spirit_burst_ex_stats)
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

        soft_stat_caps = training.get("soft_stat_caps", {})
        for stat, spin in self.soft_cap_spins.items():
            spin.blockSignals(True)
            spin.setValue(soft_stat_caps.get(stat, stat_caps.get(stat, 600)))
            spin.blockSignals(False)

        self.soft_cap_widget.setVisible(self.soft_cap_enabled.isChecked())
        
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
        self.duel_group.setVisible(mode == "ura")
        self._update_unity_score_visibility()

    def _normalize_duel_choices(self, choices):
        """Return valid duel choices, preserving configured priority order."""
        valid = [key for key, _ in self.DUEL_STAT_DISPLAY]
        if not isinstance(choices, list):
            choices = self.DEFAULT_DUEL_CHOICES

        normalized = []
        for choice in choices:
            if choice in valid and choice not in normalized:
                normalized.append(choice)
        return normalized

    def _normalize_duel_allowed_trainings(self, trainings):
        """Return valid training types where Happy Meek's Duel can score."""
        valid = [key for key, _ in self.TRAINING_STAT_DISPLAY]
        if not isinstance(trainings, list):
            trainings = self.DEFAULT_DUEL_ALLOWED_TRAININGS

        normalized = []
        for training in trainings:
            if training in valid and training not in normalized:
                normalized.append(training)
        return normalized

    def _sync_duel_priority_list(self, ordered_choices=None):
        """Mirror checked duel choices into the draggable priority list."""
        self._syncing_duel_priority = True
        try:
            if ordered_choices is None:
                ordered_choices = self._get_duel_priority_order()
            ordered_choices = self._normalize_duel_choices(ordered_choices)

            checked = [key for key, _ in self.DUEL_STAT_DISPLAY if self.duel_choice_vars[key].isChecked()]
            ordered = [key for key in ordered_choices if key in checked]
            ordered.extend(key for key in checked if key not in ordered)

            display = dict(self.DUEL_STAT_DISPLAY)
            self.duel_priority_list.clear()
            for stat in ordered:
                item = QListWidgetItem(display[stat])
                item.setData(Qt.UserRole, stat)
                item.setTextAlignment(Qt.AlignCenter)
                self.duel_priority_list.addItem(item)
        finally:
            self._syncing_duel_priority = False

    def _get_duel_priority_order(self):
        order = []
        for i in range(self.duel_priority_list.count()):
            item = self.duel_priority_list.item(i)
            if item:
                order.append(item.data(Qt.UserRole))
        return order

    def _get_training_score_filename(self, mode):
        """Return the training score config file for the active mode."""
        if mode == "unity":
            return "training_score_unity.json"
        if mode == "trackblazer":
            return "training_score_trackblazer.json"
        return "training_score.json"
    
    def _on_priority_changed(self, order):
        """Handle priority order change"""
        if not getattr(self, '_loading', False):
            self._save_training()

    def _on_duel_priority_changed(self, order):
        """Handle duel priority order change."""
        if not getattr(self, '_loading', False) and not getattr(self, '_syncing_duel_priority', False):
            self._save_training()

    def _on_duel_whitelist_changed(self):
        """Handle duel whitelist checkbox changes."""
        if getattr(self, '_loading', False):
            return
        self._sync_duel_priority_list()
        self._save_training()
    
    def _on_gambling_train_toggle(self):
        """Handle gambling train checkbox toggle"""
        self.gambling_settings_widget.setVisible(self.gambling_train.isChecked())
        if not getattr(self, '_loading', False):
            self._save_training()

    def _on_soft_cap_toggle(self):
        """Handle soft cap checkbox toggle"""
        self.soft_cap_widget.setVisible(self.soft_cap_enabled.isChecked())
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
        config["training"]["rest_in_june"] = self.rest_in_june.isChecked()
        config["training"]["skip_goal_check"] = self.skip_goal_check.isChecked()
        config["training"]["skip_infirmary_check_on_new_turn"] = self.skip_infirmary_check_on_new_turn.isChecked()
        
        # Gambling Train
        config["training"]["gambling_train_enabled"] = self.gambling_train.isChecked()
        config["training"]["gambling_train_failure_increase"] = self.gambling_failure_spin.value()
        config["training"]["gambling_train_score_per_increase"] = self.gambling_score_spin.value()
        config["training"]["duel_allowed_trainings"] = [
            stat for stat, cb in self.duel_allowed_training_vars.items() if cb.isChecked()
        ]
        config["training"]["duel_choices"] = self._get_duel_priority_order()
        
        # Unity mode fields
        if "dating" not in config:
            config["dating"] = {}
        config["dating"]["use_dating_instead_of_rest"] = self.use_dating.isChecked()
        
        config["training"]["spirit_burst_enabled_stats"] = [
            stat for stat, cb in self.spirit_burst_vars.items() if cb.isChecked()
        ]
        config["training"]["spirit_burst_ex_enabled_stats"] = [
            stat for stat, cb in self.spirit_burst_ex_vars.items() if cb.isChecked()
        ]
        
        # Min scores
        config["training"]["min_score"] = {stat: spin.value() for stat, spin in self.score_spins.items()}
        
        # Stat caps
        config["training"]["soft_cap_enabled"] = self.soft_cap_enabled.isChecked()
        config["training"]["soft_stat_caps"] = {stat: spin.value() for stat, spin in self.soft_cap_spins.items()}
        config["training"]["stat_caps"] = {stat: spin.value() for stat, spin in self.cap_spins.items()}
        
        # Actually save to file
        self.main_window.save_config()
    
    def _load_training_score_config(self):
        """Load training score settings from JSON file"""
        import json
        import os
        
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        filename = self._get_training_score_filename(mode)
        
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # Get scoring_rules from the nested structure
                    score_config = file_config.get("scoring_rules", {})
            else:
                score_config = {}
        except Exception:
            score_config = {}
        
        # Helper to get points from nested rule structure
        def get_points(rule_name, default):
            rule = score_config.get(rule_name, {})
            if isinstance(rule, dict):
                return rule.get("points", default)
            return default
        
        # Load common score settings
        self.rainbow_spin.blockSignals(True)
        self.rainbow_spin.setValue(get_points("rainbow_support", 1.0))
        self.rainbow_spin.blockSignals(False)
        
        self.low_bond_spin.blockSignals(True)
        self.low_bond_spin.setValue(get_points("not_rainbow_support_low", 0.7))
        self.low_bond_spin.blockSignals(False)
        
        self.high_bond_spin.blockSignals(True)
        self.high_bond_spin.setValue(get_points("not_rainbow_support_high", 0.0))
        self.high_bond_spin.blockSignals(False)
        
        self.hint_spin.blockSignals(True)
        self.hint_spin.setValue(get_points("hint", 0.3))
        self.hint_spin.blockSignals(False)
        
        self.friend_support_spin.blockSignals(True)
        self.friend_support_spin.setValue(get_points("friend_support", 0.5))
        self.friend_support_spin.blockSignals(False)

        self.happy_meeks_duel_spin.blockSignals(True)
        self.happy_meeks_duel_spin.setValue(get_points("happy_meeks_duel", 1.0))
        self.happy_meeks_duel_spin.blockSignals(False)
        
        # Load Unity-specific score settings (use spririt_training key for backward compat)
        self.spirit_training_spin.blockSignals(True)
        self.spirit_training_spin.setValue(get_points("spririt_training", 0.5))
        self.spirit_training_spin.blockSignals(False)
        
        self.spirit_burst_spin.blockSignals(True)
        self.spirit_burst_spin.setValue(get_points("spirit_burst", 1.0))
        self.spirit_burst_spin.blockSignals(False)

        self.spirit_burst_ex_spin.blockSignals(True)
        self.spirit_burst_ex_spin.setValue(get_points("spirit_burst_ex", 1.0))
        self.spirit_burst_ex_spin.blockSignals(False)
        
        self.spirit_training_extra_spin.blockSignals(True)
        self.spirit_training_extra_spin.setValue(get_points("spirit_training_extra", 0.2))
        self.spirit_training_extra_spin.blockSignals(False)
    
    def _save_training_score_config(self):
        """Save training score settings to JSON file"""
        import json
        import os
        
        config = self.main_window.get_config()
        mode = config.get("mode", "ura")
        filename = self._get_training_score_filename(mode)
        
        # Build scoring_rules with proper nested structure
        scoring_rules = {
            "rainbow_support": {
                "description": "Same type support card with bond level >= 4",
                "points": self.rainbow_spin.value()
            },
            "not_rainbow_support_low": {
                "description": "Support with bond level < 4",
                "points": self.low_bond_spin.value()
            },
            "not_rainbow_support_high": {
                "description": "Not same type support with bond level >= 4 (no need to get more bond)",
                "points": self.high_bond_spin.value()
            },
            "hint": {
                "description": "Hint icon present",
                "points": self.hint_spin.value()
            },
            "friend_support": {
                "description": "Friend support card with bond < 3",
                "points": self.friend_support_spin.value()
            }
        }

        if mode == "ura":
            scoring_rules["happy_meeks_duel"] = {
                "description": "Happy Meek's Duel icon present",
                "points": self.happy_meeks_duel_spin.value()
            }
        
        # Add Unity-specific settings for unity mode
        if mode == "unity":
            scoring_rules["spririt_training"] = {
                "description": "Spirit training",
                "points": self.spirit_training_spin.value()
            }
            scoring_rules["spirit_burst"] = {
                "description": "Spirit burst",
                "points": self.spirit_burst_spin.value()
            }
            scoring_rules["spirit_burst_ex"] = {
                "description": "Spirit Burst Extreme",
                "points": self.spirit_burst_ex_spin.value()
            }
            scoring_rules["spirit_training_extra"] = {
                "description": "Spirit training after burst (Set this lower if you priortize gaining burst)",
                "points": self.spirit_training_extra_spin.value()
            }
        
        file_config = {"scoring_rules": scoring_rules}
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(file_config, f, indent=2)
        except Exception as e:
            print(f"Failed to save training score config: {e}")
    
    def _on_training_score_change(self):
        """Handle training score changes - save to JSON file"""
        if not getattr(self, '_loading', False):
            self._save_training_score_config()

