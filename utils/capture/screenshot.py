import subprocess
import tempfile
import os
from PIL import Image, ImageEnhance
import numpy as np
# This module now uses the unified screenshot system
# Import all functions from the new unified module for backward compatibility
from utils.core.log import log_info, log_warning, log_error, log_debug, log_success
from utils.core.config_loader import load_config_section
from utils.capture.screenshot_unified import (
    take_screenshot,
    get_screen_size,
    enhanced_screenshot,
    enhanced_screenshot_for_failure,
    enhanced_screenshot_for_year,
    capture_region,
    get_unified_screenshot,
    UnifiedScreenshot
)

# Legacy functions for backward compatibility
def load_config():
    """Load ADB configuration from config.json (legacy function)"""
    try:
        return load_config_section('adb_config', {})
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return {}

def run_adb_command(command, binary=False):
    """Backward-compatible wrapper to utils.adb.run_adb (legacy function)"""
    from utils.platform.device import run_adb
    return run_adb(command, binary=binary, add_input_delay=False) 