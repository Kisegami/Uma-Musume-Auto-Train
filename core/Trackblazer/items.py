import itertools
import json
import os
from copy import deepcopy

from utils.constants.trackblazer import MOOD_LIST


STAT_NAME_TO_KEY = {
    "speed": "spd",
    "stamina": "sta",
    "power": "pwr",
    "guts": "guts",
    "wit": "wit",
}

NEGATIVE_CONDITIONS = [
    "Night Owl",
    "Slacker",
    "Skin Outbreak",
    "Slow Metabolism",
    "Migraine",
    "Practice Poor",
]

DEFAULT_ITEM_SETTINGS = {
    "item_purchase_file": "template/items/default.json",
    "budget_strategy": "save_priority",
    "purchase_max_swipes": 10,
    "shop_swipe_time_offset": 0,
    "auto_buy_mood_items": False,
    "use_mood_items_to_reach_great": False,
    "save_energy_recovery_for_summer": False,
    "auto_buy_negative_cure_items": False,
    "auto_buy_negative_cure_conditions": list(NEGATIVE_CONDITIONS),
    "auto_buy_friendship_items": False,
    "friendship_support_threshold": 1,
    "good_luck_charm_enabled": True,
    "good_luck_charm_score_threshold": 2.0,
    "good_luck_charm_require_score": True,
    "good_luck_charm_require_buff": False,
    "training_buff_score_threshold": 2.0,
    "training_buff_rainbow_thresholds": {
        "normal": {"spd": 2, "sta": 2, "pwr": 2, "guts": 2, "wit": 2},
        "summer": {"spd": 2, "sta": 2, "pwr": 2, "guts": 2, "wit": 2},
    },
    "specialized_buff_requires_training_buff": False,
    "training_buff_periods": ["any_time"],
    "training_buff_period_rainbow_override_enabled": False,
    "training_buff_period_rainbow_override_threshold": 2,
    "training_buff_late_senior_rainbow_requirement_one": False,
    "training_buff_highest_rainbow_override_enabled": False,
    "training_buff_highest_rainbow_override_threshold": 3,
    "enable_training_level_items": False,
    "training_level_threshold": 3,
    "training_level_stats": [],
    "training_shuffle_score_threshold": 1.0,
    "training_shuffle_restricted_periods_only": False,
    "ts_climax_hammer_reserve_count": 3,
    "reserve_ts_climax_hammers": True,
    "use_glowstick_ts_climax": False,
}

GLOWSTICK_ITEM_NAME = "Glow Sticks"

