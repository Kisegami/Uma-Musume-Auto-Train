import time
import json
from PIL import ImageStat, Image, ImageEnhance
import numpy as np
import re
import os

from utils.vision.recognizer import locate_on_screen, locate_all_on_screen, is_image_on_screen, match_template, max_match_confidence
from utils.inputs.input import tap, triple_click, swipe, tap_on_image
from utils.capture.screenshot import take_screenshot, enhanced_screenshot
from utils.constants.ura import *
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.vision.template_matching import wait_for_image, deduplicated_matches
from utils.core.config_loader import load_main_config
from utils.training_score_config import load_training_score_rules

# Load config for DEBUG_MODE
config = load_main_config()
DEBUG_MODE = config.get("debug_mode", False)



# Import ADB state functions



# Support icon templates for detailed detection
SUPPORT_ICON_PATHS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png",
}

# Bond color classification helpers
BOND_SAMPLE_OFFSET = (-2, 116)
BOND_LEVEL_COLORS = {
    5: (255, 235, 120),
    4: (255, 173, 30),
    3: (162, 230, 30),
    2: (42, 192, 255),
    1: (109, 108, 117),
}

def _classify_bond_level(rgb_tuple):
    """Classify bond level based on RGB color values"""
    r, g, b = rgb_tuple
    best_level, best_dist = 1, float('inf')
    for level, (cr, cg, cb) in BOND_LEVEL_COLORS.items():
        dr, dg, db = r - cr, g - cg, b - cb
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_dist, best_level = dist, level
    return best_level

def _filtered_template_matches(screenshot, template_path, region_cv, confidence=0.8):
    """Get filtered template matches with deduplication"""
    raw = match_template(screenshot, template_path, confidence, region_cv)
    if not raw:
        return []
    return deduplicated_matches(raw, threshold=30)



def go_to_training():
    """Go to training screen"""
    log_debug(f"Going to training screen...")
    success = tap_on_image("assets/buttons/training_btn.png", min_search=10)
    if success:
        time.sleep(0.5)
    return success

