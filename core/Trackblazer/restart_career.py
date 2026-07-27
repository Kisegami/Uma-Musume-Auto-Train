#!/usr/bin/env python3
from utils.core.log import log_info, log_warning, log_error, log_debug, log_success
"""
Restart Career functionality for Uma Musume Emulator Auto Train.
Handles career completion and auto-restart based on configuration.
"""

import sys
import os
import time
from typing import Dict, Any, Optional, Tuple

# Add the project root to the path so we can import our modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
SUPPORTS_DIR = os.path.join(PROJECT_ROOT, "template", "supports")
os.makedirs(SUPPORTS_DIR, exist_ok=True)
RESTART_BACK_BUTTON_CENTER = (123, 1764)
RESTART_CAREER_HOME_REGION = (540, 1442, 522, 297)
RESTART_FULL_SCREEN_REGION = (0, 0, 1080, 1920)
RESTART_BOTTOM_HALF_REGION = (0, 960, 1080, 960)

from utils.vision.recognizer import match_template
from utils.capture.screenshot import take_screenshot
from utils.inputs.input import tap
from core.Trackblazer.skill_auto_purchase import click_image_button, enter_skill_screen
from core.Trackblazer.ocr import extract_text, extract_number
from utils.core.config_loader import load_main_config
from utils.constants.trackblazer import RESTART_COMPLETE_SPAM_TARGET

# Module-level state for persistent restart tracking across function calls
_restart_state = {
    'restart_count': 0,
    'total_fans_acquired': 0,
    'session_active': False
}


def restart_match_template(screenshot, template_path: str, confidence: float = 0.8, region=None):
    if region is None:
        if template_path.replace("\\", "/") == "assets/buttons/Career_Home.png":
            region = RESTART_CAREER_HOME_REGION
        else:
            region = RESTART_FULL_SCREEN_REGION
    return match_template(
        screenshot,
        template_path,
        confidence=confidence,
        region=region,
    )


def restart_wait_for_image(template_path: str, timeout: int = 10, confidence: float = 0.8, region=None, check_interval: float = 0.5):
    if region is None:
        if template_path.replace("\\", "/") == "assets/buttons/Career_Home.png":
            region = RESTART_CAREER_HOME_REGION
        else:
            region = RESTART_FULL_SCREEN_REGION
    return wait_for_image(
        template_path,
        timeout=timeout,
        confidence=confidence,
        region=region,
        check_interval=check_interval,
    )


def restart_click_image_button(image_path, description="button", max_attempts=10, wait_between_attempts=0.5, confidence=0.8, region=None):
    for attempt in range(max_attempts):
        button_pos = restart_wait_for_image(
            image_path,
            timeout=1,
            confidence=confidence,
            region=region,
            check_interval=0.2,
        )
        if button_pos:
            tap(button_pos[0], button_pos[1])
            log_info(f"{description} clicked successfully (attempt {attempt + 1}")
            return True
        if attempt < max_attempts - 1:
            time.sleep(wait_between_attempts)

    log_warning(f"Failed to click {description} after {max_attempts} attempts")
    return False


def reset_restart_state():
    """Reset restart state for a new session."""
    global _restart_state
    _restart_state = {
        'restart_count': 0,
        'total_fans_acquired': 0,
        'session_active': False
    }
    log_info("Restart state reset for new session")


def get_restart_state() -> Dict[str, Any]:
    """Get current restart state."""
    return _restart_state.copy()


def load_restart_config() -> Dict[str, Any]:
    """Load restart career configuration from config.json"""
    try:
        config = load_main_config()
        return config.get('restart_career', {})
    except Exception as e:
        log_info(f"Error loading config: {e}")
        return {}


def check_complete_career_screen(screenshot=None) -> bool:
    """Check if Complete Career screen is visible"""
    if screenshot is None:
        screenshot = take_screenshot()
    matches = restart_match_template(screenshot, "assets/buttons/complete_career.png", confidence=0.8)
    if matches:
        log_info(f"✓ Complete Career screen detected")
        return True
    else:
        log_info(f"✗ Complete Career screen not detected")
        return False


def extract_total_fans(screenshot) -> int:
    """Extract total fans from the Complete Career screen"""
    region = (735, 335, 939, 401)
    cropped = screenshot.crop(region)
    text = extract_text(cropped)
    cleaned_text = ''.join(char for char in text if char.isdigit())
    
    try:
        fans = int(cleaned_text) if cleaned_text else 0
        log_info(f"Total Fans acquired this run: {fans}")
        return fans
    except ValueError:
        log_info(f"Could not parse total fans, defaulting to 0")
        return 0


def extract_skill_points(screenshot) -> int:
    """Extract skill points from the Complete Career screen"""
    region = (327, 1609, 441, 1651)
    cropped = screenshot.crop(region)
    number = extract_number(cropped)
    
    try:
        points = int(number) if number and number.isdigit() else 0
        log_info(f"Skill Points available: {points}")
        return points
    except ValueError:
        log_info(f"Could not parse skill points, defaulting to 0")
        return 0


def should_continue_restarting(current_restart_count: int, max_restart_times: int, 
                              total_fans_acquired: int, total_fans_requirement: int) -> Tuple[bool, str]:
    """Check if we should continue restarting based on config limits"""
    # Check restart count limit
    if current_restart_count >= max_restart_times:
        return False, f"Reached maximum restart limit ({max_restart_times})"
    
    # Check total fans requirement
    if total_fans_requirement > 0 and total_fans_acquired >= total_fans_requirement:
        return False, f"Reached total fans requirement ({total_fans_acquired}/{total_fans_requirement})"
    
    return True, "Continue restarting"


