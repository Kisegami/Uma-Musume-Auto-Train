"""
Scenario Event Choice Editor Window for PySide6 GUI.

Uses the same interaction model as the Uma event editor:
- one row per event
- clickable option buttons
- result preview on the right
- saves selected options as custom choices
"""

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..styles import COLORS, MAIN_STYLESHEET


class ScenarioEventWindow(QDialog):
    """Scenario event choice editor with the same layout as UmaEventWindow."""

    def __init__(self, parent, scenario_name, scenario_key, event_file_path):
        super().__init__(parent)
        self.main_window = parent.main_window
        self.scenario_name = scenario_name
        self.scenario_key = scenario_key
        self.event_file_path = event_file_path
        self.custom_file_path = os.path.join(
            "template",
            "Events",
            "Scenario",
            f"ScenarioEvents_{scenario_key}.json",
        )

        self.events = []
        self.custom_choices = {}
        self.choice_buttons = {}
        self.result_labels = {}

        self.setWindowTitle(f"Scenario Event Choices - {scenario_name}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._load_event_data()
        self._load_existing_choices()
        self._create_ui()

    def _load_event_data(self):
        try:
            with open(self.event_file_path, "r", encoding="utf-8") as f:
                raw_entries = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load scenario events:\n{e}")
            raw_entries = []

        events_grouped = {}
        for entry in raw_entries:
            event_name = entry.get("EventName", "Unknown")
            if event_name not in events_grouped:
                events_grouped[event_name] = []

            option_map = entry.get("EventOptions", {})
            for option_name, result_text in option_map.items():
                if option_name.strip():
                    events_grouped[event_name].append({
                        "option": option_name,
                        "result": result_text,
                    })

        self.events = [
            (event_name, options)
            for event_name, options in events_grouped.items()
            if options
        ]

    def _load_existing_choices(self):
        if not os.path.exists(self.custom_file_path):
            self.custom_choices = {}
            return

        try:
            with open(self.custom_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.custom_choices = data.get("CustomChoices", {})
        except Exception:
            self.custom_choices = {}

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(f"Custom Choices for {self.scenario_name}")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_primary']};")
        header.addWidget(title)
        header.addStretch()

        self.count_badge = QLabel("")
        self.count_badge.setStyleSheet(f"""
            background-color: {COLORS['accent_primary']};
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
            font-weight: bold;
        """)
        header.addWidget(self.count_badge)
        layout.addLayout(header)

        info = QLabel("Click on a choice to select it. The result will be shown on the right.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_widget = QWidget()
        self.events_layout = QVBoxLayout(scroll_widget)
        self.events_layout.setSpacing(10)

        for event_name, options in self.events:
            row = self._create_event_row(event_name, options)
            self.events_layout.addWidget(row)

        self.events_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        footer = QHBoxLayout()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        footer.addWidget(clear_btn)

        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        save_btn = QPushButton("Save Choices")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_choices)
        footer.addWidget(save_btn)

        layout.addLayout(footer)
        self._update_count()

    def _create_event_row(self, event_name, options):
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 12, 16, 12)
        row_layout.setSpacing(16)

        name_label = QLabel(event_name)
        name_label.setWordWrap(True)
        name_label.setMinimumWidth(200)
        name_label.setMaximumWidth(250)
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        row_layout.addWidget(name_label, stretch=0)

        choices_widget = QWidget()
        choices_layout = QVBoxLayout(choices_widget)
        choices_layout.setContentsMargins(0, 0, 0, 0)
        choices_layout.setSpacing(6)

        self.choice_buttons[event_name] = {}
        option_results = {opt["option"]: opt["result"] for opt in options}

        for opt in options:
            option_name = opt["option"]
            btn = QPushButton(option_name)
            btn.setMinimumWidth(150)
            btn.setMaximumWidth(180)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, en=event_name, on=option_name, ores=option_results:
                self._select_choice(en, on, ores)
            )
            choices_layout.addWidget(btn)
            self.choice_buttons[event_name][option_name] = btn

        row_layout.addWidget(choices_widget, stretch=0)

        arrow = QLabel("→")
        arrow.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        row_layout.addWidget(arrow)

        result_frame = QFrame()
        result_frame.setStyleSheet(f"""
            background-color: {COLORS['bg_input']};
            border-radius: 8px;
            padding: 8px;
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(12, 8, 12, 8)

        result_label = QLabel("")
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        result_label.setMinimumHeight(50)
        result_layout.addWidget(result_label)

        row_layout.addWidget(result_frame, stretch=1)
        self.result_labels[event_name] = result_label

        if event_name in self.custom_choices:
            selected = self.custom_choices[event_name]
            if selected in self.choice_buttons[event_name]:
                self.choice_buttons[event_name][selected].setStyleSheet(
                    f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;"
                )
                if selected in option_results:
                    result_label.setText(option_results[selected].replace("\r\n", "\n").replace("\n", "\n"))

        return row

    def _select_choice(self, event_name, option_name, option_results):
        for btn in self.choice_buttons[event_name].values():
            btn.setStyleSheet("")

        self.choice_buttons[event_name][option_name].setStyleSheet(
            f"background-color: {COLORS['accent_green']}; color: white; font-weight: bold;"
        )

        result_text = option_results.get(option_name, "")
        self.result_labels[event_name].setText(result_text.replace("\r\n", "\n").replace("\n", "\n"))
        self.custom_choices[event_name] = option_name
        self._update_count()

    def _update_count(self):
        self.count_badge.setText(f"{len(self.custom_choices)} selected")

    def _clear_all(self):
        for event_name, buttons in self.choice_buttons.items():
            for btn in buttons.values():
                btn.setStyleSheet("")

        for label in self.result_labels.values():
            label.setText("")

        self.custom_choices = {}
        self._update_count()

    def _save_choices(self):
        try:
            os.makedirs(os.path.dirname(self.custom_file_path), exist_ok=True)

            data = {
                "ScenarioName": self.scenario_name,
                "ScenarioKey": self.scenario_key,
                "CustomChoices": self.custom_choices,
            }

            with open(self.custom_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            QMessageBox.information(
                self,
                "Success",
                f"Saved {len(self.custom_choices)} choices to {os.path.basename(self.custom_file_path)}",
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
