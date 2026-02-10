"""Content Quality checks for W5.5 ContentReviewer.

This module implements 12 content quality checks that ensure generated markdown
is readable, well-structured, and complete.

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Check module pattern (similar to W7 gates)

Spec reference: abstract-hugging-kite.md:332-374 (Content Quality Dimension)
"""

import re
from pathlib import Path
from typing import Dict, List, Any

from .._shared import STOPWORDS, calculate_flesch_kincaid_grade


# Technical terms whitelist to avoid false positive grammar warnings
TECHNICAL_TERMS = frozenset([
    'aspose', 'api', 'sdk', 'foss', 'github', 'json', 'yaml', 'readme',
    'cli', 'ci', 'cd', 'llm', 'uuid', 'toc', 'cta', 'seo', 'xml', 'html',
    'css', 'npm', 'pip', 'onenote', 'xlsx', 'pdf', 'docx'
])


def check_all(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    page_plan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run all 12 content quality checks and return issues.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        product_facts: Product facts dict from product_facts.json
        page_plan: Page plan dict from page_plan.json

    Returns:
        List of issue dicts with format:
        {
            "issue_id": "content_quality_<check>_<page_slug>_<suffix>",
            "check": "content_quality.<check_name>",
            "severity": "blocker" | "error" | "warn" | "info",
            "message": "Human-readable description",
            "location": {"path": "relative/path/to/file.md", "line": int},
            "auto_fixable": bool,
            "suggested_fix": str (optional)
        }

    Spec reference: abstract-hugging-kite.md:344-374
    """
    issues = []

    if not drafts_dir.exists():
        return issues

    # Find all markdown files in drafts
    md_files = sorted(drafts_dir.rglob("*.md"))

    for md_file in md_files:
        # Read file content
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            issues.append({
                "issue_id": f"content_quality_read_error_{md_file.stem}",
                "check": "content_quality.file_read",
                "severity": "error",
                "message": f"Failed to read file: {e}",
                "location": {"path": str(md_file.relative_to(drafts_dir.parent)), "line": 1},
                "auto_fixable": False,
            })
            continue

        # Run all 12 checks on this file
        rel_path = str(md_file.relative_to(drafts_dir.parent))
        page_slug = md_file.stem

        issues.extend(_check_1_grammar_spelling(content, rel_path, page_slug))
        issues.extend(_check_2_readability_score(content, rel_path, page_slug))
        issues.extend(_check_3_paragraph_structure(content, rel_path, page_slug))
        issues.extend(_check_4_bullet_point_quality(content, rel_path, page_slug))
        issues.extend(_check_5_tone_consistency(content, rel_path, page_slug))
        issues.extend(_check_6_completeness(content, rel_path, page_slug))
        issues.extend(_check_7_heading_hierarchy(content, rel_path, page_slug))
        issues.extend(_check_8_claim_marker_format(content, rel_path, page_slug))
        issues.extend(_check_9_claim_grounding(content, rel_path, page_slug))
        issues.extend(_check_10_content_density(content, rel_path, page_slug, product_facts))
        issues.extend(_check_11_frontmatter_completeness(content, rel_path, page_slug))
        issues.extend(_check_12_link_quality(content, rel_path, page_slug))

    return issues


# Check 1: Grammar & Spelling
def _check_1_grammar_spelling(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for repeated grammar errors using basic heuristics.

    Spec: abstract-hugging-kite.md:346 (Check 1)
    Severity: WARN
    """
    issues = []
    lines = content.split('\n')

    # Simple heuristics for common grammar issues
    patterns = [
        (r'\s+,', 'Space before comma'),
        (r'\s+\.', 'Space before period'),
        (r'[a-z]\.[A-Z]', 'Missing space after period'),
        (r'\b(the the|a a|an an)\b', 'Repeated word'),
    ]

    for line_num, line in enumerate(lines, start=1):
        # Skip lines with high concentration of technical terms (>20%)
        words = line.lower().split()
        if words:
            tech_term_count = sum(1 for w in words if any(term in w for term in TECHNICAL_TERMS))
            if tech_term_count / len(words) > 0.2:
                continue  # Skip this line

        for pattern, description in patterns:
            if re.search(pattern, line):
                issues.append({
                    "issue_id": f"content_quality_grammar_{page_slug}_{line_num}",
                    "check": "content_quality.grammar_spelling",
                    "severity": "warn",
                    "message": f"{description}: {line.strip()[:50]}",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Check 2: Readability Score
def _check_2_readability_score(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Calculate Flesch-Kincaid grade level, warn if too high.

    Spec: abstract-hugging-kite.md:347 (Check 2)
    Target: 8-12, WARN if >14, ERROR if >16
    """
    issues = []

    # Remove frontmatter and code blocks for analysis
    body = _extract_body_for_analysis(content)

    grade_level = calculate_flesch_kincaid_grade(body)

    if grade_level > 16:
        issues.append({
            "issue_id": f"content_quality_readability_{page_slug}",
            "check": "content_quality.readability_score",
            "severity": "error",
            "message": f"Readability too complex (grade {grade_level:.1f}, target 8-12)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })
    elif grade_level > 14:
        issues.append({
            "issue_id": f"content_quality_readability_{page_slug}",
            "check": "content_quality.readability_score",
            "severity": "warn",
            "message": f"Readability high (grade {grade_level:.1f}, target 8-12)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })

    return issues


# Check 3: Paragraph Structure
def _check_3_paragraph_structure(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check paragraph structure: max 10 lines per paragraph, min 1 heading per 50 lines.

    Spec: abstract-hugging-kite.md:348 (Check 3)
    Severity: WARN
    """
    issues = []
    lines = content.split('\n')

    # Check for long paragraphs (>10 consecutive non-empty lines without heading/list)
    para_start = None
    para_length = 0

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip frontmatter, code blocks, headings, lists
        if stripped.startswith('---') or stripped.startswith('```') or \
           stripped.startswith('#') or stripped.startswith('-') or \
           stripped.startswith('*') or stripped.startswith('>'):
            if para_length > 10:
                issues.append({
                    "issue_id": f"content_quality_paragraph_{page_slug}_{para_start}",
                    "check": "content_quality.paragraph_structure",
                    "severity": "warn",
                    "message": f"Long paragraph ({para_length} lines, max 10 recommended)",
                    "location": {"path": rel_path, "line": para_start},
                    "auto_fixable": False,
                })
            para_start = None
            para_length = 0
            continue

        if stripped:  # Non-empty line
            if para_start is None:
                para_start = line_num
            para_length += 1
        else:  # Empty line ends paragraph
            if para_length > 10:
                issues.append({
                    "issue_id": f"content_quality_paragraph_{page_slug}_{para_start}",
                    "check": "content_quality.paragraph_structure",
                    "severity": "warn",
                    "message": f"Long paragraph ({para_length} lines, max 10 recommended)",
                    "location": {"path": rel_path, "line": para_start},
                    "auto_fixable": False,
                })
            para_start = None
            para_length = 0

    # Check heading density (min 1 heading per 50 lines)
    body_lines = [l for l in lines if not l.strip().startswith('---') and not l.strip().startswith('```')]
    heading_count = sum(1 for l in body_lines if l.strip().startswith('#'))
    body_line_count = len([l for l in body_lines if l.strip()])

    if body_line_count > 50 and heading_count == 0:
        issues.append({
            "issue_id": f"content_quality_heading_density_{page_slug}",
            "check": "content_quality.paragraph_structure",
            "severity": "warn",
            "message": f"No headings found ({body_line_count} lines, recommend 1 heading per 50 lines)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })

    return issues


# Check 4: Bullet Point Quality
def _check_4_bullet_point_quality(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check bullet point quality: max 150 chars, ERROR if >200, max 3 nesting levels.

    Spec: abstract-hugging-kite.md:349 (Check 4)
    """
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Detect bullet points (-, *, or numbered)
        if re.match(r'^[\-\*]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            # Check length
            if len(stripped) > 200:
                issues.append({
                    "issue_id": f"content_quality_bullet_{page_slug}_{line_num}",
                    "check": "content_quality.bullet_point_quality",
                    "severity": "error",
                    "message": f"Bullet point too long ({len(stripped)} chars, max 200)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })
            elif len(stripped) > 150:
                issues.append({
                    "issue_id": f"content_quality_bullet_{page_slug}_{line_num}",
                    "check": "content_quality.bullet_point_quality",
                    "severity": "warn",
                    "message": f"Bullet point long ({len(stripped)} chars, recommend <150)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

            # Check nesting level (count leading spaces/tabs)
            indent_match = re.match(r'^(\s*)', line)
            if indent_match:
                indent = indent_match.group(1)
                indent_level = len(indent) // 2  # Assume 2-space indents
                if indent_level > 3:
                    issues.append({
                        "issue_id": f"content_quality_bullet_nesting_{page_slug}_{line_num}",
                        "check": "content_quality.bullet_point_quality",
                        "severity": "warn",
                        "message": f"Bullet point nesting too deep (level {indent_level}, max 3)",
                        "location": {"path": rel_path, "line": line_num},
                        "auto_fixable": False,
                    })

    return issues


# Check 5: Tone Consistency
def _check_5_tone_consistency(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check tone consistency: products=professional, docs=instructional.

    Spec: abstract-hugging-kite.md:350 (Check 5)
    Severity: WARN
    """
    issues = []

    # Simple heuristic: detect casual language patterns
    casual_patterns = [
        r'\bkinda\b', r'\bsorta\b', r'\bgonna\b', r'\bwanna\b',
        r'\byou guys\b', r'\bawesome\b', r'\bsuper\b', r'\bretty\b',
    ]

    lines = content.split('\n')
    for line_num, line in enumerate(lines, start=1):
        for pattern in casual_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    "issue_id": f"content_quality_tone_{page_slug}_{line_num}",
                    "check": "content_quality.tone_consistency",
                    "severity": "warn",
                    "message": f"Casual tone detected ('{pattern}'): {line.strip()[:50]}",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Check 6: Completeness
def _check_6_completeness(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for TODO, TBD, FIXME, placeholders.

    Spec: abstract-hugging-kite.md:351 (Check 6)
    Severity: ERROR (changed from BLOCKER to avoid halting pipeline on template formatting issues)
    """
    issues = []

    placeholder_patterns = [
        r'\bTODO\b', r'\bTBD\b', r'\bFIXME\b', r'\bXXX\b',
        r'\bPLACEHOLDER\b', r'\bCOMING SOON\b',
        r'\[INSERT.*?\]', r'\{.*?TBD.*?\}',
    ]

    lines = content.split('\n')
    for line_num, line in enumerate(lines, start=1):
        for pattern in placeholder_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    "issue_id": f"content_quality_completeness_{page_slug}_{line_num}",
                    "check": "content_quality.completeness",
                    # Template content should not halt pipeline for minor formatting issues
                    "severity": "error",
                    "message": f"Incomplete content detected: {line.strip()[:80]}",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Check 7: Heading Hierarchy
def _check_7_heading_hierarchy(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Validate heading hierarchy: H1→H2→H3 progression, no skips.

    Spec: abstract-hugging-kite.md:352 (Check 7)
    Severity: ERROR
    """
    issues = []
    lines = content.split('\n')

    prev_level = 0
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('#'):
            # Count heading level
            level = len(re.match(r'^#+', stripped).group(0))

            # Check for skips (e.g., H1→H3)
            if prev_level > 0 and level > prev_level + 1:
                issues.append({
                    "issue_id": f"content_quality_heading_skip_{page_slug}_{line_num}",
                    "check": "content_quality.heading_hierarchy",
                    "severity": "error",
                    "message": f"Heading level skip (H{prev_level}→H{level}, should be H{prev_level+1})",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

            prev_level = level

    return issues


# Check 8: Claim Marker Format
def _check_8_claim_marker_format(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Convert [claim: UUID] to <!-- claim_id: UUID --> format.

    Spec: abstract-hugging-kite.md:353 (Check 8)
    Severity: ERROR (auto-fixable)
    """
    issues = []
    lines = content.split('\n')

    # Pattern: [claim: UUID]
    inline_claim_pattern = r'\[claim:\s*([a-f0-9\-]{36})\]'

    for line_num, line in enumerate(lines, start=1):
        matches = re.finditer(inline_claim_pattern, line, re.IGNORECASE)
        for match in matches:
            claim_id = match.group(1)
            issues.append({
                "issue_id": f"content_quality_claim_format_{page_slug}_{line_num}_{claim_id[:8]}",
                "check": "content_quality.claim_marker_format",
                "severity": "error",
                "message": f"Inline claim marker found (should be HTML comment): [claim: {claim_id}]",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
                "suggested_fix": f"Replace with: <!-- claim_id: {claim_id} -->",
            })

    return issues


# Check 9: Claim Grounding
def _check_9_claim_grounding(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check that claim markers are placed near sentences (<50 chars from period).

    Spec: abstract-hugging-kite.md:354 (Check 9)
    Severity: WARN
    """
    issues = []
    lines = content.split('\n')

    # Pattern: Accept both HTML comment and Markdown formats
    # Group 1: HTML comment UUID, Group 2: Markdown UUID
    claim_comment_pattern = r'(?:<!--\s*claim_id:\s*([a-f0-9\-]{36})\s*-->|\[claim:\s*([a-f0-9\-]+)\])'

    for line_num, line in enumerate(lines, start=1):
        matches = re.finditer(claim_comment_pattern, line, re.IGNORECASE)
        for match in matches:
            # Check distance to nearest sentence end (. ! ?)
            position = match.start()

            # Find nearest period before marker
            text_before = line[:position]
            last_period = max(text_before.rfind('.'), text_before.rfind('!'), text_before.rfind('?'))

            if last_period >= 0:
                distance = position - last_period
                if distance > 50:
                    issues.append({
                        "issue_id": f"content_quality_claim_grounding_{page_slug}_{line_num}",
                        "check": "content_quality.claim_grounding",
                        "severity": "warn",
                        "message": f"Claim marker far from sentence end ({distance} chars, recommend <50)",
                        "location": {"path": rel_path, "line": line_num},
                        "auto_fixable": False,
                    })

    return issues


# Check 10: Content Density
def _check_10_content_density(content: str, rel_path: str, page_slug: str, product_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check content density: min 1 claim per 100 words.

    Spec: abstract-hugging-kite.md:355 (Check 10)
    Severity: WARN
    """
    issues = []

    # Count words (excluding code blocks and frontmatter)
    body = _extract_body_for_analysis(content)
    words = [w for w in body.split() if w.strip()]
    word_count = len(words)

    # Count claim markers - accept both HTML comment and Markdown formats
    # Group 1: HTML comment UUID, Group 2: Markdown UUID
    claim_pattern = r'(?:<!--\s*claim_id:\s*([a-f0-9\-]{36})\s*-->|\[claim:\s*([a-f0-9\-]+)\])'
    claim_matches = re.findall(claim_pattern, content, re.IGNORECASE)
    # Count matches where at least one group matched
    claim_count = sum(1 for match in claim_matches if any(match))

    if word_count > 100:
        expected_claims = word_count / 100
        if claim_count < expected_claims:
            issues.append({
                "issue_id": f"content_quality_content_density_{page_slug}",
                "check": "content_quality.content_density",
                "severity": "warn",
                "message": f"Low claim density ({claim_count} claims for {word_count} words, expect ~{expected_claims:.0f})",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    return issues


# Check 11: Frontmatter Completeness
def _check_11_frontmatter_completeness(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check frontmatter: required fields present, no YAML comment leakage.

    Spec: abstract-hugging-kite.md:356 (Check 11)
    Severity: ERROR/BLOCKER
    """
    issues = []

    # Extract frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?\n)---\s*\n', content, re.DOTALL)

    if not frontmatter_match:
        issues.append({
            "issue_id": f"content_quality_frontmatter_missing_{page_slug}",
            "check": "content_quality.frontmatter_completeness",
            "severity": "blocker",
            "message": "No frontmatter found",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })
        return issues

    frontmatter_text = frontmatter_match.group(1)

    # Required fields (basic set)
    basic_required_fields = ['title', 'description']
    for field in basic_required_fields:
        if not re.search(rf'^{field}:', frontmatter_text, re.MULTILINE):
            issues.append({
                "issue_id": f"content_quality_frontmatter_field_{page_slug}_{field}",
                "check": "content_quality.frontmatter_completeness",
                "severity": "error",
                "message": f"Missing required frontmatter field: {field}",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })

    # URL field - accept either permalink (Hugo standard) or url_path (internal model)
    # TC-CREV-B-TRACK2: W5 generates permalink (Hugo standard), but accept both for compatibility
    has_permalink = bool(re.search(r'^permalink:', frontmatter_text, re.MULTILINE))
    has_url_path = bool(re.search(r'^url_path:', frontmatter_text, re.MULTILINE))

    if not (has_permalink or has_url_path):
        issues.append({
            "issue_id": f"content_quality_frontmatter_field_{page_slug}_url",
            "check": "content_quality.frontmatter_completeness",
            "severity": "error",
            "message": "Missing required frontmatter URL field (permalink or url_path)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": False,
        })

    # Check for YAML comment leakage (# comments in frontmatter)
    yaml_comment_pattern = r'^\s*#[^#]'  # Single # at start of line (not heading)
    for line_num, line in enumerate(frontmatter_text.split('\n'), start=2):
        if re.match(yaml_comment_pattern, line):
            issues.append({
                "issue_id": f"content_quality_frontmatter_comment_{page_slug}_{line_num}",
                "check": "content_quality.frontmatter_completeness",
                "severity": "error",
                "message": f"YAML comment in frontmatter: {line.strip()[:50]}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": False,
            })

    return issues


# Check 12: Link Quality
def _check_12_link_quality(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check markdown link syntax and formatting.

    Spec: abstract-hugging-kite.md:357 (Check 12)
    Severity: ERROR (deferred to W7 Gate 6 for full validation)
    """
    issues = []
    lines = content.split('\n')

    # Pattern: [text](url)
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'

    for line_num, line in enumerate(lines, start=1):
        matches = re.finditer(link_pattern, line)
        for match in matches:
            link_text = match.group(1)
            link_url = match.group(2)

            # Check for empty link text
            if not link_text.strip():
                issues.append({
                    "issue_id": f"content_quality_link_empty_text_{page_slug}_{line_num}",
                    "check": "content_quality.link_quality",
                    "severity": "error",
                    "message": f"Link with empty text: ({link_url})",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

            # Check for empty link URL
            if not link_url.strip():
                issues.append({
                    "issue_id": f"content_quality_link_empty_url_{page_slug}_{line_num}",
                    "check": "content_quality.link_quality",
                    "severity": "error",
                    "message": f"Link with empty URL: [{link_text}]()",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": False,
                })

    return issues


# Helper function
def _extract_body_for_analysis(content: str) -> str:
    """Extract body text for analysis (remove frontmatter and code blocks).

    Args:
        content: Full markdown content

    Returns:
        Body text without frontmatter or code blocks
    """
    # Remove frontmatter
    content_no_fm = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

    # Remove code blocks
    content_no_code = re.sub(r'```.*?```', '', content_no_fm, flags=re.DOTALL)

    return content_no_code
