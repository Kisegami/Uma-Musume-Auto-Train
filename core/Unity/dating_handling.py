"""
Dating handling module for Unity version.

Handles dating functionality when dating opportunities are available.
Dating can replace recreation/rest actions when available.
"""

import time
import os
from utils.vision.recognizer import locate_on_screen, match_template
from utils.inputs.input import tap
from utils.capture.screenshot import take_screenshot
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.vision.template_matching import wait_for_image
from core.Unity.state import check_dating_available
from utils.core.config_loader import load_main_config



def do_dating():
    """
    Perform dating action.
    
    Flow:
    1. Wait for tazuna_hint to confirm we're in lobby
    2. Tap recreation button
    3. Wait 200ms
    4. Check for cancel button (normal recreation screen)
    5. If cancel found, tap trainee_date.png
    6. Otherwise, wait and tap pal_date.png
    
    Returns:
        bool: True if dating was successfully initiated, False otherwise
    """
    log_debug(f"Starting dating workflow...")
    log_info(f"Starting dating workflow...")
    
    try:
        # Step 0: Wait for tazuna_hint to confirm we're in the lobby
        log_debug(f"Waiting for tazuna_hint to confirm we're in lobby...")
        tazuna_hint = wait_for_image("assets/ui/tazuna_hint.png", timeout=10, confidence=0.9)
        if not tazuna_hint:
            log_warning(f"tazuna_hint not found after waiting - may not be in lobby")
            # Take screenshot and save debug image
            screenshot = take_screenshot()
            debug_filename = "debug_no_tazuna_hint_found.png"
            screenshot.save(debug_filename)
            log_error(f"Saved debug screenshot to: {debug_filename}")
            log_error(f"Stopping bot execution - tazuna_hint not found")
            raise RuntimeError(f"tazuna_hint not found. Debug image saved to {debug_filename}")
        log_debug(f"tazuna_hint found, confirmed in lobby")
        
        # Step 1: Tap recreation button
        log_debug(f"Looking for recreation button...")
        recreation_btn = locate_on_screen("assets/buttons/recreation_btn.png", confidence=0.8)
        
        if recreation_btn:
            log_debug(f"Found recreation button at {recreation_btn}")
            log_info(f"Clicking recreation button to access dating...")
            tap(recreation_btn[0], recreation_btn[1])
            log_debug(f"Clicked recreation button")
        else:
            log_warning(f"No recreation button found - cannot access dating")
            # Take screenshot and save debug image
            screenshot = take_screenshot()
            debug_filename = "debug_no_recreation_button_found.png"
            screenshot.save(debug_filename)
            log_error(f"Saved debug screenshot to: {debug_filename}")
            log_error(f"Stopping bot execution - recreation button not found")
            raise RuntimeError(f"Recreation button not found. Debug image saved to {debug_filename}")
        
        # Step 2: Wait 200ms before checking
        time.sleep(0.2)
        
        # Step 3: Take screenshot and check for cancel button (normal recreation screen)
        log_debug(f"Checking for normal recreation screen (cancel button)...")
        screenshot = take_screenshot()
        cancel_matches = match_template(screenshot, "assets/buttons/cancel_btn.png", confidence=0.8)
        
        if cancel_matches:
            # Step 4: Normal recreation screen detected, tap trainee_date.png
            log_debug(f"Normal recreation screen detected, selecting trainee date...")
            log_info(f"Normal recreation screen detected, selecting trainee date...")
            
            trainee_date_btn = locate_on_screen("assets/ui/trainee_date.png", confidence=0.8)
            if trainee_date_btn:
                log_debug(f"Found trainee date button at {trainee_date_btn}")
                tap(trainee_date_btn[0], trainee_date_btn[1])
                log_info(f"Selected trainee date")
                return True
            else:
                log_warning(f"Trainee date button not found after detecting cancel button")
                return False
        else:
            # Step 5: No cancel button, wait a bit more and tap pal_date.png
            log_debug(f"No cancel button found, waiting for dating screen...")
            time.sleep(0.5)  # Wait a bit more for screen to load
            
            screenshot = take_screenshot()
            pal_date_btn = locate_on_screen("assets/ui/pal_date.png", confidence=0.8)
            
            if pal_date_btn:
                log_debug(f"Found pal date button at {pal_date_btn}")
                log_info(f"Selecting pal date...")
                tap(pal_date_btn[0], pal_date_btn[1])
                log_info(f"Selected pal date")
                return True
            else:
                log_warning(f"Pal date button not found - dating screen may not have loaded")
                return False
                
    except RuntimeError as e:
        # Re-raise RuntimeError to stop the bot (e.g., when recreation button not found)
        raise
    except Exception as e:
        log_error(f"Dating workflow failed: {e}")
        return False


def should_use_dating_for_mood(screenshot=None):
    """
    Check if dating should be used instead of recreation for mood improvement.
    
    Dating is always preferred over normal recreation when available.
    
    Args:
        screenshot: Optional existing screenshot. If None, a new one is taken.
    
    Returns:
        bool: True if dating is available, False otherwise
    """
    try:
        # Check if dating is available - always use it if available since dating > recreation
        dating_available = check_dating_available(screenshot)
        if dating_available:
            log_debug(f"Dating is available - will use dating for mood (dating > recreation)")
            return True
        else:
            log_debug(f"Dating is not available - will use normal recreation")
            return False
            
    except Exception as e:
        log_debug(f"Error checking dating availability: {e}")
        return False


def should_use_dating_for_rest(screenshot=None):
    """
    Check if dating should be used instead of rest.
    
    This checks:
    1. If dating is available
    2. If dating is enabled in config (use_dating_instead_of_rest)
    
    Args:
        screenshot: Optional existing screenshot. If None, a new one is taken.
    
    Returns:
        bool: True if dating should be used instead of rest, False otherwise
    """
    try:
        # Load config
        config = load_main_config()
        
        # Check if dating should replace rest
        replace_rest = config.get("dating", {}).get("use_dating_instead_of_rest", False)
        if not replace_rest:
            log_debug(f"Dating replacement for rest is disabled in config")
            return False
        
        # Check if dating is available
        dating_available = check_dating_available(screenshot)
        if dating_available:
            log_debug(f"Dating is available and replace_rest is enabled - will use dating instead of rest")
            return True
        else:
            log_debug(f"Dating is not available - will use normal rest")
            return False
            
    except Exception as e:
        log_debug(f"Error checking dating for rest: {e}")
        return False

