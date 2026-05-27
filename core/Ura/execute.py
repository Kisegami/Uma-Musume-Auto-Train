import time
import os
import random
import sys
import numpy as np
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

from utils.vision.recognizer import locate_on_screen, locate_all_on_screen, is_image_on_screen, match_template, max_match_confidence, match_templates_batch
from utils.inputs.input import tap, triple_click, long_press, tap_on_image
from utils.capture.screenshot import take_screenshot, enhanced_screenshot, capture_region
from utils.constants.ura import (
    MOOD_LIST, EVENT_REGION, RACE_CARD_REGION, SUPPORT_CARD_ICON_REGION
)

# Import ADB state and logic modules
from core.Ura.state import (
    check_mood, check_current_year, check_criteria, check_skill_points_cap,
    check_goal_name, check_current_stats, check_energy_bar,
    check_status_api, check_mood_api, check_current_year_api,
    check_current_stats_api, check_energy_api, check_skill_points_api,
    invalidate_status_cache, check_and_purchase_skills_before_custom_race,
)

# Import event handling functions
from core.Ura.event_handling import count_event_choices, load_event_priorities, analyze_event_options, handle_event_choice, click_event_choice

# Import training handling functions
from core.Ura.training_handling import go_to_training, check_training, do_train, check_support_card, check_failure, check_hint, choose_best_training, calculate_training_score, check_training_api

# Import race handling functions
from core.Ura.races_handling import (
    find_and_do_race, do_custom_race, race_day, check_strategy_before_race,
    change_strategy_before_race, race_prep, handle_race_retry_if_failed,
    after_race, is_racing_available, is_pre_debut_year, get_custom_race_selection
)

from utils.core.config_loader import load_main_config
config = load_main_config()
training_config_section = config.get("training", {})
racing_config_section = config.get("racing", {})
skills_config_section = config.get("skills", {})
DEBUG_MODE = config.get("debug_mode", False)
RETRY_RACE = racing_config_section.get("retry_race", config.get("retry_race", True))
_skip_infirmary_check_once = False


def should_skip_goal_check():
    """Return whether criteria/goal-name OCR checks should be skipped."""
    return config.get("training", {}).get("skip_goal_check", False)


def arm_skip_infirmary_check_for_new_turn():
    """Arm a one-shot skip for the infirmary check after starting a new career."""
    global _skip_infirmary_check_once
    training_config = load_main_config().get("training", {})
    if not training_config.get("skip_infirmary_check_on_new_turn", False):
        return

    _skip_infirmary_check_once = True
    log_info("Armed one-shot infirmary skip for the first turn of the new career")


def should_skip_infirmary_check_for_current_turn():
    """Return whether the infirmary check should be skipped for this lobby turn."""
    global _skip_infirmary_check_once
    training_config = load_main_config().get("training", {})
    if training_config.get("skip_infirmary_check_on_new_turn", False):
        log_info("Skipping infirmary check for this turn")
        _skip_infirmary_check_once = False
        return True

    if not _skip_infirmary_check_once:
        return False

    _skip_infirmary_check_once = False
    log_info("Skipping infirmary check for the first turn of the new career")
    return True

from utils.core.log import log_debug, log_info, log_warning, log_error, log_success
from utils.vision.template_matching import deduplicated_matches, wait_for_image
from utils.platform.device import reopen_and_resume_career
from utils.vision.ui_check import career_ui_check

WATCHDOG_MAX_RESTARTS = 3
WATCHDOG_CENTER_TAPS = 5
WATCHDOG_CENTER_TAP_INTERVAL = 0.4
_watchdog_restart_count = 0


def _watchdog_tap_center_recovery():
    """Try to advance an unrecognized post-resume screen before restarting."""
    log_warning(f"[Watchdog] Unrecognized career screen - tapping centre {WATCHDOG_CENTER_TAPS} times before restart.")
    for _ in range(WATCHDOG_CENTER_TAPS):
        tap(540, 960)
        time.sleep(WATCHDOG_CENTER_TAP_INTERVAL)


def _watchdog_restart_game(reason):
    """Restart the game from watchdog paths, stopping after too many restarts."""
    global _watchdog_restart_count
    _watchdog_restart_count += 1

    if _watchdog_restart_count > WATCHDOG_MAX_RESTARTS:
        log_error(
            f"[Watchdog] Restart triggered {_watchdog_restart_count} times "
            f"(limit {WATCHDOG_MAX_RESTARTS}) - stopping bot."
        )
        return False

    log_warning(
        f"[Watchdog] {reason} Restarting game "
        f"({_watchdog_restart_count}/{WATCHDOG_MAX_RESTARTS})..."
    )
    try:
        if not reopen_and_resume_career():
            log_error("[Watchdog] Reopen/resume failed - stopping bot.")
            return False
    except RuntimeError:
        raise
    except Exception as exc:
        log_error(f"[Watchdog] Reopen failed: {exc}")
        return False
    return True

try:
    from utils.integrations.umat_api import is_api_enabled
    _API_MODE = is_api_enabled()
except ImportError:
    _API_MODE = False

