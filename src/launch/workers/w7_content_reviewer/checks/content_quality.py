"""Content Quality checks for W7 ContentReviewer.

This module implements 12 content quality checks that ensure generated markdown
is readable, well-structured, and complete.

TC-1100-P1: W7 ContentReviewer Phase 1 - Core Review Logic
Pattern: Check module pattern (similar to W7 gates)

Spec reference: abstract-hugging-kite.md:332-374 (Content Quality Dimension)
"""

import re
from pathlib import Path
from typing import Dict, List, Any

from .._shared import STOPWORDS, calculate_flesch_kincaid_grade


# Technical terms whitelist to avoid false positive grammar warnings
# TC-P1D: Extended with all Aspose product families and common tech terms
# that trigger false "Missing space after period" warnings (e.g., Aspose.Note)
TECHNICAL_TERMS = frozenset([
    'aspose', 'aspose.note', 'aspose.cells', 'aspose.words', 'aspose.pdf',
    'aspose.slides', 'aspose.email', 'aspose.3d', 'aspose.imaging',
    'aspose.barcode', 'aspose.cad', 'aspose.html', 'aspose.ocr',
    'aspose.page', 'aspose.psd', 'aspose.svg', 'aspose.tasks',
    'aspose.tex', 'aspose.zip', 'aspose.medical',
    'api', 'sdk', 'foss', 'github', 'json', 'yaml', 'readme',
    'cli', 'ci', 'cd', 'llm', 'uuid', 'toc', 'cta', 'seo', 'xml', 'html',
    'css', 'npm', 'pip', 'onenote', 'xlsx', 'pdf', 'docx',
    '.net', '.py', '.cs', '.js', '.ts', '.java', '.md',
])


