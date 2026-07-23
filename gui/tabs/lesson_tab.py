"""Grand Live lesson template management."""

import glob
import json
import os
import re

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..styles import MAIN_STYLESHEET
from .training_tab import DraggableListWidget


TECHNIQUE_DEFAULT = {
    "category_priority": ["stat", "recovery", "skill_hint"],
    "stat_priority": ["spd", "sta", "pwr", "guts", "wit", "skill_points"],
    "save_recovery": True,
    "skill_types": [
        "Aptitude Appropriate",
        "Dirt", "Sprint", "Mile", "Medium", "Long",
        "Front Runner", "Pace Chaser", "Late Surger", "End Closer",
    ],
}
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


def _ordered_list(keys):
    widget = DraggableListWidget()
    widget.setFlow(QListWidget.LeftToRight)
    widget.setFixedHeight(62)
    for key in keys:
        item = QListWidgetItem(DISPLAY.get(key, key))
        item.setData(Qt.UserRole, key)
        widget.addItem(item)
    return widget


def _list_values(widget):
    return [widget.item(i).data(Qt.UserRole) for i in range(widget.count())]


class TechniqueLessonDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path
        data = _read(path, TECHNIQUE_DEFAULT)
        self.setWindowTitle("Edit Technique Lesson Priority")
        self.setMinimumWidth(800)
        self.setStyleSheet(MAIN_STYLESHEET)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Category Priority (drag left = highest priority)"))
        self.category_list = _ordered_list(data.get("category_priority", TECHNIQUE_DEFAULT["category_priority"]))
        layout.addWidget(self.category_list)

        stats = QGroupBox("Stats Lesson")
        stats_layout = QVBoxLayout(stats)
        stats_layout.addWidget(QLabel("Allowed results and priority:"))
        checks = QHBoxLayout()
        self.stat_checks = {}
        allowed = data.get("stat_priority", TECHNIQUE_DEFAULT["stat_priority"])
        for key in TECHNIQUE_DEFAULT["stat_priority"]:
            checkbox = QCheckBox(DISPLAY[key])
            checkbox.setChecked(key in allowed)
            checkbox.stateChanged.connect(self._sync_stats)
            self.stat_checks[key] = checkbox
            checks.addWidget(checkbox)
        stats_layout.addLayout(checks)
        self.stat_list = _ordered_list(allowed)
        stats_layout.addWidget(self.stat_list)
        layout.addWidget(stats)

        recovery = QGroupBox("Recovery Lesson")
        recovery_layout = QVBoxLayout(recovery)
        self.save_recovery = QCheckBox(
            "Save recovery when its Energy gain would overflow maximum Energy"
        )
        self.save_recovery.setChecked(bool(data.get("save_recovery", True)))
        recovery_layout.addWidget(self.save_recovery)
        layout.addWidget(recovery)

        skills = QGroupBox("Skill Lesson Whitelist")
        skills_layout = QVBoxLayout(skills)
        self.skill_checks = {}
        allowed_skills = data.get("skill_types", TECHNIQUE_DEFAULT["skill_types"])
        for skill_type in TECHNIQUE_DEFAULT["skill_types"]:
            checkbox = QCheckBox(skill_type)
            checkbox.setChecked(skill_type in allowed_skills)
            self.skill_checks[skill_type] = checkbox
            skills_layout.addWidget(checkbox)
        layout.addWidget(skills)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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

    def _save(self):
        _write(self.path, {
            "category_priority": _list_values(self.category_list),
            "stat_priority": _list_values(self.stat_list),
            "save_recovery": self.save_recovery.isChecked(),
            "skill_types": [key for key, box in self.skill_checks.items() if box.isChecked()],
        })
        self.accept()


class SongPriorityDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path
        self.catalog = self._catalog()
        groups = _read(path, {"priority_groups": [[], [], []]}).get("priority_groups", [])
        self.groups = [list(groups[index]) if index < len(groups) else [] for index in range(3)]
        self.setWindowTitle("Edit Song Lessons Priority")
        self.setMinimumSize(1180, 800)
        self.setStyleSheet(MAIN_STYLESHEET)
        self._build()
        self._refresh()

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
        return sorted(result, key=lambda song: (int(song.get("lesson_level", 0)), song["title"]))

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Songs List — purchasable songs sorted by Lesson Level"))
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["No.", "Jacket", "Song", "Level", "Bonus", "After Live Bonus", "Action"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        for column, width in enumerate((45, 70, 235, 55, 210, 230, 150)):
            self.table.setColumnWidth(column, width)
        layout.addWidget(self.table, 3)

        self.tabs = QTabWidget()
        self.lists = []
        for title in ("First Priority", "Second Priority", "Third Priority"):
            widget = QListWidget()
            widget.setViewMode(QListWidget.IconMode)
            widget.setIconSize(QSize(72, 72))
            widget.setDragDropMode(QAbstractItemView.InternalMove)
            widget.setDefaultDropAction(Qt.MoveAction)
            widget.setSpacing(12)
            widget.model().rowsMoved.connect(self._sync)
            widget.itemDoubleClicked.connect(self._remove_song)
            self.lists.append(widget)
            self.tabs.addTab(widget, title)
        self.tabs.currentChanged.connect(lambda _: self._table())
        layout.addWidget(self.tabs, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        return f"{value.get('effect', '')} +{value.get('value', '')}{unit}"

    def _refresh(self):
        for group, widget in zip(self.groups, self.lists):
            widget.clear()
            for song_id in group:
                song = self._by_id(song_id)
                if not song:
                    continue
                item = QListWidgetItem(QIcon(song.get("jackets", {}).get("medium", "")), "")
                item.setData(Qt.UserRole, int(song_id))
                item.setToolTip(
                    f"{song['title']}\nBonus: {self._bonus(song.get('purchase_bonus'))}\n"
                    f"After Live: {self._bonus(song.get('successful_live_bonus'))}"
                )
                widget.addItem(item)
        self._table()

    def _table(self):
        membership = {
            int(song_id): index for index, group in enumerate(self.groups) for song_id in group
        }
        self.table.setRowCount(len(self.catalog))
        for row, song in enumerate(self.catalog):
            song_id = int(song["live_id"])
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            jacket = QLabel()
            jacket.setPixmap(QIcon(song["jackets"]["medium"]).pixmap(56, 56))
            jacket.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 1, jacket)
            self.table.setItem(row, 2, QTableWidgetItem(song["title"]))
            self.table.setItem(row, 3, QTableWidgetItem(str(song.get("lesson_level", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(self._bonus(song.get("purchase_bonus"))))
            self.table.setItem(row, 5, QTableWidgetItem(self._bonus(song.get("successful_live_bonus"))))
            button = QPushButton("Add")
            if song_id in membership:
                suffix = ("1st", "2nd", "3rd")[membership[song_id]]
                button.setText(f"Added to {suffix} Priority")
                button.setEnabled(False)
            else:
                button.clicked.connect(lambda _, value=song_id: self._add(value))
            self.table.setCellWidget(row, 6, button)
            self.table.setRowHeight(row, 64)

    def _add(self, song_id):
        self._sync()
        self.groups[self.tabs.currentIndex()].append(song_id)
        self._refresh()

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
        _write(self.path, {"priority_groups": self.groups})
        self.accept()


class LessonsTab(QScrollArea):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        self.page_layout = QVBoxLayout(container)
        self.page_layout.setContentsMargins(16, 16, 16, 16)
        self._group("Technique Lessons", "technique")
        self._group("Song Lessons", "songs")
        self.page_layout.addStretch()
        self.setWidget(container)
        self.load_config()

    def _group(self, title, kind):
        group = QGroupBox(title)
        row = QHBoxLayout(group)
        row.addWidget(QLabel("Template:"))
        combo = QComboBox()
        combo.setMinimumWidth(260)
        combo.currentTextChanged.connect(lambda _, value=kind: self._save_selection(value))
        setattr(self, f"{kind}_combo", combo)
        row.addWidget(combo)
        for text, callback in (
            ("Add", self._add), ("Remove", self._remove), ("Edit", self._edit)
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda _, fn=callback, value=kind: fn(value))
            row.addWidget(button)
        row.addStretch()
        self.page_layout.addWidget(group)

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
            _write(path, TECHNIQUE_DEFAULT if kind == "technique" else {"priority_groups": [[], [], []]})
            files = [path]
        combo.addItems([os.path.basename(path) for path in files])
        index = combo.findText(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def load_config(self):
        lessons = self.main_window.get_config().get("lessons", {})
        self._reload("technique", os.path.basename(lessons.get("technique_template", "default.json")))
        self._reload("songs", os.path.basename(lessons.get("song_template", "default.json")))

    def _save_selection(self, kind):
        if getattr(self.main_window, "_ui_loading", False):
            return
        combo = getattr(self, f"{kind}_combo")
        key = "technique_template" if kind == "technique" else "song_template"
        self.main_window.get_config().setdefault("lessons", {})[key] = (
            f"template/lessons/{kind}/{combo.currentText()}"
        )
        self.main_window.save_config()

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
        _write(path, TECHNIQUE_DEFAULT if kind == "technique" else {"priority_groups": [[], [], []]})
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
        combo = getattr(self, f"{kind}_combo")
        path = os.path.join(self._directory(kind), combo.currentText())
        dialog = TechniqueLessonDialog(self, path) if kind == "technique" else SongPriorityDialog(self, path)
        dialog.exec()
