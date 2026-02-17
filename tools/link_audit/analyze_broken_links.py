#!/usr/bin/env python3
"""Analyze broken links and categorize them for gap reporting."""
import json
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(r"c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher")
results_file = REPO_ROOT / "temp_link_check_results.json"

with open(results_file) as f:
    data = json.load(f)

broken = [r for r in data['results'] if r['status'] == 'BROKEN']

# Categorize
categories = {
    'directory_links': [],
    'broken_anchors': [],
    'absolute_paths': [],
    'missing_relative_files': [],
    'line_number_anchors': []
}

for link in broken:
    reason = link['reason']
    target = link['link_target']

    if target.startswith('/'):
        categories['absolute_paths'].append(link)
    elif 'Target is not a file' in reason and target.endswith('/'):
        categories['directory_links'].append(link)
    elif 'Anchor' in reason and '#L' in target:
        categories['line_number_anchors'].append(link)
    elif 'Anchor' in reason:
        categories['broken_anchors'].append(link)
    elif 'File not found' in reason:
        categories['missing_relative_files'].append(link)

# Print summary
print("=" * 80)
print("BROKEN LINK ANALYSIS")
print("=" * 80)
print(f"\nTotal broken links: {len(broken)}")
print("\nBreakdown by category:")
for cat, links in categories.items():
    print(f"  {cat}: {len(links)}")

# Print details for each category
print("\n" + "=" * 80)
print("CATEGORY: Directory Links (should link to files, not directories)")
print("=" * 80)
for link in categories['directory_links'][:10]:
    print(f"{link['source_file']}:{link['line']}")
    print(f"  Link: [{link['link_text']}]({link['link_target']})")
    print(f"  Issue: Links to directory instead of file")
    print()

print("\n" + "=" * 80)
print("CATEGORY: Broken Anchors (heading doesn't exist)")
print("=" * 80)
for link in categories['broken_anchors'][:10]:
    print(f"{link['source_file']}:{link['line']}")
    print(f"  Link: [{link['link_text']}]({link['link_target']})")
    print(f"  Issue: {link['reason']}")
    print()

print("\n" + "=" * 80)
print("CATEGORY: Absolute Path Links (should be relative)")
print("=" * 80)
# Group by source file
abs_by_file = defaultdict(list)
for link in categories['absolute_paths']:
    abs_by_file[link['source_file']].append(link)

for source_file, links in sorted(abs_by_file.items())[:5]:
    print(f"\n{source_file}: {len(links)} absolute path links")
    for link in links[:3]:
        print(f"  Line {link['line']}: {link['link_target']}")

print("\n" + "=" * 80)
print("CATEGORY: Line Number Anchors (GitHub-style, not standard markdown)")
print("=" * 80)
for link in categories['line_number_anchors'][:10]:
    print(f"{link['source_file']}:{link['line']}")
    print(f"  Link: {link['link_target']}")
    print(f"  Issue: Line number anchors (#L123) don't work in markdown")
    print()

# Save categorized results
output = {
    'summary': {cat: len(links) for cat, links in categories.items()},
    'categories': categories
}

with open(REPO_ROOT / "temp_broken_links_categorized.json", 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nCategorized results saved to: temp_broken_links_categorized.json")
