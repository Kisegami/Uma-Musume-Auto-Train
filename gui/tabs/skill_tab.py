"""
Skill Tab for PySide6 GUI
Contains skill purchase settings and skill template management.
Matches original GUI exactly.
"""

import os
import json
import glob
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QCheckBox, QPushButton,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class SkillTab(QScrollArea):
    """Skill configuration tab - matches original GUI"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _create_ui(self):
        """Create skill tab UI matching original"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== Skill Management Section ====================
        skill_group = QGroupBox("Skill Management")
        skill_layout = QVBoxLayout(skill_group)
        skill_layout.setSpacing(12)
        
        # Enable Skill Point Check
        self.enable_skill_check = QCheckBox("Enable Skill Point check and Skill Purchase")
        self.enable_skill_check.stateChanged.connect(self._toggle_skill_settings)
        skill_layout.addWidget(self.enable_skill_check)
        
        # Settings container (hidden when disabled)
        self.settings_widget = QWidget()
        settings_layout = QGridLayout(self.settings_widget)
        settings_layout.setSpacing(12)
        
        # Skill Point Cap
        settings_layout.addWidget(QLabel("Skill Point Cap:"), 0, 0)
        self.skill_cap_spin = QSpinBox()
        self.skill_cap_spin.setRange(0, 9999)
        self.skill_cap_spin.valueChanged.connect(self._save_skill)
        settings_layout.addWidget(self.skill_cap_spin, 0, 1)
        
        # Skill Purchase Mode
        settings_layout.addWidget(QLabel("Skill Purchase Mode:"), 1, 0)
        self.purchase_combo = QComboBox()
        self.purchase_combo.addItems(['auto', 'manual'])
        self.purchase_combo.currentTextChanged.connect(self._toggle_auto_settings)
        settings_layout.addWidget(self.purchase_combo, 1, 1)
        
        skill_layout.addWidget(self.settings_widget)
        
        # Auto-specific settings
        self.auto_widget = QWidget()
        auto_layout = QHBoxLayout(self.auto_widget)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        
        auto_layout.addWidget(QLabel("Skill Template:"))
        
        self.skill_dropdown = QComboBox()
        self.skill_dropdown.setMinimumWidth(180)
        self._load_skill_templates()
        self.skill_dropdown.currentTextChanged.connect(self._save_skill)
        auto_layout.addWidget(self.skill_dropdown)
        
        add_btn = QPushButton("Add New")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_template)
        auto_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_template)
        auto_layout.addWidget(remove_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("accent")
        edit_btn.clicked.connect(self._edit_template)
        auto_layout.addWidget(edit_btn)
        
        auto_layout.addStretch()
        skill_layout.addWidget(self.auto_widget)
        
        layout.addWidget(skill_group)
        
        # ==================== End Skill Template Section ====================
        self.end_skill_group = QGroupBox("End Skill Template (Restart Career)")
        end_skill_layout = QVBoxLayout(self.end_skill_group)
        end_skill_layout.setSpacing(12)
        
        # Note label
        note_label = QLabel("⚠️ Used automatically when Restart Career is enabled")
        note_label.setStyleSheet(f"color: {COLORS['accent_orange']}; font-size: 11px;")
        end_skill_layout.addWidget(note_label)
        
        # End skill template selection (always visible)
        self.end_skill_widget = QWidget()
        end_skill_row_layout = QHBoxLayout(self.end_skill_widget)
        end_skill_row_layout.setContentsMargins(0, 0, 0, 0)
        
        end_skill_row_layout.addWidget(QLabel("End Skill Template:"))
        
        self.end_skill_dropdown = QComboBox()
        self.end_skill_dropdown.setMinimumWidth(180)
        self._load_end_skill_templates()
        self.end_skill_dropdown.currentTextChanged.connect(self._save_end_skill)
        end_skill_row_layout.addWidget(self.end_skill_dropdown)
        
        end_add_btn = QPushButton("Add New")
        end_add_btn.setObjectName("primary")
        end_add_btn.clicked.connect(self._add_end_skill_template)
        end_skill_row_layout.addWidget(end_add_btn)
        
        end_remove_btn = QPushButton("Remove")
        end_remove_btn.setObjectName("danger")
        end_remove_btn.clicked.connect(self._remove_end_skill_template)
        end_skill_row_layout.addWidget(end_remove_btn)
        
        end_edit_btn = QPushButton("Edit")
        end_edit_btn.setObjectName("accent")
        end_edit_btn.clicked.connect(self._edit_end_skill_template)
        end_skill_row_layout.addWidget(end_edit_btn)
        
        end_skill_row_layout.addStretch()
        end_skill_layout.addWidget(self.end_skill_widget)
        
        layout.addWidget(self.end_skill_group)
        
        # ==================== Support Card Filter Section ====================
        self.support_filter_group = QGroupBox("Support Card Filter (Restart Career)")
        support_filter_layout = QGridLayout(self.support_filter_group)
        support_filter_layout.setSpacing(12)
        
        # Note label
        support_note = QLabel("⚠️ These filters are checked via OCR during auto start career")
        support_note.setStyleSheet(f"color: {COLORS['accent_orange']}; font-size: 11px;")
        support_filter_layout.addWidget(support_note, 0, 0, 1, 2)
        
        # Support Speciality
        support_filter_layout.addWidget(QLabel("Support Speciality:"), 1, 0)
        self.speciality_combo = QComboBox()
        self.speciality_combo.addItems(["SPD", "STA", "PWR", "GUTS", "WIT", "PAL"])
        self.speciality_combo.currentTextChanged.connect(self._save_support_filter)
        support_filter_layout.addWidget(self.speciality_combo, 1, 1)
        
        # Support Rarity
        support_filter_layout.addWidget(QLabel("Support Rarity:"), 2, 0)
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["R", "SR", "SSR"])
        self.rarity_combo.currentTextChanged.connect(self._save_support_filter)
        support_filter_layout.addWidget(self.rarity_combo, 2, 1)
        
        layout.addWidget(self.support_filter_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _get_skills_dir(self):
        """Get skills template directory"""
        skills_dir = os.path.join("template", "skills")
        os.makedirs(skills_dir, exist_ok=True)
        return skills_dir
    
    def _load_skill_templates(self):
        """Load available skill templates"""
        self.skill_dropdown.clear()
        skills_dir = self._get_skills_dir()
        if os.path.exists(skills_dir):
            files = glob.glob(os.path.join(skills_dir, "*.json"))
            for f in sorted(files):
                self.skill_dropdown.addItem(os.path.basename(f))
        if self.skill_dropdown.count() == 0:
            self.skill_dropdown.addItem("skills.json")
    
    def _toggle_skill_settings(self):
        """Toggle skill settings visibility"""
        enabled = self.enable_skill_check.isChecked()
        self.settings_widget.setVisible(enabled)
        self.auto_widget.setVisible(enabled and self.purchase_combo.currentText() == 'auto')
        self._save_skill()
    
    def _toggle_auto_settings(self):
        """Toggle auto-specific settings visibility"""
        self.auto_widget.setVisible(
            self.enable_skill_check.isChecked() and 
            self.purchase_combo.currentText() == 'auto'
        )
        self._save_skill()
    
    def load_config(self):
        """Load config values"""
        self._loading = True
        config = self.main_window.get_config()
        skills = config.get("skills", {})
        restart = config.get("restart_career", {})
        
        self.enable_skill_check.blockSignals(True)
        self.enable_skill_check.setChecked(skills.get("enable_skill_point_check", True))
        self.enable_skill_check.blockSignals(False)
        
        self.skill_cap_spin.blockSignals(True)
        self.skill_cap_spin.setValue(skills.get("skill_point_cap", 400))
        self.skill_cap_spin.blockSignals(False)
        
        self.purchase_combo.blockSignals(True)
        self.purchase_combo.setCurrentText(skills.get("skill_purchase", "auto"))
        self.purchase_combo.blockSignals(False)
        
        # Skill file
        skill_file = skills.get("skill_file", "skills.json")
        if "/" in skill_file or "\\" in skill_file:
            skill_file = os.path.basename(skill_file)
        idx = self.skill_dropdown.findText(skill_file)
        if idx >= 0:
            self.skill_dropdown.setCurrentIndex(idx)
        
        # Update visibility without triggering save
        enabled = self.enable_skill_check.isChecked()
        self.settings_widget.setVisible(enabled)
        self.auto_widget.setVisible(enabled and self.purchase_combo.currentText() == 'auto')
        
        # End skill file
        end_skill_file = restart.get("end_skill_file", "default.json")
        if "/" in end_skill_file or "\\" in end_skill_file:
            end_skill_file = os.path.basename(end_skill_file)
        idx = self.end_skill_dropdown.findText(end_skill_file)
        if idx >= 0:
            self.end_skill_dropdown.setCurrentIndex(idx)
            
        # Support Filters
        auto_start = config.get("auto_start_career", {})
        
        self.speciality_combo.blockSignals(True)
        self.speciality_combo.setCurrentText(auto_start.get("support_speciality", "STA"))
        self.speciality_combo.blockSignals(False)
        
        self.rarity_combo.blockSignals(True)
        self.rarity_combo.setCurrentText(auto_start.get("support_rarity", "SSR"))
        self.rarity_combo.blockSignals(False)
        
        self._loading = False
    
    def _save_skill(self):
        """Save skill settings"""
        if getattr(self, '_loading', False):
            return
        
        config = self.main_window.get_config()
        if "skills" not in config:
            config["skills"] = {}
        
        config["skills"]["enable_skill_point_check"] = self.enable_skill_check.isChecked()
        config["skills"]["skill_point_cap"] = self.skill_cap_spin.value()
        config["skills"]["skill_purchase"] = self.purchase_combo.currentText()
        config["skills"]["skill_file"] = f"template/skills/{self.skill_dropdown.currentText()}"
        
        self.main_window.save_config()
    
    def _add_template(self):
        """Add new skill template"""
        name, ok = QInputDialog.getText(self, "New Template", "Enter template name:")
        if ok and name.strip():
            safe_name = name.strip()
            if not safe_name.endswith(".json"):
                safe_name += ".json"
            path = os.path.join(self._get_skills_dir(), safe_name)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2)
            self._load_skill_templates()
            idx = self.skill_dropdown.findText(safe_name)
            if idx >= 0:
                self.skill_dropdown.setCurrentIndex(idx)
    
    def _remove_template(self):
        """Remove selected template"""
        filename = self.skill_dropdown.currentText()
        if not filename:
            return
        reply = QMessageBox.question(self, "Confirm", f"Remove '{filename}'?")
        if reply == QMessageBox.Yes:
            path = os.path.join(self._get_skills_dir(), filename)
            if os.path.exists(path):
                os.remove(path)
            self._load_skill_templates()
    
    def _edit_template(self):
        """Edit selected template"""
        filename = self.skill_dropdown.currentText()
        if not filename or filename == "skills.json" and not os.path.exists(os.path.join(self._get_skills_dir(), filename)):
            # Create default if not exists
            path = os.path.join(self._get_skills_dir(), filename)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2)
        
        skill_file = os.path.join(self._get_skills_dir(), filename)
        
        from .skill_list_window import SkillListWindow
        dialog = SkillListWindow(self, skill_file)
        dialog.exec()
    
    # ==================== End Skill Template Methods ====================
    
    def _get_end_skill_dir(self):
        """Get End_skill template directory"""
        end_skill_dir = os.path.join("template", "End_skill")
        os.makedirs(end_skill_dir, exist_ok=True)
        return end_skill_dir
    
    def _load_end_skill_templates(self):
        """Load available end skill templates"""
        self.end_skill_dropdown.clear()
        end_skill_dir = self._get_end_skill_dir()
        if os.path.exists(end_skill_dir):
            files = glob.glob(os.path.join(end_skill_dir, "*.json"))
            for f in sorted(files):
                self.end_skill_dropdown.addItem(os.path.basename(f))
        if self.end_skill_dropdown.count() == 0:
            self.end_skill_dropdown.addItem("default.json")
    
    
    def _save_end_skill(self):
        """Save end skill settings to restart_career config"""
        if getattr(self, '_loading', False):
            return
        
        config = self.main_window.get_config()
        if "restart_career" not in config:
            config["restart_career"] = {}
        

        config["restart_career"]["end_skill_file"] = f"template/End_skill/{self.end_skill_dropdown.currentText()}"
        
        self.main_window.save_config()
        
    def _save_support_filter(self):
        """Save support filter settings to auto_start_career config"""
        if getattr(self, '_loading', False):
            return
            
        config = self.main_window.get_config()
        if "auto_start_career" not in config:
            config["auto_start_career"] = {}
            
        config["auto_start_career"]["support_speciality"] = self.speciality_combo.currentText()
        config["auto_start_career"]["support_rarity"] = self.rarity_combo.currentText()
        
        self.main_window.save_config()
    
    def _add_end_skill_template(self):
        """Add new end skill template"""
        name, ok = QInputDialog.getText(self, "New End Skill Template", "Enter template name:")
        if ok and name.strip():
            safe_name = name.strip()
            if not safe_name.endswith(".json"):
                safe_name += ".json"
            path = os.path.join(self._get_end_skill_dir(), safe_name)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2)
            self._load_end_skill_templates()
            idx = self.end_skill_dropdown.findText(safe_name)
            if idx >= 0:
                self.end_skill_dropdown.setCurrentIndex(idx)
    
    def _remove_end_skill_template(self):
        """Remove selected end skill template"""
        filename = self.end_skill_dropdown.currentText()
        if not filename:
            return
        reply = QMessageBox.question(self, "Confirm", f"Remove '{filename}'?")
        if reply == QMessageBox.Yes:
            path = os.path.join(self._get_end_skill_dir(), filename)
            if os.path.exists(path):
                os.remove(path)
            self._load_end_skill_templates()
    
    def _edit_end_skill_template(self):
        """Edit selected end skill template"""
        filename = self.end_skill_dropdown.currentText()
        if not filename:
            return
        
        path = os.path.join(self._get_end_skill_dir(), filename)
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2)
        
        from .skill_list_window import SkillListWindow
        dialog = SkillListWindow(self, path)
        dialog.exec()
