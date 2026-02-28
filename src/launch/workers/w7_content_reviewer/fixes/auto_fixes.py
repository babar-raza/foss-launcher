"""Auto-fix capabilities for W7 ContentReviewer.

This module implements 9 deterministic auto-fix functions that resolve
common issues identified by Phase 1 checks. All fixes are deterministic
(no LLM calls, no timestamps, stable transforms).

TC-1100-P2: W7 ContentReviewer Phase 2 - Auto-Fix Capabilities
Pattern: Based on W10 Fixer fix functions (src/launch/workers/w10_fixer/worker.py:239-424)

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
        file_path = drafts_dir / rel_path

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
                # BLOCKER-2 Final Fix: Disable snippet_attribution auto-fix
                # This fix adds <!-- source: --> comments that conflict with source_annotations check
                # The check will WARN but not auto-fix (user must add to snippet catalog)
                result = {
                    "issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "snippet_attribution",
                    "files_changed": [],
                    "success": False,
                    "error": "Auto-fix disabled: snippet_attribution conflicts with source_annotations check. Add code to snippet catalog instead."
                }
            elif "source_annotations" in check_name:
                result = fix_source_annotations(issue, file_path)
            elif "technical_terminology_consistency" in check_name:
                result = fix_terminology_consistency(issue, file_path)
            elif "completeness" in check_name:
                result = fix_placeholder_content(issue, file_path)
            elif "error_message_clarity" in check_name:
                result = fix_error_message_format(issue, file_path)
            elif "platform_listing" in check_name:
                result = fix_platform_listing(issue, file_path, product_facts)
            elif "fq1_naked_code" in check_name:
                result = fix_fq1_naked_code(issue, file_path)
            elif "fq3_truncated_bullets" in check_name:
                result = fix_fq3_truncated_bullets(issue, file_path)
            elif "fq4_double_heading" in check_name:
                result = fix_fq4_double_heading(issue, file_path)
            elif "prompt_leak" in check_name or "scaffold_leak" in check_name:
                result = fix_prompt_scaffold_leak(issue, file_path)
            elif "code_fence_fragmentation" in check_name:
                result = fix_code_fence_merge(issue, file_path)
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

    Pattern based on: W10 fix_unresolved_token (w10_fixer/worker.py:239-305)

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

    Pattern based on: W10 fix_frontmatter_invalid_yaml (w10_fixer/worker.py:355-424)

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

    Pattern based on: W10 fix_unresolved_token (w10_fixer/worker.py:239-305)

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

        # TC-1750: Flag for review instead of injecting claim markers.
        # Injecting markers (even real IDs) creates downstream issues with
        # claim_validity and evidence_linkage checks. Instead, add a review
        # comment that W7 LLM regen agents can address.
        review_comment = (
            f"\n\n<!-- W7_REVIEW: low_content_density — "
            f"expected ~{needed} claim markers, found {len(existing_ids)}. "
            f"Content needs enrichment with claim-backed statements. -->\n"
        )
        content = content.rstrip() + review_comment
        file_path.write_text(content, encoding='utf-8')

        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "low_content_density",
            "files_changed": [str(file_path)],
            "success": True,
            "action": "flagged_for_review",
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


# Fix Function 15: Example Clarity (DISABLED — generic filler adds no value)
def fix_example_clarity(issue: Dict, file_path: Path) -> Dict:
    """Disabled: generic filler text like 'The code above performs the described
    operation' adds no value and gets flagged by strip_boilerplate_sentences.

    Previously this function injected boilerplate around code blocks. Now W8
    calls strip_boilerplate_sentences() which removes these exact patterns,
    making this fix counterproductive.

    Original strategy:
    - 'missing introduction': Insert a short intro line before the code block
    - 'missing explanation': Insert a short explanation after the code block

    Args:
        issue: Issue dict with location.line and message
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    return {
        "issue_id": issue.get("issue_id", "unknown"),
        "fix_type": "example_clarity",
        "files_changed": [],
        "success": False,
        "error": "fix_example_clarity disabled — generic filler adds no value",
    }
    # --- Original implementation below (kept for reference) ---
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

    Strategy: Insert <!-- source: product API documentation --> BEFORE the code fence,
    not inside the block. This prevents Python syntax errors from HTML comments.

    BLOCKER-2 Fix: Fence-aware insertion logic.

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

        # BLOCKER-2 Fix: Track fence state from start to find correct insertion point
        # This handles line drift from multiple fixes on the same file
        insert_pos = -1
        in_fence = False
        fence_start = -1

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track fence state
            if stripped.startswith('```'):
                if not in_fence:
                    fence_start = i
                    in_fence = True
                else:
                    in_fence = False
                    fence_start = -1

            # Check if this is the target line
            if i == target_line - 1:  # Convert to 0-indexed
                if stripped.startswith('```') and not in_fence:
                    # Target is a fence opener - insert before it
                    insert_pos = i
                elif in_fence and fence_start >= 0:
                    # Target is inside a block - insert before the opening fence
                    insert_pos = fence_start
                else:
                    # Target is outside any block - insert before it
                    insert_pos = i
                break

        if insert_pos < 0:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "snippet_attribution",
                "files_changed": [],
                "success": False,
                "error": "Could not determine insertion position",
            }

        attribution = "<!-- source: product API documentation -->"
        lines.insert(insert_pos, attribution)

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


