"""Test the _fix_collapsed_frontmatter logic with multi-line joins."""
import re
import sys
sys.path.insert(0, "src")

from launch.workers.w5_section_writer.worker import _fix_collapsed_frontmatter

# Simulate the actual broken frontmatter from feature.md
broken = """---
title: "Aspose.3D FOSS for Python - Aspose. 3d - Feature"
description: "Comprehensive guide and resources for Aspose. 3d. Learn how to use 3d features in your applications.

" summary: "Learn how to use Aspose. 3d for feature with examples and documentation. " type: docs layout: docs permalink: /3d/feature/ machine_readable:   product_name: "Aspose. 3D FOSS for Python"   product_family: "3d"   page_role: "workflow_page"   claim_ids: []   keywords: [3d].
description: "Aspose.3D FOSS for Python feature documentation"
url_path: /feature/
---
## Overview

Body content here.
"""

print("=== INPUT ===")
for i, line in enumerate(broken.split('\n'), 1):
    print(f"{i:3d}| {line}")

result = _fix_collapsed_frontmatter(broken)

print("\n=== OUTPUT ===")
for i, line in enumerate(result.split('\n'), 1):
    print(f"{i:3d}| {line}")

# Check if collapsed YAML remains
fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
markers = list(fm_pattern.finditer(result))
if len(markers) >= 2:
    fm_text = result[markers[0].end():markers[1].start()]
    for line_num, line in enumerate(fm_text.split('\n'), start=2):
        masked = re.sub(r'"[^"]*"', lambda m: '"' + '#' * (len(m.group()) - 2) + '"', line)
        masked = re.sub(r"'[^']*'", lambda m: "'" + '#' * (len(m.group()) - 2) + "'", masked)
        key_matches = re.findall(r'(?:^|\s)(\w+):\s', masked)
        if len(key_matches) >= 2:
            print(f"\nSTILL COLLAPSED at line {line_num}: {len(key_matches)} keys: {line[:80]}")
    else:
        print("\nAll frontmatter lines have ≤1 key. FIX SUCCESSFUL!")
