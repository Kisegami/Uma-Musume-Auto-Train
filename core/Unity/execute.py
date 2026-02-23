import time
import os
import random
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

from utils.recognizer import locate_on_screen, locate_all_on_screen, is_image_on_screen, match_template, max_match_confidence
from utils.input import tap, triple_click, long_press, tap_on_image
from utils.screenshot import take_screenshot, enhanced_screenshot, capture_region
from utils.constants_unity import (
    MOOD_LIST, EVENT_REGION, RACE_CARD_REGION, SUPPORT_CARD_ICON_REGION
)

# Import ADB state and logic modules
from core.Unity.state import check_mood, check_current_year, check_criteria, check_skill_points_cap, check_goal_name, check_current_stats, check_energy_bar, check_dating_available

# Import event handling functions
from core.Unity.event_handling import count_event_choices, load_event_priorities, analyze_event_options, handle_event_choice, click_event_choice

# Import training handling functions
from core.Unity.training_handling import go_to_training, check_training, do_train, check_support_card, check_failure, check_hint, choose_best_training, calculate_training_score
from core.Unity.unity_race_handling import unity_race_workflow

# Import dating handling functions
from core.Unity.dating_handling import do_dating, should_use_dating_for_mood, should_use_dating_for_rest

# Import race handling functions
from core.Unity.races_handling import (
    find_and_do_race, do_custom_race, race_day, check_strategy_before_race,
    change_strategy_before_race, race_prep, handle_race_retry_if_failed,
    after_race, is_racing_available, is_pre_debut_year
)

from utils.config_loader import load_main_config
config = load_main_config()
DEBUG_MODE = config.get("debug_mode", False)
racing_config = config.get("racing", {})
RETRY_RACE = racing_config.get("retry_race", True)

from utils.log import log_debug, log_info, log_warning, log_error, log_success
from utils.template_matching import deduplicated_matches, wait_for_image
from utils.device import reopen_and_resume_career

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
            from utils.screenshot import take_screenshot
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
    from utils.recognizer import locate_on_screen
    back_btn = locate_on_screen("assets/buttons/back_btn.png", confidence=0.8)
    if back_btn:
        log_debug(f"Going back to lobby to find rest button...")
        log_info(f"Going back to lobby to find rest button...")
        from utils.input import tap
        tap(back_btn[0], back_btn[1])
        time.sleep(1.0)  # Wait for lobby to load
    tazuna_hint = locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.95)
    if not tazuna_hint:
        log_debug(f"tazuna_hint.png not found, taking screenshot again to ensure we are in the lobby...")
        time.sleep(0.7)
        # Take a new screenshot and try again
        from utils.screenshot import take_screenshot
        take_screenshot()
        tazuna_hint = locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.95)
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
        from utils.input import tap
        tap(rest_btn[0], rest_btn[1])
        log_debug(f"Clicked rest button")
        log_info(f"Rest button clicked")
    elif rest_summer_btn:
        log_debug(f"Clicking summer rest button at {rest_summer_btn}")
        log_info(f"Clicking summer rest button at {rest_summer_btn}")
        from utils.input import tap
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
        return
    
    # Wait up to 5 seconds for screen to load and check for cancel button
    log_debug(f"Waiting for recreation screen to load (checking for cancel button)...")
    cancel_matches = None
    screenshot = None
    max_wait_time = 5.0
    check_interval = 0.5
    elapsed_time = 0.0
    
    while elapsed_time < max_wait_time:
        screenshot = take_screenshot()
        cancel_matches = match_template(screenshot, "assets/buttons/cancel_recreation.png", confidence=0.8)
        if cancel_matches:
            log_debug(f"Cancel button found after {elapsed_time:.1f}s")
            break
        time.sleep(check_interval)
        elapsed_time += check_interval
    
    if cancel_matches:
        # Normal recreation screen detected, tap trainee_date.png
        log_debug(f"Normal recreation screen detected, selecting trainee date...")
        log_info(f"Normal recreation screen detected, selecting trainee date...")
        
        trainee_date_btn = locate_on_screen("assets/ui/trainee_date.png", confidence=0.8)
        if trainee_date_btn:
            log_debug(f"Found trainee date button at {trainee_date_btn}")
            tap(trainee_date_btn[0], trainee_date_btn[1])
            log_info(f"Selected trainee date")
        else:
            log_warning(f"Trainee date button not found after detecting cancel button")
    else:
        log_debug(f"No cancel button found after {elapsed_time:.1f}s - normal recreation flow")
        if screenshot and DEBUG_MODE:
            screenshot.save("debug_recreation_no_cancel.png")
            log_debug(f"Saved debug screenshot to debug_recreation_no_cancel.png")