# Fix Function 19: Source Annotations
def fix_source_annotations(issue: Dict, file_path: Path) -> Dict:
    """Remove source attribution comments from body content.

    Pattern: Strip <!-- source: ... --> comments that leaked into final output.

    TC-1504 (Check CQ-13 auto-fix)

    Args:
        issue: Issue dict with location.line
        file_path: Path to file to fix

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Pattern: <!-- source: ... --> on its own line or inline
        source_annotation_pattern = r'<!--\s*source:.*?-->\s*\n?'

        # Count matches
        original_count = len(re.findall(source_annotation_pattern, content, re.IGNORECASE))

        # Remove all source annotations
        content = re.sub(source_annotation_pattern, '', content, flags=re.IGNORECASE)

        if original_count > 0:
            # Clean up triple newlines
            content = re.sub(r'\n{3,}', '\n\n', content)

            file_path.write_text(content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "source_annotations",
                "files_changed": [str(file_path)],
                "success": True,
                "annotations_removed": original_count,
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "source_annotations",
                "files_changed": [],
                "success": False,
                "error": "No source annotations found",
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "source_annotations",
            "files_changed": [],
            "success": False,
            "error": str(e),
        }


# Fix Function 20: Platform Listing
def fix_platform_listing(issue: Dict, file_path: Path, product_facts: Dict) -> Dict:
    """Remove wrong platform listings from Available Platforms section.

    Strategy: Find the section, remove lines mentioning wrong platforms.

    TC-1504 (Check U-13 auto-fix)

    Args:
        issue: Issue dict with message containing wrong platforms
        file_path: Path to file to fix
        product_facts: Product facts for platform detection

    Returns:
        Fix result dict
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Extract target platform from product_name
        product_name = product_facts.get("product_name", "")
        target_platform = None

        if "python" in product_name.lower():
            target_platform = "python"
        elif ".net" in product_name.lower() or "dotnet" in product_name.lower():
            target_platform = ".net"
        elif "java" in product_name.lower():
            target_platform = "java"

        if not target_platform:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "platform_listing",
                "files_changed": [],
                "success": False,
                "error": "Cannot determine target platform",
            }

        # Find Available Platforms section
        platform_section_pattern = r'(##\s+Available\s+Platforms?.*?\n)(.*?)(?=\n##|\Z)'
        match = re.search(platform_section_pattern, content, re.IGNORECASE | re.DOTALL)

        if not match:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "platform_listing",
                "files_changed": [],
                "success": False,
                "error": "No Available Platforms section found",
            }

        heading = match.group(1)
        section_content = match.group(2)

        # Define wrong platform keywords
        wrong_keywords = []
        if target_platform == "python":
            wrong_keywords = [".net", "dotnet", "c#", "csharp", "java"]
        elif target_platform == ".net":
            wrong_keywords = ["python", "py", "java"]
        elif target_platform == "java":
            wrong_keywords = ["python", "py", ".net", "dotnet", "c#", "csharp"]

        # Remove lines containing wrong platforms
        lines = section_content.split('\n')
        filtered_lines = []
        removed_count = 0

        for line in lines:
            line_lower = line.lower()
            has_wrong_platform = any(kw in line_lower for kw in wrong_keywords)

            if has_wrong_platform:
                removed_count += 1
            else:
                filtered_lines.append(line)

        if removed_count > 0:
            new_section = '\n'.join(filtered_lines)
            new_content = content[:match.start()] + heading + new_section + content[match.end():]

            # Clean up triple newlines
            new_content = re.sub(r'\n{3,}', '\n\n', new_content)

            file_path.write_text(new_content, encoding='utf-8')

            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "platform_listing",
                "files_changed": [str(file_path)],
                "success": True,
                "lines_removed": removed_count,
            }
        else:
            return {
                "issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "platform_listing",
                "files_changed": [],
                "success": False,
                "error": "No wrong platform lines found to remove",
            }

    except Exception as e:
        return {
            "issue_id": issue.get("issue_id", "unknown"),
            "fix_type": "platform_listing",
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


# BLKR-02: FQ Auto-Fix Functions

def fix_fq1_naked_code(issue: Dict, file_path: Path) -> Dict:
    """FQ-1: Wrap naked code lines (outside fences) in a fenced code block.

    Detects the specific line reported by the check and wraps it in a
    ```python fence if it looks like Python, or ```bash for shell commands.

    BLKR-02: Auto-fix for technical_accuracy.fq1_naked_code issues.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        line_num = issue.get("location", {}).get("line", 0)
        if not line_num:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq1_naked_code",
                    "files_changed": [], "success": False, "error": "No line number"}

        lines = content.split('\n')
        if line_num < 1 or line_num > len(lines):
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq1_naked_code",
                    "files_changed": [], "success": False, "error": f"Line {line_num} out of range"}

        target = lines[line_num - 1]
        stripped = target.strip()

        # Choose language tag
        if stripped.startswith('$') or stripped.startswith('pip '):
            lang = 'bash'
        else:
            lang = 'python'

        lines[line_num - 1] = f'```{lang}\n{stripped}\n```'
        new_content = '\n'.join(lines)

        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq1_naked_code",
                    "files_changed": [str(file_path)], "success": True}

        return {"issue_id": issue.get("issue_id"), "fix_type": "fq1_naked_code",
                "files_changed": [], "success": False, "error": "No change made"}
    except Exception as e:
        return {"issue_id": issue.get("issue_id", "unknown"), "fix_type": "fq1_naked_code",
                "files_changed": [], "success": False, "error": str(e)}


def fix_fq3_truncated_bullets(issue: Dict, file_path: Path) -> Dict:
    """FQ-3: End truncated bullet points with a period.

    Appends a period to bullets that end with a trailing comma or a
    dangling preposition/conjunction. This makes the bullet syntactically
    complete without changing the meaning.

    BLKR-02: Auto-fix for technical_accuracy.fq3_truncated_bullets issues.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        line_num = issue.get("location", {}).get("line", 0)
        if not line_num:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq3_truncated_bullets",
                    "files_changed": [], "success": False, "error": "No line number"}

        lines = content.split('\n')
        if line_num < 1 or line_num > len(lines):
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq3_truncated_bullets",
                    "files_changed": [], "success": False, "error": f"Line {line_num} out of range"}

        target = lines[line_num - 1]
        rstripped = target.rstrip()

        # Remove trailing comma and add period, or just add period
        if rstripped.endswith(','):
            fixed = rstripped[:-1] + '.'
        elif not rstripped.endswith('.'):
            fixed = rstripped + '.'
        else:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq3_truncated_bullets",
                    "files_changed": [], "success": False, "error": "Line already ends with period"}

        lines[line_num - 1] = fixed
        new_content = '\n'.join(lines)

        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq3_truncated_bullets",
                    "files_changed": [str(file_path)], "success": True}

        return {"issue_id": issue.get("issue_id"), "fix_type": "fq3_truncated_bullets",
                "files_changed": [], "success": False, "error": "No change made"}
    except Exception as e:
        return {"issue_id": issue.get("issue_id", "unknown"), "fix_type": "fq3_truncated_bullets",
                "files_changed": [], "success": False, "error": str(e)}


