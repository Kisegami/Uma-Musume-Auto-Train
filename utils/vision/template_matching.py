import cv2
import numpy as np
from typing import List, Tuple, Optional
from utils.core.log import debug_print
from utils.core.log import log_debug, log_info, log_warning, log_error

def deduplicated_matches(matches: List[Tuple[int, int, int, int]], 
                        threshold: int = 30) -> List[Tuple[int, int, int, int]]:
    """
    Remove duplicate template matches based on center distance.
    
    Args:
        matches: List of (x, y, w, h) bounding boxes
        threshold: Minimum distance between centers (default: 30px)
    
    Returns:
        Filtered list with duplicates removed
    """
    # Safety check: ensure matches is a list
    if not matches:
        return []
    
    # Additional safety check: ensure matches is actually a list
    if not isinstance(matches, list):
        log_warning(f"deduplicated_matches received non-list: {type(matches)}, {matches}")
        return []
    
    # Safety check: ensure matches has at least one element
    if len(matches) == 0:
        return []
    
    filtered = [matches[0]]
    
    for match in matches[1:]:
        # Safety check: ensure match is a valid tuple
        if not isinstance(match, tuple) or len(match) != 4:
            log_warning(f"Invalid match format: {match}")
            continue
            
        match_center = (match[0] + match[2]//2, match[1] + match[3]//2)
        
        is_duplicate = False
        for existing in filtered:
            existing_center = (existing[0] + existing[2]//2, existing[1] + existing[3]//2)
            
            distance = np.sqrt((match_center[0] - existing_center[0])**2 + 
                             (match_center[1] - existing_center[1])**2)
            
            if distance < threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered.append(match)
    
    return filtered

def wait_for_image(template_path: str, 
                   timeout: int = 10, 
                   confidence: float = 0.8, 
                   region: Optional[Tuple[int, int, int, int]] = None,
                   check_interval: float = 0.5) -> Optional[Tuple[int, int]]:
    """
    Wait for an image to appear on screen with configurable timeout and interval.
    
    Args:
        template_path: Path to template image
        timeout: Maximum time to wait in seconds
        confidence: Template matching confidence threshold
        region: Optional region to search in (x, y, w, h)
        check_interval: Time between checks in seconds
    
    Returns:
        (x, y) center coordinates if image found, None if timeout
    """
    import time
    from utils.vision.recognizer import locate_on_screen
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        result = locate_on_screen(template_path, confidence, region)
        if result:
            return result
        time.sleep(check_interval)
    
    return None
