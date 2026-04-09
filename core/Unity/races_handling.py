import time
import json
import random
import numpy as np
from PIL import ImageStat

from utils.vision.recognizer import locate_on_screen, match_template, locate_all_on_screen, max_match_confidence
from utils.inputs.input import tap, triple_click, long_press, tap_on_image, swipe
from utils.capture.screenshot import take_screenshot
from utils.vision.template_matching import wait_for_image, deduplicated_matches
from utils.core.log import log_debug, log_info, log_warning, log_error, log_success
from utils.core.config_loader import load_main_config
from core.Unity.state import check_skill_points_cap, check_current_year
from core.Unity.ocr import extract_text
from utils.constants.unity import get_template_region
import os

# Helper function to get project root directory
def _get_project_root():
    """Get the project root directory (3 levels up from core/Unity/)"""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

project_root = _get_project_root()


def _load_config():
    return load_main_config(os.path.join(project_root, "config.json"))


# Load config for RETRY_RACE
try:
    config = _load_config()
    racing_config = config.get("racing", {})
    RETRY_RACE = racing_config.get("retry_race", True)
    BUY_CLOCK_CARATS = racing_config.get("buy_clock_carats", False)
    STOP_ON_RACE_FAIL = racing_config.get("stop_on_race_fail", True)
except Exception:
    config = {}
    RETRY_RACE = True
    BUY_CLOCK_CARATS = False
    STOP_ON_RACE_FAIL = True

# Region offsets from fan center (same as test code)
GRADE_OFFSET = (-118, -115, 93, 69)  # x, y, width, height
OCR_OFFSET = (-37, -120, 580, 69)  # x, y, width, height

def is_racing_available(year):
    """Check if racing is available based on the current year/month"""
    # No races in Pre-Debut
    if is_pre_debut_year(year):
        return False
    # No races in Finale Underway (final training period before URA)
    if "Finale Underway" in year:
        return False
    year_parts = year.split(" ")
    # No races in July and August (summer break)
    if len(year_parts) > 3 and year_parts[3] in ["Jul", "Aug"] and year_parts[0] != "Junior":
        return False
    return True

def is_pre_debut_year(year):
    return ("Pre-Debut" in year or "PreDebut" in year or 
            "PreeDebut" in year or "Pre" in year)

def get_grade_priority(grade):
    """Get priority score for a grade (lower number = higher priority)"""
    grade_priority = {
        "G1": 1,
        "G2": 2,
        "G3": 3,
        "OP": 4,
        "PRE-OP": 5
    }
    return grade_priority.get(grade.upper(), 999)  # Unknown grades get lowest priority

def check_race_in_database(year=None):
    """Check if a suitable race exists in the database for the current year.
    
    This function ONLY checks the database - it does NOT navigate or click anything.
    Use this to decide whether to attempt racing before leaving the training screen.
    
    Returns:
        bool: True if a suitable race is available, False otherwise
    """
    try:
        # Get current year if not provided
        if year is None:
            year = check_current_year()
        if not year:
            log_debug(f"check_race_in_database: Could not detect current year")
            return False
        
        # Check basic racing availability
        if not is_racing_available(year):
            log_debug(f"check_race_in_database: Racing not available for {year}")
            return False
        
        # Load configuration
        try:
            config = _load_config()
        except Exception as e:
            log_debug(f"check_race_in_database: Error loading config: {e}")
            return False
        
        # Load race data
        try:
            with open(os.path.join(project_root, "assets/races/clean_race_data.json"), "r", encoding="utf-8") as f:
                race_data = json.load(f)
        except Exception as e:
            log_debug(f"check_race_in_database: Error loading race data: {e}")
            return False
        
        if not race_data or year not in race_data:
            log_debug(f"check_race_in_database: No race data for {year}")
            return False
        
        # Get config criteria
        racing_config_section = config.get("racing", {})
        allowed_grades = racing_config_section.get("allowed_grades", ["G1", "G2", "G3", "OP", "PRE-OP"])
        allowed_tracks = racing_config_section.get("allowed_tracks", ["Turf", "Dirt"])
        allowed_distances = racing_config_section.get("allowed_distances", ["Sprint", "Mile", "Medium", "Long"])
        
        # Check if any race matches criteria
        for race_name, race_info in race_data[year].items():
            race_grade = race_info.get("grade", "UNKNOWN")
            race_surface = race_info.get("surface", "UNKNOWN")
            race_category = race_info.get("distance_type", "UNKNOWN")
            
            if race_grade not in allowed_grades:
                continue
            if allowed_tracks and race_surface not in allowed_tracks:
                continue
            if allowed_distances and race_category not in allowed_distances:
                continue
            
            # Found a suitable race
            log_debug(f"check_race_in_database: Found suitable race: {race_name} ({race_grade})")
            return True
        
        log_debug(f"check_race_in_database: No suitable race found in database")
        return False
        
    except Exception as e:
        log_debug(f"check_race_in_database: Error: {e}")
        return False

