"""
Trackblazer item usage condition template editor.
"""

import json
import os

import qtawesome as qta
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIntValidator, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..styles import COLORS, MAIN_STYLESHEET
from .item_priority_window import get_item_by_id


SCORE_TARGETS = [
    ("Any", "any"),
    ("Speed", "spd"),
    ("Stamina", "sta"),
    ("Power", "pwr"),
    ("Guts", "guts"),
    ("Wit", "wit"),
]

COL_NO_WIDTH = 32
COL_IMAGE_WIDTH = 40
COL_NAME_WIDTH = 200
COL_EFFECT_WIDTH = 260
COL_TYPE_WIDTH = 120


def _item_icon_path(icon_name):
    return os.path.join("gui", "assets", "items", icon_name)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _normalize_condition(condition):
    cond_type = condition.get("type", "picked_training_score")
    target = condition.get("target", "any")
    value = max(0, _safe_int(condition.get("value"), 0))

    if cond_type == "energy":
        return {
            "type": "energy",
            "operator": "less_than",
            "value": value,
        }

    return {
        "type": "picked_training_score",
        "target": target,
        "operator": "more_than",
        "value": value,
    }


def _condition_to_text(condition):
    condition = _normalize_condition(condition)
    if condition["type"] == "energy":
        return f"Energy < {condition['value']}"

    target_label = next((label for label, value in SCORE_TARGETS if value == condition.get("target")), "Any")
    return f"Picked Training Score: {target_label} > {condition['value']}"


def _conditions_summary(conditions, condition_type):
    if not conditions:
        return "Use Immediately"

    joiner = f" {condition_type} " if len(conditions) > 1 else ""
    return joiner.join(_condition_to_text(condition) for condition in conditions)


class ConditionClauseRow(QWidget):
    """Single condition clause editor."""

    def __init__(self, condition=None, remove_callback=None):
        super().__init__()
        self.remove_callback = remove_callback
        self._build_ui()
        self.set_condition(condition or {"type": "picked_training_score", "target": "any", "value": 0})

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Picked Training Score", "picked_training_score")
        self.type_combo.addItem("Energy", "energy")
        self.type_combo.currentIndexChanged.connect(self._sync_state)
        layout.addWidget(self.type_combo)

        self.target_combo = QComboBox()
        for label, value in SCORE_TARGETS:
            self.target_combo.addItem(label, value)
        layout.addWidget(self.target_combo)

        self.operator_label = QLabel()
        self.operator_label.setMinimumWidth(70)
        layout.addWidget(self.operator_label)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("0")
        self.value_input.setValidator(QIntValidator(0, 99999, self))
        self.value_input.setFixedWidth(100)
        layout.addWidget(self.value_input)

        remove_button = QPushButton()
        remove_button.setObjectName("danger")
        remove_button.setIcon(qta.icon("fa5s.minus", color="white"))
        remove_button.setIconSize(QSize(14, 14))
        remove_button.setFixedSize(34, 34)
        remove_button.clicked.connect(self._remove_self)
        layout.addWidget(remove_button)

    def _sync_state(self):
        cond_type = self.type_combo.currentData()
        is_score = cond_type == "picked_training_score"
        self.target_combo.setVisible(is_score)
        self.operator_label.setText("More than" if is_score else "Less than")

    def _remove_self(self):
        if self.remove_callback is not None:
            self.remove_callback(self)

    def set_condition(self, condition):
        condition = _normalize_condition(condition)
        index = self.type_combo.findData(condition["type"])
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        target_index = self.target_combo.findData(condition.get("target", "any"))
        if target_index >= 0:
            self.target_combo.setCurrentIndex(target_index)

        self.value_input.setText(str(condition.get("value", 0)))
        self._sync_state()

    def get_condition(self):
        value_text = self.value_input.text().strip()
        value = _safe_int(value_text, 0)
        cond_type = self.type_combo.currentData()

        if cond_type == "energy":
            return {
                "type": "energy",
                "operator": "less_than",
                "value": value,
            }

        return {
            "type": "picked_training_score",
            "target": self.target_combo.currentData(),
            "operator": "more_than",
            "value": value,
        }


