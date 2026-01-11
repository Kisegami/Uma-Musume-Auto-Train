import re
import time
import os

from PIL import Image, ImageEnhance
from utils.screenshot import capture_region, enhanced_screenshot, enhanced_screenshot_for_failure, enhanced_screenshot_for_year, take_screenshot
from core.Unity.ocr import extract_text, extract_number
from utils.recognizer import match_template, max_match_confidence
from core.Unity.skill_auto_purchase import execute_skill_purchases, click_image_button, extract_skill_points
from core.Unity.skill_recognizer import scan_all_skills_with_scroll
from core.Unity.skill_purchase_optimizer import load_skill_config, create_purchase_plan, filter_affordable_skills

from utils.constants_unity import (
    SUPPORT_CARD_ICON_REGION, TURN_REGION, FAILURE_REGION, YEAR_REGION, 
    CRITERIA_REGION, SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION,
    SKILL_PTS_REGION, FAILURE_REGION_SPD, FAILURE_REGION_STA, FAILURE_REGION_PWR, FAILURE_REGION_GUTS, FAILURE_REGION_WIT
)

from utils.log import log_debug, log_info, log_warning, log_error
from utils.config_loader import load_main_config

# Load config and check debug mode
config = load_main_config()
DEBUG_MODE = config.get("debug_mode", False)
from utils.template_matching import deduplicated_matches

# Get Stat
def stat_state(screenshot=None):
    stat_regions = {
        "spd": SPD_REGION,
        "sta": STA_REGION,
        "pwr": PWR_REGION,
        "guts": GUTS_REGION,
        "wit": WIT_REGION
    }

    result = {}
    for stat, region in stat_regions.items():
        img = enhanced_screenshot(region, screenshot)
        val = extract_number(img)
        digits = ''.join(filter(str.isdigit, val))
        result[stat] = int(digits) if digits.isdigit() else 0
    return result


def check_dating_available(screenshot=None, confidence: float = 0.8) -> bool:
    """
    Check if a dating opportunity is available by scanning for the dating icon on screen.

    Uses template matching against assets/icons/dating.png.

    Args:
        screenshot: Optional existing screenshot. If None, a new one is taken.
        confidence: Template matching confidence threshold.

    Returns:
        bool: True if the dating icon is found, False otherwise.
    """
    try:
        if screenshot is None:
            screenshot = take_screenshot()

        template_path = os.path.join("assets", "icons", "dating.png")

        matches = match_template(screenshot, template_path, confidence)
        found = bool(matches and len(matches) > 0)

        log_debug(f"Dating icon found: {found}")

        if DEBUG_MODE and found:
            try:
                x, y, w, h = matches[0]
                crop = screenshot.crop((x, y, x + w, y + h))
                crop.save("debug_dating_icon.png")
                log_debug("Saved dating icon debug image to debug_dating_icon.png")
            except Exception as e:
                log_debug(f"Failed to save dating debug image: {e}")

        return found
    except Exception as e:
        log_debug(f"check_dating_available failed: {e}")
        return False


# Old OCR fuzzy mood helper removed after switching to template-based detection

def check_mood(screenshot=None):
    """Detect mood using template matching in a fixed region.

    Uses the new template-based method instead of OCR. Returns one of
    MOOD_LIST values, or "UNKNOWN" if confidence is too low.
    """
    try:
        # Use provided screenshot or take a fresh one
        if screenshot is None:
            screenshot = take_screenshot()

        # Region (left, top, right, bottom) and its (x, y, w, h) variant
        region_pil = (774, 203, 1080, 287)
        x, y = region_pil[0], region_pil[1]
        region_cv = (x, y, region_pil[2] - region_pil[0], region_pil[3] - region_pil[1])

        templates = {
            "AWFUL": os.path.join("assets", "mood", "awful.png"),
            "BAD": os.path.join("assets", "mood", "bad.png"),
            "NORMAL": os.path.join("assets", "mood", "normal.png"),
            "GOOD": os.path.join("assets", "mood", "good.png"),
            "GREAT": os.path.join("assets", "mood", "great.png"),
        }

        # Allow threshold override via config; default to 0.55
        threshold = float(config.get("mood_template_threshold", 0.55))

        best_label = None
        best_score = -1.0
        scores = {}

        for label, path in templates.items():
            score = float(max_match_confidence(screenshot, path, region=region_cv) or 0.0)
            scores[label] = score
            if score > best_score:
                best_label = label
                best_score = score

        if DEBUG_MODE:
            log_debug(f"Mood scores: {scores}")

        if best_label is None or best_score < threshold:
            log_debug(f"Mood confidence too low: best={best_label} score={best_score:.3f} threshold={threshold:.2f}")
            return "UNKNOWN"

        return best_label
    except Exception as e:
        log_debug(f"Template mood detection failed: {e}")
        return "UNKNOWN"

