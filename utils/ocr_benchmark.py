"""
OCR Benchmark Utility
Run OCR performance benchmarks using real-time emulator capture.
Supports both Tesseract and EasyOCR GPU backends.
"""

import time
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from PIL import Image
import pytesseract
import re

from utils.screenshot_unified import get_unified_screenshot
from utils.screenshot import enhanced_screenshot
from utils.constants_unity import (
    TURN_REGION, YEAR_REGION, CRITERIA_REGION, SKILL_PTS_REGION,
    SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION
)

# Goal region (same as in test_ocr_speed_comparison.py)
GOAL_REGION = (357, 113, 714, 155)


@dataclass
class RegionResult:
    """Result for a single OCR region benchmark"""
    region_name: str
    tesseract_time_ms: float
    tesseract_result: str
    easyocr_time_ms: Optional[float] = None
    easyocr_result: Optional[str] = None
    
    @property
    def speedup(self) -> Optional[float]:
        """Calculate speedup (>1 means EasyOCR is faster)"""
        if self.easyocr_time_ms and self.easyocr_time_ms > 0:
            return self.tesseract_time_ms / self.easyocr_time_ms
        return None


@dataclass 
class BenchmarkResult:
    """Complete benchmark result"""
    regions: List[RegionResult]
    total_tesseract_ms: float
    total_easyocr_ms: Optional[float]
    screenshot: Image.Image
    iterations: int
    error: Optional[str] = None
    
    @property
    def overall_speedup(self) -> Optional[float]:
        if self.total_easyocr_ms and self.total_easyocr_ms > 0:
            return self.total_tesseract_ms / self.total_easyocr_ms
        return None


def _extract_text_tesseract(pil_img: Image.Image, config: str = None) -> str:
    """Extract text using Tesseract OCR"""
    try:
        img_np = np.array(pil_img)
        if config:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        else:
            text = pytesseract.image_to_string(img_np, lang='eng')
        return text.strip()
    except Exception:
        return ""


def _extract_number_tesseract(pil_img: Image.Image) -> str:
    """Extract numbers using Tesseract OCR"""
    try:
        img_np = np.array(pil_img)
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        return text.strip()
    except Exception:
        return ""


def _get_easyocr_reader():
    """Get EasyOCR reader (lazy loaded)"""
    try:
        import easyocr
        import torch
        if not torch.cuda.is_available():
            return None
        reader = easyocr.Reader(['en'], gpu=True)
        return reader
    except ImportError:
        return None
    except Exception:
        return None


def _extract_text_easyocr(pil_img: Image.Image, reader) -> str:
    """Extract text using GPU EasyOCR"""
    try:
        img_np = np.array(pil_img)
        if len(img_np.shape) == 2:
            img_np = np.stack([img_np] * 3, axis=-1)
        elif img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]
        
        results = reader.readtext(img_np)
        sorted_results = sorted(results, key=lambda r: min(p[0] for p in r[0]))
        text_parts = [result[1] for result in sorted_results]
        return ' '.join(text_parts).strip()
    except Exception:
        return ""


def _extract_number_easyocr(pil_img: Image.Image, reader) -> str:
    """Extract numbers using GPU EasyOCR"""
    try:
        img_np = np.array(pil_img)
        if len(img_np.shape) == 2:
            img_np = np.stack([img_np] * 3, axis=-1)
        elif img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]
        
        results = reader.readtext(img_np)
        text_parts = [result[1] for result in results]
        full_text = ' '.join(text_parts)
        digits = re.findall(r'\d+', full_text)
        return ''.join(digits) if digits else ""
    except Exception:
        return ""


def capture_emulator_screenshot() -> Image.Image:
    """
    Capture screenshot from the emulator using UnifiedScreenshot.
    
    Returns:
        PIL Image of the current emulator screen
        
    Raises:
        Exception if capture fails
    """
    unified = get_unified_screenshot()
    screenshot = unified.take_screenshot()
    return screenshot


