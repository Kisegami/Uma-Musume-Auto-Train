"""
Trackblazer item priority template editor.
"""

import json
import os

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, QMimeData
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSpinBox, QVBoxLayout, QWidget
)

from ..styles import COLORS, MAIN_STYLESHEET


ITEM_MIME_TYPE = "application/x-umat-item-id"

_items_cache = None
_items_by_id = {}

COL_NO_WIDTH = 32
COL_ICON_WIDTH = 40
COL_NAME_WIDTH = 220
COL_GROUP_WIDTH = 110
COL_EFFECT_TYPE_WIDTH = 150
COL_LIMIT_WIDTH = 100
COL_ACTION_WIDTH = 42


def _items_map_path():
    return os.path.join("gui", "assets", "items", "items_map.json")


def _items_source_path():
    return os.path.join("assets", "trackblazer", "items", "items_list.json")


def _item_icon_path(icon_name):
    return os.path.join("gui", "assets", "items", icon_name)


def load_items_catalog():
    global _items_cache, _items_by_id
    if _items_cache is not None:
        return _items_cache

    _items_cache = []
    _items_by_id = {}

    try:
        with open(_items_map_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", [])

        source_by_id = {}
        if os.path.exists(_items_source_path()):
            try:
                with open(_items_source_path(), "r", encoding="utf-8") as f:
                    source_items = json.load(f)
                source_by_id = {
                    int(item["id"]): item
                    for item in source_items
                    if isinstance(item, dict) and "id" in item
                }
            except Exception:
                source_by_id = {}

        merged_items = []
        for item in items:
            merged = dict(item)
            source_item = source_by_id.get(int(item.get("id", 0)), {})
            if source_item:
                merged["group"] = source_item.get("Group", "")
                merged["effect_type"] = source_item.get("Effect Type", "")
            else:
                merged["group"] = item.get("group", "")
                merged["effect_type"] = item.get("effect_type", "")
            merged_items.append(merged)

        _items_cache = sorted(merged_items, key=lambda item: int(item.get("id", 0)))
        _items_by_id = {int(item["id"]): item for item in _items_cache if "id" in item}
    except Exception:
        _items_cache = []
        _items_by_id = {}

    return _items_cache


def get_item_by_id(item_id):
    load_items_catalog()
    return _items_by_id.get(int(item_id))


class ItemCatalogList(QListWidget):
    """Draggable item catalog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSpacing(6)
        self.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 6px;
            }}
            QListWidget::item {{
                border: none;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background: {COLORS['bg_hover']};
            }}
        """)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return

        item_id = item.data(Qt.UserRole)
        mime = QMimeData()
        mime.setData(ITEM_MIME_TYPE, str(item_id).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class ItemCatalogCard(QFrame):
    """Catalog entry shown in the right sidebar."""

    def __init__(self, item_data, add_callback):
        super().__init__()
        self.item_data = item_data
        self.add_callback = add_callback
        self.setObjectName("card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(_item_icon_path(item_data.get("icon", "")))
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(f"{item_data.get('id', '')} - {item_data.get('name', '')}")
        title.setStyleSheet("font-weight: 700;")
        title.setWordWrap(True)
        text_layout.addWidget(title)

        effect = QLabel(item_data.get("effect", ""))
        effect.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        effect.setWordWrap(True)
        text_layout.addWidget(effect)

        layout.addLayout(text_layout, stretch=1)

        add_button = QPushButton()
        add_button.setIcon(qta.icon("fa5s.plus", color="white"))
        add_button.setIconSize(QSize(16, 16))
        add_button.setToolTip("Add item")
        add_button.setObjectName("primary")
        add_button.setFixedSize(36, 36)
        add_button.clicked.connect(lambda: self.add_callback(int(self.item_data["id"])))
        layout.addWidget(add_button)


class ItemPriorityRow(QWidget):
    """Single row in the selected item priority table."""

    def __init__(self, row_data, remove_callback):
        super().__init__()
        self.row_data = row_data
        self.remove_callback = remove_callback
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(12)
        self.setCursor(Qt.OpenHandCursor)

        self.no_label = QLabel("")
        self.no_label.setFixedWidth(COL_NO_WIDTH)
        layout.addWidget(self.no_label)

        icon_label = QLabel()
        icon_label.setFixedSize(COL_ICON_WIDTH, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(_item_icon_path(self.row_data.get("icon", "")))
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(icon_label)

        name_label = QLabel(self.row_data.get("name", ""))
        name_label.setFixedWidth(COL_NAME_WIDTH)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        group_label = QLabel(self.row_data.get("group", ""))
        group_label.setFixedWidth(COL_GROUP_WIDTH)
        group_label.setWordWrap(True)
        group_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(group_label)

        effect_type_label = QLabel(self.row_data.get("effect_type", ""))
        effect_type_label.setFixedWidth(COL_EFFECT_TYPE_WIDTH)
        effect_type_label.setWordWrap(True)
        effect_type_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(effect_type_label)

        layout.addStretch()

        self.limit_spin = QSpinBox()
        self.limit_spin.setMinimum(1)
        self.limit_spin.setMaximum(999)
        self.limit_spin.setValue(int(self.row_data.get("item_limit", 1)))
        self.limit_spin.valueChanged.connect(self._on_limit_changed)
        self.limit_spin.setFixedWidth(COL_LIMIT_WIDTH)
        layout.addWidget(self.limit_spin)

        remove_button = QPushButton()
        remove_button.setObjectName("danger")
        remove_button.setIcon(qta.icon("fa5s.trash", color="white"))
        remove_button.setIconSize(QSize(16, 16))
        remove_button.setToolTip("Remove item")
        remove_button.setFixedSize(COL_ACTION_WIDTH, 42)
        remove_button.clicked.connect(lambda: self.remove_callback(self.row_data["id"]))
        layout.addWidget(remove_button)

    def _on_limit_changed(self, value):
        self.row_data["item_limit"] = int(value)

    def set_index(self, index):
        self.no_label.setText(str(index))


class SelectedItemsList(QListWidget):
    """Selected items list with external drops and internal reordering."""

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['bg_card']};
                border: 1px dashed {COLORS['border_light']};
                border-radius: 12px;
                padding: 6px;
            }}
            QListWidget::item {{
                border: none;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(ITEM_MIME_TYPE) or event.source() is self:
            self.setStyleSheet(f"""
                QListWidget {{
                    background: {COLORS['bg_hover']};
                    border: 1px dashed {COLORS['accent_blue']};
                    border-radius: 12px;
                    padding: 6px;
                }}
                QListWidget::item {{
                    border: none;
                    padding: 0px;
                }}
                QListWidget::item:selected {{
                    background: transparent;
                }}
            """)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._reset_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(ITEM_MIME_TYPE) and event.source() is not self:
            item_id = int(bytes(event.mimeData().data(ITEM_MIME_TYPE)).decode("utf-8"))
            self.parent_window.add_item_by_id(item_id)
            self._reset_style()
            event.acceptProposedAction()
            return

        super().dropEvent(event)
        self._reset_style()
        self.parent_window.sync_selected_items_from_list()
        event.acceptProposedAction()

    def _reset_style(self):
        self.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['bg_card']};
                border: 1px dashed {COLORS['border_light']};
                border-radius: 12px;
                padding: 6px;
            }}
            QListWidget::item {{
                border: none;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)


class ItemPriorityWindow(QDialog):
    """Editor for Trackblazer item purchase priority templates."""

    def __init__(self, parent, template_path):
        super().__init__(parent)
        self.template_path = template_path
        self.catalog_items = load_items_catalog()
        self.selected_items = []

        self.setWindowTitle("Edit Item Purchase Priority")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._load_template()
        self._build_ui()
        self._refresh_catalog()
        self._refresh_selected_items()

    def _load_template(self):
        self.selected_items = []
        if not os.path.exists(self.template_path):
            return

        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        for entry in data.get("items_priority", []):
            item_id = entry.get("id")
            item_data = get_item_by_id(item_id)
            if not item_data:
                continue
            self.selected_items.append({
                "id": int(item_id),
                "name": item_data.get("name", entry.get("name", "")),
                "icon": item_data.get("icon", ""),
                "item_limit": max(1, int(entry.get("item_limit", 1))),
            })

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Item Purchase Priority Manager")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Search items on the right, then drag them into the priority list on the left."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        header = QFrame()
        header.setObjectName("card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(12)

        no_label = QLabel("No.")
        no_label.setFixedWidth(COL_NO_WIDTH)
        no_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(no_label)

        icon_label = QLabel("Item")
        icon_label.setFixedWidth(COL_ICON_WIDTH)
        icon_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(icon_label)

        name_label = QLabel("Name")
        name_label.setFixedWidth(COL_NAME_WIDTH)
        name_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(name_label)

        group_label = QLabel("Group")
        group_label.setFixedWidth(COL_GROUP_WIDTH)
        group_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(group_label)

        effect_type_label = QLabel("Effect Type")
        effect_type_label.setFixedWidth(COL_EFFECT_TYPE_WIDTH)
        effect_type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(effect_type_label)

        header_layout.addStretch()

        limit_label = QLabel("Item Limit")
        limit_label.setFixedWidth(COL_LIMIT_WIDTH)
        limit_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(limit_label)

        action_label = QLabel("Action")
        action_label.setFixedWidth(COL_ACTION_WIDTH)
        action_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 700;")
        header_layout.addWidget(action_label)

        left_panel.addWidget(header)

        self.empty_label = QLabel("Drag items here from the right sidebar.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 18px 0;")
        left_panel.addWidget(self.empty_label)

        self.selected_list = SelectedItemsList(self)
        left_panel.addWidget(self.selected_list, stretch=1)

        body.addLayout(left_panel, stretch=2)

        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        sidebar_title = QLabel("All Items")
        sidebar_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        right_layout.addWidget(sidebar_title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by id, name, group, effect type, or effect")
        self.search_input.textChanged.connect(self._refresh_catalog)
        right_layout.addWidget(self.search_input)

        self.catalog_list = ItemCatalogList()
        right_layout.addWidget(self.catalog_list, stretch=1)

        body.addWidget(right_panel, stretch=1)
        layout.addLayout(body, stretch=1)

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

    def _refresh_catalog(self):
        self.catalog_list.clear()
        query = self.search_input.text().strip().lower()
        selected_ids = {entry["id"] for entry in self.selected_items}

        for item in self.catalog_items:
            item_id = int(item.get("id", 0))
            if item_id in selected_ids:
                continue

            haystack = " ".join([
                str(item_id),
                item.get("name", ""),
                item.get("group", ""),
                item.get("effect_type", ""),
                item.get("effect", ""),
            ]).lower()
            if query and query not in haystack:
                continue

            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, item_id)
            list_item.setSizeHint(QSize(320, 74))
            self.catalog_list.addItem(list_item)
            self.catalog_list.setItemWidget(list_item, ItemCatalogCard(item, self.add_item_by_id))

    def _refresh_selected_items(self):
        self.selected_list.clear()
        for index, row_data in enumerate(self.selected_items, start=1):
            row = ItemPriorityRow(row_data, self._remove_item)
            row.set_index(index)
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, int(row_data["id"]))
            list_item.setSizeHint(QSize(760, 58))
            self.selected_list.addItem(list_item)
            self.selected_list.setItemWidget(list_item, row)

        self.empty_label.setVisible(len(self.selected_items) == 0)
        self._refresh_catalog()

    def add_item_by_id(self, item_id):
        if any(entry["id"] == item_id for entry in self.selected_items):
            QMessageBox.information(self, "Already Added", "That item is already in the priority list.")
            return

        item_data = get_item_by_id(item_id)
        if not item_data:
            return

        self.selected_items.append({
            "id": int(item_data["id"]),
            "name": item_data.get("name", ""),
            "group": item_data.get("group", ""),
            "effect_type": item_data.get("effect_type", ""),
            "icon": item_data.get("icon", ""),
            "item_limit": 1,
        })
        self._refresh_selected_items()

    def _remove_item(self, item_id):
        self.selected_items = [entry for entry in self.selected_items if entry["id"] != item_id]
        self._refresh_selected_items()

    def sync_selected_items_from_list(self):
        reordered = []
        for index in range(self.selected_list.count()):
            item = self.selected_list.item(index)
            row = self.selected_list.itemWidget(item)
            if row is None:
                continue
            reordered.append(row.row_data)
        self.selected_items = reordered
        self._refresh_selected_items()

    def _save_template(self):
        os.makedirs(os.path.dirname(self.template_path), exist_ok=True)
        payload = {
            "items_priority": [
                {
                    "id": entry["id"],
                    "name": entry["name"],
                    "item_limit": int(entry.get("item_limit", 1)),
                }
                for entry in self.selected_items
            ],
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
            f"Saved {len(self.selected_items)} items to {os.path.basename(self.template_path)}",
        )
        self.accept()
