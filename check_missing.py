import os

# These emojis were stripped entirely during refactor (not just corrupted)
# We need to restore them in the current files

# Direct hit emoji U+1F3AF
direct_hit = b'\xf0\x9f\x8e\xaf'
# Check if corrupted version exists
corrupted_direct_hit = b'\xc3\xb0\xc5\xb8\xc5\xbd\xc2\xaf'

found = False
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'ref', '.git', '_internal')]
    for fn in files:
        if fn.endswith('.py'):
            fpath = os.path.join(root, fn)
            with open(fpath, 'rb') as f:
                data = f.read()
            if corrupted_direct_hit in data:
                print(f'Found corrupted direct hit in {fpath}')
                found = True

if not found:
    print('No corrupted direct hit emoji found - it was stripped during refactor')

# Now look at what the current event_handling files have where emojis should be
for fpath in ['core/Unity/event_handling.py', 'core/Ura/event_handling.py']:
    print(f'\n=== {fpath} ===')
    with open(fpath, 'rb') as f:
        data = f.read()
    
    needles = [
        b'Custom template match',
        b'Hardcoded event: Tutorial',
        b'Hardcoded event: A Team',
    ]
    for needle in needles:
        idx = data.find(needle)
        if idx >= 0:
            ctx = data[max(0, idx-30):idx+len(needle)+10]
            print(f'  {repr(ctx)}')

    # Check indicator appends
    idx = 0
    while True:
        i = data.find(b'indicators.append(', idx)
        if i < 0:
            break
        ctx = data[i:i+50]
        print(f'  indicator: {repr(ctx)}')
        idx = i + 1