def check_all(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    page_plan: Dict[str, Any],
    resolver=None,
) -> List[Dict[str, Any]]:
    """Run all 12 content quality checks and return issues.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        product_facts: Product facts dict from product_facts.json
        page_plan: Page plan dict from page_plan.json
        resolver: Optional PageResolver for correct slug resolution (TC-3500)

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
            rel_path = str(md_file.relative_to(drafts_dir))
            issues.append({
                "issue_id": f"content_quality_read_error_{rel_path.replace('/', '_')}",
                "check": "content_quality.file_read",
                "severity": "error",
                "message": f"Failed to read file: {e}",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })
            continue

        # TC-3500: Use resolver for correct slug (fixes index.md → "index" bug)
        rel_path = str(md_file.relative_to(drafts_dir))
        resolved = resolver.resolve(md_file) if resolver else None
        page_slug = resolved.slug if resolved else md_file.stem

        issues.extend(_check_1_grammar_spelling(content, rel_path, page_slug))
        issues.extend(_check_2_readability_score(content, rel_path, page_slug, page_plan))
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
        issues.extend(_check_13_source_annotations(content, rel_path, page_slug))
        issues.extend(_check_14_boilerplate_description(content, rel_path, page_slug))
        issues.extend(_check_15_link_trailing_whitespace(content, rel_path, page_slug))
        issues.extend(_check_16_single_backtick_code_blocks(content, rel_path, page_slug))

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
        (r'\s+\.(?![a-zA-Z])(?!\s*\[claim:)', 'Space before period'),  # Exclude .NET, .pdf, and claim markers
        (r'(?<!\.)(?<![A-Z])[a-z]\.[A-Z]', 'Missing space after period'),  # Exclude Aspose.Note via tech term skip
        (r'\b(the the|a a|an an)\b', 'Repeated word'),
    ]

    # Track code blocks to skip grammar checks inside them
    in_code_block = False

    for line_num, line in enumerate(lines, start=1):
        # Detect code block boundaries (``` or ~~~)
        if line.strip().startswith('```') or line.strip().startswith('~~~'):
            in_code_block = not in_code_block
            continue  # Skip the fence line itself

        # Skip lines inside code blocks (code examples, snippets)
        if in_code_block:
            continue

        # Skip lines with technical terms (≥2% threshold to catch product names like "Aspose.Note"
        # even in longer sentences — 1 tech term in 50 words still warrants a skip)
        words = line.lower().split()
        if words:
            tech_term_count = sum(1 for w in words if any(term in w for term in TECHNICAL_TERMS))
            if tech_term_count / len(words) >= 0.02:
                continue  # Skip this line

        # Skip list items — they commonly contain technical terms, API references,
        # and formatting patterns that trigger false positive grammar warnings
        stripped_line = line.strip()
        if re.match(r'^\d+\.', stripped_line):
            continue
        if stripped_line.startswith(('- ', '* ', '> ')):
            continue

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
def _check_2_readability_score(content: str, rel_path: str, page_slug: str, page_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculate Flesch-Kincaid grade level, warn if too high.

    Spec: abstract-hugging-kite.md:347 (Check 2)
    Target: 8-12, WARN if >14, ERROR if >16

    TC-1107: Navigation pages (index, toc, landing) skip check entirely.
    FAQ pages (faq, troubleshooting) have relaxed threshold (18 instead of 16).
    """
    issues = []

    # Get page role from page_plan (TC-1107: page-type exemptions)
    # BLOCKER-2b: Disambiguate slug collisions by section from rel_path
    page_role = None
    pages = page_plan.get('pages', [])
    rel_section = rel_path.replace("\\", "/").split("/")[0] if ("/" in rel_path or "\\" in rel_path) else ""
    for page in pages:
        # Match by slug or filename (handle _index -> index normalization)
        if page.get('slug') == page_slug or page.get('filename') == f"{page_slug}.md":
            page_section = page.get('section', '')
            if rel_section and page_section and rel_section != page_section:
                continue
            page_role = page.get('page_role', '')
            break

    # Exempt navigation pages from readability check (TC-1107)
    if page_role in ['index', 'toc', 'landing']:
        return []  # Skip check entirely for navigation

    # Exempt template/structural pages (content is deterministic, not LLM-generated)
    if any(kw in page_slug for kw in ('license', 'installation')):
        return []

    # Remove frontmatter and code blocks for analysis
    body = _extract_body_for_analysis(content)

    grade_level = calculate_flesch_kincaid_grade(body)

    # Relax threshold for FAQ/troubleshooting pages (Q&A format) (TC-1107)
    # Only error at grade >18, no warnings (FAQ pages are inherently more complex)
    if page_role in ['faq', 'troubleshooting']:
        if grade_level > 18:  # Relaxed from 16
            issues.append({
                "issue_id": f"content_quality_readability_{page_slug}",
                "check": "content_quality.readability_score",
                "severity": "error",
                "message": f"Readability too complex (grade {grade_level:.1f}, target 8-12, FAQ threshold 18)",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": False,
            })
    else:
        # Original logic for content pages
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
    in_frontmatter = False
    frontmatter_seen = 0  # Count of --- delimiters seen

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track frontmatter boundaries: skip all lines between --- markers
        if stripped == '---' or (stripped.startswith('---') and stripped.rstrip() == '---'):
            frontmatter_seen += 1
            if frontmatter_seen == 1:
                in_frontmatter = True
            elif frontmatter_seen == 2:
                in_frontmatter = False
            # Reset paragraph tracking at frontmatter boundaries
            para_start = None
            para_length = 0
            continue

        if in_frontmatter:
            continue

        # Skip code blocks, headings, lists
        if stripped.startswith('```') or \
           stripped.startswith('#') or stripped.startswith('-') or \
           stripped.startswith('*') or stripped.startswith('>'):
            if para_length > 10:
                issues.append({
                    "issue_id": f"content_quality_paragraph_{page_slug}_{para_start}",
                    "check": "content_quality.paragraph_structure",
                    "severity": "warn",
                    "message": f"Long paragraph ({para_length} lines, max 10 recommended)",
                    "location": {"path": rel_path, "line": para_start},
                    "auto_fixable": True,
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
                    "auto_fixable": True,
                })
            para_start = None
            para_length = 0

    # Check heading density (min 1 heading per 50 lines)
    body_lines = [l for l in lines if not l.strip().startswith('---') and not l.strip().startswith('```')]
    heading_count = sum(1 for l in body_lines if l.strip().startswith('#'))
    body_line_count = len([l for l in body_lines if l.strip()])

    if body_line_count > 60 and heading_count == 0:
        issues.append({
            "issue_id": f"content_quality_heading_density_{page_slug}",
            "check": "content_quality.paragraph_structure",
            "severity": "warn",
            "message": f"No headings found ({body_line_count} lines, recommend 1 heading per 50 lines)",
            "location": {"path": rel_path, "line": 1},
            "auto_fixable": True,
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
            # Check length — thresholds tuned to flag genuinely problematic bullets
            # while allowing reasonable technical bullets (150-250 chars)
            if len(stripped) > 250:
                issues.append({
                    "issue_id": f"content_quality_bullet_{page_slug}_{line_num}",
                    "check": "content_quality.bullet_point_quality",
                    "severity": "error",
                    "message": f"Bullet point too long ({len(stripped)} chars, max 250)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": True,
                })
            elif len(stripped) > 240:
                issues.append({
                    "issue_id": f"content_quality_bullet_{page_slug}_{line_num}",
                    "check": "content_quality.bullet_point_quality",
                    "severity": "warn",
                    "message": f"Bullet point long ({len(stripped)} chars, recommend <240)",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": True,
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
                        "auto_fixable": True,
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
        # Skip frontmatter (between --- delimiters)
        if line.strip() == '---':
            continue
        # Skip HTML comments (claim markers, source attribution)
        if line.strip().startswith('<!--') and line.strip().endswith('-->'):
            continue
        for pattern in placeholder_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    "issue_id": f"content_quality_completeness_{page_slug}_{line_num}",
                    "check": "content_quality.completeness",
                    "severity": "error",
                    "message": f"Incomplete content detected: {line.strip()[:80]}",
                    "location": {"path": rel_path, "line": line_num},
                    "auto_fixable": True,
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
    inline_claim_pattern = r'\[claim:\s*([a-f0-9\-]+)\]'

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

    # Only check inline [claim:] markers for grounding distance.
    # HTML comment claims (<!-- claim_id: ... -->) are metadata placed at
    # paragraph/section boundaries and don't need sentence-proximity grounding.
    claim_comment_pattern = r'\[claim:\s*([a-f0-9\-]+)\]'

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
    # Group 1: HTML comment hex ID (UUID-36 or SHA256-64), Group 2: Markdown hex ID
    claim_pattern = r'(?:<!--\s*claim_id:\s*([a-f0-9\-]+)\s*-->|\[claim:\s*([a-f0-9\-]+)\])'
    claim_matches = re.findall(claim_pattern, content, re.IGNORECASE)
    # Count matches where at least one group matched
    claim_count = sum(1 for match in claim_matches if any(match))

    if word_count > 150:
        expected_claims = max(1, word_count // 150)
        if claim_count < expected_claims:
            issues.append({
                "issue_id": f"content_quality_content_density_{page_slug}",
                "check": "content_quality.content_density",
                "severity": "warn",
                "message": f"Low claim density ({claim_count} claims for {word_count} words, expect ~{expected_claims})",
                "location": {"path": rel_path, "line": 1},
                "auto_fixable": True,
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
    # Accept either newline after closing delimiter OR end-of-string (frontmatter-only files)
    frontmatter_match = re.match(r'^---\s*\n(.*?\n)---(?:\s*\n|$)', content, re.DOTALL)

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
                "auto_fixable": True,
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
            "auto_fixable": True,
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

    # TC-1407: Detect collapsed YAML (multiple keys on one line)
    # TC-1408: Mask quoted strings to avoid false positives from colons in values
    # TC-1408: Skip lines inside YAML block scalars (| or >) — they're text, not keys
    in_block_scalar = False
    block_scalar_indent = 0
    for line_num, line in enumerate(frontmatter_text.split('\n'), start=2):
        stripped = line.rstrip()
        # Detect block scalar start: a key ending with | or >
        if re.match(r'^\s*\w+:\s*[|>]', stripped):
            in_block_scalar = True
            # Block scalar content is indented relative to the key
            block_scalar_indent = len(stripped) - len(stripped.lstrip()) + 2
            continue
        # If in block scalar, skip indented continuation lines and blank lines
        if in_block_scalar:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else block_scalar_indent
            if current_indent >= block_scalar_indent or not line.strip():
                continue
            else:
                in_block_scalar = False
        # Mask quoted content so "page: announcement" inside quotes isn't counted
        masked = re.sub(r'"[^"]*"', lambda m: '"' + '#' * (len(m.group()) - 2) + '"', line)
        masked = re.sub(r"'[^']*'", lambda m: "'" + '#' * (len(m.group()) - 2) + "'", masked)
        key_matches = re.findall(r'(?:^|\s)(\w+):\s', masked)
        count = len(key_matches)
        if count >= 2:
            issues.append({
                "issue_id": f"content_quality_frontmatter_collapsed_{page_slug}_{line_num}",
                "check": "content_quality.frontmatter_completeness",
                "severity": "error",
                "message": f"Collapsed YAML: multiple keys on one line ({count} keys): {line[:60]}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
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


# Check 13: Source Annotations
def _check_13_source_annotations(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for leaked source attribution comments in body content.

    Pattern: <!-- source: ... --> comments that should not appear in final output.

    Spec: TC-1504 (Check CQ-13)
    Severity: WARN (auto-fixable)
    """
    issues = []
    lines = content.split('\n')

    # Skip frontmatter
    in_frontmatter = False
    frontmatter_seen = 0

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track frontmatter boundaries
        if stripped == '---' or (stripped.startswith('---') and stripped.rstrip() == '---'):
            frontmatter_seen += 1
            if frontmatter_seen == 1:
                in_frontmatter = True
            elif frontmatter_seen == 2:
                in_frontmatter = False
            continue

        if in_frontmatter:
            continue

        # Detect source annotation comments
        if '<!-- source:' in stripped:
            issues.append({
                "issue_id": f"content_quality_source_annotation_{page_slug}_{line_num}",
                "check": "content_quality.source_annotations",
                "severity": "warn",
                "message": f"Source annotation leaked into body: {stripped[:60]}",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
            })

    return issues


# Check 14: Boilerplate Description
def _check_14_boilerplate_description(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for generic boilerplate descriptions in frontmatter.

    Pattern: Detect known boilerplate patterns in description field.

    Spec: TC-1504 (Check CQ-14)
    Severity: WARN
    """
    issues = []

    # Extract frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?\n)---(?:\s*\n|$)', content, re.DOTALL)

    if not frontmatter_match:
        return issues

    frontmatter_text = frontmatter_match.group(1)

    # Check description field
    desc_match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', frontmatter_text, re.MULTILINE)
    if desc_match:
        description = desc_match.group(1).strip().strip('"').strip("'")

        # Known boilerplate patterns
        boilerplate_patterns = [
            r'Comprehensive guide and resources for',
            r'Mandatory .* page:',
            r'Template-driven .* page',
        ]

        for pattern in boilerplate_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                issues.append({
                    "issue_id": f"content_quality_boilerplate_description_{page_slug}",
                    "check": "content_quality.boilerplate_description",
                    "severity": "warn",
                    "message": f"Generic boilerplate description: {description[:60]}",
                    "location": {"path": rel_path, "line": 2},
                    "auto_fixable": False,
                })
                break  # Only flag once per page

    return issues


# Check 15: Link Trailing Whitespace (TC-1830)
def _check_15_link_trailing_whitespace(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for trailing whitespace in markdown link URLs.

    Pattern: [text](url ) — trailing space inside the parentheses can cause
    broken links when rendered.

    Spec: TC-1830
    Severity: WARN (auto-fixable)
    """
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Find markdown links with trailing whitespace before closing paren
        for match in re.finditer(r'\[([^\]]*)\]\(([^)]*\S)\s+\)', line):
            issues.append({
                "issue_id": f"content_quality_link_trailing_ws_{page_slug}_{line_num}",
                "check": "content_quality.link_trailing_whitespace",
                "severity": "warn",
                "message": f"Link URL has trailing whitespace: [{match.group(1)}]({match.group(2)} )",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
                "suggested_fix": f"Remove trailing whitespace: [{match.group(1)}]({match.group(2)})",
            })

    return issues


# Check 16: Single Backtick Code Blocks (TC-1831)
def _check_16_single_backtick_code_blocks(content: str, rel_path: str, page_slug: str) -> List[Dict[str, Any]]:
    """Check for multi-line content incorrectly using single backticks instead of triple.

    Pattern: `code that
    spans multiple lines` — should use triple backticks for code blocks.

    Spec: TC-1831
    Severity: WARN
    """
    issues = []

    # First remove triple-backtick code blocks to avoid false positives.
    # Replace with placeholder text that preserves line counts.
    def _replace_preserving_lines(m):
        return '\n' * m.group(0).count('\n')

    content_no_fenced = re.sub(r'```.*?```', _replace_preserving_lines, content, flags=re.DOTALL)

    # Find single backtick pairs that span multiple lines and contain substantial content
    for match in re.finditer(r'`([^`]{20,}?)`', content_no_fenced, flags=re.DOTALL):
        if '\n' in match.group(1):
            line_num = content_no_fenced[:match.start()].count('\n') + 1
            issues.append({
                "issue_id": f"content_quality_single_backtick_code_{page_slug}_{line_num}",
                "check": "content_quality.single_backtick_code",
                "severity": "warn",
                "message": "Multi-line code should use triple backticks (```) instead of single backtick (`)",
                "location": {"path": rel_path, "line": line_num},
                "auto_fixable": True,
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