def is_infirmary_active_adb(button_location, screenshot=None):
    """
    Check if the infirmary button is active (bright) or disabled (dark).
    Args:
        button_location: tuple (x, y, w, h) of the button location
        screenshot: Optional PIL Image. If None, takes a new screenshot.
    Returns:
        bool: True if button is active (bright), False if disabled (dark)
    """
    try:
        x, y, w, h = button_location
        
        # Use provided screenshot or take new one if not provided
        if screenshot is None:
            from utils.capture.screenshot import take_screenshot
            screenshot = take_screenshot()
        
        # Crop the button region from the screenshot
        button_region = screenshot.crop((x, y, x + w, y + h))
        
        # Convert to grayscale and calculate average brightness
        grayscale = button_region.convert("L")
        stat = ImageStat.Stat(grayscale)
        avg_brightness = stat.mean[0]
        
        # Threshold for active button (same as PC version)
        is_active = avg_brightness > 170
        log_debug(f"Infirmary brightness: {avg_brightness:.1f} ({'active' if is_active else 'disabled'})")
        
        return is_active
    except Exception as e:
        log_error(f"Failed to check infirmary button brightness: {e}")
        return False

def claw_machine():
    """Handle claw machine interaction"""
    log_info(f"Claw machine detected, starting interaction...")
    
    # Wait 2 seconds before interacting
    time.sleep(1)
    
    # Find the claw button location
    claw_location = locate_on_screen("assets/buttons/claw.png", confidence=0.8)
    if not claw_location:
        log_warning(f"Claw button not found for interaction")
        return False
    
    # Get center coordinates (locate_on_screen returns center coordinates)
    center_x, center_y = claw_location
    
    # Generate random hold duration between 3-4 seconds (in milliseconds)
    hold_duration = random.randint(1000, 3000)
    log_info(f"Holding claw button for {hold_duration}ms...")
    
    # Use ADB long press to hold the claw button
    long_press(center_x, center_y, hold_duration)
    
    log_info(f"Claw machine interaction completed")
    return True

def do_rest():
    """Perform rest action"""
    log_debug(f"Performing rest action...")
    log_info(f"Performing rest action...")
    
    # Rest button is in the lobby, not on training screen
    # If we're on training screen, go back to lobby first
    from utils.vision.recognizer import locate_on_screen
    back_btn = locate_on_screen("assets/buttons/back_btn.png", confidence=0.8)
    if back_btn:
        log_debug(f"Going back to lobby to find rest button...")
        log_info(f"Going back to lobby to find rest button...")
        from utils.inputs.input import tap
        tap(back_btn[0], back_btn[1])
        time.sleep(1.0)  # Wait for lobby to load
    tazuna_hint = locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.9)
    if not tazuna_hint:
        log_debug(f"tazuna_hint.png not found, taking screenshot again to ensure we are in the lobby...")
        time.sleep(0.7)
        # Take a new screenshot and try again
        from utils.capture.screenshot import take_screenshot
        take_screenshot()
        tazuna_hint = locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.9)
        if not tazuna_hint:
            log_warning(f"Still not in lobby after retrying screenshot. Rest button search may fail.")
    # Now look for rest buttons in the lobby
    rest_btn = locate_on_screen("assets/buttons/rest_btn.png", confidence=0.5)
    rest_summer_btn = locate_on_screen("assets/buttons/rest_summer_btn.png", confidence=0.5)
    
    log_debug(f"Rest button found: {rest_btn}")
    log_debug(f"Summer rest button found: {rest_summer_btn}")
    
    if rest_btn:
        log_debug(f"Clicking rest button at {rest_btn}")
        log_info(f"Clicking rest button at {rest_btn}")
        from utils.inputs.input import tap
        tap(rest_btn[0], rest_btn[1])
        log_debug(f"Clicked rest button")
        log_info(f"Rest button clicked")
    elif rest_summer_btn:
        log_debug(f"Clicking summer rest button at {rest_summer_btn}")
        log_info(f"Clicking summer rest button at {rest_summer_btn}")
        from utils.inputs.input import tap
        tap(rest_summer_btn[0], rest_summer_btn[1])
        log_debug(f"Clicked summer rest button")
        log_info(f"Summer rest button clicked")
    else:
        log_debug(f"No rest button found in lobby")
        log_warning(f"No rest button found in lobby")
    time.sleep(3)

def do_recreation():
    """Perform recreation action"""
    log_debug(f"Performing recreation action...")
    recreation_btn = locate_on_screen("assets/buttons/recreation_btn.png", confidence=0.8)
    recreation_summer_btn = locate_on_screen("assets/buttons/rest_summer_btn.png", confidence=0.8)
    
    if recreation_btn:
        log_debug(f"Found recreation button at {recreation_btn}")
        tap(recreation_btn[0], recreation_btn[1])
        log_debug(f"Clicked recreation button")
    elif recreation_summer_btn:
        log_debug(f"Found summer recreation button at {recreation_summer_btn}")
        tap(recreation_summer_btn[0], recreation_summer_btn[1])
        log_debug(f"Clicked summer recreation button")
    else:
        log_debug(f"No recreation button found")

