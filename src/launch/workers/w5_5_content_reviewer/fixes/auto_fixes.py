"""Auto-fix capabilities for W5.5 ContentReviewer.

This module implements 9 deterministic auto-fix functions that resolve
common issues identified by Phase 1 checks. All fixes are deterministic
(no LLM calls, no timestamps, stable transforms).

TC-1100-P2: W5.5 ContentReviewer Phase 2 - Auto-Fix Capabilities
Pattern: Based on W8 Fixer fix functions (src/launch/workers/w8_fixer/worker.py:239-424)

Spec reference: abstract-hugging-kite.md:286-330 (Auto-fix requirements)
"""

from __future__ import annotations

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

from .iteration_tracker import IterationTracker


def apply_auto_fixes(
    issues: List[Dict],
    drafts_dir: Path,
    product_facts: Dict,
    iteration_tracker: IterationTracker
) -> List[Dict]:
    """Apply deterministic auto-fixes to markdown drafts.

    This function processes issues identified by Phase 1 checks and applies
    appropriate fixes. Only issues with auto_fixable=True are processed.

    Args:
        issues: List of issue dicts from Phase 1 checks
        drafts_dir: Path to drafts/ directory
        product_facts: ProductFacts for context
        iteration_tracker: Tracks iterations per page

    Returns:
        List of fix_result dicts:
        {
            "issue_id": str,
            "fix_type": str,
            "files_changed": List[str],
            "success": bool,
            "error": str (if failed)
        }

    Spec reference: abstract-hugging-kite.md:288-292 (Auto-fix orchestration)
    """
    fix_results = []

    # Group issues by file path
    issues_by_path = {}
    for issue in issues:
        if not issue.get("auto_fixable", False):
            continue

        path = issue.get("location", {}).get("path", "")
        if not path:
            continue

        if path not in issues_by_path:
            issues_by_path[path] = []

        issues_by_path[path].append(issue)

    # Process each file
    for rel_path, file_issues in sorted(issues_by_path.items()):
        # Convert relative path to absolute
        file_path = drafts_dir.parent / rel_path

        if not file_path.exists():
            for issue in file_issues:
                fix_results.append({
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "error",
                    "files_changed": [],
                    "success": False,
                    "error": f"File not found: {file_path}"
                })
            continue

        # Extract page_id from path for iteration tracking
        page_id = _extract_page_id(rel_path)

        # Check if we can iterate on this page
        if not iteration_tracker.can_iterate(page_id):
            for issue in file_issues:
                fix_results.append({
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "max_iterations",
                    "files_changed": [],
                    "success": False,
                    "error": f"Max iterations ({iteration_tracker.MAX_ITERATIONS}) reached for page {page_id}"
                })
            continue

        # Apply fixes for this file
        fixes_applied = 0
        for issue in file_issues:
            check_name = issue.get("check", "")

            # Route to appropriate fix function
            if "claim_marker_format" in check_name:
                result = fix_claim_markers(issue, file_path)
            elif "frontmatter_completeness" in check_name and "comment" in issue.get("message", "").lower():
                result = fix_frontmatter_comments(issue, file_path)
            elif "template_token" in check_name.lower():
                result = fix_template_tokens(issue, file_path, product_facts)
            elif "heading_hierarchy" in check_name:
                result = fix_heading_hierarchy(issue, file_path)
            elif "paragraph_structure" in check_name and "long paragraph" in issue.get("message", "").lower():
                result = fix_paragraph_breaks(issue, file_path)
            elif "link" in check_name and "./page.md" in issue.get("message", ""):
                result = fix_link_normalization(issue, file_path)
            elif "bullet" in check_name and "too long" in issue.get("message", "").lower():
                result = fix_bullet_splitting(issue, file_path)
            elif "alt_text" in check_name or ("image" in issue.get("message", "").lower() and "alt" in issue.get("message", "").lower()):
                result = fix_alt_text(issue, file_path)
            elif "metadata" in check_name or "product_name" in issue.get("message", "").lower():
                result = fix_metadata(issue, file_path, product_facts)
            else:
                # Unknown fix type
                result = {
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "unknown",
                    "files_changed": [],
                    "success": False,
                    "error": f"No fix handler for check: {check_name}"
                }

            fix_results.append(result)

            if result.get("success", False):
                fixes_applied += 1

        # Record iteration if fixes were applied
        if fixes_applied > 0:
            iteration_tracker.record_iteration(
                page_id=page_id,
                fix_type="auto_fixes",
                count=fixes_applied
            )

    return fix_results


