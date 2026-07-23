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
from utils.vision.recognizer import locate_on_screen


DEFAULT_CATEGORY_PRIORITY = ["stat", "recovery", "skill_hint"]
DEFAULT_STAT_PRIORITY = ["spd", "sta", "pwr", "guts", "wit", "skill_points"]
DEFAULT_SELECTION_METHOD = "save_best"
AVAILABLE_SELECTION_METHOD = "available"
DEFAULT_SONG_REQUIREMENTS = {
    "catch_up_missed_minimum": False,
    "concerts": {
        str(index): {"minimum": 3, "maximum": 21}
        for index in range(1, 6)
    },
}
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
NORMAL_LESSONS_BUTTON = "assets/grandlive/lessons_btn.png"
CONCERT_LESSONS_BUTTON = "assets/grandlive/lessons_btn_2.png"
LEARN_BUTTON = "assets/grandlive/learn_btn.png"
BACK_BUTTON = "assets/buttons/back_btn.png"
LESSON_UI_TIMEOUT = 10.0


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


def _song_requirements(config=None):
    config = config or load_main_config()
    raw = config.get("lessons", {}).get("song_requirements", {})
    raw_concerts = raw.get("concerts", {})
    concerts = {}
    for index in range(1, 6):
        configured = raw_concerts.get(str(index), {})
        minimum = max(3, int(configured.get("minimum", 3)))
        maximum = max(minimum, int(configured.get("maximum", 21)))
        concerts[str(index)] = {"minimum": minimum, "maximum": maximum}
    return {
        "catch_up_missed_minimum": bool(
            raw.get("catch_up_missed_minimum", False)
        ),
        "concerts": concerts,
    }


def next_concert_index(grand_live):
    """Return the upcoming concert number (1-5) from detailed API state."""
    next_concert = (grand_live or {}).get("next_concert") or {}
    value = next_concert.get("id", next_concert.get("live_type"))
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    if 1 <= value <= 5:
        return value

    completed = len((grand_live or {}).get("live_results") or [])
    return min(5, completed + 1) if completed < 5 else 5


def _song_progress_counts(grand_live):
    song_progress = (grand_live or {}).get("song_progress") or {}
    hype = song_progress.get("hype") or {}
    current_concert_songs = song_progress.get("next_concert")
    if current_concert_songs is None:
        current_concert_songs = hype.get("current")
    if current_concert_songs is None:
        current_concert_songs = len(
            (grand_live or {}).get("next_concert_songs") or []
        )
    return (
        int(current_concert_songs or 0),
        int(song_progress.get("learned_total", 0) or 0),
    )


def song_requirement_status(grand_live, concert_index=None, config=None):
    """Calculate per-concert or cumulative minimum progress from API state."""
    requirements = _song_requirements(config)
    concert_index = int(concert_index or next_concert_index(grand_live))
    concert_index = min(5, max(1, concert_index))
    current_requirement = requirements["concerts"][str(concert_index)]
    current_concert_songs, learned_total = _song_progress_counts(grand_live)

    catch_up = requirements["catch_up_missed_minimum"]
    if catch_up:
        target = sum(
            requirements["concerts"][str(index)]["minimum"]
            for index in range(1, concert_index + 1)
        )
        progress = learned_total
    else:
        target = current_requirement["minimum"]
        progress = current_concert_songs

    return {
        "concert_index": concert_index,
        "minimum": current_requirement["minimum"],
        "maximum": current_requirement["maximum"],
        "current_concert_songs": current_concert_songs,
        "learned_total": learned_total,
        "catch_up": catch_up,
        "target": target,
        "progress": progress,
        "deficit": max(0, target - progress),
    }


def unknown_concert_requirement_status(grand_live):
    """Return the safe requirement used when the concert day is unknown."""
    current_concert_songs, learned_total = _song_progress_counts(grand_live)
    minimum = 3
    maximum = DEFAULT_SONG_REQUIREMENTS["concerts"]["1"]["maximum"]
    return {
        "concert_index": None,
        "minimum": minimum,
        "maximum": maximum,
        "current_concert_songs": current_concert_songs,
        "learned_total": learned_total,
        "catch_up": False,
        "target": minimum,
        "progress": current_concert_songs,
        "deficit": max(0, minimum - current_concert_songs),
    }


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


def _recovery_would_overflow(choice, technique, energy_current, energy_max):
    if (
        (choice or {}).get("category") != "recovery"
        or not technique.get("save_recovery", True)
    ):
        return False
    recovery = _recovery_value(choice.get("effect"))
    return bool(recovery and energy_current + recovery > energy_max)


