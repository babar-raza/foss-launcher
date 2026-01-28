#!/usr/bin/env python3
"""
Comprehensive link checker for markdown files.
Checks all internal links (relative paths and anchors).
"""
import re
import os
from pathlib import Path
from typing import List, Tuple, Set
import json

REPO_ROOT = Path(r"c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher")

def find_all_markdown_files() -> List[Path]:
    """Find all markdown files excluding dependencies."""
    md_files = []
    for md_file in REPO_ROOT.rglob("*.md"):
        # Skip dependencies
        if any(skip in str(md_file) for skip in ['.venv', '.git', 'node_modules', '.pytest_cache']):
            continue
        md_files.append(md_file)
    return md_files

def extract_links(file_path: Path) -> List[Tuple[int, str, str]]:
    """Extract all markdown links from a file. Returns (line_num, link_text, link_target)."""
    links = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # Match [text](target) patterns
            matches = re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', line)
            for match in matches:
                link_text = match.group(1)
                link_target = match.group(2)
                links.append((line_num, link_text, link_target))
    return links

def is_internal_link(target: str) -> bool:
    """Check if link is internal (not http/https/mailto)."""
    return not target.startswith(('http://', 'https://', 'mailto:', '#'))

def resolve_relative_path(source_file: Path, target: str) -> Path:
    """Resolve a relative link target from source file."""
    # Remove anchor if present
    if '#' in target:
        target = target.split('#')[0]

    if not target:  # Pure anchor link
        return source_file

    # Resolve relative to source file's directory
    source_dir = source_file.parent
    resolved = (source_dir / target).resolve()
    return resolved

def extract_anchors(file_path: Path) -> Set[str]:
    """Extract all heading anchors from a markdown file."""
    anchors = set()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Match markdown headings
            match = re.match(r'^#+\s+(.+)$', line.strip())
            if match:
                heading = match.group(1)
                # Convert to anchor format (GitHub-style)
                anchor = heading.lower()
                anchor = re.sub(r'[^\w\s-]', '', anchor)
                anchor = re.sub(r'[-\s]+', '-', anchor)
                anchors.add(anchor)
    return anchors

def check_link(source_file: Path, line_num: int, link_text: str, link_target: str) -> dict:
    """Check if a link is valid."""
    result = {
        'source_file': str(source_file.relative_to(REPO_ROOT)),
        'line': line_num,
        'link_text': link_text,
        'link_target': link_target,
        'status': 'OK',
        'reason': ''
    }

    if not is_internal_link(link_target):
        result['status'] = 'EXTERNAL'
        return result

    # Check if it's a pure anchor link
    if link_target.startswith('#'):
        anchor = link_target[1:]
        anchors = extract_anchors(source_file)
        if anchor not in anchors:
            result['status'] = 'BROKEN'
            result['reason'] = f'Anchor #{anchor} not found in {source_file.name}'
        return result

    # Extract anchor if present
    anchor = None
    if '#' in link_target:
        path_part, anchor = link_target.split('#', 1)
        target_path = path_part
    else:
        target_path = link_target

    # Resolve the target file
    if target_path:  # Non-empty path
        resolved = resolve_relative_path(source_file, target_path)

        # Check if file exists
        if not resolved.exists():
            result['status'] = 'BROKEN'
            result['reason'] = f'File not found: {resolved}'
            return result

        # Check if it's a file (not directory)
        if not resolved.is_file():
            result['status'] = 'BROKEN'
            result['reason'] = f'Target is not a file: {resolved}'
            return result

        # If anchor specified, check if anchor exists
        if anchor:
            anchors = extract_anchors(resolved)
            if anchor not in anchors:
                result['status'] = 'BROKEN'
                result['reason'] = f'Anchor #{anchor} not found in {resolved.relative_to(REPO_ROOT)}'
                return result

    return result

def main():
    print("Starting comprehensive link check...")
    print(f"Repository root: {REPO_ROOT}")

    md_files = find_all_markdown_files()
    print(f"Found {len(md_files)} markdown files")

    all_results = []
    broken_count = 0
    total_internal_links = 0

    for md_file in md_files:
        links = extract_links(md_file)
        for line_num, link_text, link_target in links:
            result = check_link(md_file, line_num, link_text, link_target)
            if result['status'] in ['OK', 'BROKEN']:
                total_internal_links += 1
                all_results.append(result)
                if result['status'] == 'BROKEN':
                    broken_count += 1
                    print(f"BROKEN: {result['source_file']}:{line_num} -> {link_target}")
                    print(f"  Reason: {result['reason']}")

    # Save results
    output_file = REPO_ROOT / "temp_link_check_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_markdown_files': len(md_files),
            'total_internal_links': total_internal_links,
            'broken_links': broken_count,
            'results': all_results
        }, f, indent=2)

    print(f"\nSummary:")
    print(f"  Total markdown files: {len(md_files)}")
    print(f"  Total internal links checked: {total_internal_links}")
    print(f"  Broken links: {broken_count}")
    print(f"\nResults saved to: {output_file}")

    return broken_count

if __name__ == '__main__':
    exit(main())
