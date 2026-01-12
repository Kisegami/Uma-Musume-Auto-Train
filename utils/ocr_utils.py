"""
Unified OCR utility module for all OCR operations.
Handles text extraction, number extraction, and specialized OCR tasks.
Supports both Tesseract (default) and EasyOCR GPU backends.
"""

import cv2
import numpy as np
import pytesseract
import os
import sys
import json
import time
import re
from PIL import Image
from typing import Tuple, Optional

from utils.log import log_debug, log_info, log_warning
from utils.config_loader import load_main_config

# ==================== EasyOCR GPU Backend ====================
# Lazy-loaded EasyOCR reader singleton (GPU only)
_easyocr_reader = None
_easyocr_init_attempted = False


def _get_ocr_backend() -> str:
    """Get configured OCR backend from config."""
    try:
        config = load_main_config()
        return config.get("ocr_backend", "tesseract")
    except Exception:
        return "tesseract"


def _get_easyocr_reader():
    """
    Get or initialize EasyOCR GPU reader (singleton, lazy-loaded).
    Returns None if EasyOCR GPU is not available.
    """
    global _easyocr_reader, _easyocr_init_attempted
    
    if _easyocr_reader is not None:
        return _easyocr_reader
    
    if _easyocr_init_attempted:
        return None  # Already tried and failed
    
    _easyocr_init_attempted = True
    
    try:
        import easyocr
        import torch
        
        # Only use GPU - no CPU fallback per requirements
        if not torch.cuda.is_available():
            log_warning("EasyOCR GPU requested but CUDA not available. Falling back to Tesseract.")
            return None
        
        log_info("Initializing EasyOCR GPU reader...")
        _easyocr_reader = easyocr.Reader(['en'], gpu=True)
        
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "Unknown"
        log_info(f"EasyOCR GPU initialized successfully using {gpu_name}")
        
        return _easyocr_reader
        
    except ImportError as e:
        log_warning(f"EasyOCR not installed: {e}. Falling back to Tesseract.")
        return None
    except Exception as e:
        log_warning(f"Failed to initialize EasyOCR GPU: {e}. Falling back to Tesseract.")
        return None


def _extract_text_easyocr_gpu(pil_img: Image.Image) -> str:
    """
    Extract text from image using GPU EasyOCR.
    
    Args:
        pil_img: PIL Image to extract text from
    
    Returns:
        Extracted text string
    """
    reader = _get_easyocr_reader()
    if reader is None:
        return ""
    
    try:
        img_np = np.array(pil_img)
        
        # Handle different image modes
        if len(img_np.shape) == 2:
            # Grayscale - convert to 3-channel
            img_np = np.stack([img_np] * 3, axis=-1)
        elif len(img_np.shape) == 3 and img_np.shape[2] == 4:
            # RGBA - convert to RGB
            img_np = img_np[:, :, :3]
        
        results = reader.readtext(img_np)
        
        # Sort by x-coordinate (left-to-right) for correct reading order
        sorted_results = sorted(results, key=lambda r: min(p[0] for p in r[0]))
        text_parts = [result[1] for result in sorted_results]
        return ' '.join(text_parts).strip()
        
    except Exception as e:
        log_debug(f"EasyOCR text extraction error: {e}")
        return ""


def _extract_number_easyocr_gpu(pil_img: Image.Image) -> str:
    """
    Extract numbers from image using GPU EasyOCR.
    
    Args:
        pil_img: PIL Image to extract numbers from
    
    Returns:
        Extracted digits string
    """
    reader = _get_easyocr_reader()
    if reader is None:
        return ""
    
    try:
        img_np = np.array(pil_img)
        
        # Handle different image modes
        if len(img_np.shape) == 2:
            img_np = np.stack([img_np] * 3, axis=-1)
        elif len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]
        
        results = reader.readtext(img_np)
        
        # Extract only digits from results
        text_parts = [result[1] for result in results]
        full_text = ' '.join(text_parts)
        
        # Extract all digit sequences
        digits = re.findall(r'\d+', full_text)
        return ''.join(digits) if digits else ""
        
    except Exception as e:
        log_debug(f"EasyOCR number extraction error: {e}")
        return ""


# ==================== End EasyOCR GPU Backend ====================

