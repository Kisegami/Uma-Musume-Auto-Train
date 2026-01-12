#!/usr/bin/env python3
from utils.log import log_info, log_warning, log_error, log_debug, log_success
"""
Restart Career functionality for Uma Musume Emulator Auto Train.
Handles career completion and auto-restart based on configuration.
"""

import sys
import os
import time
from typing import Dict, Any, Optional, Tuple

# Add the project root to the path so we can import our modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
SUPPORTS_DIR = os.path.join(PROJECT_ROOT, "supports")
os.makedirs(SUPPORTS_DIR, exist_ok=True)

from utils.recognizer import match_template
from utils.screenshot import take_screenshot
from utils.input import tap
from core.Ura.skill_auto_purchase import click_image_button
from core.Ura.ocr import extract_text, extract_number
from utils.config_loader import load_main_config


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
    matches = match_template(screenshot, "assets/buttons/complete_career.png", confidence=0.8)
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
    from core.Ura.skill_auto_purchase import click_image_button
    from core.Ura.skill_recognizer import scan_all_skills_with_scroll
    from core.Ura.skill_purchase_optimizer import load_skill_config, create_purchase_plan, filter_affordable_skills
    from core.Ura.skill_auto_purchase import execute_skill_purchases
    from core.Ura.skill_recognizer import deduplicate_skills
    
    # Tap end skill button
    if not click_image_button("assets/buttons/end_skill.png", "end skill button", max_attempts=5):
        log_info(f"Failed to tap end skill button")
        return
    
    time.sleep(2)
    
    # Scan for available skills
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
            affordable_skills, total_cost, remaining_points = filter_affordable_skills(purchase_plan, available_points)
            if affordable_skills:
                execute_skill_purchases(affordable_skills, end_career=True)
    
    # Return to complete career screen
    return_to_complete_career_screen()


def return_to_complete_career_screen():
    """Return to the complete career screen after skill purchase"""
    back_success = click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
    if back_success:
        time.sleep(1.5)
        return check_complete_career_screen()
    return False


def finish_career_completion() -> bool:
    """Complete the career and navigate through completion screens"""
    log_info(f"=== Completing Career ===")
    
    # Click complete career button
    if not click_image_button("assets/buttons/complete_career.png", "complete career button", max_attempts=5):
        log_info(f"Failed to click complete career button")
        return False
    
    time.sleep(0.5)
    
    # Click finish button
    if not click_image_button("assets/buttons/finish.png", "finish button", max_attempts=5):
        log_info(f"Failed to click finish button")
        return False
    
    time.sleep(0.5)
    
    # Navigate through completion screens with spam-tap strategy
    start_time = time.time()
    max_duration_seconds = 120  # Safety timeout to avoid infinite loop

    while time.time() - start_time < max_duration_seconds:
        # Always check if we're already on Career Home
        screenshot = take_screenshot()
        career_home_matches = match_template(screenshot, "assets/buttons/Career_Home.png", confidence=0.8)
        if career_home_matches:
            log_info(f"✓ Career Home screen detected - Career completion successful")
            return True

        # Look for the first actionable button (Next -> Close -> To Home)
        first_button = None
        first_button_name = None
        for template_path, name in [
            ("assets/buttons/next_btn.png", "next button"),
            ("assets/buttons/close.png", "close button"),
            ("assets/buttons/to_home.png", "to_home button"),
        ]:
            matches = match_template(screenshot, template_path, confidence=0.8)
            if matches:
                x, y, w, h = matches[0]
                cx, cy = x + w // 2, y + h // 2
                first_button = (cx, cy)
                first_button_name = name
                break

        if first_button is not None:
            cx, cy = first_button
            log_info(f"{first_button_name} detected at ({cx}, {cy}) - spamming taps for 10s")

            # Spam tap on detected button position for 10 seconds
            spam_end = time.time() + 10
            while time.time() < spam_end:
                tap(cx, cy)
                time.sleep(0.08)

            # After spam, check Career Home briefly
            for _ in range(5):
                screenshot = take_screenshot()
                career_home_matches = match_template(screenshot, "assets/buttons/Career_Home.png", confidence=0.8)
                if career_home_matches:
                    log_info(f"✓ Career Home screen detected - Career completion successful")
                    return True
                time.sleep(1.0)

            # Not at home yet; tap 2 more times then continue loop
            tap(cx, cy)
            time.sleep(0.1)
            tap(cx, cy)
            time.sleep(0.3)
            continue

        # If nothing actionable found, short wait and retry
        time.sleep(0.7)

    log_info(f"Failed to complete career navigation")
    return False


