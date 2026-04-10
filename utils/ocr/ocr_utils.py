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
import threading
from PIL import Image
from typing import Tuple, Optional, Dict, Any

from utils.core.log import log_debug, log_info, log_warning
from utils.core.config_loader import load_main_config

# ==================== EasyOCR GPU Backend ====================
# Lazy-loaded EasyOCR reader singleton (GPU only)
_easyocr_reader = None
_easyocr_init_attempted = False
_easyocr_init_lock = threading.Lock()
_easyocr_status = {
    "state": "idle",
    "ready": False,
    "gpu_name": None,
    "cuda_version": None,
    "error": None,
    "init_duration_ms": None,
}


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

    with _easyocr_init_lock:
        if _easyocr_reader is not None:
            return _easyocr_reader

        if _easyocr_init_attempted:
            return None

        _easyocr_init_attempted = True
        _easyocr_status.update({
            "state": "initializing",
            "ready": False,
            "gpu_name": None,
            "cuda_version": None,
            "error": None,
            "init_duration_ms": None,
        })
        start_time = time.perf_counter()

        try:
            import easyocr
            import torch
            
            # Only use GPU - no CPU fallback per requirements
            if not torch.cuda.is_available():
                message = "EasyOCR GPU requested but CUDA not available. Falling back to Tesseract."
                _easyocr_status.update({
                    "state": "failed",
                    "error": message,
                    "cuda_version": torch.version.cuda,
                })
                log_warning(message)
                return None
            
            log_info("Initializing EasyOCR GPU reader with english_g2 model...")
            
            # Use custom model from utils/models directory
            utils_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(utils_dir, 'models')
            
            _easyocr_reader = easyocr.Reader(
                ['en'],
                gpu=True,
                model_storage_directory=model_dir,
                recog_network='english_g2'
            )
            
            gpu_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "Unknown"
            init_duration_ms = (time.perf_counter() - start_time) * 1000
            _easyocr_status.update({
                "state": "ready",
                "ready": True,
                "gpu_name": gpu_name,
                "cuda_version": torch.version.cuda,
                "error": None,
                "init_duration_ms": init_duration_ms,
            })
            log_info(f"EasyOCR GPU initialized successfully with english_g2 model using {gpu_name}")
            
            return _easyocr_reader
            
        except ImportError as e:
            message = f"EasyOCR not installed: {e}. Falling back to Tesseract."
            _easyocr_status.update({
                "state": "failed",
                "error": message,
                "init_duration_ms": (time.perf_counter() - start_time) * 1000,
            })
            log_warning(message)
            return None
        except Exception as e:
            message = f"Failed to initialize EasyOCR GPU: {e}. Falling back to Tesseract."
            _easyocr_status.update({
                "state": "failed",
                "error": message,
                "init_duration_ms": (time.perf_counter() - start_time) * 1000,
            })
            log_warning(message)
            return None


def get_easyocr_runtime_status() -> Dict[str, Any]:
    """Return the current EasyOCR runtime initialization status."""
    return dict(_easyocr_status)


def warmup_easyocr_reader() -> Dict[str, Any]:
    """Initialize the EasyOCR GPU reader in advance and return runtime status."""
    _get_easyocr_reader()
    return get_easyocr_runtime_status()


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
        
        # Use direct OCR with relaxed parameters for better small text detection
        # detail=0 returns just text strings, paragraph=False treats each line separately
        # low_text=0.3 and link_threshold=0.3 help detect smaller text
        results = reader.readtext(
            img_np,
            detail=1,
            paragraph=False,
            contrast_ths=0.1,
            adjust_contrast=0.5,
            text_threshold=0.5,
            low_text=0.3,
            link_threshold=0.3
        )
        
        if not results:
            return ""
        
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
        
        # Use relaxed parameters for better small text/number detection
        results = reader.readtext(
            img_np,
            detail=1,
            paragraph=False,
            contrast_ths=0.1,
            adjust_contrast=0.5,
            text_threshold=0.5,
            low_text=0.3,
            link_threshold=0.3,
            allowlist='0123456789%'  # Only detect digits and percent sign
        )
        
        if not results:
            return ""
        
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
# Get project root (utils/ocr/ocr_utils.py -> utils -> root)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