_CATALOG_CACHE = None
_CATALOG_BY_ID = None
_CATALOG_BY_NAME = None


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _normalize_text(value):
    text = str(value or "").strip().lower()
    cleaned = []
    for ch in text:
        cleaned.append(ch if ch.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _normalize_stat_key(value):
    return STAT_NAME_TO_KEY.get(_normalize_text(value), "")


def _normalize_condition_name(value):
    normalized = _normalize_text(value)
    replacements = {
        "charming": "charming",
        "hot topic": "hot topic",
        "practice perfect": "practice perfect",
        "fast learner": "fast learner",
        "night owl": "night owl",
        "slacker": "slacker",
        "dry skin": "skin outbreak",
        "skin outbreak": "skin outbreak",
        "slow metabolism": "slow metabolism",
        "migraine": "migraine",
        "practice poor": "practice poor",
    }
    for key, mapped in replacements.items():
        if key in normalized:
            return mapped
    return normalized


def _derive_duration_turns(entry):
    if entry["effect_type"] != "Training Buff":
        return 0

    text = _normalize_text(entry.get("effect_text", ""))
    for turns in (4, 3, 2):
        if f"for {turns} turns" in text:
            return turns
    return 0


def _build_conflict_key(entry):
    if entry["effect_type"] == "Training Buff":
        return "training_buff:any"
    if entry["effect_type"] == "Specialized Training Buff" and entry["target_stat"]:
        return f"specialized_training_buff:{entry['target_stat']}"
    if entry["effect_type"] == "Race Bonus":
        return "race_bonus:any"
    if entry["effect_type"] == "Fan Gain":
        return "fan_gain:any"
    if entry["effect_type"] == "Positive Condition" and entry["target_condition"]:
        return f"positive_condition:{entry['target_condition']}"
    return ""


def load_item_catalog():
    global _CATALOG_CACHE, _CATALOG_BY_ID, _CATALOG_BY_NAME
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    path = os.path.join(_project_root(), "assets", "trackblazer", "items", "items_list.json")
    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    catalog = []
    by_id = {}
    by_name = {}
    for raw in raw_items:
        entry = {
            "item_id": int(raw["id"]),
            "name": raw.get("name", ""),
            "group": raw.get("Group", ""),
            "effect_type": raw.get("Effect Type", ""),
            "target_stat": _normalize_stat_key(raw.get("Stat Type", "")),
            "target_condition": _normalize_condition_name(raw.get("Value", "")) if "Condition" in raw.get("Effect Type", "") else "",
            "value": raw.get("Value", 0),
            "base_price": raw.get("price", 0),
            "effect_text": raw.get("effect", ""),
        }
        entry["duration_turns"] = _derive_duration_turns(entry)
        entry["effect_conflict_key"] = _build_conflict_key(entry)
        entry["usage_family"] = entry["effect_type"]
        catalog.append(entry)
        by_id[entry["item_id"]] = entry
        by_name[_normalize_text(entry["name"])] = entry

    _CATALOG_CACHE = catalog
    _CATALOG_BY_ID = by_id
    _CATALOG_BY_NAME = by_name
    return _CATALOG_CACHE


def get_item_by_id(item_id):
    load_item_catalog()
    return _CATALOG_BY_ID.get(int(item_id))


def get_item_by_name(item_name):
    load_item_catalog()
    return _CATALOG_BY_NAME.get(_normalize_text(item_name))


def load_item_template(template_path):
    if not template_path:
        return {"items_priority": []}

    abs_path = template_path
    if not os.path.isabs(abs_path):
        abs_path = os.path.join(_project_root(), template_path)

    if not os.path.exists(abs_path):
        return {"items_priority": []}

    with open(abs_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"items_priority": list(data.get("items_priority", []))}


def load_item_settings(config):
    raw_items_config = config.get("items", {})
    items_config = dict(DEFAULT_ITEM_SETTINGS)
    items_config.update(raw_items_config)

    selected_conditions = items_config.get("auto_buy_negative_cure_conditions")
    if not isinstance(selected_conditions, list) or not selected_conditions:
        items_config["auto_buy_negative_cure_conditions"] = list(NEGATIVE_CONDITIONS)

    stats = items_config.get("training_level_stats", [])
    if not isinstance(stats, list):
        items_config["training_level_stats"] = []

    periods = items_config.get("training_buff_periods")
    if isinstance(periods, str):
        periods = [periods]
    elif not isinstance(periods, list) or not periods:
        legacy_period = items_config.get("training_buff_period", "any_time")
        periods = [legacy_period] if legacy_period else ["any_time"]
    normalized_periods = [str(period) for period in periods if period]
    items_config["training_buff_periods"] = normalized_periods or ["any_time"]

    default_rainbow_threshold = max(0, int(float(items_config.get("training_buff_score_threshold", 2.0))))
    raw_rainbow_thresholds = items_config.get("training_buff_rainbow_thresholds", {})
    normalized_rainbow_thresholds = {}
    for period_key in ("normal", "summer"):
        period_thresholds = raw_rainbow_thresholds.get(period_key, {}) if isinstance(raw_rainbow_thresholds, dict) else {}
        normalized_rainbow_thresholds[period_key] = {}
        for stat_key in ("spd", "sta", "pwr", "guts", "wit"):
            normalized_rainbow_thresholds[period_key][stat_key] = max(
                0,
                int(period_thresholds.get(stat_key, default_rainbow_threshold)),
            )
    items_config["training_buff_rainbow_thresholds"] = normalized_rainbow_thresholds
    items_config["training_buff_period_rainbow_override_threshold"] = max(
        0,
        int(items_config.get("training_buff_period_rainbow_override_threshold", 2)),
    )
    items_config["training_buff_highest_rainbow_override_threshold"] = max(
        0,
        int(items_config.get("training_buff_highest_rainbow_override_threshold", 3)),
    )

    reserve_count = raw_items_config.get("ts_climax_hammer_reserve_count")
    if reserve_count is None:
        reserve_count = 3 if bool(items_config.get("reserve_ts_climax_hammers", True)) else 0
    items_config["ts_climax_hammer_reserve_count"] = max(0, int(reserve_count))
    items_config["reserve_ts_climax_hammers"] = items_config["ts_climax_hammer_reserve_count"] > 0

    return items_config


def _get_ts_climax_hammer_reserve_count(settings):
    return max(0, int(settings.get("ts_climax_hammer_reserve_count", 3)))


def _build_inventory_by_name(inventory_items):
    inventory_by_name = {}
    for item in inventory_items or []:
        item_name = str(item.get("item_name", "")).strip()
        if not item_name:
            continue
        normalized_name = _normalize_text(item_name)
        current = inventory_by_name.setdefault(normalized_name, {"item_name": item_name, "count": 0})
        current["count"] += int(item.get("count", 0))
        current["base_price"] = item.get("base_price", current.get("base_price", 0))
    return inventory_by_name


def _canonicalize_api_item(item):
    canonical = dict(item)
    catalog_item = get_item_by_name(item.get("item_name", ""))
    if not catalog_item and not item.get("item_name"):
        catalog_item = get_item_by_id(item.get("item_id", 0))
    if catalog_item:
        canonical["item_id"] = int(catalog_item["item_id"])
        canonical["item_name"] = catalog_item["name"]
        canonical["base_price"] = int(catalog_item.get("base_price", item.get("base_price", 0)))
    return canonical


def _extract_training_levels(training_results):
    levels = {}
    if not training_results:
        return levels
    for stat_key, result in training_results.items():
        level = result.get("level")
        if isinstance(level, int):
            levels[stat_key] = level
    return levels


def _count_low_bond_supports(training_results, threshold=4):
    count = 0
    if not training_results:
        return count
    for result in training_results.values():
        for entries in result.get("support_detail", {}).values():
            for entry in entries:
                if int(entry.get("bond_level", 0)) < threshold:
                    count += 1
    return count


def normalize_active_item_effects(active_effects):
    normalized = set()
    for effect in active_effects or []:
        item_id = None
        if isinstance(effect, dict):
            item_id = effect.get("item_id")
        if item_id:
            catalog_item = get_item_by_id(item_id)
            if catalog_item and catalog_item["effect_conflict_key"]:
                normalized.add(catalog_item["effect_conflict_key"])
                continue

        text = _normalize_text(effect if isinstance(effect, str) else json.dumps(effect, ensure_ascii=False))
        if "megaphone" in text or "training buff" in text:
            normalized.add("training_buff:any")
        for stat_key, stat_label in (("spd", "speed"), ("sta", "stamina"), ("pwr", "power"), ("guts", "guts"), ("wit", "wit")):
            if stat_label in text and ("ankle" in text or "specialized" in text):
                normalized.add(f"specialized_training_buff:{stat_key}")
        if "glow stick" in text or "fan gain" in text:
            normalized.add("fan_gain:any")
        if "cleat hammer" in text or "race bonus" in text:
            normalized.add("race_bonus:any")
    return normalized


def normalize_item_state(status_data, training_results=None):
    training_results = training_results or {}
    stats = dict(status_data.get("stats", {}))
    energy = dict(status_data.get("energy", {}))
    mood = dict(status_data.get("mood", {}))
    conditions = status_data.get("conditions", [])
    normalized_conditions = {_normalize_condition_name(value) for value in conditions}
    inventory_items = [_canonicalize_api_item(item) for item in status_data.get("inventory_items", [])]
    shop_items = [_canonicalize_api_item(item) for item in status_data.get("shop_items", [])]

    energy_current = int(energy.get("current", 0))
    energy_max = int(energy.get("max", 0))
    mood_name = str(mood.get("name", "UNKNOWN")).upper()
    mood_value = mood.get("value")
    if not isinstance(mood_value, int):
        mood_value = MOOD_LIST.index(mood_name) if mood_name in MOOD_LIST else 0

    year = status_data.get("year", "Unknown Year")
    if "Year 4" in year:
        year = "TS Climax"

    return {
        "year": year,
        "stats": {
            "spd": int(stats.get("spd", 0)),
            "sta": int(stats.get("sta", 0)),
            "pwr": int(stats.get("pwr", 0)),
            "guts": int(stats.get("guts", 0)),
            "wit": int(stats.get("wit", 0)),
        },
        "energy_current": energy_current,
        "energy_max": energy_max,
        "mood_name": mood_name,
        "mood_value": mood_value,
        "conditions": list(normalized_conditions),
        "condition_lookup": normalized_conditions,
        "shop_coin": int(status_data.get("shop_coin", 0)),
        "shop_items": shop_items,
        "inventory_items": inventory_items,
        "inventory_by_name": _build_inventory_by_name(inventory_items),
        "active_effect_keys": normalize_active_item_effects(status_data.get("active_item_effects", [])),
        "training_results": training_results,
        "training_levels": _extract_training_levels(training_results),
        "low_bond_support_count": _count_low_bond_supports(training_results),
    }


def get_minimum_mood_value(training_config):
    mood_name = str(training_config.get("minimum_mood", "GREAT")).upper()
    if mood_name in MOOD_LIST:
        return MOOD_LIST.index(mood_name)
    return MOOD_LIST.index("GREAT")


def get_mood_item_target_value(config, settings):
    minimum_mood_value = get_minimum_mood_value(config.get("training", {}))
    if settings.get("use_mood_items_to_reach_great"):
        return max(minimum_mood_value, MOOD_LIST.index("GREAT"))
    return minimum_mood_value


def _is_single_buff_period_allowed(setting, year):
    if setting == "any_time":
        return True
    normalized_year = str(year or "")
    if setting == "classic_senior_summer":
        return ("Classic" in normalized_year or "Senior" in normalized_year) and ("Jul" in normalized_year or "Aug" in normalized_year)
    if setting == "senior_year":
        return "Senior" in normalized_year or "TS Climax" in normalized_year
    if setting == "ts_climax":
        return "TS Climax" in normalized_year
    return True


def _is_buff_period_allowed(settings, year):
    periods = settings if isinstance(settings, list) else [settings]
    if "any_time" in periods:
        return True
    return any(_is_single_buff_period_allowed(setting, year) for setting in periods)


def _is_summer_period(year):
    return _is_single_buff_period_allowed("classic_senior_summer", year)


def _count_rainbow_supports(training_type, training_result):
    if not training_type or not training_result:
        return 0

    count = 0
    for entry in training_result.get("support_detail", {}).get(training_type, []):
        if int(entry.get("bond_level", 0)) >= 4:
            count += 1
    return count


def _get_training_buff_rainbow_threshold(settings, training_type, year):
    if (
        bool(settings.get("training_buff_late_senior_rainbow_requirement_one", False))
        and _is_after_senior_summer_or_ts_climax(year)
    ):
        return 1

    period_key = "summer" if _is_summer_period(year) else "normal"
    thresholds = settings.get("training_buff_rainbow_thresholds", {})
    period_thresholds = thresholds.get(period_key, {}) if isinstance(thresholds, dict) else {}
    return int(period_thresholds.get(training_type, 2))


def _is_training_buff_allowed(settings, training_type, training_result, year):
    rainbow_count = _count_rainbow_supports(training_type, training_result)
    threshold = _get_training_buff_rainbow_threshold(settings, training_type, year)
    rainbow_allowed = rainbow_count >= threshold
    period_allowed = _is_buff_period_allowed(settings.get("training_buff_periods", ["any_time"]), year)
    if period_allowed:
        return rainbow_allowed, rainbow_count

    override_enabled = bool(settings.get("training_buff_period_rainbow_override_enabled", False))
    override_threshold = int(settings.get("training_buff_period_rainbow_override_threshold", 2))
    return override_enabled and rainbow_count >= override_threshold, rainbow_count


def _is_after_senior_summer_or_ts_climax(year):
    normalized_year = str(year or "")
    if "TS Climax" in normalized_year:
        return True
    if "Senior" not in normalized_year:
        return False

    month_order = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    for month_name, month_index in month_order.items():
        if month_name in normalized_year:
            return month_index > month_order["Aug"]
    return False


def _should_hold_energy_recovery_for_summer(settings, year):
    if not bool(settings.get("save_energy_recovery_for_summer", False)):
        return False
    if _is_summer_period(year):
        return False
    if _is_after_senior_summer_or_ts_climax(year):
        return False
    return True


def _expand_inventory_items(inventory_by_name, effect_type=None):
    expanded = []
    for item_name, item_data in inventory_by_name.items():
        catalog_item = get_item_by_name(item_name)
        if not catalog_item:
            continue
        if effect_type and catalog_item["effect_type"] != effect_type:
            continue
        for _ in range(int(item_data.get("count", 0))):
            expanded.append(catalog_item)
    return expanded


def _find_best_energy_combo(inventory_by_name, missing_energy):
    if missing_energy <= 0:
        return {}

    candidates = _expand_inventory_items(inventory_by_name, "Energy Recovery")
    best = None
    for r in range(1, len(candidates) + 1):
        for combo in itertools.combinations(range(len(candidates)), r):
            total = sum(int(candidates[idx]["value"]) for idx in combo)
            if total > missing_energy:
                continue
            score = (missing_energy - total, r, -total)
            if best is None or score < best[0]:
                counts = {}
                for idx in combo:
                    item_name = candidates[idx]["name"]
                    counts[item_name] = counts.get(item_name, 0) + 1
                best = (score, counts)
    return best[1] if best else {}


def _find_best_mood_combo_from_items(items, required_gain):
    if required_gain <= 0:
        return {}

    expanded = []
    for item in items:
        for _ in range(int(item.get("count", 1))):
            expanded.append(item)

    best = None
    for r in range(1, len(expanded) + 1):
        for combo in itertools.combinations(range(len(expanded)), r):
            total_gain = sum(int(expanded[idx]["value"]) for idx in combo)
            if total_gain < required_gain:
                continue
            total_cost = sum(int(expanded[idx].get("price", expanded[idx].get("base_price", 0))) for idx in combo)
            score = (total_gain - required_gain, total_cost, r)
            if best is None or score < best[0]:
                counts = {}
                for idx in combo:
                    item_name = expanded[idx]["item_name"]
                    counts[item_name] = counts.get(item_name, 0) + 1
                best = (score, counts)
    return best[1] if best else {}


def _priority_limits(template_data):
    limits = {}
    for entry in template_data.get("items_priority", []):
        item_id = int(entry.get("id", 0))
        if item_id <= 0:
            continue
        limits[item_id] = max(1, int(entry.get("item_limit", 1)))
    return limits


def _effective_item_limit(item_id, template_limits, desired_quantity, state):
    catalog_item = get_item_by_id(item_id)
    if catalog_item and catalog_item.get("group") == "Race" and state.get("year") == "TS Climax":
        return 1
    if item_id in template_limits:
        return template_limits[item_id]
    return max(1, int(desired_quantity))


def _available_shop_entries(shop_items, item_name):
    entries = []
    for entry in shop_items:
        if _normalize_text(entry.get("item_name", "")) != _normalize_text(item_name):
            continue
        if entry.get("sold_out"):
            continue
        if int(entry.get("item_buy_num", 0)) >= int(entry.get("limit_buy_count", 1)):
            continue
        entries.append(entry)
    return sorted(entries, key=lambda item: (int(item.get("price", 0)), int(item.get("shop_item_id", 0))))


def _can_buy_more(item_id, template_limits, inventory_count, planned_count, desired_quantity, state):
    limit = _effective_item_limit(item_id, template_limits, desired_quantity, state)
    return inventory_count + planned_count < limit


def _item_targets_capped_stat(catalog_item, state, config):
    target_stat = catalog_item.get("target_stat")
    if not target_stat:
        return False

    if catalog_item.get("group") != "Stat" and catalog_item.get("effect_type") != "Specialized Training Buff":
        return False

    training_config = config.get("training", {})
    stat_caps = training_config.get("stat_caps", {})
    hard_cap = int(stat_caps.get(target_stat, 1200))
    return int(state["stats"].get(target_stat, 0)) >= hard_cap


def _item_grants_existing_positive_condition(catalog_item, state):
    if catalog_item.get("effect_type") != "Positive Condition":
        return False

    target_condition = catalog_item.get("target_condition")
    if not target_condition:
        return False

    return target_condition in state.get("condition_lookup", set())


def _is_item_usage_blocked_by_hard_cap(catalog_item, state, config):
    target_stat = catalog_item.get("target_stat")
    if not target_stat:
        return False

    if catalog_item.get("group") != "Stat":
        return False

    training_config = config.get("training", {})
    stat_caps = training_config.get("stat_caps", {})
    hard_cap = int(stat_caps.get(target_stat, 1200))
    return int(state["stats"].get(target_stat, 0)) >= hard_cap


def _build_auto_buy_candidates(state, settings, template_limits, config):
    del template_limits
    candidates = []
    inventory_by_name = state["inventory_by_name"]
    condition_lookup = state["condition_lookup"]

    mood_gap = max(0, get_mood_item_target_value(config, settings) - state["mood_value"])
    if (settings.get("auto_buy_mood_items") or settings.get("use_mood_items_to_reach_great")) and mood_gap > 0:
        current_mood_items = []
        for item_name, item_data in inventory_by_name.items():
            catalog_item = get_item_by_name(item_name)
            if catalog_item and catalog_item["effect_type"] == "Mood":
                current_mood_items.append({
                    "item_name": catalog_item["name"],
                    "value": int(catalog_item["value"]),
                    "count": item_data["count"],
                    "base_price": catalog_item["base_price"],
                })
        current_gain = sum(int(item["value"]) * int(item["count"]) for item in current_mood_items)
        needed_gain = max(0, mood_gap - current_gain)
        if needed_gain > 0:
            shop_mood_items = []
            for shop_item in state["shop_items"]:
                catalog_item = get_item_by_name(shop_item.get("item_name", ""))
                if not catalog_item or catalog_item["effect_type"] != "Mood" or shop_item.get("sold_out"):
                    continue
                shop_mood_items.append({
                    "item_name": catalog_item["name"],
                    "shop_item_id": int(shop_item.get("shop_item_id", 0)),
                    "value": int(catalog_item["value"]),
                    "price": int(shop_item.get("price", 0)),
                    "count": 1,
                })
            combo = _find_best_mood_combo_from_items(shop_mood_items, needed_gain)
            for item_name, quantity in combo.items():
                candidates.append({"item_name": item_name, "desired_quantity": quantity, "reason": "auto_buy_mood"})

    if settings.get("auto_buy_negative_cure_items"):
        enabled_conditions = {_normalize_condition_name(name) for name in settings.get("auto_buy_negative_cure_conditions", [])}
        active_negative_conditions = _negative_condition_set(condition_lookup)
        owned_cures = set()
        for item_name in inventory_by_name:
            catalog_item = get_item_by_name(item_name)
            if catalog_item and catalog_item["effect_type"] == "Negative Condition Cure":
                owned_cures.add(catalog_item["target_condition"])
        planned_conditions = set()
        for condition_name in active_negative_conditions:
            if len(active_negative_conditions) != 1:
                continue
            if condition_name not in enabled_conditions:
                continue
            if condition_name not in condition_lookup or condition_name in owned_cures or condition_name in planned_conditions:
                continue
            for shop_item in state["shop_items"]:
                catalog_item = get_item_by_name(shop_item.get("item_name", ""))
                if not catalog_item or catalog_item["effect_type"] != "Negative Condition Cure":
                    continue
                if catalog_item["name"] == "Miracle Cure" or catalog_item["target_condition"] != condition_name:
                    continue
                candidates.append({"item_name": catalog_item["name"], "desired_quantity": 1, "reason": f"auto_buy_cure:{condition_name}"})
                planned_conditions.add(condition_name)
                break

    if settings.get("enable_training_level_items"):
        priority_order = {stat: idx for idx, stat in enumerate(config.get("training", {}).get("priority_stat", []))}
        threshold = int(settings.get("training_level_threshold", 3))
        selected_stats = sorted(settings.get("training_level_stats", []), key=lambda stat: priority_order.get(stat, 999))
        for stat_key in selected_stats:
            current_level = int(state["training_levels"].get(stat_key, 5))
            if current_level >= threshold:
                continue
            for item in load_item_catalog():
                if item["effect_type"] == "Training Level" and item["target_stat"] == stat_key:
                    candidates.append({"item_name": item["name"], "desired_quantity": 1, "reason": f"auto_buy_training_level:{stat_key}"})
                    break

    reserve_count = _get_ts_climax_hammer_reserve_count(settings)

    if state.get("year") == "TS Climax":
        artisan_count = int(inventory_by_name.get(_normalize_text("Artisan Cleat Hammer"), {}).get("count", 0))
        master_count = int(inventory_by_name.get(_normalize_text("Master Cleat Hammer"), {}).get("count", 0))
        glowstick_count = int(inventory_by_name.get(_normalize_text(GLOWSTICK_ITEM_NAME), {}).get("count", 0))

        master_entries = _available_shop_entries(state["shop_items"], "Master Cleat Hammer")
        artisan_entries = _available_shop_entries(state["shop_items"], "Artisan Cleat Hammer")
        glowstick_entries = _available_shop_entries(state["shop_items"], GLOWSTICK_ITEM_NAME)

        # During TS Climax, keep at least one hammer available for races and
        # upgrade an Artisan-only inventory to Master when the shop offers it.
        if master_count <= 0:
            if master_entries:
                candidates.append({
                    "item_name": "Master Cleat Hammer",
                    "desired_quantity": 1,
                    "reason": "auto_buy_ts_climax_master_active",
                })
            elif artisan_count <= 0 and artisan_entries:
                candidates.append({
                    "item_name": "Artisan Cleat Hammer",
                    "desired_quantity": 1,
                    "reason": "auto_buy_ts_climax_hammer_active",
                })
        if bool(settings.get("use_glowstick_ts_climax", False)) and glowstick_count <= 0 and glowstick_entries:
            candidates.append({
                "item_name": GLOWSTICK_ITEM_NAME,
                "desired_quantity": 1,
                "reason": "auto_buy_ts_climax_glowstick_active",
            })
    elif reserve_count > 0:
        artisan_count = int(inventory_by_name.get(_normalize_text("Artisan Cleat Hammer"), {}).get("count", 0))
        master_count = int(inventory_by_name.get(_normalize_text("Master Cleat Hammer"), {}).get("count", 0))
        total_hammer_count = artisan_count + master_count

        master_entries = _available_shop_entries(state["shop_items"], "Master Cleat Hammer")
        artisan_entries = _available_shop_entries(state["shop_items"], "Artisan Cleat Hammer")

        if total_hammer_count < reserve_count:
            missing_hammer_count = reserve_count - total_hammer_count
            master_purchase_count = min(missing_hammer_count, len(master_entries))
            artisan_purchase_count = missing_hammer_count - master_purchase_count

            # Before TS Climax, fill the configured reserve count. Masters take
            # the first slots, then Artisans cover any remaining missing reserve.
            if master_purchase_count > 0:
                candidates.append({
                    "item_name": "Master Cleat Hammer",
                    "desired_quantity": master_count + master_purchase_count,
                    "reason": "auto_buy_ts_climax_master_reserve",
                })
            if artisan_purchase_count > 0 and artisan_entries:
                candidates.append({
                    "item_name": "Artisan Cleat Hammer",
                    "desired_quantity": artisan_count + artisan_purchase_count,
                    "reason": "auto_buy_ts_climax_hammer_reserve",
                })
        elif artisan_count > 0 and master_entries:
            # If the reserve is already full but contains Artisan hammers, buy a
            # Master as an upgrade. The displaced Artisan becomes excess and can
            # be spent before TS Climax.
            candidates.append({
                "item_name": "Master Cleat Hammer",
                "desired_quantity": master_count + 1,
                "reason": "auto_buy_ts_climax_master_reserve",
            })

    return candidates


def _sort_auto_buy_candidates(candidates):
    priority_order = {
        "auto_buy_ts_climax_master_active": 0,
        "auto_buy_ts_climax_hammer_active": 1,
        "auto_buy_ts_climax_master_reserve": 2,
        "auto_buy_ts_climax_hammer_reserve": 3,
        "auto_buy_ts_climax_glowstick_active": 4,
    }
    return sorted(
        enumerate(candidates),
        key=lambda entry: (priority_order.get(entry[1].get("reason", ""), 100), entry[0]),
    )


def plan_item_purchases(state, template_data, config):
    settings = load_item_settings(config)
    template_limits = _priority_limits(template_data)
    planned_counts = {}
    planned_shop_entries = set()
    purchase_actions = []
    remaining_coin = int(state["shop_coin"])

    auto_candidates = [
        candidate
        for _, candidate in _sort_auto_buy_candidates(
            _build_auto_buy_candidates(state, settings, template_limits, config)
        )
    ]
    candidate_specs = list(auto_candidates)

    for entry in template_data.get("items_priority", []):
        catalog_item = get_item_by_id(int(entry.get("id", 0)))
        if not catalog_item:
            continue
        candidate_specs.append({"item_name": catalog_item["name"], "desired_quantity": max(1, int(entry.get("item_limit", 1))), "reason": "priority"})

    stop_after_unaffordable = settings.get("budget_strategy", "save_priority") == "save_priority"

    for spec in candidate_specs:
        item_name = spec["item_name"]
        catalog_item = get_item_by_name(item_name)
        if not catalog_item:
            continue

        if _item_targets_capped_stat(catalog_item, state, config):
            continue

        if _item_grants_existing_positive_condition(catalog_item, state):
            continue

        inventory_count = int(state["inventory_by_name"].get(_normalize_text(item_name), {}).get("count", 0))
        planned_count = int(planned_counts.get(_normalize_text(item_name), 0))
        desired_quantity = max(1, int(spec["desired_quantity"]))
        if not _can_buy_more(catalog_item["item_id"], template_limits, inventory_count, planned_count, desired_quantity, state):
            continue

        affordable_for_candidate = False
        available_shop_entries = []
        for shop_entry in _available_shop_entries(state["shop_items"], item_name):
            shop_item_id = int(shop_entry.get("shop_item_id", 0))
            shop_entry_key = ("shop_item_id", shop_item_id) if shop_item_id else ("entry", id(shop_entry))
            if shop_entry_key not in planned_shop_entries:
                available_shop_entries.append(shop_entry)
        saw_shop_entry = bool(available_shop_entries)
        for shop_entry in available_shop_entries:
            shop_item_id = int(shop_entry.get("shop_item_id", 0))
            shop_entry_key = ("shop_item_id", shop_item_id) if shop_item_id else ("entry", id(shop_entry))
            if not _can_buy_more(catalog_item["item_id"], template_limits, inventory_count, planned_counts.get(_normalize_text(item_name), 0), desired_quantity, state):
                break
            price = int(shop_entry.get("price", 0))
            if price > remaining_coin:
                continue

            purchase_actions.append({
                "shop_item_id": shop_item_id,
                "item_name": catalog_item["name"],
                "price": price,
                "reason": spec["reason"],
            })
            remaining_coin -= price
            planned_counts[_normalize_text(item_name)] = planned_counts.get(_normalize_text(item_name), 0) + 1
            planned_shop_entries.add(shop_entry_key)
            affordable_for_candidate = True

        if stop_after_unaffordable and spec["reason"] == "priority" and saw_shop_entry and not affordable_for_candidate:
            return purchase_actions

    return purchase_actions


def plan_training_level_purchases(state, config):
    settings = load_item_settings(config)
    if not settings.get("enable_training_level_items"):
        return []

    remaining_coin = int(state["shop_coin"])
    purchase_actions = []
    stop_after_unaffordable = settings.get("budget_strategy", "save_priority") == "save_priority"
    priority_order = {stat: idx for idx, stat in enumerate(config.get("training", {}).get("priority_stat", []))}
    threshold = int(settings.get("training_level_threshold", 3))
    selected_stats = sorted(settings.get("training_level_stats", []), key=lambda stat: priority_order.get(stat, 999))

    for stat_key in selected_stats:
        current_level = int(state["training_levels"].get(stat_key, 5))
        if current_level >= threshold:
            continue

        target_item = None
        for item in load_item_catalog():
            if item["effect_type"] == "Training Level" and item["target_stat"] == stat_key:
                target_item = item
                break
        if not target_item:
            continue

        item_name = target_item["name"]
        if int(state["inventory_by_name"].get(_normalize_text(item_name), {}).get("count", 0)) > 0:
            continue

        shop_entries = _available_shop_entries(state["shop_items"], item_name)
        if not shop_entries:
            continue

        price = int(shop_entries[0].get("price", 0))
        if price > remaining_coin:
            if stop_after_unaffordable:
                break
            continue

        purchase_actions.append({
            "shop_item_id": int(shop_entries[0].get("shop_item_id", 0)),
            "item_name": target_item["name"],
            "price": price,
            "reason": f"auto_buy_training_level:{stat_key}",
        })
        remaining_coin -= price

    return purchase_actions


def plan_friendship_purchases(state, config):
    settings = load_item_settings(config)
    if not settings.get("auto_buy_friendship_items"):
        return []

    threshold = int(settings.get("friendship_support_threshold", 1))
    if int(state.get("low_bond_support_count", 0)) < threshold:
        return []

    item_name = "Grilled Carrots"
    if int(state["inventory_by_name"].get(_normalize_text(item_name), {}).get("count", 0)) > 0:
        return []

    shop_entries = _available_shop_entries(state["shop_items"], item_name)
    if not shop_entries:
        return []

    price = int(shop_entries[0].get("price", 0))
    if price > int(state["shop_coin"]):
        return []

    return [{
        "shop_item_id": int(shop_entries[0].get("shop_item_id", 0)),
        "item_name": item_name,
        "price": price,
        "reason": "auto_buy_friendship",
    }]


def plan_turn_item_purchases(state, template_data, config):
    """Build one budget-aware purchase plan using the turn's training data."""
    purchase_actions = plan_friendship_purchases(state, config)
    planned_state = apply_purchase_plan(state, purchase_actions)
    purchase_actions.extend(plan_item_purchases(planned_state, template_data, config))
    return purchase_actions


def apply_purchase_plan(state, purchase_actions):
    updated = deepcopy(state)
    for action in purchase_actions:
        updated["shop_coin"] = max(0, int(updated["shop_coin"]) - int(action["price"]))
        normalized_name = _normalize_text(action["item_name"])
        inventory_item = updated["inventory_by_name"].setdefault(normalized_name, {"item_name": action["item_name"], "count": 0})
        inventory_item["count"] += 1
        shop_item_id = int(action.get("shop_item_id", 0))
        if shop_item_id:
            for shop_item in updated.get("shop_items", []):
                if int(shop_item.get("shop_item_id", 0)) == shop_item_id:
                    shop_item["sold_out"] = True
                    break
    return updated


def _append_usage(actions, item_name, quantity, reason):
    if quantity <= 0:
        return
    actions.append({
        "item_name": item_name,
        "quantity": int(quantity),
        "reason": reason,
    })


def _negative_condition_set(condition_lookup):
    negative_conditions = {_normalize_condition_name(value) for value in NEGATIVE_CONDITIONS}
    return {
        condition_name for condition_name in condition_lookup
        if condition_name in negative_conditions
    }


def _plan_negative_condition_cures(actions, inventory_by_name, remaining_negative_conditions):
    miracle_cure_available = False
    specific_cure_actions = []
    for item_name, inventory_item in sorted(inventory_by_name.items()):
        if int(inventory_item.get("count", 0)) <= 0:
            continue
        catalog_item = get_item_by_name(item_name)
        if not catalog_item or catalog_item["effect_type"] != "Negative Condition Cure":
            continue
        if catalog_item["name"] == "Miracle Cure":
            miracle_cure_available = True
            continue
        if catalog_item["target_condition"] in remaining_negative_conditions:
            specific_cure_actions.append(catalog_item)

    if miracle_cure_available and len(remaining_negative_conditions) > 1:
        _append_usage(actions, "Miracle Cure", 1, "use_negative_condition_cure")
        remaining_negative_conditions.clear()
        return

    for catalog_item in specific_cure_actions:
        if catalog_item["target_condition"] in remaining_negative_conditions:
            _append_usage(actions, catalog_item["name"], 1, "use_negative_condition_cure")
            remaining_negative_conditions.discard(catalog_item["target_condition"])

    if miracle_cure_available and remaining_negative_conditions:
        _append_usage(actions, "Miracle Cure", 1, "use_negative_condition_cure")
        remaining_negative_conditions.clear()


def plan_immediate_item_usage(state, config, is_race_turn=False):
    settings = load_item_settings(config)
    actions = []
    mood_item_target_value = get_mood_item_target_value(config, settings)
    inventory_by_name = state["inventory_by_name"]
    condition_lookup = state["condition_lookup"]
    remaining_negative_conditions = _negative_condition_set(condition_lookup)

    for item_name, inventory_item in sorted(inventory_by_name.items()):
        catalog_item = get_item_by_name(item_name)
        if catalog_item and catalog_item["group"] == "Stat":
            if _is_item_usage_blocked_by_hard_cap(catalog_item, state, config):
                continue
            _append_usage(actions, catalog_item["name"], inventory_item["count"], "use_all_stat_items")

    for item_name, inventory_item in sorted(inventory_by_name.items()):
        catalog_item = get_item_by_name(item_name)
        if catalog_item and catalog_item["effect_type"] == "Energy Cap":
            _append_usage(actions, catalog_item["name"], inventory_item["count"], "use_energy_cap")

    if not is_race_turn and not _should_hold_energy_recovery_for_summer(settings, state.get("year")):
        missing_energy = max(0, int(state["energy_max"]) - int(state["energy_current"]))
        for item_name, quantity in _find_best_energy_combo(inventory_by_name, missing_energy).items():
            _append_usage(actions, item_name, quantity, "use_energy_recovery")

    mood_gap = max(0, mood_item_target_value - int(state["mood_value"]))
    if mood_gap > 0:
        mood_inventory = []
        for item_name, inventory_item in inventory_by_name.items():
            catalog_item = get_item_by_name(item_name)
            if not catalog_item or catalog_item["effect_type"] != "Mood":
                continue
            mood_inventory.append({
                "item_name": catalog_item["name"],
                "value": int(catalog_item["value"]),
                "count": int(inventory_item["count"]),
                "base_price": int(catalog_item["base_price"]),
            })
        for item_name, quantity in _find_best_mood_combo_from_items(mood_inventory, mood_gap).items():
            _append_usage(actions, item_name, quantity, "use_mood_items")

    _plan_negative_condition_cures(actions, inventory_by_name, remaining_negative_conditions)

    for item_name, inventory_item in sorted(inventory_by_name.items()):
        catalog_item = get_item_by_name(item_name)
        if not catalog_item:
            continue
        if catalog_item["effect_type"] == "Positive Condition" and catalog_item["target_condition"] not in condition_lookup:
            _append_usage(actions, catalog_item["name"], 1, "use_positive_condition_item")
        if catalog_item["name"] == "Grilled Carrots":
            _append_usage(actions, catalog_item["name"], inventory_item["count"], "use_grilled_carrots")

    return actions


def _select_training_buff(inventory_by_name, active_effect_keys, prefer_highest=False):
    if "training_buff:any" in active_effect_keys:
        return None
    selected_item = None
    for item_name, inventory_item in inventory_by_name.items():
        if int(inventory_item.get("count", 0)) <= 0:
            continue
        catalog_item = get_item_by_name(item_name)
        if not catalog_item or catalog_item["effect_type"] != "Training Buff":
            continue
        if selected_item is None:
            selected_item = catalog_item
            continue
        if prefer_highest and int(catalog_item["value"]) > int(selected_item["value"]):
            selected_item = catalog_item
        if not prefer_highest and int(catalog_item["value"]) < int(selected_item["value"]):
            selected_item = catalog_item
    return selected_item


def _select_specialized_buff(inventory_by_name, training_type, active_effect_keys):
    conflict_key = f"specialized_training_buff:{training_type}"
    if conflict_key in active_effect_keys:
        return None

    best_item = None
    for item_name, inventory_item in inventory_by_name.items():
        if int(inventory_item.get("count", 0)) <= 0:
            continue
        catalog_item = get_item_by_name(item_name)
        if not catalog_item or catalog_item["effect_type"] != "Specialized Training Buff":
            continue
        if catalog_item["target_stat"] != training_type:
            continue
        if best_item is None or int(catalog_item["value"]) > int(best_item["value"]):
            best_item = catalog_item
    return best_item


def training_item_use_requires_refresh(actions):
    refresh_reasons = {
        "use_training_buff",
        "use_specialized_training_buff",
        "use_good_luck_charm",
        "use_training_shuffle",
    }
    return any(action["reason"] in refresh_reasons for action in actions)


def plan_training_item_usage(state, config, chosen_training, chosen_training_result, would_be_rejected):
    settings = load_item_settings(config)
    actions = []
    inventory_by_name = state["inventory_by_name"]
    has_training_choice = bool(chosen_training and chosen_training_result)
    chosen_score = float(chosen_training_result.get("score", 0)) if chosen_training_result else 0.0
    training_is_accepted = has_training_choice and not would_be_rejected
    buff_allowed, rainbow_count = _is_training_buff_allowed(
        settings,
        chosen_training,
        chosen_training_result,
        state["year"],
    ) if has_training_choice else (False, 0)

    training_buff_item = None
    if training_is_accepted and buff_allowed:
        prefer_highest = _is_summer_period(state["year"]) or _is_after_senior_summer_or_ts_climax(state["year"])
        if bool(settings.get("training_buff_highest_rainbow_override_enabled", False)):
            highest_threshold = int(settings.get("training_buff_highest_rainbow_override_threshold", 3))
            prefer_highest = prefer_highest or rainbow_count >= highest_threshold
        training_buff_item = _select_training_buff(
            inventory_by_name,
            state["active_effect_keys"],
            prefer_highest=prefer_highest,
        )
        if training_buff_item:
            _append_usage(actions, training_buff_item["name"], 1, "use_training_buff")

    if training_is_accepted and buff_allowed:
        specialized_item = _select_specialized_buff(
            inventory_by_name,
            chosen_training,
            state["active_effect_keys"],
        )
        requires_training_buff = bool(settings.get("specialized_buff_requires_training_buff"))
        has_training_buff = training_buff_item is not None or "training_buff:any" in state["active_effect_keys"]
        if specialized_item and (not requires_training_buff or has_training_buff):
            _append_usage(actions, specialized_item["name"], 1, "use_specialized_training_buff")

    if has_training_choice and settings.get("enable_training_level_items"):
        threshold = int(settings.get("training_level_threshold", 3))
        selected_stats = settings.get("training_level_stats", [])
        priority_order = {stat: idx for idx, stat in enumerate(config.get("training", {}).get("priority_stat", []))}
        for stat_key in sorted(selected_stats, key=lambda stat: priority_order.get(stat, 999)):
            if int(state["training_levels"].get(stat_key, 5)) >= threshold:
                continue
            for item in load_item_catalog():
                if item["effect_type"] == "Training Level" and item["target_stat"] == stat_key and int(inventory_by_name.get(_normalize_text(item["name"]), {}).get("count", 0)) > 0:
                    _append_usage(actions, item["name"], 1, "use_training_level_item")
                    break

    highest_score = max(float(result.get("score", 0)) for result in state["training_results"].values()) if state["training_results"] else 0.0
    if highest_score < float(settings.get("training_shuffle_score_threshold", 1.0)):
        restricted = bool(settings.get("training_shuffle_restricted_periods_only"))
        in_restricted_period = _is_single_buff_period_allowed("classic_senior_summer", state["year"]) or _is_single_buff_period_allowed("ts_climax", state["year"])
        if not restricted or in_restricted_period:
            shuffle_count = int(state["inventory_by_name"].get(_normalize_text("Reset Whistle"), {}).get("count", 0))
            if shuffle_count > 0:
                _append_usage(actions, "Reset Whistle", 1, "use_training_shuffle")

    if has_training_choice and settings.get("good_luck_charm_enabled", True):
        charm_count = int(state["inventory_by_name"].get(_normalize_text("Good-luck Charm"), {}).get("count", 0))
        if charm_count > 0 and would_be_rejected:
            require_score = bool(settings.get("good_luck_charm_require_score", True))
            require_buff = bool(settings.get("good_luck_charm_require_buff", False))
            score_ok = chosen_score > float(settings.get("good_luck_charm_score_threshold", 2.0))
            buff_ok = any(action["reason"] in {"use_training_buff", "use_specialized_training_buff"} for action in actions)
            if ((not require_score) or score_ok) and ((not require_buff) or buff_ok):
                _append_usage(actions, "Good-luck Charm", 1, "use_good_luck_charm")

    return actions


def _select_race_bonus_item(inventory_by_name, reserve_count, is_ts_climax_race):
    artisan_count = int(inventory_by_name.get(_normalize_text("Artisan Cleat Hammer"), {}).get("count", 0))
    master_count = int(inventory_by_name.get(_normalize_text("Master Cleat Hammer"), {}).get("count", 0))
    total_hammer_count = artisan_count + master_count
    if total_hammer_count <= 0:
        return None

    if is_ts_climax_race:
        return "Master Cleat Hammer" if master_count > 0 else "Artisan Cleat Hammer"

    if total_hammer_count <= reserve_count:
        return None

    return "Artisan Cleat Hammer" if artisan_count > 0 else "Master Cleat Hammer"


def plan_race_item_usage(
    state,
    config,
    is_custom_race=False,
    custom_race_use_glowstick=False,
    custom_race_use_hammer=False,
    is_ts_climax_race=False,
):
    settings = load_item_settings(config)
    actions = []

    race_bonus_item_id = _select_race_bonus_item(
        state["inventory_by_name"],
        reserve_count=_get_ts_climax_hammer_reserve_count(settings),
        is_ts_climax_race=is_ts_climax_race,
    )
    if race_bonus_item_id:
        reason = "use_custom_race_hammer" if is_custom_race and custom_race_use_hammer else "use_race_bonus"
        _append_usage(actions, race_bonus_item_id, 1, reason)

    use_glowstick = custom_race_use_glowstick or (is_ts_climax_race and bool(settings.get("use_glowstick_ts_climax", False)))
    if use_glowstick and int(state["inventory_by_name"].get(_normalize_text(GLOWSTICK_ITEM_NAME), {}).get("count", 0)) > 0:
        _append_usage(actions, GLOWSTICK_ITEM_NAME, 1, "use_glowstick")

    return actions


def apply_usage_plan(state, usage_actions):
    updated = deepcopy(state)
    for action in usage_actions:
        item_name = action["item_name"]
        quantity = int(action.get("quantity", 1))
        inventory_item = updated["inventory_by_name"].get(_normalize_text(item_name))
        if inventory_item:
            inventory_item["count"] = max(0, int(inventory_item["count"]) - quantity)

        catalog_item = get_item_by_name(item_name)
        if not catalog_item:
            continue

        if catalog_item["group"] == "Stat" and catalog_item["target_stat"]:
            updated["stats"][catalog_item["target_stat"]] = updated["stats"].get(catalog_item["target_stat"], 0) + int(catalog_item["value"]) * quantity
        elif catalog_item["effect_type"] == "Energy Cap":
            updated["energy_max"] += int(catalog_item["value"]) * quantity
            updated["energy_current"] = min(updated["energy_max"], updated["energy_current"] + (5 if catalog_item["name"] == "Bucket of Weights" else 0))
        elif catalog_item["effect_type"] == "Energy Recovery":
            updated["energy_current"] = min(updated["energy_max"], updated["energy_current"] + int(catalog_item["value"]) * quantity)
        elif catalog_item["effect_type"] == "Mood":
            updated["mood_value"] += int(catalog_item["value"]) * quantity
        elif catalog_item["effect_type"] == "Negative Condition Cure":
            updated["condition_lookup"].discard(catalog_item["target_condition"])
        elif catalog_item["effect_type"] == "Positive Condition":
            updated["condition_lookup"].add(catalog_item["target_condition"])
        elif catalog_item["effect_conflict_key"]:
            updated["active_effect_keys"].add(catalog_item["effect_conflict_key"])
    return updated


def format_action_plan(actions):
    if not actions:
        return "none"
    parts = []
    for action in actions:
        parts.append(f"{action['item_name']} x{action.get('quantity', 1)} [{action['reason']}]")
    return "\n".join(f"  - {part}" for part in parts)