def _normalize_ocr_text(text: str) -> str:
    """Normalize OCR text to fix common misreadings.
    
    Common OCR errors:
    - O (letter) misread as 0 (zero) or vice versa
    - l (lowercase L) misread as 1 (one)
    - I (uppercase i) misread as 1 (one)
    """
    import re
    
    if not text:
        return text
    
    # For distance patterns, convert O to 0 (e.g., "200Om" -> "2000m", "120Om" -> "1200m")
    # Match patterns like digits followed by O and then 'm'
    text = re.sub(r'(\d+)O([mM])', r'\g<1>0\2', text)
    
    # Also handle multiple O's like "20OOm" -> "2000m"
    text = re.sub(r'(\d+)O+([mM])', lambda m: m.group(1) + '0' * m.group(0).count('O') + m.group(2), text)
    
    return text


def find_target_race_in_screenshot(screenshot, race_description):
    """Find target race in a given screenshot and return fan center coordinates"""
    matches = locate_all_on_screen("assets/races/fan.png", confidence=0.8, region=(390, 1138, 513, 1495))
    
    log_debug(f"Found {len(matches) if matches else 0} fan matches")
    
    if not matches:
        return None, None
    
    unique_fans = deduplicated_matches(matches, threshold=30)
    log_debug(f"After deduplication: {len(unique_fans)} unique fans")
    
    # Normalize the race description for comparison
    normalized_description = _normalize_ocr_text(race_description) if race_description else ""
    
    for i, (x, y, w, h) in enumerate(unique_fans):
        center_x, center_y = x + w//2, y + h//2
        
        # OCR region
        ox, oy, ow, oh = center_x + OCR_OFFSET[0], center_y + OCR_OFFSET[1], OCR_OFFSET[2], OCR_OFFSET[3]
        text = extract_text(screenshot.crop((ox, oy, ox + ow, oy + oh)))
        
        # Normalize OCR text to fix common misreadings (O -> 0, etc.)
        normalized_text = _normalize_ocr_text(text) if text else ""
        
        log_debug(f"Fan {i+1} at ({center_x}, {center_y}) - OCR text: '{text}' -> normalized: '{normalized_text}'")
        
        # Check if the race description appears in the normalized OCR text
        if normalized_description and normalized_text and normalized_description.lower() in normalized_text.lower():
            log_debug(f"Found race with description '{race_description}' at fan center ({center_x}, {center_y})")
            return center_x, center_y
    
    return None, None

def execute_race_after_selection():
    """Execute race after race selection - handles race button tapping and race execution"""
    log_info(f"Race Execute - Starting race after selection...")
    
    # Wait for race button to appear after selecting race
    log_info(f"Race Execute - Waiting for race button...")
    race_btn = wait_for_image("assets/buttons/race_btn.png", timeout=10, region=get_template_region("assets/buttons/race_btn.png"))
    if not race_btn:
        log_warning(f"Race Execute - Race button not found after 10s")
        return False
    
    # Click race button twice to start the race
    for j in range(2):
        if tap_on_image("assets/buttons/race_btn.png", confidence=0.8, min_search=1, region=get_template_region("assets/buttons/race_btn.png")):
            log_debug(f"Race button clicked {j+1}/2")
            time.sleep(0.5)
        else:
            log_debug(f"Failed to click race button {j+1}/2")
    
    # Race starts automatically after clicking race button twice
    # Use the existing race_prep function to handle strategy and race execution
    log_info(f"Race Execute - Race started, calling race_prep...")
    race_prep()
    # time.sleep(1)
    # Handle post-race actions
    after_race()
    return True

def search_race_with_swiping(race_description, year, max_swipes=3):
    """Helper function to search for a race with swiping - eliminates duplicate code"""
    log_info(f"Race Search - Looking for: {race_description}")
    
    # Take screenshot and search for the race
    screenshot = take_screenshot()
    target_x, target_y = find_target_race_in_screenshot(screenshot, race_description)
    
    if target_x and target_y:
        log_info(f"Race Search - Race found on initial screen! Tapping at ({target_x}, {target_y})")
        tap(target_x, target_y)
        time.sleep(0.5)
        return True
    
    # If not found initially, perform swipes
    log_debug(f"Race not found on initial screen, performing swipes...")
    
    for swipe_num in range(1, max_swipes + 1):
        log_debug(f"Swipe {swipe_num}:")
        swipe(381, 1415, 381, 1223, duration_ms=240)
        time.sleep(1)  # Wait for swipe animation
        
        # Take new screenshot after swipe
        screenshot = take_screenshot()
        
        # Search for the race after each swipe
        target_x, target_y = find_target_race_in_screenshot(screenshot, race_description)
        
        if target_x and target_y:
            log_info(f"Race Search - Race found after swipe {swipe_num}! Tapping at ({target_x}, {target_y})")
            tap(target_x, target_y)
            # time.sleep(0.5)
            return True
    
    log_info(f"Race Search - Race not found after {max_swipes} swipes")
    return False