class ItemConditionEditorDialog(QDialog):
    """Dialog for editing one item's usage conditions."""

    def __init__(self, parent, item_name, conditions):
        super().__init__(parent)
        self.item_name = item_name
        self.condition_rows = []
        self.setWindowTitle(f"Edit Usage Condition - {item_name}")
        self.setMinimumWidth(760)
        self.setStyleSheet(MAIN_STYLESHEET)
        self._build_ui()

        for condition in conditions:
            self._add_condition_row(condition)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(self.item_name)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Add one or more conditions. Leave it empty to keep the default behavior: Use Immediately."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.conditions_holder = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_holder)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        self.conditions_layout.setSpacing(8)
        layout.addWidget(self.conditions_holder)

        add_button = QPushButton("Add Condition")
        add_button.setObjectName("primary")
        add_button.clicked.connect(lambda: self._add_condition_row())
        layout.addWidget(add_button, alignment=Qt.AlignLeft)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.accept)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def _add_condition_row(self, condition=None):
        row = ConditionClauseRow(condition, self._remove_condition_row)
        self.condition_rows.append(row)
        self.conditions_layout.addWidget(row)

    def _remove_condition_row(self, row):
        if row not in self.condition_rows:
            return
        self.condition_rows.remove(row)
        self.conditions_layout.removeWidget(row)
        row.deleteLater()

    def get_conditions(self):
        return [row.get_condition() for row in self.condition_rows]


class UsageConditionRow(QWidget):
    """Single item row in the usage condition table."""

    def __init__(self, index, item_data, usage_data, edit_callback):
        super().__init__()
        self.item_data = item_data
        self.conditions = [_normalize_condition(condition) for condition in usage_data.get("conditions", [])]
        self.edit_callback = edit_callback
        self._build_ui(index)
        self.set_condition_type(usage_data.get("condition_type", "AND"))
        self.refresh_summary()

    def _build_ui(self, index):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(12)

        self.no_label = QLabel(str(index))
        self.no_label.setFixedWidth(COL_NO_WIDTH)
        layout.addWidget(self.no_label)

        icon_label = QLabel()
        icon_label.setFixedSize(COL_IMAGE_WIDTH, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(_item_icon_path(self.item_data.get("icon", "")))
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon_label)

        name_label = QLabel(self.item_data.get("name", ""))
        name_label.setFixedWidth(COL_NAME_WIDTH)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        effect_label = QLabel(self.item_data.get("effect", ""))
        effect_label.setWordWrap(True)
        effect_label.setFixedWidth(COL_EFFECT_WIDTH)
        effect_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(effect_label)

        condition_widget = QWidget()
        condition_layout = QVBoxLayout(condition_widget)
        condition_layout.setContentsMargins(0, 0, 0, 0)
        condition_layout.setSpacing(6)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        condition_layout.addWidget(self.summary_label)

        edit_button = QPushButton("Edit Conditions")
        edit_button.setObjectName("accent")
        edit_button.clicked.connect(lambda: self.edit_callback(self))
        condition_layout.addWidget(edit_button, alignment=Qt.AlignLeft)

        condition_widget.setMinimumWidth(280)
        layout.addWidget(condition_widget, stretch=1)

        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItem("AND")
        self.condition_type_combo.addItem("OR")
        self.condition_type_combo.setFixedWidth(COL_TYPE_WIDTH)
        layout.addWidget(self.condition_type_combo)

    def set_condition_type(self, value):
        index = self.condition_type_combo.findText(str(value).upper())
        if index < 0:
            index = 0
        self.condition_type_combo.setCurrentIndex(index)

    def get_condition_type(self):
        return self.condition_type_combo.currentText()

    def set_conditions(self, conditions):
        self.conditions = [_normalize_condition(condition) for condition in conditions]
        self.refresh_summary()

    def refresh_summary(self):
        self.summary_label.setText(_conditions_summary(self.conditions, self.get_condition_type()))
        self.condition_type_combo.setEnabled(len(self.conditions) > 1)

    def get_payload(self):
        return {
            "id": int(self.item_data["id"]),
            "name": self.item_data.get("name", ""),
            "condition_type": self.get_condition_type(),
            "conditions": [_normalize_condition(condition) for condition in self.conditions],
        }


