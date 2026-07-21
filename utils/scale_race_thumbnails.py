"""Generate screen-scale race templates from the source race thumbnails."""

import argparse
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets" / "races" / "races_thumb"
OUTPUT_DIR = ROOT / "assets" / "races" / "race_thumb_scaled"
SCALE = 0.52
CROP_INSET = 8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate existing templates")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    templates = []

    for source in sorted(SOURCE_DIR.glob("*.png")):
        image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise RuntimeError(f"Could not read {source}")
        if image.shape[0] <= CROP_INSET * 2 or image.shape[1] <= CROP_INSET * 2:
            raise ValueError(f"Image is too small to crop: {source}")

        cropped = image[CROP_INSET:-CROP_INSET, CROP_INSET:-CROP_INSET]
        width = round(cropped.shape[1] * SCALE)
        height = round(cropped.shape[0] * SCALE)
        output = OUTPUT_DIR / source.name
        if args.force or not output.exists():
            scaled = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_AREA)
            if not cv2.imwrite(str(output), scaled):
                raise RuntimeError(f"Could not write {output}")

        templates.append(
            {
                "source": source.relative_to(ROOT).as_posix(),
                "scaled": output.relative_to(ROOT).as_posix(),
                "width": width,
                "height": height,
            }
        )

    manifest = {
        "source_dir": SOURCE_DIR.relative_to(ROOT).as_posix(),
        "output_dir": OUTPUT_DIR.relative_to(ROOT).as_posix(),
        "scale": SCALE,
        "crop_inset": CROP_INSET,
        "template_count": len(templates),
        "templates": templates,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(templates)} scaled race thumbnails in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