def check_training(go_back=True, year=None, current_stats=None):
    """Check training results using fixed coordinates, collecting support counts,
    bond levels and hint presence in one hover pass before computing failure rates.
    
    Args:
        go_back (bool): If True, tap back to lobby after checking. If False, stay on training screen.
        current_stats (dict, optional): Current character stats to check against caps. If provided,
            training types where the stat is already at/above cap will be skipped to save time.
    """
    log_debug(f"Checking training options...")
    
    from core.Grandlive.logic import are_all_stats_capped, get_effective_stat_cap
    bypass_stat_caps = are_all_stats_capped(current_stats)
    if bypass_stat_caps:
        log_info("All tracked stats are at or above cap; evaluating all training options normally")
    
    # Fixed coordinates for each training type
    training_coords = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }
    results = {}
    skipped_stats = []

    for key, coords in training_coords.items():
        # Early stat cap check - skip analysis if stat is already at/above cap
        if current_stats and not bypass_stat_caps:
            current_stat_value = int(current_stats.get(key, 0))
            stat_cap, cap_label = get_effective_stat_cap(key, current_stats, year=year)
            if current_stat_value >= stat_cap:
                log_info(f"[{key.upper()}] SKIPPED - stat {current_stat_value} >= {cap_label} cap {stat_cap}")
                skipped_stats.append(key)
                # Add placeholder result with score 0 so it won't be selected
                results[key] = {
                    "support": {},
                    "support_detail": {},
                    "hint": False,
                    "total_support": 0,
                    "failure": 100,  # Set high to prevent selection
                    "confidence": 1.0,
                    "score": 0,
                    "skipped": True
                }
                continue
        log_debug(f"Checking {key.upper()} training at coordinates {coords}...")
        
        # Proper hover simulation: move to position, hold, check, move away, release
        log_debug(f"Hovering over {key.upper()} training to check support cards...")
        
        # Step 1: Hold at button position and move mouse up to simulate hover
        log_debug(f"Holding at {key.upper()} training button and moving mouse up...")
        start_x, start_y = coords
        end_x, end_y = start_x, start_y - 200
        swipe(start_x, start_y, end_x, end_y, duration_ms=20)
        time.sleep(0.3)  # Let hover info appear
        
        # Step 2: One pass: capture screenshot, evaluate support counts, bond levels, and hint
        screenshot = take_screenshot()
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)

        # Support counts - pass screenshot to avoid taking new one
        support_counts = check_support_card(screenshot)  # ✅ Pass screenshot
        total_support = sum(support_counts.values())

        # Bond levels per type
        detailed_support = {}
        rgb_img = screenshot.convert("RGB")
        width, height = rgb_img.size
        dx, dy = BOND_SAMPLE_OFFSET
        for t_key, tpl in SUPPORT_ICON_PATHS.items():
            matches = _filtered_template_matches(screenshot, tpl, region_cv, confidence=0.8)
            if not matches:
                continue
            entries = []
            for (x, y, w, h) in matches:
                cx, cy = int(x + w // 2), int(y + h // 2)
                sx, sy = cx + dx, cy + dy
                sx = max(0, min(width - 1, sx))
                sy = max(0, min(height - 1, sy))
                r, g, b = rgb_img.getpixel((sx, sy))
                level = _classify_bond_level((r, g, b))
                entries.append({
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "center": [cx, cy],
                    "bond_sample_point": [int(sx), int(sy)],
                    "bond_color": [int(r), int(g), int(b)],
                    "bond_level": int(level),
                })
            if entries:
                detailed_support[t_key] = entries

        # Hint - pass screenshot to avoid taking new one
        hint_found = check_hint(screenshot)  # ✅ Pass screenshot

        # Calculate score for this training type
        score = calculate_training_score(detailed_support, hint_found, key, year=year)

        log_debug(f"Support counts: {support_counts} | hint_found={hint_found} | score={score}")

        log_debug(f"Checking failure rate for {key.upper()} training...")
        # Pass screenshot to avoid taking new ones
        failure_chance, confidence = check_failure(screenshot, key)  # ✅ Pass screenshot
        
        results[key] = {
            "support": support_counts,
            "support_detail": detailed_support,
            "hint": bool(hint_found),
            "total_support": total_support,
            "failure": failure_chance,
            "confidence": confidence,
            "score": score
        }
        
        # Use clean format matching training_score_test.py exactly
        log_info(f"\n[{key.upper()}]")
        
        # Show support card details (similar to test script)
        if detailed_support:
            support_lines = []
            for card_type, entries in detailed_support.items():
                for idx, entry in enumerate(entries, start=1):
                    level = entry['bond_level']
                    is_rainbow = (card_type == key and level >= 4)
                    label = f"{card_type.upper()}{idx}: {level}"
                    if is_rainbow:
                        label += " (Rainbow)"
                    support_lines.append(label)
            log_info(f", ".join(support_lines))
        else:
            log_info(f"-")
        
        log_info(f"hint={hint_found}")
        log_info(f"Fail: {failure_chance}% - Confident: {confidence:.2f}")
        log_info(f"Score: {score}")
        

    
    if go_back:
        log_debug(f"Going back from training screen...")
        tap_on_image("assets/buttons/back_btn.png")
    
    # Print overall summary
    log_info(f"\n=== Overall ===")
    for k in ["spd", "sta", "pwr", "guts", "wit"]:
        if k in results:
            data = results[k]
            log_info(f"{k.upper()}: Score={data['score']:.2f}, Fail={data['failure']}% - Confident: {data['confidence']:.2f}")
    
    return results

def do_train(train, already_on_training_screen=False):
    """Perform training of specified type
    
    Args:
        train (str): Training type to perform (spd, sta, pwr, guts, wit)
        already_on_training_screen (bool): If True, skip navigation to training screen (already there)
    """
    log_debug(f"Performing {train.upper()} training...")
    
    # # First, go to training screen unless already there
    # if not already_on_training_screen:
    #     if not go_to_training():
    #         log_debug(f"Failed to go to training screen, cannot perform {train.upper()} training")
    #         return
    #     time.sleep(0.3)  # Wait for screen to load
    
    # Fixed coordinates for each training type
    training_coords = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }
    
    # Check if the requested training type exists
    if train not in training_coords:
        log_debug(f"Unknown training type: {train}")
        return
    
    # Get the coordinates for the requested training type
    train_coords = training_coords[train]
    log_debug(f"Found {train.upper()} training at coordinates {train_coords}")
    triple_click(train_coords[0], train_coords[1], interval=0.1)
    log_debug(f"Triple clicked {train.upper()} training button")
    time.sleep(1.0)