def check_turn(screenshot=None):
    """Fast turn detection with minimal OCR"""
    log_debug(f"Starting turn detection...")
    
    try:
        turn_img = enhanced_screenshot(TURN_REGION, screenshot)
        log_debug(f"Turn region screenshot taken: {TURN_REGION}")
        
        # Save the turn region image for debugging
        turn_img.save("debug_turn_region.png")
        log_debug(f"Saved turn region image to debug_turn_region.png")
        
        # Apply additional enhancement for better digit recognition
        from PIL import ImageEnhance
        
        # Increase contrast more aggressively for turn detection
        contrast_enhancer = ImageEnhance.Contrast(turn_img)
        turn_img = contrast_enhancer.enhance(2.0)  # More aggressive contrast
        
        # Increase sharpness to make digits clearer
        sharpness_enhancer = ImageEnhance.Sharpness(turn_img)
        turn_img = sharpness_enhancer.enhance(2.0)
        
        # Save the enhanced version
        turn_img.save("debug_turn_enhanced.png")
        log_debug(f"Saved enhanced turn image to debug_turn_enhanced.png")
        
        # Use the best method found in testing: basic processing + PSM 7
        import re
        
        # Apply basic grayscale processing (like test_turn_basic_grayscale)
        turn_img = turn_img.convert("L")
        turn_img = turn_img.resize((turn_img.width * 2, turn_img.height * 2), Image.BICUBIC)
        
        # Use PSM 7 (single line) which had 94% confidence in testing
        turn_text = extract_text(turn_img, config='--oem 3 --psm 7')
        log_debug(f"Turn OCR raw result: '{turn_text}'")
        
        # Check for "Race Day" first (before character replacements that would corrupt it)
        if "Race Day" in turn_text or "RaceDay" in turn_text or "Race Da" in turn_text:
            log_debug(f"Race Day detected: {turn_text}")
            return "Race Day"
        
        # Character replacements for common OCR errors (only for digit extraction)
        original_text = turn_text
        turn_text = turn_text.replace('y', '9').replace(']', '1').replace('l', '1').replace('I', '1').replace('o', '8').replace('O', '0').replace('/', '7').replace('®', '9')
        log_debug(f"Turn OCR after character replacement: '{turn_text}' (was '{original_text})')")
        
        # Extract all consecutive digits (not just first digit)
        digit_match = re.search(r'(\d+)', turn_text)
        if digit_match:
            turn_num = int(digit_match.group(1))
            log_debug(f"Turn OCR result: {turn_num} (from '{turn_text})')")
            return turn_num
        
        log_debug(f"No digits found in turn text: '{turn_text}', defaulting to 1")
        return 1  # Default to turn 1
        
    except Exception as e:
        log_debug(f"Turn detection failed with error: {e}")
        return 1

def check_current_year(screenshot=None):
    """Fast year detection using regular screenshot"""
    year_img = enhanced_screenshot(YEAR_REGION, screenshot)
    
    text = extract_text(year_img)
    
    if text:
        # Clean OCR result - correct common OCR errors
        if "Pre-Debu" in text:
            text = text.replace("Pre-Debu", "Pre-Debut")
        
        log_debug(f"Year OCR result: '{text}'")
        return text
    
    return "Unknown Year"