def _parse_tesseract_confidence(raw_conf: Any) -> int:
    """Parse a Tesseract confidence value into an integer score."""
    try:
        return int(float(raw_conf))
    except (TypeError, ValueError):
        return -1


def _extract_event_name_candidates(img_np: np.ndarray) -> list[tuple[str, int, list[str], str]]:
    """Run several OCR passes and return ranked event-name candidates.

    Each entry is: (text, score, all_words, pass_name)
    """
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np.copy()

    # Upscale small crops to improve OCR stability on emulator captures.
    upscaled_gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    processed_variants = [
        ("white_180", _preprocess_white_text(img_np, threshold=180)),
        ("white_165", _preprocess_white_text(img_np, threshold=165)),
        ("gray", gray),
        ("gray_up2x", upscaled_gray),
    ]
    tesseract_configs = [
        ("psm7", "--oem 3 --psm 7 -c preserve_interword_spaces=1"),
        ("psm6", "--oem 3 --psm 6 -c preserve_interword_spaces=1"),
    ]

    candidates = []
    for variant_name, processed in processed_variants:
        for config_name, tess_config in tesseract_configs:
            try:
                data = pytesseract.image_to_data(
                    processed,
                    config=tess_config,
                    lang='eng',
                    output_type=pytesseract.Output.DICT
                )
            except Exception as e:
                log_debug(f"Event OCR pass failed for {variant_name}/{config_name}: {e}")
                continue

            words = []
            conf_sum = 0
            conf_count = 0
            all_words = []

            for i in range(len(data.get('text', []))):
                word = data['text'][i].strip()
                conf = _parse_tesseract_confidence(data['conf'][i])
                if word:
                    all_words.append(f"{word}({conf})")
                    if conf >= 50:
                        words.append(word)
                        conf_sum += conf
                        conf_count += 1

            text = ' '.join(words).strip()
            avg_conf = int(conf_sum / conf_count) if conf_count else -1

            # Score favors confident text with useful length.
            score = avg_conf
            if text:
                score += min(len(text), 30)

            candidates.append((text, score, all_words, f"{variant_name}/{config_name}"))

    return sorted(candidates, key=lambda item: item[1], reverse=True)


def extract_event_name_text(pil_img: Image.Image) -> str:
    """Extract event name text using a multi-pass OCR fallback pipeline."""
    try:
        img_np = _normalize_image(pil_img)
        candidates = _extract_event_name_candidates(img_np)

        if DEBUG_MODE:
            if candidates:
                for text, score, all_words, pass_name in candidates[:4]:
                    if all_words:
                        log_debug(f"Event OCR {pass_name}: {' '.join(all_words)} | score={score} | text='{text}'")
                    else:
                        log_debug(f"Event OCR {pass_name}: no text | score={score}")
            else:
                log_debug("Event name OCR: No text detected at all")

        for text, score, _, pass_name in candidates:
            if text:
                if DEBUG_MODE:
                    log_debug(f"Event name OCR result: '{text}' from {pass_name} (score={score})")
                return text

        if DEBUG_MODE:
            cleaned = _preprocess_white_text(img_np, threshold=180)
            log_debug("Event name: No usable text found across OCR passes")
            processed_img = Image.fromarray(cleaned)
            debug_filename = f"debug_event_ocr_processed_{int(time.time())}.png"
            processed_img.save(debug_filename)
            log_debug(f"Event name: Processed OCR image saved to {debug_filename}")
        return ""
    except Exception as e:
        log_warning(f"Event name OCR extraction failed: {e}")
        return ""