# Training-related functions moved from state.py
def check_support_card(screenshot, threshold=0.9):
    SUPPORT_ICONS = {
        "spd": "assets/icons/support_card_type_spd.png",
        "sta": "assets/icons/support_card_type_sta.png",
        "pwr": "assets/icons/support_card_type_pwr.png",
        "guts": "assets/icons/support_card_type_guts.png",
        "wit": "assets/icons/support_card_type_wit.png",
        "friend": "assets/icons/support_card_type_friend.png"
    }

    count_result = {}

    # Use provided screenshot instead of taking new one
    # screenshot = take_screenshot()  # ❌ REMOVED
    
    # Save full screenshot for debugging only in debug mode
    if DEBUG_MODE:
        screenshot.save("debug_support_cards_screenshot.png")
        log_debug(f"Saved full screenshot to debug_support_cards_screenshot.png")

    # Convert PIL region format (left, top, right, bottom) to OpenCV format (x, y, width, height)
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    log_debug(f"Searching in region: {region_cv} (PIL format: {SUPPORT_CARD_ICON_REGION})")
    
    # Crop and save the search region for debugging only in debug mode
    if DEBUG_MODE:
        search_region = screenshot.crop(SUPPORT_CARD_ICON_REGION)
        search_region.save("debug_support_cards_search_region.png")
        log_debug(f"Saved search region to debug_support_cards_search_region.png")

    for key, icon_path in SUPPORT_ICONS.items():
        log_debug(f"\nTesting {key.upper()} support card detection...")
        
        # Use single threshold for faster detection
        matches = match_template(screenshot, icon_path, 0.8, region_cv)
        log_debug(f"Raw matches for {key.upper()}: {matches}")
        
        filtered_matches = deduplicated_matches(matches, threshold=30) if matches else []
        log_debug(f"After deduplication for {key.upper()}: {filtered_matches}")
        
        # Ensure filtered_matches is always a list
        if filtered_matches is None:
            log_debug(f"WARNING: filtered_matches is None for {key.upper()}, setting to empty list")
            filtered_matches = []
        
        # Additional safety check
        if not isinstance(filtered_matches, list):
            log_debug(f"WARNING: filtered_matches is not a list for {key.upper()}, type: {type(filtered_matches)}, setting to empty list")
            filtered_matches = []
        
        log_debug(f" Found {len(filtered_matches)} {key.upper()} support cards (filtered from {len(matches) if matches else 0})")
        
        # Show coordinates of each match
        for i, match in enumerate(filtered_matches):
            x, y, w, h = match
            center_x, center_y = x + w//2, y + h//2
            log_debug(f"   {key.upper()} match {i+1}: center=({center_x}, {center_y}), bbox=({x}, {y}, {w}, {h})")
        
        # Skip expensive image annotation and only save debug images when DEBUG_MODE is true
        if not filtered_matches:
            log_debug(f" No {key.upper()} support cards found")
        
        count_result[key] = len(filtered_matches)
        
        # Debug output for each support card type
        if count_result[key] > 0:
            log_debug(f" {key.upper()} support cards found: {count_result[key]}")

    return count_result

def check_hint(screenshot, template_path: str = "assets/icons/hint.png", confidence: float = 0.8) -> bool:
    """Detect presence of a hint icon within the support card search region.

    Args:
        template_path: Path to the hint icon template image.
        confidence: Minimum confidence threshold for template matching.

    Returns:
        True if at least one hint icon is found in `SUPPORT_CARD_ICON_REGION`, otherwise False.
    """
    try:
        # Use provided screenshot instead of taking new one
        # screenshot = take_screenshot()  # ❌ REMOVED

        # Convert PIL (left, top, right, bottom) to OpenCV (x, y, width, height)
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        log_debug(f" Checking hint in region: {region_cv} using template: {template_path}")

        if DEBUG_MODE:
            try:
                screenshot.crop(SUPPORT_CARD_ICON_REGION).save("debug_hint_search_region.png")
                log_debug(f" Saved hint search region to debug_hint_search_region.png")
            except Exception:
                pass

        matches = match_template(screenshot, template_path, confidence, region_cv)

        found = bool(matches and len(matches) > 0)
        log_debug(f" Hint icon found: {found}")
        return found
    except Exception as e:
        log_debug(f" check_hint failed: {e}")
        return False

