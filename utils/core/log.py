import os
import sys
import logging
from datetime import datetime
from utils.core.config_loader import load_main_config

# Load DEBUG_MODE once; fallback to False on error
_cfg = load_main_config()
DEBUG_MODE = _cfg.get("debug_mode", False)

# Configure logger
logger = logging.getLogger('uma_musume_bot')
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

# Prevent duplicate messages by disabling propagation to root logger
logger.propagate = False

# Create console handler if not already exists
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    # Create formatter without timestamp since GUI adds its own timestamp
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)

def safe_encode_message(message):
    """Safely encode message to handle Unicode errors"""
    try:
        return str(message)
    except UnicodeEncodeError:
        try:
            return str(message).encode('ascii', errors='replace').decode('ascii')
        except Exception:
            return "[Message encoding error]"

def log_info(message):
    """Log info level message"""
    try:
        safe_message = safe_encode_message(message)
        logger.info(safe_message)
        sys.stdout.flush()
    except Exception:
        print(f"[INFO] {safe_encode_message(message)}")
        sys.stdout.flush()

def log_warning(message):
    """Log warning level message"""
    try:
        safe_message = safe_encode_message(message)
        logger.warning(safe_message)
        sys.stdout.flush()
    except Exception:
        print(f"[WARNING] {safe_encode_message(message)}")
        sys.stdout.flush()

def log_error(message):
    """Log error level message"""
    try:
        safe_message = safe_encode_message(message)
        logger.error(safe_message)
        sys.stdout.flush()
    except Exception:
        print(f"[ERROR] {safe_encode_message(message)}")
        sys.stdout.flush()

def log_debug(message):
    """Log debug level message"""
    if DEBUG_MODE:
        try:
            safe_message = safe_encode_message(message)
            logger.debug(safe_message)
            sys.stdout.flush()
        except Exception:
            print(f"[DEBUG] {safe_encode_message(message)}")
            sys.stdout.flush()

def log_success(message):
    """Log success level message (treated as info with SUCCESS prefix)"""
    try:
        safe_message = safe_encode_message(message)
        logger.info(f"SUCCESS: {safe_message}")
        sys.stdout.flush()
    except Exception:
        print(f"[SUCCESS] {safe_encode_message(message)}")
        sys.stdout.flush()

# Legacy functions for backward compatibility
def debug_print(message):
    """Legacy debug print function - use log_debug instead"""
    log_debug(message)

def safe_print(message):
    """Legacy safe print function - use log_info instead"""
    log_info(message)