def check_criteria(screenshot=None):
    """Enhanced criteria detection"""
    criteria_img = enhanced_screenshot(CRITERIA_REGION, screenshot)
    
    # Use single, fast OCR configuration
    text = extract_text(criteria_img, config='--oem 3 --psm 7')
    
    if text:
        # Apply common OCR corrections
        text = text.replace("Entrycriteriamet", "Entry criteria met")
        text = text.replace("Entrycriteria", "Entry criteria")  
        text = text.replace("criteriamet", "criteria met")
        text = text.replace("Goalachieved", "Goal achieved")
        
        log_debug(f"Criteria OCR result: '{text}'")
    else:
        # Single fallback attempt
        fallback_text = extract_text(criteria_img)
        if fallback_text.strip():
            log_debug(f"Using fallback criteria OCR result: '{fallback_text}'")
            text = fallback_text.strip()
        else:
            text = "Unknown Criteria"
    
    return text

def check_goal_name(screenshot=None):
    """Detect the current goal name using simple Tesseract OCR.

    Captures the region (372, 113, 912, 152) and returns the recognized
    goal name as a string. Mirrors the lightweight OCR approach used in
    check_criteria (PSM 7, single line) with a single fallback to the
    shared extract_text helper.
    """
    GOAL_REGION = (357, 113, 714, 155)

    # Capture enhanced image of the goal name region for better OCR
    goal_img = enhanced_screenshot(GOAL_REGION, screenshot)

    # Save debug images if enabled
    if DEBUG_MODE:
        try:
            raw_img = capture_region(GOAL_REGION)
            raw_img.save("debug_goal_region_raw.png")
        except Exception:
            pass
        try:
            goal_img.save("debug_goal_region_enhanced.png")
        except Exception:
            pass

    # Primary OCR path: single line recognition
    text = extract_text(goal_img, config='--oem 3 --psm 7')

    if not text:
        # Fallback once to the shared OCR helper
        fallback_text = extract_text(goal_img)
        if fallback_text.strip():
            log_debug(f"Using fallback goal OCR result: '{fallback_text}'")
            text = fallback_text.strip()

    if DEBUG_MODE:
        log_debug(f"Goal name OCR result: '{text}'")

    return text



def check_skill_points(screenshot=None):
    skill_img = enhanced_screenshot(SKILL_PTS_REGION, screenshot)
    
    # Apply sharpening for better OCR accuracy
    sharpener = ImageEnhance.Sharpness(skill_img)
    skill_img_sharp = sharpener.enhance(2.5)  # Increase sharpness by 2.5x
    
    # Save debug images for skill points OCR troubleshooting (only when debug mode is enabled)
    if DEBUG_MODE:
        skill_img.save("debug_skill_points_original.png")
        skill_img_sharp.save("debug_skill_points_sharpened.png")
        log_debug(f"Saved original skill points image to debug_skill_points_original.png")
        log_debug(f"Saved sharpened skill points image to debug_skill_points_sharpened.png")
    log_debug(f"Skill points region: {SKILL_PTS_REGION}")
    
    # Use sharpened image for OCR
    skill_text = extract_number(skill_img_sharp)
    digits = ''.join(filter(str.isdigit, skill_text))
    
    log_debug(f"Skill points OCR raw result: '{skill_text}'")
    log_debug(f"Extracted digits: '{digits}'")
    
    result = int(digits) if digits.isdigit() else 0
    log_debug(f"Final skill points value: {result}")
    
    # Cache the skill points for reuse in skill auto-purchase
    if result > 0:
        from core.Unity.skill_auto_purchase import cache_skill_points
        cache_skill_points(result)
    
    return result