def load_config():
    """Load configuration from config.json"""
    try:
        return load_main_config()
    except Exception as e:
        log_info(f"Error loading config: {e}")
        return {}


from utils.template_matching import wait_for_image


def filter_support():
    """Filter support cards based on configuration."""
    log_info(f"Filtering support cards...")
    
    config = load_config()
    auto_start_career = config.get('auto_start_career', {})

    # Use template selection when enabled
    use_templates = auto_start_career.get('use_support_templates', False)
    template_name = auto_start_career.get('support_template_name', '')
    log_info(f"Support template toggle: {use_templates}, template name: '{template_name}'")
    if use_templates:
        template_path = os.path.join(SUPPORTS_DIR, template_name) if template_name else None
        if template_path and os.path.exists(template_path):
            log_info(f"Support template mode ON -> using '{template_name}' at '{template_path}'")
            screenshot = take_screenshot()
            matches = match_template(screenshot, template_path, confidence=0.7)
            log_info(f"Template matches found: {len(matches) if matches else 0}")
            if matches:
                x, y, w, h = matches[0]
                center = (x + w//2, y + h//2)
                tap(center[0], center[1])
                time.sleep(0.5)
                return
            else:
                log_warning("Support template enabled but no match found on screen; falling back to following card.")
        else:
            log_warning("Support template enabled but template file missing or not set; falling back to following card.")

    # Fallback: select first following card
    time.sleep(1)
    screenshot = take_screenshot()
    following_matches = match_template(screenshot, "assets/icons/following.png", confidence=0.8)
    
    if following_matches:
        following_matches.sort(key=lambda match: match[1])
        x, y, w, h = following_matches[0]
        center = (x + w//2, y + h//2)
        tap(center[0], center[1])
        time.sleep(0.5)


def restore_tp() -> bool:
    """Restore TP using TP bottle when out of TP.
    
    Returns:
        bool: True if TP restored successfully, False if no bottles available
    """
    log_info("=== Restoring TP ===")
    
    # Step 1: Tap restore button
    if not click_image_button("assets/buttons/restore_btn.png", "restore button", max_attempts=5):
        log_warning("Failed to tap restore button")
        return False
    
    time.sleep(1)
    
    # Step 2: Wait for TP bottle to appear
    tp_bottle_matches = wait_for_image("assets/icons/tp_bottle.png", timeout=10, confidence=0.8)
    if not tp_bottle_matches:
        log_error("Out of TP Bottle")
        return False
    
    # Step 3: Calculate Use button position (offset from bottle)
    # TP Bottle at (131, 481) → Use button at (912, 481)
    # X offset = 912 - 131 = 781
    bottle_x, bottle_y = tp_bottle_matches[0], tp_bottle_matches[1]
    use_btn_x = bottle_x + 781
    use_btn_y = bottle_y
    
    log_info(f"TP bottle at ({bottle_x}, {bottle_y}), tapping Use at ({use_btn_x}, {use_btn_y})")
    tap(use_btn_x, use_btn_y)
    time.sleep(1)
    
    # Step 4: Tap OK button
    if not click_image_button("assets/buttons/ok_restore.png", "OK button", max_attempts=10):
        log_warning("Failed to tap OK button")
        return False
    
    time.sleep(0.5)
    
    # Step 5: Tap Close button
    if not click_image_button("assets/buttons/close.png", "close button", max_attempts=10):
        log_warning("Failed to tap close button")
        return False
    
    log_info("✓ TP restored successfully")
    return True


def skip_check():
    """Check which skip button is on screen and adjust accordingly."""
    log_info(f"Checking skip button...")
    
    screenshot = take_screenshot()
    
    skip_variants = [
        ("assets/buttons/skip_off.png", "Skip Off"),
        ("assets/buttons/skip_x1.png", "Skip x1"),
        ("assets/buttons/skip_x2.png", "Skip x2")
    ]
    
    best_match = None
    best_confidence = 0
    
    for template_path, variant_name in skip_variants:
        if os.path.exists(template_path):
            from utils.recognizer import max_match_confidence
            confidence = max_match_confidence(screenshot, template_path)
            if confidence and confidence > best_confidence:
                best_confidence = confidence
                best_match = template_path
    
    if best_match and best_confidence > 0.7:
        if "skip_off" in best_match:
            matches = match_template(screenshot, best_match, confidence=0.7)
            if matches:
                x, y, w, h = matches[0]
                center = (x + w//2, y + h//2)
                tap(center[0], center[1])
                time.sleep(0.1)
                tap(center[0], center[1])
        elif "skip_x1" in best_match:
            matches = match_template(screenshot, best_match, confidence=0.7)
            if matches:
                x, y, w, h = matches[0]
                center = (x + w//2, y + h//2)
                tap(center[0], center[1])


def start_career() -> bool:
    """Start a new career using the existing start_career logic"""
    log_info(f"=== Starting New Career ===")
    
    config = load_config()
    auto_start_career = config.get('auto_start_career', {})
    include_guests_legacy = auto_start_career.get('include_guests_legacy', False)
    
    try:
        # Step 1: Tap Career Home and wait 10s
        career_home_matches = match_template(take_screenshot(), "assets/buttons/Career_Home.png", confidence=0.8)
        if career_home_matches:
            x, y, w, h = career_home_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(10)
        else:
            log_info(f"Career Home not found")
            return False
        
        # Step 2: Tap Next button twice
        for i in range(2):
            next_matches = match_template(take_screenshot(), "assets/buttons/next_btn.png", confidence=0.8)
            if next_matches:
                x, y, w, h = next_matches[0]
                center = (x + w//2, y + h//2)
                tap(center[0], center[1])
                time.sleep(1)
            else:
                return False
        
        # Step 3: Tap Next button
        next_matches = match_template(take_screenshot(), "assets/buttons/next_btn.png", confidence=0.8)
        if next_matches:
            x, y, w, h = next_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(1)
        else:
            return False
        
        # Step 4: Tap Friend Support Choose
        log_info(f"Friend Support...")
        friend_support_matches = match_template(take_screenshot(), "assets/buttons/Friend_support_choose.png", confidence=0.8)
        if friend_support_matches:
            x, y, w, h = friend_support_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(1)
        else:
            return False
        
        # Step 5: Filter support
        log_info(f"Filtering...")
        filter_support()
        time.sleep(1)
        
        # Step 6: Start Career 1
        start_career_1_matches = match_template(take_screenshot(), "assets/buttons/start_career_1.png", confidence=0.8)
        if start_career_1_matches:
            x, y, w, h = start_career_1_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
            time.sleep(0.5)
            
            # Check for insufficient TP (restore button appears)
            restore_matches = match_template(take_screenshot(), "assets/buttons/restore_btn.png", confidence=0.8)
            if restore_matches:
                auto_charge = auto_start_career.get('auto_charge_tp', False)
                if auto_charge:
                    log_info("Insufficient TP detected - attempting auto restore")
                    if not restore_tp():
                        log_error("TP restore failed - Out of TP Bottle")
                        return False
                    # After restore, tap Start Career 1 again
                    time.sleep(1)
                    start_career_1_matches = match_template(take_screenshot(), "assets/buttons/start_career_1.png", confidence=0.8)
                    if start_career_1_matches:
                        x, y, w, h = start_career_1_matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
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
        start_career_2_matches = match_template(take_screenshot(), "assets/buttons/start_career_2.png", confidence=0.8)
        if start_career_2_matches:
            x, y, w, h = start_career_2_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
        else:
            return False
        
        # Step 8: Wait for skip button and double tap
        log_info(f"Skip button...")
        skip_matches = wait_for_image("assets/buttons/skip_btn.png", timeout=30, confidence=0.8)
        if skip_matches:
            tap(skip_matches[0], skip_matches[1])
            time.sleep(0.1)
            tap(skip_matches[0], skip_matches[1])
            time.sleep(0.5)
        else:
            return False
        
        # Step 9: Wait for confirm button
        log_info(f"Confirm button...")
        confirm_matches = wait_for_image("assets/buttons/confirm.png", timeout=30, confidence=0.8)
        if not confirm_matches:
            return False
        
        # Step 10: Tap coordinates
        tap(213, 939)
        time.sleep(0.5)
        
        # Step 11: Skip check
        skip_check()
        time.sleep(0.5)
        
        # Step 12: Tap confirm
        confirm_matches = match_template(take_screenshot(), "assets/buttons/confirm.png", confidence=0.8)
        if confirm_matches:
            x, y, w, h = confirm_matches[0]
            center = (x + w//2, y + h//2)
            tap(center[0], center[1])
        else:
            return False
        
        # Step 13: Wait for Tazuna hint
        tazuna_hint_matches = wait_for_image("assets/ui/tazuna_hint.png", timeout=60, confidence=0.8)
        if tazuna_hint_matches:
            log_info(f"Career start completed!")
            return True
        else:
            return False
            
    except Exception as e:
        log_error(f"{e}")
        return False


def complete_career(current_restart_count: int, max_restart_times: int, 
                   total_fans_acquired: int, total_fans_requirement: int) -> Tuple[bool, int, int]:
    """Execute the complete career workflow including skill purchase"""
    log_info(f"=== Executing Complete Career Workflow ===")
    
    # Extract fans and skill points first
    screenshot = take_screenshot()
    run_fans = extract_total_fans(screenshot)
    skill_points = extract_skill_points(screenshot)
    
    # Add fans to total
    total_fans_acquired += run_fans
    log_info(f"Total fans acquired so far: {total_fans_acquired}")
    
    # Send Discord webhook notification
    try:
        from utils.discord_webhook import is_webhook_enabled, send_run_complete_webhook
        if is_webhook_enabled():
            run_number = current_restart_count + 1
            average_per_run = total_fans_acquired // run_number if run_number > 0 else 0
            send_run_complete_webhook(
                run_number=run_number,
                max_runs=max_restart_times,
                fans_this_run=run_fans,
                session_total=total_fans_acquired,
                today_total=total_fans_acquired,
                average_per_run=average_per_run,
                screenshot=screenshot
            )
    except Exception as e:
        log_warning(f"Failed to send Discord webhook: {e}")
    
    # Check if we should continue
    should_continue, reason = should_continue_restarting(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    if not should_continue:
        log_info(f"Career completion criteria met: {reason}")
        return False, current_restart_count, total_fans_acquired
    
    # Increment restart count
    current_restart_count += 1
    log_info(f"Restart count: {current_restart_count}/{max_restart_times}")
    
    # Execute skill purchase workflow (if skill points available)
    if skill_points > 0:
        execute_skill_purchase_workflow(skill_points)
    
    # Complete the career
    success = finish_career_completion()
    return success, current_restart_count, total_fans_acquired


def execute_restart_cycle(current_restart_count: int, max_restart_times: int, 
                         total_fans_acquired: int, total_fans_requirement: int) -> Tuple[bool, int, int]:
    """Execute one complete restart cycle"""
    log_info(f"\n=== Restart Cycle {current_restart_count + 1}/{max_restart_times} ===")
    
    # Complete the current career
    success, new_restart_count, new_total_fans = complete_career(
        current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
    )
    
    if not success:
        log_info(f"Failed to complete career - stopping workflow")
        return False, current_restart_count, total_fans_acquired
    
    # Start new career
    if not start_career():
        log_info(f"Failed to start new career")
        return False, new_restart_count, new_total_fans
    
    log_info(f"✓ Restart cycle {new_restart_count} completed successfully")
    return True, new_restart_count, new_total_fans


def run_restart_workflow() -> bool:
    """Main restart workflow - continues until criteria are met"""
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
    
    # Runtime state - managed in function scope
    current_restart_count = 0
    total_fans_acquired = 0
    
    # Continue restarting until criteria are met
    while True:
        should_continue, reason = should_continue_restarting(
            current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
        )
        if not should_continue:
            log_info(f"Restart criteria met: {reason}")
            break
        
        success, new_restart_count, new_total_fans = execute_restart_cycle(
            current_restart_count, max_restart_times, total_fans_acquired, total_fans_requirement
        )
        
        if not success:
            # Check if we reached completion criteria
            should_continue, reason = should_continue_restarting(
                new_restart_count, max_restart_times, new_total_fans, total_fans_requirement
            )
            if not should_continue:
                log_info(f"Career completion criteria met: {reason}")
                break
            else:
                log_info(f"Restart cycle failed")
                break
        
        # Update state for next iteration
        current_restart_count = new_restart_count
        total_fans_acquired = new_total_fans
    
    log_info(f"=== Career Restart Workflow Complete ===")
    log_info(f"Total restarts completed: {current_restart_count}")
    log_info(f"Total fans acquired: {total_fans_acquired}")
    
    return True


def career_lobby_check(screenshot=None) -> bool:
    """Check if we should restart career from career lobby"""
    # Load configuration
    restart_config = load_restart_config()
    restart_enabled = restart_config.get('restart_enabled', False)
    
    if not restart_enabled:
        log_info(f"Restart is disabled - stopping bot")
        return False
    
    # Check if complete career screen is visible
    if check_complete_career_screen(screenshot):
        log_info(f"Complete Career screen detected - starting restart workflow")
        return run_restart_workflow()
    
    return True  # Continue with normal career lobby


