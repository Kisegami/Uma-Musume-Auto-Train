"""Grand Live lesson template management."""

import glob
import json
import os
import re

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QGridLayout, QGroupBox, QHeaderView, QHBoxLayout, QInputDialog, QLabel,
    QListView, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QToolTip, QWidget,
)

from ..styles import COLORS, MAIN_STYLESHEET
from .training_tab import DraggableListWidget


TECHNIQUE_DEFAULT = {
    "selection_method": "save_best",
    "category_priority": ["stat", "recovery", "skill_hint"],
    "stat_priority": ["spd", "sta", "pwr", "guts", "wit", "skill_points"],
    "save_recovery": True,
    "skip_recovery_while_pal_dating": False,
    "skill_types": [
        "Aptitude Appropriate",
        "Dirt", "Sprint", "Mile", "Medium", "Long",
        "Front Runner", "Pace Chaser", "Late Surger", "End Closer",
    ],
}
SONG_DEFAULT = {
    "selection_method": "save_best",
    "save_for_better_after_three": False,
    "priority_groups": [[], [], []],
}
SELECTION_METHODS = (
    ("Pick any good available lesson", "available"),
    ("Save points for best lesson", "save_best"),
)
SAVE_BEST_NOTE = (
    "If minimum songs before concert is not met, it will choose any lesson on Concert day."
)
CONCERT_REQUIREMENT_LABELS = (
    "1st Concert",
    "2nd Concert",
    "3rd Concert",
    "4th Concert",
    "Grand Concert",
)
DEFAULT_CONCERT_REQUIREMENTS = {
    str(index): {"minimum": 3, "maximum": 4}
    for index in range(1, 6)
}
DEFAULT_TRY_LEARN_18_BEFORE_GRAND_CONCERT = False
DISPLAY = {
    "stat": "Stats Lesson", "recovery": "Recovery Lesson", "skill_hint": "Skill Lesson",
    "spd": "Speed", "sta": "Stamina", "pwr": "Power", "guts": "Guts",
    "wit": "Wit", "skill_points": "Skill Pts",
}


def _read(path, default):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else dict(default)
    except (OSError, ValueError):
        return dict(default)


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)


PRIORITY_LIST_STYLE = f"""
    QListWidget {{
        background-color: {COLORS['bg_darkest']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 8px;
        padding: 6px;
    }}
    QListWidget::item {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 7px;
        padding: 8px 14px;
        margin: 2px 4px;
        font-weight: 600;
    }}
    QListWidget::item:selected {{
        background-color: {COLORS['accent_primary']};
        border-color: {COLORS['accent_primary']};
    }}
    QListWidget::item:hover:!selected {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['accent_primary']};
    }}
"""

AVAILABLE_SONG_BUTTON_STYLE = """
    QPushButton {
        padding: 0 8px;
        min-height: 0;
    }
"""

SELECTED_SONG_BUTTON_STYLE = """
    QPushButton, QPushButton:disabled {
        background-color: #f2c94c;
        color: #1a1a1a;
        border: 1px solid #ffe082;
        padding: 0 8px;
        min-height: 0;
        font-weight: 700;
    }
"""


def _ordered_list(keys):
    widget = DraggableListWidget()
    widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    widget.setMinimumWidth(0)
    widget.setFlow(QListWidget.LeftToRight)
    widget.setWrapping(False)
    widget.setFixedHeight(64)
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    widget.setStyleSheet(PRIORITY_LIST_STYLE)
    for key in keys:
        item = QListWidgetItem(DISPLAY.get(key, key))
        item.setData(Qt.UserRole, key)
        widget.addItem(item)
    return widget


def _list_values(widget):
    return [widget.item(i).data(Qt.UserRole) for i in range(widget.count())]


def _selection_method_combo():
    combo = QComboBox()
    for label, value in SELECTION_METHODS:
        combo.addItem(label, value)
    combo.setMinimumWidth(280)
    return combo


def _yellow_selection_note():
    note = QLabel(SAVE_BEST_NOTE)
    note.setWordWrap(True)
    note.setStyleSheet("color: #f2c94c; font-weight: 600;")
    return note