def execute_skill_purchase_workflow(available_points: int):
    """Execute the skill purchase workflow with merged priorities (main → end → budget)"""
    log_info(f"=== Auto Skill Purchase Workflow ===")
    
    # Import here to avoid circular imports
    from core.Trackblazer.skill_auto_purchase import click_image_button
    from core.Trackblazer.skill_recognizer import scan_all_skills_with_scroll, get_skills_api
    from core.Trackblazer.skill_purchase_optimizer import load_skill_config, create_purchase_plan, filter_affordable_skills
    from core.Trackblazer.skill_auto_purchase import execute_skill_purchases
    from core.Trackblazer.skill_recognizer import deduplicate_skills
    try:
        from utils.integrations.umat_api import is_api_enabled
        api_mode = is_api_enabled()
    except ImportError:
        api_mode = False

    if api_mode:
        all_available_skills = get_skills_api()
        if all_available_skills is None:
            log_error("API mode is enabled but failed to get end-career skills from /skills")
            raise RuntimeError("API mode is enabled but /skills API is not responding. Check API connection or set api.enabled to false in config.json.")
        log_info(f"[API] Got {len(all_available_skills)} end-career skills from API (skipping OCR scan)")
    else:
        if not enter_skill_screen(end_career=True):
            log_info(f"Failed to tap end skill button")
            return
        scan_result = scan_all_skills_with_scroll(confidence=0.9, brightness_threshold=150, max_scrolls=20)
        all_available_skills = scan_result.get('all_skills', [])
    
    if all_available_skills:
        # Deduplicate and optimize skill purchase
        deduplicated_skills = deduplicate_skills(all_available_skills, similarity_threshold=0.8)
        
        # Load main skill config
        main_config = load_skill_config()
        
        # Load end skill config (always used during restart career)
        restart_config = load_restart_config()
        end_skill_file = restart_config.get("end_skill_file", "")
        
        # Merge configs: main priority list + end skill priority list
        merged_config = {
            "skill_priority": list(main_config.get("skill_priority", [])),
            "gold_skill_upgrades": dict(main_config.get("gold_skill_upgrades", {}))
        }
        
        if end_skill_file:
            try:
                import json
                import os
                # Handle relative path
                if not os.path.isabs(end_skill_file):
                    end_skill_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), end_skill_file)
                
                if os.path.exists(end_skill_file):
                    with open(end_skill_file, 'r', encoding='utf-8') as f:
                        end_config = json.load(f)
                    
                    # Append end skill priorities (avoid duplicates)
                    existing_priorities = set(merged_config["skill_priority"])
                    for skill in end_config.get("skill_priority", []):
                        if skill not in existing_priorities:
                            merged_config["skill_priority"].append(skill)
                            existing_priorities.add(skill)
                    
                    # Merge gold skill upgrades
                    merged_config["gold_skill_upgrades"].update(end_config.get("gold_skill_upgrades", {}))
                    
                    log_info(f"Merged end skill config from: {end_skill_file}")
                else:
                    log_info(f"End skill file not found: {end_skill_file}")
            except Exception as e:
                log_info(f"Failed to load end skill config: {e}")
        
        # Use end_career=True to buy all available skills instead of just priority skills
        purchase_plan = create_purchase_plan(deduplicated_skills, merged_config, end_career=True)
        
        if purchase_plan:
            affordable_skills, total_cost, remaining_points = filter_affordable_skills(
                purchase_plan,
                available_points,
                merged_config.get("gold_skill_upgrades", {}),
            )
            if affordable_skills:
                # OCR mode is already inside the end-skill screen after scanning.
                # Only API mode needs to open the screen before purchasing.
                if api_mode:
                    if not enter_skill_screen(end_career=True):
                        log_info(f"Failed to tap end skill button")
                        return_to_complete_career_screen()
                        return
                execute_skill_purchases(affordable_skills, end_career=True, reset_to_top=not api_mode)
    
    # Return to complete career screen
    return_to_complete_career_screen()


def return_to_complete_career_screen():
    """Return to the complete career screen after skill purchase"""
    back_success = restart_click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
    if not back_success:
        log_warning("Template back button click failed, trying fallback coordinates")
        tap(RESTART_BACK_BUTTON_CENTER[0], RESTART_BACK_BUTTON_CENTER[1])
        time.sleep(1.5)
        if check_complete_career_screen():
            log_info("Returned to complete career screen using fallback back-button coordinates")
            return True

    if back_success:
        time.sleep(1.5)
        return check_complete_career_screen()
    return False