def race_day():
    """Handle race day"""
    # Check skill points cap before race day (if enabled)
    config = _load_config()
    skills_config = config.get("skills", {})
    enable_skill_check = skills_config.get("enable_skill_point_check", True)
    
    if enable_skill_check:
        log_info(f"Race Day - Checking skill points cap...")
        check_skill_points_cap()
    
    log_info(f"Race Day - Clicking race day button...")
    if tap_on_image("assets/buttons/race_day_btn.png", min_search=10, region=get_template_region("assets/buttons/race_day_btn.png")):
        log_info(f"Race Day - Race day button clicked, clicking OK button...")
        time.sleep(0.5)
        tap_on_image("assets/buttons/ok_btn.png", confidence=0.6, min_search=2, region=get_template_region("assets/buttons/ok_btn.png"))
        
        # Wait for race selection screen to appear by waiting for race button
        log_info(f"Race Day - Waiting for race selection screen...")
        race_btn_found = wait_for_image("assets/buttons/race_btn.png", timeout=10, region=get_template_region("assets/buttons/race_btn.png"))
        if not race_btn_found:
            log_info(f"Race Day - Race button not found after 10s, failed to enter race selection")
            return False
        
        log_info(f"Race Day - Race selection screen appeared, selecting race...")
        
        # Try to find and click race button with better error handling
        race_clicked = False
        for attempt in range(3):  # Try up to 3 times
            if tap_on_image("assets/buttons/race_btn.png", confidence=0.7, min_search=1, region=get_template_region("assets/buttons/race_btn.png")):
                log_info(f"Race Day - Race button clicked (attempt {attempt + 1})")
                time.sleep(0.5)  # Wait between clicks
                
                # Click race button twice like in race_select
                for j in range(2):
                    if tap_on_image("assets/buttons/race_btn.png", confidence=0.7, min_search=5, region=get_template_region("assets/buttons/race_btn.png")):
                        log_debug(f"Race button clicked {j+1} time(s)")
                        time.sleep(0.2)
                    else:
                        log_debug(f"Failed to click race button {j+1} time(s)")
                
                race_clicked = True
                time.sleep(0.8)  # Wait for UI to respond
                break
            else:
                log_debug(f"Race button not found, attempt {attempt + 1}")
                time.sleep(0.5)
        
        if not race_clicked:
            log_info(f"Race Day - Failed to click race button after all attempts")
            return False
            
        log_info(f"Race Day - Starting race preparation...")
        race_prep()
        # time.sleep(1)
        
        # Loop to check for either next button or clock icon with polling (200ms interval, tap between checks)
        log_debug(f"Checking for next button or clock icon with polling...")
        retry_count = 0
        max_retries_per_race = 250  # 50 seconds timeout (250 * 200ms)
        
        while retry_count < max_retries_per_race:
            retry_count += 1
            log_debug(f"Check attempt {retry_count}")
            
            screenshot = take_screenshot()
            
            # Check for clock icon (race failure)
            clock_matches = match_template(screenshot, "assets/icons/clock.png", confidence=0.8, region=get_template_region("assets/icons/clock.png"))
            if clock_matches:
                log_info(f"Race Day - Race FAILED (clock icon detected, attempt {retry_count}), handling retry...")
                # Handle race retry
                handle_race_retry_if_failed()
                # Continue the loop to check again after retry
                continue
            
            # Check for next button
            next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.8, region=get_template_region("assets/buttons/next_btn.png"))
            if next_matches:
                log_info(f"Race Day - Race complete (next button found after {retry_count} attempts)")
                after_race()
                return True
            
            # Tap middle of screen between checks to advance UI
            tap(540, 960)  # Click middle of screen (1080x1920 resolution)
            time.sleep(0.2)  # 200ms interval
        
        # Safety check to prevent infinite loops
        log_info(f"Race Day - Safety limit reached ({max_retries_per_race} attempts), proceeding with after_race")
        after_race()
        return True
    return False