# Fix Windows console encoding for Unicode support
if os.name == 'nt':
    try:
        os.system('chcp 65001 > nul')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configure Tesseract to use custom trained data
# Get project root (utils/ocr_utils.py -> utils -> root)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tessdata_dir = os.path.join(_project_root, 'tessdata')
os.environ['TESSDATA_PREFIX'] = tessdata_dir

# Load config
config = load_main_config()
DEBUG_MODE = config.get("debug_mode", False)

# Try to find Tesseract executable automatically
def _setup_tesseract():
    """Setup Tesseract executable path"""
    try:
        if os.name == 'nt':
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(
                    os.getenv('USERNAME', '')
                )
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
    except Exception:
        pass  # Fall back to system PATH

_setup_tesseract()

# Verify tessdata directory
if not os.path.exists(tessdata_dir):
    if DEBUG_MODE:
        log_info(f"⚠️  Warning: tessdata directory not found: {tessdata_dir}")
        log_info(f"   Falling back to system Tesseract models")
else:
    available_models = [f for f in os.listdir(tessdata_dir) if f.endswith('.traineddata')]
    if available_models and DEBUG_MODE:
        log_info(f"✅ Using custom Tesseract models from: {tessdata_dir}")
        log_info(f"   Available models: {', '.join(available_models)}")


def verify_tesseract_config():
    """Verify which Tesseract configuration is being used"""
    try:
        tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'system PATH')
        log_info(f"🔍 Tesseract executable: {tesseract_cmd}")
        
        tessdata_prefix = os.environ.get('TESSDATA_PREFIX', 'Not set')
        log_info(f"🔍 TESSDATA_PREFIX: {tessdata_prefix}")
        
        if os.path.exists(tessdata_dir):
            custom_models = [f for f in os.listdir(tessdata_dir) if f.endswith('.traineddata')]
            log_info(f"🔍 Custom tessdata models: {custom_models}")
            
            try:
                version = pytesseract.get_tesseract_version()
                languages = pytesseract.get_languages()
                log_info(f"🔍 Tesseract version: {version}")
                log_info(f"🔍 Available languages: {languages}")
            except Exception as e:
                log_info(f"🔍 Could not get Tesseract info: {e}")
        else:
            log_info(f"🔍 Custom tessdata directory not found: {tessdata_dir}")
    except Exception as e:
        log_info(f"🔍 Error verifying Tesseract config: {e}")


# Verify configuration on import if debug mode is enabled
if DEBUG_MODE:
    verify_tesseract_config()


