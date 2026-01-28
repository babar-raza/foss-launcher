#!/usr/bin/env python3
"""
Markdown Internal Link Checker

Checks all markdown files for broken internal links (file references).
Ignores external URLs.

Exit codes:
  0 - All internal links valid
  1 - Broken links found
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple


def extract_markdown_links(content: str, source_file: Path) -> List[Tuple[str, int]]:
    """
    Extract markdown links from content.
    Returns list of (link_target, line_number) tuples.
    Skips links inside code fences.
    """
    links = []
    lines = content.split("\n")
    in_code_fence = False

    for line_num, line in enumerate(lines, start=1):
        # Track code fence state (``` or ~~~)
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            continue

        # Skip lines inside code fences
        if in_code_fence:
            continue

        # Remove inline code (text between backticks) to avoid false positives
        # Replace backtick-enclosed text with spaces to preserve positions
        cleaned_line = re.sub(r'`[^`]*`', lambda m: ' ' * len(m.group(0)), line)

        # Match markdown links: [text](url) and [text](url#anchor)
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", cleaned_line):
            link = match.group(2)
            # Skip external URLs (http://, https://, mailto:, etc.)
            if re.match(r"^[a-z]+://", link) or link.startswith("mailto:"):
                continue
            # Skip anchors without file references (starting with #)
            if link.startswith("#"):
                continue
            links.append((link, line_num))

    return links


def resolve_link_target(link: str, source_file: Path, repo_root: Path) -> Path:
    """
    Resolve a link target to an absolute path.
    Handles both relative and absolute (from repo root) links.
    """
    # Remove anchor fragments
    link_path = link.split("#")[0]

    # If link starts with /, it's relative to repo root
    if link_path.startswith("/"):
        return repo_root / link_path.lstrip("/")

    # Otherwise, it's relative to the source file's directory
    return (source_file.parent / link_path).resolve()


def check_link_exists(target_path: Path) -> bool:
    """Check if a link target exists (file or directory)."""
    return target_path.exists()


def check_markdown_file(md_file: Path, repo_root: Path) -> List[str]:
    """
    Check all internal links in a markdown file.
    Returns list of error messages (empty if all valid).
    """
    errors = []

    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read file: {e}"]

    links = extract_markdown_links(content, md_file)

    for link, line_num in links:
        target = resolve_link_target(link, md_file, repo_root)
        if not check_link_exists(target):
            relative_target = target.relative_to(repo_root) if target.is_relative_to(repo_root) else target
            errors.append(
                f"Line {line_num}: Broken link '{link}' -> {relative_target}"
            )

    return errors


def find_markdown_files(repo_root: Path) -> List[Path]:
    """Find all markdown files in the repository."""
    md_files = []

    # Key directories to check
    check_dirs = [
        repo_root / "specs",
        repo_root / "plans",
        repo_root / "docs",
        repo_root / "reports",
    ]

    # Also check root-level markdown files
    for md_file in repo_root.glob("*.md"):
        if md_file.is_file():
            md_files.append(md_file)

    # Check subdirectories
    for check_dir in check_dirs:
        if check_dir.exists():
            for md_file in check_dir.rglob("*.md"):
                if md_file.is_file():
                    md_files.append(md_file)

    return sorted(set(md_files))


def main():
    """Main validation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Checking markdown links in: {repo_root}")
    print()

    # Find all markdown files
    md_files = find_markdown_files(repo_root)
    if not md_files:
        print("WARNING: No markdown files found")
        return 0

    print(f"Found {len(md_files)} markdown file(s) to check")
    print()

    # Check each file
    all_valid = True
    total_broken = 0

    for md_file in md_files:
        relative_path = md_file.relative_to(repo_root)
        errors = check_markdown_file(md_file, repo_root)

        if not errors:
            print(f"[OK] {relative_path}")
        else:
            all_valid = False
            total_broken += len(errors)
            print(f"[FAIL] {relative_path}")
            for error in errors:
                print(f"  {error}")
            print()

    # Summary
    print()
    print("=" * 70)
    if all_valid:
        print(f"SUCCESS: All internal links valid ({len(md_files)} files checked)")
        return 0
    else:
        print(f"FAILURE: {total_broken} broken link(s) found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
