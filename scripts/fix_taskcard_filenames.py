#!/usr/bin/env python3
"""
Script to fix taskcard filenames by extracting titles from frontmatter
and renaming files to follow the standardized naming convention:
TC-XXXX_description_of_task.md
"""

import os
import re
import yaml
from pathlib import Path


def extract_title_from_frontmatter(filepath):
    """Extract the title from a taskcard file's frontmatter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try to extract title from frontmatter (YAML between --- markers)
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            if frontmatter and 'title' in frontmatter:
                return frontmatter['title']
        except yaml.YAMLError:
            pass
    
    # Fallback: try to find title in markdown body
    title_match = re.search(r'^#\s+(?:Taskcard\s+)?TC-\d+\s*[-:]\s*(.+)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    
    return None


def title_to_filename(title):
    """Convert a title to a snake_case filename suffix."""
    # Remove special characters and convert to snake_case
    # Keep alphanumeric, spaces, hyphens, underscores, and common symbols
    result = title.lower()
    
    # Replace common special characters with words
    replacements = {
        ':': ' ',
        '—': ' ',
        '-': ' ',
        '/': '_or_',
        '+': '_plus_',
        '&': '_and_',
        '@': '_at_',
        '%': '_percent_',
        '#': '_number_',
        '$': '_dollar_',
        '!': '',
        '?': '',
        '.': '',
        ',': '',
        '(': '',
        ')': '',
        "'": '',
        '"': '',
    }
    
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # Replace multiple spaces with single space
    result = re.sub(r'\s+', ' ', result)
    
    # Replace spaces with underscores
    result = result.strip().replace(' ', '_')
    
    # Remove any remaining non-alphanumeric characters except underscores
    result = re.sub(r'[^a-z0-9_]', '', result)
    
    # Remove consecutive underscores
    result = re.sub(r'_+', '_', result)
    
    return result


def main():
    taskcards_dir = Path('plans/taskcards')
    
    # Find all TC-XXXX.md files in the range
    files_to_fix = []
    
    for filepath in taskcards_dir.glob('TC-*.md'):
        basename = filepath.name
        match = re.search(r'TC-(\d+)\.md$', basename.replace('\\', '/'))
        if match:
            num = int(match.group(1))
            # Only process files in the range 1616-2451
            if 1616 <= num <= 2451:
                files_to_fix.append((num, filepath))
    
    print(f"Found {len(files_to_fix)} files in range TC-1616 to TC-2451")
    print()
    
    # Process each file
    for num, filepath in sorted(files_to_fix):
        title = extract_title_from_frontmatter(filepath)
        
        if title:
            # Clean up the title for display
            clean_title = re.sub(r'\s+', ' ', title.strip())
            filename_suffix = title_to_filename(title)
            new_filename = f"TC-{num:04d}_{filename_suffix}.md"
            
            print(f"TC-{num:04d}.md")
            print(f"  Title: {clean_title}")
            print(f"  New filename: {new_filename}")
            print()
            
            # Rename the file
            new_filepath = filepath.parent / new_filename
            if filepath != new_filepath:
                print(f"  Renaming: {filepath.name} -> {new_filename}")
                filepath.rename(new_filepath)
                print(f"  Done!")
                print()
        else:
            print(f"TC-{num:04d}.md - WARNING: Could not extract title!")
            print()


if __name__ == '__main__':
    main()