def check_strategy_before_race(region=(660, 974, 378, 120), max_retries=2) -> bool:
    """Check and ensure strategy matches config before race."""
    log_debug(f"Checking strategy before race... (retries left: {max_retries})")
    
    try:
        screenshot = take_screenshot()
        
        templates = {
            "front": "assets/icons/front.png",
            "late": "assets/icons/late.png", 
            "pace": "assets/icons/pace.png",
            "end": "assets/icons/end.png",
        }
        
        # Find brightest strategy using existing project functions
        best_match = None
        best_brightness = 0
        
        for name, path in templates.items():
            try:
                # Use existing match_template function
                matches = match_template(screenshot, path, confidence=0.5, region=region)
                if matches:
                    # Get confidence for best match
                    confidence = max_match_confidence(screenshot, path, region)
                    if confidence:
                        # Check brightness of the matched region
                        x, y, w, h = matches[0]
                        roi = screenshot.convert("L").crop((x, y, x + w, y + h))
                        bright = float(ImageStat.Stat(roi).mean[0])
                        
                        if bright >= 160 and bright > best_brightness:
                            best_match = (name, matches[0], confidence, bright)
                            best_brightness = bright
            except Exception:
                continue
        
        if not best_match:
            log_debug(f"No strategy found with brightness >= 160")
            return False
        
        strategy_name, bbox, conf, bright = best_match
        current_strategy = strategy_name.upper()
        
        # Load expected strategy from config
        try:
            config = _load_config()
            racing_config = config.get("racing", {})
            expected_strategy = racing_config.get("strategy", "").upper()
        except Exception:
            log_debug(f"Cannot read config.json")
            return False
        
        matches = current_strategy == expected_strategy
        log_info(f"Strategy Check - Current: {current_strategy}, Expected: {expected_strategy}, Match: {matches}")
        
        if matches:
            log_debug(f"Strategy matches config, proceeding with race")
            return True
        
        # Strategy doesn't match, try to change it
        if max_retries <= 0:
            log_warning(f"Strategy Check - Max retries reached, giving up on strategy change")
            return False
        
        log_info(f"Strategy Check - Mismatch, changing to {expected_strategy}")
        
        if change_strategy_before_race(expected_strategy):
            # Recheck after change with decremented retry count
            time.sleep(1)  # Wait for UI to settle
            strategy_changed = check_strategy_before_race(region, max_retries=max_retries - 1)
            if strategy_changed:
                log_debug(f"Strategy successfully changed")
                return True
            else:
                log_debug(f"Strategy change failed")
                return False
        else:
            log_debug(f"Failed to change strategy")
            return False
            
    except Exception as e:
        log_debug(f"Error checking strategy: {e}")
        return False

def change_strategy_before_race(expected_strategy: str) -> bool:
    """Change strategy to the expected one before race."""
    log_debug(f"Changing strategy to: {expected_strategy}")
    
    # Strategy coordinates mapping
    strategy_coords = {
        "FRONT": (882, 1159),
        "PACE": (645, 1159),
        "LATE": (414, 1159),
        "END": (186, 1162),
    }
    
    if expected_strategy not in strategy_coords:
        log_debug(f"Unknown strategy: {expected_strategy}")
        return False
    
    try:
        # Step 1: Find and tap strategy_change.png
        log_debug(f"Looking for strategy change button...")
        change_btn = wait_for_image("assets/buttons/strategy_change.png", timeout=10, confidence=0.8)
        if not change_btn:
            log_debug(f"Strategy change button not found")
            return False
        
        log_debug(f"Found strategy change button at {change_btn}")
        tap(change_btn[0], change_btn[1])
        log_debug(f"Tapped strategy change button")
        
        # Step 2: Wait for confirm.png to appear
        log_debug(f"Waiting for confirm button to appear...")
        confirm_btn = wait_for_image("assets/buttons/confirm.png", timeout=10, confidence=0.8)
        if not confirm_btn:
            log_debug(f"Confirm button not found after strategy change")
            return False
        
        log_debug(f"Confirm button appeared at {confirm_btn}")
        
        # Step 3: Tap on the specified coordinate for the right strategy
        target_x, target_y = strategy_coords[expected_strategy]
        log_debug(f"Tapping strategy position: ({target_x}, {target_y}) for {expected_strategy}")
        tap(target_x, target_y)
        log_debug(f"Tapped strategy position for {expected_strategy}")
        
        # Wait for the game to register the strategy selection
        time.sleep(0.5)
        
        # Step 4: Tap confirm.png from found location
        log_debug(f"Confirming strategy change...")
        tap(confirm_btn[0], confirm_btn[1])
        log_debug(f"Tapped confirm button")
        
        # Wait a moment for the change to take effect
        time.sleep(1)
        
        log_debug(f"Strategy change completed for {expected_strategy}")
        return True
        
    except Exception as e:
        log_debug(f"Error during strategy change: {e}")
        return False