class ItemUsageConditionWindow(QDialog):
    """Editor for Trackblazer item usage conditions."""

    def __init__(self, parent, template_path):
        super().__init__(parent)
        self.template_path = template_path
        self.priority_items = []
        self.usage_data = {}
        self.rows = []

        self.setWindowTitle("Edit Item Usage Conditions")
        self.setMinimumSize(1280, 760)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._load_template()
        self._build_ui()

    def _load_template(self):
        data = {"items_priority": [], "items_usage_conditions": []}
        if os.path.exists(self.template_path):
            try:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"items_priority": [], "items_usage_conditions": []}

        self.priority_items = data.get("items_priority", [])
        self.usage_data = {}
        for entry in data.get("items_usage_conditions", []):
            try:
                self.usage_data[int(entry.get("id"))] = {
                    "condition_type": str(entry.get("condition_type", "AND")).upper(),
                    "conditions": entry.get("conditions", []),
                }
            except Exception:
                continue

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Item Usage Condition Manager")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Conditions are evaluated only for items that already exist in Items Purchase Priority."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        no_label = QLabel("No.")
        no_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        no_label.setFixedWidth(COL_NO_WIDTH)
        header_layout.addWidget(no_label)

        image_label = QLabel("Image")
        image_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        image_label.setFixedWidth(COL_IMAGE_WIDTH)
        header_layout.addWidget(image_label)

        name_label = QLabel("Name")
        name_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        name_label.setFixedWidth(COL_NAME_WIDTH)
        header_layout.addWidget(name_label)

        effect_label = QLabel("Effect")
        effect_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        effect_label.setFixedWidth(COL_EFFECT_WIDTH)
        header_layout.addWidget(effect_label)

        condition_label = QLabel("Condition")
        condition_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        condition_label.setMinimumWidth(280)
        header_layout.addWidget(condition_label, stretch=1)

        type_label = QLabel("Condition Type")
        type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        type_label.setFixedWidth(COL_TYPE_WIDTH)
        header_layout.addWidget(type_label)

        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.rows_layout = QVBoxLayout(container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)

        for index, priority_item in enumerate(self.priority_items, start=1):
            item_id = _safe_int(priority_item.get("id"))
            catalog_item = get_item_by_id(item_id) or {}
            row_item_data = {
                "id": item_id,
                "name": catalog_item.get("name", priority_item.get("name", "")),
                "icon": catalog_item.get("icon", ""),
                "effect": catalog_item.get("effect", ""),
            }
            usage_data = self.usage_data.get(item_id, {"condition_type": "AND", "conditions": []})
            row = UsageConditionRow(index, row_item_data, usage_data, self._edit_row_conditions)
            row.condition_type_combo.currentTextChanged.connect(
                lambda _text, current_row=row: current_row.refresh_summary()
            )
            self.rows.append(row)
            self.rows_layout.addWidget(row)

        self.rows_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_template)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def _edit_row_conditions(self, row):
        dialog = ItemConditionEditorDialog(self, row.item_data.get("name", "Item"), row.conditions)
        if dialog.exec():
            row.set_conditions(dialog.get_conditions())

    def _save_template(self):
        existing_data = {}
        if os.path.exists(self.template_path):
            try:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        payload = {
            "items_priority": existing_data.get("items_priority", self.priority_items),
            "items_usage_conditions": [row.get_payload() for row in self.rows],
        }

        try:
            with open(self.template_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return

        QMessageBox.information(
            self,
            "Saved",
            f"Saved usage conditions for {len(self.rows)} items to {os.path.basename(self.template_path)}",
        )
        self.accept()
