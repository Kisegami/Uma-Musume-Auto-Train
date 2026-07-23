import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import time
import re
import json
from utils.capture.screenshot import take_screenshot
from utils.inputs.input import perform_swipe
from utils.inputs.skill_swipe import swipe_skill_list_down_slow
from utils.vision.recognizer import match_template

from utils.core.log import log_debug, log_info, log_warning, log_error

# OCR is now handled by utils.ocr.ocr_utils
# Check if OCR functions are available
try:
    from core.Grandlive.ocr import extract_text
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    log_debug(f"Warning: OCR not available. OCR features will be disabled.")



def remove_overlapping_rectangles(rectangles, overlap_threshold=0.5):
    """
    Remove overlapping rectangles based on overlap threshold.
    
    Args:
        rectangles: List of (x, y, width, height) tuples
        overlap_threshold: Minimum overlap ratio to consider rectangles as duplicates
    
    Returns:
        List of non-overlapping rectangles
    """
    if not rectangles:
        return []
    
    # Convert to (x1, y1, x2, y2) format for easier calculation
    boxes = []
    for x, y, w, h in rectangles:
        boxes.append([x, y, x + w, y + h])
    
    # Sort by area (largest first)
    boxes = sorted(boxes, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
    
    keep = []
    
    for box in boxes:
        should_keep = True
        
        for kept_box in keep:
            # Calculate intersection
            x1 = max(box[0], kept_box[0])
            y1 = max(box[1], kept_box[1])
            x2 = min(box[2], kept_box[2])
            y2 = min(box[3], kept_box[3])
            
            if x1 < x2 and y1 < y2:
                # Calculate overlap area
                intersection_area = (x2 - x1) * (y2 - y1)
                box_area = (box[2] - box[0]) * (box[3] - box[1])
                
                # Calculate overlap ratio
                overlap_ratio = intersection_area / box_area
                
                if overlap_ratio >= overlap_threshold:
                    should_keep = False
                    break
        
        if should_keep:
            keep.append(box)
    
    # Convert back to (x, y, width, height) format
    result = []
    for x1, y1, x2, y2 in keep:
        result.append((x1, y1, x2 - x1, y2 - y1))
    
    return result

def extract_skill_info(screenshot, button_x, button_y, anchor_x=946, anchor_y=809):
    """
    Extract skill name and price from screenshot using button position as anchor.
    
    Args:
        screenshot: PIL Image of the screen
        button_x, button_y: Detected skill_up button position
        anchor_x, anchor_y: Reference anchor position (946, 809)
    
    Returns:
        dict: {'name': str, 'price': str, 'name_region': tuple, 'price_region': tuple}
    """
    try:
        if not OCR_AVAILABLE:
            return {
                'name': 'OCR not available',
                'price': 'OCR not available',
                'name_region': None,
                'price_region': None
            }
        
        # Calculate offset from anchor position
        offset_x = button_x - anchor_x
        offset_y = button_y - anchor_y
        
        # Define regions relative to anchor
        # Skill name region: 200, 716, 731, 767 (width: 531, height: 51)
        name_x1 = 200 + offset_x
        name_y1 = 716 + offset_y
        name_x2 = 731 + offset_x
        name_y2 = 767 + offset_y
        name_region = (name_x1, name_y1, name_x2, name_y2)
        
        # Skill price region: 834, 803, 927, 854 (width: 93, height: 51)
        price_x1 = 834 + offset_x
        price_y1 = 803 + offset_y
        price_x2 = 927 + offset_x
        price_y2 = 854 + offset_y
        price_region = (price_x1, price_y1, price_x2, price_y2)
        
        # Extract skill name with simple OCR
        from core.Grandlive.ocr import extract_text, extract_number
        skill_name = "Name Error"
        try:
            name_crop = screenshot.crop(name_region)
            skill_name_raw = extract_text(name_crop)
            skill_name = clean_skill_name(skill_name_raw)
        except Exception as e:
            log_debug(f"Name OCR error: {e}")
        
        # Extract skill price with simple OCR
        skill_price = "Price Error"
        try:
            price_crop = screenshot.crop(price_region)
            
            # Try multiple OCR approaches
            skill_price_raw = ""
            
            # Approach 1: Simple OCR
            skill_price_raw = extract_text(price_crop)
            
            # Approach 2: If empty, try with digits-only config
            if not skill_price_raw:
                skill_price_raw = extract_number(price_crop, config='--psm 8 -c tessedit_char_whitelist=0123456789')
            
            # Approach 3: If still empty, try different PSM
            if not skill_price_raw:
                skill_price_raw = extract_text(price_crop, config='--psm 7')
            
            log_debug(f"Raw price OCR: '{skill_price_raw}'")
            skill_price = clean_skill_price(skill_price_raw)
            log_debug(f"Cleaned price: '{skill_price}'")
            
            # Save debug image if price OCR still fails
            if not skill_price_raw or skill_price == "0":
                debug_filename = f"debug_price_{skill_name.replace(' ', '_')}.png"
                price_crop.save(debug_filename)
                log_debug(f"Saved debug image: {debug_filename}")
                
        except Exception as e:
            log_debug(f"Price OCR error: {e}")
        
        result = {
            'name': skill_name,
            'price': skill_price,
            'name_region': name_region,
            'price_region': price_region
        }
        return result
        
    except Exception as e:
        log_debug(f"Error extracting skill info: {e}")
        log_debug(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {
            'name': 'Error',
            'price': 'Error',
            'name_region': None,
            'price_region': None
        }



def clean_skill_name(text):
    """
    Clean and format skill name text from OCR.
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned skill name string
    """
    if not text:
        return "Unknown Skill"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s\-\(\)\'\"&]', '', text)
    
    # Fix common OCR errors at the beginning
    # Remove leading numbers that shouldn't be there
    text = re.sub(r'^[0-9]+', '', text).strip()
    
    # Fix specific known OCR misreads
    if text.lower().startswith('1can see right through you'):
        text = 'I Can See Right Through You'
    elif text.lower().startswith('1') and 'can see' in text.lower():
        text = 'I Can See Right Through You'
    elif 'can see right through you' in text.lower() and text.lower() != 'i can see right through you':
        text = 'I Can See Right Through You'
    
    # Fix Umastan -> Uma Stan
    if text.lower() in ['umastan', 'uma stan', 'umestan']:
        text = 'Uma Stan'
    
    # Keep original capitalization (don't force title case)
    # This preserves natural capitalization like "Professor of Curvature"
    
    return text if text else "Unknown Skill"

def clean_skill_price(text):
    """
    Clean and format skill price text from OCR.
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned price string
    """
    if not text:
        return "0"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Extract numbers (price is likely numeric) 
    numbers = re.findall(r'\d+', text)
    if numbers:
        return numbers[0]  # Return first number found
    
    # If no numbers found, return the raw text (might still be useful)
    return text if text else "0"

def is_button_available(screenshot, x, y, width, height, brightness_threshold=150):
    """
    Check if a skill button is available (bright) or unavailable (dark).
    
    Args:
        screenshot: PIL Image of the screen
        x, y, width, height: Button location and size
        brightness_threshold: Minimum average brightness for available buttons
    
    Returns:
        tuple: (is_available: bool, avg_brightness: float)
    """
    try:
        # Extract the button region
        button_region = screenshot.crop((x, y, x + width, y + height))
        
        # Convert to grayscale for brightness analysis
        gray_button = button_region.convert('L')
        
        # Calculate average brightness
        import numpy as np
        brightness_array = np.array(gray_button)
        avg_brightness = np.mean(brightness_array)
        
        # Check if button is bright enough (available)
        is_available = avg_brightness >= brightness_threshold
        
        return is_available, avg_brightness
        
    except Exception as e:
        log_debug(f"Error checking button availability: {e}")
        return True, 0  # Default to available if check fails

# Helper functions for skill recognition (broken down from large function)
def _load_skill_template():
    """Return the skill_up template path. Returns (path, error_dict)."""
    template_path = "assets/buttons/skill_up.png"
    if not os.path.exists(template_path):
        return None, {
            'count': 0, 'locations': [], 'debug_image_path': None,
            'error': f"Template not found: {template_path}"
        }

    return template_path, None

def _perform_template_matching(screenshot, template_path, confidence):
    """Perform template matching through the shared recognizer."""
    return match_template(screenshot, template_path, confidence=confidence)

def _filter_available_buttons(screenshot, unique_matches, filter_dark_buttons, brightness_threshold):
    """Filter out dark/unavailable buttons and return available matches with brightness info."""
    if not filter_dark_buttons:
        log_debug(f"Found {len(unique_matches)} buttons (no brightness filtering)")
        return unique_matches, []
    
    log_debug(f"Filtering dark buttons (brightness threshold: {brightness_threshold})...")
    available_matches = []
    brightness_info = []
    
    for x, y, w, h in unique_matches:
        is_available, avg_brightness = is_button_available(
            screenshot, x, y, w, h, brightness_threshold
        )
        brightness_info.append({
            'location': (x, y, w, h),
            'brightness': avg_brightness,
            'available': is_available
        })
        
        if is_available:
            available_matches.append((x, y, w, h))
    
    log_debug(f"Found {len(unique_matches)} unique matches, {len(available_matches)} available (bright) buttons")
    return available_matches, brightness_info

def _extract_skills_info(screenshot, available_matches, extract_skills):
    """Extract skill information using OCR if requested."""
    if not extract_skills or not available_matches:
        return []
    
    log_debug(f"Extracting skill information using OCR...")
    skills_info = []
    
    for i, (x, y, w, h) in enumerate(available_matches):
        try:
            skill_info = extract_skill_info(screenshot, x, y)
            skill_data = {
                'name': skill_info['name'],
                'price': skill_info['price'],
                'location': (x, y, w, h),
                'regions': {
                    'name_region': skill_info['name_region'],
                    'price_region': skill_info['price_region']
                }
            }
            skills_info.append(skill_data)
            log_debug(f"{i+1}. {skill_info['name']} - {skill_info['price']}")
        except Exception as e:
            log_debug(f"{i+1}. Error extracting skill: {e}")
            # Add fallback skill entry
            skill_data = {
                'name': f'Skill {i+1} (Error)',
                'price': 'Error',
                'location': (x, y, w, h),
                'regions': {'name_region': None, 'price_region': None}
            }
            skills_info.append(skill_data)
    
    return skills_info

def recognize_skill_up_locations(confidence=0.9, debug_output=True, overlap_threshold=0.5, 
                               filter_dark_buttons=True, brightness_threshold=150,
                               extract_skills=True):
    """
    Recognize and count skill_up.png locations on screen using ADB capture.
    
    Args:
        confidence: Minimum confidence threshold for template matching (0.0 to 1.0)
        debug_output: Whether to generate debug image with bounding boxes
        overlap_threshold: Minimum overlap ratio to consider rectangles as duplicates
        filter_dark_buttons: Whether to filter out dark/unavailable skill buttons
        brightness_threshold: Minimum average brightness for available buttons (0-255)
        extract_skills: Whether to extract skill names and prices using OCR
    
    Returns:
        dict: Recognition results with count, locations, skills, and debug info
    """
    try:
        # Take screenshot
        screenshot = take_screenshot()
        
        # Load template
        template, error_result = _load_skill_template()
        if template is None:
            return error_result
        
        # Perform template matching
        matches = _perform_template_matching(screenshot, template, confidence)
        
        # Remove overlapping rectangles
        unique_matches = remove_overlapping_rectangles(matches, overlap_threshold)
        
        # Filter available buttons
        available_matches, brightness_info = _filter_available_buttons(
            screenshot, unique_matches, filter_dark_buttons, brightness_threshold
        )
        
        # Extract skill information
        skills_info = _extract_skills_info(screenshot, available_matches, extract_skills)
        
        # Generate debug image if requested
        debug_image_path = None
        if debug_output and (available_matches or unique_matches):
            debug_image_path = generate_debug_image(
                screenshot, 
                available_matches if filter_dark_buttons else unique_matches, 
                confidence,
                brightness_info if filter_dark_buttons else None,
                filter_dark_buttons
            )
        
        # Build result dictionary
        result = {
            'count': len(available_matches),
            'locations': available_matches,
            'skills': skills_info,
            'debug_image_path': debug_image_path,
            'raw_matches': len(matches) if matches else 0,
            'deduplicated_matches': len(unique_matches),
            'confidence_used': confidence,
            'overlap_threshold_used': overlap_threshold,
            'brightness_threshold_used': brightness_threshold if filter_dark_buttons else None,
            'filter_dark_buttons_used': filter_dark_buttons,
            'extract_skills_used': extract_skills
        }
        
        if filter_dark_buttons:
            result['brightness_info'] = brightness_info
            result['dark_buttons_filtered'] = len(unique_matches) - len(available_matches)
        
        return result
        
    except Exception as e:
        log_debug(f"Error in skill recognition: {e}")
        return {
            'count': 0,
            'locations': [],
            'skills': [],
            'debug_image_path': None,
            'error': str(e)
        }

def generate_debug_image(screenshot, locations, confidence, brightness_info=None, filter_dark_buttons=False):
    """
    Generate debug image with bounding boxes drawn on detected skill_up locations.
    
    Args:
        screenshot: PIL Image of the screen
        locations: List of (x, y, width, height) tuples
        confidence: Confidence threshold used for detection
        brightness_info: List of brightness information for each detection
        filter_dark_buttons: Whether dark button filtering was applied
    
    Returns:
        str: Path to the saved debug image
    """
    try:
        # Create a copy of the screenshot for drawing
        debug_image = screenshot.copy()
        draw = ImageDraw.Draw(debug_image)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Draw bounding boxes and labels
        for i, (x, y, width, height) in enumerate(locations):
            # Determine box color based on availability
            box_color = "green"  # Default for available buttons
            label = f"{i+1}"
            
            # Add brightness info if available
            if brightness_info:
                # Find brightness info for this location
                brightness_data = None
                for info in brightness_info:
                    if info['location'] == (x, y, width, height):
                        brightness_data = info
                        break
                
                if brightness_data:
                    if brightness_data['available']:
                        box_color = "green"
                        label = f"{i+1} (✓{brightness_data['brightness']:.0f})"
                    else:
                        box_color = "red"
                        label = f"{i+1} (✗{brightness_data['brightness']:.0f})"
            
            # Draw rectangle with colored border
            draw.rectangle([x, y, x + width, y + height], outline=box_color, width=3)
            
            # Draw label
            if font:
                # Calculate text size for background
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Draw background for text
                draw.rectangle([x, y - text_height - 2, x + text_width + 4, y], 
                             fill=box_color, outline=box_color)
                
                # Draw text
                draw.text((x + 2, y - text_height - 1), label, fill="white", font=font)
            else:
                # Fallback without font
                draw.text((x + 2, y - 15), label, fill=box_color)
        
        # Add summary information
        summary_lines = [
            f"Skill Up Detection Results:",
            f"Available Buttons: {len(locations)}",
            f"Confidence: {confidence}"
        ]
        
        if filter_dark_buttons and brightness_info:
            total_detected = len(brightness_info)
            dark_buttons = len([info for info in brightness_info if not info['available']])
            summary_lines.extend([
                f"Total Detected: {total_detected}",
                f"Dark/Unavailable: {dark_buttons}",
                f"Legend: ✓=Available, ✗=Dark"
            ])
        
        summary_text = "\n".join(summary_lines)
        
        if font:
            draw.text((10, 10), summary_text, fill="blue", font=font)
        else:
            draw.text((10, 10), summary_text, fill="blue")
        
        # Save debug image with timestamp
        timestamp = int(time.time())
        debug_filename = f"debug_skill_up_{timestamp}.png"
        debug_path = os.path.join("debug_images", debug_filename)
        
        # Create debug directory if it doesn't exist
        os.makedirs("debug_images", exist_ok=True)
        
        # Save the image
        debug_image.save(debug_path)
        log_debug(f"Debug image saved: {debug_path}")
        
        return debug_path
        
    except Exception as e:
        log_debug(f"Error generating debug image: {e}")
        return None

def scan_all_skills_with_scroll(confidence=0.9, brightness_threshold=150, max_scrolls=20):
    """
    Scan all available skills by scrolling through the list until duplicates are found.
    Uses optimized slow swipe for smooth scrolling without acceleration.
    
    Args:
        confidence: Template matching confidence (default: 0.9)
        brightness_threshold: Brightness threshold for available buttons (default: 150)
        max_scrolls: Maximum number of scrolls to prevent infinite loops (default: 20)
    
    Returns:
        dict: {
            'all_skills': [list of all unique skills found],
            'total_unique_skills': int,
            'scrolls_performed': int,
            'duplicate_found': str or None
        }
    """
    log_debug(f"Scanning all available skills with scrolling")
    log_debug(f"=" * 60)
    
    all_skills = []
    seen_skill_names = set()
    scrolls_performed = 0
    duplicate_found = None
    
    try:
        while scrolls_performed < max_scrolls:
            log_debug(f"Scroll {scrolls_performed + 1}/{max_scrolls}")
            
            # Take screenshot and detect skills
            result = recognize_skill_up_locations(
                confidence=confidence,
                debug_output=False,
                filter_dark_buttons=True,
                brightness_threshold=brightness_threshold,
                extract_skills=True
            )
            
            if 'error' in result:
                log_debug(f"Error during skill detection: {result['error']}")
                break
            
            current_skills = result.get('skills', [])
            new_skills_found = 0
            
            if not current_skills:
                log_debug(f"No skills found on this screen")
                # Don't break here - continue scrolling to find skills
                # Only break if we've tried several empty screens in a row
                if scrolls_performed >= 3 and len(all_skills) == 0:
                    log_debug(f"No skills found after 3 scrolls - may not be on skill screen")
                    break
            else:
                # Check for duplicates and add new skills
                for skill in current_skills:
                    skill_name = skill['name']
                    
                    if skill_name in seen_skill_names:
                        log_debug(f"Duplicate found: '{skill_name}' - end of list reached")
                        duplicate_found = skill_name
                        log_debug(f"Stopping scan - we've looped back to already seen skills")
                        break
                    else:
                        seen_skill_names.add(skill_name)
                        all_skills.append(skill)
                        new_skills_found += 1
                        log_debug(f"{len(all_skills)}. {skill_name} - {skill['price']}")
                
                # Stop if duplicate found
                if duplicate_found:
                    break
            
            log_debug(f"Found {new_skills_found} new skills (Total: {len(all_skills)}")
            
            # Perform swipe to scroll down
            scrolls_performed += 1
            if scrolls_performed < max_scrolls:
                log_debug(f"Scrolling")
                success = swipe_skill_list_down_slow(wait_before=0.5, wait_after=1.5)
                
                if not success:
                    log_debug(f"Failed to perform swipe, stopping scan")
                    break
        
        # Summary
        log_debug(f"=" * 60)
        log_debug(f"Skill Scan Complete")
        log_debug(f"Total unique skills found: {len(all_skills)}")
        log_debug(f"Scrolls performed: {scrolls_performed}")
        if duplicate_found:
            log_debug(f"Stopped due to duplicate: {duplicate_found}")
        elif scrolls_performed >= max_scrolls:
            log_debug(f"Stopped due to max scroll limit reached")
        else:
            log_debug(f"Scan completed - reached end of list")
        
        return {
            'all_skills': all_skills,
            'total_unique_skills': len(all_skills),
            'scrolls_performed': scrolls_performed,
            'duplicate_found': duplicate_found
        }
        
    except Exception as e:
        log_debug(f"Error during skill scanning: {e}")
        return {
            'all_skills': all_skills,
            'total_unique_skills': len(all_skills),
            'scrolls_performed': scrolls_performed,
            'duplicate_found': None,
            'error': str(e)
        }


def deduplicate_skills(skills_list, similarity_threshold=0.8):
    """
    Deduplicate skills based on name similarity to avoid purchasing duplicate skills.
    
    Args:
        skills_list: List of skill dictionaries with 'name' and other fields
        similarity_threshold: Minimum similarity ratio to consider skills as duplicates (0.0 to 1.0)
    
    Returns:
        List of deduplicated skills
    """
    if not skills_list:
        return []
    
    if len(skills_list) == 1:
        return skills_list
    
    # Sort skills by price (cheaper first) to prioritize cheaper duplicates
    sorted_skills = sorted(skills_list, key=lambda x: int(x.get('price', '0')) if x.get('price', '0').isdigit() else 0)
    
    deduplicated = []
    seen_names = set()
    
    for skill in sorted_skills:
        skill_name = skill.get('name', '').lower().strip()
        
        if not skill_name:
            continue
        
        # Check if this skill name is similar to any already seen
        is_duplicate = False
        for seen_name in seen_names:
            similarity = calculate_string_similarity(skill_name, seen_name)
            if similarity >= similarity_threshold:
                is_duplicate = True
                log_debug(f"Duplicate detected: '{skill['name']}' similar to '{seen_name}' (similarity: {similarity:.2f}")
                break
        
        if not is_duplicate:
            deduplicated.append(skill)
            seen_names.add(skill_name)
            log_debug(f"Added unique skill: '{skill['name']}'")
        else:
            log_debug(f"Skipped duplicate skill: '{skill['name']}'")
    
    log_debug(f"Deduplication: {len(skills_list)} -> {len(deduplicated)} skills")
    return deduplicated


def calculate_string_similarity(str1, str2):
    """
    Calculate similarity between two strings using Levenshtein distance.
    
    Args:
        str1, str2: Strings to compare
    
    Returns:
        float: Similarity ratio (0.0 to 1.0, where 1.0 is identical)
    """
    if not str1 or not str2:
        return 0.0
    
    if str1 == str2:
        return 1.0
    
    # Calculate Levenshtein distance
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    distance = levenshtein_distance(str1, str2)
    max_length = max(len(str1), len(str2))
    
    if max_length == 0:
        return 1.0
    
    similarity = 1.0 - (distance / max_length)
    return similarity


def get_skills_api():
    """
    Get available skills from the API instead of OCR scan.

    Returns list of skill dicts matching scan_all_skills_with_scroll() output,
    or None if API is unavailable.
    """
    try:
        from utils.integrations.umat_api import get_skills, is_api_enabled
        if not is_api_enabled():
            return None
        api_data = get_skills()
    except ImportError:
        return None

    if api_data is None:
        return None

    skills_list = api_data.get("skills", [])
    if not skills_list:
        log_debug("[API] No skills from API")
        return None

    result = []
    for skill in skills_list:
        result.append({
            "name": skill.get("name", "Unknown"),
            "price": str(skill.get("price", 0)),
            "location": (0, 0, 0, 0),
            "regions": {"name_region": None, "price_region": None},
        })

    log_debug(f"[API] Got {len(result)} skills from API")
    return result

