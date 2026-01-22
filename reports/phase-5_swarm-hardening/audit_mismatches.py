#!/usr/bin/env python3
"""
Phase 5 Audit: Identify frontmatter vs body mismatches in all taskcards.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


def extract_frontmatter(content: str) -> Dict | None:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def extract_body_allowed_paths(content: str) -> List[str]:
    """Extract allowed paths from the body ## Allowed paths section."""
    # Find the ## Allowed paths section
    match = re.search(r"^## Allowed paths\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    paths = []

    # Extract bullet points
    for line in section.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            # Remove the bullet and any markdown formatting
            path = line[1:].strip()
            # Remove parenthetical notes like "(implementation evidence only)"
            path = re.sub(r'\s*\(.*?\)\s*', '', path)
            path = path.strip()
            if path:
                paths.append(path)

    return paths


def audit_taskcard(filepath: Path) -> Dict:
    """Audit a single taskcard for mismatches."""
    content = filepath.read_text(encoding='utf-8')

    frontmatter = extract_frontmatter(content)
    if not frontmatter:
        return {
            'file': filepath.name,
            'error': 'No valid frontmatter',
            'frontmatter_paths': [],
            'body_paths': [],
            'mismatch': True
        }

    tc_id = frontmatter.get('id', 'UNKNOWN')
    frontmatter_paths = frontmatter.get('allowed_paths', [])
    body_paths = extract_body_allowed_paths(content)

    # Normalize for comparison
    fm_set = set(p.strip() for p in frontmatter_paths)
    body_set = set(p.strip() for p in body_paths)

    mismatch = fm_set != body_set

    return {
        'file': filepath.name,
        'tc_id': tc_id,
        'frontmatter_paths': sorted(fm_set),
        'body_paths': sorted(body_set),
        'mismatch': mismatch,
        'in_frontmatter_only': sorted(fm_set - body_set),
        'in_body_only': sorted(body_set - fm_set)
    }


def find_overlaps(taskcards_dir: Path) -> Dict[str, List[str]]:
    """Find overlapping paths across all taskcards."""
    from collections import defaultdict

    path_usage = defaultdict(list)

    for md_file in sorted(taskcards_dir.glob("TC-*.md")):
        content = md_file.read_text(encoding='utf-8')
        frontmatter = extract_frontmatter(content)
        if not frontmatter:
            continue

        tc_id = frontmatter.get('id', 'UNKNOWN')
        allowed_paths = frontmatter.get('allowed_paths', [])

        for path in allowed_paths:
            normalized = path.strip()
            path_usage[normalized].append(tc_id)

    # Filter to only overlaps
    overlaps = {path: tc_list for path, tc_list in path_usage.items() if len(tc_list) > 1}

    return overlaps


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    taskcards_dir = repo_root / "plans" / "taskcards"

    print("=" * 80)
    print("PHASE 5 AUDIT: Frontmatter vs Body Allowed Paths Mismatches")
    print("=" * 80)
    print()

    # Find all taskcards
    taskcards = sorted(taskcards_dir.glob("TC-*.md"))
    if not taskcards:
        print("ERROR: No taskcards found")
        return 1

    print(f"Found {len(taskcards)} taskcard(s)\n")

    # Audit each taskcard
    results = []
    mismatch_count = 0

    for tc_path in taskcards:
        result = audit_taskcard(tc_path)
        results.append(result)
        if result.get('mismatch'):
            mismatch_count += 1

    # Print detailed results
    print("MISMATCH DETAILS")
    print("=" * 80)
    print()

    for result in results:
        if result.get('mismatch'):
            print(f"[MISMATCH] {result['tc_id']} ({result['file']})")

            if result.get('error'):
                print(f"  ERROR: {result['error']}")
            else:
                if result['in_frontmatter_only']:
                    print(f"  In frontmatter but NOT in body:")
                    for path in result['in_frontmatter_only']:
                        print(f"    + {path}")

                if result['in_body_only']:
                    print(f"  In body but NOT in frontmatter:")
                    for path in result['in_body_only']:
                        print(f"    - {path}")

            print()

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total taskcards: {len(taskcards)}")
    print(f"Mismatches: {mismatch_count}")
    print(f"Matching: {len(taskcards) - mismatch_count}")
    print()

    # Check for overlaps
    print("=" * 80)
    print("OVERLAP ANALYSIS")
    print("=" * 80)
    print()

    overlaps = find_overlaps(taskcards_dir)

    if not overlaps:
        print("✓ No overlapping paths found")
    else:
        print(f"Found {len(overlaps)} overlapping path(s):\n")
        for path, tc_list in sorted(overlaps.items()):
            print(f"  {path}")
            print(f"    Used by: {', '.join(sorted(tc_list))}")
            print()

    print("=" * 80)

    if mismatch_count > 0:
        print(f"\nFAILURE: {mismatch_count} taskcard(s) have mismatches")
        return 1
    else:
        print("\nSUCCESS: All taskcards have matching frontmatter and body")
        return 0


if __name__ == "__main__":
    sys.exit(main())
