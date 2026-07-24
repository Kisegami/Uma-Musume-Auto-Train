import time
from core.Grandlive.skill_recognizer import take_screenshot, recognize_skill_up_locations
from utils.inputs.input import tap, tap_on_image
from utils.inputs.skill_swipe import swipe_skill_list_down_slow
from core.Grandlive.skill_purchase_optimizer import fuzzy_match_skill_name
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config
from utils.vision.recognizer import locate_on_screen
from utils.vision.template_matching import wait_for_image

# Load config and check debug mode
_config = load_main_config()
DEBUG_MODE = _config.get("debug_mode", False)

BACK_BUTTON_TEMPLATE = "assets/buttons/back_btn.png"
CLOSE_BUTTON_TEMPLATE = "assets/buttons/close.png"
SKILLS_LEARNED_CLOSE_FALLBACK = (540, 1250)


# Global cache for skill points to avoid re-detection
_skill_points_cache = None
_cache_timestamp = 0
_cache_lifetime = 300  # Cache valid for 5 minutes


def cache_skill_points(points: int):
    """Cache skill points for reuse (called from race day detection)"""
    global _skill_points_cache, _cache_timestamp
    _skill_points_cache = points
    _cache_timestamp = time.time()
    log_debug(f"Cached skill points: {points}")

def get_cached_skill_points() -> int | None:
    """Get cached skill points if still valid, None if expired/missing"""
    global _skill_points_cache, _cache_timestamp
    if _skill_points_cache is None:
        return None
    if time.time() - _cache_timestamp > _cache_lifetime:
        log_debug(f"Skill points cache expired")
        _skill_points_cache = None
        return None
    log_debug(f"Using cached skill points: {_skill_points_cache}")
    return _skill_points_cache

def extract_skill_points(screenshot=None):
    """
    Extract available skill points from the screen using OCR with enhanced preprocessing.
    First checks cache, then falls back to OCR detection.
    
    Args:
        screenshot: PIL Image (optional, will take new screenshot if not provided)
    
    Returns:
        int: Available skill points, or 0 if extraction fails
    """
    # Check cache first
    cached = get_cached_skill_points()
    if cached is not None:
        log_info(f"Using cached skill points: {cached}")
        return cached

    try:
        if screenshot is None:
            from utils.capture.screenshot import take_screenshot
            screenshot = take_screenshot()
        
        # Skill points region: 825, 605, 936, 656 (width: 111, height: 51)
        skill_points_region = (825, 605, 936, 656)
        
        # Crop the skill points region
        points_crop = screenshot.crop(skill_points_region)
        
        # Save original debug image (only when debug mode is enabled)
        if DEBUG_MODE:
            points_crop.save("debug_skill_points.png")
            log_debug(f"Saved skill points debug image: debug_skill_points.png")
        
        # Optimized OCR - precise region makes simple approach work perfectly
        from core.Grandlive.ocr import extract_text, extract_number
        skill_points_raw = extract_text(points_crop)
        log_debug(f"OCR result: '{skill_points_raw}'")
        
        # Fallback with digits-only if simple OCR fails (rare with current precision)
        if not skill_points_raw:
            log_debug(f"Fallback: Using enhanced OCR with digits-only filter")
            enhanced_crop = enhance_image_for_ocr(points_crop)
            skill_points_raw = extract_number(enhanced_crop, config='--psm 8 -c tessedit_char_whitelist=0123456789')
            log_debug(f"Fallback result: '{skill_points_raw}'")
        
        # Clean and extract numbers
        skill_points = clean_skill_points(skill_points_raw)
        log_info(f"Available skill points: {skill_points}")
        
        # Cache the result for future use
        cache_skill_points(skill_points)
        return skill_points
        
    except Exception as e:
        log_error(f"Error extracting skill points: {e}")
        return 0

def clean_skill_points(text):
    """
    Clean and extract skill points from OCR text.
    
    Args:
        text: Raw OCR text
    
    Returns:
        int: Extracted skill points
    """
    if not text:
        return 0
    
    import re
    # Normalize common OCR confusions before extracting digits
    # Treat backslash as '1' (e.g., 77\ -> 771)
    text = text.replace('\\', '1')
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Extract all numbers
    numbers = re.findall(r'\d+', text)
    
    if numbers:
        # Return the largest number found (skill points are usually the biggest number)
        skill_points = max(int(num) for num in numbers)
        return skill_points
    
    return 0

