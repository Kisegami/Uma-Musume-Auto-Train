"""
Items Tab for PySide6 GUI.
Contains Trackblazer item purchase template management and item behavior settings.
"""

import glob
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)
from PySide6.QtGui import QCursor, QPixmap

from core.Trackblazer.items import DEFAULT_ITEM_SETTINGS, NEGATIVE_CONDITIONS
from .item_priority_window import load_items_catalog


def _item_icon_path(icon_name):
    return os.path.join("gui", "assets", "items", icon_name)


def _get_catalog_items_by_name(name):
    return [item for item in load_items_catalog() if item.get("name", "") == name]


def _get_catalog_items_by_group(group):
    return [item for item in load_items_catalog() if item.get("group", "") == group]


def _get_catalog_items_by_effect_type(effect_type):
    return [item for item in load_items_catalog() if item.get("effect_type", "") == effect_type]


class ItemPreviewPopup(QFrame):
    """Tooltip-style popup showing matching items."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip)
        self.setObjectName("card")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight: 700;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.items_widget = QWidget()
        self.items_layout = QGridLayout(self.items_widget)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setHorizontalSpacing(10)
        self.items_layout.setVerticalSpacing(8)
        layout.addWidget(self.items_widget)

    def show_preview(self, title, items, global_pos):
        self.title_label.setText(title)

        while self.items_layout.count() > 0:
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for index, item in enumerate(items[:12]):
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(8)

            icon_label = QLabel()
            icon_label.setFixedSize(32, 32)
            pixmap = QPixmap(_item_icon_path(item.get("icon", "")))
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            cell_layout.addWidget(icon_label)

            name_label = QLabel(item.get("name", ""))
            name_label.setWordWrap(True)
            cell_layout.addWidget(name_label, stretch=1)

            self.items_layout.addWidget(cell, index // 2, index % 2)

        self.adjustSize()
        self.move(global_pos.x() + 14, global_pos.y() + 18)
        self.show()


class HoverPreviewLabel(QLabel):
    def __init__(self, text, popup, title_getter, items_getter, parent=None):
        super().__init__(text, parent)
        self.popup = popup
        self.title_getter = title_getter
        self.items_getter = items_getter
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("text-decoration: underline;")

    def enterEvent(self, event):
        items = self.items_getter() or []
        if items:
            self.popup.show_preview(self.title_getter(), items, QCursor.pos())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.popup.hide()
        super().leaveEvent(event)


class HoverPreviewCheckBox(QCheckBox):
    def __init__(self, text, popup, title_getter, items_getter, parent=None):
        super().__init__(text, parent)
        self.popup = popup
        self.title_getter = title_getter
        self.items_getter = items_getter
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        items = self.items_getter() or []
        if items:
            self.popup.show_preview(self.title_getter(), items, QCursor.pos())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.popup.hide()
        super().leaveEvent(event)


class ItemsTab(QScrollArea):
    """Trackblazer item configuration tab."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.preview_popup = ItemPreviewPopup(self)

        self.condition_checkboxes = {}
        self.training_level_stat_checkboxes = {}
        self.training_buff_period_checkboxes = {}

        self._create_ui()
        self.load_config()

    def _create_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addWidget(self._build_purchase_group())
        layout.addWidget(self._build_mood_group())
        layout.addWidget(self._build_condition_group())
        layout.addWidget(self._build_training_group())
        layout.addWidget(self._build_race_group())
        layout.addStretch()

        self.setWidget(container)
        self._load_templates()

    def _build_purchase_group(self):
        group = QGroupBox("Purchase Priority")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

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

        edit_priority_btn = QPushButton("Edit")
        edit_priority_btn.setObjectName("accent")
        edit_priority_btn.clicked.connect(self._edit_priority_template)
        template_row.addWidget(edit_priority_btn)

        template_row.addStretch()
        group_layout.addLayout(template_row)

        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel("Budget Strategy:"))
        self.budget_strategy_combo = QComboBox()
        self.budget_strategy_combo.addItem("Save for higher priority items", "save_priority")
        self.budget_strategy_combo.addItem("Buy as much items as possible", "buy_max")
        self.budget_strategy_combo.currentIndexChanged.connect(self._save_items_config)
        strategy_row.addWidget(self.budget_strategy_combo)
        strategy_row.addStretch()
        group_layout.addLayout(strategy_row)

        swipe_offset_group = QGroupBox("Shop Purchase Scan")
        swipe_offset_layout = QVBoxLayout(swipe_offset_group)
        swipe_offset_layout.setSpacing(12)

        desc_text = (
            "Purchase max swipes limits shop scanning so the purchase flow cannot loop forever when an item is missing.\n\n"
            "Shop swipe offset adjusts swipe duration for your device, similar to the skill list swipe tuning.\n"
            "Increase offset (+) for a shorter swipe distance, decrease offset (-) for a longer swipe distance."
        )
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        swipe_offset_layout.addWidget(desc_label)

        max_swipes_row = QHBoxLayout()
        max_swipes_row.addWidget(QLabel("Purchase max swipes:"))
        self.purchase_max_swipes_spin = QSpinBox()
        self.purchase_max_swipes_spin.setRange(1, 50)
        self.purchase_max_swipes_spin.valueChanged.connect(self._save_items_config)
        max_swipes_row.addWidget(self.purchase_max_swipes_spin)
        max_swipes_row.addStretch()
        swipe_offset_layout.addLayout(max_swipes_row)

        swipe_offset_row = QHBoxLayout()
        swipe_offset_row.addWidget(QLabel("Shop swipe offset (ms):"))
        self.shop_swipe_offset_spin = QSpinBox()
        self.shop_swipe_offset_spin.setRange(-2000, 2000)
        self.shop_swipe_offset_spin.valueChanged.connect(self._save_items_config)
        self.shop_swipe_offset_spin.setMinimumWidth(100)
        swipe_offset_row.addWidget(self.shop_swipe_offset_spin)
        swipe_offset_row.addStretch()
        swipe_offset_layout.addLayout(swipe_offset_row)

        group_layout.addWidget(swipe_offset_group)

        return group

    def _build_mood_group(self):
        group = QGroupBox("Mood Items")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        self.auto_buy_mood = HoverPreviewCheckBox(
            "Auto-buy mood items when current mood is below minimum mood",
            self.preview_popup,
            lambda: "Mood items",
            lambda: _get_catalog_items_by_effect_type("Mood"),
        )
        self.auto_buy_mood.stateChanged.connect(self._save_items_config)
        layout.addWidget(self.auto_buy_mood)

        info = QLabel("The bot calculates the exact +1 / +2 mood combination it needs, then uses it immediately.")
        info.setWordWrap(True)
        layout.addWidget(info)
        return group

    def _build_condition_group(self):
        group = QGroupBox("Condition Items")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        self.auto_buy_negative_cure = HoverPreviewCheckBox(
            "Automatically buy cure items for bad conditions",
            self.preview_popup,
            lambda: "Negative Condition Cure items",
            lambda: _get_catalog_items_by_effect_type("Negative Condition Cure"),
        )
        self.auto_buy_negative_cure.stateChanged.connect(self._on_auto_buy_negative_cure_changed)
        layout.addWidget(self.auto_buy_negative_cure)

        self.condition_options_widget = QWidget()
        options_layout = QVBoxLayout(self.condition_options_widget)
        options_layout.setContentsMargins(18, 0, 0, 0)
        options_layout.setSpacing(8)

        self.all_conditions_checkbox = HoverPreviewCheckBox(
            "Buy cures for all supported bad conditions",
            self.preview_popup,
            lambda: "Negative Condition Cure items",
            lambda: _get_catalog_items_by_effect_type("Negative Condition Cure"),
        )
        self.all_conditions_checkbox.stateChanged.connect(self._on_all_conditions_changed)
        options_layout.addWidget(self.all_conditions_checkbox)

        grid = QGridLayout()
        for index, condition_name in enumerate(NEGATIVE_CONDITIONS):
            checkbox = QCheckBox(condition_name)
            checkbox.stateChanged.connect(self._on_condition_checkbox_changed)
            self.condition_checkboxes[condition_name] = checkbox
            grid.addWidget(checkbox, index // 3, index % 3)
        options_layout.addLayout(grid)

        note = QLabel("Miracle Cure is intentionally excluded from cure auto-buy.")
        note.setWordWrap(True)
        options_layout.addWidget(note)
        layout.addWidget(self.condition_options_widget)
        return group

    def _build_training_group(self):
        group = QGroupBox("Training Items")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        friendship_group = QGroupBox("Grilled Carrots")
        friendship_layout = QVBoxLayout(friendship_group)
        friendship_layout.setSpacing(8)
        self.auto_buy_friendship = HoverPreviewCheckBox(
            "Buy Grilled Carrots when enough support cards are still below rainbow bond",
            self.preview_popup,
            lambda: "Item: Grilled Carrots",
            lambda: _get_catalog_items_by_name("Grilled Carrots"),
        )
        self.auto_buy_friendship.stateChanged.connect(self._on_auto_buy_friendship_changed)
        friendship_layout.addWidget(self.auto_buy_friendship)
        self.friendship_options_widget = QWidget()
        friendship_row = QHBoxLayout(self.friendship_options_widget)
        friendship_row.setContentsMargins(18, 0, 0, 0)
        friendship_row.addWidget(QLabel("Buy when support cards below rainbow bond level (4) is at least:"))
        self.friendship_threshold_spin = QSpinBox()
        self.friendship_threshold_spin.setMinimum(1)
        self.friendship_threshold_spin.setMaximum(6)
        self.friendship_threshold_spin.valueChanged.connect(self._save_items_config)
        friendship_row.addWidget(self.friendship_threshold_spin)
        friendship_row.addStretch()
        friendship_layout.addWidget(self.friendship_options_widget)
        layout.addWidget(friendship_group)

        charm_group = QGroupBox("Good-luck Charm")
        charm_layout = QGridLayout(charm_group)
        self.good_luck_charm_enabled = HoverPreviewCheckBox(
            "Enable Good-luck Charm logic",
            self.preview_popup,
            lambda: "Item: Good-Luck Charm",
            lambda: _get_catalog_items_by_name("Good-Luck Charm"),
        )
        self.good_luck_charm_enabled.stateChanged.connect(self._on_good_luck_charm_changed)
        charm_layout.addWidget(self.good_luck_charm_enabled, 0, 0, 1, 2)
        self.good_luck_charm_options_widget = QWidget()
        good_luck_options_layout = QGridLayout(self.good_luck_charm_options_widget)
        good_luck_options_layout.setContentsMargins(18, 0, 0, 0)
        self.good_luck_charm_require_score = QCheckBox("Require chosen training score above:")
        self.good_luck_charm_require_score.stateChanged.connect(self._save_items_config)
        good_luck_options_layout.addWidget(self.good_luck_charm_require_score, 0, 0)
        self.good_luck_charm_score_threshold = QDoubleSpinBox()
        self.good_luck_charm_score_threshold.setDecimals(1)
        self.good_luck_charm_score_threshold.setRange(0.0, 20.0)
        self.good_luck_charm_score_threshold.setSingleStep(0.5)
        self.good_luck_charm_score_threshold.valueChanged.connect(self._save_items_config)
        good_luck_options_layout.addWidget(self.good_luck_charm_score_threshold, 0, 1)
        self.good_luck_charm_require_buff = QCheckBox("Require Training Buff or Specialized Training Buff used this turn")
        self.good_luck_charm_require_buff.stateChanged.connect(self._save_items_config)
        good_luck_options_layout.addWidget(self.good_luck_charm_require_buff, 1, 0, 1, 2)
        charm_layout.addWidget(self.good_luck_charm_options_widget, 1, 0, 1, 2)
        layout.addWidget(charm_group)

        buff_group = QGroupBox("Training Buffs")
        buff_layout = QGridLayout(buff_group)
        training_buff_label = HoverPreviewLabel(
            "Training Buff score threshold:",
            self.preview_popup,
            lambda: "Effect Type: Training Buff",
            lambda: _get_catalog_items_by_effect_type("Training Buff"),
        )
        buff_layout.addWidget(training_buff_label, 0, 0)
        self.training_buff_score_threshold = QDoubleSpinBox()
        self.training_buff_score_threshold.setDecimals(1)
        self.training_buff_score_threshold.setRange(0.0, 20.0)
        self.training_buff_score_threshold.setSingleStep(0.5)
        self.training_buff_score_threshold.valueChanged.connect(self._save_items_config)
        buff_layout.addWidget(self.training_buff_score_threshold, 0, 1)
        self.specialized_requires_training_buff = HoverPreviewCheckBox(
            "Specialized Training Buff requires Training Buff active or used",
            self.preview_popup,
            lambda: "Effect Type: Specialized Training Buff",
            lambda: _get_catalog_items_by_effect_type("Specialized Training Buff"),
        )
        self.specialized_requires_training_buff.stateChanged.connect(self._save_items_config)
        buff_layout.addWidget(self.specialized_requires_training_buff, 1, 0, 1, 2)
        buffs_period_label = HoverPreviewLabel(
            "Use buffs only during:",
            self.preview_popup,
            lambda: "Training Buff items",
            lambda: _get_catalog_items_by_effect_type("Training Buff") + _get_catalog_items_by_effect_type("Specialized Training Buff"),
        )
        buff_layout.addWidget(buffs_period_label, 2, 0, 1, 2)
        self.training_buff_periods_widget = QWidget()
        periods_layout = QVBoxLayout(self.training_buff_periods_widget)
        periods_layout.setContentsMargins(18, 0, 0, 0)
        periods_layout.setSpacing(6)
        period_options = [
            ("Any time", "any_time"),
            ("Classic / Senior Summer (July / August)", "classic_senior_summer"),
            ("Senior Year", "senior_year"),
            ("TS Climax", "ts_climax"),
        ]
        for label, key in period_options:
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self._on_training_buff_period_changed)
            self.training_buff_period_checkboxes[key] = checkbox
            periods_layout.addWidget(checkbox)
        buff_layout.addWidget(self.training_buff_periods_widget, 3, 0, 1, 2)
        layout.addWidget(buff_group)

        level_group = QGroupBox("Training Level Items")
        level_layout = QGridLayout(level_group)
        self.enable_training_level_items = HoverPreviewCheckBox(
            "Automatically buy training level items",
            self.preview_popup,
            lambda: "Effect Type: Training Level",
            lambda: _get_catalog_items_by_effect_type("Training Level"),
        )
        self.enable_training_level_items.stateChanged.connect(self._on_training_level_toggle_changed)
        level_layout.addWidget(self.enable_training_level_items, 0, 0, 1, 2)
        self.training_level_options_widget = QWidget()
        training_level_options_layout = QGridLayout(self.training_level_options_widget)
        training_level_options_layout.setContentsMargins(18, 0, 0, 0)
        training_level_options_layout.addWidget(QLabel("Buy when training level is below:"), 0, 0)
        self.training_level_threshold = QSpinBox()
        self.training_level_threshold.setMinimum(1)
        self.training_level_threshold.setMaximum(5)
        self.training_level_threshold.valueChanged.connect(self._save_items_config)
        training_level_options_layout.addWidget(self.training_level_threshold, 0, 1)
        for index, (label, key) in enumerate((("Speed", "spd"), ("Stamina", "sta"), ("Power", "pwr"), ("Guts", "guts"), ("Wit", "wit"))):
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self._save_items_config)
            self.training_level_stat_checkboxes[key] = checkbox
            training_level_options_layout.addWidget(checkbox, 1 + index // 3, index % 3)
        level_layout.addWidget(self.training_level_options_widget, 1, 0, 1, 2)
        layout.addWidget(level_group)

        shuffle_group = QGroupBox("Training Shuffle")
        shuffle_layout = QGridLayout(shuffle_group)
        training_shuffle_label = HoverPreviewLabel(
            "Use when best training score is below:",
            self.preview_popup,
            lambda: "Effect Type: Training Shuffle",
            lambda: _get_catalog_items_by_effect_type("Training Shuffle"),
        )
        shuffle_layout.addWidget(training_shuffle_label, 0, 0)
        self.training_shuffle_score_threshold = QDoubleSpinBox()
        self.training_shuffle_score_threshold.setDecimals(1)
        self.training_shuffle_score_threshold.setRange(0.0, 20.0)
        self.training_shuffle_score_threshold.setSingleStep(0.5)
        self.training_shuffle_score_threshold.valueChanged.connect(self._save_items_config)
        shuffle_layout.addWidget(self.training_shuffle_score_threshold, 0, 1)
        self.training_shuffle_restricted = QCheckBox("Only use Training Shuffle in Summer and TS Climax")
        self.training_shuffle_restricted.stateChanged.connect(self._save_items_config)
        shuffle_layout.addWidget(self.training_shuffle_restricted, 1, 0, 1, 2)
        layout.addWidget(shuffle_group)

        return group

    def _build_race_group(self):
        group = QGroupBox("Race Items")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        self.reserve_hammers = HoverPreviewCheckBox(
            "Reserve at least 3 Cleat Hammers for TS Climax",
            self.preview_popup,
            lambda: "Effect Type: Race Bonus",
            lambda: _get_catalog_items_by_effect_type("Race Bonus"),
        )
        self.reserve_hammers.stateChanged.connect(self._save_items_config)
        layout.addWidget(self.reserve_hammers)

        self.use_glowstick_ts_climax = HoverPreviewCheckBox(
            "Use Glowstick on TS Climax races",
            self.preview_popup,
            lambda: "Item: Glow Sticks",
            lambda: _get_catalog_items_by_name("Glow Sticks"),
        )
        self.use_glowstick_ts_climax.stateChanged.connect(self._save_items_config)
        layout.addWidget(self.use_glowstick_ts_climax)

        note = QLabel("Per-custom-race Glowstick selection is configured in the Custom Race editor.")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _get_items_dir(self):
        items_dir = os.path.join("template", "items")
        os.makedirs(items_dir, exist_ok=True)
        return items_dir

    def _default_template_data(self):
        return {
            "items_priority": [],
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

    def _set_condition_checkboxes_enabled(self, enabled):
        self.condition_options_widget.setVisible(enabled)
        self.all_conditions_checkbox.setEnabled(enabled)
        for checkbox in self.condition_checkboxes.values():
            checkbox.setEnabled(enabled)

    def _set_friendship_options_visible(self, visible):
        self.friendship_options_widget.setVisible(visible)

    def _set_good_luck_charm_options_visible(self, visible):
        self.good_luck_charm_options_widget.setVisible(visible)

    def _set_training_level_options_visible(self, visible):
        self.training_level_options_widget.setVisible(visible)

    def _save_items_config(self):
        if getattr(self, "_loading", False):
            return

        filename = self.template_combo.currentText()
        if not filename:
            return

        config = self.main_window.get_config()
        items_config = dict(DEFAULT_ITEM_SETTINGS)
        items_config.update(config.get("items", {}))

        items_config["item_purchase_file"] = f"template/items/{filename}"
        items_config["budget_strategy"] = self.budget_strategy_combo.currentData()
        items_config["purchase_max_swipes"] = self.purchase_max_swipes_spin.value()
        items_config["shop_swipe_time_offset"] = self.shop_swipe_offset_spin.value()
        items_config["auto_buy_mood_items"] = self.auto_buy_mood.isChecked()
        items_config["auto_buy_negative_cure_items"] = self.auto_buy_negative_cure.isChecked()
        items_config["auto_buy_negative_cure_conditions"] = [
            name for name, checkbox in self.condition_checkboxes.items() if checkbox.isChecked()
        ]
        items_config["auto_buy_friendship_items"] = self.auto_buy_friendship.isChecked()
        items_config["friendship_support_threshold"] = self.friendship_threshold_spin.value()
        items_config["good_luck_charm_enabled"] = self.good_luck_charm_enabled.isChecked()
        items_config["good_luck_charm_score_threshold"] = self.good_luck_charm_score_threshold.value()
        items_config["good_luck_charm_require_score"] = self.good_luck_charm_require_score.isChecked()
        items_config["good_luck_charm_require_buff"] = self.good_luck_charm_require_buff.isChecked()
        items_config["training_buff_score_threshold"] = self.training_buff_score_threshold.value()
        items_config["specialized_buff_requires_training_buff"] = self.specialized_requires_training_buff.isChecked()
        selected_periods = [key for key, checkbox in self.training_buff_period_checkboxes.items() if checkbox.isChecked()]
        items_config["training_buff_periods"] = selected_periods or ["any_time"]
        items_config["training_buff_period"] = items_config["training_buff_periods"][0]
        items_config["enable_training_level_items"] = self.enable_training_level_items.isChecked()
        items_config["training_level_threshold"] = self.training_level_threshold.value()
        items_config["training_level_stats"] = [
            key for key, checkbox in self.training_level_stat_checkboxes.items() if checkbox.isChecked()
        ]
        items_config["training_shuffle_score_threshold"] = self.training_shuffle_score_threshold.value()
        items_config["training_shuffle_restricted_periods_only"] = self.training_shuffle_restricted.isChecked()
        items_config["reserve_ts_climax_hammers"] = self.reserve_hammers.isChecked()
        items_config["use_glowstick_ts_climax"] = self.use_glowstick_ts_climax.isChecked()

        config["items"] = items_config
        self.main_window.save_config()

    def load_config(self):
        self._loading = True
        self._load_templates()

        config = self.main_window.get_config()
        items_config = dict(DEFAULT_ITEM_SETTINGS)
        items_config.update(config.get("items", {}))
        item_file = os.path.basename(items_config.get("item_purchase_file", "template/items/default.json"))

        self._ensure_template_exists(item_file)
        self._load_templates()

        index = self.template_combo.findText(item_file)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)

        strategy_index = self.budget_strategy_combo.findData(items_config.get("budget_strategy", "save_priority"))
        if strategy_index >= 0:
            self.budget_strategy_combo.setCurrentIndex(strategy_index)
        self.purchase_max_swipes_spin.setValue(int(items_config.get("purchase_max_swipes", 10)))
        self.shop_swipe_offset_spin.setValue(int(items_config.get("shop_swipe_time_offset", 0)))

        self.auto_buy_mood.setChecked(bool(items_config.get("auto_buy_mood_items", False)))
        self.auto_buy_negative_cure.setChecked(bool(items_config.get("auto_buy_negative_cure_items", False)))

        selected_conditions = set(items_config.get("auto_buy_negative_cure_conditions", NEGATIVE_CONDITIONS))
        all_selected = len(selected_conditions) == len(NEGATIVE_CONDITIONS)
        self.all_conditions_checkbox.setChecked(all_selected)
        for name, checkbox in self.condition_checkboxes.items():
            checkbox.setChecked(name in selected_conditions)
        self._set_condition_checkboxes_enabled(self.auto_buy_negative_cure.isChecked())

        self.auto_buy_friendship.setChecked(bool(items_config.get("auto_buy_friendship_items", False)))
        self._set_friendship_options_visible(self.auto_buy_friendship.isChecked())
        self.friendship_threshold_spin.setValue(int(items_config.get("friendship_support_threshold", 1)))
        self.good_luck_charm_enabled.setChecked(bool(items_config.get("good_luck_charm_enabled", True)))
        self._set_good_luck_charm_options_visible(self.good_luck_charm_enabled.isChecked())
        self.good_luck_charm_score_threshold.setValue(float(items_config.get("good_luck_charm_score_threshold", 2.0)))
        self.good_luck_charm_require_score.setChecked(bool(items_config.get("good_luck_charm_require_score", True)))
        self.good_luck_charm_require_buff.setChecked(bool(items_config.get("good_luck_charm_require_buff", False)))
        self.training_buff_score_threshold.setValue(float(items_config.get("training_buff_score_threshold", 2.0)))
        self.specialized_requires_training_buff.setChecked(bool(items_config.get("specialized_buff_requires_training_buff", False)))
        selected_periods = set(items_config.get("training_buff_periods", [items_config.get("training_buff_period", "any_time")]))
        if not selected_periods:
            selected_periods = {"any_time"}
        for key, checkbox in self.training_buff_period_checkboxes.items():
            checkbox.setChecked(key in selected_periods)
        self.enable_training_level_items.setChecked(bool(items_config.get("enable_training_level_items", False)))
        self._set_training_level_options_visible(self.enable_training_level_items.isChecked())
        self.training_level_threshold.setValue(int(items_config.get("training_level_threshold", 3)))
        selected_stats = set(items_config.get("training_level_stats", []))
        for key, checkbox in self.training_level_stat_checkboxes.items():
            checkbox.setChecked(key in selected_stats)
        self.training_shuffle_score_threshold.setValue(float(items_config.get("training_shuffle_score_threshold", 1.0)))
        self.training_shuffle_restricted.setChecked(bool(items_config.get("training_shuffle_restricted_periods_only", False)))
        self.reserve_hammers.setChecked(bool(items_config.get("reserve_ts_climax_hammers", True)))
        self.use_glowstick_ts_climax.setChecked(bool(items_config.get("use_glowstick_ts_climax", False)))

        self._loading = False

    def _on_auto_buy_negative_cure_changed(self):
        enabled = self.auto_buy_negative_cure.isChecked()
        self._set_condition_checkboxes_enabled(enabled)
        self._save_items_config()

    def _on_auto_buy_friendship_changed(self):
        enabled = self.auto_buy_friendship.isChecked()
        self._set_friendship_options_visible(enabled)
        self._save_items_config()

    def _on_good_luck_charm_changed(self):
        enabled = self.good_luck_charm_enabled.isChecked()
        self._set_good_luck_charm_options_visible(enabled)
        self._save_items_config()

    def _on_training_level_toggle_changed(self):
        enabled = self.enable_training_level_items.isChecked()
        self._set_training_level_options_visible(enabled)
        self._save_items_config()

    def _on_training_buff_period_changed(self):
        if getattr(self, "_loading", False):
            return
        if self.sender() is self.training_buff_period_checkboxes.get("any_time") and self.training_buff_period_checkboxes["any_time"].isChecked():
            for key, checkbox in self.training_buff_period_checkboxes.items():
                if key == "any_time":
                    continue
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
        elif self.sender() is not self.training_buff_period_checkboxes.get("any_time") and self.sender().isChecked():
            any_checkbox = self.training_buff_period_checkboxes["any_time"]
            any_checkbox.blockSignals(True)
            any_checkbox.setChecked(False)
            any_checkbox.blockSignals(False)

        if not any(checkbox.isChecked() for checkbox in self.training_buff_period_checkboxes.values()):
            any_checkbox = self.training_buff_period_checkboxes["any_time"]
            any_checkbox.blockSignals(True)
            any_checkbox.setChecked(True)
            any_checkbox.blockSignals(False)

        self._save_items_config()

    def _on_all_conditions_changed(self):
        if getattr(self, "_loading", False):
            return
        checked = self.all_conditions_checkbox.isChecked()
        for checkbox in self.condition_checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        self._save_items_config()

    def _on_condition_checkbox_changed(self):
        if getattr(self, "_loading", False):
            return
        all_checked = all(checkbox.isChecked() for checkbox in self.condition_checkboxes.values())
        self.all_conditions_checkbox.blockSignals(True)
        self.all_conditions_checkbox.setChecked(all_checked)
        self.all_conditions_checkbox.blockSignals(False)
        self._save_items_config()
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

    def _edit_priority_template(self):
        filename = self.template_combo.currentText()
        if not filename:
            return

        self._ensure_template_exists(filename)
        template_path = os.path.join(self._get_items_dir(), filename)

        from .item_priority_window import ItemPriorityWindow

        dialog = ItemPriorityWindow(self, template_path)
        dialog.exec()
