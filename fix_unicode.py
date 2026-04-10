import os
from pathlib import Path


def cp(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


# Mojibake sequences found in the refactored tree.
# Order matters: longer patterns first to avoid partial matches.
TEXT_REPLACEMENTS = [
    (cp(0x00C3, 0x00A2, 0x00C2, 0x009D, 0x00C5, 0x2019), "❌"),
    (cp(0x00F0, 0x0178, 0x201D, 0x008D), "🔍"),
    (cp(0x00F0, 0x0178, 0x201C, 0x2039), "📋"),
    (cp(0x00F0, 0x0178, 0x017D, 0x2030), "🎉"),
    (cp(0x00F0, 0x0178, 0x2018, 0x0081), "👁"),
    (cp(0x00F0, 0x0178, 0x008F, 0x00A0), "🏠"),
    (cp(0x00F0, 0x0178, 0x201C, 0x0160), "📊"),
    (cp(0x00F0, 0x0178, 0x201C, 0x2026), "📅"),
    (cp(0x00F0, 0x0178, 0x201C, 0x02C6), "📈"),
    (cp(0x00F0, 0x0178, 0x201D, 0x201D), "🔔"),
    (cp(0x00E2, 0x0153, 0x2026), "✅"),
    (cp(0x00E2, 0x20AC, 0x00A2), "•"),
    (cp(0x00C3, 0x00A2, 0x00C5, 0x00A1, 0x00C2, 0x00A0, 0x00C3, 0x00AF, 0x00C2, 0x00B8, 0x00C2, 0x008F), "⚠️"),
    (cp(0x00C3, 0x00A2, 0x00C5, 0x201C, 0x201C), "✓"),
    (cp(0x00C3, 0x00A2, 0x00C5, 0x201C, 0x2014), "✗"),
    (cp(0x00C3, 0x00A2, 0x00C5, 0x201C, 0x2026), "✅"),
    (cp(0x00C3, 0x00A2, 0x00E2, 0x201A, 0x00AC, 0x201D), "—"),
    (cp(0x00C3, 0x00A2, 0x00E2, 0x201A, 0x00AC, 0x201C), "–"),
    (cp(0x00C3, 0x00A2, 0x00E2, 0x201A, 0x00AC, 0x00A2), "•"),
    (cp(0x00C3, 0x00A2, 0x2020, 0x2019), "→"),
    (cp(0x00C3, 0x00A2, 0x201D, 0x20AC), "─"),
    (cp(0x00C3, 0x00A2, 0x2122, 0x00AA), "♪"),
    (cp(0x00C3, 0x00A2, 0x00C2, 0x009D, 0x00C2, 0x00AF), "❯"),
]


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "core").is_dir() and (candidate / "gui").is_dir():
            return candidate
    return start


def fix_file(filepath: str) -> bool:
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    original = text
    for corrupted, correct in TEXT_REPLACEMENTS:
        text = text.replace(corrupted, correct)

    if text != original:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return True
    return False


def main() -> None:
    base = find_repo_root(Path(__file__).resolve().parent)
    scan_dirs = ["core", "utils", "gui"]
    fixed = 0
    scanned = 0

    for scan_dir in scan_dirs:
        dirpath = base / scan_dir
        if not dirpath.exists():
            continue
        for root, dirs, files in os.walk(dirpath):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "ref", ".git")]
            for fn in files:
                if fn.endswith(".py"):
                    fpath = os.path.join(root, fn)
                    scanned += 1
                    if fix_file(fpath):
                        print(f"  FIXED: {os.path.relpath(fpath, base)}")
                        fixed += 1

    for fn in os.listdir(base):
        if fn.endswith(".py") and fn != "fix_unicode.py":
            fpath = base / fn
            scanned += 1
            if fix_file(str(fpath)):
                print(f"  FIXED: {os.path.relpath(fpath, base)}")
                fixed += 1

    print(f"\nScanned {scanned} files, fixed {fixed} files.")


if __name__ == "__main__":
    main()