def race_prep():
    """Prepare for race"""
    log_info(f"Race Prep - Preparing for race...")
    
    # Wait for view results button with polling (200ms interval, tap between checks)
    log_debug(f"Waiting for view results button...")
    view_result_btn = None
    max_attempts = 100  # 20 seconds timeout (100 * 200ms)
    
    for attempt in range(max_attempts):
        screenshot = take_screenshot()
        view_result_matches = match_template(screenshot, "assets/buttons/view_results.png", confidence=0.8)
        
        if view_result_matches:
            x, y, w, h = view_result_matches[0]
            view_result_btn = (x + w//2, y + h//2)
            log_info(f"Race Prep - Found view results button (attempt {attempt + 1})")
            break
        
        # Tap middle of screen between checks to advance UI
        tap(540, 960)
        time.sleep(0.2)  # 200ms interval
    
    if not view_result_btn:
        log_warning(f"Race Prep - View results button not found after {max_attempts} attempts")
        return
    
    # Check and ensure strategy matches config before race
    if not check_strategy_before_race():
        log_info(f"Race Prep - Strategy check failed, proceeding anyway...")

        # Tap view results button
    log_info(f"Race Prep - Tapping view results button...")
    tap(view_result_btn[0], view_result_btn[1])
    
    # Wait for next button or race to start with polling (200ms interval, tap between checks)
    log_debug(f"Waiting for next button or race to start...")
    next_btn = None
    race_started = False
    
    for attempt in range(max_attempts):
        screenshot = take_screenshot()
        next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.8)
        
        if next_matches:
            x, y, w, h = next_matches[0]
            next_btn = (x + w//2, y + h//2)
            log_info(f"Race Prep - Next button found, race starting (attempt {attempt + 1})")
            # Tap next button
            tap(next_btn[0], next_btn[1])
            race_started = True
            break
        
        # Check if race has started (view results button disappeared)
        view_result_check = match_template(screenshot, "assets/buttons/view_results.png", confidence=0.8)
        if not view_result_check:
            log_info(f"Race Prep - View results disappeared, race starting (attempt {attempt + 1})")
            race_started = True
            break
        
        # Tap middle of screen between checks to advance UI
        tap(540, 960)
        time.sleep(0.2)  # 200ms interval
    
    if not race_started:
        log_warning(f"Race Prep - Race did not start after {max_attempts} attempts")

def handle_race_retry_if_failed():
    """Detect race failure on race day and retry based on config.

    Recognizes failure by detecting `assets/icons/clock.png` on screen.
    If `retry_race` is true in config, taps `assets/buttons/try_again.png`, waits 5s,
    and calls `race_prep()` again. Returns True if a retry was performed, False otherwise.
    """
    try:
        # Check for failure indicator (clock icon)
        clock = locate_on_screen("assets/icons/clock.png", confidence=0.8, region=get_template_region("assets/icons/clock.png"))
        if not clock:
            return False

        log_info(f"Race failed detected (clock icon).")

        if not RETRY_RACE:
            if STOP_ON_RACE_FAIL:
                log_info(f"retry_race is disabled and stop_on_race_fail is ON. Stopping automation.")
                raise SystemExit(0)
            else:
                log_info(f"retry_race is disabled. Skipping failed race (tapping cancel + next)...")
                # Try cancel buttons in order
                for cancel_path in [
                    "assets/buttons/cancel_btn.png",
                    "assets/buttons/cancel_lobby.png",
                    "assets/buttons/cancel_recreation.png",
                ]:
                    cancel = locate_on_screen(cancel_path, confidence=0.8, region=get_template_region(cancel_path))
                    if cancel:
                        tap(cancel[0], cancel[1])
                        log_info(f"Tapped {cancel_path}")
                        break
                time.sleep(1)
                # Tap next button twice to continue career
                for i in range(2):
                    next_btn = locate_on_screen("assets/buttons/next_btn.png", confidence=0.8, region=get_template_region("assets/buttons/next_btn.png"))
                    if next_btn:
                        tap(next_btn[0], next_btn[1])
                        log_info(f"Tapped next button ({i+1}/2)")
                        time.sleep(0.5)
                return True

        # Try to click Try Again button
        try_again = locate_on_screen("assets/buttons/try_again.png", confidence=0.8, region=get_template_region("assets/buttons/try_again.png"))
        if try_again:
            time.sleep(0.5)
            log_info(f"Clicking Try Again button.")
            tap(try_again[0], try_again[1])
        else:
            log_info(f"Try Again button not found. Attempting helper click...")
            # Fallback: attempt generic click using click helper
            tap_on_image("assets/buttons/try_again.png", confidence=0.8, min_search=10, region=get_template_region("assets/buttons/try_again.png"))

        # Check for clock purchase popup (user is out of clocks)
        time.sleep(2)
        clock_purchase = locate_on_screen("assets/ui/clock_purchase.png", confidence=0.8)
        if clock_purchase:
            if BUY_CLOCK_CARATS:
                log_info(f"Out of clocks - buying clock with carats...")
                tap_on_image("assets/buttons/ok_btn.png", confidence=0.6, min_search=5, region=get_template_region("assets/buttons/ok_btn.png"))
            else:
                log_info(f"Out of clocks and buy_clock_carats is disabled. Stopping automation.")
                raise SystemExit(0)

        # Wait before re-prepping the race
        log_info(f"Waiting 5 seconds before retrying the race...")
        time.sleep(5)
        log_info(f"Re-preparing race...")
        race_prep()
        return True
    except SystemExit:
        raise
    except Exception as e:
        log_error(f"handle_race_retry_if_failed error: {e}")
        return False

def after_race():
    """Handle post-race actions"""
    log_info(f"After Race - Handling post-race actions...")
    
    # Wait for first next button with polling (200ms interval, tap between checks)
    log_debug(f"Waiting for first next button...")
    next_btn = None
    max_attempts = 150  # 30 seconds timeout (150 * 200ms)
    
    for attempt in range(max_attempts):
        screenshot = take_screenshot()
        
        # Check for next button
        next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.7, region=get_template_region("assets/buttons/next_btn.png"))
        if next_matches:
            x, y, w, h = next_matches[0]
            next_btn = (x + w//2, y + h//2)
            log_info(f"After Race - Found first next button (attempt {attempt + 1})")
            # Tap next button
            tap(next_btn[0], next_btn[1])
            break
        
        # Also check for clock icon (race failure can occur here too)
        clock_matches = match_template(screenshot, "assets/icons/clock.png", confidence=0.8, region=get_template_region("assets/icons/clock.png"))
        if clock_matches:
            log_info(f"After Race - Clock icon found, handling retry...")
            handle_race_retry_if_failed()
            # Restart waiting for next button after retry
            attempt = -1  # Will be incremented to 0 in next iteration
            continue
        
        # Tap middle of screen between checks to advance UI
        tap(540, 960)
        time.sleep(0.2)  # 200ms interval
    
    if not next_btn:
        log_warning(f"After Race - First next button not found after {max_attempts} attempts")
    
    # Wait for second next button with polling and spam tap until it appears
    log_debug(f"Waiting for second next button (spam tapping)...")
    next2_btn = None
    
    for attempt in range(max_attempts):
        screenshot = take_screenshot()
        
        # Check for second next button
        next2_matches = match_template(screenshot, "assets/buttons/next2_btn.png", confidence=0.7, region=get_template_region("assets/buttons/next2_btn.png"))
        if next2_matches:
            x, y, w, h = next2_matches[0]
            next2_btn = (x + w//2, y + h//2)
            log_info(f"After Race - Found second next button (attempt {attempt + 1})")
            # Tap next2 button
            tap(next2_btn[0], next2_btn[1])
            break
        
        # Also check for clock icon (race failure can occur here too)
        clock_matches = match_template(screenshot, "assets/icons/clock.png", confidence=0.8, region=get_template_region("assets/icons/clock.png"))
        if clock_matches:
            log_info(f"After Race - Clock icon found during second next, handling retry...")
            handle_race_retry_if_failed()
            # Restart waiting for next buttons after retry
            # Re-check first next button
            next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.7, region=get_template_region("assets/buttons/next_btn.png"))
            if next_matches:
                x, y, w, h = next_matches[0]
                tap(x + w//2, y + h//2)
            attempt = -1  # Will be incremented to 0 in next iteration
            continue
        
        # Spam tap middle of screen between checks to advance UI
        tap(540, 960)
        time.sleep(0.2)  # 200ms interval
    
    if not next2_btn:
        log_warning(f"After Race - Second next button not found after {max_attempts} attempts")
    
    log_info(f"After Race - Post-race actions complete")

def enter_race_selection_screen():
    """Helper function to enter race selection screen - eliminates duplicate code"""
    log_info(f"Race Select - Entering race selection screen...")
    
    # Tap races button
    if not tap_on_image("assets/buttons/races_btn.png", min_search=10, region=get_template_region("assets/buttons/races_btn.png")):
        log_warning(f"Race Select - Failed to find races button")
        return False
    
    time.sleep(0.5)
    
    # Try to tap OK button if it appears (optional)
    ok_clicked = tap_on_image("assets/buttons/ok_btn.png", confidence=0.5, min_search=2, region=get_template_region("assets/buttons/ok_btn.png"))
    if ok_clicked:
        log_debug(f"OK button found and clicked")
    else:
        log_debug(f"OK button not found, proceeding without it")
    
    # Wait for race button to appear, indicating the race list is loaded
    log_debug(f"Waiting for race button to appear (race list loading)...")
    race_btn = wait_for_image("assets/buttons/race_btn.png", timeout=10, region=get_template_region("assets/buttons/race_btn.png"))
    if not race_btn:
        log_debug(f"Race button not found after 10 seconds, race list may not have loaded")
        return False
    
    log_info(f"Race Select - Race list loaded, ready for selection")
    return True

def check_and_select_maiden_race():
    """Helper function to check for and select maiden races - eliminates duplicate code"""
    log_debug(f"Checking for maiden races...")
    maiden_races = locate_all_on_screen("assets/races/maiden.png", confidence=0.8)
    
    if maiden_races:
        log_info(f"Maiden Race - Found {len(maiden_races)} maiden race(s)!")
        
        # Sort by Y coordinate (highest Y = top of screen)
        maiden_races.sort(key=lambda x: x[1])  # Sort by Y coordinate
        
        # Select the topmost maiden race (highest Y coordinate)
        top_maiden = maiden_races[0]
        maiden_x, maiden_y, maiden_w, maiden_h = top_maiden
        maiden_center_x = maiden_x + maiden_w // 2
        maiden_center_y = maiden_y + maiden_h // 2
        
        log_info(f"Maiden Race - Selecting top maiden race at ({maiden_center_x}, {maiden_center_y})")
        log_debug(f"Tapping on maiden race...")
        
        tap(maiden_center_x, maiden_center_y)
        time.sleep(0.5)
        
        log_debug(f"Maiden race selected successfully!")
        return True
    
    log_debug(f"No maiden races found")
    return False

def find_and_do_race():
    """Find and execute race using intelligent race selection - replaces old do_race()"""
    log_info(f"Race Selection - Starting intelligent race selection...")
    
    try:
        # 1. Setup common environment
        year = check_current_year()
        if not year:
            log_warning(f"Race Selection - Could not detect current year")
            return False
        
        # 2. Load configuration and race data
        try:
            config = _load_config()
        except Exception as e:
            log_debug(f"Error loading config: {e}")
            return False
        
        try:
            project_root = _get_project_root()
            with open(os.path.join(project_root, "assets/races/clean_race_data.json"), "r", encoding="utf-8") as f:
                race_data = json.load(f)
        except Exception as e:
            log_debug(f"Error loading race data: {e}")
            return False
        
        if not race_data:
            log_debug(f"Failed to load race data")
            return False
        
        # 3. Choose best race based on database and config criteria
        # Check if goal contains G1 and override allowed grades if so
        training_config = config.get("training", {})
        skip_goal_check = training_config.get("skip_goal_check", False)
        if skip_goal_check:
            goal_name = ""
            log_info("Goal name check skipped by config")
        else:
            from core.Unity.state import check_goal_name
            goal_name = check_goal_name()
        
        # Override allowed grades if goal contains G1
        racing_config_section = config.get("racing", {})
        if goal_name and "G1" in goal_name:
            log_debug(f"Goal contains G1: '{goal_name}' - Overriding to only allow G1 races")
            allowed_grades = ["G1"]
        else:
            allowed_grades = racing_config_section.get("allowed_grades", ["G1", "G2", "G3", "OP", "PRE-OP"])
        
        allowed_tracks = racing_config_section.get("allowed_tracks", ["Turf", "Dirt"])
        allowed_distances = racing_config_section.get("allowed_distances", ["Sprint", "Mile", "Medium", "Long"])
        
        # Find best race using the existing logic
        best_race = None
        best_grade = None
        best_priority = 999
        best_fans = 0
        
        if year in race_data:
            for race_name, race_info in race_data[year].items():
                race_grade = race_info.get("grade", "UNKNOWN")
                race_surface = race_info.get("surface", "UNKNOWN")
                race_category = race_info.get("distance_type", "UNKNOWN")
                
                # Check if this grade is allowed
                if race_grade not in allowed_grades:
                    continue
                
                # Check if this track/surface is allowed
                if allowed_tracks and race_surface not in allowed_tracks:
                    continue
                
                # Check if this distance/category is allowed
                if allowed_distances and race_category not in allowed_distances:
                    continue
                
                # Get priority score for this grade
                priority = get_grade_priority(race_grade)
                fans = race_info.get("fans", 0)
                
                # Update best race if this one is better
                if priority < best_priority or (priority == best_priority and fans > best_fans):
                    best_race = race_name
                    best_grade = race_grade
                    best_priority = priority
                    best_fans = fans
        
        if not best_race:
            log_info(f"Race Selection - No suitable race found")
            return False
        
        log_info(f"Race Selection - Best race: {best_race} ({best_grade})")
        
        # 4. Enter race selection screen
        if not enter_race_selection_screen():
            return False
        
        # 5. Check for maiden races first (priority over database selection)
        log_debug(f"Checking for maiden races...")
        if check_and_select_maiden_race():
            log_info(f"Race Selection - Maiden race selected successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        log_debug(f"No maiden races found, proceeding with database selection...")
        
        # 6. Find and choose the selected race using OCR
        log_debug(f"Searching for selected race in Race Select Screen...")
        log_info(f"Race Selection - Searching for: {best_race}")
        
        # Get race description for OCR matching
        race_info = race_data[year][best_race]
        race_description = race_info.get("description", "")
        log_info(f"Race Selection - Description: {race_description}")
        
        # Search for race with swiping using the same logic as test file
        if search_race_with_swiping(race_description, year):
            log_info(f"Race Selection - Race selection completed successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        return False
        
    except Exception as e:
        log_debug(f"Error in find_and_do_race: {e}")
        return False

def do_custom_race(year_override=None):
    """Handle custom races from custom_races.json - bypasses all criteria checks
    
    Args:
        year_override: If provided, skip OCR year detection and use this value.
    """
    log_debug(f"Checking for custom race...")
    
    try:
        project_root = _get_project_root()
        # 1. Get current year (use override if provided)
        if year_override:
            year = year_override
        else:
            year = check_current_year()
            if not year:
                return False
        
        # 2. Load custom races data
        try:
            # Read config to get optional custom race file override
            cfg = _load_config()
            # config now stores custom race path under racing.custom_race_file
            custom_race_file = (
                cfg.get("racing", {}).get("custom_race_file")
                or cfg.get("custom_race_file")
                or "template/races/custom_races.json"
            )
            custom_race_path = _resolve_custom_race_path(custom_race_file, project_root)
            with open(custom_race_path, "r", encoding="utf-8") as f:
                custom_races = json.load(f)
        except Exception as e:
            log_debug(f"Failed to load custom races file: {e}")
            return False
        
        # 3. Check if there's a custom race for the current year
        if year not in custom_races:
            return False
        
        custom_race = custom_races[year]
        if not custom_race or custom_race.strip() == "":
            return False
        
        log_info(f"Custom Race - Custom race found for {year}: {custom_race}")
        
        # 4. Enter race selection screen
        if not enter_race_selection_screen():
            log_debug(f"Failed to enter race selection screen")
            return False
        
        # 5. Check for maiden races first (priority over custom race)
        log_debug(f"Checking for maiden races...")
        if check_and_select_maiden_race():
            log_info(f"Custom Race - Maiden race selected instead!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        log_debug(f"No maiden races found, proceeding with custom race...")
        
        # 6. Search for the custom race using OCR
        log_debug(f"Searching for custom race in Race Select Screen...")
        
        # Load race data to get the description for OCR matching
        try:
            project_root = _get_project_root()
            with open(os.path.join(project_root, "assets/races/clean_race_data.json"), "r", encoding="utf-8") as f:
                race_data = json.load(f)
        except Exception as e:
            log_debug(f"Error loading race data: {e}")
            race_data = {}
        
        if year in race_data and custom_race in race_data[year]:
            race_info = race_data[year][custom_race]
            race_description = race_info.get("description", "")
            log_debug(f"Race description: {race_description}")
        else:
            log_debug(f"Warning: Race '{custom_race}' not found in race database for {year}")
            log_debug(f"Will search by race name directly")
            race_description = custom_race
        
        # Search for race with swiping
        if search_race_with_swiping(race_description, year):
            log_info(f"Custom Race - Race selection completed successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        # If not found, try to navigate back to lobby to resume loop cleanly
        log_info(f"Custom Race - Race not found after search, navigating back to lobby")
        # Try tapping the back button image first; if not found, tap a likely back position
        if not tap_on_image("assets/buttons/back_btn.png", confidence=0.6, min_search=3, region=get_template_region("assets/buttons/back_btn.png")):
            # Fallback: common back coordinate in race selection
            tap(78, 138)
            time.sleep(0.5)
        return False
        
    except Exception as e:
        log_debug(f"Error in do_custom_race: {e}")
        return False


def _resolve_custom_race_path(path, project_root):
    """Resolve custom race file path, preferring files under races/."""
    if not path:
        path = "races/custom_races.json"
    if os.path.isabs(path):
        return path
    normalized = path.replace("\\", "/")
    candidates = [normalized]
    base_name = os.path.basename(normalized)
    if not normalized.startswith("template/races/"):
        candidates.append(os.path.join("template", "races", base_name))
    for candidate in candidates:
        candidate_abs = os.path.join(project_root, candidate)
        if os.path.exists(candidate_abs):
            return candidate_abs
    return os.path.join(project_root, candidates[-1])