def check_skill_points_cap(screenshot=None):
    """Check skill points and handle cap logic (same as PC version)"""
    import tkinter as tk
    from tkinter import messagebox
    
    # Load config
    try:
        config = load_main_config()
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return True
    
    skills_config = config.get("skills", {})
    skill_point_cap = skills_config.get("skill_point_cap", 9999)
    current_skill_points = check_skill_points(screenshot)
    
    log_info(f"Current skill points: {current_skill_points}, Cap: {skill_point_cap}")
    
    if current_skill_points > skill_point_cap:
        log_warning(f"Skill points ({current_skill_points}) exceed cap ({skill_point_cap})")
        
        # Decide flow based on config
        skill_purchase_mode = skills_config.get("skill_purchase", "manual").lower()
        if skill_purchase_mode == "auto":
            log_info(f"Auto skill purchase enabled - starting automation")
            try:
                # 1) Enter skill screen
                entered = click_image_button("assets/buttons/skills_btn.png", "skills button", max_attempts=5)
                if not entered:
                    log_error(f"Could not find/open skills screen")
                    return True
                time.sleep(1.0)

                # 2) Scan skills and prepare purchase plan
                scan_result = scan_all_skills_with_scroll()
                if 'error' in scan_result:
                    log_error(f"Skill scanning failed: {scan_result['error']}")
                    # Attempt to go back anyway
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True
                all_skills = scan_result.get('all_skills', [])
                if not all_skills:
                    log_warning(f"No skills detected on skill screen")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Read current available skill points from the skill screen
                available_points = extract_skill_points()
                log_info(f"Detected available skill points: {available_points}")

                # Build purchase plan from config priorities
                skill_file = skills_config.get("skill_file", "template/skills/skills.json")
                skill_file = _resolve_skill_file_path(skill_file)
                log_info(f"Loading skills from: {skill_file}")
                cfg = load_skill_config(skill_file)
                purchase_plan = create_purchase_plan(all_skills, cfg, end_career=False)
                if not purchase_plan:
                    log_info(f"No skills from priority list are currently available")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Filter by budget if we have points
                final_plan = purchase_plan
                if isinstance(available_points, int) and available_points > 0:
                    affordable_skills, total_cost, remaining_points = filter_affordable_skills(purchase_plan, available_points)
                    final_plan = affordable_skills if affordable_skills else []
                    log_info(f"Affordable skills: {len(final_plan)}; Total cost: {total_cost}; Remaining: {remaining_points}")

                if not final_plan:
                    log_info(f"Nothing affordable to purchase at the moment")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Execute automated purchases
                exec_result = execute_skill_purchases(final_plan)
                if not exec_result.get('success'):
                    log_warning(f"Automated purchase completed with issues: {exec_result.get('error', 'unknown error')}")

                # 3) Return to lobby
                back = click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                if not back:
                    log_warning(f"Could not find back button after purchases; ensure you return to lobby manually")
                time.sleep(1.0)
            except Exception as e:
                log_error(f"Auto skill purchase failed: {e}")
            
            return True
        
        # Manual mode (original prompt)
        try:
            # Create a hidden root window
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Show the message box
            result = messagebox.showinfo(
                title="Skill Points Cap Reached",
                message=f"Skill points ({current_skill_points}) exceed the cap ({skill_point_cap}).\n\nYou can:\n• Use your skill points manually, then click OK\n• Click OK without spending (automation continues)\n\nNote: This check only happens on race days."
            )
            
            # Destroy the root window
            root.destroy()
            
            log_info(f"Player acknowledged skill points cap warning")
            
        except Exception as e:
            log_error(f"Failed to show GUI popup: {e}")
            log_info(f"Skill points cap reached - automation continuing")
        
        return True
    
    return True