def _technique_rank(
    choice,
    technique,
    energy_current,
    energy_max,
    keep_overflow_recovery=False,
):
    category = choice.get("category")
    if category == "stat":
        stat = _effect_stat(choice.get("effect"))
        priority = technique.get("stat_priority", DEFAULT_STAT_PRIORITY)
        if stat not in priority:
            return None
        return priority.index(stat)

    if category == "recovery":
        if (
            not keep_overflow_recovery
            and _recovery_would_overflow(
                choice, technique, energy_current, energy_max
            )
        ):
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
    selection_method = technique.get("selection_method", DEFAULT_SELECTION_METHOD)
    for choice in choices:
        if choice.get("category") == "song":
            continue
        if (
            selection_method == AVAILABLE_SELECTION_METHOD
            and not choice.get("affordable", False)
        ):
            continue
        inner_rank = _technique_rank(
            choice,
            technique,
            energy_current,
            energy_max,
            keep_overflow_recovery=(
                selection_method == DEFAULT_SELECTION_METHOD
            ),
        )
        if inner_rank is None:
            continue
        ranked.append((_category_rank(choice, technique), inner_rank, int(choice.get("slot", 99)), choice))
    return min(ranked, key=lambda row: row[:3])[-1] if ranked else None


def choose_song_lesson(choices, songs):
    """Prefer priority group then order, optionally excluding unaffordable songs."""
    groups = songs.get("priority_groups", [[], [], []])
    selection_method = songs.get("selection_method", DEFAULT_SELECTION_METHOD)
    positions = {
        int(song_id): (group_index, song_index)
        for group_index, group in enumerate(groups)
        for song_index, song_id in enumerate(group)
    }
    ranked = []
    for choice in choices:
        if choice.get("category") != "song":
            continue
        if (
            selection_method == AVAILABLE_SELECTION_METHOD
            and not choice.get("affordable", False)
        ):
            continue
        song = choice.get("song") or {}
        identifiers = (song.get("live_id"), song.get("command_id"), choice.get("id"))
        rank = next((positions[int(value)] for value in identifiers if value is not None and int(value) in positions), None)
        if rank is not None:
            ranked.append((rank[0], rank[1], int(choice.get("slot", 99)), choice))
    return min(ranked, key=lambda row: row[:3])[-1] if ranked else None


def _song_settings_for_progress(grand_live, songs):
    """Apply the optional save-for-better rule after three current-cycle songs."""
    effective = dict(songs)
    current_concert_songs, _ = _song_progress_counts(grand_live)
    if (
        effective.get("save_for_better_after_three", False)
        and current_concert_songs >= 3
    ):
        effective["selection_method"] = DEFAULT_SELECTION_METHOD
    return effective


def choose_lesson(grand_live, config=None, energy_current=0, energy_max=100):
    """Choose from the API's current three slots using the active templates."""
    choices = (grand_live or {}).get("lesson_choices", [])
    if not choices:
        return None
    config = config or load_main_config()
    technique, songs = _lesson_config(config)
    if all(choice.get("category") == "song" for choice in choices):
        requirement = song_requirement_status(grand_live, config=config)
        if requirement["current_concert_songs"] >= requirement["maximum"]:
            return None
        return choose_song_lesson(
            choices,
            _song_settings_for_progress(grand_live, songs),
        )
    return choose_technique_lesson(choices, technique, energy_current, energy_max)


def _choice_selection_method(choice, technique, songs, grand_live=None):
    if (choice or {}).get("category") == "song":
        effective = _song_settings_for_progress(grand_live, songs)
        return effective.get("selection_method", DEFAULT_SELECTION_METHOD)
    return technique.get("selection_method", DEFAULT_SELECTION_METHOD)


def choose_any_available_lesson(
    grand_live, config=None, energy_current=0, energy_max=100
):
    """Choose any affordable lesson, preferring the active lesson templates."""
    choices = (grand_live or {}).get("lesson_choices", [])
    config = config or load_main_config()
    technique, songs = _lesson_config(config)
    affordable = [
        choice
        for choice in choices
        if choice.get("affordable", False)
    ]
    if not all(choice.get("category") == "song" for choice in choices):
        affordable = [
            choice
            for choice in affordable
            if not _recovery_would_overflow(
                choice, technique, energy_current, energy_max
            )
        ]
    if not affordable:
        return None

    if all(choice.get("category") == "song" for choice in choices):
        available_songs = dict(songs)
        available_songs["selection_method"] = AVAILABLE_SELECTION_METHOD
        preferred = choose_song_lesson(choices, available_songs)
    else:
        available_technique = dict(technique)
        available_technique["selection_method"] = AVAILABLE_SELECTION_METHOD
        preferred = choose_technique_lesson(
            choices,
            available_technique,
            energy_current,
            energy_max,
        )
    if preferred is not None:
        return preferred
    return min(affordable, key=lambda choice: int(choice.get("slot", 99)))


