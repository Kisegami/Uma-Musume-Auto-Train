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
from PySide6.QtGui import QPixmap

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
        
        criteria_layout.addWidget(fans_widget)
        
        # Restore TP checkbox
        self.restore_tp_checkbox = QCheckBox("Restore TP using TP Bottle")
        self.restore_tp_checkbox.stateChanged.connect(self._on_restore_tp_changed)
        criteria_layout.addWidget(self.restore_tp_checkbox)
        
        # Restore TP Carats checkbox
        self.restore_tp_carats_checkbox = QCheckBox("Use Carats to restore TP (needs \"Restore TP using TP Bottle\")")
        self.restore_tp_carats_checkbox.stateChanged.connect(self._save_restart)
        self.restore_tp_carats_checkbox.setEnabled(False) # Default to false until config is loaded
        criteria_layout.addWidget(self.restore_tp_carats_checkbox)
        
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
        
        # Template preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(100)
        self.preview_label.setStyleSheet("background-color: #2a2a2a; border-radius: 8px; padding: 8px;")
        support_layout.addWidget(self.preview_label)
        
        # Connect template change to preview update
        self.template_combo.currentTextChanged.connect(self._update_template_preview)
        
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
        visible = self.use_templates.isChecked()
        self.template_row.setVisible(visible)
        self.preview_label.setVisible(visible)
        if visible:
            self._update_template_preview()
        self._save_restart()
    
    def _update_template_preview(self):
        """Update the template preview image"""
        template = self.template_combo.currentText()
        if not template or template == "No templates":
            self.preview_label.setText("No template selected")
            self.preview_label.setPixmap(QPixmap())
            return
        
        path = os.path.join(self._get_supports_dir(), template)
        if not os.path.exists(path):
            self.preview_label.setText("Template file not found")
            self.preview_label.setPixmap(QPixmap())
            return
        
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.preview_label.setText("Failed to load image")
                return
            
            # Scale to fit, max height 200px
            scaled = pixmap.scaledToHeight(200, Qt.SmoothTransformation)
            if scaled.width() > 400:
                scaled = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
            
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText("")
        except Exception as e:
            self.preview_label.setText(f"Error: {e}")
    
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
        
        # Restore TP
        self.restore_tp_checkbox.blockSignals(True)
        self.restore_tp_checkbox.setChecked(auto_start.get("auto_charge_tp", True))
        self.restore_tp_checkbox.blockSignals(False)
        
        self.restore_tp_carats_checkbox.blockSignals(True)
        self.restore_tp_carats_checkbox.setChecked(auto_start.get("auto_charge_tp_carats", False))
        # Initial state for Carats checkbox based on TP bottle checkbox
        self.restore_tp_carats_checkbox.setEnabled(self.restore_tp_checkbox.isChecked())
        self.restore_tp_carats_checkbox.blockSignals(False)
        
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
        visible = self.use_templates.isChecked()
        self.template_row.setVisible(visible)
        self.preview_label.setVisible(visible)
        if visible:
            self._update_template_preview()
        
        self._loading = False
    
    def _on_restore_tp_changed(self, state):
        """Handle auto charge config value and dependent checkboxes"""
        is_checked = state == Qt.CheckState.Checked.value
        self.restore_tp_carats_checkbox.setEnabled(is_checked)
        if not is_checked:
            self.restore_tp_carats_checkbox.setChecked(False)
        self._save_restart()
    
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
        config["auto_start_career"]["auto_charge_tp"] = self.restore_tp_checkbox.isChecked()
        config["auto_start_career"]["auto_charge_tp_carats"] = self.restore_tp_carats_checkbox.isChecked()
        template = self.template_combo.currentText()
        if template != "No templates":
            config["auto_start_career"]["support_template_name"] = template
        
        self.main_window.save_config()
    
    def _add_template(self):
        """Capture emulator screen, crop, and save as a new template."""
        try:
            from utils.screenshot import take_screenshot
        except ImportError:
            QMessageBox.warning(
                self, "Error",
                "Screenshot module not available.\n\n"
                "To add a support template manually:\n"
                "1. Take a screenshot of your support card lineup\n"
                "2. Save it as a PNG file in template/supports/"
            )
            return
        
        # Take screenshot
        try:
            screenshot = take_screenshot()
            if screenshot is None:
                QMessageBox.warning(self, "Error", "Failed to take screenshot. Make sure emulator is running.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to take screenshot: {e}")
            return
        
        # Show crop dialog
        cropped = self._show_crop_dialog(screenshot)
        if cropped is None:
            return
        
        # Prompt for template name
        name, ok = QInputDialog.getText(self, "Template Name", "Enter template name (without extension):")
        if not ok or not name.strip():
            return
        
        # Save template
        safe_name = f"{name.strip()}.png"
        save_path = os.path.join(self._get_supports_dir(), safe_name)
        try:
            cropped.save(save_path)
            QMessageBox.information(self, "Saved", f"Template saved to {save_path}")
            self._refresh_template_dropdown()
            self.template_combo.setCurrentText(safe_name)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save template: {e}")
    
    def _show_crop_dialog(self, pil_image):
        """Show a crop dialog and return cropped image or None"""
        from PIL import Image
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
        from PySide6.QtGui import QPixmap, QPainter, QPen
        from PySide6.QtCore import QRect, QPoint
        
        class CropDialog(QDialog):
            def __init__(self, parent, pil_img):
                super().__init__(parent)
                self.setWindowTitle("Crop Template")
                self.setModal(True)
                
                self.pil_image = pil_img
                self.cropped_result = None
                
                # Scale image to fit screen
                screen = self.screen().availableGeometry()
                max_w = int(screen.width() * 0.75)
                max_h = int(screen.height() * 0.75) - 100
                
                img_w, img_h = pil_img.size
                self.scale = min(max_w / img_w, max_h / img_h, 1.0)
                
                display_w = int(img_w * self.scale)
                display_h = int(img_h * self.scale)
                
                # Convert PIL to QPixmap
                img_data = pil_img.convert("RGB").tobytes("raw", "RGB")
                from PySide6.QtGui import QImage
                qimg = QImage(img_data, img_w, img_h, img_w * 3, QImage.Format_RGB888)
                self.pixmap = QPixmap.fromImage(qimg).scaled(display_w, display_h)
                
                # Selection state
                self.start_pos = None
                self.end_pos = None
                self.selecting = False
                
                # Layout
                layout = QVBoxLayout(self)
                
                # Image label
                self.image_label = QLabel()
                self.image_label.setPixmap(self.pixmap)
                self.image_label.setMouseTracking(True)
                layout.addWidget(self.image_label)
                
                # Buttons
                btn_layout = QHBoxLayout()
                confirm_btn = QPushButton("Confirm")
                confirm_btn.clicked.connect(self._confirm)
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.reject)
                btn_layout.addWidget(confirm_btn)
                btn_layout.addWidget(cancel_btn)
                btn_layout.addStretch()
                layout.addLayout(btn_layout)
                
                self.resize(display_w + 40, display_h + 80)
            
            def mousePressEvent(self, event):
                pos = self.image_label.mapFrom(self, event.pos())
                if self.image_label.rect().contains(pos):
                    self.start_pos = pos
                    self.selecting = True
            
            def mouseMoveEvent(self, event):
                if self.selecting:
                    self.end_pos = self.image_label.mapFrom(self, event.pos())
                    self._draw_selection()
            
            def mouseReleaseEvent(self, event):
                if self.selecting:
                    self.end_pos = self.image_label.mapFrom(self, event.pos())
                    self.selecting = False
                    self._draw_selection()
            
            def _draw_selection(self):
                if self.start_pos and self.end_pos:
                    pm = self.pixmap.copy()
                    painter = QPainter(pm)
                    pen = QPen()
                    pen.setColor(Qt.red)
                    pen.setWidth(2)
                    painter.setPen(pen)
                    rect = QRect(self.start_pos, self.end_pos).normalized()
                    painter.drawRect(rect)
                    painter.end()
                    self.image_label.setPixmap(pm)
            
            def _confirm(self):
                if not self.start_pos or not self.end_pos:
                    QMessageBox.warning(self, "No Selection", "Please drag to select an area.")
                    return
                
                rect = QRect(self.start_pos, self.end_pos).normalized()
                if rect.width() < 10 or rect.height() < 10:
                    QMessageBox.warning(self, "Too Small", "Selection is too small.")
                    return
                
                # Convert to original coordinates
                x1 = int(rect.left() / self.scale)
                y1 = int(rect.top() / self.scale)
                x2 = int(rect.right() / self.scale)
                y2 = int(rect.bottom() / self.scale)
                
                self.cropped_result = self.pil_image.crop((x1, y1, x2, y2))
                self.accept()
        
        dialog = CropDialog(self, pil_image)
        if dialog.exec() == QDialog.Accepted:
            return dialog.cropped_result
        return None
    
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