def enhance_image_for_ocr(image):
    """
    Simple image enhancement for OCR fallback (rarely needed with precise region).
    
    Args:
        image: PIL Image
    
    Returns:
        PIL Image: Enhanced image
    """
    try:
        from PIL import ImageEnhance
        # Convert to grayscale and resize for better OCR
        if image.mode != 'L':
            image = image.convert('L')
        
        width, height = image.size
        image = image.resize((width * 3, height * 3), Image.LANCZOS)
        
        return image
        
    except Exception as e:
        log_info(f"Error enhancing image: {e}")
        return image

def click_skill_up_button(x, y):
    """
    Click on a skill_up button at the specified coordinates.
    
    Args:
        x, y: Coordinates of the skill_up button
    
    Returns:
        bool: True if click was successful, False otherwise
    """
    try:
        result = tap(x, y)
        if result is not None:
            log_debug(f"Clicked skill_up button at ({x}, {y}")
            return True
        log_error(f"Failed to click at ({x}, {y}")
        return False
    except Exception as e:
        log_error(f"Error clicking button: {e}")
        return False

def click_image_button(
    image_path,
    description="button",
    max_attempts=10,
    wait_between_attempts=0.5,
    timeout_seconds=None,
):
    """
    Find and click a button by image template matching with retry attempts.
    
    Args:
        image_path: Path to the button image template
        description: Description for logging
        max_attempts: Maximum number of attempts to find the button
        wait_between_attempts: Seconds to wait between attempts
        timeout_seconds: Optional elapsed-time limit. When set, keep retrying until
            the timeout expires instead of stopping after max_attempts.
    
    Returns:
        bool: True if button was found and clicked, False otherwise
    """
    try:
        if timeout_seconds is None:
            log_debug(f"Looking for {description} (max {max_attempts} attempts)")
        else:
            log_debug(f"Looking for {description} (timeout {timeout_seconds}s)")
        
        start_time = time.time()
        attempt = 0
        while True:
            attempt += 1
            try:
                location = locate_on_screen(image_path, confidence=0.8)

                if location:
                    success = click_skill_up_button(location[0], location[1])
                    if success:
                        log_info(f"{description} clicked successfully (attempt {attempt})")
                        return True
                    else:
                        log_error(f"Failed to click {description} (attempt {attempt})")
                else:
                    if timeout_seconds is None:
                        log_debug(f"{description} not found (attempt {attempt}/{max_attempts})")
                    else:
                        elapsed = time.time() - start_time
                        log_debug(f"{description} not found (attempt {attempt}, {elapsed:.1f}/{timeout_seconds}s)")
                
                if timeout_seconds is None:
                    should_continue = attempt < max_attempts
                else:
                    should_continue = time.time() - start_time < timeout_seconds

                if not should_continue:
                    break

                time.sleep(wait_between_attempts)
                    
            except Exception as e:
                log_warning(f"Error in attempt {attempt}: {e}")
                if timeout_seconds is None:
                    should_continue = attempt < max_attempts
                else:
                    should_continue = time.time() - start_time < timeout_seconds

                if not should_continue:
                    break

                time.sleep(wait_between_attempts)
        
        if timeout_seconds is None:
            log_error(f"{description} not found after {max_attempts} attempts")
        else:
            log_error(f"{description} not found after {timeout_seconds}s")
        return False
            
    except Exception as e:
        log_error(f"Error finding {description}: {e}")
        return False


def dismiss_skill_result_dialog(timeout_seconds=12):
    """Dismiss the post-purchase result dialog and wait for the skill screen."""
    start_time = time.time()
    attempt = 0
    while time.time() - start_time < timeout_seconds:
        attempt += 1
        if wait_for_image(BACK_BUTTON_TEMPLATE, timeout=0.2, confidence=0.8, check_interval=0.1):
            return True

        close_location = locate_on_screen(CLOSE_BUTTON_TEMPLATE, confidence=0.75)
        if close_location:
            log_debug(f"Dismissing skill result dialog with Close button (attempt {attempt})")
            tap(close_location[0], close_location[1])
        else:
            log_debug(f"Close button template not visible; tapping result-dialog fallback (attempt {attempt})")
            tap(SKILLS_LEARNED_CLOSE_FALLBACK[0], SKILLS_LEARNED_CLOSE_FALLBACK[1])

        time.sleep(0.8)

    return wait_for_image(BACK_BUTTON_TEMPLATE, timeout=1.0, confidence=0.8, check_interval=0.2)


