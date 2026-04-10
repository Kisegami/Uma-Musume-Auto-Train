"""
OCR module for Trackblazer mode.
This module re-exports OCR functions from utils.ocr.ocr_utils for backward compatibility.
All OCR functionality has been moved to utils.ocr.ocr_utils for better code organization.
"""

# Re-export all OCR functions from utils.ocr.ocr_utils
from utils.ocr.ocr_utils import (
    extract_text,
    extract_number,
    extract_text_with_data,
    extract_event_name_text,
    verify_tesseract_config
)

# Re-export event matching from event_handling
from core.Trackblazer.event_handling import find_best_event_match

__all__ = [
    'extract_text',
    'extract_number',
    'extract_text_with_data',
    'extract_event_name_text',
    'find_best_event_match',
    'verify_tesseract_config'
]