# Fix Function 1: Claim Markers
def fix_claim_markers(issue: Dict, file_path: Path) -> Dict:
    """Convert [claim: UUID] to <!-- claim_id: UUID --> format.

    Pattern based on: W8 fix_unresolved_token (w8_fixer/worker.py:239-305)

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:302-304 (Fix 1: Claim markers)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Pattern: [claim: UUID]
        inline_claim_pattern = r'\[claim:\s*([a-f0-9\-]{36})\]'

        # Replace all inline claim markers with HTML comments
        def replace_claim(match):
            claim_id = match.group(1)
            return f'<!-- claim_id: {claim_id} -->'

        # Count replacements
        original_content = content
        content = re.sub(inline_claim_pattern, replace_claim, content, flags=re.IGNORECASE)

        replacements = len(re.findall(inline_claim_pattern, original_content, re.IGNORECASE))

        if content != original_content:
            # Write back
            file_path.write_text(content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "claim_markers",
                "files_changed": [str(file_path)],
                "success": True,
                "replacements": replacements
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "claim_markers",
                "files_changed": [],
                "success": False,
                "error": "No claim markers found to replace"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "claim_markers",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 2: Frontmatter Comments
def fix_frontmatter_comments(issue: Dict, file_path: Path) -> Dict:
    """Strip YAML # comment lines from frontmatter.

    Pattern based on: W8 fix_frontmatter_invalid_yaml (w8_fixer/worker.py:355-424)

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:305-307 (Fix 2: Frontmatter comments)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?\n)---\s*\n', content, re.DOTALL)

        if not frontmatter_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "frontmatter_comments",
                "files_changed": [],
                "success": False,
                "error": "No frontmatter found"
            }

        frontmatter_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():]

        # Remove YAML comment lines (lines starting with #, but not headings)
        lines = frontmatter_text.split('\n')
        cleaned_lines = []
        comments_removed = 0

        for line in lines:
            # Keep lines that don't start with # (or are empty/whitespace)
            if not re.match(r'^\s*#[^#]', line):
                cleaned_lines.append(line)
            else:
                comments_removed += 1

        if comments_removed > 0:
            # Reconstruct frontmatter
            cleaned_frontmatter = '\n'.join(cleaned_lines)
            fixed_content = f'---\n{cleaned_frontmatter}---\n{body}'

            # Write back
            file_path.write_text(fixed_content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "frontmatter_comments",
                "files_changed": [str(file_path)],
                "success": True,
                "comments_removed": comments_removed
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "frontmatter_comments",
                "files_changed": [],
                "success": False,
                "error": "No comments found to remove"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "frontmatter_comments",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 3: Template Tokens
def fix_template_tokens(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Remove/replace unresolved __TOKEN__ using product_facts.

    Pattern based on: W8 fix_unresolved_token (w8_fixer/worker.py:239-305)

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts for token replacement

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:308-310 (Fix 3: Template tokens)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Pattern: __TOKEN__
        token_pattern = r'__([A-Z0-9_]+)__'

        # Find all tokens
        tokens = re.findall(token_pattern, content)

        if not tokens:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "template_tokens",
                "files_changed": [],
                "success": False,
                "error": "No tokens found"
            }

        replacements = 0
        for token in tokens:
            # Try to resolve token from product_facts
            token_lower = token.lower()
            replacement = None

            # Common token mappings
            if token_lower == "product_name":
                replacement = product_facts.get("product_name", "")
            elif token_lower == "product_family":
                replacement = product_facts.get("product_family", "")
            elif token_lower == "language":
                replacement = product_facts.get("primary_language", "")
            elif token_lower == "package_name":
                replacement = product_facts.get("package_name", "")

            # If no mapping found, remove token
            if replacement:
                content = content.replace(f'__{token}__', replacement)
                replacements += 1
            else:
                # Remove token entirely
                content = content.replace(f'__{token}__', '')
                replacements += 1

        if replacements > 0:
            # Write back
            file_path.write_text(content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "template_tokens",
                "files_changed": [str(file_path)],
                "success": True,
                "replacements": replacements
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "template_tokens",
                "files_changed": [],
                "success": False,
                "error": "No tokens replaced"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "template_tokens",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 4: Heading Hierarchy
def fix_heading_hierarchy(issue: Dict, file_path: Path) -> Dict:
    """Adjust H1→H3 to proper H1→H2→H3.

    Strategy: When H1→H3 skip detected, convert H3 to H2.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:311-313 (Fix 4: Heading hierarchy)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Extract line number from issue
        line_num = issue.get("location", {}).get("line", 0)

        if line_num <= 0 or line_num > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "heading_hierarchy",
                "files_changed": [],
                "success": False,
                "error": f"Invalid line number: {line_num}"
            }

        # Get the line with the skip
        problem_line = lines[line_num - 1]

        # Detect heading level
        heading_match = re.match(r'^(#+)\s+(.+)', problem_line)
        if not heading_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "heading_hierarchy",
                "files_changed": [],
                "success": False,
                "error": f"Line {line_num} is not a heading"
            }

        hashes = heading_match.group(1)
        heading_text = heading_match.group(2)
        current_level = len(hashes)

        # Extract expected level from message (H1→H3 means H3 should be H2)
        # Message format: "Heading level skip (H1→H3, should be H2)"
        message = issue.get("message", "")
        expected_match = re.search(r'should be H(\d+)', message)

        if expected_match:
            expected_level = int(expected_match.group(1))
        else:
            # Fallback: reduce by 1 level
            expected_level = current_level - 1

        # Adjust heading level
        new_hashes = '#' * expected_level
        fixed_line = f'{new_hashes} {heading_text}'
        lines[line_num - 1] = fixed_line

        # Write back
        fixed_content = '\n'.join(lines)
        file_path.write_text(fixed_content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "heading_hierarchy",
            "files_changed": [str(file_path)],
            "success": True,
            "adjustment": f"H{current_level} → H{expected_level}"
        }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "heading_hierarchy",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 5: Paragraph Breaks
def fix_paragraph_breaks(issue: Dict, file_path: Path) -> Dict:
    """Split 15+ line paragraphs at period boundaries.

    Strategy: Find paragraph, split at sentence boundaries (periods),
    insert blank line to create 2+ paragraphs.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:314-316 (Fix 5: Paragraph breaks)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Extract line number from issue (start of paragraph)
        para_start = issue.get("location", {}).get("line", 0)

        if para_start <= 0 or para_start > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "paragraph_breaks",
                "files_changed": [],
                "success": False,
                "error": f"Invalid line number: {para_start}"
            }

        # Find paragraph bounds (continuous non-empty lines)
        para_end = para_start
        for i in range(para_start, len(lines)):
            if lines[i].strip() == '' or lines[i].strip().startswith('#') or \
               lines[i].strip().startswith('-') or lines[i].strip().startswith('*'):
                para_end = i
                break
        else:
            para_end = len(lines)

        para_length = para_end - para_start + 1

        if para_length <= 10:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "paragraph_breaks",
                "files_changed": [],
                "success": False,
                "error": f"Paragraph not long enough ({para_length} lines)"
            }

        # Join paragraph lines and split at sentences
        para_text = ' '.join(lines[para_start - 1:para_end])

        # Split at periods (simple heuristic)
        sentences = [s.strip() + '.' for s in para_text.split('.') if s.strip()]

        # Split into 2 chunks at midpoint
        midpoint = len(sentences) // 2
        chunk1 = ' '.join(sentences[:midpoint])
        chunk2 = ' '.join(sentences[midpoint:])

        # Replace paragraph with 2 paragraphs
        lines[para_start - 1:para_end] = [chunk1, '', chunk2]

        # Write back
        fixed_content = '\n'.join(lines)
        file_path.write_text(fixed_content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "paragraph_breaks",
            "files_changed": [str(file_path)],
            "success": True,
            "chunks_created": 2
        }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "paragraph_breaks",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 6: Link Normalization
