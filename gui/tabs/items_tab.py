"""
Items Tab for PySide6 GUI.
Contains Trackblazer item purchase priority template management.
"""

import glob
import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QFrame, QScrollArea, QPushButton, QMessageBox, QInputDialog
)


class ItemsTab(QScrollArea):
    """Trackblazer items configuration tab."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        self._create_ui()
        self.load_config()

    def _create_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        priority_group = QGroupBox("Items purchase Priority")
        priority_layout = QVBoxLayout(priority_group)
        priority_layout.setSpacing(12)

        template_row = QHBoxLayout()
        template_row.setSpacing(10)
        template_row.addWidget(QLabel("Template:"))

        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(220)
        self.template_combo.currentTextChanged.connect(self._save_items_config)
        template_row.addWidget(self.template_combo)

        add_btn = QPushButton("Add New")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_template)
        template_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_template)
        template_row.addWidget(remove_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("accent")
        edit_btn.clicked.connect(self._edit_template)
        template_row.addWidget(edit_btn)

        template_row.addStretch()
        priority_layout.addLayout(template_row)

        layout.addWidget(priority_group)
        layout.addStretch()
        self.setWidget(container)

        self._load_templates()

    def _get_items_dir(self):
        items_dir = os.path.join("template", "items")
        os.makedirs(items_dir, exist_ok=True)
        return items_dir

    def _default_template_data(self):
        return {
            "items_priority": []
        }

    def _ensure_template_exists(self, filename):
        if not filename:
            return

        path = os.path.join(self._get_items_dir(), filename)
        if os.path.exists(path):
            return

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._default_template_data(), f, indent=2, ensure_ascii=False)

    def _load_templates(self):
        self.template_combo.blockSignals(True)
        current = self.template_combo.currentText()
        self.template_combo.clear()

        files = glob.glob(os.path.join(self._get_items_dir(), "*.json"))
        for path in sorted(files):
            self.template_combo.addItem(os.path.basename(path))

        if self.template_combo.count() == 0:
            self.template_combo.addItem("default.json")
            self._ensure_template_exists("default.json")

        if current:
            index = self.template_combo.findText(current)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)

        self.template_combo.blockSignals(False)

    def load_config(self):
        self._loading = True
        self._load_templates()

        config = self.main_window.get_config()
        items_config = config.get("items", {})
        item_file = items_config.get("item_purchase_file", "template/items/default.json")
        item_file = os.path.basename(item_file)
        self._ensure_template_exists(item_file)
        self._load_templates()

        index = self.template_combo.findText(item_file)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)

        self._loading = False

    def _save_items_config(self):
        if getattr(self, "_loading", False):
            return

        filename = self.template_combo.currentText()
        if not filename:
            return

        config = self.main_window.get_config()
        config.setdefault("items", {})
        config["items"]["item_purchase_file"] = f"template/items/{filename}"
        self.main_window.save_config()

    def _add_template(self):
        name, ok = QInputDialog.getText(self, "New Item Template", "Enter template name:")
        if not ok or not name.strip():
            return

        safe_name = name.strip()
        if not safe_name.endswith(".json"):
            safe_name += ".json"

        path = os.path.join(self._get_items_dir(), safe_name)
        if os.path.exists(path):
            QMessageBox.information(self, "Template Exists", f"'{safe_name}' already exists.")
            return

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._default_template_data(), f, indent=2, ensure_ascii=False)

        self._load_templates()
        index = self.template_combo.findText(safe_name)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)
        self._save_items_config()

    def _remove_template(self):
        filename = self.template_combo.currentText()
        if not filename:
            return

        reply = QMessageBox.question(self, "Confirm", f"Remove '{filename}'?")
        if reply != QMessageBox.Yes:
            return

        path = os.path.join(self._get_items_dir(), filename)
        if os.path.exists(path):
            os.remove(path)

        self._load_templates()
        self._save_items_config()

    def _edit_template(self):
        filename = self.template_combo.currentText()
        if not filename:
            return

        self._ensure_template_exists(filename)
        template_path = os.path.join(self._get_items_dir(), filename)

        from .item_priority_window import ItemPriorityWindow

        dialog = ItemPriorityWindow(self, template_path)
        dialog.exec()