def _normalize_image(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL image to numpy array"""
    if isinstance(pil_img, Image.Image):
        return np.array(pil_img)
    return pil_img


def _preprocess_white_text(img_np: np.ndarray, threshold: int = 180) -> np.ndarray:
    """Preprocess image for white text extraction using thresholding"""
    # Convert to grayscale
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # White specialization - threshold bright pixels
    _, cleaned = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    
    # Clean up with morphological operations
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
    
    return cleaned


def extract_text(pil_img: Image.Image, config: Optional[str] = None) -> str:
    """Extract text from image using configured OCR backend.
    
    Uses EasyOCR GPU if configured and available, otherwise falls back to Tesseract.
    
    Args:
        pil_img: PIL Image to extract text from
        config: Optional Tesseract config string (only used with Tesseract backend)
    
    Returns:
        Extracted text string
    """
    # Check if EasyOCR GPU backend is configured
    backend = _get_ocr_backend()
    if backend == "easyocr_gpu":
        result = _extract_text_easyocr_gpu(pil_img)
        if result:  # EasyOCR succeeded
            return result
        # Fall through to Tesseract if EasyOCR failed
    
    # Use Tesseract (default or fallback)
    return _extract_text_tesseract(pil_img, config)


def _extract_text_tesseract(pil_img: Image.Image, config: Optional[str] = None) -> str:
    """Extract text from image using Tesseract OCR (internal function)"""
    try:
        img_np = _normalize_image(pil_img)
        text = pytesseract.image_to_string(img_np, lang='eng', config=config or '')
        result = text.strip()
        
        if not result and DEBUG_MODE:
            debug_filename = f"debug_ocr_text_failed_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR text extraction failed, saved debug image: {debug_filename}")
        
        return result
    except Exception as e:
        if DEBUG_MODE:
            debug_filename = f"debug_ocr_text_error_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR text extraction error: {e}, saved debug image: {debug_filename}")
        log_warning(f"OCR extraction failed: {e}")
        return ""


def extract_number(pil_img: Image.Image, config: Optional[str] = None) -> str:
    """Extract numbers from image using configured OCR backend.
    
    Uses EasyOCR GPU if configured and available, otherwise falls back to Tesseract.
    
    Args:
        pil_img: PIL Image to extract numbers from
        config: Optional Tesseract config string (only used with Tesseract backend)
    
    Returns:
        Extracted digits string
    """
    # Check if EasyOCR GPU backend is configured
    backend = _get_ocr_backend()
    if backend == "easyocr_gpu":
        result = _extract_number_easyocr_gpu(pil_img)
        if result:  # EasyOCR succeeded
            return result
        # Fall through to Tesseract if EasyOCR failed
    
    # Use Tesseract (default or fallback)
    return _extract_number_tesseract(pil_img, config)


def _extract_number_tesseract(pil_img: Image.Image, config: Optional[str] = None) -> str:
    """Extract numbers from image using Tesseract OCR (internal function)
    
    Args:
        pil_img: PIL Image to extract numbers from
        config: Optional Tesseract config string. Default: '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
    """
    try:
        img_np = _normalize_image(pil_img)
        if config is None:
            config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        result = text.strip()
        
        if not result and DEBUG_MODE:
            debug_filename = f"debug_ocr_number_failed_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR number extraction failed, saved debug image: {debug_filename}")
        
        return result
    except Exception as e:
        if DEBUG_MODE:
            debug_filename = f"debug_ocr_number_error_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR number extraction error: {e}, saved debug image: {debug_filename}")
        log_warning(f"Number extraction failed: {e}")
        return ""


def extract_text_with_data(pil_img: Image.Image, config: Optional[str] = None) -> dict:
    """Extract text with detailed OCR data (including confidence scores)
    
    Args:
        pil_img: PIL Image to extract text from
        config: Optional Tesseract config string
    
    Returns:
        dict: Tesseract OCR data dictionary with keys: 'text', 'conf', 'left', 'top', 'width', 'height', etc.
    """
    try:
        img_np = _normalize_image(pil_img)
        data = pytesseract.image_to_data(
            img_np,
            config=config or '',
            lang='eng',
            output_type=pytesseract.Output.DICT
        )
        return data
    except Exception as e:
        log_warning(f"OCR data extraction failed: {e}")
        return {}


def extract_event_name_text(pil_img: Image.Image) -> str:
    """Extract event name text using white specialization and confidence filtering"""
    try:
        img_np = _normalize_image(pil_img)
        cleaned = _preprocess_white_text(img_np, threshold=180)
        
        # OCR with confidence filtering
        data = pytesseract.image_to_data(
            cleaned,
            config="-c preserve_interword_spaces=1",
            lang='eng',
            output_type=pytesseract.Output.DICT
        )
        
        # Filter by confidence (>= 70)
        high_confidence_words = []
        all_words = []
        
        for i in range(len(data['text'])):
            word = data['text'][i].strip()
            conf = int(data['conf'][i])
            if word:
                all_words.append(f"{word}({conf})")
                if conf >= 70:
                    high_confidence_words.append(word)
        
        if DEBUG_MODE:
            if all_words:
                log_debug(f"Event name ALL OCR detections: {' '.join(all_words)}")
            else:
                log_debug(f"Event name OCR: No text detected at all")
        
        result_text = ' '.join(high_confidence_words).strip()
        
        if result_text:
            if DEBUG_MODE:
                log_debug(f"Event name OCR result: '{result_text}'")
            return result_text
        else:
            if DEBUG_MODE:
                log_debug(f"Event name: No high-confidence text found (threshold: 70)")
                processed_img = Image.fromarray(cleaned)
                debug_filename = f"debug_event_ocr_processed_{int(time.time())}.png"
                processed_img.save(debug_filename)
                log_debug(f"Event name: Processed OCR image saved to {debug_filename}")
            return ""
    except Exception as e:
        log_warning(f"Event name OCR extraction failed: {e}")
        return ""