def fix_link_normalization(issue: Dict, file_path: Path) -> Dict:
    """Convert ./page.md → /docs/page/.

    Pattern: Convert relative markdown links to absolute Hugo links.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:317-319 (Fix 6: Link normalization)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Pattern: [text](./page.md) or [text](../page.md)
        link_pattern = r'\[([^\]]+)\]\((\.{1,2}/[^\)]+\.md)\)'

        def normalize_link(match):
            link_text = match.group(1)
            link_path = match.group(2)

            # Convert ./page.md → /docs/page/
            # Remove leading ./ or ../
            link_path = link_path.lstrip('./')
            link_path = link_path.lstrip('../')

            # Remove .md extension
            link_path = link_path.replace('.md', '')

            # Add leading /docs/ and trailing /
            normalized = f'/docs/{link_path}/'

            return f'[{link_text}]({normalized})'

        # Replace all relative links
        original_content = content
        content = re.sub(link_pattern, normalize_link, content)

        replacements = len(re.findall(link_pattern, original_content))

        if content != original_content:
            # Write back
            file_path.write_text(content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "link_normalization",
                "files_changed": [str(file_path)],
                "success": True,
                "replacements": replacements
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "link_normalization",
                "files_changed": [],
                "success": False,
                "error": "No relative links found"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "link_normalization",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 7: Bullet Splitting
def fix_bullet_splitting(issue: Dict, file_path: Path) -> Dict:
    """Split 300+ char bullets into 2-3 bullets.

    Strategy: Split bullet at commas or conjunctions (and, or).

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:320-322 (Fix 7: Bullet splitting)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Extract line number from issue
        line_num = issue.get("location", {}).get("line", 0)

        if line_num <= 0 or line_num > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "bullet_splitting",
                "files_changed": [],
                "success": False,
                "error": f"Invalid line number: {line_num}"
            }

        # Get the bullet line
        bullet_line = lines[line_num - 1]

        # Detect bullet type and indentation
        bullet_match = re.match(r'^(\s*)([\-\*]|\d+\.)\s+(.+)', bullet_line)

        if not bullet_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "bullet_splitting",
                "files_changed": [],
                "success": False,
                "error": f"Line {line_num} is not a bullet point"
            }

        indent = bullet_match.group(1)
        bullet_marker = bullet_match.group(2)
        bullet_text = bullet_match.group(3)

        # Split at commas or conjunctions
        # Try commas first
        if ',' in bullet_text:
            parts = [p.strip() for p in bullet_text.split(',') if p.strip()]
        # Try conjunctions (and, or)
        elif ' and ' in bullet_text.lower():
            parts = [p.strip() for p in re.split(r'\s+and\s+', bullet_text, flags=re.IGNORECASE) if p.strip()]
        elif ' or ' in bullet_text.lower():
            parts = [p.strip() for p in re.split(r'\s+or\s+', bullet_text, flags=re.IGNORECASE) if p.strip()]
        else:
            # Split at midpoint
            midpoint = len(bullet_text) // 2
            parts = [bullet_text[:midpoint].strip(), bullet_text[midpoint:].strip()]

        # Limit to 3 parts
        parts = parts[:3]

        # Create new bullet lines
        new_bullets = [f'{indent}{bullet_marker} {part}' for part in parts]

        # Replace original line with new bullets
        lines[line_num - 1:line_num] = new_bullets

        # Write back
        fixed_content = '\n'.join(lines)
        file_path.write_text(fixed_content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "bullet_splitting",
            "files_changed": [str(file_path)],
            "success": True,
            "bullets_created": len(new_bullets)
        }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "bullet_splitting",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 8: Alt Text