def run_ocr_benchmark(
    include_easyocr: bool = False,
    iterations: int = 5,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> BenchmarkResult:
    """
    Run OCR benchmark using real-time emulator capture.
    
    Args:
        include_easyocr: If True, also benchmark EasyOCR GPU
        iterations: Number of iterations for each test
        progress_callback: Optional callback(message, percent) for progress updates
        
    Returns:
        BenchmarkResult with timing data for all regions
    """
    def report(msg: str, pct: int):
        if progress_callback:
            progress_callback(msg, pct)
    
    try:
        # Step 1: Capture screenshot
        report("Capturing emulator screenshot...", 5)
        screenshot = capture_emulator_screenshot()
        report(f"Screenshot captured ({screenshot.size[0]}x{screenshot.size[1]})", 10)
        
        # Step 2: Initialize EasyOCR if needed
        reader = None
        if include_easyocr:
            report("Initializing EasyOCR GPU...", 15)
            reader = _get_easyocr_reader()
            if not reader:
                return BenchmarkResult(
                    regions=[],
                    total_tesseract_ms=0,
                    total_easyocr_ms=None,
                    screenshot=screenshot,
                    iterations=iterations,
                    error="EasyOCR GPU not available"
                )
            report("EasyOCR GPU ready", 20)
        
        # Step 3: Define test regions
        test_regions = [
            ('Year', YEAR_REGION, 'text'),
            ('Criteria', CRITERIA_REGION, 'text'),
            ('Goal', GOAL_REGION, 'text'),
            ('Skill Points', SKILL_PTS_REGION, 'number'),
            ('SPD', SPD_REGION, 'number'),
            ('STA', STA_REGION, 'number'),
            ('PWR', PWR_REGION, 'number'),
            ('GUTS', GUTS_REGION, 'number'),
            ('WIT', WIT_REGION, 'number'),
        ]
        
        # Warmup iteration
        report("Running warmup...", 25)
        warmup_img = screenshot.crop(YEAR_REGION)
        _extract_text_tesseract(warmup_img)
        if reader:
            _extract_text_easyocr(warmup_img, reader)
        
        # Step 4: Run benchmarks
        results = []
        total_tesseract = 0
        total_easyocr = 0
        
        for idx, (name, region, ocr_type) in enumerate(test_regions):
            progress = 30 + int((idx / len(test_regions)) * 60)
            report(f"Testing {name}...", progress)
            
            # Get region image
            if ocr_type == 'text' and name in ('Year', 'Goal'):
                region_img = enhanced_screenshot(region, screenshot)
            else:
                region_img = screenshot.crop(region)
            
            # Tesseract benchmark
            tess_times = []
            tess_result = ""
            for i in range(iterations):
                start = time.perf_counter()
                if ocr_type == 'number':
                    tess_result = _extract_number_tesseract(region_img)
                else:
                    tess_result = _extract_text_tesseract(region_img, '--oem 3 --psm 7')
                tess_times.append(time.perf_counter() - start)
            
            avg_tess = sum(tess_times) / len(tess_times) * 1000
            total_tesseract += avg_tess
            
            # EasyOCR benchmark (if enabled)
            avg_easyocr = None
            easyocr_result = None
            if reader:
                easyocr_times = []
                for i in range(iterations):
                    start = time.perf_counter()
                    if ocr_type == 'number':
                        easyocr_result = _extract_number_easyocr(region_img, reader)
                    else:
                        easyocr_result = _extract_text_easyocr(region_img, reader)
                    easyocr_times.append(time.perf_counter() - start)
                
                avg_easyocr = sum(easyocr_times) / len(easyocr_times) * 1000
                total_easyocr += avg_easyocr
            
            results.append(RegionResult(
                region_name=name,
                tesseract_time_ms=avg_tess,
                tesseract_result=tess_result[:30] if tess_result else "",
                easyocr_time_ms=avg_easyocr,
                easyocr_result=easyocr_result[:30] if easyocr_result else None
            ))
        
        report("Benchmark complete!", 100)
        
        return BenchmarkResult(
            regions=results,
            total_tesseract_ms=total_tesseract,
            total_easyocr_ms=total_easyocr if reader else None,
            screenshot=screenshot,
            iterations=iterations
        )
        
    except Exception as e:
        return BenchmarkResult(
            regions=[],
            total_tesseract_ms=0,
            total_easyocr_ms=None,
            screenshot=None,
            iterations=iterations,
            error=str(e)
        )
