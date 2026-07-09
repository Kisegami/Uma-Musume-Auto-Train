import os
import json
import re
import time
import sys
from PIL import ImageStat

# Fix Windows console encoding for Unicode support
if os.name == 'nt':  # Windows
    try:
        # Set console to UTF-8 mode
        os.system('chcp 65001 > nul')
        # Also try to set stdout encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from utils.vision.recognizer import locate_all_on_screen, match_template
from utils.capture.screenshot import take_screenshot, capture_region
from utils.ocr.ocr_utils import extract_event_name_text
from core.Ura.duel_handling import HAPPY_MEEKS_CHALLENGE_EVENT, handle_happy_meeks_challenge
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.vision.template_matching import deduplicated_matches
from utils.core.config_loader import load_main_config

# Helper function to get project root directory
def _get_project_root():
    """Get the project root directory (3 levels up from core/Ura/)"""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Load config and check debug mode
project_root = _get_project_root()
config = load_main_config(os.path.join(project_root, "config.json"))
DEBUG_MODE = config.get("debug_mode", False)

# Cache for event databases to avoid reloading JSON files
_event_cache = {
    "support_card": None,
    "uma_data": None,
    "ura_finale": None,
    "custom_uma_events": None,
    "custom_support_events": None,
    "custom_scenario_events": None
}

def _load_event_databases():
    """Load all event databases with caching for performance"""
    global _event_cache
    
    # Load Support Card events if not cached
    if _event_cache["support_card"] is None and os.path.exists("assets/events/support_card.json"):
        try:
            with open("assets/events/support_card.json", "r", encoding="utf-8-sig") as f:
                _event_cache["support_card"] = json.load(f)
        except Exception as e:
            log_warning(f"Error loading support_card.json: {e}")
            _event_cache["support_card"] = []
    
    # Load Uma Data events if not cached
    if _event_cache["uma_data"] is None and os.path.exists("assets/events/uma_data.json"):
        try:
            with open("assets/events/uma_data.json", "r", encoding="utf-8-sig") as f:
                _event_cache["uma_data"] = json.load(f)
        except Exception as e:
            log_warning(f"Error loading uma_data.json: {e}")
            _event_cache["uma_data"] = []
    
    # Load Ura Finale events if not cached
    if _event_cache["ura_finale"] is None and os.path.exists("assets/events/ura_finale.json"):
        try:
            with open("assets/events/ura_finale.json", "r", encoding="utf-8-sig") as f:
                _event_cache["ura_finale"] = json.load(f)
        except Exception as e:
            log_warning(f"Error loading ura_finale.json: {e}")
            _event_cache["ura_finale"] = []
    
    return _event_cache


def _load_custom_event_templates():
    """Load custom event templates from config.json's events section
    
    Loads:
    - Uma events from: template/Events/Uma/Events_{uma_event_file}.json
    - Support card events from: template/Events/Supports/SupportCards_{support_card_template}.json
    """
    global _event_cache
    
    # Only load once (cache check)
    if (
        _event_cache["custom_uma_events"] is not None
        or _event_cache["custom_support_events"] is not None
        or _event_cache["custom_scenario_events"] is not None
    ):
        return _event_cache
    
    events_config = config.get("events", {})
    project_root = _get_project_root()
    
    # Load Uma event template
    uma_event_file = events_config.get("uma_event_file", "")
    if uma_event_file:
        uma_template_path = os.path.join(project_root, "template", "Events", "Uma", f"Events_{uma_event_file}.json")
        if os.path.exists(uma_template_path):
            try:
                with open(uma_template_path, "r", encoding="utf-8-sig") as f:
                    uma_data = json.load(f)
                    _event_cache["custom_uma_events"] = uma_data.get("CustomChoices", {})
                    log_info(f"Loaded custom Uma event template: {uma_event_file} ({len(_event_cache['custom_uma_events'])} events)")
            except Exception as e:
                log_warning(f"Error loading Uma event template {uma_event_file}: {e}")
                _event_cache["custom_uma_events"] = {}
        else:
            log_debug(f"Uma event template not found: {uma_template_path}")
            _event_cache["custom_uma_events"] = {}
    else:
        _event_cache["custom_uma_events"] = {}
    
    # Load Support Card event template
    support_template = events_config.get("support_card_template", "")
    if support_template:
        support_template_path = os.path.join(project_root, "template", "Events", "Supports", f"SupportCards_{support_template}.json")
        if os.path.exists(support_template_path):
            try:
                with open(support_template_path, "r", encoding="utf-8-sig") as f:
                    support_data = json.load(f)
                    # Convert array format to dict for quick lookup
                    custom_choices = support_data.get("CustomChoices", [])
                    _event_cache["custom_support_events"] = {item["EventName"]: item["SelectedOption"] for item in custom_choices}
                    log_info(f"Loaded custom Support Card template: {support_template} ({len(_event_cache['custom_support_events'])} events)")
            except Exception as e:
                log_warning(f"Error loading Support Card template {support_template}: {e}")
                _event_cache["custom_support_events"] = {}
        else:
            log_debug(f"Support Card template not found: {support_template_path}")
            _event_cache["custom_support_events"] = {}
    else:
        _event_cache["custom_support_events"] = {}

    scenario_key = "ura"
    scenario_template_path = os.path.join(project_root, "template", "Events", "Scenario", f"ScenarioEvents_{scenario_key}.json")
    if os.path.exists(scenario_template_path):
        try:
            with open(scenario_template_path, "r", encoding="utf-8-sig") as f:
                scenario_data = json.load(f)
                _event_cache["custom_scenario_events"] = scenario_data.get("CustomChoices", {})
                log_info(
                    f"Loaded custom Scenario event template: {scenario_key} "
                    f"({len(_event_cache['custom_scenario_events'])} events)"
                )
        except Exception as e:
            log_warning(f"Error loading Scenario event template {scenario_key}: {e}")
            _event_cache["custom_scenario_events"] = {}
    else:
        _event_cache["custom_scenario_events"] = {}
    
    return _event_cache