def career_lobby():
    """Main career lobby loop"""
    # Use existing config loaded at module level
    training_config_section = config.get("training", {})
    MINIMUM_MOOD = training_config_section.get("minimum_mood", "GREAT")

    # ── Lobby-stuck watchdog ──────────────────────────────────────────────
    # Tracks time spent spinning while NOT in lobby. Starts at the first
    # tazuna_hint check, resets the moment the lobby is confirmed.
    LOBBY_STUCK_TIMEOUT = 60  # seconds; purely lobby-wait time
    _lobby_wait_start = None  # None = not currently waiting for lobby
    _waiting_for_lobby_logged = False
    # ─────────────────────────────────────────────────────────────────────

    # Program start
    while True:
        log_debug(f"\n===== Starting new loop iteration =====")
        
        # Take screenshot first for all checks
        log_debug(f"Taking screenshot for UI element checks...")
        screenshot = take_screenshot()
        
        # Check for career restart first (highest priority) - quick check only
        log_debug(f"Quick check for Complete Career screen...")
        try:
            # Quick check for Complete Career button without importing full module
            complete_career_matches = match_template(screenshot, "assets/buttons/complete_career.png", confidence=0.8)
            if complete_career_matches:
                log_info(f"Complete Career screen detected - starting restart workflow")
                from core.Unity.restart_career import career_lobby_check
                should_continue = career_lobby_check(screenshot)
                if not should_continue:
                    log_info(f"Career restart workflow completed - stopping bot")
                    return False
        except Exception as e:
            log_error(f"Career restart check failed: {e}")
        
        # Batch UI check - use existing screenshot for multiple elements
        log_debug(f"Performing batch UI element check...")
        
        # Check claw machine first (highest priority)
        log_debug(f"Checking for claw machine...")
        claw_matches = match_template(screenshot, "assets/buttons/claw.png", confidence=0.8)
        if claw_matches:
            _lobby_wait_start = None
            claw_machine()
            continue
        
        # Check OK button
        log_debug(f"Checking for OK button...")
        ok_matches = match_template(screenshot, "assets/buttons/ok_btn.png", confidence=0.8)
        if ok_matches:
            x, y, w, h = ok_matches[0]
            center = (x + w//2, y + h//2)
            log_info(f"OK button found, clicking it.")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue
        
        # Check for events
        log_debug(f"Checking for events...")
        try:
            event_choice_region = (6, 450, 126, 1776)
            event_matches = match_template(screenshot, "assets/icons/event_choice_1.png", confidence=0.7, region=event_choice_region)
            
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
                        # Fallback using existing match
                        x, y, w, h = event_matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
                        _lobby_wait_start = None
                        continue
                else:
                    # If no choice locations were returned, skip clicking and continue loop
                    if not choice_locations:
                        log_debug(f"Skipping event click due to no visible choices after stabilization")
                        _lobby_wait_start = None
                        continue
                    log_warning(f"Event analysis failed, falling back to top choice")
                    # Fallback using existing match
                    x, y, w, h = event_matches[0]
                    center = (x + w//2, y + h//2)
                    tap(center[0], center[1])
                    _lobby_wait_start = None
                    continue
            else:
                log_debug(f"No events found")
        except RuntimeError as e:
            # Re-raise RuntimeError (critical failures that should stop the bot)
            if "Event detection failed" in str(e):
                raise
            log_error(f"Event handling error: {e}")
        except Exception as e:
            log_error(f"Event handling error: {e}")

        # Check for Unity Cup (Unity race workflow)
        log_debug(f"Checking for Unity Cup...")
        unity_cup = locate_on_screen("assets/unity/unity_cup.png", confidence=0.8)
        if unity_cup:
            log_info(f"Unity Cup detected, starting Unity race workflow...")
            try:
                if unity_race_workflow():
                    log_info(f"Unity race workflow completed.")
                    _lobby_wait_start = None
                    continue
            except Exception as e:
                log_warning(f"Unity race workflow failed: {e}")

        # Check inspiration button
        log_debug(f"Checking for inspiration...")
        inspiration_matches = match_template(screenshot, "assets/buttons/inspiration_btn.png", confidence=0.5)
        if inspiration_matches:
            x, y, w, h = inspiration_matches[0]
            center = (x + w//2, y + h//2)
            log_info(f"Inspiration found.")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # Check cancel button
        log_debug(f"Checking for cancel button...")
        cancel_matches = match_template(screenshot, "assets/buttons/cancel_lobby.png", confidence=0.8)
        if cancel_matches:
            x, y, w, h = cancel_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking cancel_btn.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # Check clóe button
        log_debug(f"Checking for close button...")
        close_matches = match_template(screenshot, "assets/buttons/close.png", confidence=0.8)
        if close_matches:
            x, y, w, h = close_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking close.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # Check next button
        log_debug(f"Checking for next button...")
        next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.8)
        if next_matches:
            x, y, w, h = next_matches[0]
            center = (x + w//2, y + h//2)
            log_debug(f"Clicking next_btn.png at position {center}")
            tap(center[0], center[1])
            _lobby_wait_start = None
            continue

        # Check if current menu is in career lobby
        log_debug(f"Checking if in career lobby...")
        tazuna_hint = locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.95)

        if tazuna_hint is None:
            # Check for back button to navigate back to lobby
            back_btn_matches = match_template(screenshot, "assets/buttons/back_btn.png", confidence=0.8)
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
                log_debug(f"[Watchdog] Lobby wait timer started.")
            elif time.time() - _lobby_wait_start > LOBBY_STUCK_TIMEOUT:
                log_warning(f"[Watchdog] Stuck waiting for lobby >{LOBBY_STUCK_TIMEOUT}s — restarting game...")
                try:
                    reopen_and_resume_career()
                except Exception as _wde:
                    log_error(f"[Watchdog] Reopen failed: {_wde}")
                _lobby_wait_start = None
            # ─────────────────────────────────────────────────────────────
            if not _waiting_for_lobby_logged:
                log_info(f"Waiting for Career lobby")
                _waiting_for_lobby_logged = True
            continue

        # Lobby confirmed — reset watchdog timer
        _lobby_wait_start = None
        _waiting_for_lobby_logged = False
        log_debug(f"Confirmed in career lobby")
        time.sleep(0.2)
        # Take a fresh screenshot after confirming lobby to ensure stable UI state
        log_debug(f"Taking fresh screenshot after lobby confirmation...")
        screenshot = take_screenshot()

        # Check if there is debuff status
        log_debug(f"Checking for debuff status...")
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
        mood = check_mood(screenshot)
        mood_index = MOOD_LIST.index(mood)
        minimum_mood = MOOD_LIST.index(MINIMUM_MOOD)
        year = check_current_year(screenshot)
        goal_data = check_goal_name(screenshot)
        criteria_text = check_criteria(screenshot)
        
        log_info("")
        log_info("=== GAME STATUS ===")
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
                        from core.Unity.races_handling import execute_race_after_selection
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
        log_debug(f"Checking energy bar...")
        energy_percentage = check_energy_bar(screenshot)
        training_config_section = config.get("training", {})
        min_energy = training_config_section.get("min_energy", 30)
        
        log_info(f"Energy: {energy_percentage:.1f}% (Minimum: {min_energy}%)")
        
        # Early check for race day to avoid rest_in_june on race day
        goal_matches_early = match_template(screenshot, "assets/unity/goal.png", confidence=0.8)
        is_race_day_early = bool(goal_matches_early)
        
        # Check for rest in June to save energy for summer (skip on Race Day)
        rest_in_june_enabled = training_config_section.get("rest_in_june", False)
        if rest_in_june_enabled and "Jun" in year and "Junior" not in year and energy_percentage <= 60 and not is_race_day_early:
            log_info(f"Rest in June enabled - Energy <= 60%. Going to rest to save energy for summer.")
            do_rest()
            continue
        
        # Get and display current stats
        try:
            from core.Unity.state import check_current_stats
            current_stats = check_current_stats(screenshot)
            stats_str = f"SPD: {current_stats.get('spd', 0)}, STA: {current_stats.get('sta', 0)}, PWR: {current_stats.get('pwr', 0)}, GUTS: {current_stats.get('guts', 0)}, WIT: {current_stats.get('wit', 0)}"
            log_info(f"Current stats: {stats_str}")
        except Exception as e:
            log_debug(f"Could not get current stats: {e}")
        
        # Check and display dating availability
        dating_available = check_dating_available(screenshot)
        log_info(f"Dating Available: {dating_available}")
        
        # Check if goals criteria are NOT met AND it is not Pre-Debut
        # Prioritize racing when criteria are not met to help achieve goals
        log_debug(f"Checking goal criteria...")
        goal_analysis = check_goal_criteria({"text": criteria_text}, year)
        
        if goal_analysis["should_prioritize_racing"]:
            log_info(f"Decision: Criteria not met - Prioritizing races to meet goals")
            race_found = find_and_do_race()
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

        # Check for race day using goal.png image
        log_debug(f"Checking for race day (goal.png)...")
        goal_matches = match_template(screenshot, "assets/unity/goal.png", confidence=0.8)
        is_race_day = bool(goal_matches)
        
        # URA SCENARIO
        log_debug(f"Checking for URA scenario...")
        if year == "Finale Underway" and is_race_day:
            log_info(f"URA Finale")
            
            # Check skill points cap before URA race day (if enabled)
            skills_config = config.get("skills", {})
            enable_skill_check = skills_config.get("enable_skill_point_check", True)
            
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
        racing_config_section = config.get("racing", {})
        do_custom_race_enabled = racing_config_section.get("do_custom_race", False)
        
        if do_custom_race_enabled:
            log_debug(f"Custom race is enabled, checking for custom race...")
            custom_race_found = do_custom_race()
            if custom_race_found:
            # Reset failure cache on success
                log_info(f"Custom race executed successfully")
                continue
            else:
                log_debug(f"No custom race found or executed")
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
                log_debug(f"Mood too low ({mood_index} < {minimum_mood}), checking for dating or recreation")
                # Check if dating should be used instead of recreation
                if should_use_dating_for_mood(screenshot):
                    log_info(f"Mood is low, using dating to increase mood")
                    if do_dating():
                        log_info(f"Dating initiated successfully")
                    else:
                        log_warning(f"Dating failed, falling back to recreation")
                        do_recreation()
                else:
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
            if should_use_dating_for_rest(screenshot):
                log_info(f"Using dating instead of rest")
                if not do_dating():
                    log_warning(f"Dating failed, falling back to rest")
                    do_rest()
            else:
                do_rest()
            continue
            
        if not go_to_training():
            log_warning("Training button is not found.")
            continue

        # Last, do training
        log_debug(f"Analyzing training options...")
        time.sleep(0.5)
        # Stay on training screen after checking (don't go back to lobby yet)
        results_training = check_training(go_back=False, year=year, current_stats=current_stats)
        
        log_debug(f"Deciding best training action using scoring algorithm...")
        
        # Use existing config for scoring thresholds
        training_config_section = config.get("training", {})
        min_score_config = training_config_section.get("min_score", {})
        
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
            min_wit_score = training_config_section.get("min_wit_score", None)
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
            "maximum_failure": training_config_section.get("maximum_failure", 15),
            "min_score": min_score_config,
            "priority_stat": training_config_section.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])
        }

        do_race_when_bad_training_flag = training_config_section.get("do_race_when_bad_training", True)
        
        # Use new scoring algorithm to choose best training (with stat cap filtering)
        log_debug(f"Choosing best training with stat cap filtering. Current stats: {current_stats}")
        best_training = choose_best_training(results_training, training_config, current_stats)
        
        if best_training:
            log_debug(f"Scoring algorithm selected: {best_training.upper()} training")
            log_info(f"Selected {best_training.upper()} training based on scoring algorithm")
            # Already on training screen, so skip navigation
            do_train(best_training, already_on_training_screen=True)
        else:
            log_debug(f"No suitable training found based on scoring criteria")
            log_info(f"No suitable training found based on scoring criteria.")
            
            # Check if we should prioritize racing when no good training is available
            do_race_when_bad_training = do_race_when_bad_training_flag
            
            if do_race_when_bad_training:
                # Check if all training options have failure rates above maximum
                from core.Unity.logic import all_training_unsafe
                max_failure = training_config.get('maximum_failure', 15)
                log_debug(f"Checking if all training options have failure rate > {max_failure}%")
                log_debug(f"Training results: {[(k, v['failure']) for k, v in results_training.items()]}")
                
                if all_training_unsafe(results_training, max_failure):
                    log_debug(f"All training options have failure rate > {max_failure}%")
                    # If all trainings are unsafe AND wit score is low, rest; otherwise try a relaxed training
                    wit_score = results_training.get('wit', {}).get('score', 0)
                    if wit_score < 1.0:
                        log_info(f"All training options unsafe and WIT score < 1.0. Choosing to rest.")
                        # Need to go back to lobby first since we're still on training screen
                        log_debug(f"Going back from training screen to lobby...")
                        tap_on_image("assets/buttons/back_btn.png")
                        time.sleep(0.3)
                        if should_use_dating_for_rest(screenshot):
                            log_info(f"Using dating instead of rest")
                            if not do_dating():
                                log_warning(f"Dating failed, falling back to rest")
                                do_rest()
                        else:
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
                        fallback_training = choose_best_training(results_training, relaxed_config, current_stats)
                        if fallback_training:
                            log_info(f"Proceeding with training ({fallback_training.upper()}) despite poor options (relaxed selection)")
                            # Already on training screen, so skip navigation
                            do_train(fallback_training, already_on_training_screen=True)
                            continue
                        else:
                            log_info(f"No viable training even after relaxed selection. Choosing to rest.")
                            # Need to go back to lobby first since we're still on training screen
                            log_debug(f"Going back from training screen to lobby...")
                            tap_on_image("assets/buttons/back_btn.png")
                            time.sleep(0.3)
                            if should_use_dating_for_rest(screenshot):
                                log_info(f"Using dating instead of rest")
                                if not do_dating():
                                    log_warning(f"Dating failed, falling back to rest")
                                    do_rest()
                            else:
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
                        fallback_training = choose_best_training(results_training, relaxed_config, current_stats)
                        if fallback_training:
                            log_info(f"Proceeding with training ({fallback_training.upper()}) due to no races")
                            # Already on training screen, so skip navigation
                            do_train(fallback_training, already_on_training_screen=True)
                            continue
                        else:
                            # If even relaxed cannot find, decide rest only if WIT score < 1.0, else do_rest as last resort
                            wit_score = results_training.get('wit', {}).get('score', 0)
                            # Need to go back to lobby first since we're still on training screen
                            log_debug(f"Going back from training screen to lobby...")
                            tap_on_image("assets/buttons/back_btn.png")
                            time.sleep(0.3)
                            if wit_score < 1.0:
                                log_info(f"No viable training after relaxation and no races. Choosing to rest.")
                                if should_use_dating_for_rest(screenshot):
                                    log_info(f"Using dating instead of rest")
                                    if not do_dating():
                                        log_warning(f"Dating failed, falling back to rest")
                                        do_rest()
                                else:
                                    do_rest()
                            else:
                                log_info(f"No training selected after relaxation. Choosing to rest.")
                                if should_use_dating_for_rest(screenshot):
                                    log_info(f"Using dating instead of rest")
                                    if not do_dating():
                                        log_warning(f"Dating failed, falling back to rest")
                                        do_rest()
                                else:
                                    do_rest()
                        
                    else:
                        log_info(f"Prioritizing race due to insufficient training scores.")
                        log_info(f"Training Race Check: Checking database for available races...")
                        
                        # Check database while still on training screen (no navigation)
                        from core.Unity.races_handling import check_race_in_database
                        race_available = check_race_in_database(year)
                        
                        if race_available:
                            log_info(f"Good race found in database. Going back to lobby to do race.")
                            # Go back to lobby and do the race
                            tap_on_image("assets/buttons/back_btn.png", text="[INFO] Going back to lobby to search for race...")
                            time.sleep(0.5)
                            race_found = find_and_do_race()
                            if race_found:
                                log_info(f"Training Race Result: Race executed successfully")
                                continue
                            else:
                                log_info(f"Training Race Result: Race execution failed")
                                # Go back to training and use relaxed config
                                if not go_to_training():
                                    log_warning("Could not return to training screen. Choosing to rest.")
                                    if should_use_dating_for_rest(screenshot):
                                        log_info(f"Using dating instead of rest")
                                        if not do_dating():
                                            log_warning(f"Dating failed, falling back to rest")
                                            do_rest()
                                    else:
                                        do_rest()
                                    continue
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
                            relaxed_training = choose_best_training(results_training, relaxed_config, current_stats)
                            if relaxed_training:
                                log_info(f"Proceeding with training ({relaxed_training.upper()}) using relaxed scoring")
                                do_train(relaxed_training, already_on_training_screen=True)
                                continue
                            else:
                                log_info(f"No training found even with relaxed scoring. Going back to rest.")
                                tap_on_image("assets/buttons/back_btn.png")
                                time.sleep(0.3)
                                if should_use_dating_for_rest(screenshot):
                                    log_info(f"Using dating instead of rest")
                                    if not do_dating():
                                        log_warning(f"Dating failed, falling back to rest")
                                        do_rest()
                                else:
                                    do_rest()
                        else:
                            log_info(f"Energy is {energy_percentage:.1f}% (< 50%). Going back to lobby to rest.")
                            tap_on_image("assets/buttons/back_btn.png")
                            time.sleep(0.3)
                            if should_use_dating_for_rest(screenshot):
                                log_info(f"Using dating instead of rest")
                                if not do_dating():
                                    log_warning(f"Dating failed, falling back to rest")
                                    do_rest()
                            else:
                                do_rest()
            else:
                # Race prioritization disabled: if no training was chosen here, rest
                # (min_score and failure thresholds are still enforced)
                log_info(f"Race prioritization disabled and no valid training found. Choosing to rest.")
                # Need to go back to lobby first since we're still on training screen
                log_debug(f"Going back from training screen to lobby...")
                tap_on_image("assets/buttons/back_btn.png")
                time.sleep(0.3)
                if should_use_dating_for_rest(screenshot):
                    log_info(f"Using dating instead of rest")
                    if not do_dating():
                        log_warning(f"Dating failed, falling back to rest")
                        do_rest()
                else:
                    do_rest()
        
        log_debug(f"Waiting before next iteration...")
        time.sleep(1)

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

# log_and_flush function removed - using utils.log directly