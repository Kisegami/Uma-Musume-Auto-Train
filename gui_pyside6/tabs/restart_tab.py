"""
Restart Tab for PySide6 GUI
Contains restart career settings and support card templates.
Matches original GUI with template-based support selection.
"""

import os
import glob
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QGroupBox, QGridLayout, QFrame, QScrollArea, QCheckBox, 
    QPushButton, QRadioButton, QButtonGroup, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

from ..styles import COLORS


class RestartTab(QScrollArea):
    """Restart configuration tab - matches original GUI with templates"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        
        self._create_ui()
        self.load_config()
    
    def _get_supports_dir(self):
        """Return the supports template directory"""
        supports_dir = os.path.join("template", "supports")
        os.makedirs(supports_dir, exist_ok=True)
        return supports_dir
    
    def _load_support_templates(self):
        """Load available support templates (PNG files)"""
        supports_dir = self._get_supports_dir()
        templates = []
        if os.path.exists(supports_dir):
            templates = [f for f in os.listdir(supports_dir) if f.lower().endswith(".png")]
            templates.sort()
        return templates
    
    def _create_ui(self):
        """Create restart tab UI matching original"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ==================== Restart Career Settings ====================
        restart_group = QGroupBox("Restart Career Settings")
        restart_layout = QVBoxLayout(restart_group)
        restart_layout.setSpacing(12)
        
        # Restart Career Run checkbox
        self.restart_enabled = QCheckBox("Restart Career run")
        self.restart_enabled.stateChanged.connect(self._toggle_restart_settings)
        restart_layout.addWidget(self.restart_enabled)
        
        # Restart criteria frame (hidden when disabled)
        self.criteria_widget = QWidget()
        criteria_layout = QVBoxLayout(self.criteria_widget)
        criteria_layout.setContentsMargins(0, 8, 0, 0)
        criteria_layout.setSpacing(8)
        
        criteria_layout.addWidget(QLabel("Restart Criteria (choose one):"))
        
        # Radio button group
        self.criteria_group = QButtonGroup()
        
        # Times option
        times_widget = QWidget()
        times_layout = QHBoxLayout(times_widget)
        times_layout.setContentsMargins(0, 0, 0, 0)
        
        self.times_radio = QRadioButton("Restart career")
        self.times_radio.setChecked(True)
        self.criteria_group.addButton(self.times_radio, 0)
        times_layout.addWidget(self.times_radio)
        
        self.restart_times_spin = QSpinBox()
        self.restart_times_spin.setRange(0, 999)
        self.restart_times_spin.valueChanged.connect(self._save_restart)
        times_layout.addWidget(self.restart_times_spin)
        
        times_layout.addWidget(QLabel("times"))
        times_layout.addStretch()
        criteria_layout.addWidget(times_widget)
        
        # Fans option
        fans_widget = QWidget()
        fans_layout = QHBoxLayout(fans_widget)
        fans_layout.setContentsMargins(0, 0, 0, 0)
        
        self.fans_radio = QRadioButton("Run until achieve")
        self.criteria_group.addButton(self.fans_radio, 1)
        fans_layout.addWidget(self.fans_radio)
        
        self.total_fans_spin = QSpinBox()
        self.total_fans_spin.setRange(0, 999999999)
        self.total_fans_spin.valueChanged.connect(self._save_restart)
        fans_layout.addWidget(self.total_fans_spin)
        
        fans_layout.addWidget(QLabel("fans"))
        fans_layout.addStretch()
        criteria_layout.addWidget(fans_widget)
        
        self.criteria_group.buttonClicked.connect(self._on_criteria_change)
        
        restart_layout.addWidget(self.criteria_widget)
        layout.addWidget(restart_group)
        
        # ==================== Support Templates Section ====================
        self.support_group = QGroupBox("Support Templates")
        support_layout = QVBoxLayout(self.support_group)
        support_layout.setSpacing(12)
        
        # Use Support Templates checkbox
        self.use_templates = QCheckBox("Use Support cards template")
        self.use_templates.stateChanged.connect(self._toggle_template_controls)
        support_layout.addWidget(self.use_templates)
        
        # Template selection row (hidden when disabled)
        self.template_row = QWidget()
        template_row_layout = QHBoxLayout(self.template_row)
        template_row_layout.setContentsMargins(0, 0, 0, 0)
        
        template_row_layout.addWidget(QLabel("Template:"))
        
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(180)
        self._refresh_template_dropdown()
        self.template_combo.currentTextChanged.connect(self._save_restart)
        template_row_layout.addWidget(self.template_combo)
        
        add_btn = QPushButton("Add New")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_template)
        template_row_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_template)
        template_row_layout.addWidget(remove_btn)
        
        template_row_layout.addStretch()
        support_layout.addWidget(self.template_row)
        
        layout.addWidget(self.support_group)
        
        layout.addStretch()
        self.setWidget(container)
    
    def _refresh_template_dropdown(self):
        """Refresh the template dropdown"""
        self.template_combo.blockSignals(True)
        current = self.template_combo.currentText()
        self.template_combo.clear()
        templates = self._load_support_templates()
        if templates:
            self.template_combo.addItems(templates)
            if current in templates:
                self.template_combo.setCurrentText(current)
        else:
            self.template_combo.addItem("No templates")
        self.template_combo.blockSignals(False)
    
    def _toggle_restart_settings(self):
        """Toggle visibility of restart settings"""
        enabled = self.restart_enabled.isChecked()
        self.criteria_widget.setVisible(enabled)
        self.support_group.setVisible(enabled)
        self._save_restart()
    
    def _toggle_template_controls(self):
        """Toggle visibility of template controls"""
        self.template_row.setVisible(self.use_templates.isChecked())
        self._save_restart()
    
    def _on_criteria_change(self):
        """Handle criteria radio button change"""
        if self.times_radio.isChecked():
            self.total_fans_spin.setValue(0)
        else:
            self.restart_times_spin.setValue(0)
        self._save_restart()
    
    def load_config(self):
        """Load config values"""
        self._loading = True
        config = self.main_window.get_config()
        restart = config.get("restart_career", {})
        auto_start = config.get("auto_start_career", {})
        
        # Restart enabled
        self.restart_enabled.blockSignals(True)
        self.restart_enabled.setChecked(restart.get("restart_enabled", False))
        self.restart_enabled.blockSignals(False)
        
        # Criteria
        if restart.get("total_fans_requirement", 0) > 0:
            self.fans_radio.setChecked(True)
        else:
            self.times_radio.setChecked(True)
        
        self.restart_times_spin.blockSignals(True)
        self.restart_times_spin.setValue(restart.get("restart_times", 5))
        self.restart_times_spin.blockSignals(False)
        
        self.total_fans_spin.blockSignals(True)
        self.total_fans_spin.setValue(restart.get("total_fans_requirement", 0))
        self.total_fans_spin.blockSignals(False)
        
        # Support templates
        self.use_templates.blockSignals(True)
        self.use_templates.setChecked(auto_start.get("use_support_templates", False))
        self.use_templates.blockSignals(False)
        
        template_name = auto_start.get("support_template_name", "")
        if template_name:
            idx = self.template_combo.findText(template_name)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        
        # Update visibility
        self.criteria_widget.setVisible(self.restart_enabled.isChecked())
        self.support_group.setVisible(self.restart_enabled.isChecked())
        self.template_row.setVisible(self.use_templates.isChecked())
        
        self._loading = False
    
    def _save_restart(self):
        """Save restart settings"""
        if getattr(self, '_loading', False):
            return
        
        config = self.main_window.get_config()
        
        # Restart career
        if "restart_career" not in config:
            config["restart_career"] = {}
        
        config["restart_career"]["restart_enabled"] = self.restart_enabled.isChecked()
        
        if self.times_radio.isChecked():
            config["restart_career"]["restart_times"] = self.restart_times_spin.value()
            config["restart_career"]["total_fans_requirement"] = 0
        else:
            config["restart_career"]["restart_times"] = 0
            config["restart_career"]["total_fans_requirement"] = self.total_fans_spin.value()
        
        # Auto start career
        if "auto_start_career" not in config:
            config["auto_start_career"] = {}
        
        config["auto_start_career"]["use_support_templates"] = self.use_templates.isChecked()
        template = self.template_combo.currentText()
        if template != "No templates":
            config["auto_start_career"]["support_template_name"] = template
        
        self.main_window.save_config()
    
    def _add_template(self):
        """Add new support template - placeholder for screenshot crop"""
        QMessageBox.information(
            self, "Add Template", 
            "To add a support template:\n"
            "1. Take a screenshot of your support card lineup\n"
            "2. Save it as a PNG file in template/supports/\n\n"
            "The template will be used to match support cards during restart."
        )
        self._refresh_template_dropdown()
    
    def _remove_template(self):
        """Remove selected template"""
        template = self.template_combo.currentText()
        if not template or template == "No templates":
            return
        
        reply = QMessageBox.question(self, "Confirm", f"Remove template '{template}'?")
        if reply == QMessageBox.Yes:
            path = os.path.join(self._get_supports_dir(), template)
            if os.path.exists(path):
                os.remove(path)
            self._refresh_template_dropdown()
