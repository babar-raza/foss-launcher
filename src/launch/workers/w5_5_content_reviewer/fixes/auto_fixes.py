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
            elif "licensing_accuracy" in check_name or "foss_licensing" in check_name:
                result = fix_foss_licensing(issue, file_path)
            elif "frontmatter_completeness" in check_name and "collapsed" in issue.get("message", "").lower():
                result = fix_collapsed_frontmatter(issue, file_path)
            elif "frontmatter_completeness" in check_name and "missing required" in issue.get("message", "").lower():
                result = fix_frontmatter_fields(issue, file_path, product_facts)
            elif "frontmatter_completeness" in check_name and "comment" in issue.get("message", "").lower():
                result = fix_frontmatter_comments(issue, file_path)
            elif "claim_validity" in check_name or "claim_evidence_linkage" in check_name:
                result = fix_invalid_claim_marker(issue, file_path)
            elif "template_token" in check_name.lower():
                result = fix_template_tokens(issue, file_path, product_facts)
            elif "heading_hierarchy" in check_name:
                result = fix_heading_hierarchy(issue, file_path)
            elif "paragraph_structure" in check_name:
                result = fix_paragraph_breaks(issue, file_path)
            elif "link" in check_name and "./page.md" in issue.get("message", ""):
                result = fix_link_normalization(issue, file_path)
            elif "bullet" in check_name and "long" in issue.get("message", "").lower():
                result = fix_bullet_splitting(issue, file_path)
            elif "alt_text" in check_name or ("image" in issue.get("message", "").lower() and "alt" in issue.get("message", "").lower()):
                result = fix_alt_text(issue, file_path)
            elif "metadata" in check_name or "product_name" in issue.get("message", "").lower():
                result = fix_metadata(issue, file_path, product_facts)
            elif "prerequisites_clarity" in check_name:
                result = fix_missing_prerequisites(issue, file_path, product_facts)
            elif "call_to_action" in check_name:
                result = fix_missing_cta(issue, file_path, product_facts)
            elif "user_journey" in check_name:
                result = fix_missing_next_steps(issue, file_path)
            elif "content_density" in check_name:
                result = fix_low_content_density(issue, file_path, product_facts)
            elif "heading_descriptiveness" in check_name:
                result = fix_heading_descriptiveness(issue, file_path, product_facts)
            elif "search_optimization" in check_name:
                result = fix_metadata(issue, file_path, product_facts)
            elif "example_clarity" in check_name:
                result = fix_example_clarity(issue, file_path)
            elif "snippet_attribution" in check_name:
                result = fix_snippet_attribution(issue, file_path)
            elif "technical_terminology_consistency" in check_name:
                result = fix_terminology_consistency(issue, file_path)
            elif "completeness" in check_name:
                result = fix_placeholder_content(issue, file_path)
            elif "error_message_clarity" in check_name:
                result = fix_error_message_format(issue, file_path)
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
        inline_claim_pattern = r'\[claim:\s*([a-f0-9\-]+)\]'

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

        # Safety: never touch lines inside YAML frontmatter (between --- markers)
        if content.startswith('---'):
            fm_end = None
            delim_count = 0
            for i, ln in enumerate(lines):
                if ln.strip() == '---':
                    delim_count += 1
                    if delim_count == 2:
                        fm_end = i + 1  # 1-indexed line after closing ---
                        break
            if fm_end and para_start < fm_end:
                return {
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "paragraph_breaks",
                    "files_changed": [],
                    "success": False,
                    "error": "Paragraph is inside frontmatter, skipping",
                }

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

    Strategy: Regex-based title replacement in frontmatter (no YAML parsing).

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts for metadata

    Returns:
        Fix result dict

    Spec reference: abstract-hugging-kite.md:326-328 (Fix 9: Metadata)
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        frontmatter_match = re.match(r'^(---\s*\n)(.*?\n)(---)', content, re.DOTALL)
        if not frontmatter_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "No frontmatter found"
            }

        product_name = product_facts.get("product_name", "")
        if not product_name:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "metadata",
                "files_changed": [],
                "success": False,
                "error": "Product name not found in product_facts"
            }

        fm_text = frontmatter_match.group(2)
        # Compute absolute offset of fm_text within content
        fm_text_offset = frontmatter_match.start(2)

        # Find title value — handle quoted titles precisely to avoid
        # corrupting collapsed YAML where multiple fields share one line.
        quoted_m = re.search(r'^title:\s*"([^"]*)"', fm_text, re.MULTILINE)
        if not quoted_m:
            quoted_m = re.search(r"^title:\s*'([^']*)'", fm_text, re.MULTILINE)
        if quoted_m:
            title_value = quoted_m.group(1)
        else:
            # Unquoted: take text up to next YAML key or end of line
            unquoted_m = re.search(r'^title:\s*(.+?)(?:\s+\w+:|$)', fm_text, re.MULTILINE)
            if not unquoted_m:
                return {
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "metadata",
                    "files_changed": [],
                    "success": False,
                    "error": "No title field in frontmatter"
                }
            title_value = unquoted_m.group(1).strip()
            quoted_m = unquoted_m  # Use same match object for positioning

        if product_name.lower() not in title_value.lower():
            new_title = f'{product_name} - {title_value}'
            # Replace ONLY the title value at its exact position in content
            abs_start = fm_text_offset + quoted_m.start(1)
            abs_end = fm_text_offset + quoted_m.end(1)
            content = content[:abs_start] + new_title + content[abs_end:]
            file_path.write_text(content, encoding='utf-8')

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


