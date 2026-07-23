"""API-mode Grand Live lesson selection and execution."""

from __future__ import annotations

import json
import os
import re
import time

from utils.core.config_loader import load_main_config
from utils.core.log import log_info, log_warning
from utils.inputs.input import tap, tap_on_image
from utils.integrations.umat_api import get_grand_live, get_status


DEFAULT_CATEGORY_PRIORITY = ["stat", "recovery", "skill_hint"]
DEFAULT_STAT_PRIORITY = ["spd", "sta", "pwr", "guts", "wit", "skill_points"]
DEFAULT_SKILL_TYPES = [
    "Aptitude Appropriate",
    "Dirt", "Sprint", "Mile", "Medium", "Long",
    "Front Runner", "Pace Chaser", "Late Surger", "End Closer",
]
STAT_EFFECT_KEYS = {
    "speed": "spd",
    "stamina": "sta",
    "power": "pwr",
    "guts": "guts",
    "wit": "wit",
    "skill pts": "skill_points",
}
# The three API slots are displayed as vertical cards on the lesson screen.
LESSON_SLOT_COORDS = {1: (540, 525), 2: (540, 935), 3: (540, 1350)}


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _load_json(path, default):
    full_path = path if os.path.isabs(path) else os.path.join(_project_root(), path)
    try:
        with open(full_path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else default
    except (OSError, ValueError):
        return default


def _lesson_config(config=None):
    config = config or load_main_config()
    lessons = config.get("lessons", {})
    technique = _load_json(
        lessons.get("technique_template", "template/lessons/technique/default.json"),
        {},
    )
    songs = _load_json(
        lessons.get("song_template", "template/lessons/songs/default.json"),
        {},
    )
    return technique, songs


def _effect_stat(effect):
    prefix = str(effect or "").split("+", 1)[0].strip().lower()
    return STAT_EFFECT_KEYS.get(prefix)


def _recovery_value(effect):
    match = re.search(r"Energy\s*\+\s*(\d+)", str(effect or ""), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _skill_type(effect):
    match = re.search(r"\(([^)]+)\)", str(effect or ""))
    if match:
        return match.group(1).strip()
    if "appropriate for aptitude" in str(effect or "").lower():
        return "Aptitude Appropriate"
    return None


def _category_rank(choice, technique):
    priority = technique.get("category_priority", DEFAULT_CATEGORY_PRIORITY)
    try:
        return priority.index(choice.get("category"))
    except ValueError:
        return len(priority)


def _technique_rank(choice, technique, energy_current, energy_max):
    category = choice.get("category")
    if category == "stat":
        stat = _effect_stat(choice.get("effect"))
        priority = technique.get("stat_priority", DEFAULT_STAT_PRIORITY)
        if stat not in priority:
            return None
        return priority.index(stat)

    if category == "recovery":
        if technique.get("save_recovery", True):
            recovery = _recovery_value(choice.get("effect"))
            if recovery and energy_current + recovery > energy_max:
                return None
        return 0

    if category == "skill_hint":
        skill_type = _skill_type(choice.get("effect"))
        allowed = technique.get("skill_types", DEFAULT_SKILL_TYPES)
        if skill_type not in allowed:
            return None
        return allowed.index(skill_type)

    return None


def choose_technique_lesson(choices, technique, energy_current=0, energy_max=100):
    """Return the best allowed technique choice, reserving it later if needed."""
    ranked = []
    for choice in choices:
        if choice.get("category") == "song":
            continue
        inner_rank = _technique_rank(choice, technique, energy_current, energy_max)
        if inner_rank is None:
            continue
        ranked.append((_category_rank(choice, technique), inner_rank, int(choice.get("slot", 99)), choice))
    return min(ranked, key=lambda row: row[:3])[-1] if ranked else None


def choose_song_lesson(choices, songs):
    """Prefer priority group first, then order; affordability does not alter priority."""
    groups = songs.get("priority_groups", [[], [], []])
    positions = {
        int(song_id): (group_index, song_index)
        for group_index, group in enumerate(groups)
        for song_index, song_id in enumerate(group)
    }
    ranked = []
    for choice in choices:
        if choice.get("category") != "song":
            continue
        song = choice.get("song") or {}
        identifiers = (song.get("live_id"), song.get("command_id"), choice.get("id"))
        rank = next((positions[int(value)] for value in identifiers if value is not None and int(value) in positions), None)
        if rank is not None:
            ranked.append((rank[0], rank[1], int(choice.get("slot", 99)), choice))
    return min(ranked, key=lambda row: row[:3])[-1] if ranked else None


def choose_lesson(grand_live, config=None, energy_current=0, energy_max=100):
    """Choose from the API's current three slots using the active templates."""
    choices = (grand_live or {}).get("lesson_choices", [])
    if not choices:
        return None
    technique, songs = _lesson_config(config)
    if all(choice.get("category") == "song" for choice in choices):
        return choose_song_lesson(choices, songs)
    return choose_technique_lesson(choices, technique, energy_current, energy_max)


def handle_lessons(energy_current=None, energy_max=None):
    """Open Lessons and tap the configured API-selected slot."""
    grand_live = get_grand_live()
    reserve_square_id = int((grand_live or {}).get("reserve_square_id", 0) or 0)
    if reserve_square_id:
        reserved_choice = next(
            (
                item for item in (grand_live or {}).get("lesson_choices", [])
                if reserve_square_id in (
                    int(item.get("id", 0) or 0),
                    int(item.get("master_bonus_id", 0) or 0),
                )
            ),
            None,
        )
        if reserved_choice is None or not reserved_choice.get("affordable", False):
            log_info(f"Keeping reserved Grand Live lesson #{reserve_square_id} until it is affordable")
            return False
        choice = reserved_choice
        log_info(f"Reserved Grand Live lesson #{reserve_square_id} is now affordable")
    else:
        choice = None
    if energy_current is None or energy_max is None:
        status = get_status() or {}
        energy = status.get("energy", {})
        energy_current = energy.get("current", 0)
        energy_max = energy.get("max", 100)
    if choice is None:
        choice = choose_lesson(grand_live, energy_current=energy_current, energy_max=energy_max)
    if choice is None:
        log_info("No lesson matches the active lesson template")
        return False

    if not (
        tap_on_image("assets/grandlive/lessons_btn.png", confidence=0.8, min_search=2)
        or tap_on_image("assets/grandlive/lessons_btn_2.png", confidence=0.8, min_search=2)
    ):
        log_warning("Grand Live Lessons button disappeared before it could be opened")
        return False

    time.sleep(0.8)
    slot = int(choice.get("slot", 0))
    coordinate = LESSON_SLOT_COORDS.get(slot)
    if coordinate is None:
        log_warning(f"Grand Live API returned unsupported lesson slot: {slot}")
        return False

    action = "Studying" if choice.get("affordable", False) else "Reserving"
    log_info(
        f"{action} lesson slot {slot}: {choice.get('title', 'Unknown')} "
        f"({choice.get('effect', '')})"
    )
    tap(*coordinate)
    time.sleep(0.8)
    tap_on_image("assets/buttons/ok_btn.png", confidence=0.7, min_search=3)
    return True