def fast_swipe_to_top(end_career=False):
    """
    Navigate to top of skill list by tapping back button and then skills button again.
    This is much faster than swiping multiple times.
    
    Args:
        end_career: If True, use the Grand Live completion-screen Skills button.
    """
    log_info(f"Navigating to top of skill list (back + skills button)")
    
    # Step 1: Tap back button to exit skill list
    log_debug(f"Tapping back button...")
    if tap_on_image("assets/buttons/back_btn.png", confidence=0.8, min_search=10):
        log_debug(f"Back button clicked")
        time.sleep(0.5)  # Wait for UI to respond
    else:
        log_warning(f"Back button not found, trying to continue anyway")
        time.sleep(0.5)
    
    # Step 2: Wait a moment for UI to settle
    time.sleep(0.5)
    
    # Step 3: Tap skills button again to return to top of list
    # Grand Live has a distinct Skills button on the career-completion screen.
    skill_button = (
        "assets/grandlive/skills_btn_complete.png"
        if end_career
        else "assets/buttons/skills_btn.png"
    )
    log_debug(f"Tapping skills button to return to top of list ({skill_button})...")
    if tap_on_image(skill_button, confidence=0.8, min_search=10):
        log_debug(f"Skills button clicked")
        time.sleep(1.0)  # Wait for skill list to load
    else:
        log_error(f"Skills button not found after back button")
        return
    
    log_debug(f"Successfully navigated to top of skill list")

