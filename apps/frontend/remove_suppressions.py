#!/usr/bin/env python3
"""Remove unused biome-ignore suppression comments from TypeScript/TSX files."""
import subprocess
import re
import os

base_dir = r"C:\Users\thomas.leberre\Repositories\Auto-Claude_EBP\apps\frontend"

def get_suppression_locations():
    """Run biome check and get list of (file, line) pairs with unused suppressions."""
    result = subprocess.run(
        ["npx", "biome", "check", "src/", "--max-diagnostics=10000"],
        capture_output=True, cwd=base_dir, shell=True
    )
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
    output = stdout + stderr

    locations = {}
    for line in output.splitlines():
        if "suppressions/unused" in line:
            # Format: src\path\to\file.ts:123:4 suppressions/unused
            match = re.match(r'^(src[^\s:]+):(\d+):\d+\s+suppressions', line)
            if match:
                filepath = match.group(1).replace("\\", "/")
                lineno = int(match.group(2))
                if filepath not in locations:
                    locations[filepath] = []
                locations[filepath].append(lineno)

    return locations

def remove_suppression_line(filepath, line_numbers):
    """Remove biome-ignore comment lines at the given 1-indexed line numbers."""
    full_path = os.path.join(base_dir, filepath.replace("/", os.sep))

    with open(full_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Convert to 0-indexed and sort descending so we can remove without shifting
    line_indices = sorted(set(n - 1 for n in line_numbers), reverse=True)

    removed = 0
    for idx in line_indices:
        if idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            # Check if this line is a biome-ignore comment
            if ('biome-ignore' in stripped):
                lines.pop(idx)
                removed += 1
            else:
                print(f"  WARNING: Line {idx+1} in {filepath} doesn't look like biome-ignore: {repr(stripped[:80])}")

    if removed > 0:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"  Removed {removed} lines from {filepath}")

    return removed

# Get all locations
print("Getting suppression locations...")
locations = get_suppression_locations()
print(f"Found {len(locations)} files with unused suppressions")

total_removed = 0
for filepath, line_numbers in sorted(locations.items()):
    print(f"\nProcessing {filepath} (lines: {sorted(line_numbers)})...")
    removed = remove_suppression_line(filepath, line_numbers)
    total_removed += removed

print(f"\nTotal lines removed: {total_removed}")