def fix_alt_text(issue: Dict, file_path: Path) -> Dict:
    """Add alt="" for images without alt text.

    Pattern: ![](image.png) → ![Description](image.png)

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:323-325 (Fix 8: Alt text)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Pattern: ![](url) - image with empty alt text
        empty_alt_pattern = r'!\[\]\(([^\)]+)\)'

        def add_alt_text(match):
            image_url = match.group(1)

            # Generate alt text from filename
            filename = Path(image_url).stem
            # Convert underscores/hyphens to spaces, capitalize
            alt_text = filename.replace('_', ' ').replace('-', ' ').title()

            return f'![{alt_text}]({image_url})'

        # Replace all images with empty alt text
        original_content = content
        content = re.sub(empty_alt_pattern, add_alt_text, content)

        replacements = len(re.findall(empty_alt_pattern, original_content))

        if content != original_content:
            # Write back
            file_path.write_text(content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "alt_text",
                "files_changed": [str(file_path)],
                "success": True,
                "replacements": replacements
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "alt_text",
                "files_changed": [],
                "success": False,
                "error": "No images with empty alt text found"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "alt_text",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Fix Function 9: Metadata
def fix_metadata(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Add product_name to title if missing.

    Strategy: Parse frontmatter, add product name prefix to title.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts for metadata

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:326-328 (Fix 9: Metadata)
    """
    try:
        # Read file
        content = file_path.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?\n)---\s*\n', content, re.DOTALL)

        if not frontmatter_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "No frontmatter found"
            }

        frontmatter_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():]

        # Parse YAML frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": f"Invalid YAML: {e}"
            }

        if not isinstance(frontmatter, dict):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "Frontmatter is not a dict"
            }

        # Get product name
        product_name = product_facts.get("product_name", "")

        if not product_name:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "Product name not found in product_facts"
            }

        # Add product name to title if not present
        title = frontmatter.get("title", "")

        if product_name.lower() not in title.lower():
            frontmatter["title"] = f"{product_name} - {title}"

            # Reconstruct frontmatter
            updated_frontmatter = yaml.safe_dump(frontmatter, default_flow_style=False, allow_unicode=True)
            fixed_content = f'---\n{updated_frontmatter}---\n{body}'

            # Write back
            file_path.write_text(fixed_content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [str(file_path)],
                "success": True,
                "title_updated": True
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "Product name already in title"
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "metadata",
            "files_changed": [],
            "success": False,
            "error": str(e)
        }


# Helper function
def _extract_page_id(rel_path: str) -> str:
    """Extract page ID from relative path.

    Args:
        rel_path: Relative path (e.g., "drafts/docs/overview/index.md")

    Returns:
        Page ID (e.g., "docs/overview/index")
    """
    # Remove drafts/ prefix
    path = rel_path.replace('drafts/', '')

    # Remove .md extension
    path = path.replace('.md', '')

    return path