class NonHighlightTableWidget(QTableWidget):
    """Table whose data cells never become selected or current when clicked."""

    def mousePressEvent(self, event):
        if self.indexAt(event.position().toPoint()).isValid():
            self.clearSelection()
            self.setCurrentCell(-1, -1)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.indexAt(event.position().toPoint()).isValid():
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class TechniqueLessonEditor(QWidget):
    """Inline, auto-saving editor for the selected technique template."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = None
        self._loading = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        selection = QGroupBox("Selection Method")
        selection_layout = QVBoxLayout(selection)
        self.selection_method = _selection_method_combo()
        selection_layout.addWidget(self.selection_method, 0, Qt.AlignLeft)
        self.selection_note = _yellow_selection_note()
        selection_layout.addWidget(self.selection_note)
        self.selection_method.currentIndexChanged.connect(
            self._selection_method_changed
        )
        layout.addWidget(selection)

        category = QGroupBox("Category Priority")
        category_layout = QVBoxLayout(category)
        hint = QLabel("Drag cards left or right. The leftmost category is selected first.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        category_layout.addWidget(hint)
        self.category_list = _ordered_list(TECHNIQUE_DEFAULT["category_priority"])
        self.category_list.orderChanged.connect(lambda _: self._save())
        category_layout.addWidget(self.category_list)
        layout.addWidget(category)

        stats = QGroupBox("Stats Lesson")
        stats_layout = QVBoxLayout(stats)
        stats_layout.setSpacing(10)
        stat_hint = QLabel("Enable the results you want, then drag their cards into priority order.")
        stat_hint.setObjectName("muted")
        stat_hint.setWordWrap(True)
        stat_hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        stats_layout.addWidget(stat_hint)
        checks = QGridLayout()
        checks.setHorizontalSpacing(18)
        checks.setVerticalSpacing(8)
        self.stat_checks = {}
        for index, key in enumerate(TECHNIQUE_DEFAULT["stat_priority"]):
            checkbox = QCheckBox(DISPLAY[key])
            checkbox.stateChanged.connect(self._sync_stats)
            self.stat_checks[key] = checkbox
            checks.addWidget(checkbox, index // 3, index % 3)
        stats_layout.addLayout(checks)
        self.stat_list = _ordered_list(TECHNIQUE_DEFAULT["stat_priority"])
        self.stat_list.orderChanged.connect(lambda _: self._save())
        stats_layout.addWidget(self.stat_list)
        layout.addWidget(stats)

        recovery = QGroupBox("Recovery Lesson")
        recovery_layout = QVBoxLayout(recovery)
        self.save_recovery = QCheckBox("Skip recovery lessons that would overflow Energy")
        self.save_recovery.stateChanged.connect(self._save)
        recovery_layout.addWidget(self.save_recovery)
        self.skip_recovery_while_pal_dating = QCheckBox(
            "Skip recovery lessons while Pal Dating is available"
        )
        self.skip_recovery_while_pal_dating.stateChanged.connect(self._save)
        recovery_layout.addWidget(self.skip_recovery_while_pal_dating)
        recovery_note = QLabel(
            "The first option keeps recovery lessons for later when their Energy gain "
            "would exceed maximum Energy. The second skips them until Pal Dating is "
            "completed or no longer available."
        )
        recovery_note.setObjectName("muted")
        recovery_note.setWordWrap(True)
        recovery_layout.addWidget(recovery_note)
        layout.addWidget(recovery)

        skills = QGroupBox("Skill Lesson Whitelist")
        skills_layout = QGridLayout(skills)
        skills_layout.setHorizontalSpacing(20)
        skills_layout.setVerticalSpacing(8)
        self.skill_checks = {}
        for index, skill_type in enumerate(TECHNIQUE_DEFAULT["skill_types"]):
            checkbox = QCheckBox(skill_type)
            checkbox.stateChanged.connect(self._save)
            self.skill_checks[skill_type] = checkbox
            skills_layout.addWidget(checkbox, index // 3, index % 3)
        layout.addWidget(skills)

        saved_hint = QLabel("Changes to technique priorities are saved automatically.")
        saved_hint.setObjectName("muted")
        saved_hint.setAlignment(Qt.AlignRight)
        layout.addWidget(saved_hint)
        self._loading = False

    @staticmethod
    def _fill_list(widget, keys):
        widget.clear()
        for key in keys:
            item = QListWidgetItem(DISPLAY.get(key, key))
            item.setData(Qt.UserRole, key)
            widget.addItem(item)

    def load(self, path):
        self.path = path
        data = _read(path, TECHNIQUE_DEFAULT)
        self._loading = True
        method = data.get("selection_method", TECHNIQUE_DEFAULT["selection_method"])
        method_index = self.selection_method.findData(method)
        self.selection_method.setCurrentIndex(method_index if method_index >= 0 else 1)
        self.selection_note.setVisible(
            self.selection_method.currentData() == "save_best"
        )
        self._fill_list(
            self.category_list,
            data.get("category_priority", TECHNIQUE_DEFAULT["category_priority"]),
        )
        allowed = data.get("stat_priority", TECHNIQUE_DEFAULT["stat_priority"])
        for key, checkbox in self.stat_checks.items():
            checkbox.setChecked(key in allowed)
        self._fill_list(self.stat_list, allowed)
        self.save_recovery.setChecked(bool(data.get("save_recovery", True)))
        self.skip_recovery_while_pal_dating.setChecked(
            bool(data.get("skip_recovery_while_pal_dating", False))
        )
        allowed_skills = data.get("skill_types", TECHNIQUE_DEFAULT["skill_types"])
        for skill_type, checkbox in self.skill_checks.items():
            checkbox.setChecked(skill_type in allowed_skills)
        self._loading = False

    def _selection_method_changed(self, _index):
        self.selection_note.setVisible(
            self.selection_method.currentData() == "save_best"
        )
        self._save()

    def _sync_stats(self):
        previous = _list_values(self.stat_list)
        checked = [key for key, box in self.stat_checks.items() if box.isChecked()]
        order = [key for key in previous if key in checked]
        order += [key for key in checked if key not in order]
        self.stat_list.clear()
        for key in order:
            item = QListWidgetItem(DISPLAY[key])
            item.setData(Qt.UserRole, key)
            self.stat_list.addItem(item)
        self._save()

    def _save(self):
        if self._loading or not self.path:
            return
        _write(self.path, {
            "selection_method": self.selection_method.currentData(),
            "category_priority": _list_values(self.category_list),
            "stat_priority": _list_values(self.stat_list),
            "save_recovery": self.save_recovery.isChecked(),
            "skip_recovery_while_pal_dating":
                self.skip_recovery_while_pal_dating.isChecked(),
            "skill_types": [key for key, box in self.skill_checks.items() if box.isChecked()],
        })


class SongPriorityDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path
        self.catalog = self._catalog()
        groups = _read(path, SONG_DEFAULT).get("priority_groups", [])
        self.groups = [list(groups[index]) if index < len(groups) else [] for index in range(3)]
        self.setWindowTitle("Edit Song Lessons Priority")
        self.setMinimumSize(900, 650)
        self.setStyleSheet(MAIN_STYLESHEET)
        self._build()
        self._refresh()
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = min(1120, int(available.width() * 0.9)) if available else 1080
        height = min(820, int(available.height() * 0.9)) if available else 760
        self.resize(max(900, width), max(650, height))

    def _catalog(self):
        source = _read(
            os.path.join("assets", "grandlive", "grand_live_song_lessons.json"), {}
        )
        result = []
        for title, raw in source.items():
            if raw.get("purchasable", True) is False or not raw.get("cost"):
                continue
            song = dict(raw)
            song["title"] = raw.get("display_title", title)
            result.append(song)
        return sorted(
            result,
            key=lambda song: (int(song.get("availability_part", 5)), song["title"]),
        )

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("Available Songs")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.active_hint = QLabel()
        self.active_hint.setObjectName("muted")
        title_row.addWidget(self.active_hint)
        layout.addLayout(title_row)

        self.table = NonHighlightTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["No.", "Jacket", "Song", "Available Concert", "Bonus", "After Live Bonus", "Action"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setShowGrid(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_darkest']};
                alternate-background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                border: none;
                border-bottom: 1px solid {COLORS['border_light']};
                padding: 8px 5px;
                font-weight: 600;
            }}
        """)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 68)
        self.table.setColumnWidth(6, 104)
        self._table_populated = False
        self._action_buttons = {}
        layout.addWidget(self.table, 5)

        selected_group = QGroupBox("Selected Song Order")
        selected_layout = QVBoxLayout(selected_group)
        selected_layout.setContentsMargins(10, 14, 10, 10)
        selected_layout.setSpacing(6)
        selected_hint = QLabel(
            "Drag songs to reorder them. Double-click a song to remove it from its priority."
        )
        selected_hint.setObjectName("muted")
        selected_layout.addWidget(selected_hint)
        self.tabs = QTabWidget()
        self.lists = []
        for title in ("First Priority", "Second Priority", "Third Priority"):
            widget = QListWidget()
            widget.setViewMode(QListView.ListMode)
            widget.setFlow(QListWidget.LeftToRight)
            widget.setWrapping(False)
            widget.setMovement(QListView.Snap)
            widget.setResizeMode(QListView.Fixed)
            widget.setIconSize(QSize(56, 56))
            widget.setGridSize(QSize(82, 70))
            widget.setUniformItemSizes(True)
            widget.setWordWrap(False)
            widget.setMouseTracking(True)
            widget.setDragDropMode(QAbstractItemView.InternalMove)
            widget.setDragDropOverwriteMode(False)
            widget.setDefaultDropAction(Qt.MoveAction)
            widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            widget.setSpacing(4)
            widget.setStyleSheet(f"""
                QListWidget {{
                    background-color: {COLORS['bg_darkest']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 6px;
                }}
                QListWidget::item {{
                    background-color: {COLORS['bg_input']};
                    border: 1px solid {COLORS['border_light']};
                    border-radius: 8px;
                    padding: 6px 4px;
                    margin: 3px;
                }}
                QListWidget::item:selected {{
                    background-color: {COLORS['accent_primary']};
                    border-color: {COLORS['accent_primary']};
                }}
                QListWidget::item:hover:!selected {{
                    background-color: {COLORS['bg_hover']};
                    border-color: {COLORS['accent_primary']};
                }}
            """)
            widget.model().rowsMoved.connect(self._sync)
            widget.itemDoubleClicked.connect(self._remove_song)
            widget.itemEntered.connect(
                lambda item, view=widget: self._show_song_tooltip(view, item)
            )
            self.lists.append(widget)
            self.tabs.addTab(widget, title)
        self.tabs.setMinimumHeight(135)
        self.tabs.currentChanged.connect(self._priority_changed)
        self._priority_changed(self.tabs.currentIndex())
        selected_layout.addWidget(self.tabs)
        layout.addWidget(selected_group, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _priority_changed(self, _index):
        labels = ("First Priority", "Second Priority", "Third Priority")
        self.active_hint.setText(f"Add destination: {labels[self.tabs.currentIndex()]}")
        self._table()

    @staticmethod
    def _show_song_tooltip(view, item):
        rect = view.visualItemRect(item)
        position = view.viewport().mapToGlobal(rect.bottomLeft())
        QToolTip.showText(position, item.toolTip(), view, rect, 5000)

    def _by_id(self, song_id):
        return next(
            (song for song in self.catalog if int(song.get("live_id", 0)) == int(song_id)),
            None,
        )

    @staticmethod
    def _bonus(value):
        if not value:
            return ""
        unit = "%" if value.get("unit") == "percent" else ""
        effect = value.get("effect", "")
        if effect == "Extra Stat Gain" and value.get("stat"):
            effect = f"Extra {value['stat']} Gained"
        return f"{effect} +{value.get('value', '')}{unit}"

    def _refresh(self):
        for group, widget in zip(self.groups, self.lists):
            widget.clear()
            for song_id in group:
                song = self._by_id(song_id)
                if not song:
                    continue
                item = QListWidgetItem(
                    QIcon(song.get("jackets", {}).get("medium", "")),
                    "",
                )
                item.setData(Qt.UserRole, int(song_id))
                item.setSizeHint(QSize(76, 64))
                item.setToolTip(
                    f"{song['title']}\n"
                    f"Available: {self._availability(song)}\n"
                    f"Bonus: {self._bonus(song.get('purchase_bonus'))}\n"
                    f"After Live: {self._bonus(song.get('successful_live_bonus'))}"
                )
                widget.addItem(item)
        self._table()

    def _table(self):
        if not self._table_populated:
            self._populate_table()
        self._update_table_actions()

    @staticmethod
    def _availability(song):
        part = int(song.get("availability_part", 5))
        return {
            1: "1st",
            2: "2nd",
            3: "3rd",
            4: "4th",
            5: "Grand",
        }.get(part, "Grand")

    def _populate_table(self):
        """Create static song cells once so refreshes cannot leave orphan widgets."""
        self.table.setRowCount(len(self.catalog))
        for row, song in enumerate(self.catalog):
            song_id = int(song["live_id"])
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            jacket = QLabel()
            jacket.setPixmap(QIcon(song["jackets"]["medium"]).pixmap(56, 56))
            jacket.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 1, jacket)
            self.table.setItem(row, 2, QTableWidgetItem(song["title"]))
            self.table.setItem(row, 3, QTableWidgetItem(self._availability(song)))
            self.table.setItem(row, 4, QTableWidgetItem(self._bonus(song.get("purchase_bonus"))))
            self.table.setItem(row, 5, QTableWidgetItem(self._bonus(song.get("successful_live_bonus"))))

            button = QPushButton("Add")
            button.setFixedSize(88, 32)
            button.setStyleSheet(AVAILABLE_SONG_BUTTON_STYLE)
            button.clicked.connect(lambda _, value=song_id: self._add(value))
            self._action_buttons[song_id] = button
            action = QWidget()
            action_layout = QHBoxLayout(action)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.addStretch()
            action_layout.addWidget(button)
            action_layout.addStretch()
            self.table.setCellWidget(row, 6, action)
            self.table.setRowHeight(row, 70)
        self._table_populated = True

    def _update_table_actions(self):
        membership = {
            int(song_id): index for index, group in enumerate(self.groups) for song_id in group
        }
        for song in self.catalog:
            song_id = int(song["live_id"])
            button = self._action_buttons[song_id]
            if song_id in membership:
                priority = membership[song_id] + 1
                button.setText(f"Priority {priority}")
                button.setToolTip(f"Already selected in priority group {priority}")
                button.setStyleSheet(SELECTED_SONG_BUTTON_STYLE)
                button.setEnabled(False)
            else:
                button.setText("Add")
                button.setToolTip(
                    f"Add to {('First', 'Second', 'Third')[self.tabs.currentIndex()]} Priority"
                )
                button.setStyleSheet(AVAILABLE_SONG_BUTTON_STYLE)
                button.setEnabled(True)

    def _add(self, song_id):
        scroll_bar = self.table.verticalScrollBar()
        scroll_position = scroll_bar.value()
        self._sync()
        self.groups[self.tabs.currentIndex()].insert(0, song_id)
        self._refresh()
        scroll_bar.setValue(scroll_position)
        QTimer.singleShot(
            0,
            lambda bar=scroll_bar, position=scroll_position: bar.setValue(position),
        )

    def _remove_song(self, item):
        song_id = int(item.data(Qt.UserRole))
        self.groups = [
            [value for value in group if int(value) != song_id]
            for group in self.groups
        ]
        self._refresh()

    def _sync(self):
        for index, widget in enumerate(self.lists):
            self.groups[index] = [
                widget.item(row).data(Qt.UserRole) for row in range(widget.count())
            ]

    def _save(self):
        self._sync()
        template = _read(self.path, SONG_DEFAULT)
        template["priority_groups"] = self.groups
        _write(self.path, template)
        self.accept()