def _tap_first_template_match(screenshot, template_path: str, description: str, confidence: float = 0.8, region=None) -> bool:
    matches = restart_match_template(screenshot, template_path, confidence=confidence, region=region)
    if not matches:
        return False

    x, y, w, h = matches[0]
    center = (x + w // 2, y + h // 2)
    tap(center[0], center[1])
    log_info(f"{description} found and tapped at {center}")
    return True


def _wait_for_template_absent(template_path: str, timeout: float = 5.0, confidence: float = 0.8, region=None) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        screenshot = take_screenshot()
        if not restart_match_template(screenshot, template_path, confidence=confidence, region=region):
            return True
        time.sleep(0.2)
    return False


def _tap_bottom_completion_button(screenshot) -> bool:
    """Tap visible bottom-half Close/Next buttons during end-career navigation."""
    bottom_buttons = [
        ("assets/buttons/close.png", "bottom close button"),
        ("assets/buttons/next_btn.png", "bottom next button"),
        ("assets/buttons/next2_btn.png", "bottom next2 button"),
    ]

    for template_path, description in bottom_buttons:
        if _tap_first_template_match(
            screenshot,
            template_path,
            description,
            confidence=0.8,
            region=RESTART_BOTTOM_HALF_REGION,
        ):
            return True

    return False


def _wait_for_reroll_spark_sequence(timeout: int = 120) -> bool:
    """Advance completion screens until reroll spark appears, then confirm and close."""
    log_info("Waiting for reroll spark sequence...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        screenshot = take_screenshot()
        reroll_spark_matches = restart_match_template(
            screenshot,
            "assets/buttons/reroll_spark.png",
            confidence=0.8,
        )
        if reroll_spark_matches:
            log_info("Reroll spark button detected")
            break

        if _tap_bottom_completion_button(screenshot):
            time.sleep(0.25)
            continue

        time.sleep(0.2)
    else:
        log_warning("Reroll spark button not found during completion navigation")
        return False

    confirm_pos = restart_wait_for_image("assets/buttons/confirm.png", timeout=10, confidence=0.8)
    if not confirm_pos:
        log_warning("First confirm button not found after reroll spark")
        return False
    tap(confirm_pos[0], confirm_pos[1])
    log_info("First reroll spark confirm tapped")
    _wait_for_template_absent("assets/buttons/confirm.png", timeout=5, confidence=0.8)

    confirm_pos = restart_wait_for_image("assets/buttons/confirm.png", timeout=10, confidence=0.8)
    if not confirm_pos:
        log_warning("Second confirm button not found after reroll spark")
        return False
    tap(confirm_pos[0], confirm_pos[1])
    log_info("Second reroll spark confirm tapped")
    time.sleep(0.5)

    close_pos = restart_wait_for_image("assets/buttons/close.png", timeout=10, confidence=0.8)
    if not close_pos:
        log_warning("Close button not found after reroll spark confirms")
        return False
    tap(close_pos[0], close_pos[1])
    log_info("Reroll spark close tapped")
    time.sleep(0.5)

    return True


def finish_career_completion() -> bool:
    """Complete the career and navigate through completion screens"""
    log_info(f"=== Completing Career ===")
    
    # Click complete career button
    if not restart_click_image_button("assets/buttons/complete_career.png", "complete career button", max_attempts=5):
        log_info(f"Failed to click complete career button")
        return False
    
    time.sleep(0.5)

    if not restart_click_image_button("assets/buttons/finish.png", "finish button", max_attempts=5):
        log_info(f"Failed to click finish button")
        return False

    time.sleep(0.5)

    if not _wait_for_reroll_spark_sequence():
        return False

    # Some end-of-run screens are not stable enough for template clicks.
    # Keep tapping the known continue area until the start-career screen appears.
    start_time = time.time()
    max_duration_seconds = 120  # Safety timeout to avoid infinite loop

    while time.time() - start_time < max_duration_seconds:
        screenshot = take_screenshot()
        ready_screen = _detect_start_career_screen(screenshot)
        if ready_screen:
            time.sleep(1)
            log_info(f"{ready_screen} detected - Career completion successful")
            return True

        _tap_bottom_completion_button(screenshot)
        tap(RESTART_COMPLETE_SPAM_TARGET[0], RESTART_COMPLETE_SPAM_TARGET[1])
        time.sleep(0.08)

    log_info(f"Failed to complete career navigation")
    return False


def _detect_start_career_screen(screenshot=None) -> Optional[str]:
    """Return the current screen name when the game is back at Career Home."""
    if screenshot is None:
        screenshot = take_screenshot()

    if restart_match_template(screenshot, "assets/buttons/Career_Home.png", confidence=0.8):
        return "Career Home"

    return None



def load_config():
    """Load configuration from config.json"""
    try:
        return load_main_config()
    except Exception as e:
        log_info(f"Error loading config: {e}")
        return {}


from utils.vision.template_matching import wait_for_image


def filter_support() -> bool:
    """Filter support cards based on configuration utilizing OCR to check status.
    Returns False if support template is strictly required but fundamentally unfindable."""
    log_info(f"Checking support card filter status...")
    
    config = load_config()
    auto_start_career = config.get('auto_start_career', {})
    
    # Check filter status via OCR
    screenshot = take_screenshot()
    filter_status_region = (399, 1593, 585, 1647)
    cropped_filter = screenshot.crop(filter_status_region)
    filter_text = extract_text(cropped_filter)
    
    # Clean text to ease matching
    clean_text = filter_text.strip().upper()
    log_info(f"Filter OCR text: '{clean_text}'")
    
    if "OFF" in clean_text:
        log_info("Filters are OFF, applying filter settings...")
        support_speciality = auto_start_career.get('support_speciality', 'SPEED')
        support_rarity = auto_start_career.get('support_rarity', 'SSR')
        
        # Tap filter button
        tap(696, 1621)
        time.sleep(0.5)
        
        # Tap additional filter coordinate
        tap(774, 206)
        time.sleep(0.5)

        # Reset filter
        screen_for_reset = take_screenshot()
        reset_filter_matches = restart_match_template(screen_for_reset, "assets/buttons/reset_filter.png", confidence=0.8)
        if reset_filter_matches:
            x, y, w, h = reset_filter_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(0.5)
        
        # Set support speciality
        support_speciality_coords = {
            "SPD": (102, 627),
            "STA": (444, 623),
            "PWR": (786, 618),
            "GUTS": (109, 741),
            "WIT": (442, 732),
            "PAL": (777, 731),
        }
        
        if support_speciality in support_speciality_coords:
            x, y = support_speciality_coords[support_speciality]
            tap(x, y)
            time.sleep(0.5)
        
        # Set support rarity
        support_rarity_coords = {
            "R": (102, 408),
            "SR": (437, 414),
            "SSR": (777, 410),
        }
        
        if support_rarity in support_rarity_coords:
            x, y = support_rarity_coords[support_rarity]
            tap(x, y)
            time.sleep(0.5)
        
        # OK button after filter selection
        ok_matches = restart_match_template(take_screenshot(), "assets/buttons/ok_btn.png", confidence=0.6)
        if ok_matches:
            x, y, w, h = ok_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(1.0) # Wait for filter to apply
    else:
        log_info("Filters are already ON (or not OFF), skipping filter setup...")

    # Use template selection when enabled
    use_templates = auto_start_career.get('use_support_templates', False)
    template_name = auto_start_career.get('support_template_name', '')
    log_info(f"Support template toggle: {use_templates}, template name: '{template_name}'")
    if use_templates:
        template_path = os.path.join(SUPPORTS_DIR, template_name) if template_name else None
        if template_path and os.path.exists(template_path):
            log_info(f"Support template mode ON -> using '{template_name}' at '{template_path}'")
            max_refreshes = 3
            max_scrolls_per_refresh = 3
            
            for refresh_attempt in range(max_refreshes + 1): # 0 is initial load, 1-3 are actual refreshes
                for scroll_attempt in range(max_scrolls_per_refresh + 1): # 0 is initial view, 1-3 are scrolls
                    screenshot = take_screenshot()
                    matches = restart_match_template(screenshot, template_path, confidence=0.7)
                    
                    if matches:
                        log_info(f"Template '{template_name}' found!")
                        x, y, w, h = matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
                        time.sleep(0.5)
                        return True
                    else:
                        if scroll_attempt < max_scrolls_per_refresh:
                            log_warning(f"No match found on screen (Refresh {refresh_attempt}, Scroll {scroll_attempt}); attempting to scroll.")
                            from utils.inputs.support_swipe import swipe_support_list_down
                            swipe_support_list_down(wait_before=0.5, wait_after=1.5)
                        else:
                            log_warning(f"Max scrolls reached for this refresh cycle.")
                            
                # If we exhausted all scrolls and didn't find it, we try to refresh if we have attempts left
                if refresh_attempt < max_refreshes:
                    log_info(f"Attempting to refresh support cards list (Refresh {refresh_attempt + 1}/{max_refreshes})...")
                    # Tap refresh button
                    refresh_matches = restart_match_template(take_screenshot(), "assets/buttons/supports_refresh.png", confidence=0.8)
                    if refresh_matches:
                        x, y, w, h = refresh_matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
                        time.sleep(1.0)
                        
                        # Tap OK button for refresh confirm
                        ok_matches = restart_match_template(take_screenshot(), "assets/buttons/ok_btn.png", confidence=0.6)
                        if ok_matches:
                            x, y, w, h = ok_matches[0]
                            center = (x + w//2, y + h//2)
                            tap(center[0], center[1])
                            time.sleep(1.5) # Wait for list to reload
                    else:
                         log_warning("Could not find refresh button. Exiting refresh loop.")
                         break # Break to outer error handling if refresh button simply isn't there
                         
            # If we exhausted all refreshes and all their scrolls
            log_error("Cannot find template support card and stop the bot instead choose the first following supports cards")
            return False
        else:
            log_warning(f"Support template enabled but template file missing at '{template_path}'; falling back to following card.")
            # Note: Explicit fallback requested by user ONLY if the setting is true but the file on disk doesn't exist
            # If it does exist but can't be found on screen, we return False per instructions.

    # Fallback: select first following card (only reached if use_templates is False or template file physically missing)
    time.sleep(1)
    screenshot = take_screenshot()
    following_matches = match_template(screenshot, "assets/icons/following.png", confidence=0.8)
    
    if following_matches:
        following_matches.sort(key=lambda match: match[1])
        x, y, w, h = following_matches[0]
        center = (x + w//2, y + h//2)
        tap(center[0], center[1])
        time.sleep(0.5)
        
    return True


def restore_tp() -> bool:
    """Restore TP using TP bottle or Carats when out of TP.
    
    Returns:
        bool: True if TP restored successfully, False if no bottles/carats available
    """
    log_info("=== Restoring TP ===")
    
    config = load_config()
    auto_start_career = config.get('auto_start_career', {})
    use_carats = auto_start_career.get('auto_charge_tp_carats', False)
    
    # Step 1: Tap restore button
    if not restart_click_image_button("assets/buttons/restore_btn.png", "restore button", max_attempts=5):
        log_warning("Failed to tap restore button")
        return False
    
    time.sleep(1)
    
    # Step 2: Wait for TP bottle to appear
    tp_bottle_matches = restart_wait_for_image("assets/icons/tp_bottle.png", timeout=5, confidence=0.8)
    
    if tp_bottle_matches:
        # Step 3: Calculate Use button position (offset from bottle)
        # TP Bottle at (131, 481) → Use button at (912, 481)
        # X offset = 912 - 131 = 781
        bottle_x, bottle_y = tp_bottle_matches[0], tp_bottle_matches[1]
        use_btn_x = bottle_x + 781
        use_btn_y = bottle_y
        
        log_info(f"TP bottle at ({bottle_x}, {bottle_y}), tapping Use at ({use_btn_x}, {use_btn_y})")
        tap(use_btn_x, use_btn_y)
        time.sleep(1)
    else:
        log_warning("Out of TP Bottle")
        if use_carats:
            log_info("Trying to restore using Carats instead")
            tp_carats_matches = restart_wait_for_image("assets/icons/tp_carats.png", timeout=5, confidence=0.8)
            if not tp_carats_matches:
                log_error("Carats icon not found")
                return False
                
            carats_x, carats_y = tp_carats_matches[0], tp_carats_matches[1]
            use_btn_x = carats_x + 781
            use_btn_y = carats_y
            
            log_info(f"Carats icon at ({carats_x}, {carats_y}), tapping Use at ({use_btn_x}, {use_btn_y})")
            tap(use_btn_x, use_btn_y)
            time.sleep(1)
            
            # For Carats, tap the tp_plus button before confirming
            if not restart_click_image_button("assets/buttons/tp_plus.png", "tp plus button", max_attempts=5):
                log_warning("Failed to tap tp plus button")
                return False
            time.sleep(0.5)
        else:
            log_error("Carats restore not enabled, stopping bot")
            return False
            
    # Step 4: Tap OK button
    if not restart_click_image_button("assets/buttons/ok_restore.png", "OK button", max_attempts=10):
        log_warning("Failed to tap OK button")
        return False
    
    time.sleep(0.5)
    
    # Step 5: Tap Close button
    if not restart_click_image_button("assets/buttons/close.png", "close button", max_attempts=10):
        log_warning("Failed to tap close button")
        return False
    
    log_info("✓ TP restored successfully")
    return True


def _detect_skip_variant(screenshot=None, confidence: float = 0.7) -> Tuple[Optional[str], Optional[Tuple[int, int]], float]:
    """Detect the current skip button variant and return its center position."""
    if screenshot is None:
        screenshot = take_screenshot()

    skip_variants = [
        ("assets/buttons/skip_off.png", "skip_off"),
        ("assets/buttons/skip_x1.png", "skip_x1"),
        ("assets/buttons/skip_x2.png", "skip_x2"),
        ("assets/buttons/skip_btn.png", "skip_btn"),
    ]

    best_variant = None
    best_center = None
    best_confidence = 0.0

    from utils.vision.recognizer import max_match_confidence

    for template_path, variant_name in skip_variants:
        if not os.path.exists(template_path):
            continue

        match_confidence = max_match_confidence(screenshot, template_path)
        if match_confidence and match_confidence > best_confidence:
            matches = restart_match_template(screenshot, template_path, confidence=confidence)
            if matches:
                x, y, w, h = matches[0]
                best_variant = variant_name
                best_center = (x + w // 2, y + h // 2)
                best_confidence = match_confidence

    return best_variant, best_center, best_confidence


def wait_for_skip_variant(timeout: int = 10, confidence: float = 0.7) -> Tuple[Optional[str], Optional[Tuple[int, int]], float]:
    """Wait for any skip button variant to appear."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        variant, center, match_confidence = _detect_skip_variant(confidence=confidence)
        if variant:
            return variant, center, match_confidence
        time.sleep(0.3)

    return None, None, 0.0


def _find_confirm_center(screenshot=None, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """Return the center of the confirm button when it is visible."""
    if screenshot is None:
        screenshot = take_screenshot()

    matches = restart_match_template(screenshot, "assets/buttons/confirm.png", confidence=confidence)
    if not matches:
        return None

    x, y, w, h = matches[0]
    return (x + w // 2, y + h // 2)


def wait_for_confirm_after_skip(timeout: int = 30, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """Keep advancing skip state until the confirm button appears."""
    start_time = time.time()
    last_skip_tap = 0.0

    while time.time() - start_time < timeout:
        screenshot = take_screenshot()

        confirm_center = _find_confirm_center(screenshot=screenshot, confidence=confidence)
        if confirm_center:
            return confirm_center

        variant, center, match_confidence = _detect_skip_variant(screenshot=screenshot, confidence=0.7)
        now = time.time()
        if center and (now - last_skip_tap) >= 0.5:
            if variant == "skip_off":
                log_info(
                    f"Confirm not visible yet; retrying skip_off at {center} "
                    f"(confidence {match_confidence:.2f})"
                )
                tap(center[0], center[1])
                time.sleep(0.12)
                tap(center[0], center[1])
                last_skip_tap = time.time()
                time.sleep(0.35)
                continue

            if variant in {"skip_x1", "skip_btn"}:
                action = "retrying skip_x1" if variant == "skip_x1" else "retrying generic skip"
                log_info(
                    f"Confirm not visible yet; {action} at {center} "
                    f"(confidence {match_confidence:.2f})"
                )
                tap(center[0], center[1])
                if variant == "skip_btn":
                    time.sleep(0.12)
                    tap(center[0], center[1])
                last_skip_tap = time.time()
                time.sleep(0.35)
                continue

        time.sleep(0.25)

    return None


def normalize_skip_state(timeout: int = 5) -> bool:
    """Normalize skip state to x2 when possible."""
    log_info("Checking skip button state...")

    variant, center, match_confidence = wait_for_skip_variant(timeout=timeout, confidence=0.7)
    if not variant or not center:
        log_warning("Skip button state not detected")
        return False

    log_info(f"Detected {variant} (confidence {match_confidence:.2f}) at {center}")

    if variant == "skip_off":
        tap(center[0], center[1])
        time.sleep(0.15)
        tap(center[0], center[1])
        log_info("Tapped skip_off twice")
        time.sleep(0.3)

        variant, center, _ = wait_for_skip_variant(timeout=2, confidence=0.7)
        if variant == "skip_x1" and center:
            tap(center[0], center[1])
            log_info("Tapped skip_x1 once")
            time.sleep(0.3)
    elif variant == "skip_x1":
        tap(center[0], center[1])
        log_info("Tapped skip_x1 once")
        time.sleep(0.3)
    elif variant == "skip_btn":
        tap(center[0], center[1])
        time.sleep(0.1)
        tap(center[0], center[1])
        log_info("Double-tapped generic skip button")
        time.sleep(0.3)
    else:
        log_info("Skip already enabled (skip_x2)")

    final_variant, _, final_confidence = _detect_skip_variant(confidence=0.7)
    if final_variant == "skip_x2":
        log_info(f"Skip normalized to skip_x2 (confidence {final_confidence:.2f})")
        return True

    log_warning(f"Skip normalization incomplete; final state: {final_variant or 'unknown'}")
    return False


def skip_check(timeout: int = 5) -> bool:
    """Backward-compatible alias for skip normalization."""
    return normalize_skip_state(timeout=timeout)


def retry_skip_normalization(max_attempts: int = 3, timeout: int = 30) -> bool:
    """Retry skip normalization with a fresh screenshot on each attempt."""
    for attempt in range(1, max_attempts + 1):
        take_screenshot()
        log_info(f"[Step 8/13] Skip normalization attempt {attempt}/{max_attempts}")
        if normalize_skip_state(timeout=timeout):
            return True
        if attempt < max_attempts:
            time.sleep(0.5)
    return False


def retry_confirm_check(max_attempts: int = 3, timeout: int = 30, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """Retry confirm detection with a fresh screenshot on each attempt."""
    for attempt in range(1, max_attempts + 1):
        take_screenshot()
        log_info(f"[Step 9/13] Confirm detection attempt {attempt}/{max_attempts}")
        confirm_center = wait_for_confirm_after_skip(timeout=timeout, confidence=confidence)
        if confirm_center:
            return confirm_center
        if attempt < max_attempts:
            time.sleep(0.5)
    return None


def start_career() -> bool:
    """Start a new career using the existing start_career logic"""
    log_info(f"=== Starting New Career ===")
    
    config = load_config()
    auto_start_career = config.get('auto_start_career', {})
    include_guests_legacy = auto_start_career.get('include_guests_legacy', False)
    
    try:
        # Step 1: Tap Career Home and wait 10s
        career_home_pos = restart_wait_for_image("assets/buttons/Career_Home.png", timeout=10, confidence=0.8)
        if career_home_pos:
            tap(career_home_pos[0], career_home_pos[1])
            time.sleep(10)
        else:
            log_info(f"Career Home not found")
            return False
        
        # Step 2: Tap Next button twice
        # Tap 1: Scenario Select
        next_pos = restart_wait_for_image("assets/buttons/next_btn.png", timeout=10, confidence=0.8)
        if next_pos:
            tap(next_pos[0], next_pos[1])

            # Wait for event popup for up to 10.0 seconds
            start_time = time.time()
            while time.time() - start_time < 10.0:
                screenshot = take_screenshot()

                confirm_pos = match_template(screenshot, "assets/buttons/confirm.png", confidence=0.7, region=RESTART_FULL_SCREEN_REGION)
                if confirm_pos:
                    x, y, w, h = confirm_pos[0]
                    log_info("Event popup detected (confirm). Tapping confirm...")
                    tap(x + w//2, y + h//2)
                    break

                ok_pos = match_template(screenshot, "assets/buttons/ok_btn.png", confidence=0.7, region=RESTART_FULL_SCREEN_REGION)
                if ok_pos:
                    x, y, w, h = ok_pos[0]
                    log_info("Event popup detected (OK). Tapping OK...")
                    tap(x + w//2, y + h//2)
                    break

                close_pos = match_template(screenshot, "assets/buttons/close.png", confidence=0.7, region=RESTART_FULL_SCREEN_REGION)
                if close_pos:
                    x, y, w, h = close_pos[0]
                    log_info("Event popup detected (Close). Tapping close...")
                    tap(x + w//2, y + h//2)
                    break

                if time.time() - start_time > 1.2:
                    next_btn_visible = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.8)
                    if next_btn_visible:
                        log_info("Next screen detected without event popup. Proceeding.")
                        break

                time.sleep(0.2)
        else:
            return False

        # Tap 2: Character Select
        next_pos = restart_wait_for_image("assets/buttons/next_btn.png", timeout=30, confidence=0.8)
        if next_pos:
            tap(next_pos[0], next_pos[1])
            time.sleep(1)
        else:
            return False
        
        # Step 3: Tap Next button
        log_info("[Step 3/13] Tapping Next button...")
        next_pos = restart_wait_for_image("assets/buttons/next_btn.png", timeout=10, confidence=0.8)
        if next_pos:
            tap(next_pos[0], next_pos[1])
            log_info("[Step 3/13] ✓ Next button tapped")
            time.sleep(1)
        else:
            log_error("[Step 3/13] ✗ Next button not found")
            return False

        # Step 4: Tap Friend Support Choose
        log_info(f"Friend Support...")
        friend_support_pos = restart_wait_for_image("assets/buttons/Friend_support_choose.png", timeout=30, confidence=0.8)
        if friend_support_pos:
            tap(friend_support_pos[0], friend_support_pos[1])
            time.sleep(1)
        else:
            return False
        
        # Step 5: Filter support
        log_info(f"Filtering...")
        if filter_support() is False:
            return False
            
        time.sleep(1)
        
        # Step 6: Start Career 1
        start_career_1_pos = restart_wait_for_image("assets/buttons/start_career_1.png", timeout=10, confidence=0.8)
        if start_career_1_pos:
            tap(start_career_1_pos[0], start_career_1_pos[1])
            time.sleep(0.5)
            
            # Check for insufficient TP (restore button appears)
            restore_pos = restart_wait_for_image("assets/buttons/restore_btn.png", timeout=3, confidence=0.8)
            if restore_pos:
                auto_charge = auto_start_career.get('auto_charge_tp', False)
                if auto_charge:
                    log_info("Insufficient TP detected - attempting auto restore")
                    if not restore_tp():
                        log_error("TP restore failed - Out of TP Bottle")
                        return False
                    # After restore, tap Start Career 1 again
                    start_career_1_pos = restart_wait_for_image("assets/buttons/start_career_1.png", timeout=10, confidence=0.8)
                    if start_career_1_pos:
                        tap(start_career_1_pos[0], start_career_1_pos[1])
                        time.sleep(0.5)
                    else:
                        log_error("Failed to find Start Career 1 button after TP restore")
                        return False
                else:
                    log_error("Insufficient TP and auto_charge_tp is disabled - stopping bot")
                    return False
        else:
            return False
        
        # Step 7: Start Career 2
        start_career_2_pos = restart_wait_for_image("assets/buttons/start_career_2.png", timeout=15, confidence=0.8)
        if start_career_2_pos:
            tap(start_career_2_pos[0], start_career_2_pos[1])
        else:
            return False
        
        # Step 8: Wait for skip button state and normalize it
        log_info("[Step 8/13] Waiting for skip control (30s timeout)...")
        skip_ready = retry_skip_normalization(max_attempts=3, timeout=30)
        if not skip_ready:
            log_warning("[Step 8/13] Skip state not fully normalized; will continue while waiting for confirm")
            variant, _, _ = _detect_skip_variant(confidence=0.7)
            if not variant:
                log_error("[Step 8/13] ✗ Skip button state could not be detected")
                return False
        else:
            log_info("[Step 8/13] ✓ Skip button handled successfully")
        time.sleep(0.5)
        
        # Step 9: Wait for confirm button
        log_info("[Step 9/13] Waiting for confirm button (30s timeout)...")
        confirm_center = retry_confirm_check(max_attempts=3, timeout=30, confidence=0.8)
        if not confirm_center:
            log_error("[Step 9/13] ✗ Confirm button not found within 30s")
            return False
        log_info("[Step 9/13] ✓ Confirm button found")
        
        # Step 10: Tap coordinates
        log_info("[Step 10/13] Tapping coordinates (213, 939)...")
        tap(213, 939)
        time.sleep(0.5)
        
        # Step 11: Skip check
        log_info("[Step 11/13] Rechecking skip state...")
        skip_check()
        time.sleep(0.5)
        
        # Step 12: Tap confirm
        log_info("[Step 12/13] Looking for final confirm button...")
        confirm_pos = restart_wait_for_image(
            "assets/buttons/confirm.png",
            timeout=10,
            confidence=0.8,
        )
        if confirm_pos:
            tap(confirm_pos[0], confirm_pos[1])
            log_info("[Step 12/13] Final confirm tapped")
        else:
            log_error("[Step 12/13] Final confirm button not found")
            return False
        
        # Step 13: Wait for Tazuna hint
        tazuna_hint_matches = restart_wait_for_image("assets/ui/tazuna_hint.png", timeout=60, confidence=0.9)
        if tazuna_hint_matches:
            from core.Trackblazer.execute import arm_skip_infirmary_check_for_new_turn

            arm_skip_infirmary_check_for_new_turn()
            log_info(f"Career start completed!")
            return True
        else:
            return False
            
    except Exception as e:
        log_error(f"{e}")
        return False


def notify_run_completion(screenshot, current_restart_count: int, max_restart_times: int, 
                           total_fans_acquired: int) -> Tuple[int, int]:
    """
    Extract fans and send webhook notification.
    Returns (run_fans, new_total_fans_acquired)
    """
    run_fans = extract_total_fans(screenshot)
    new_total_fans = total_fans_acquired + run_fans
    
    log_info(f"Total fans acquired so far: {new_total_fans}")
    
    # Send Discord webhook notification
    try:
        from utils.integrations.discord_webhook import is_webhook_enabled, send_run_complete_webhook
        if is_webhook_enabled():
            run_number = current_restart_count + 1
            # If max_restart_times is 0 or 1 generally implies single run if logic holds, 
            # but usually it's set to N. If restart disabled, maybe show 1/1?
            
            average_per_run = new_total_fans // run_number if run_number > 0 else 0
            send_run_complete_webhook(
                run_number=run_number,
                max_runs=max_restart_times,
                fans_this_run=run_fans,
                session_total=new_total_fans,
                today_total=new_total_fans,
                average_per_run=average_per_run,
                screenshot=screenshot
            )
    except Exception as e:
        log_warning(f"Failed to send Discord webhook: {e}")
        
    return run_fans, new_total_fans


def complete_career(current_restart_count: int, max_restart_times: int, 
                   total_fans_acquired: int, total_fans_requirement: int) -> Tuple[bool, int, int]:
    """Execute the complete career workflow including skill purchase"""
    log_info(f"=== Executing Complete Career Workflow ===")
    
    # Extract fans and skill points first
    screenshot = take_screenshot()
    restart_config = load_restart_config()
    ignore_end_skill_purchase = restart_config.get("ignore_end_skill_purchase", False)
    if ignore_end_skill_purchase:
        skill_points = 0
        log_info("End career skill purchase ignored by config")
    else:
        skill_points = extract_skill_points(screenshot)
    
    # Handle notification and fan merging
    run_fans, total_fans_acquired = notify_run_completion(
        screenshot, current_restart_count, max_restart_times, total_fans_acquired
    )
    
    # Increment restart count first (this run just completed)
    current_restart_count += 1
    log_info(f"Restart count: {current_restart_count}/{max_restart_times}")
    
    # Check if we should continue
    should_continue, reason = should_continue_restarting(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    if not should_continue:
        log_info(f"Career completion criteria met: {reason}")
        return False, current_restart_count, total_fans_acquired
    
    # Execute skill purchase workflow (if skill points available)
    if not ignore_end_skill_purchase and skill_points > 0:
        execute_skill_purchase_workflow(skill_points)
    
    # Complete the career
    success = finish_career_completion()
    return success, current_restart_count, total_fans_acquired


def execute_restart_cycle(current_restart_count: int, max_restart_times: int, 
                         total_fans_acquired: int, total_fans_requirement: int) -> Tuple[bool, int, int, bool]:
    """Execute one complete restart cycle.
    
    Returns:
        Tuple of (success, new_restart_count, new_total_fans, career_started)
        - career_started: True if a new career was started and we should exit the restart loop
    """
    log_info(f"\n=== Restart Cycle {current_restart_count + 1}/{max_restart_times} ===")
    
    # Complete the current career
    success, new_restart_count, new_total_fans = complete_career(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    
    if not success:
        log_info(f"Failed to complete career - stopping workflow")
        return False, current_restart_count, total_fans_acquired, False
    
    # Start new career
    if not start_career():
        log_info(f"Failed to start new career")
        return False, new_restart_count, new_total_fans, False
    
    log_info(f"✓ Restart cycle {new_restart_count} completed successfully")
    # Return True with career_started=True to signal we should exit the loop
    # and let the main bot handle gameplay until next career completion
    return True, new_restart_count, new_total_fans, True


def run_restart_workflow() -> bool:
    """Main restart workflow - executes ONE complete career and starts next.
    
    This function completes the current career and starts a new one.
    After starting a new career, it returns True to let the main bot loop
    handle gameplay. The workflow will be triggered again when the next
    career completion is detected.
    
    Uses module-level _restart_state to persist counts across calls.
    """
    global _restart_state
    
    log_info(f"=== Starting Career Restart Workflow ===")
    
    # Load configuration
    restart_config = load_restart_config()
    restart_enabled = restart_config.get('restart_enabled', False)
    max_restart_times = restart_config.get('restart_times', 5)
    total_fans_requirement = restart_config.get('total_fans_requirement', 0)
    
    log_info(f"Restart enabled: {restart_enabled}")
    log_info(f"Max restarts: {max_restart_times}")
    log_info(f"Total fans requirement: {total_fans_requirement}")
    
    if not restart_enabled:
        log_info(f"Restart is disabled in config")
        return False
    
    # Use persistent state
    current_restart_count = _restart_state['restart_count']
    total_fans_acquired = _restart_state['total_fans_acquired']
    
    log_info(f"Current session state: {current_restart_count} restarts, {total_fans_acquired} total fans")
    
    # Check if we should continue
    should_continue, reason = should_continue_restarting(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    if not should_continue:
        log_info(f"Restart criteria met: {reason}")
        reset_restart_state()  # Reset for next session
        return False
    
    # Execute one restart cycle
    success, new_restart_count, new_total_fans, career_started = execute_restart_cycle(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    
    if not success:
        log_info(f"Restart cycle failed")
        return False
    
    # Update persistent state
    _restart_state['restart_count'] = new_restart_count
    _restart_state['total_fans_acquired'] = new_total_fans
    _restart_state['session_active'] = True
    
    if career_started:
        # New career was started - return True to let main bot handle gameplay
        # The restart workflow will be triggered again when career completion is detected
        log_info(f"=== New career started - returning control to main bot ===")
        log_info(f"Session progress: {new_restart_count}/{max_restart_times} restarts, {new_total_fans} total fans")
        return True
    
    log_info(f"=== Career Restart Workflow Complete ===")
    log_info(f"Total restarts completed: {new_restart_count}")
    log_info(f"Total fans acquired: {new_total_fans}")
    reset_restart_state()  # Reset for next session
    
    return True


def career_lobby_check(screenshot=None) -> bool:
    """Check if we should restart career from career lobby"""
    # Load configuration
    restart_config = load_restart_config()
    restart_enabled = restart_config.get('restart_enabled', False)
    
    # Check if complete career screen is visible
    if check_complete_career_screen(screenshot):
        # Even if restart is disabled, we might want to send the webhook (User Request)
        if not restart_enabled:
            log_info("Restart is disabled but Career Completion detected - Sending Webhook")
            # For single run, run_number=1, max_runs=1 (conceptually)
            notify_run_completion(screenshot, 0, 1, 0)
            log_info(f"Restart is disabled - stopping bot after webhook")
            return False

        log_info(f"Complete Career screen detected - starting restart workflow")
        return run_restart_workflow()
    
    if not restart_enabled:
        log_info(f"Restart is disabled - stopping bot")
        return False
    
    return True  # Continue with normal career lobby