def fix_fq4_double_heading(issue: Dict, file_path: Path) -> Dict:
    """FQ-4: Insert a newline between an oversized heading and its body text.

    When a heading line exceeds 70 chars, the extra text is likely paragraph
    content that leaked in. This fix splits the line at the first sentence
    boundary ('. ' or ': ') after a reasonable heading length.

    BLKR-02: Auto-fix for technical_accuracy.fq4_double_heading issues.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        line_num = issue.get("location", {}).get("line", 0)
        if not line_num:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                    "files_changed": [], "success": False, "error": "No line number"}

        lines = content.split('\n')
        if line_num < 1 or line_num > len(lines):
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                    "files_changed": [], "success": False, "error": f"Line {line_num} out of range"}

        target = lines[line_num - 1]
        # Find heading prefix
        m = re.match(r'^(#{1,6}\s+)(.+)', target)
        if not m:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                    "files_changed": [], "success": False, "error": "Not a heading line"}

        prefix = m.group(1)
        heading_body = m.group(2)

        # Try to split at a sentence boundary after 30 chars
        split_pos = -1
        for sep in ['. ', '? ', '! ']:
            pos = heading_body.find(sep, 30)
            if pos != -1:
                split_pos = pos + len(sep) - 1
                break

        if split_pos == -1:
            # No sentence boundary found; split at first capital after 30 chars
            for i in range(30, len(heading_body) - 1):
                if heading_body[i] == ' ' and heading_body[i + 1].isupper():
                    split_pos = i
                    break

        if split_pos == -1:
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                    "files_changed": [], "success": False,
                    "error": "Could not find split point in heading"}

        heading_part = prefix + heading_body[:split_pos].rstrip()
        body_part = heading_body[split_pos:].lstrip()
        lines[line_num - 1] = heading_part + '\n\n' + body_part
        new_content = '\n'.join(lines)

        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                    "files_changed": [str(file_path)], "success": True}

        return {"issue_id": issue.get("issue_id"), "fix_type": "fq4_double_heading",
                "files_changed": [], "success": False, "error": "No change made"}
    except Exception as e:
        return {"issue_id": issue.get("issue_id", "unknown"), "fix_type": "fq4_double_heading",
                "files_changed": [], "success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Fix: Prompt/Scaffold Leak Removal
# ---------------------------------------------------------------------------

_SCAFFOLD_HEADING_RE = [
    re.compile(r'^#{1,3}\s+Product\s+Context', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Instructions\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Output\s+Rules\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Source\s+Material\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+CRITICAL\s+Rules?\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+FORMATTING\s+RULES\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Page-Specific\s+Context\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Requirements\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+(?:Output\s+)?Format(?:ting)?\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Audience\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+SEO\s+Keywords?\s*$', re.IGNORECASE),
    # Non-heading forms
    re.compile(r'^\*{1,2}Product\s+Context\*{1,2}\s*$', re.IGNORECASE),
    re.compile(r'^Product\s+Context:\s*$', re.IGNORECASE),
    re.compile(r'^[-*]\s+Product\s+Context:\s*$', re.IGNORECASE),
    # TC-2890: claims/API/issues/content prompt section headings
    re.compile(r'^#{1,3}\s+Available\s+Claims\b', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Known\s+API\s+Surface\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Issues\s+Found\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Original\s+Content\s*$', re.IGNORECASE),
    re.compile(r'^#{1,3}\s+Key\s+Claims\s*$', re.IGNORECASE),
]

_W_REVIEW_RE = re.compile(r'W\d+(?:\.\d+)?_REVIEW\b')

_XML_PROMPT_TAG_RE = re.compile(
    r'<(instructions|context|original-content|issues)>'
    r'.*?'
    r'</\1>',
    re.DOTALL | re.IGNORECASE,
)


def fix_prompt_scaffold_leak(issue: Dict, file_path: Path) -> Dict:
    """Strip leaked prompt/scaffold sections from a markdown file.

    Removes:
    - Scaffold headings (Product Context, Instructions, etc.) + body until next heading
    - W*_REVIEW markers as plain text
    - XML prompt structure tags and their content
    - Bold/label forms of scaffold sections

    Fence-aware: never strips content inside code fences.
    Idempotent: running twice yields identical output.
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Pass 1: Strip XML prompt tag pairs (multiline, before line-based processing)
        cleaned = _XML_PROMPT_TAG_RE.sub('', content)

        # Pass 2: Line-based scaffold heading + W_REVIEW removal (fence-aware)
        lines = cleaned.split('\n')
        result: list = []
        in_fence = False
        skip_until_heading = False

        for line in lines:
            stripped = line.strip()

            # Track fence state
            if stripped.startswith('```'):
                in_fence = not in_fence
                if not skip_until_heading:
                    result.append(line)
                continue

            # Never strip inside fences
            if in_fence:
                if not skip_until_heading:
                    result.append(line)
                continue

            # Detect scaffold headings
            if any(p.match(stripped) for p in _SCAFFOLD_HEADING_RE):
                skip_until_heading = True
                continue

            # Stop skipping at the next heading
            if skip_until_heading:
                if re.match(r'^#{1,6}\s', stripped):
                    skip_until_heading = False
                    result.append(line)
                continue

            # Strip W*_REVIEW markers
            if _W_REVIEW_RE.search(line) and not in_fence:
                continue

            result.append(line)

        new_content = '\n'.join(result)

        # Collapse triple+ blank lines to double
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)

        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {"issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "prompt_scaffold_leak",
                    "files_changed": [str(file_path)], "success": True}

        return {"issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "prompt_scaffold_leak",
                "files_changed": [], "success": False,
                "error": "No scaffold leak content found to remove"}
    except Exception as e:
        return {"issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "prompt_scaffold_leak",
                "files_changed": [], "success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Fix: Code Fence Fragmentation (merge adjacent same-language fences)
# ---------------------------------------------------------------------------

def fix_code_fence_merge(issue: Dict, file_path: Path) -> Dict:
    """Merge adjacent same-language code fences in a markdown file.

    Delegates to content_sanitizer.merge_adjacent_code_blocks() which already
    implements comprehensive merging logic (blank-line separators, comment
    separators, claim markers, language matching, safety limit of 20 merges).

    Idempotent: after merging, no adjacent same-language fences remain.
    """
    try:
        from ..._shared.content_sanitizer import merge_adjacent_code_blocks

        content = file_path.read_text(encoding='utf-8')
        new_content = merge_adjacent_code_blocks(content)

        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return {"issue_id": issue.get("issue_id", "unknown"),
                    "fix_type": "code_fence_merge",
                    "files_changed": [str(file_path)], "success": True}

        return {"issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "code_fence_merge",
                "files_changed": [], "success": False,
                "error": "No adjacent same-language fences found to merge"}
    except Exception as e:
        return {"issue_id": issue.get("issue_id", "unknown"),
                "fix_type": "code_fence_merge",
                "files_changed": [], "success": False, "error": str(e)}