def _wait_for_image(
    image_path, timeout=LESSON_UI_TIMEOUT, confidence=0.8, poll_interval=0.1
):
    """Wait for an image and return its center without tapping it."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        location = locate_on_screen(image_path, confidence=confidence)
        if location:
            return location
        time.sleep(poll_interval)
    return None


def _double_tap_slot(choice):
    slot = int(choice.get("slot", 0))
    coordinate = LESSON_SLOT_COORDS.get(slot)
    if coordinate is None:
        log_warning(f"Grand Live API returned unsupported lesson slot: {slot}")
        return False
    tap(*coordinate)
    time.sleep(0.1)
    tap(*coordinate)
    return True


def _concert_requirement(grand_live, concert_index, config=None):
    if concert_index is None:
        return unknown_concert_requirement_status(grand_live)
    return song_requirement_status(
        grand_live,
        concert_index=concert_index,
        config=config,
    )


def _lesson_cost_text(choice):
    costs = []
    for cost in (choice or {}).get("cost") or []:
        name = cost.get("performance") or f"Type {cost.get('performance_type', '?')}"
        costs.append(f"{name} {cost.get('value', 0)}")
    return ", ".join(costs) if costs else "No cost data"


def _log_lesson_choices(grand_live):
    """Log the API lesson scan before applying selection rules."""
    choices = (grand_live or {}).get("lesson_choices") or []
    if not choices:
        log_info("Grand Live lesson scan: no lessons found")
        return

    log_info(f"Grand Live lesson scan: found {len(choices)} lesson(s)")
    for choice in sorted(choices, key=lambda item: int(item.get("slot", 99))):
        category = str(choice.get("category", "unknown")).replace("_", " ").title()
        affordability = (
            "Affordable" if choice.get("affordable", False) else "Unaffordable"
        )
        log_info(
            f"  Slot {choice.get('slot', '?')} | {category} | "
            f"{choice.get('title', 'Unknown')} | "
            f"{choice.get('effect', 'No effect data')} | "
            f"Cost: {_lesson_cost_text(choice)} | {affordability}"
        )


def handle_concert_day_lessons(concert_index, config=None):
    """Try one affordable song when the concert-day minimum is still unmet."""
    grand_live = get_grand_live()
    if not grand_live:
        log_warning("Cannot check concert song requirement: Grand Live API unavailable")
        return False

    unknown_concert = concert_index is None
    requirement = (
        unknown_concert_requirement_status(grand_live)
        if unknown_concert
        else song_requirement_status(
            grand_live, concert_index=concert_index, config=config
        )
    )
    concert_label = "Unknown concert" if unknown_concert else f"Concert {concert_index}"
    if requirement["current_concert_songs"] >= requirement["maximum"]:
        log_info(
            f"{concert_label} song maximum met "
            f"({requirement['current_concert_songs']}/{requirement['maximum']})"
        )
        return False

    if requirement["deficit"] > 0:
        scope = "total" if requirement["catch_up"] else "current concert"
        log_info(
            f"{concert_label} song minimum not met for {scope}: "
            f"{requirement['progress']}/{requirement['target']}; "
            "trying any affordable technique or song lesson"
        )
    else:
        log_info(
            f"{concert_label} song minimum met "
            f"({requirement['progress']}/{requirement['target']}); "
            "continuing with the configured song method until it stops "
            "or the maximum is reached"
        )
    return handle_lessons(
        config=config,
        force_any_available=True,
        concert_day=True,
        concert_index=concert_index,
        grand_live=grand_live,
    )


def handle_lessons(
    energy_current=None,
    energy_max=None,
    *,
    config=None,
    force_any_available=False,
    concert_day=False,
    concert_index=None,
    grand_live=None,
):
    """Open Lessons and learn eligible API-selected lessons until none remain."""
    grand_live = grand_live or get_grand_live()
    if energy_current is None or energy_max is None:
        status = get_status() or {}
        energy = status.get("energy", {})
        energy_current = energy.get("current", 0)
        energy_max = energy.get("max", 100)

    def select_choice(state):
        choices = (state or {}).get("lesson_choices", [])
        _log_lesson_choices(state)
        technique, songs = _lesson_config(config)

        def should_save_recovery(choice):
            if not _recovery_would_overflow(
                choice, technique, energy_current, energy_max
            ):
                return False
            log_info(
                f"Saving Recovery lesson slot {choice.get('slot', '?')} "
                f"until its {choice.get('effect', 'Energy recovery')} will not "
                "overflow Energy"
            )
            return True

        reserve_square_id = int((state or {}).get("reserve_square_id", 0) or 0)
        reserved_choice = None
        if reserve_square_id:
            reserved_choice = next(
                (
                    item for item in choices
                    if reserve_square_id in (
                        int(item.get("id", 0) or 0),
                        int(item.get("master_bonus_id", 0) or 0),
                    )
                ),
                None,
            )

        if force_any_available:
            requirement = _concert_requirement(
                state,
                concert_index,
                config=config,
            )
            if requirement["current_concert_songs"] >= requirement["maximum"]:
                log_info(
                    f"Concert song maximum reached "
                    f"({requirement['current_concert_songs']}/"
                    f"{requirement['maximum']})"
                )
                return None

            if requirement["deficit"] > 0:
                if (
                    reserved_choice is not None
                    and reserved_choice.get("affordable", False)
                ):
                    return reserved_choice
                return choose_any_available_lesson(
                    state,
                    config=config,
                    energy_current=energy_current,
                    energy_max=energy_max,
                )

            if reserved_choice is not None:
                reserved_method = _choice_selection_method(
                    reserved_choice, technique, songs, state
                )
                if reserved_method == DEFAULT_SELECTION_METHOD:
                    if reserved_choice.get("affordable", False):
                        if should_save_recovery(reserved_choice):
                            return None
                        return reserved_choice
                    log_info(
                        f"Saving Performance Points for reserved lesson "
                        f"#{reserve_square_id}"
                    )
                    return None

            selected = choose_lesson(
                state,
                config=config,
                energy_current=energy_current,
                energy_max=energy_max,
            )
            if selected is not None and not selected.get("affordable", False):
                log_info(
                    f"Saving Performance Points for lesson slot "
                    f"{selected.get('slot', '?')}: "
                    f"{selected.get('title', 'Unknown')}"
                )
                return None
            if selected is not None and should_save_recovery(selected):
                return None
            return selected

        if reserved_choice is not None:
            reserved_method = _choice_selection_method(
                reserved_choice, technique, songs, state
            )
            if (
                reserved_method == DEFAULT_SELECTION_METHOD
                and reserved_choice.get("affordable", False)
            ):
                if should_save_recovery(reserved_choice):
                    return None
                if reserved_choice.get("category") == "song":
                    requirement = song_requirement_status(state, config=config)
                    if (
                        requirement["current_concert_songs"]
                        >= requirement["maximum"]
                    ):
                        log_info(
                            f"Not learning reserved song: Concert "
                            f"{requirement['concert_index']} maximum "
                            f"({requirement['maximum']}) has been reached"
                        )
                        return None
                return reserved_choice
            if reserved_method == DEFAULT_SELECTION_METHOD:
                log_info(
                    f"Best reserved Grand Live lesson #{reserve_square_id} "
                    "is not affordable yet"
                )
                return None

        selected = choose_lesson(
            state,
            config=config,
            energy_current=energy_current,
            energy_max=energy_max,
        )
        if selected is not None and not selected.get("affordable", False):
            log_info(
                f"Saving Performance Points for lesson slot "
                f"{selected.get('slot', '?')}: "
                f"{selected.get('title', 'Unknown')}"
            )
            return None
        if selected is not None and should_save_recovery(selected):
            return None
        return selected

    choice = select_choice(grand_live)
    if choice is None:
        log_info(
            "No concert-day song lesson matches the current requirement and method"
            if force_any_available
            else "No affordable lesson matches the active lesson method"
        )
        return False

    entry_button = CONCERT_LESSONS_BUTTON if concert_day else NORMAL_LESSONS_BUTTON
    if not tap_on_image(entry_button, confidence=0.8, min_search=3):
        day_label = "concert" if concert_day else "normal"
        log_warning(f"Grand Live {day_label}-day Lessons button was not found")
        return False

    if not _wait_for_image(BACK_BUTTON):
        log_warning("Lesson screen did not finish opening")
        tap_on_image(BACK_BUTTON, confidence=0.8, min_search=2)
        return True

    while choice is not None:
        time.sleep(0.1)
        log_info(
            f"Learning lesson slot {choice.get('slot', '?')}: "
            f"{choice.get('title', 'Unknown')} ({choice.get('effect', '')})"
        )
        if not _double_tap_slot(choice):
            break

        learn_button = _wait_for_image(LEARN_BUTTON)
        if not learn_button:
            log_warning("Learn button did not appear after selecting the lesson")
            break
        time.sleep(0.1)
        tap(*learn_button)

        time.sleep(3.0)
        if not _wait_for_image(BACK_BUTTON):
            log_warning("Lesson screen did not return after learning the lesson")
            break

        grand_live = get_grand_live()
        if not grand_live:
            log_warning("Grand Live API unavailable after learning a lesson")
            break
        refreshed_status = get_status() or {}
        refreshed_energy = refreshed_status.get("energy") or {}
        energy_current = refreshed_energy.get("current", energy_current)
        energy_max = refreshed_energy.get("max", energy_max)
        choice = select_choice(grand_live)

    if not tap_on_image(BACK_BUTTON, confidence=0.8, min_search=3):
        log_warning("Could not leave the Grand Live lesson screen")
    return True