def career_lobby(timeout=None):
    """Main career lobby loop
    Args:
        timeout: Optional timeout in seconds. If set, the loop exits after
                 this duration instead of running forever. Used by ui_check().
    """
    # Use existing config loaded at module level
    MINIMUM_MOOD = training_config_section.get("minimum_mood", config.get("minimum_mood", "GREAT"))
    # Track last day we attempted a custom race but failed, to avoid re-checking within same day
    last_failed_custom_race_day = None

    # ── Lobby-stuck watchdog ──────────────────────────────────────────────
    # Tracks time spent spinning while NOT in lobby. Starts at the first
    # tazuna_hint check, resets the moment the lobby is confirmed.
    LOBBY_STUCK_TIMEOUT = 30  # seconds; purely lobby-wait time
    _lobby_wait_start = None  # None = not currently waiting for lobby
    _waiting_for_lobby_logged = False
    # ─────────────────────────────────────────────────────────────────────

    # ── Freeze detection (identical-screenshot watchdog) ─────────────────
    FREEZE_SAME_THRESHOLD = 10  # consecutive identical frames → frozen
    _prev_screenshot = None
    _freeze_same_count = 0
    FREEZE_MIN_DURATION = 12.0  # identical frames must persist this long before restart
    _freeze_same_since = None
    # ─────────────────────────────────────────────────────────────────────

    # Timeout support for bounded checks (e.g. from ui_check)
    _timeout_start = time.time() if timeout else None

    # Program start
    while True:
        # Check timeout if set
        if _timeout_start and (time.time() - _timeout_start) > timeout:
            log_info(f"Career lobby timeout reached ({timeout}s), returning to caller")
            return True
        log_debug(f"\n===== Starting new loop iteration =====")
        
        # Take screenshot first for all checks
        log_debug(f"Taking screenshot for UI element checks...")
        screenshot = take_screenshot()

        # ── Freeze detection: compare with previous screenshot ────────
        if _prev_screenshot is not None:
            try:
                diff = np.mean(np.abs(
                    np.array(screenshot).astype(np.int16)
                    - np.array(_prev_screenshot).astype(np.int16)
                ))
                if diff < 0.5:  # effectively identical
                    _freeze_same_count += 1
                    if _freeze_same_since is None:
                        _freeze_same_since = time.time()
                    log_debug(f"[Watchdog] Identical frame #{_freeze_same_count}/{FREEZE_SAME_THRESHOLD}")
                    frozen_for = time.time() - _freeze_same_since
                    if _freeze_same_count >= FREEZE_SAME_THRESHOLD and frozen_for >= FREEZE_MIN_DURATION:
                        if not _watchdog_restart_game(
                            f"Screen frozen for {_freeze_same_count} consecutive frames."
                        ):
                            return False
                        _freeze_same_count = 0
                        _freeze_same_since = None
                        _prev_screenshot = None
                        _lobby_wait_start = None
                        continue
                else:
                    _freeze_same_count = 0
                    _freeze_same_since = None
            except Exception as _cmp_err:
                log_debug(f"[Watchdog] Screenshot comparison failed: {_cmp_err}")
                _freeze_same_count = 0
                _freeze_same_since = None
        _prev_screenshot = screenshot.copy()
        # ──────────────────────────────────────────────────────────────
        
        # ── Batch pre-lobby UI checks ─────────────────────────────────
        # Match ALL interrupt/navigation templates in ONE pass:
        # single screenshot→CV conversion, cached template loading
        log_debug(f"Performing batch UI element check...")
        lobby_template_specs = [
            ("assets/buttons/complete_career.png", 0.8, None),
            ("assets/buttons/claw.png", 0.8, None),
            ("assets/buttons/ok_btn.png", 0.8, None),
            ("assets/icons/event_choice_1.png", 0.7, (6, 450, 126, 1776)),
            ("assets/buttons/inspiration_btn.png", 0.5, None),
            ("assets/buttons/cancel_lobby.png", 0.8, None),
            ("assets/buttons/close.png", 0.8, None),
            ("assets/buttons/next_btn.png", 0.8, None),
            ("assets/ui/tazuna_hint.png", 0.9, None),
            ("assets/buttons/back_btn.png", 0.8, None),
        ]
        batch_results = match_templates_batch(screenshot, lobby_template_specs)
        # ──────────────────────────────────────────────────────────────

        # 1. Check for career restart (highest priority)
        log_debug(f"Quick check for Complete Career screen...")
        try:
            complete_career_matches = batch_results["assets/buttons/complete_career.png"]
            if complete_career_matches:
                log_info(f"Complete Career screen detected - starting restart workflow")
                from core.Ura.restart_career import career_lobby_check
                should_continue = career_lobby_check(screenshot)
                if not should_continue:
                    log_info(f"Career restart workflow completed - stopping bot")
                    return False
        except Exception as e:
            log_error(f"Career restart check failed: {e}")

        # 2. Check claw machine
        log_debug(f"Checking for claw machine...")
        claw_matches = batch_results["assets/buttons/claw.png"]
        if claw_matches:
            _lobby_wait_start = None
            claw_machine()
            continue

        # 3. Check OK button
        log_debug(f"Checking for OK button...")
        ok_matches = batch_results["assets/buttons/ok_btn.png"]
        if ok_matches:
            x, y, w, h = ok_matches[0]
            center = (x + w//2, y + h//2)
            log_info(f"OK button found, clicking it.")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # 4. Check for events
        log_debug(f"Checking for events...")
        try:
            event_matches = batch_results["assets/icons/event_choice_1.png"]

            if event_matches:
                log_info(f"Event detected, analyzing choices...")
                choice_number, success, choice_locations = handle_event_choice()
                if success:
                    click_success = click_event_choice(choice_number, choice_locations)
                    if click_success:
                        log_info(f"Successfully selected choice {choice_number}")
                        time.sleep(0.5)
                        _lobby_wait_start = None
                        continue
                    else:
                        log_warning(f"Failed to click event choice, falling back to top choice")
                        x, y, w, h = event_matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
                        _lobby_wait_start = None
                        continue
                else:
                    if not choice_locations:
                        log_debug(f"Skipping event click due to no visible choices after stabilization")
                        _lobby_wait_start = None
                        continue
                    log_warning(f"Event analysis failed, falling back to top choice")
                    x, y, w, h = event_matches[0]
                    center = (x + w//2, y + h//2)
                    tap(center[0], center[1])
                    _lobby_wait_start = None
                    continue
            else:
                log_debug(f"No events found")
        except RuntimeError as e:
            if "Event detection failed" in str(e):
                raise
            log_error(f"Event handling error: {e}")
        except Exception as e:
            log_error(f"Event handling error: {e}")

        # 5. Check inspiration button
        log_debug(f"Checking for inspiration...")
        inspiration_matches = batch_results["assets/buttons/inspiration_btn.png"]
        if inspiration_matches:
            x, y, w, h = inspiration_matches[0]
            center = (x + w//2, y + h//2)
            log_info(f"Inspiration found.")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # 6. Check cancel button
        log_debug(f"Checking for cancel button...")
        cancel_matches = batch_results["assets/buttons/cancel_lobby.png"]
        if cancel_matches:
            x, y, w, h = cancel_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking cancel_btn.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # 7. Check close button
        log_debug(f"Checking for close button...")
        close_matches = batch_results["assets/buttons/close.png"]
        if close_matches:
            x, y, w, h = close_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking close.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # 8. Check next button
        log_debug(f"Checking for next button...")
        next_matches = batch_results["assets/buttons/next_btn.png"]
        if next_matches:
            x, y, w, h = next_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking next_btn.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # 9. Check if in career lobby (no extra screenshot needed now)
        log_debug(f"Checking if in career lobby...")
        tazuna_hint = batch_results["assets/ui/tazuna_hint.png"]

        if not tazuna_hint:
            back_btn_matches = batch_results["assets/buttons/back_btn.png"]
            if back_btn_matches:
                x, y, w, h = back_btn_matches[0]
                center = (x + w//2, y + h//2)
                log_info(f"Back button found, tapping to return to lobby...")
                tap(center[0], center[1])
                _lobby_wait_start = None
                time.sleep(0.5)
                continue

            # ── Watchdog: start / check lobby-wait timer ──────────────────
            if _lobby_wait_start is None:
                _lobby_wait_start = time.time()
                _freeze_same_count = 0
                _freeze_same_since = None
                log_debug(f"[Watchdog] Lobby wait timer started.")
            elif time.time() - _lobby_wait_start > LOBBY_STUCK_TIMEOUT:
                log_warning(f"[Watchdog] Stuck waiting for lobby >{LOBBY_STUCK_TIMEOUT}s — attempting career_ui_check before restart...")
                _recovered = False
                for _ui_attempt in range(3):
                    log_info(f"[Watchdog] Running career_ui_check - Attempt {_ui_attempt + 1}/3...")
                    try:
                        if career_ui_check():
                            log_info(f"[Watchdog] career_ui_check recovered on attempt {_ui_attempt + 1}")
                            _recovered = True
                            break
                    except RuntimeError:
                        raise  # Bot-stop signals must propagate
                    except Exception as _uce:
                        log_warning(f"[Watchdog] career_ui_check attempt {_ui_attempt + 1} failed: {_uce}")
                    time.sleep(1)
                if not _recovered:
                    _watchdog_tap_center_recovery()
                    for _ui_attempt in range(3):
                        log_info(f"[Watchdog] Re-running career_ui_check after centre taps - Attempt {_ui_attempt + 1}/3...")
                        try:
                            if career_ui_check():
                                log_info(f"[Watchdog] Centre-tap recovery succeeded on attempt {_ui_attempt + 1}")
                                _recovered = True
                                break
                        except RuntimeError:
                            raise
                        except Exception as _uce:
                            log_warning(f"[Watchdog] post-tap career_ui_check attempt {_ui_attempt + 1} failed: {_uce}")
                        time.sleep(1)
                if not _recovered:
                    if not _watchdog_restart_game("career_ui_check failed after centre-tap recovery."):
                        return False
                _lobby_wait_start = None
                _freeze_same_count = 0
                _freeze_same_since = None
            # ─────────────────────────────────────────────────────────────
            if not _waiting_for_lobby_logged:
                log_info(f"Waiting for Career lobby")
                _waiting_for_lobby_logged = True
            continue

        # Lobby confirmed — reset watchdog timer
        _lobby_wait_start = None
        _waiting_for_lobby_logged = False
        _freeze_same_count = 0
        _freeze_same_since = None
        log_debug(f"Confirmed in career lobby")
        time.sleep(0.5)
        # Take a fresh screenshot after confirming lobby to ensure stable UI state
        log_debug(f"Taking fresh screenshot after lobby confirmation...")
        screenshot = take_screenshot()

        invalidate_status_cache()

        # Check if there is debuff status
        log_debug(f"Checking for debuff status...")
        if should_skip_infirmary_check_for_current_turn():
            log_debug("Skipping infirmary detection on this lobby turn")
        else:
            # Use match_template to get full bounding box for brightness check
            infirmary_matches = match_template(screenshot, "assets/buttons/infirmary_btn2.png", confidence=0.9)

            if infirmary_matches:
                debuffed_box = infirmary_matches[0]  # Get first match (x, y, w, h)
                x, y, w, h = debuffed_box
                center_x, center_y = x + w//2, y + h//2

                # Check if the button is actually active (bright) or just disabled (dark)
                if is_infirmary_active_adb(debuffed_box, screenshot):
                    tap(center_x, center_y)
                    log_info(f"Character has debuff, go to infirmary instead.")
                    continue
                else:
                    log_debug(f"Infirmary button found but is disabled (dark)")
            else:
                log_debug(f"No infirmary button detected")

        # Get current state
        log_debug(f"Getting current game state...")
        skip_goal_check = should_skip_goal_check()
        if _API_MODE:
            api_status = check_status_api()
            if api_status is None:
                log_error("API mode is enabled but failed to get status from /status")
                raise RuntimeError("API mode is enabled but /status API is not responding. Check API connection or set api.enabled to false in config.json.")
            mood = api_status["mood"]
            year = api_status["year"]
            current_stats = api_status["stats"]
            energy_percentage = api_status["energy_pct"]
            if skip_goal_check:
                goal_data = "Skipped"
                criteria_text = "Skipped"
            else:
                goal_data = check_goal_name(screenshot)
                criteria_text = check_criteria(screenshot)
        else:
            api_status = None
            mood = check_mood(screenshot)
            year = check_current_year(screenshot)
            if skip_goal_check:
                goal_data = "Skipped"
                criteria_text = "Skipped"
            else:
                goal_data = check_goal_name(screenshot)
                criteria_text = check_criteria(screenshot)

        mood_index = MOOD_LIST.index(mood) if mood in MOOD_LIST else 0
        minimum_mood = MOOD_LIST.index(MINIMUM_MOOD)

        race_day_matches = match_template(screenshot, "assets/buttons/race_day_btn.png", confidence=0.8)
        is_race_day = bool(race_day_matches)
        ura_finale_race_matches = match_template(screenshot, "assets/buttons/race_ura.png", confidence=0.8)
        is_ura_finale_race = bool(ura_finale_race_matches) and year == "Finale Underway"
        
        log_info(f"=== GAME STATUS{' (API)' if api_status else ''} ===")
        log_info(f"Year: {year}")
        log_info(f"Mood: {mood}")
        log_info(f"Goal Name: {goal_data}")
        log_info(f"Status: {criteria_text}")

        # Check for maiden (2-star) race opportunity in career lobby
        # Only check if year is not Pre-Debut
        if not is_pre_debut_year(year):
            log_debug(f"Checking for maiden race icon in lobby...")
            # Check for maiden_lobby.png in specific region (x=0, y=1123, width=378, height=111)
            maiden_lobby_region = (0, 1123, 378, 111)
            maiden_lobby_matches = match_template(screenshot, "assets/icons/maiden_lobby.png", confidence=0.8, region=maiden_lobby_region)
            
            if maiden_lobby_matches:
                log_info(f"Maiden race icon found in lobby! Checking for 2-star races...")
                
                # Navigate to race menu
                if tap_on_image("assets/buttons/races_btn.png", min_search=10):
                    time.sleep(0.5)
                    # Handle OK button if it appears
                    tap_on_image("assets/buttons/ok_btn.png", confidence=0.5, min_search=2)
                    time.sleep(0.5)
                    
                    # Take fresh screenshot to check for 2-star race
                    race_screenshot = take_screenshot()
                    two_star_matches = match_template(race_screenshot, "assets/races/2_star_race.png", confidence=0.8)
                    
                    if two_star_matches:
                        log_info(f"2-star race found! Tapping to select...")
                        x, y, w, h = two_star_matches[0]
                        center_x, center_y = x + w//2, y + h//2
                        tap(center_x, center_y)
                        time.sleep(0.5)
                        
                        # Execute the race after selection
                        from core.Ura.races_handling import execute_race_after_selection
                        if execute_race_after_selection():
                            log_info(f"2-star race completed successfully!")
                            continue
                    else:
                        log_debug(f"No 2-star race found, tapping back to continue normally...")
                        tap_on_image("assets/buttons/back_btn.png", confidence=0.8, min_search=5)
                        time.sleep(0.5)
            else:
                log_debug(f"No maiden race icon in lobby")

        log_debug(f"Mood index: {mood_index}, Minimum mood index: {minimum_mood}")
        
        # Check energy bar before proceeding with training decisions
        if not api_status:
            log_debug(f"Checking energy bar...")
            energy_percentage = check_energy_bar(screenshot)
        min_energy = training_config_section.get("min_energy", config.get("min_energy", 30))
        log_info(f"Energy: {energy_percentage:.1f}% (Minimum: {min_energy}%)")
        # Check for rest in June to save energy for summer (skip on race day)
        rest_in_june_enabled = training_config_section.get("rest_in_june", False)
        if rest_in_june_enabled and "Jun" in year and "Junior" not in year and energy_percentage <= 60 and not is_race_day and not is_ura_finale_race:
            log_info(f"Rest in June enabled - Energy <= 60%. Going to rest to save energy for summer.")
            do_rest()
            continue
        
        # Get current stats
        if not api_status:
            current_stats = {}
            try:
                current_stats = check_current_stats(screenshot)
            except Exception as e:
                log_debug(f"Could not get current stats: {e}")
        stats_str = f"SPD: {current_stats.get('spd', 0)}, STA: {current_stats.get('sta', 0)}, PWR: {current_stats.get('pwr', 0)}, GUTS: {current_stats.get('guts', 0)}, WIT: {current_stats.get('wit', 0)}" if current_stats else "N/A"
        
        log_info(f"Current stats: {stats_str}")
        log_info(f"")
        
        # Check if goals criteria are NOT met AND it is not Pre-Debut.
        # Prioritize racing when criteria are not met to help achieve goals.
        log_debug(f"Checking goal criteria...")
        if skip_goal_check:
            goal_analysis = {
                "criteria_met": True,
                "is_pre_debut": is_pre_debut_year(year),
                "should_prioritize_racing": False,
            }
            log_info("Goal criteria check skipped by config")
        else:
            goal_analysis = check_goal_criteria({"text": criteria_text}, year)
        
        if goal_analysis["should_prioritize_racing"]:
            log_info(f"Decision: Criteria not met - Prioritizing races to meet goals")
            race_found = find_and_do_race(year)
            if race_found:
                log_info(f"Race Result: Found Race")
                continue
            else:
                log_info(f"Race Result: No Race Found")
                # If there is no race found, go back and do training instead
                tap_on_image("assets/buttons/back_btn.png", text="[INFO] Race not found. Proceeding to training.")
                time.sleep(0.5)
        else:
            log_info(f"Decision: Criteria met or conditions not suitable for racing")
            log_debug(f"Racing not prioritized - Criteria met: {goal_analysis['criteria_met']}, Pre-debut: {goal_analysis['is_pre_debut']}")
        
        log_info(f"")

        # URA SCENARIO
        log_debug(f"Checking for URA scenario...")
        if is_ura_finale_race:
            log_info(f"URA Finale")
            
            # Check skill points cap before URA race day (if enabled)
            enable_skill_check = skills_config_section.get("enable_skill_point_check", config.get("enable_skill_point_check", True))
            
            if enable_skill_check:
                log_info(f"URA Finale Race Day - Checking skill points cap...")
                check_skill_points_cap(screenshot)
            
            # URA race logic would go here
            log_debug(f"Starting URA race...")
            if tap_on_image("assets/buttons/race_ura.png", min_search=10):
                time.sleep(0.5)
                # Click race button 2 times after entering race menu
                for i in range(2):
                    if tap_on_image("assets/buttons/race_btn.png", min_search=2):
                        log_debug(f"Successfully clicked race button {i+1}/2")
                        time.sleep(0.5)
                    else:
                        log_debug(f"Race button not found on attempt {i+1}/2")
            
            race_prep()
            # time.sleep(1)
            # If race failed screen appears, handle retry before proceeding
            handle_race_retry_if_failed()
            after_race()
            continue
        else:
            log_debug(f"Not URA scenario")

        # If calendar is race day, do race
        log_debug(f"Checking for race day...")
        if is_race_day and year != "Finale Underway":
            log_info(f"Race Day.")
            race_day()
            continue
        else:
            log_debug(f"Not race day")

        # Check for custom race (bypasses all criteria) - only if enabled in config
        log_debug(f"Checking if custom race is enabled...")
        do_custom_race_enabled = racing_config_section.get("do_custom_race", config.get("do_custom_race", False))
        
        if do_custom_race_enabled:
            # Build a stable key for the current day without relying on turn OCR.
            day_key = f"{year}|{goal_data}|{criteria_text}"
            if last_failed_custom_race_day == day_key:
                log_debug(f"Skipping custom race check (already attempted and failed this day)")
            else:
                custom_race_selection = get_custom_race_selection(year)
                if custom_race_selection and custom_race_selection.get("race"):
                    if check_and_purchase_skills_before_custom_race(screenshot):
                        invalidate_status_cache()
                        screenshot = take_screenshot()
                log_debug(f"Custom race is enabled, checking for custom race...")
                custom_race_found = do_custom_race(year)
                if custom_race_found:
                    # Reset failure cache on success
                    last_failed_custom_race_day = None
                    log_info(f"Custom race executed successfully")
                    continue
                else:
                    log_debug(f"No custom race found or executed")
                    # Remember that we failed this day to avoid re-checking until day changes
                    last_failed_custom_race_day = day_key
        else:
            log_debug(f"Custom race is disabled in config")

        # Mood check
        log_debug(f"Checking mood...")
        if mood_index < minimum_mood:
            # Check if energy is too high (>90%) before doing recreation
            if energy_percentage > 90:
                log_debug(f"Mood too low ({mood_index} < {minimum_mood}) but energy too high ({energy_percentage:.1f}% > 90%), skipping recreation")
                log_info(f"Mood is low but energy is too high ({energy_percentage:.1f}% > 90%), skipping recreation")
            else:
                log_debug(f"Mood too low ({mood_index} < {minimum_mood}), doing recreation")
                log_info(f"Mood is low, trying recreation to increase mood")
                do_recreation()
                continue
        else:
            log_debug(f"Mood is good ({mood_index} >= {minimum_mood})")

        # Check training button
        log_debug(f"Going to training...")
        
        # Check energy before proceeding with training
        if energy_percentage < min_energy:
            log_warning(f"Energy too low ({energy_percentage:.1f}% < {min_energy}%), skipping training and going to rest")
            do_rest()
            continue
            
        _on_training_screen = False
        if _API_MODE:
            results_training = check_training_api(year=year, current_stats=current_stats)
            if results_training is None:
                log_error("API mode is enabled but failed to get training data from /training")
                raise RuntimeError("API mode is enabled but /training API is not responding. Check API connection or set api.enabled to false in config.json.")
            log_info(f"[API] Training data from API (no screen navigation needed)")
        else:
            if not go_to_training():
                log_warning("Training button is not found.")
                continue

            # Last, do training
            log_debug(f"Analyzing training options...")
            time.sleep(0.5)
            results_training = check_training(go_back=False, year=year, current_stats=current_stats)
            _on_training_screen = True
        
        log_debug(f"Deciding best training action using scoring algorithm...")
        
        # Use existing config for scoring thresholds
        min_score_config = training_config_section.get("min_score", config.get("min_score", {}))
        
        # Handle backward compatibility: if min_score is a number, convert to dict
        if isinstance(min_score_config, (int, float)):
            default_score = min_score_config
            min_score_config = {
                "spd": default_score,
                "sta": default_score,
                "pwr": default_score,
                "guts": default_score,
                "wit": default_score
            }
            # Check for legacy min_wit_score
            min_wit_score = config.get("min_wit_score", None)
            if min_wit_score is not None:
                min_score_config["wit"] = min_wit_score
        
        # Ensure all stats have a default value
        default_min_score = 1.0
        min_score_config = {
            "spd": min_score_config.get("spd", default_min_score),
            "sta": min_score_config.get("sta", default_min_score),
            "pwr": min_score_config.get("pwr", default_min_score),
            "guts": min_score_config.get("guts", default_min_score),
            "wit": min_score_config.get("wit", default_min_score)
        }
        
        training_config = {
            "maximum_failure": training_config_section.get("maximum_failure", config.get("maximum_failure", 15)),
            "min_score": min_score_config,
            "priority_stat": training_config_section.get("priority_stat", config.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])),
            "gambling_train_enabled": training_config_section.get("gambling_train_enabled", False),
            "gambling_train_failure_increase": training_config_section.get("gambling_train_failure_increase", 5),
            "gambling_train_score_per_increase": training_config_section.get("gambling_train_score_per_increase", 1.0)
        }

        do_race_when_bad_training_flag = training_config_section.get("do_race_when_bad_training", config.get("do_race_when_bad_training", True))
        
        # Use new scoring algorithm to choose best training (with stat cap filtering)
        log_debug(f"Choosing best training with stat cap filtering. Current stats: {current_stats}")
        best_training = choose_best_training(results_training, training_config, current_stats, year=year)
        
        if best_training:
            log_debug(f"Scoring algorithm selected: {best_training.upper()} training")
            log_info(f"Selected {best_training.upper()} training based on scoring algorithm")
            if not _on_training_screen:
                if not go_to_training():
                    log_warning("Training button not found after API check.")
                    continue
            do_train(best_training, already_on_training_screen=True)
        else:
            log_debug(f"No suitable training found based on scoring criteria")
            log_info(f"No suitable training found based on scoring criteria.")
            
            # Check if we should prioritize racing when no good training is available
            do_race_when_bad_training = do_race_when_bad_training_flag
            
            if do_race_when_bad_training:
                # Check if all training options have failure rates above maximum
                from core.Ura.logic import all_training_unsafe
                max_failure = training_config.get('maximum_failure', 15)
                log_debug(f"Checking if all training options have failure rate > {max_failure}%")
                log_debug(f"Training results: {[(k, v['failure']) for k, v in results_training.items()]}")
                
                if all_training_unsafe(results_training, max_failure):
                    log_debug(f"All training options have failure rate > {max_failure}%")
                    # If all trainings are unsafe AND wit score is low, rest; otherwise try a relaxed training
                    wit_score = results_training.get('wit', {}).get('score', 0)
                    if wit_score < 1.0:
                        log_info(f"All training options unsafe and WIT score < 1.0. Choosing to rest.")
                        if _on_training_screen:
                            tap_on_image("assets/buttons/back_btn.png")
                            time.sleep(0.3)
                        do_rest()
                        continue
                    else:
                        # Try to pick a training with relaxed thresholds despite high failure context
                        relaxed_config = dict(training_config)
                        relaxed_config['min_score'] = {
                            "spd": 0.0,
                            "sta": 0.0,
                            "pwr": 0.0,
                            "guts": 0.0,
                            "wit": 0.0
                        }
                        fallback_training = choose_best_training(results_training, relaxed_config, current_stats, year=year)
                        if fallback_training:
                            log_info(f"Proceeding with training ({fallback_training.upper()}) despite poor options (relaxed selection)")
                            if not _on_training_screen:
                                if not go_to_training():
                                    log_warning("Could not navigate to training screen for relaxed training.")
                                    continue
                            do_train(fallback_training)
                            continue
                        else:
                            log_info(f"No viable training even after relaxed selection. Choosing to rest.")
                            if _on_training_screen:
                                tap_on_image("assets/buttons/back_btn.png")
                                time.sleep(0.3)
                            do_rest()
                            continue
                else:
                    # Check if racing is available (no races in July/August)
                    if not is_racing_available(year):
                        log_debug(f"Racing not available (summer break)")
                        log_info(f"July/August detected. No races available during summer break. Trying training instead.")
                        # Try training with relaxed thresholds
                        relaxed_config = dict(training_config)
                        relaxed_config['min_score'] = {
                            "spd": 0.0,
                            "sta": 0.0,
                            "pwr": 0.0,
                            "guts": 0.0,
                            "wit": 0.0
                        }
                        fallback_training = choose_best_training(results_training, relaxed_config, current_stats, year=year)
                        if fallback_training:
                            log_info(f"Proceeding with training ({fallback_training.upper()}) due to no races")
                            if not _on_training_screen:
                                if not go_to_training():
                                    log_warning("Could not navigate to training screen.")
                                    continue
                            do_train(fallback_training)
                            continue
                        else:
                            # If even relaxed cannot find, decide rest only if WIT score < 1.0, else do_rest as last resort
                            wit_score = results_training.get('wit', {}).get('score', 0)
                            if _on_training_screen:
                                tap_on_image("assets/buttons/back_btn.png")
                                time.sleep(0.3)
                            if wit_score < 1.0:
                                log_info(f"No viable training after relaxation and no races. Choosing to rest.")
                                do_rest()
                            else:
                                log_info(f"No training selected after relaxation. Choosing to rest.")
                                do_rest()
                        
                    else:
                        log_info(f"Prioritizing race due to insufficient training scores.")
                        log_info(f"Training Race Check: Checking database for available races...")
                        
                        # Check database while still on training screen (no navigation)
                        from core.Ura.races_handling import check_race_in_database
                        race_available = check_race_in_database(year)
                        
                        if race_available:
                            log_info(f"Good race found in database. Going back to lobby to do race.")
                            # Go back to lobby and do the race
                            if _on_training_screen:
                                tap_on_image("assets/buttons/back_btn.png", text="[INFO] Going back to lobby to search for race...")
                                time.sleep(0.5)
                            race_found = find_and_do_race(year)
                            if race_found:
                                log_info(f"Training Race Result: Race executed successfully")
                                continue
                            else:
                                log_info(f"Training Race Result: Race execution failed")
                                # Go back to training and use relaxed config
                                if not go_to_training():
                                    log_warning("Could not return to training screen. Choosing to rest.")
                                    do_rest()
                                    continue
                                _on_training_screen = True
                        else:
                            log_info(f"No good race found in database.")
                        
                        # No race available - check energy to decide next action
                        # We're still on training screen
                        if energy_percentage >= 50:
                            log_info(f"Energy is {energy_percentage:.1f}% (>= 50%). Using relaxed scoring to train.")
                            relaxed_config = dict(training_config)
                            relaxed_config['min_score'] = {
                                "spd": 0.0,
                                "sta": 0.0,
                                "pwr": 0.0,
                                "guts": 0.0,
                                "wit": 0.0
                            }
                            relaxed_training = choose_best_training(results_training, relaxed_config, current_stats, year=year)
                            if relaxed_training:
                                log_info(f"Proceeding with training ({relaxed_training.upper()}) using relaxed scoring")
                                if not _on_training_screen:
                                    if not go_to_training():
                                        log_warning("Could not navigate to training screen.")
                                        continue
                                do_train(relaxed_training, already_on_training_screen=True)
                                continue
                            else:
                                log_info(f"No training found even with relaxed scoring. Going back to rest.")
                                if _on_training_screen:
                                    tap_on_image("assets/buttons/back_btn.png")
                                    time.sleep(0.3)
                                do_rest()
                        else:
                            log_info(f"Energy is {energy_percentage:.1f}% (< 50%). Going back to lobby to rest.")
                            if _on_training_screen:
                                tap_on_image("assets/buttons/back_btn.png")
                                time.sleep(0.3)
                            do_rest()
            else:
                # Race prioritization disabled: if no training was chosen here, rest
                # (min_score and failure thresholds are still enforced)
                log_info(f"Race prioritization disabled and no valid training found. Choosing to rest.")
                if _on_training_screen:
                    tap_on_image("assets/buttons/back_btn.png")
                    time.sleep(0.3)
                do_rest()
        
        log_debug(f"Starting next iteration immediately...")

def check_goal_criteria(criteria_data, year):
    """
    Check if goal criteria are met and determine if racing should be prioritized.
    
    Args:
        criteria_data (dict): The criteria data from OCR with text
        year (str): Current year text
    Returns:
        dict: Dictionary containing criteria analysis and decision
    """
    # Extract criteria text
    criteria_text = criteria_data.get("text", "")
    
    # Check if goals criteria are met
    criteria_met = (criteria_text.split(" ")[0] == "criteria" or 
                    "criteria met" in criteria_text.lower() or 
                    "goal achieved" in criteria_text.lower())
    
    # Check if it's pre-debut year
    is_pre_debut = is_pre_debut_year(year)
    
    # Determine if racing should be prioritized (when criteria not met, not pre-debut)
    should_prioritize_racing = not criteria_met and not is_pre_debut 
    
    log_debug(f"Year: '{year}', Criteria met: {criteria_met}, Pre-debut: {is_pre_debut}")
    
    return {
        "criteria_met": criteria_met,
        "is_pre_debut": is_pre_debut,
        "should_prioritize_racing": should_prioritize_racing
    } 

# log_and_flush function removed - using utils.core.log directly