def check_failure(screenshot, train_type):
    """
    Check failure rate for a specific training type using provided screenshot instead of taking new ones.
    Args:
        screenshot: PIL Image object to analyze
        train_type (str): One of 'spd', 'sta', 'pwr', 'guts', 'wit'
    Returns:
        (rate, confidence)
    """
    log_debug(f" ===== STARTING FAILURE DETECTION for {train_type.upper()} =====")
    from utils.constants.ura import FAILURE_REGION_SPD, FAILURE_REGION_STA, FAILURE_REGION_PWR, FAILURE_REGION_GUTS, FAILURE_REGION_WIT
    from utils.capture.screenshot import enhanced_screenshot, take_screenshot
    import numpy as np
    import re
    from PIL import ImageEnhance

    region_map = {
        'spd': FAILURE_REGION_SPD,
        'sta': FAILURE_REGION_STA,
        'pwr': FAILURE_REGION_PWR,
        'guts': FAILURE_REGION_GUTS,
        'wit': FAILURE_REGION_WIT
    }
    region = region_map[train_type]
    percentage_patterns = [
        r"(\d{1,3})\s*%",  # "29%", "29 %" - most reliable
        r"%\s*(\d{1,3})",  # "% 29" - reversed format
        r"(\d{1,3})",      # Just the number - fallback
    ]
    
    # Step 1: Try white-specialized OCR 3 times
    for attempt in range(3):
        log_debug(f" White OCR attempt {attempt+1}/3 for {train_type.upper()}")
        
        # Take new screenshot for each retry instead of shifting region
        if attempt > 0:
            log_debug(f" Taking new screenshot for retry {attempt+1}")
            current_screenshot = take_screenshot()
        else:
            current_screenshot = screenshot
        
        # Crop from current screenshot
        img = current_screenshot.crop(region)
        
        # White text specialization: create white mask and enhance contrast
        raw_img = img.convert("RGB")
        raw_np = np.array(raw_img)
        
        # Create white text mask (high values in all RGB channels)
        white_mask = (
            (raw_np[:, :, 0] > 200) &  # High red
            (raw_np[:, :, 1] > 200) &  # High green  
            (raw_np[:, :, 2] > 200)    # High blue
        )
        
        # Create white text result (white text on black background)
        white_result = np.zeros_like(raw_np)
        white_result[white_mask] = [255, 255, 255]
        white_img = Image.fromarray(white_result).convert("L")
        
        # Enhance contrast for better OCR
        white_img = ImageEnhance.Contrast(white_img).enhance(2.0)
        
        if DEBUG_MODE:
            img.save(f"debug_failure_{train_type}_white_attempt_{attempt+1}.png")
            white_img.save(f"debug_failure_{train_type}_white_enhanced_{attempt+1}.png")
        
        # Get OCR data with confidence from enhanced white image
        from core.Grandlive.ocr import extract_text_with_data, extract_text
        ocr_data = extract_text_with_data(white_img, config='--oem 3 --psm 6')
        text = extract_text(white_img, config='--oem 3 --psm 6')
        log_debug(f" White OCR result: '{text}'")
        
        # Calculate average confidence from OCR data
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        
        for pattern in percentage_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if 0 <= rate <= 100:
                    log_debug(f" Found percentage: {rate}% (white) confidence: {avg_confidence:.2f} for {train_type.upper()}")
                    if avg_confidence >= 0.8:
                        log_debug(f" Confidence {avg_confidence:.2f} meets minimum 0.8, accepting result")
                        return (rate, avg_confidence)
                    else:
                        log_debug(f" Confidence {avg_confidence:.2f} below minimum 0.8, continuing to retry")
        if attempt < 2:
            log_debug(f" No valid percentage found, retrying...")
            time.sleep(0.1)
    
    # Step 2: Try yellow threshold OCR 3 times
    for attempt in range(3):
        log_debug(f" Yellow OCR attempt {attempt+1}/3 for {train_type.upper()}")
        
        # Take new screenshot for each retry instead of shifting region
        if attempt > 0:
            log_debug(f" Taking new screenshot for retry {attempt+1}")
            current_screenshot = take_screenshot()
        else:
            current_screenshot = screenshot
        
        # Crop from current screenshot
        raw_img = current_screenshot.crop(region)
        raw_img = raw_img.resize((raw_img.width * 2, raw_img.height * 2), Image.BICUBIC)
        raw_img = raw_img.convert("RGB")
        raw_np = np.array(raw_img)
        yellow_mask = (
            (raw_np[:, :, 0] > 180) &  # High red
            (raw_np[:, :, 1] > 120) &  # High green
            (raw_np[:, :, 2] < 80)     # Low blue
        )
        yellow_result = np.zeros_like(raw_np)
        yellow_result[yellow_mask] = [255, 255, 255]
        yellow_img = Image.fromarray(yellow_result).convert("L")
        yellow_img = ImageEnhance.Contrast(yellow_img).enhance(1.5)
        if DEBUG_MODE:
            yellow_img.save(f"debug_failure_{train_type}_yellow_attempt_{attempt+1}.png")
        
        # Get OCR data with confidence
        ocr_data = extract_text_with_data(yellow_img, config='--oem 3 --psm 6')
        text = extract_text(yellow_img, config='--oem 3 --psm 6')
        log_debug(f" Yellow OCR result: '{text}'")
        
        # Calculate average confidence from OCR data
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        
        for pattern in percentage_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if 0 <= rate <= 100:
                    log_debug(f" Found percentage: {rate}% (yellow) confidence: {avg_confidence:.2f} for {train_type.upper()}")
                    if avg_confidence >= 0.9:
                        log_debug(f" Confidence {avg_confidence:.2f} meets minimum 0.9, accepting result")
                        return (rate, avg_confidence)
                    else:
                        log_debug(f" Confidence {avg_confidence:.2f} below minimum 0.9, continuing to retry")
        if attempt < 2:
            log_debug(f" No valid yellow percentage found, retrying...")
            time.sleep(0.1)
    
    # If we get here, all OCR attempts failed
    log_debug(f" ===== FAILURE DETECTION FAILED for {train_type.upper()} =====")
    log_debug(f" All OCR attempts failed to extract failure rate")
    
    if DEBUG_MODE:
        # Save the original cropped region for debugging
        original_crop = screenshot.crop(region)
        debug_filename = f"debug_failure_{train_type}_failed_region.png"
        original_crop.save(debug_filename)
        log_debug(f" Saved failed region to: {debug_filename}")
        log_debug(f" Region coordinates: {region}")
        log_debug(f" Region size: {original_crop.size}")
        
        # Stop execution in debug mode
        log_debug(f" Stopping execution due to failure rate extraction failure for {train_type.upper()}")
        log_debug(f" Please check the debug image: {debug_filename}")
        raise RuntimeError(f"Failure rate extraction failed for {train_type.upper()} training. Debug image saved to {debug_filename}")
    
    log_debug(f" No valid failure rate found for {train_type.upper()}, returning 100% (safe fallback)")
    return (100, 0.0)  # 100% failure rate when detection completely fails (prevents choosing unknown training)

