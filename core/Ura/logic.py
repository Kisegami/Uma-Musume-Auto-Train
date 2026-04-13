from core.Ura.state import check_current_year, stat_state
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config

config = load_main_config()

# Training config (supports both nested and legacy keys)
training_config = config.get("training", {})
default_priority = ["spd", "sta", "wit", "pwr", "guts"]
PRIORITY_STAT = training_config.get("priority_stat", config.get("priority_stat", default_priority))
MAX_FAILURE = training_config.get("maximum_failure", config.get("maximum_failure", 15))
STAT_CAPS = training_config.get("stat_caps", config.get("stat_caps", {}))
SOFT_CAP_ENABLED = training_config.get("soft_cap_enabled", config.get("soft_cap_enabled", False))
SOFT_STAT_CAPS = training_config.get("soft_stat_caps", config.get("soft_stat_caps", {}))
DO_RACE_WHEN_BAD_TRAINING = training_config.get("do_race_when_bad_training", config.get("do_race_when_bad_training", True))
MIN_CONFIDENCE = 0.5  # Minimum confidence threshold for training decisions (currently used for retry logic)
TRACKED_STATS = ("spd", "sta", "pwr", "guts", "wit")

# Get priority stat from config
def get_stat_priority(stat_key: str) -> int:
  return PRIORITY_STAT.index(stat_key) if stat_key in PRIORITY_STAT else 999


# Check if all training options have failure rates above maximum
def all_training_unsafe(results, maximum_failure=None):
  if maximum_failure is None:
    maximum_failure = MAX_FAILURE
  for stat, data in results.items():
    if int(data["failure"]) <= maximum_failure:
      return False
  return True

def _get_hard_stat_cap(stat):
  return int(STAT_CAPS.get(stat, 1200))

def _get_soft_stat_cap(stat):
  hard_cap = _get_hard_stat_cap(stat)
  soft_cap = int(SOFT_STAT_CAPS.get(stat, hard_cap))
  return min(soft_cap, hard_cap)

def _are_all_stats_at_caps(current_stats, cap_getter):
  if not current_stats:
    return False

  for stat in TRACKED_STATS:
    if int(current_stats.get(stat, 0)) < cap_getter(stat):
      return False

  return True

def are_all_stats_soft_capped(current_stats):
  if not SOFT_CAP_ENABLED:
    return True
  return _are_all_stats_at_caps(current_stats, _get_soft_stat_cap)

def are_all_stats_capped(current_stats):
  return _are_all_stats_at_caps(current_stats, _get_hard_stat_cap)

def get_effective_stat_cap(stat, current_stats):
  if SOFT_CAP_ENABLED and not are_all_stats_soft_capped(current_stats):
    return _get_soft_stat_cap(stat), "soft"
  return _get_hard_stat_cap(stat), "hard"

def filter_by_stat_caps(results, current_stats):
  filtered = {}
  if are_all_stats_capped(current_stats):
    log_info("All tracked stats reached their caps; bypassing stat cap filtering")
    return dict(results)

  cap_mode = "soft" if SOFT_CAP_ENABLED and not are_all_stats_soft_capped(current_stats) else "hard"
  log_debug(f"Filtering training options by stat caps. Current stats: {current_stats}")
  log_debug(f"Current stat cap mode: {cap_mode}")
  log_debug(f"Available training options: {list(results.keys())}")
  
  for stat, data in results.items():
    current_stat_value = int(current_stats.get(stat, 0))
    stat_cap, cap_label = get_effective_stat_cap(stat, current_stats)
    if current_stat_value < stat_cap:
      filtered[stat] = data
      log_debug(f"{stat.upper()} training allowed: current {current_stat_value} < {cap_label} cap {stat_cap}")
    else:
      log_info(f"{stat.upper()} training filtered out: current {current_stat_value} >= {cap_label} cap {stat_cap}")
      log_debug(f"{stat.upper()} training filtered out: current {current_stat_value} >= {cap_label} cap {stat_cap}")
  
  log_debug(f"After stat cap filtering: {list(filtered.keys())} training options remaining")
  return filtered
