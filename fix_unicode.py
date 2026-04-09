import os
import sys

# All corrupted byte patterns mapped to their correct UTF-8 bytes.
# These arose from double-encoding: UTF-8 bytes read as CP1252, then re-encoded as UTF-8.
BYTE_REPLACEMENTS = [
    # Order matters: longer patterns first to avoid partial matches

    # WARNING SIGN U+26A0 + variation selector U+FE0F (11 bytes -> 6 bytes)
    (b'\xc3\xa2\xc5\xa1\xc2\xa0\xc3\xaf\xc2\xb8\xc2\x8f', b'\xe2\x9a\xa0\xef\xb8\x8f'),

    # CHECK MARK U+2713 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xc5\x93\xe2\x80\x9c', b'\xe2\x9c\x93'),

    # BALLOT X U+2717 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xc5\x93\xe2\x80\x94', b'\xe2\x9c\x97'),

    # WHITE HEAVY CHECK MARK U+2705 (checkmark emoji, 6 bytes -> 3 bytes)
    (b'\xc3\xa2\xc5\x93\xe2\x80\xa6', b'\xe2\x9c\x85'),

    # CROSS MARK U+274C (5 bytes -> 3 bytes)
    (b'\xc3\xa2\xc2\x9d\xc5\x92', b'\xe2\x9d\x8c'),

    # EM DASH U+2014 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9d', b'\xe2\x80\x94'),

    # EN DASH U+2013 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9c', b'\xe2\x80\x93'),

    # BULLET U+2022 (5 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x82\xac\xc2\xa2', b'\xe2\x80\xa2'),

    # RIGHT ARROW U+2192 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x80\xa0\xe2\x80\x99', b'\xe2\x86\x92'),

    # BOX DRAWINGS LIGHT HORIZONTAL U+2500 (6 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x80\x9d\xe2\x82\xac', b'\xe2\x94\x80'),

    # MUSICAL NOTE U+266A (5 bytes -> 3 bytes)
    (b'\xc3\xa2\xe2\x84\xa2\xc2\xaa', b'\xe2\x99\xaa'),

    # SUN/CIRCLE symbol used in event names - U+2DAF or similar game chars
    # Actual bytes in reference: e2 9d af which is U+276F? Let me check...
    # From the reference: the pattern (a-combining-right-half-ring) might be decorative
    # The reference file has: \xe2\x9d\xaf which is U+276F = HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT
    (b'\xc3\xa2\xc2\x9d\xc2\xaf', b'\xe2\x9d\xaf'),
]


def fix_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    original = data
    for corrupted, correct in BYTE_REPLACEMENTS:
        data = data.replace(corrupted, correct)

    if data != original:
        with open(filepath, 'wb') as f:
            f.write(data)
        return True
    return False


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    scan_dirs = ['core', 'utils', 'gui']
    fixed = 0
    scanned = 0

    for scan_dir in scan_dirs:
        dirpath = os.path.join(base, scan_dir)
        if not os.path.exists(dirpath):
            continue
        for root, dirs, files in os.walk(dirpath):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'ref', '.git')]
            for fn in files:
                if fn.endswith('.py'):
                    fpath = os.path.join(root, fn)
                    scanned += 1
                    if fix_file(fpath):
                        print(f"  FIXED: {os.path.relpath(fpath, base)}")
                        fixed += 1

    # Also scan root py files
    for fn in os.listdir(base):
        if fn.endswith('.py') and fn != 'fix_unicode.py':
            fpath = os.path.join(base, fn)
            scanned += 1
            if fix_file(fpath):
                print(f"  FIXED: {os.path.relpath(fpath, base)}")
                fixed += 1

    print(f"\nScanned {scanned} files, fixed {fixed} files.")


if __name__ == '__main__':
    main()