def choose_best_training(training_results, config, current_stats, year=None):
    """
    Choose the best training option based on scoring algorithm.
    
    Args:
        training_results (dict): Results from check_training()
        config (dict): Training configuration with thresholds
        current_stats (dict): Current character stats to check against caps
        
    Returns:
        str: Best training type (spd, sta, pwr, guts, wit) or None
    """
    if not training_results:
        return None

    from utils.training_score_adjustments import apply_over_1200_score_reduction
    training_results = apply_over_1200_score_reduction(
        training_results, config, current_stats
    )
    
    max_failure = config.get("maximum_failure", 15)
    min_score_config = config.get("min_score", {})
    priority_stat = config.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])
    
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
    min_scores = {
        "spd": min_score_config.get("spd", default_min_score),
        "sta": min_score_config.get("sta", default_min_score),
        "pwr": min_score_config.get("pwr", default_min_score),
        "guts": min_score_config.get("guts", default_min_score),
        "wit": min_score_config.get("wit", default_min_score)
    }

    from utils.training_score_adjustments import format_training_score_evaluation
    for line in format_training_score_evaluation(training_results, current_stats, min_scores):
        log_info(line)
    
    # Gambling train config - increases max failure for high score training
    gambling_enabled = config.get("gambling_train_enabled", False)
    gambling_failure_increase = config.get("gambling_train_failure_increase", 5)
    gambling_score_per_increase = config.get("gambling_train_score_per_increase", 1.0)
    
    # Filter out training options with failure rates above maximum (with gambling train adjustments)
    log_debug(
        f" Failure filter start: base max failure = {max_failure}% | "
        f"gambling_enabled={gambling_enabled} "
        f"(+{gambling_failure_increase}% per {gambling_score_per_increase:.1f} score)"
    )
    safe_options = {}
    for k, v in training_results.items():
        failure_rate = v.get('failure', 100)
        score = v.get('score', 0)
        
        # Calculate effective max failure for this training option
        effective_max_failure = max_failure
        score_multiplier = 0
        if gambling_enabled and gambling_score_per_increase > 0:
            # Increase max failure based on score (e.g., +5% for each 1.0 score)
            score_multiplier = int(score / gambling_score_per_increase)
            effective_max_failure = max_failure + (gambling_failure_increase * score_multiplier)
        
        decision = "SAFE" if failure_rate <= effective_max_failure else "UNSAFE"
        if gambling_enabled and gambling_score_per_increase > 0:
            log_debug(
                f"  {k.upper()}: failure={failure_rate}% | score={score:.1f} | "
                f"base max={max_failure}% -> effective max={effective_max_failure}% "
                f"(multiplier={score_multiplier}) => {decision}"
            )
        else:
            log_debug(
                f"  {k.upper()}: failure={failure_rate}% | score={score:.1f} | "
                f"max failure={effective_max_failure}% => {decision}"
            )
        
        if failure_rate <= effective_max_failure:
            safe_options[k] = v
    
    if not safe_options:
        log_debug(f" No training options passed failure filter")
        return None
    
    log_debug(f" Training options after failure filter: {list(safe_options.keys())}")
    
    # Filter by stat caps BEFORE other filtering
    from core.Grandlive.logic import filter_by_stat_caps, are_all_stats_capped
    
    # Safety check for current_stats
    if not current_stats:
        log_debug(f" No current stats available, skipping stat cap filtering")
        capped_options = safe_options
    elif are_all_stats_capped(current_stats):
        log_debug(f" All tracked stats are capped, bypassing stat cap filtering")
        capped_options = safe_options
    else:
        log_debug(f" Applying stat cap filtering with current stats: {current_stats}")
        capped_options = filter_by_stat_caps(safe_options, current_stats, year=year)
    
    if not capped_options:
        log_debug(f" All training options filtered out by stat caps")
        return None
    
    # Filter by minimum score requirements (per-stat)
    valid_options = {}
    for k, v in capped_options.items():
        score = v.get('score', 0)
        min_score_for_stat = min_scores.get(k, default_min_score)
        if score < min_score_for_stat:
            continue
        valid_options[k] = v
    
    if not valid_options:
        log_debug(f" No training options meet minimum score requirements")
        return None
    
    # Sort by score first (desc), use priority as tiebreaker only
    def sort_key(item):
        k, v = item
        priority_index = priority_stat.index(k) if k in priority_stat else len(priority_stat)
        return (-v.get('score', 0), priority_index)
    
    sorted_options = sorted(valid_options.items(), key=sort_key)
    best_training = sorted_options[0][0]
    
    log_debug(f" Best training selected: {best_training} (score: {sorted_options[0][1].get('score', 0):.2f})")
    return best_training