def check_current_stats(screenshot=None):
    """
    Check current character stats using OCR on the stat regions.
    
    Args:
        screenshot: Optional PIL Image. If None, takes a new screenshot.
    
    Returns:
        dict: Dictionary of current stats with keys: spd, sta, pwr, guts, wit
    """
    from utils.constants_unity import SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION
    from utils.screenshot import take_screenshot
    
    # Use provided screenshot or take new one if not provided
    if screenshot is None:
        screenshot = take_screenshot()
    
    stats = {}
    stat_regions = {
        'spd': SPD_REGION,
        'sta': STA_REGION,
        'pwr': PWR_REGION,
        'guts': GUTS_REGION,
        'wit': WIT_REGION
    }
    
    for stat_name, region in stat_regions.items():
        try:
            # Crop to stat region from provided screenshot
            stat_img = screenshot.crop(region)
            
            # Direct OCR on the stat value (no preprocessing)
            stat_text = extract_number(stat_img, config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789')
            
            # Try to extract the number
            if stat_text:
                # Remove any non-digit characters and take the first number
                import re
                numbers = re.findall(r'\d+', stat_text)
                if numbers:
                    stats[stat_name] = int(numbers[0])
                    log_debug(f"{stat_name.upper()} stat: {stats[stat_name]}")
                else:
                    stats[stat_name] = 0
                    log_debug(f"Failed to extract {stat_name.upper()} stat from text: '{stat_text}'")
            else:
                stats[stat_name] = 0
                log_debug(f"No text found for {stat_name.upper()} stat")
                
        except Exception as e:
            log_debug(f"Error reading {stat_name.upper()} stat: {e}")
            stats[stat_name] = 0
    
    log_debug(f"Current stats: {stats}")
    return stats



def check_energy_bar(screenshot=None, debug_visualization=False):
    """Compute energy percentage using pill-stroke detection and midline analysis.

    - Crop to the energy region
    - Detect the dark stroke (~80,80,80) to get the pill interior
    - Use midline and 5px-inward boundaries
    - Count right-side gray (~117,117,117); colorful left is energy
    """
    try:
        import cv2
        import numpy as np
        from utils.screenshot import take_screenshot

        if screenshot is None:
            screenshot = take_screenshot()

        # Crop region (x, y, w, h)
        x, y, width, height = 330, 203, 602, 72
        cropped = screenshot.crop((x, y, x + width, y + height))

        img = np.array(cropped, dtype=np.uint8)
        if img.shape[2] == 4:
            img = img[:, :, :3]

        # Stroke mask around (80,80,80)
        lower_stroke = np.array([60, 60, 60], dtype=np.uint8)
        upper_stroke = np.array([110, 110, 110], dtype=np.uint8)
        stroke = cv2.inRange(img, lower_stroke, upper_stroke)
        kernel = np.ones((3, 3), np.uint8)
        stroke = cv2.morphologyEx(stroke, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(stroke, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            log_debug(f"No stroke contour found for energy pill")
            return 0.0
        largest = max(contours, key=cv2.contourArea)

        h, w = img.shape[:2]
        filled = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(filled, [largest], 255)
        interior = cv2.erode(filled, kernel, iterations=3)

        ys, xs = np.where(interior > 0)
        if ys.size == 0:
            log_debug(f"No interior found inside pill stroke")
            return 0.0
        mid_y = int((ys.min() + ys.max()) / 2)

        line = interior[mid_y, :]
        cols = np.where(line > 0)[0]
        if cols.size == 0:
            log_debug(f"No interior on midline")
            return 0.0
        left_edge = int(cols[0])
        right_edge = int(cols[-1])

        # Move 5px inward
        shift = 5
        left_in = min(max(left_edge + shift, 0), w - 1)
        right_in = max(min(right_edge - shift, w - 1), left_in)
        total_width = right_in - left_in + 1
        if total_width <= 0:
            return 0.0

        # Gray empty (~117,117,117)
        lower_gray = np.array([100, 100, 100], dtype=np.uint8)
        upper_gray = np.array([140, 140, 140], dtype=np.uint8)
        gray = cv2.inRange(img, lower_gray, upper_gray)
        gray_segment = gray[mid_y, left_in:right_in + 1]
        gray_width = int(np.count_nonzero(gray_segment))
        filled_width = max(total_width - gray_width, 0)
        percentage = float(filled_width / total_width * 100.0)

        if debug_visualization:
            try:
                cv2.imwrite("debug_energy_cropped.png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                debug_img = cv2.cvtColor(img.copy(), cv2.COLOR_RGB2BGR)
                cv2.line(debug_img, (0, mid_y), (w - 1, mid_y), (0, 255, 0), 2)
                cv2.line(debug_img, (left_in, 0), (left_in, h - 1), (255, 0, 0), 2)
                cv2.line(debug_img, (right_in, 0), (right_in, h - 1), (255, 0, 0), 2)
                cv2.putText(debug_img, f"Left: {left_in}, Right: {right_in}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imwrite("debug_horizontal_line.png", debug_img)
                vis = debug_img.copy()
                text = f"Energy: {percentage:.1f}%"
                cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
                cv2.imwrite("debug_energy_visualization.png", vis)
            except Exception as viz_e:
                log_debug(f"Energy debug visualization failed: {viz_e}")

        return percentage

    except Exception as e:
        log_debug(f"Energy bar check failed: {e}")
        return 0.0


def _create_energy_debug_visualization(original_image, contour, interior_mask, gray_mask, percentage, middle_y, leftmost, rightmost, gray_positions):
    """
    Create debug visualization files for energy bar detection analysis.
    
    Args:
        original_image: The cropped energy bar image
        contour: The detected energy bar contour
        interior_mask: Mask of the interior area
        gray_mask: Mask of gray (empty) pixels
        percentage: Calculated fill percentage
        middle_y: Y coordinate of analysis line
        leftmost: Left boundary of energy bar
        rightmost: Right boundary of energy bar
        gray_positions: Positions of gray pixels on analysis line
    """
    try:
        import cv2
        import numpy as np
        
        # Create cropped region debug
        cv2.imwrite("debug_energy_cropped.png", cv2.cvtColor(original_image, cv2.COLOR_RGB2BGR))
        log_debug(f"Saved cropped region to: debug_energy_cropped.png")
        
        # Create horizontal line analysis debug
        debug_img = cv2.cvtColor(original_image.copy(), cv2.COLOR_RGB2BGR)
        
        # Draw the horizontal analysis line in green
        cv2.line(debug_img, (0, middle_y), (original_image.shape[1]-1, middle_y), (0, 255, 0), 2)
        
        # Draw the left and right boundaries in blue, shifted inward by 5px
        shift = 5
        draw_left = min(max(leftmost + shift, 0), original_image.shape[1]-1)
        draw_right = max(min(rightmost - shift, original_image.shape[1]-1), draw_left)
        cv2.line(debug_img, (draw_left, 0), (draw_left, original_image.shape[0]-1), (255, 0, 0), 2)
        cv2.line(debug_img, (draw_right, 0), (draw_right, original_image.shape[0]-1), (255, 0, 0), 2)
        
        # Mark gray positions with red dots
        for gray_x in gray_positions:
            cv2.circle(debug_img, (int(gray_x), middle_y), 2, (0, 0, 255), -1)
        
        # Add text annotations
        cv2.putText(debug_img, f"Analysis Line: y={middle_y}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(debug_img, f"Left: {draw_left}, Right: {draw_right}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(debug_img, f"Gray pixels: {len(gray_positions)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imwrite("debug_horizontal_line.png", debug_img)
        log_debug(f"Saved horizontal line analysis to: debug_horizontal_line.png")
        
        # Create final visualization
        vis_image = cv2.cvtColor(original_image.copy(), cv2.COLOR_RGB2BGR)
        
        # Draw the contour in green
        cv2.drawContours(vis_image, [contour], -1, (0, 255, 0), 2)
        
        # Show interior area in blue tint
        blue_overlay = np.zeros_like(vis_image)
        blue_overlay[:, :, 0] = interior_mask  # Blue channel
        vis_image = cv2.addWeighted(vis_image, 0.8, blue_overlay, 0.2, 0)
        
        # Show gray areas in red tint
        red_overlay = np.zeros_like(vis_image)
        red_overlay[:, :, 2] = gray_mask  # Red channel
        vis_image = cv2.addWeighted(vis_image, 0.8, red_overlay, 0.2, 0)
        
        # Add percentage text
        text = f"Energy: {percentage:.1f}%"
        cv2.putText(vis_image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(vis_image, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)
        
        # Save visualization
        cv2.imwrite("debug_energy_visualization.png", vis_image)
        log_debug(f"Saved visualization to: debug_energy_visualization.png")
        
    except Exception as e:
        log_debug(f"Failed to create debug visualization: {e}")


def _resolve_skill_file_path(path):
    """Resolve skill config path, preferring files under skills/."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not path:
        return os.path.join(project_root, "template", "skills", "skills.json")
    if os.path.isabs(path):
        return path
    normalized = path.replace("\\", "/")
    candidates = [normalized]
    base = os.path.basename(normalized)
    if not normalized.startswith("template/skills/"):
        candidates.append(os.path.join("template", "skills", base))
    for candidate in candidates:
        candidate_abs = os.path.join(project_root, candidate)
        if os.path.exists(candidate_abs):
            return candidate_abs
    return os.path.join(project_root, candidates[-1])