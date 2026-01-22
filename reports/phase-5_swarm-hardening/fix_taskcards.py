#!/usr/bin/env python3
"""
Phase 5: Fix all taskcards to have matching frontmatter and body allowed_paths.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List
import yaml


def extract_frontmatter(content: str) -> tuple[Dict | None, str]:
    """Extract YAML frontmatter and remaining content."""
    if not content.startswith("---\n"):
        return None, content

    match = re.match(r"^(---\n.*?\n---\n)(.*)", content, re.DOTALL)
    if not match:
        return None, content

    frontmatter_block = match.group(1)
    body = match.group(2)

    try:
        # Extract just the YAML part
        yaml_content = frontmatter_block.strip("---\n").strip()
        frontmatter = yaml.safe_load(yaml_content)
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


def generate_allowed_paths_section(allowed_paths: List[str]) -> str:
    """Generate the ## Allowed paths section from frontmatter list."""
    lines = ["## Allowed paths"]
    for path in allowed_paths:
        lines.append(f"- {path}")
    lines.append("")  # Blank line after section
    return "\n".join(lines)


def fix_taskcard(filepath: Path, dry_run: bool = False) -> bool:
    """Fix a single taskcard's ## Allowed paths section."""
    content = filepath.read_text(encoding='utf-8')

    # Extract frontmatter and body
    frontmatter, body = extract_frontmatter(content)
    if not frontmatter:
        print(f"  [SKIP] No valid frontmatter in {filepath.name}")
        return False

    allowed_paths = frontmatter.get('allowed_paths', [])
    if not allowed_paths:
        print(f"  [SKIP] No allowed_paths in frontmatter for {filepath.name}")
        return False

    # Find the current ## Allowed paths section
    match = re.search(r"^## Allowed paths\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if not match:
        print(f"  [WARN] No ## Allowed paths section found in {filepath.name}")
        return False

    old_section = match.group(0)

    # Generate new section
    new_section = generate_allowed_paths_section(allowed_paths)

    # Replace the section
    new_body = body.replace(old_section, new_section, 1)

    # Reconstruct full content
    # Extract frontmatter block from original content
    fm_match = re.match(r"^(---\n.*?\n---\n)", content, re.DOTALL)
    if not fm_match:
        print(f"  [ERROR] Cannot extract frontmatter block from {filepath.name}")
        return False

    frontmatter_block = fm_match.group(1)
    new_content = frontmatter_block + new_body

    if dry_run:
        print(f"  [DRY-RUN] Would fix {filepath.name}")
        return True
    else:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"  [FIXED] {filepath.name}")
        return True


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    taskcards_dir = repo_root / "plans" / "taskcards"

    print("=" * 80)
    print("PHASE 5: Fix Taskcard Allowed Paths Sections")
    print("=" * 80)
    print()

    # Find all taskcards (exclude meta files)
    taskcards = []
    for md_file in sorted(taskcards_dir.glob("TC-*.md")):
        taskcards.append(md_file)

    if not taskcards:
        print("ERROR: No taskcards found")
        return 1

    print(f"Found {len(taskcards)} taskcard(s) to process\n")

    # Process each taskcard
    fixed_count = 0
    for tc_path in taskcards:
        if fix_taskcard(tc_path, dry_run=False):
            fixed_count += 1

    print()
    print("=" * 80)
    print(f"COMPLETED: Fixed {fixed_count}/{len(taskcards)} taskcard(s)")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