def calculate_training_score(support_detail, hint_found, training_type, year=None):
    """
    Calculate training score based on support cards, bond levels, and hints.
    
    Args:
        support_detail: Dictionary of support card details with bond levels
        hint_found: Boolean indicating if hint is present
        training_type: The type of training being evaluated
    
    Returns:
        float: Calculated score for the training
    """
    # Load scoring rules from training_score.json
    scoring_rules = {}
    try:
        # Get project root: core/Grandlive/training_handling.py -> core/Grandlive -> core -> root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        scoring_rules = load_training_score_rules(project_root, "grand_live", year)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        log_warning(f"Could not load training_score.json: {e}")
        # Fallback to default values if config file is not available
        scoring_rules = {
            "rainbow_support": {"points": 1.0},
            "not_rainbow_support_low": {"points": 0.7},
            "not_rainbow_support_high": {"points": 0.0},
            "hint": {"points": 0.3},
            "friend_support": {"points": 0.5},
            "friend_support_high": {"points": 0.5},
        }
    
    score = 0.0
    
    # Score support cards based on bond levels
    for card_type, entries in support_detail.items():
        for entry in entries:
            level = entry['bond_level']
            
            # Friend support cards have separate scoring logic
            if card_type == "friend":
                if level < 3:
                    score += scoring_rules.get("friend_support", {}).get("points", 0.5)
                else:
                    score += scoring_rules.get("friend_support_high", {}).get("points", 0.5)
                continue
            
            # Normal support card scoring
            is_rainbow = (card_type == training_type and level >= 4)
            
            if is_rainbow:
                score += scoring_rules.get("rainbow_support", {}).get("points", 1.0)
            else:
                if level < 4:
                    score += scoring_rules.get("not_rainbow_support_low", {}).get("points", 0.7)
                else:  # bond >= 4 for non-rainbow
                    score += scoring_rules.get("not_rainbow_support_high", {}).get("points", 0.0)
    
    # Add hint bonus
    if hint_found:
        score += scoring_rules.get("hint", {}).get("points", 0.3)
    
    return round(score, 2)