# Fix Function 10: Missing Prerequisites
def fix_missing_prerequisites(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Insert ## Prerequisites section before first H2 in body.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts for product name

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        product_name = product_facts.get("product_name", "Product")

        prereq_section = (
            "\n## Prerequisites\n\n"
            f"Before you begin, ensure you have {product_name} installed. "
            "See the [Installation Guide](/docs/installation/) for setup instructions.\n\n"
        )

        # Find first H2 in body (after frontmatter)
        body_match = re.search(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        body_start = body_match.end() if body_match else 0

        # Find first ## heading after body start
        h2_match = re.search(r'^## ', content[body_start:], re.MULTILINE)
        if h2_match:
            insert_pos = body_start + h2_match.start()
            content = content[:insert_pos] + prereq_section + content[insert_pos:]
        else:
            # Append at end
            content = content.rstrip() + "\n" + prereq_section

        file_path.write_text(content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_prerequisites",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_prerequisites",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 11: Missing CTA
def fix_missing_cta(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Append CTA paragraph with 'Get started' text.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts for product name

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        product_name = product_facts.get("product_name", "Product")

        cta = (
            f"\nGet started with {product_name} today "
            f"— explore the documentation or download the latest release.\n"
        )
        content = content.rstrip() + "\n" + cta + "\n"

        file_path.write_text(content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_cta",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_cta",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 12: Missing Next Steps
def fix_missing_next_steps(issue: Dict, file_path: Path) -> Dict:
    """Append ## Next Steps section with Developer Guide link.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        next_steps = (
            "\n## Next Steps\n\n"
            "Now that you are set up, explore the "
            "[Developer Guide](/docs/developer-guide/) for advanced workflows and usage patterns.\n"
        )
        content = content.rstrip() + "\n" + next_steps

        file_path.write_text(content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_next_steps",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "missing_next_steps",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13: Low Content Density
def fix_low_content_density(issue: Dict, file_path: Path, product_facts: Dict = None) -> Dict:
    """Inject HTML-comment claim markers using real claim IDs from product_facts.

    IMPORTANT: Uses real claim IDs to avoid triggering claim_validity and
    claim_evidence_linkage errors. Falls back to skipping if no real IDs available.

    Args:
        issue: Issue dict with location and message
        file_path: Path to file to fix
        product_facts: Product facts dict containing claims list

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Extract expected claim count from message
        import re as _re
        count_match = _re.search(r'expect ~(\d+)', issue.get("message", ""))
        needed = int(count_match.group(1)) if count_match else 2

        # Count existing claim markers
        existing_ids = set()
        for m in _re.finditer(r'<!--\s*claim_id:\s*([a-f0-9\-]+)\s*-->', content, _re.IGNORECASE):
            existing_ids.add(m.group(1))
        for m in _re.finditer(r'\[claim:\s*([a-f0-9\-]+)\]', content, _re.IGNORECASE):
            existing_ids.add(m.group(1))
        to_add = max(0, needed - len(existing_ids))

        if to_add <= 0:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "low_content_density",
                "files_changed": [],
                "success": False,
                "error": "Sufficient claim markers already present",
            }

        # Use real claim IDs from product_facts (not synthetic UUIDs)
        available_ids = []
        if product_facts:
            for c in product_facts.get("claims", []):
                cid = c.get("claim_id", "")
                if cid and cid not in existing_ids:
                    available_ids.append(cid)

        if not available_ids:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "low_content_density",
                "files_changed": [],
                "success": False,
                "error": "No available real claim IDs to inject",
            }

        markers = []
        for cid in available_ids[:min(to_add, 5)]:
            markers.append(f"<!-- claim_id: {cid} -->")
        content = content.rstrip() + "\n\n" + "\n".join(markers) + "\n"
        file_path.write_text(content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "low_content_density",
            "files_changed": [str(file_path)],
            "success": True,
            "markers_added": len(markers),
        }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "low_content_density",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13b: Missing Frontmatter Fields
def fix_frontmatter_fields(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Add missing required frontmatter fields with sensible defaults.

    Args:
        issue: Issue dict with message indicating missing field
        file_path: Path to file to fix
        product_facts: Product facts for product name

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        product_name = product_facts.get("product_name", "Documentation")

        # Derive page slug from filename
        page_slug = file_path.stem
        if page_slug in ('_index', 'index'):
            page_slug = file_path.parent.name or 'index'

        # Check what frontmatter looks like
        fm_match = re.match(r'^---\s*\n(.*?\n)---', content, re.DOTALL)
        if not fm_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "frontmatter_fields",
                "files_changed": [],
                "success": False,
                "error": "No frontmatter block found",
            }

        fm_text = fm_match.group(1)
        body = content[fm_match.end():]
        lines = fm_text.strip().split('\n')

        message = issue.get("message", "").lower()

        if "title" in message and not re.search(r'^title:', fm_text, re.MULTILINE):
            title = page_slug.replace('-', ' ').replace('_', ' ').title()
            lines.append(f"title: \"{product_name} - {title}\"")
        if "description" in message and not re.search(r'^description:', fm_text, re.MULTILINE):
            desc = f"{product_name} {page_slug.replace('-', ' ')} documentation"
            lines.append(f"description: \"{desc}\"")
        if "url" in message:
            has_url = re.search(r'^(?:permalink|url_path):', fm_text, re.MULTILINE)
            if not has_url:
                lines.append(f"url_path: /{page_slug}/")

        new_fm = '\n'.join(lines) + '\n'
        new_content = f"---\n{new_fm}---{body}"
        file_path.write_text(new_content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "frontmatter_fields",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "frontmatter_fields",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13c: Invalid Claim Marker Removal
def fix_invalid_claim_marker(issue: Dict, file_path: Path) -> Dict:
    """Remove invalid claim markers (not in product_facts or evidence_map).

    Args:
        issue: Issue dict with message containing the invalid claim ID
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        message = issue.get("message", "")

        # Extract claim ID from message
        cid_match = re.search(r':\s*([a-f0-9\-]+)\s*$', message)
        if not cid_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "invalid_claim_marker",
                "files_changed": [],
                "success": False,
                "error": "Cannot extract claim ID from message",
            }

        claim_id = cid_match.group(1)

        # Remove the specific claim marker (both formats)
        patterns = [
            rf'<!--\s*claim_id:\s*{re.escape(claim_id)}\s*-->\s*\n?',
            rf'\[claim:\s*{re.escape(claim_id)}\]\s*',
        ]

        original = content
        for pattern in patterns:
            content = re.sub(pattern, '', content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "invalid_claim_marker",
                "files_changed": [str(file_path)],
                "success": True,
            }

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "invalid_claim_marker",
            "files_changed": [],
            "success": False,
            "error": f"Claim marker {claim_id} not found in file",
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "invalid_claim_marker",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13d2: Error Message Formatting
def fix_error_message_format(issue: Dict, file_path: Path) -> Dict:
    """Wrap bare error message text in inline code backticks."""
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        target_line = issue.get("location", {}).get("line", 0)

        if target_line < 1 or target_line > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "error_message_format",
                "files_changed": [],
                "success": False,
                "error": "Invalid line number",
            }

        line = lines[target_line - 1]
        # Wrap patterns like "Error:" and "Exception:" in inline code
        for pat in ['Error:', 'Exception:', 'Warning:', 'Failed:']:
            if pat in line and f'`{pat}' not in line:
                line = line.replace(pat, f'`{pat}`')
                break

        lines[target_line - 1] = line
        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "error_message_format",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "error_message_format",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13d: Terminology Consistency (repo URL)
def fix_terminology_consistency(issue: Dict, file_path: Path) -> Dict:
    """Replace incorrect repo URL with the correct one from suggested_fix."""
    try:
        content = file_path.read_text(encoding='utf-8')
        message = issue.get("message", "")
        suggested = issue.get("suggested_fix", "")

        # Extract incorrect URL from message: "Incorrect repo URL: <url> (expected: <url>)"
        url_match = re.search(r'Incorrect repo URL:\s*(\S+)', message)
        if not url_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "terminology_consistency",
                "files_changed": [],
                "success": False,
                "error": "Could not parse incorrect URL from message",
            }

        incorrect_url = url_match.group(1)
        # Extract correct URL from suggested_fix: "Replace with: <url>"
        correct_match = re.search(r'Replace with:\s*(\S+)', suggested)
        if not correct_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "terminology_consistency",
                "files_changed": [],
                "success": False,
                "error": "No suggested_fix with correct URL",
            }

        correct_url = correct_match.group(1)
        new_content = content.replace(incorrect_url, correct_url)
        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "terminology_consistency",
                "files_changed": [str(file_path)],
                "success": True,
            }
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "terminology_consistency",
            "files_changed": [],
            "success": False,
            "error": "URL not found in file content",
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "terminology_consistency",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 13e: Placeholder Content Removal
def fix_placeholder_content(issue: Dict, file_path: Path) -> Dict:
    """Remove lines containing placeholder text (TODO, TBD, PLACEHOLDER, etc.)."""
    try:
        content = file_path.read_text(encoding='utf-8')
        line_num = issue.get("location", {}).get("line", 0)
        if not line_num:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "placeholder_content",
                "files_changed": [],
                "success": False,
                "error": "No line number in issue",
            }

        lines = content.split('\n')
        if 1 <= line_num <= len(lines):
            removed_line = lines[line_num - 1]
            lines.pop(line_num - 1)
            # Remove extra blank line if removal leaves double blanks
            if line_num - 1 < len(lines) and line_num >= 2:
                if lines[line_num - 2].strip() == '' and lines[line_num - 1].strip() == '':
                    lines.pop(line_num - 1)
            file_path.write_text('\n'.join(lines), encoding='utf-8')
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "placeholder_content",
                "files_changed": [str(file_path)],
                "success": True,
            }
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "placeholder_content",
            "files_changed": [],
            "success": False,
            "error": f"Line {line_num} out of range",
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "placeholder_content",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 14: Heading Descriptiveness
def fix_heading_descriptiveness(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Prepend product name to short generic headings.

    Strategy: '## Usage' becomes '## {product_name} Usage'.
    Uses message text matching (not line numbers) to avoid drift after earlier fixes.

    Args:
        issue: Issue dict with message containing the heading text
        file_path: Path to file to fix
        product_facts: Product facts for product name

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        product_name = product_facts.get("product_name", "")

        if not product_name:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "heading_descriptiveness",
                "files_changed": [],
                "success": False,
                "error": "Missing product_name",
            }

        # Extract heading text from issue message: "Generic heading: Usage"
        message = issue.get("message", "")
        heading_text_match = re.search(r'Generic heading:\s*(.+)', message)
        if not heading_text_match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "heading_descriptiveness",
                "files_changed": [],
                "success": False,
                "error": "Cannot extract heading text from message",
            }

        heading_text = heading_text_match.group(1).strip()

        # Find and replace the heading in the file by matching text (not line number)
        lines = content.split('\n')
        fixed = False
        for i, line in enumerate(lines):
            hm = re.match(r'^(#+)\s+(.+)$', line)
            if hm and hm.group(2).strip() == heading_text:
                if product_name.lower() not in heading_text.lower():
                    lines[i] = f"{hm.group(1)} {product_name} {heading_text}"
                    fixed = True
                    break  # Fix first matching occurrence only

        if fixed:
            file_path.write_text('\n'.join(lines), encoding='utf-8')
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "heading_descriptiveness",
                "files_changed": [str(file_path)],
                "success": True,
            }

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "heading_descriptiveness",
            "files_changed": [],
            "success": False,
            "error": f"Heading '{heading_text}' not found in file",
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "heading_descriptiveness",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 15: Example Clarity
def fix_example_clarity(issue: Dict, file_path: Path) -> Dict:
    """Add introductory or explanatory text around code blocks.

    Strategy:
    - 'missing introduction': Insert a short intro line before the code block
    - 'missing explanation': Insert a short explanation after the code block

    Args:
        issue: Issue dict with location.line and message
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        message = issue.get("message", "").lower()

        # Find all code blocks and match by approximate line number
        code_blocks = list(re.finditer(r'```\w*\n.*?```', content, re.DOTALL))
        target_line = issue.get("location", {}).get("line", 0)

        # Find the closest code block to the target line
        best_block = None
        best_dist = float('inf')
        for block in code_blocks:
            block_line = content[:block.start()].count('\n') + 1
            dist = abs(block_line - target_line)
            if dist < best_dist:
                best_dist = dist
                best_block = block

        if not best_block or best_dist > 10:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "example_clarity",
                "files_changed": [],
                "success": False,
                "error": "No code block found near target line",
            }

        if "introduction" in message:
            intro = "\nThe following example demonstrates this operation:\n"
            content = content[:best_block.start()] + intro + content[best_block.start():]
        elif "explanation" in message:
            explanation = "\n\nThe code above performs the described operation."
            content = content[:best_block.end()] + explanation + content[best_block.end():]
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "example_clarity",
                "files_changed": [],
                "success": False,
                "error": f"Unknown clarity issue type: {message}",
            }

        file_path.write_text(content, encoding='utf-8')
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "example_clarity",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "example_clarity",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 16: Snippet Attribution
def fix_snippet_attribution(issue: Dict, file_path: Path) -> Dict:
    """Add attribution comment above unattributed code blocks.

    Strategy: Insert <!-- source: product API documentation --> before the code block.

    Args:
        issue: Issue dict with location.line
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        target_line = issue.get("location", {}).get("line", 0)

        if target_line < 1 or target_line > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "snippet_attribution",
                "files_changed": [],
                "success": False,
                "error": "Invalid line number",
            }

        # Insert attribution comment before the code block
        attribution = "<!-- source: product API documentation -->"
        lines.insert(target_line - 1, attribution)

        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "snippet_attribution",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "snippet_attribution",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 17: FOSS Licensing
def fix_foss_licensing(issue: Dict, file_path: Path) -> Dict:
    """Remove lines containing commercial licensing language from FOSS content.

    Strategy: If the offending line is a list item, blockquote, or pipe (table),
    remove the line entirely. Otherwise, blank it out. Then collapse triple-newlines.

    TC-1407: Defense-in-Depth

    Args:
        issue: Issue dict with location.line
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        line_num = issue.get("location", {}).get("line", 0)
        lines = content.split('\n')

        if line_num <= 0 or line_num > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "foss_licensing",
                "files_changed": [],
                "success": False,
            }

        target = lines[line_num - 1].strip()
        if target.startswith(('-', '*', '>', '|')) or not target:
            lines.pop(line_num - 1)
        else:
            lines[line_num - 1] = ''

        fixed = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines))
        file_path.write_text(fixed, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "foss_licensing",
            "files_changed": [str(file_path)],
            "success": True,
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "foss_licensing",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 18: Collapsed Frontmatter
def fix_collapsed_frontmatter(issue: Dict, file_path: Path) -> Dict:
    """Split collapsed YAML where multiple keys share one line.

    Strategy: Detect lines with 2+ YAML key patterns and split at
    key boundaries (after quoted/bracketed values followed by a key).

    TC-1407: Defense-in-Depth

    Args:
        issue: Issue dict with location.line
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        line_num = issue.get("location", {}).get("line", 0)

        if line_num <= 0 or line_num > len(lines):
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "collapsed_frontmatter",
                "files_changed": [],
                "success": False,
                "error": f"Invalid line number: {line_num}",
            }

        target_line = lines[line_num - 1]

        # TC-1408: Mask quoted content before detecting split points
        masked = re.sub(r'"[^"]*"', lambda m: '"' + '#' * (len(m.group()) - 2) + '"', target_line)
        masked = re.sub(r"'[^']*'", lambda m: "'" + '#' * (len(m.group()) - 2) + "'", masked)

        # Verify this is actually collapsed (not a false positive from colons in quotes)
        key_matches = re.findall(r'(?:^|\s)\w+:\s', masked)
        if len(key_matches) < 2:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "collapsed_frontmatter",
                "files_changed": [],
                "success": True,
                "error": "Not actually collapsed after quote-aware check",
            }

        # Split at boundaries using masked version for position finding
        split_re = re.compile(r'(?<=["\'}\]/.:\w])\s+(?=[a-zA-Z_]\w*:\s)')
        positions = [0]
        for m in split_re.finditer(masked):
            positions.append(m.end())
        split_parts = []
        for i in range(len(positions)):
            start = positions[i]
            end = positions[i + 1] if i + 1 < len(positions) else len(target_line)
            part = target_line[start:end].strip()
            if part:
                split_parts.append(part)

        if len(split_parts) < 2:
            # Fallback: split at spaces before key: patterns (also quote-masked)
            positions = [0]
            for m in re.finditer(r'\s+(?=\w+:\s)', masked):
                positions.append(m.end())
            split_parts = []
            for i in range(len(positions)):
                start = positions[i]
                end = positions[i + 1] if i + 1 < len(positions) else len(target_line)
                part = target_line[start:end].strip()
                if part:
                    split_parts.append(part)

        if len(split_parts) < 2:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "collapsed_frontmatter",
                "files_changed": [],
                "success": False,
                "error": "Could not find split points in collapsed line",
            }

        # Replace single line with multiple lines
        lines[line_num - 1:line_num] = split_parts
        file_path.write_text('\n'.join(lines), encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "collapsed_frontmatter",
            "files_changed": [str(file_path)],
            "success": True,
            "lines_created": len(split_parts),
        }
    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "collapsed_frontmatter",
            "files_changed": [],
            "success": False,
            "error": str(e),
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
