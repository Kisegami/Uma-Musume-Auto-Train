from core.Unity.state import check_current_year, stat_state
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config

config = load_main_config()

# Get training config with defaults
training_config = config.get("training", {})
PRIORITY_STAT = training_config.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])
MAX_FAILURE = training_config.get("maximum_failure", 15)
STAT_CAPS = training_config.get("stat_caps", {})
DO_RACE_WHEN_BAD_TRAINING = training_config.get("do_race_when_bad_training", True)
MIN_CONFIDENCE = 0.5  # Minimum confidence threshold for training decisions (currently used for retry logic)

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

def filter_by_stat_caps(results, current_stats):
  filtered = {}
  log_debug(f"Filtering training options by stat caps. Current stats: {current_stats}")
  log_debug(f"Available training options: {list(results.keys())}")
  
  for stat, data in results.items():
    current_stat_value = current_stats.get(stat, 0)
    stat_cap = STAT_CAPS.get(stat, 1200)
    if current_stat_value < stat_cap:
      filtered[stat] = data
      log_debug(f"{stat.upper()} training allowed: current {current_stat_value} < cap {stat_cap}")
    else:
      log_info(f"{stat.upper()} training filtered out: current {current_stat_value} >= cap {stat_cap}")
      log_debug(f"{stat.upper()} training filtered out: current {current_stat_value} >= cap {stat_cap}")
  
  log_debug(f"After stat cap filtering: {list(filtered.keys())} training options remaining")
  return filtered
