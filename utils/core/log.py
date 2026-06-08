import os
import sys
import logging
from collections import deque
from datetime import datetime
from threading import Lock
from utils.core.config_loader import load_main_config

# Load DEBUG_MODE once; fallback to False on error
_cfg = load_main_config()
DEBUG_MODE = _cfg.get("debug_mode", False)

# Configure logger
logger = logging.getLogger('uma_musume_bot')
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

# Prevent duplicate messages by disabling propagation to root logger
logger.propagate = False

_recent_log_lines = deque(maxlen=1000)
_recent_log_lock = Lock()


class _RecentLogHandler(logging.Handler):
    """Keep timestamped log lines available for diagnostic bundles."""

    def emit(self, record):
        try:
            timestamp = datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds")
            message_lines = record.getMessage().splitlines() or [""]
            with _recent_log_lock:
                for line in message_lines:
                    _recent_log_lines.append({
                        "timestamp": timestamp,
                        "level": record.levelname,
                        "message": line,
                    })
        except Exception:
            self.handleError(record)

# Create console handler if not already exists
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    # Create formatter without timestamp since GUI adds its own timestamp
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)

if not any(isinstance(handler, _RecentLogHandler) for handler in logger.handlers):
    recent_log_handler = _RecentLogHandler()
    recent_log_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    logger.addHandler(recent_log_handler)


def get_recent_log_lines(limit=100):
    """Return a copy of the latest timestamped log lines."""
    safe_limit = max(0, int(limit))
    with _recent_log_lock:
        if safe_limit == 0:
            return []
        return [dict(entry) for entry in list(_recent_log_lines)[-safe_limit:]]

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