def execute_skill_purchases(purchase_plan, max_scrolls=30, end_career=False, reset_to_top=True):
    """
    Execute the automated skill purchase plan.
    
    Args:
        purchase_plan: List of skills to purchase (from create_purchase_plan)
        max_scrolls: Maximum number of scrolls to prevent infinite loops
        end_career: If True, use the Grand Live completion-screen Skills button.
        reset_to_top: If True, reopen the skill list from the top before scanning.
            Set to False when the caller has already opened the skill list and wants
            to avoid an unnecessary back/reopen cycle (for example in API mode).
    
    Returns:
        dict: {
            'success': bool,
            'purchased_skills': [list of successfully purchased skills],
            'failed_skills': [list of skills that couldn't be found/purchased],
            'scrolls_performed': int
        }
    """
    log_info(f"EXECUTING AUTOMATED SKILL PURCHASES")
    log_info(f"=" * 60)
    
    if not purchase_plan:
        log_error(f"No skills to purchase!")
        return {
            'success': False,
            'purchased_skills': [],
            'failed_skills': [],
            'scrolls_performed': 0,
            'error': 'No skills in purchase plan'
        }
    
    log_info(f"Skills to purchase: {len(purchase_plan)}")
    for i, skill in enumerate(purchase_plan, 1):
        log_info(f"   {i}. {skill['name']} - {skill['price']} points")
    log_info(f"")
    
    purchased_skills = []
    failed_skills = []
    remaining_skills = purchase_plan.copy()
    scrolls_performed = 0
    
    try:
        # Step 1: Optionally reopen the skill list to guarantee we start from the top.
        if reset_to_top:
            fast_swipe_to_top(end_career=end_career)
        else:
            log_info(f"Using current skill list screen without reopening")
            time.sleep(0.5)
        
        # Step 2: Scroll down slowly to find and purchase skills
        log_info(f"Searching for skills to purchase")
        
        while remaining_skills and scrolls_performed < max_scrolls:
            scrolls_performed += 1
            log_info(f"\n[INFO] Scroll {scrolls_performed}/{max_scrolls}")
            log_debug(f"Looking for: {[s['name'] for s in remaining_skills]}")
            
            # Scan current screen for available skills
            result = recognize_skill_up_locations(
                confidence=0.9,
                debug_output=False,
                filter_dark_buttons=True,
                brightness_threshold=150,
                extract_skills=True
            )
            
            if 'error' in result:
                log_error(f"Error during skill detection: {result['error']}")
                break
            
            current_skills = result.get('skills', [])
            if not current_skills:
                log_debug(f"No skills found on this screen")
            else:
                log_debug(f"Found {len(current_skills)} available skills on screen")
                
                # Check if any of our target skills are on this screen
                skills_found_on_screen = []
                
                for target_skill in remaining_skills:
                    for screen_skill in current_skills:
                        # Use fuzzy matching to find target skills
                        if fuzzy_match_skill_name(screen_skill['name'], target_skill['name']):
                            skills_found_on_screen.append({
                                'target': target_skill,
                                'screen': screen_skill
                            })
                            log_info(f"Found target skill: {screen_skill['name']} (matches {target_skill['name']})")
                            break
                
                # Purchase found skills
                for match in skills_found_on_screen:
                    target_skill = match['target']
                    screen_skill = match['screen']
                    
                    # Get button coordinates
                    x, y, w, h = screen_skill['location']
                    button_center_x = x + w // 2
                    button_center_y = y + h // 2
                    
                    log_info(f"Purchasing: {screen_skill['name']}")
                    
                    # Click the skill_up button
                    if click_skill_up_button(button_center_x, button_center_y):
                        purchased_skills.append(target_skill)
                        remaining_skills.remove(target_skill)
                        log_info(f"Successfully purchased: {screen_skill['name']}")
                        
                        # Short wait after purchase
                        time.sleep(1)
                    else:
                        log_error(f"Failed to purchase: {screen_skill['name']}")
                
                # If we found and purchased skills, wait a bit longer
                if skills_found_on_screen:
                    time.sleep(1.5)
            
            # Continue scrolling if we haven't found all skills
            if remaining_skills and scrolls_performed < max_scrolls:
                log_debug(f"Scrolling down to find more skills")
                success = swipe_skill_list_down_slow(wait_before=0.1)
                if not success:
                    log_error(f"Failed to scroll, stopping search")
                    break
        
        # Step 3: Click confirm button
        if purchased_skills:
            log_info(f"\n[INFO] Purchased {len(purchased_skills)} skills, looking for confirm button")
            
            confirm_success = click_image_button("assets/buttons/confirm.png", "confirm button", max_attempts=10)
            if confirm_success:
                log_debug(f"Waiting for confirmation")
                time.sleep(1)  # Reduced wait time
                
                # Step 4: Click learn button
                log_debug(f"Looking for learn button")
                learn_success = click_image_button("assets/buttons/learn.png", "learn button", max_attempts=10)
                if learn_success:
                    log_debug(f"Waiting for learning to complete")
                    time.sleep(1)  # Reduced wait time
                    
                    # Step 5: Click close button (it can appear late on slow connections)
                    log_debug(f"Waiting for close button to appear")
                    close_success = click_image_button(
                        CLOSE_BUTTON_TEMPLATE,
                        "close button",
                        wait_between_attempts=0.5,
                        timeout_seconds=30,
                    )
                    dismissed = dismiss_skill_result_dialog()
                    if close_success and dismissed:
                        log_info(f"Skill purchase sequence completed successfully")
                    elif dismissed:
                        log_info(f"Skill purchase sequence completed; result dialog dismissed by fallback")
                    else:
                        log_warning(f"Close button not found - manual intervention may be needed")
                else:
                    log_warning(f"Learn button not found or failed to click")
            else:
                log_warning(f"Confirm button not found or failed to click")
        
        # Add any remaining skills to failed list
        failed_skills.extend(remaining_skills)
        
        # Summary
        log_info(f"\n" + "=" * 60)
        log_info(f"PURCHASE EXECUTION COMPLETE")
        log_info(f"   Successfully purchased: {len(purchased_skills)} skills")
        log_info(f"   Failed to find/purchase: {len(failed_skills)} skills")
        log_info(f"   Scrolls performed: {scrolls_performed}")
        
        if purchased_skills:
            log_info(f"\n[INFO] Purchased skills:")
            for skill in purchased_skills:
                log_info(f"   • {skill['name']} - {skill['price']} points")
        
        if failed_skills:
            log_info(f"\n[WARNING] Failed to purchase:")
            for skill in failed_skills:
                log_info(f"   • {skill['name']} - {skill['price']} points")
        
        return {
            'success': len(purchased_skills) > 0,
            'purchased_skills': purchased_skills,
            'failed_skills': failed_skills,
            'scrolls_performed': scrolls_performed
        }
        
    except Exception as e:
        log_error(f"Error during skill purchase execution: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'purchased_skills': purchased_skills,
            'failed_skills': failed_skills + remaining_skills,
            'scrolls_performed': scrolls_performed,
            'error': str(e)
        }

