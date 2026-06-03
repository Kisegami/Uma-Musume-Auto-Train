"""
Template matching benchmark utilities.

This module is focused on measuring Trackblazer template matching cost on a
live emulator screenshot. It compares region-limited searches against
full-screen searches and validates that the recognizer resolves Trackblazer
regions as expected.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

from utils.capture.screenshot_unified import get_unified_screenshot
from utils.constants.trackblazer import TRACKBLAZER_TEMPLATE_REGIONS, get_template_region
from utils.core.log import log_error, log_info
from utils.vision import recognizer


BenchmarkRegion = Tuple[int, int, int, int]


@dataclass
class TemplateBenchmarkResult:
    template_path: str
    template_size: Tuple[int, int]
    resolved_region: Optional[BenchmarkRegion]
    resolver_ok: bool
    region_search_area: Optional[int]
    full_search_area: int
    area_reduction_ratio: Optional[float]
    region_avg_ms: Optional[float]
    full_avg_ms: float
    speedup: Optional[float]
    region_match_count: Optional[int]
    full_match_count: int
    region_max_confidence: Optional[float]
    full_max_confidence: float


@dataclass
class TrackblazerTemplateBenchmarkResult:
    screenshot_size: Tuple[int, int]
    iterations: int
    templates_tested: int
    results: List[TemplateBenchmarkResult]
    avg_region_ms: Optional[float]
    avg_full_ms: float
    avg_speedup: Optional[float]
    all_resolvers_ok: bool
    report_path: Optional[str] = None
    error: Optional[str] = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_report_path() -> Path:
    debug_dir = _project_root() / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir / "trackblazer_template_match_benchmark.json"


def _capture_screenshot() -> Image.Image:
    unified = get_unified_screenshot()
    return unified.take_screenshot()


def _run_match_benchmark(
    screenshot_cv: np.ndarray,
    template: np.ndarray,
    confidence: float,
    iterations: int,
    region: Optional[BenchmarkRegion],
) -> Tuple[float, int, float]:
    if region is not None:
        x, y, w, h = region
        search_img = screenshot_cv[y:y + h, x:x + w]
    else:
        search_img = screenshot_cv

    times: List[float] = []
    match_count = 0
    max_confidence = 0.0

    for _ in range(iterations):
        start = time.perf_counter()
        result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times.append(elapsed_ms)

        locations = np.where(result >= confidence)
        match_count = len(locations[0])
        _, peak, _, _ = cv2.minMaxLoc(result)
        max_confidence = float(peak)

    return sum(times) / len(times), match_count, max_confidence


def _resolve_region_for_trackblazer(template_path: str) -> Optional[BenchmarkRegion]:
    original_loader = recognizer.load_main_config
    try:
        recognizer.load_main_config = lambda path="config.json": {
            "mode": "trackblazer",
            "bypass_template_regions": False,
        }
        return recognizer._resolve_search_region(template_path, None)
    finally:
        recognizer.load_main_config = original_loader


def run_trackblazer_template_benchmark(
    iterations: int = 20,
    confidence: float = 0.8,
    template_paths: Optional[Sequence[str]] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    report_path: Optional[Path] = None,
) -> TrackblazerTemplateBenchmarkResult:
    def report(message: str, pct: int) -> None:
        if progress_callback:
            progress_callback(message, pct)

    try:
        report("Capturing emulator screenshot...", 5)
        screenshot = _capture_screenshot()
        screenshot_cv = recognizer._screenshot_to_cv(screenshot)
        screen_w, screen_h = screenshot.size
        full_area = screen_w * screen_h

        paths = list(template_paths) if template_paths else sorted(TRACKBLAZER_TEMPLATE_REGIONS)
        results: List[TemplateBenchmarkResult] = []

        report("Running template matching benchmark...", 10)
        for index, template_path in enumerate(paths, start=1):
            pct = 10 + int(index / max(len(paths), 1) * 80)
            report(f"Benchmarking {template_path}...", pct)

            template = recognizer._load_template(template_path)
            if template is None:
                continue

            resolved_region = _resolve_region_for_trackblazer(template_path)
            expected_region = get_template_region(template_path)
            resolver_ok = resolved_region == expected_region

            full_avg_ms, full_count, full_conf = _run_match_benchmark(
                screenshot_cv,
                template,
                confidence,
                iterations,
                region=None,
            )

            region_avg_ms: Optional[float] = None
            region_count: Optional[int] = None
            region_conf: Optional[float] = None
            region_area: Optional[int] = None
            area_reduction_ratio: Optional[float] = None
            speedup: Optional[float] = None

            if resolved_region is not None:
                region_avg_ms, region_count, region_conf = _run_match_benchmark(
                    screenshot_cv,
                    template,
                    confidence,
                    iterations,
                    region=resolved_region,
                )
                region_area = resolved_region[2] * resolved_region[3]
                area_reduction_ratio = 1.0 - (region_area / full_area)
                if region_avg_ms > 0:
                    speedup = full_avg_ms / region_avg_ms

            results.append(
                TemplateBenchmarkResult(
                    template_path=template_path,
                    template_size=(int(template.shape[1]), int(template.shape[0])),
                    resolved_region=resolved_region,
                    resolver_ok=resolver_ok,
                    region_search_area=region_area,
                    full_search_area=full_area,
                    area_reduction_ratio=area_reduction_ratio,
                    region_avg_ms=region_avg_ms,
                    full_avg_ms=full_avg_ms,
                    speedup=speedup,
                    region_match_count=region_count,
                    full_match_count=full_count,
                    region_max_confidence=region_conf,
                    full_max_confidence=full_conf,
                )
            )

        avg_region_values = [row.region_avg_ms for row in results if row.region_avg_ms is not None]
        avg_speedup_values = [row.speedup for row in results if row.speedup is not None]

        benchmark = TrackblazerTemplateBenchmarkResult(
            screenshot_size=(screen_w, screen_h),
            iterations=iterations,
            templates_tested=len(results),
            results=results,
            avg_region_ms=(sum(avg_region_values) / len(avg_region_values)) if avg_region_values else None,
            avg_full_ms=(sum(row.full_avg_ms for row in results) / len(results)) if results else 0.0,
            avg_speedup=(sum(avg_speedup_values) / len(avg_speedup_values)) if avg_speedup_values else None,
            all_resolvers_ok=all(row.resolver_ok for row in results),
        )

        output_path = report_path or _default_report_path()
        output_path.write_text(
            json.dumps(asdict(benchmark), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        benchmark.report_path = str(output_path)
        report("Benchmark complete.", 100)
        return benchmark
    except Exception as exc:
        log_error(f"Trackblazer template benchmark failed: {exc}")
        return TrackblazerTemplateBenchmarkResult(
            screenshot_size=(0, 0),
            iterations=iterations,
            templates_tested=0,
            results=[],
            avg_region_ms=None,
            avg_full_ms=0.0,
            avg_speedup=None,
            all_resolvers_ok=False,
            error=str(exc),
        )


def _print_summary(result: TrackblazerTemplateBenchmarkResult, top: int) -> None:
    if result.error:
        print(f"Benchmark failed: {result.error}")
        return

    print(f"Screenshot: {result.screenshot_size[0]}x{result.screenshot_size[1]}")
    print(f"Iterations per template: {result.iterations}")
    print(f"Templates tested: {result.templates_tested}")
    print(f"Resolver OK for all templates: {result.all_resolvers_ok}")
    if result.avg_region_ms is not None:
        print(f"Average region search time: {result.avg_region_ms:.3f} ms")
    print(f"Average full-screen search time: {result.avg_full_ms:.3f} ms")
    if result.avg_speedup is not None:
        print(f"Average speedup: {result.avg_speedup:.2f}x")
    if result.report_path:
        print(f"Report saved to: {result.report_path}")

    ranked = sorted(
        (row for row in result.results if row.speedup is not None),
        key=lambda row: row.speedup,
        reverse=True,
    )
    if not ranked:
        return

    print("")
    print(f"Top {min(top, len(ranked))} speedups:")
    for row in ranked[:top]:
        print(
            f"- {row.template_path}: "
            f"region={row.region_avg_ms:.3f} ms, "
            f"full={row.full_avg_ms:.3f} ms, "
            f"speedup={row.speedup:.2f}x, "
            f"resolver_ok={row.resolver_ok}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark Trackblazer template matching using one live emulator screenshot.",
    )
    parser.add_argument("--iterations", type=int, default=20, help="Benchmark iterations per template.")
    parser.add_argument("--confidence", type=float, default=0.8, help="Confidence threshold for counting matches.")
    parser.add_argument("--top", type=int, default=10, help="Number of top speedups to print.")
    parser.add_argument(
        "--template",
        action="append",
        dest="templates",
        help="Optional template path filter. Repeat to benchmark multiple templates.",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Optional output path for the JSON report.",
    )
    args = parser.parse_args()

    if args.iterations <= 0:
        print("--iterations must be > 0")
        return 1

    report_path = Path(args.report) if args.report else None
    result = run_trackblazer_template_benchmark(
        iterations=args.iterations,
        confidence=args.confidence,
        template_paths=args.templates,
        report_path=report_path,
    )
    _print_summary(result, top=args.top)
    return 1 if result.error else 0


if __name__ == "__main__":
    raise SystemExit(main())