def check_training_api(year=None, current_stats=None):
    """
    Fetch training data from the API and convert it to the same result format
    as check_training() so it can be used as a drop-in replacement.

    Returns:
        dict | None: Training results keyed by stat name, or None if API is unavailable.
    """
    try:
        from utils.integrations.umat_api import get_training, is_api_enabled
        if not is_api_enabled():
            return None
        api_data = get_training()
    except ImportError:
        return None

    if api_data is None:
        return None

    trainings_list = api_data.get("trainings", [])
    if not trainings_list:
        log_debug("[API] Training data empty")
        return None

    from core.Grandlive.logic import are_all_stats_capped, get_effective_stat_cap
    bypass_stat_caps = are_all_stats_capped(current_stats)
    if bypass_stat_caps:
        log_info("[API] All tracked stats are at or above cap; evaluating all training options normally")

    results = {}
    log_info("--- Training (API) ---")

    for t in trainings_list:
        key = t.get("name", "")
        if key not in ("spd", "sta", "pwr", "guts", "wit"):
            log_debug(f"[API] Skipping unknown training name: {key}")
            continue

        if current_stats and not bypass_stat_caps:
            current_val = int(current_stats.get(key, 0))
            cap_val, cap_label = get_effective_stat_cap(key, current_stats, year=year)
            if current_val >= cap_val:
                log_info(f"[{key.upper()}] SKIPPED - stat {current_val} >= {cap_label} cap {cap_val}")
                results[key] = {
                    "support": {},
                    "support_detail": {},
                    "hint": False,
                    "total_support": 0,
                    "failure": 100,
                    "confidence": 1.0,
                    "score": 0,
                    "skipped": True,
                }
                continue

        failure = t.get("failure", 0)
        hint_found = t.get("hint_found", False)

        support_counts = {}
        detailed_support = {}
        for card in t.get("support_cards", []):
            card_type = card.get("type", "")
            bond_level = card.get("bond_level", 0)
            support_counts[card_type] = support_counts.get(card_type, 0) + 1
            entry = {
                "bbox": [0, 0, 0, 0],
                "center": [0, 0],
                "bond_sample_point": [0, 0],
                "bond_color": [0, 0, 0],
                "bond_level": bond_level,
            }
            detailed_support.setdefault(card_type, []).append(entry)

        total_support = sum(support_counts.values())
        score = calculate_training_score(detailed_support, hint_found, key, year=year)

        results[key] = {
            "support": support_counts,
            "support_detail": detailed_support,
            "hint": bool(hint_found),
            "total_support": total_support,
            "failure": failure,
            "confidence": 1.0,
            "score": score,
        }

        if detailed_support:
            parts = []
            for ctype, entries in detailed_support.items():
                for idx, entry in enumerate(entries, 1):
                    lv = entry["bond_level"]
                    is_rainbow = (ctype == key and lv >= 4)
                    label = f"{ctype.upper()}{idx}:{lv}"
                    if is_rainbow:
                        label += "(R)"
                    parts.append(label)
            support_str = ",".join(parts)
        else:
            support_str = "-"

        extras = " hint" if hint_found else ""
        log_info(f"  {key.upper():>4}: Score={score:.1f} Fail={failure}%(API) | {support_str}{extras}")

    if not results:
        log_debug("[API] No training results parsed")
        return None

    return results