class LessonsTab(QScrollArea):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.page_layout = QVBoxLayout(container)
        self.page_layout.setContentsMargins(16, 16, 16, 16)
        self.page_layout.setSpacing(16)
        self._group("Technique Lessons", "technique")
        self._group("Song Lessons", "songs")
        self._build_song_requirements_group()
        self.page_layout.addStretch()
        self.setWidget(container)
        self.load_config()

    def _group(self, title, kind):
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        group.setMinimumWidth(0)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Template:"))
        combo = QComboBox()
        combo.setMinimumWidth(260)
        combo.currentTextChanged.connect(lambda _, value=kind: self._save_selection(value))
        setattr(self, f"{kind}_combo", combo)
        row.addWidget(combo)
        actions = [("Add", self._add), ("Remove", self._remove)]
        if kind == "songs":
            actions.append(("Edit Priorities", self._edit))
        for text, callback in actions:
            button = QPushButton(text)
            if text == "Edit Priorities":
                button.setObjectName("accent")
            button.clicked.connect(lambda _, fn=callback, value=kind: fn(value))
            row.addWidget(button)
        row.addStretch()
        group_layout.addLayout(row)
        if kind == "technique":
            self.technique_editor = TechniqueLessonEditor(group)
            group_layout.addWidget(self.technique_editor)
        else:
            selection = QGroupBox("Selection Method")
            selection_layout = QVBoxLayout(selection)
            self.song_selection_method = _selection_method_combo()
            selection_layout.addWidget(
                self.song_selection_method, 0, Qt.AlignLeft
            )
            self.song_selection_note = _yellow_selection_note()
            selection_layout.addWidget(self.song_selection_note)
            self.song_save_after_three = QCheckBox(
                "Stop learning new songs and save for an unaffordable better "
                "song after 3 songs are learned"
            )
            self.song_save_after_three.setToolTip(
                "Uses songs learned for the current Concert cycle. Below 3, "
                "the selected method behaves normally."
            )
            selection_layout.addWidget(self.song_save_after_three)
            self._song_method_loading = False
            self.song_selection_method.currentIndexChanged.connect(
                self._save_song_selection_method
            )
            self.song_save_after_three.stateChanged.connect(
                self._save_song_selection_method
            )
            group_layout.addWidget(selection)

            description = QLabel(
                "Choose which songs the bot should reserve or study first. "
                "Use Edit Priorities to arrange the three priority groups."
            )
            description.setObjectName("muted")
            description.setWordWrap(True)
            group_layout.addWidget(description)
            self._build_song_preview(group_layout)
        self.page_layout.addWidget(group)

    def _build_song_requirements_group(self):
        group = QGroupBox("Songs requirements")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        description = QLabel(
            "Minimum/Maximum songs to learn before each Concert"
        )
        description.setObjectName("muted")
        layout.addWidget(description)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel("Concert"), 0, 0)
        grid.addWidget(QLabel("Minimum"), 0, 1)
        grid.addWidget(QLabel("Maximum"), 0, 2)
        self.requirement_minimum_spins = {}
        self.requirement_maximum_spins = {}
        self._requirements_loading = True

        for index, title in enumerate(CONCERT_REQUIREMENT_LABELS, start=1):
            grid.addWidget(QLabel(title), index, 0)
            minimum = QSpinBox()
            minimum.setRange(3, 21)
            maximum = QSpinBox()
            maximum.setRange(3, 21)
            minimum.valueChanged.connect(
                lambda value, concert=index: self._requirement_minimum_changed(
                    concert, value
                )
            )
            maximum.valueChanged.connect(
                lambda _value, concert=index: self._save_song_requirements()
            )
            grid.addWidget(minimum, index, 1)
            grid.addWidget(maximum, index, 2)
            self.requirement_minimum_spins[index] = minimum
            self.requirement_maximum_spins[index] = maximum

        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)

        self.catch_up_song_minimum = QCheckBox(
            "Try to reach the total minimum when an earlier Concert minimum was missed"
        )
        self.catch_up_song_minimum.stateChanged.connect(
            self._save_song_requirements
        )
        layout.addWidget(self.catch_up_song_minimum)
        catch_up_note = QLabel(
            "Enabled: compares total songs learned with the cumulative minimum through "
            "the upcoming Concert. Disabled: only checks the current Concert."
        )
        catch_up_note.setObjectName("muted")
        catch_up_note.setWordWrap(True)
        layout.addWidget(catch_up_note)

        self.try_learn_18_before_grand_concert = QCheckBox(
            "Try to learn 18 songs total before the Grand Concert"
        )
        self.try_learn_18_before_grand_concert.setToolTip(
            "On Senior Year Early Dec, checks the total songs learned and "
            "spends available Performance Points on affordable lessons, "
            "including filler lessons that refresh the board, until 18 songs "
            "are learned or no affordable lesson remains."
        )
        self.try_learn_18_before_grand_concert.stateChanged.connect(
            self._save_song_requirements
        )
        layout.addWidget(self.try_learn_18_before_grand_concert)
        grand_concert_note = QLabel(
            "Runs on Senior Year Early Dec and spends affordable technique "
            "lessons as needed to reveal more songs while catching up."
        )
        grand_concert_note.setObjectName("muted")
        grand_concert_note.setWordWrap(True)
        layout.addWidget(grand_concert_note)
        self._requirements_loading = False
        self.page_layout.addWidget(group)

    def _requirement_minimum_changed(self, concert, value):
        maximum = self.requirement_maximum_spins[concert]
        maximum.setMinimum(value)
        if maximum.value() < value:
            maximum.setValue(value)
        self._save_song_requirements()

    def _load_song_requirements(self):
        raw = (
            self.main_window.get_config()
            .get("lessons", {})
            .get("song_requirements", {})
        )
        concerts = raw.get("concerts", {})
        self._requirements_loading = True
        for index in range(1, 6):
            configured = concerts.get(
                str(index), DEFAULT_CONCERT_REQUIREMENTS[str(index)]
            )
            minimum_value = max(3, min(21, int(configured.get("minimum", 3))))
            maximum_value = max(
                minimum_value,
                min(21, int(configured.get("maximum", 4))),
            )
            minimum = self.requirement_minimum_spins[index]
            maximum = self.requirement_maximum_spins[index]
            minimum.setValue(minimum_value)
            maximum.setMinimum(minimum_value)
            maximum.setValue(maximum_value)
        self.catch_up_song_minimum.setChecked(
            bool(raw.get("catch_up_missed_minimum", False))
        )
        self.try_learn_18_before_grand_concert.setChecked(
            bool(
                raw.get(
                    "try_learn_18_before_grand_concert",
                    DEFAULT_TRY_LEARN_18_BEFORE_GRAND_CONCERT,
                )
            )
        )
        self._requirements_loading = False

    def _save_song_requirements(self, *_args):
        if self._requirements_loading or getattr(
            self.main_window, "_ui_loading", False
        ):
            return
        requirements = {
            "catch_up_missed_minimum": self.catch_up_song_minimum.isChecked(),
            "try_learn_18_before_grand_concert":
                self.try_learn_18_before_grand_concert.isChecked(),
            "concerts": {
                str(index): {
                    "minimum": self.requirement_minimum_spins[index].value(),
                    "maximum": self.requirement_maximum_spins[index].value(),
                }
                for index in range(1, 6)
            },
        }
        self.main_window.get_config().setdefault("lessons", {})[
            "song_requirements"
        ] = requirements
        self.main_window.save_config()

    def _build_song_preview(self, parent_layout):
        preview = QGroupBox("Priority Preview")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setSpacing(8)
        self.song_preview_layouts = []
        self.song_preview_scrolls = []

        for title in ("First Priority", "Second Priority", "Third Priority"):
            row = QHBoxLayout()
            label = QLabel(title)
            label.setFixedWidth(100)
            label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-weight: 600;"
            )
            row.addWidget(label)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFixedHeight(78)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {COLORS['bg_darkest']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            container = QWidget()
            items = QHBoxLayout(container)
            items.setContentsMargins(7, 6, 7, 6)
            items.setSpacing(7)
            scroll.setWidget(container)
            row.addWidget(scroll, 1)
            preview_layout.addLayout(row)
            self.song_preview_layouts.append(items)
            self.song_preview_scrolls.append(scroll)

        parent_layout.addWidget(preview)

    @staticmethod
    def _clear_preview_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_song_preview(self):
        if not hasattr(self, "song_preview_layouts"):
            return

        filename = self.songs_combo.currentText()
        path = os.path.join(self._directory("songs"), filename) if filename else ""
        groups = _read(path, SONG_DEFAULT).get("priority_groups", [])
        source = _read(
            os.path.join("assets", "grandlive", "grand_live_song_lessons.json"),
            {},
        )
        songs_by_id = {
            int(song.get("live_id", 0)): (song.get("display_title", title), song)
            for title, song in source.items()
            if song.get("live_id") is not None
        }

        for index, layout in enumerate(self.song_preview_layouts):
            self._clear_preview_layout(layout)
            song_ids = groups[index] if index < len(groups) else []
            shown = 0
            for song_id in song_ids:
                entry = songs_by_id.get(int(song_id))
                if not entry:
                    continue
                title, song = entry
                jacket = QLabel()
                jacket.setFixedSize(60, 60)
                jacket.setAlignment(Qt.AlignCenter)
                jacket.setPixmap(
                    QIcon(song.get("jackets", {}).get("medium", "")).pixmap(52, 52)
                )
                jacket.setStyleSheet(
                    f"background-color: {COLORS['bg_input']}; "
                    f"border: 1px solid {COLORS['border_light']}; border-radius: 7px;"
                )
                jacket.setToolTip(
                    f"{title}\n"
                    f"Available Concert: {SongPriorityDialog._availability(song)}\n"
                    f"Bonus: {SongPriorityDialog._bonus(song.get('purchase_bonus'))}\n"
                    f"After Live: {SongPriorityDialog._bonus(song.get('successful_live_bonus'))}"
                )
                layout.addWidget(jacket)
                shown += 1

            if not shown:
                empty = QLabel("No songs")
                empty.setObjectName("muted")
                layout.addWidget(empty)
            layout.addStretch()

    @staticmethod
    def _directory(kind):
        return os.path.join("template", "lessons", kind)

    def _reload(self, kind, selected="default.json"):
        combo = getattr(self, f"{kind}_combo")
        combo.blockSignals(True)
        combo.clear()
        directory = self._directory(kind)
        os.makedirs(directory, exist_ok=True)
        files = sorted(glob.glob(os.path.join(directory, "*.json")))
        if not files:
            path = os.path.join(directory, "default.json")
            _write(path, TECHNIQUE_DEFAULT if kind == "technique" else SONG_DEFAULT)
            files = [path]
        combo.addItems([os.path.basename(path) for path in files])
        index = combo.findText(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def load_config(self):
        lessons = self.main_window.get_config().get("lessons", {})
        self._reload("technique", os.path.basename(lessons.get("technique_template", "default.json")))
        self._reload("songs", os.path.basename(lessons.get("song_template", "default.json")))
        self._load_technique_editor()
        self._load_song_selection_method()
        self._update_song_preview()
        self._load_song_requirements()

    def _load_technique_editor(self):
        filename = self.technique_combo.currentText()
        if filename:
            self.technique_editor.load(
                os.path.join(self._directory("technique"), filename)
            )

    def _load_song_selection_method(self):
        filename = self.songs_combo.currentText()
        if not filename:
            return
        template = _read(
            os.path.join(self._directory("songs"), filename),
            SONG_DEFAULT,
        )
        method = template.get("selection_method", SONG_DEFAULT["selection_method"])
        self._song_method_loading = True
        index = self.song_selection_method.findData(method)
        self.song_selection_method.setCurrentIndex(index if index >= 0 else 1)
        self.song_selection_note.setVisible(
            self.song_selection_method.currentData() == "save_best"
        )
        self.song_save_after_three.setChecked(
            bool(
                template.get(
                    "save_for_better_after_three",
                    SONG_DEFAULT["save_for_better_after_three"],
                )
            )
        )
        self._song_method_loading = False

    def _save_song_selection_method(self, _index):
        if self._song_method_loading:
            return
        filename = self.songs_combo.currentText()
        if not filename:
            return
        path = os.path.join(self._directory("songs"), filename)
        template = _read(path, SONG_DEFAULT)
        template["selection_method"] = self.song_selection_method.currentData()
        template["save_for_better_after_three"] = (
            self.song_save_after_three.isChecked()
        )
        _write(path, template)
        self.song_selection_note.setVisible(
            self.song_selection_method.currentData() == "save_best"
        )

    def _save_selection(self, kind):
        if getattr(self.main_window, "_ui_loading", False):
            return
        combo = getattr(self, f"{kind}_combo")
        key = "technique_template" if kind == "technique" else "song_template"
        self.main_window.get_config().setdefault("lessons", {})[key] = (
            f"template/lessons/{kind}/{combo.currentText()}"
        )
        self.main_window.save_config()
        if kind == "technique":
            self._load_technique_editor()
        else:
            self._load_song_selection_method()
            self._update_song_preview()

    def _add(self, kind):
        name, ok = QInputDialog.getText(self, "New Lesson Template", "Template name:")
        if not ok or not name.strip():
            return
        name = re.sub(r'[<>:"/\\\\|?*]+', "_", name.strip())
        filename = name if name.endswith(".json") else f"{name}.json"
        path = os.path.join(self._directory(kind), filename)
        if os.path.exists(path):
            QMessageBox.information(self, "Template Exists", filename)
            return
        _write(path, TECHNIQUE_DEFAULT if kind == "technique" else SONG_DEFAULT)
        self._reload(kind, filename)
        self._save_selection(kind)

    def _remove(self, kind):
        combo = getattr(self, f"{kind}_combo")
        if combo.count() <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one template must remain.")
            return
        if QMessageBox.question(self, "Confirm", f"Remove '{combo.currentText()}'?") != QMessageBox.Yes:
            return
        os.remove(os.path.join(self._directory(kind), combo.currentText()))
        self._reload(kind)
        self._save_selection(kind)

    def _edit(self, kind):
        if kind != "songs":
            return
        combo = getattr(self, f"{kind}_combo")
        path = os.path.join(self._directory(kind), combo.currentText())
        SongPriorityDialog(self, path).exec()
        self._update_song_preview()