def _normalize_event_name(name: str) -> str:
    """Remove special markers and symbols from event names for matching
    
    Removes: (❯), (❯❯), (❯❯❯), ♪, and extra whitespace
    """
    result = name.replace("(❯)", "").replace("(❯❯)", "").replace("(❯❯❯)", "").replace("♪", "")
    return result.strip()


def _normalize_event_name_for_route(name: str) -> str:
    """Normalize OCR punctuation for exact special-event routing."""
    if not name:
        return ""

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00b4": "'",
        "`": "'",
    }
    normalized = name.strip()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return " ".join(normalized.split())


def search_custom_events(event_name):
    """Search for event in custom templates (from config.json)
    
    Args:
        event_name: The event name to search for
        
    Returns:
        str or None: The pre-configured option (e.g., "Top Option") if found, None otherwise
    """
    # Ensure custom templates are loaded
    _load_custom_event_templates()
    
    # Normalize the search term
    normalized_search = _normalize_event_name(event_name).lower()
    
    # Check Uma events first
    if _event_cache["custom_uma_events"]:
        # Try exact match first
        if event_name in _event_cache["custom_uma_events"]:
            return _event_cache["custom_uma_events"][event_name]
        
        # Try normalized exact match
        for custom_event, selected_option in _event_cache["custom_uma_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom == normalized_search:
                return selected_option
        
        # Try prefix match (e.g., "Solid Showing" matches "Solid Showing (G1)")
        for custom_event, selected_option in _event_cache["custom_uma_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom.startswith(normalized_search) and len(normalized_search) >= 5:
                log_debug(f"Prefix match: '{event_name}' → '{custom_event}'")
                return selected_option
        
        # Try substring/contains match (e.g., "Get Well Soon!" matches "Failed training (Get Well Soon!)")
        for custom_event, selected_option in _event_cache["custom_uma_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if len(normalized_search) >= 5 and normalized_search in normalized_custom:
                log_debug(f"Substring match: '{event_name}' → '{custom_event}'")
                return selected_option
    
    # Check Support Card events
    if _event_cache["custom_support_events"]:
        # Try exact match first
        if event_name in _event_cache["custom_support_events"]:
            return _event_cache["custom_support_events"][event_name]
        
        # Try normalized exact match
        for custom_event, selected_option in _event_cache["custom_support_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom == normalized_search:
                return selected_option
        
        # Try prefix match
        for custom_event, selected_option in _event_cache["custom_support_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom.startswith(normalized_search) and len(normalized_search) >= 5:
                log_debug(f"Prefix match: '{event_name}' → '{custom_event}'")
                return selected_option
        
        # Try substring/contains match
        for custom_event, selected_option in _event_cache["custom_support_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if len(normalized_search) >= 5 and normalized_search in normalized_custom:
                log_debug(f"Substring match: '{event_name}' → '{custom_event}'")
                return selected_option

    # Check Scenario events
    if _event_cache["custom_scenario_events"]:
        if event_name in _event_cache["custom_scenario_events"]:
            return _event_cache["custom_scenario_events"][event_name]

        for custom_event, selected_option in _event_cache["custom_scenario_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom == normalized_search:
                return selected_option

        for custom_event, selected_option in _event_cache["custom_scenario_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if normalized_custom.startswith(normalized_search) and len(normalized_search) >= 5:
                log_debug(f"Prefix match: '{event_name}' → '{custom_event}'")
                return selected_option

        for custom_event, selected_option in _event_cache["custom_scenario_events"].items():
            normalized_custom = _normalize_event_name(custom_event).lower()
            if len(normalized_search) >= 5 and normalized_search in normalized_custom:
                log_debug(f"Substring match: '{event_name}' → '{custom_event}'")
                return selected_option

    return None


# Cache for event names (for OCR matching)
_event_names_cache = None


def _load_all_event_names():
    """Load all event names from databases with caching for OCR matching"""
    global _event_names_cache
    
    if _event_names_cache is not None:
        return _event_names_cache
    
    try:
        from difflib import SequenceMatcher
        all_event_names = []
        event_files = [
            "assets/events/support_card.json",
            "assets/events/uma_data.json",
            "assets/events/ura_finale.json"
        ]
        
        project_root = _get_project_root()
        for event_file in event_files:
            file_path = os.path.join(project_root, event_file)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    
                    if event_file.endswith("uma_data.json"):
                        # Handle character-based structure
                        for character in data:
                            for event in character.get("UmaEvents", []):
                                event_name = event.get("EventName", "")
                                if event_name and event_name not in all_event_names:
                                    all_event_names.append(event_name)
                    else:
                        # Handle direct event list structure
                        for event in data:
                            event_name = event.get("EventName", "")
                            if event_name and event_name not in all_event_names:
                                all_event_names.append(event_name)
        
        _event_names_cache = all_event_names
        return all_event_names
    except Exception as e:
        log_warning(f"Error loading event names: {e}")
        return []


def find_best_event_match(ocr_text: str) -> str:
    """Find best matching event from database using priority-based matching
    
    Priority:
    1. Exact match (case-insensitive)
    2. Substring match (OCR text contained in DB name)
    3. Similarity match (60%+ similar)
    
    Args:
        ocr_text: The OCR-extracted event name
    
    Returns:
        str: Best matching event name from database, or original text if no match
    """
    try:
        from difflib import SequenceMatcher
        
        all_event_names = _load_all_event_names()
        
        if not ocr_text or not all_event_names:
            return ocr_text
        
        def normalize(s: str) -> str:
            """Remove special markers from event names"""
            return s.replace("(❯)", "").replace("(❯❯)", "").replace("(❯❯❯)", "").strip()
        
        clean_ocr = normalize(ocr_text.strip())
        if not clean_ocr:
            return ocr_text
        
        clean_ocr_lower = clean_ocr.lower()
        best_match = ocr_text
        best_ratio = 0.0
        best_is_substring = False
        
        for db_event in all_event_names:
            db_norm = normalize(db_event)
            db_norm_lower = db_norm.lower()
            
            # Priority 1: Exact match
            if db_norm_lower == clean_ocr_lower:
                return db_event
            
            # Priority 2: Substring match
            if clean_ocr_lower in db_norm_lower:
                if not best_is_substring or len(db_norm) < len(normalize(best_match)):
                    best_match = db_event
                    best_is_substring = True
            
            # Priority 3: Similarity match
            elif not best_is_substring:
                ratio = SequenceMatcher(None, clean_ocr_lower, db_norm_lower).ratio()
                if ratio > best_ratio and ratio >= 0.6:
                    best_ratio = ratio
                    best_match = db_event
        
        return best_match
    except Exception as e:
        log_warning(f"Event name matching failed: {e}")
        return ocr_text

 

def count_event_choices():
    """
    Count how many event choice icons are found on screen.
    Uses event_choice_1.png as template to find all U-shaped icons.
    Filters matches by brightness to avoid dim/false positives.
    Returns:
        tuple: (count, locations) - number of unique bright choices found and their locations
    """
    template_path = "assets/icons/event_choice_1.png"
    
    if not os.path.exists(template_path):
        log_debug(f" Template not found: {template_path}")
        return 0, []
    
    try:
        log_debug(f" Searching for event choices using: {template_path}")
        
        screenshot = take_screenshot()
        raw_locations = match_template(
            screenshot,
            template_path,
            confidence=0.45,
            region=(6, 450, 126, 1776),
        )
        
        log_debug(f" Raw locations found: {len(raw_locations)}")
        if not raw_locations:
            log_debug(f" No event choice locations found")
            return 0, []
        
        # Sort locations by y, then x (top to bottom, left to right)
        raw_locations = sorted(raw_locations, key=lambda loc: (loc[1], loc[0]))
        unique_locations = deduplicated_matches(raw_locations, threshold=150)
        
        # Compute brightness and filter
        grayscale = screenshot.convert("L")
        bright_threshold = 160.0
        bright_locations = []
        for (x, y, w, h) in unique_locations:
            try:
                region_img = grayscale.crop((x, y, x + w, y + h))
                avg_brightness = ImageStat.Stat(region_img).mean[0]
                log_debug(f" Choice at ({x},{y},{w},{h}) brightness: {avg_brightness:.1f}")
                if avg_brightness > bright_threshold:
                    bright_locations.append((x, y, w, h))
            except Exception:
                # If brightness calc fails, skip this location
                continue

        log_debug(f" Final unique bright locations: {len(bright_locations)} (threshold: {bright_threshold})")
        return len(bright_locations), bright_locations
    except Exception as e:
        log_info(f"❌ Error counting event choices: {str(e)}")
        return 0, []

def wait_for_stable_event_choices(timeout: float = 2.0, check_interval: float = 0.2, stable_reads: int = 2):
    """
    Wait for event choice markers to stabilize before using them.

    Event title OCR can finish before the choice dialog animation is done,
    which briefly returns 0 or an incomplete choice list.
    """
    start_time = time.time()
    last_count = None
    last_locations = []
    consecutive_same = 0
    best_count = 0
    best_locations = []

    while time.time() - start_time < timeout:
        count, locations = count_event_choices()

        if count > best_count:
            best_count = count
            best_locations = locations

        if count == last_count and locations == last_locations:
            consecutive_same += 1
        else:
            last_count = count
            last_locations = locations
            consecutive_same = 1

        if count > 0 and consecutive_same >= stable_reads:
            log_debug(f" Event choices stabilized at {count}")
            return count, locations

        time.sleep(check_interval)

    if best_count > 0:
        log_debug(f" Event choices did not fully stabilize, using best observed count: {best_count}")
        return best_count, best_locations

    return last_count or 0, last_locations


def load_event_priorities():
    """Load event priority configuration from event_priority.json"""
    try:
        project_root = _get_project_root()
        event_priority_path = os.path.join(project_root, "event_priority.json")
        if os.path.exists(event_priority_path):
            with open(event_priority_path, "r", encoding="utf-8") as f:
                priorities = json.load(f)
            return priorities
        else:
            log_info(f"Warning: event_priority.json not found")
            return {"Good_choices": [], "Bad_choices": []}
    except Exception as e:
        log_info(f"Error loading event priorities: {e}")
        return {"Good_choices": [], "Bad_choices": []}

def analyze_event_options(options, priorities):
    """Analyze event options and recommend the best choice based on priorities (optimized version)"""
    good_choices = priorities.get("Good_choices", [])
    bad_choices = priorities.get("Bad_choices", [])
    
    option_analysis = {}
    all_options_bad = True
    
    # Analyze each option
    for option_name, option_reward in options.items():
        reward_lower = option_reward.lower()
        
        # Check for good choices
        good_matches = []
        for good_choice in good_choices:
            if good_choice.lower() in reward_lower:
                good_matches.append(good_choice)
        
        # Check for bad choices
        bad_matches = []
        for bad_choice in bad_choices:
            if bad_choice.lower() in reward_lower:
                bad_matches.append(bad_choice)
        
        option_analysis[option_name] = {
            "reward": option_reward,
            "good_matches": good_matches,
            "bad_matches": bad_matches,
            "has_good": len(good_matches) > 0,
            "has_bad": len(bad_matches) > 0
        }
        
        # If any option has good choices, not all options are bad
        if len(good_matches) > 0:
            all_options_bad = False
    
    # Determine recommendation
    recommended_option = None
    recommendation_reason = ""
    
    if all_options_bad:
        # If all options have bad choices, pick based on good choice priority
        best_options = []
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            for good_choice in analysis["good_matches"]:
                try:
                    priority = good_choices.index(good_choice)
                    if priority < best_priority or best_priority == -1:
                        best_priority = priority
                        best_options = [option_name]
                    elif priority == best_priority:
                            best_options.append(option_name)
                except ValueError:
                    continue
        
        if best_options:
            recommended_option = best_options[0]
            best_option_analysis = option_analysis[recommended_option]
            recommendation_reason = f"All options have bad choices. Recommended based on highest priority good choice: '{best_option_analysis['good_matches'][0]}'"
    else:
        # Normal case: avoid bad choices completely
        best_options = []
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            # Only consider options that have good choices AND NO bad choices
            if analysis["has_good"] and not analysis["has_bad"]:
                for good_choice in analysis["good_matches"]:
                    try:
                        priority = good_choices.index(good_choice)
                        if priority < best_priority or best_priority == -1:
                            best_priority = priority
                            best_options = [option_name]
                        elif priority == best_priority:
                            best_options.append(option_name)
                    except ValueError:
                        continue
        
        if best_options:
            recommended_option = best_options[0]
            best_option_analysis = option_analysis[recommended_option]
            recommendation_reason = f"Recommended based on highest priority good choice: '{best_option_analysis['good_matches'][0]}'"
        else:
            # Fallback: pick option with least bad choices
            best_option = None
            min_bad_choices = 999
            
            for option_name, analysis in option_analysis.items():
                bad_count = len(analysis["bad_matches"])
                if bad_count < min_bad_choices:
                    min_bad_choices = bad_count
                    best_option = option_name
            
            if best_option:
                recommended_option = best_option
                recommendation_reason = f"No clean options available. Selected option with fewest bad choices: {min_bad_choices} bad choices"
    
    return {
        "recommended_option": recommended_option,
        "recommendation_reason": recommendation_reason,
        "option_analysis": option_analysis,
        "all_options_bad": all_options_bad
    }

def search_events_exact(event_name):
    """Search for exact event name match in all databases (cached)"""
    results = {}
    cache = _load_event_databases()
    
    # Support Card
    if cache["support_card"]:
        for ev in cache["support_card"]:
            if ev.get("EventName") == event_name:
                entry = results.setdefault(event_name, {"source": "Support Card", "options": {}})
                entry["options"].update(ev.get("EventOptions", {}))
    
    # Uma Data
    if cache["uma_data"]:
        for character in cache["uma_data"]:
            for ev in character.get("UmaEvents", []):
                if ev.get("EventName") == event_name:
                    entry = results.setdefault(event_name, {"source": "Uma Data", "options": {}})
                    if entry["source"] == "Support Card":
                        entry["source"] = "Both"
                    elif entry["source"].startswith("Support Card +"):
                        entry["source"] = entry["source"].replace("Support Card +", "Both +")
                    entry["options"].update(ev.get("EventOptions", {}))
    
    # Ura Finale
    if cache["ura_finale"]:
        for ev in cache["ura_finale"]:
            if ev.get("EventName") == event_name:
                entry = results.setdefault(event_name, {"source": "Ura Finale", "options": {}})
                if entry["source"] == "Support Card":
                    entry["source"] = "Support Card + Ura Finale"
                elif entry["source"] == "Uma Data":
                    entry["source"] = "Uma Data + Ura Finale"
                elif entry["source"] == "Both":
                    entry["source"] = "All Sources"
                entry["options"].update(ev.get("EventOptions", {}))
    
    return results

def search_events_fuzzy(event_name):
    """Search for fuzzy event name match in all databases (cached, optimized)
    
    Uses improved matching that prioritizes:
    1. Events that start with the OCR text
    2. Events where OCR text is a complete word
    3. Substring matches (deprioritized)
    """
    exact_matches = {}  # For events starting with OCR text
    word_matches = {}   # For events where OCR is a complete word
    loose_matches = {}  # For substring matches (deprioritized)
    
    event_name_lower = event_name.lower().strip()
    cache = _load_event_databases()
    
    def categorize_match(db_name, db_name_lower):
        """Categorize how well the event name matches"""
        # Exact match at start (highest priority)
        if db_name_lower.startswith(event_name_lower):
            return "exact"
        
        # Check if OCR text is a complete word in the database name
        db_words = re.split(r'[\s\!\?\(\)\[\]\-\>\<\,\.]', db_name_lower)
        db_words = [w for w in db_words if w]
        
        for word in db_words:
            if word == event_name_lower:  # Complete word match
                return "word"
            if word.startswith(event_name_lower) and len(event_name_lower) >= 3:
                return "word"
        
        # Substring match (lowest priority)
        if len(event_name_lower) >= 5 and event_name_lower in db_name_lower:
            return "loose"
        
        return None
    
    # Process Support Card events
    if cache["support_card"]:
        for ev in cache["support_card"]:
            db_name = ev.get("EventName", "")
            if not db_name:
                continue
            db_name_lower = db_name.lower().strip()
            
            match_type = categorize_match(db_name, db_name_lower)
            if match_type == "exact":
                entry = exact_matches.setdefault(db_name, {"source": "Support Card", "options": {}})
                entry["options"].update(ev.get("EventOptions", {}))
            elif match_type == "word":
                entry = word_matches.setdefault(db_name, {"source": "Support Card", "options": {}})
                entry["options"].update(ev.get("EventOptions", {}))
            elif match_type == "loose":
                entry = loose_matches.setdefault(db_name, {"source": "Support Card", "options": {}})
                entry["options"].update(ev.get("EventOptions", {}))
    
    # Process Uma Data events
    if cache["uma_data"]:
        for character in cache["uma_data"]:
            for ev in character.get("UmaEvents", []):
                db_name = ev.get("EventName", "")
                if not db_name:
                    continue
                db_name_lower = db_name.lower().strip()
                
                match_type = categorize_match(db_name, db_name_lower)
                target_dict = exact_matches if match_type == "exact" else (word_matches if match_type == "word" else (loose_matches if match_type == "loose" else None))
                
                if target_dict is not None:
                    entry = target_dict.setdefault(db_name, {"source": "Uma Data", "options": {}})
                    if entry["source"] == "Support Card":
                        entry["source"] = "Both"
                    elif entry["source"].startswith("Support Card +"):
                        entry["source"] = entry["source"].replace("Support Card +", "Both +")
                    entry["options"].update(ev.get("EventOptions", {}))
    
    # Process Ura Finale events
    if cache["ura_finale"]:
        for ev in cache["ura_finale"]:
            db_name = ev.get("EventName", "")
            if not db_name:
                continue
            db_name_lower = db_name.lower().strip()
            
            match_type = categorize_match(db_name, db_name_lower)
            target_dict = exact_matches if match_type == "exact" else (word_matches if match_type == "word" else (loose_matches if match_type == "loose" else None))
            
            if target_dict is not None:
                entry = target_dict.setdefault(db_name, {"source": "Ura Finale", "options": {}})
                if entry["source"] == "Support Card":
                    entry["source"] = "Support Card + Ura Finale"
                elif entry["source"] == "Uma Data":
                    entry["source"] = "Uma Data + Ura Finale"
                elif entry["source"] == "Both":
                    entry["source"] = "All Sources"
                entry["options"].update(ev.get("EventOptions", {}))
    
    # Return in priority order
    if exact_matches:
        return exact_matches
    elif word_matches:
        return word_matches
    elif loose_matches:
        return loose_matches
    
    return {}


def get_event_api():
    """
    Get the current event payload from the API instead of OCR.

    Returns:
        dict | None: Event payload, or None if API unavailable.
    """
    try:
        from utils.integrations.umat_api import get_events, is_api_enabled
        if not is_api_enabled():
            return None
        data = get_events()
    except ImportError:
        return None

    if data is None:
        return None

    events = data.get("events", [])
    if not events:
        log_debug("[API] No events from API")
        return None

    name = events[0].get("name", "")
    if name:
        log_debug(f"[API] Event name: {name}")
        return events[0]
    return None


def get_event_name_api():
    """
    Get the current event name from the API instead of OCR.

    Returns:
        str | None: Event name string, or None if API unavailable.
    """
    event_data = get_event_api()
    if event_data:
        return event_data.get("name", "")
    return None

def handle_event_choice():
    """
    Main function to handle event detection and choice selection.
    This function should be called when an event is detected.
    
    Returns:
        tuple: (choice_number, success, choice_locations) - choice number, success status, and found locations
    """
    # Define the region for event name detection
    from utils.constants.ura import EVENT_REGION
    event_region = EVENT_REGION
    
    log_info(f"Event detected, scan event")
    
    try:
        time.sleep(0.5)
        event_data = None

        # Re-validate that this is a choices event before OCR (avoid scanning non-choice dialogs)
        recheck_count, recheck_locations = wait_for_stable_event_choices()
        log_debug(f" Recheck choices after delay: {recheck_count}")
        if recheck_count == 0:
            log_info(f"[INFO] Event choices not visible after delay, skipping analysis")
            return 1, False, []

        try:
            from utils.integrations.umat_api import is_api_enabled
            _api_on = is_api_enabled()
        except ImportError:
            _api_on = False

        if _api_on:
            event_image = None
            event_data = get_event_api()
            event_name = event_data.get("name", "") if event_data else ""
            if event_name:
                log_info(f"[API] Event name from API: {event_name}")
            else:
                log_warning("[API] Failed to get event name from API; skipping event handling for this loop.")
                return 1, False, []
        else:
            event_image = capture_region(event_region)
            event_name = extract_event_name_text(event_image).strip()
        
        if not event_name:
            log_error(f"❌ EVENT DETECTION FAILED: No text detected in event region")
            
            # Save debug image for analysis (only when debug mode is enabled)
            if DEBUG_MODE:
                debug_filename = f"debug_event_detection_failure_{int(time.time())}.png"
                event_image.save(debug_filename)
                log_error(f"❌ Debug image saved to: {debug_filename}")
            log_error(f"❌ Event region coordinates: {event_region}")
            log_error(f"❌ Image size: {event_image.size}")
            log_error(f"❌ Check the OCR logs above for what text was detected (if any)")
            
            # Check if bot should stop on detection failure (configurable)
            stop_on_event_failure = config.get("stop_on_event_detection_failure", False)
            
            if stop_on_event_failure:
                log_error(f"❌ BOT STOPPED - Please check the event screen and OCR configuration")
                log_error(f"❌ (To disable auto-stop, set 'stop_on_event_detection_failure' to false in config.json)")
                raise RuntimeError("Event detection failed: No text detected in event region. Bot stopped.")
            else:
                log_warning(f"⚠️  Continuing with fallback (top choice) - Enable 'stop_on_event_detection_failure' in config to stop on failure")
                # Fallback to top choice
                return 1, False, recheck_locations
        
        log_info(f"Event found: {event_name}")

        if _normalize_event_name_for_route(event_name) == HAPPY_MEEKS_CHALLENGE_EVENT:
            return handle_happy_meeks_challenge(recheck_locations, event_data=event_data)

        # Check custom event templates first (from config.json)
        custom_choice = search_custom_events(event_name)
        if custom_choice:
            log_info(f"🎯 Custom template match: {event_name} → {custom_choice}")
            choices_found, choice_locations = wait_for_stable_event_choices()
            
            # Map custom_choice to choice number
            choice_number = 1
            if choices_found == 2:
                if "top" in custom_choice.lower():
                    choice_number = 1
                elif "bottom" in custom_choice.lower():
                    choice_number = 2
            elif choices_found == 3:
                if "top" in custom_choice.lower():
                    choice_number = 1
                elif "middle" in custom_choice.lower():
                    choice_number = 2
                elif "bottom" in custom_choice.lower():
                    choice_number = 3
            elif choices_found >= 4:
                option_match = re.search(r'option\s*(\d+)', custom_choice.lower())
                if option_match:
                    choice_number = int(option_match.group(1))
            
            if choice_number > choices_found:
                log_warning(f"Custom choice {choice_number} exceeds available choices ({choices_found}), defaulting to first")
                choice_number = 1
            
            log_info(f"Choose choice: {choice_number}")
            return choice_number, True, choice_locations

        # Search for event in database
        found_events = search_events_exact(event_name)
        if not found_events:
            # Fallback to fuzzy search for partial matches
            found_events = search_events_fuzzy(event_name)
        
        # Count event choices on screen
        choices_found, choice_locations = wait_for_stable_event_choices()
        
        # Load event priorities
        priorities = load_event_priorities()
        
        if found_events:
            # Event found in database
            event_name_key = list(found_events.keys())[0]
            event_data = found_events[event_name_key]
            options = event_data["options"]
            
            log_info(f"Source: {event_data['source']}")
            log_info(f"Options:")
            
            if options:
                # Analyze options with priorities
                analysis = analyze_event_options(options, priorities)
                
                for option_name, option_reward in options.items():
                    # Replace all line breaks with ', '
                    reward_single_line = option_reward.replace("\r\n", ", ").replace("\n", ", ").replace("\r", ", ")
                    
                    # Add analysis indicators
                    option_analysis = analysis["option_analysis"][option_name]
                    indicators = []
                    if option_analysis["has_good"]:
                        indicators.append("✅ Good")
                    if option_analysis["has_bad"]:
                        indicators.append("❌ Bad")
                    if option_name == analysis["recommended_option"]:
                        indicators.append("🎯 RECOMMENDED")
                    
                    indicator_text = f" [{', '.join(indicators)}]" if indicators else ""
                    log_info(f"  {option_name}: {reward_single_line}{indicator_text}")
                
                # Print recommendation
                log_info(f"Recommend: {analysis['recommended_option']}")
                
                # Determine which choice to select based on recommendation and choice count
                expected_options = len(options)
                recommended_option = analysis["recommended_option"]
                
                # If no recommendation, default to first choice
                if recommended_option is None:
                    log_info(f"No recommendation found, defaulting to first choice")
                    choice_number = 1
                else:
                    # Map recommended option to choice number
                    choice_number = 1  # Default to first choice
                    
                    if expected_options == 2:
                        if "top" in recommended_option.lower():
                            choice_number = 1
                        elif "bottom" in recommended_option.lower():
                            choice_number = 2
                    elif expected_options == 3:
                        if "top" in recommended_option.lower():
                            choice_number = 1
                        elif "middle" in recommended_option.lower():
                            choice_number = 2
                        elif "bottom" in recommended_option.lower():
                            choice_number = 3
                    elif expected_options >= 4:
                        # For 4+ choices, look for "Option 1", "Option 2", etc.
                        option_match = re.search(r'option\s*(\d+)', recommended_option.lower())
                        if option_match:
                            choice_number = int(option_match.group(1))
                
                # Verify choice number is valid
                if choice_number > choices_found:
                    log_info(f"Warning: Recommended choice {choice_number} exceeds available choices ({choices_found})")
                    choice_number = 1  # Fallback to first choice
                
                log_info(f"Choose choice: {choice_number}")
                return choice_number, True, choice_locations
            else:
                log_info(f"No valid options found in database")
                return 1, False, choice_locations
        else:
            # Unknown event
            log_info(f"Unknown event - not found in database")
            log_info(f"Choices found: {choices_found}")
            return 1, False, choice_locations  # Default to first choice for unknown events
    
    except Exception as e:
        # Check if this is a critical event detection failure that should stop the bot
        error_msg = str(e)
        if "Event detection failed" in error_msg:
            # Re-raise the error to stop the bot completely
            log_error(f"❌ Critical event detection failure - stopping bot execution")
            raise  # Re-raise the original exception to stop execution
        
        # Handle other errors gracefully with fallback
        try:
            log_info(f"Error during event handling: {error_msg}")
        except UnicodeEncodeError:
            # Fallback: print error without problematic characters
            log_info(f"Error during event handling: {repr(e)}")
        
        # If choices are visible, return their locations to allow fallback top-choice click
        try:
            _, fallback_locations = wait_for_stable_event_choices()
        except Exception:
            fallback_locations = []
        
        log_warning("Event analysis failed; skipping event handling for this loop")
        return 1, False, []  # Let the main loop continue without clicking

def click_event_choice(choice_number, choice_locations=None):
    """
    Click on the specified event choice using pre-found locations.
    
    Args:
        choice_number: The choice number to click (1, 2, 3, etc.)
        choice_locations: Pre-found locations from count_event_choices() (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from utils.inputs.input import tap
        
        # Use pre-found locations if provided, otherwise search again
        if choice_locations is None or len(choice_locations) < choice_number:
            log_debug(f" No pre-found locations, searching for event choices...")
            if not choice_locations:
                _, choice_locations = wait_for_stable_event_choices()
                if not choice_locations:
                    log_info(f"No event choice icons found")
                    return False
        else:
            log_debug(f" Using pre-found choice locations")
        unique_locations = sorted(choice_locations, key=lambda loc: loc[1])
        
        # Click the specified choice
        if 1 <= choice_number <= len(unique_locations):
            target_location = unique_locations[choice_number - 1]
            x, y, w, h = target_location
            center = (x + w//2, y + h//2)
            
            log_info(f"Clicking choice {choice_number} at position {center}")
            tap(center[0], center[1])
            return True
        else:
            log_info(f"Invalid choice number: {choice_number} (available: 1-{len(unique_locations)})")
            return False
    
    except Exception as e:
        log_info(f"Error clicking event choice: {e}")
        return False
