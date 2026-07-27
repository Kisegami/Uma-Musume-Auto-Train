"""Check the Grand Live lessons button template against saved screenshots.

Run from anywhere in the repository:

    python tests_grandlive/lessons_btn_template_check.py

The script tries both lessons button variants and reports the best match in
every screenshot. Use ``--require-all`` when every screenshot is expected to
contain either variant.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATES = (
    PROJECT_ROOT / "assets" / "grandlive" / "lessons_btn.png",
    PROJECT_ROOT / "assets" / "grandlive" / "lessons_btn_2.png",
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def load_image(path: Path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return image


def find_best_match(screenshot, template) -> tuple[float, tuple[int, int, int, int]]:
    screenshot_height, screenshot_width = screenshot.shape[:2]
    template_height, template_width = template.shape[:2]
    if template_height > screenshot_height or template_width > screenshot_width:
        raise ValueError(
            "Template is larger than screenshot "
            f"({template_width}x{template_height} > "
            f"{screenshot_width}x{screenshot_height})"
        )

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, location = cv2.minMaxLoc(result)
    x, y = location
    return float(confidence), (x, y, template_width, template_height)


def screenshot_paths(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Template-match both Grand Live lessons button variants against "
            "every screenshot in tests_grandlive."
        )
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Minimum confidence considered a match (default: 0.80).",
    )
    parser.add_argument(
        "--template",
        type=Path,
        action="append",
        dest="templates",
        help=(
            "Template image path. May be supplied multiple times. By default, "
            "lessons_btn.png and lessons_btn_2.png are both tested."
        ),
    )
    parser.add_argument(
        "--screenshot-dir",
        type=Path,
        default=DEFAULT_SCREENSHOT_DIR,
        help="Directory containing screenshots.",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Exit with failure if the template is missing from any screenshot.",
    )
    args = parser.parse_args()

    if not 0.0 <= args.threshold <= 1.0:
        parser.error("--threshold must be between 0 and 1")
    if not args.screenshot_dir.is_dir():
        parser.error(f"screenshot directory does not exist: {args.screenshot_dir}")

    template_paths = args.templates or list(DEFAULT_TEMPLATES)
    templates = [(path, load_image(path)) for path in template_paths]
    screenshots = screenshot_paths(args.screenshot_dir)
    if not screenshots:
        print(f"No screenshots found in {args.screenshot_dir}")
        return 1

    matched_count = 0
    print("Templates:")
    for template_path, _ in templates:
        print(f"  - {template_path}")
    print(f"Threshold: {args.threshold:.3f}")
    print()

    for path in screenshots:
        screenshot = load_image(path)
        candidates = []
        for template_path, template in templates:
            confidence, bbox = find_best_match(screenshot, template)
            candidates.append((confidence, bbox, template_path))

        confidence, bbox, template_path = max(candidates, key=lambda item: item[0])
        matched = confidence >= args.threshold
        matched_count += int(matched)
        status = "MATCH" if matched else "NO MATCH"
        x, y, width, height = bbox
        print(
            f"{status:<8} {path.name}  confidence={confidence:.4f}  "
            f"template={template_path.name}  bbox=({x}, {y}, {width}, {height})"
        )

    print()
    print(
        f"Matched {matched_count}/{len(screenshots)} screenshot(s) "
        f"at threshold {args.threshold:.3f}."
    )

    if args.require_all and matched_count != len(screenshots):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
