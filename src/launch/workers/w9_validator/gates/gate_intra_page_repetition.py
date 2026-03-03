"""Gate G2: Intra-Page Repetition (TC-3670, TC-3688).

Detects near-duplicate paragraphs within a single markdown file.
Uses deterministic Jaccard similarity on word-level token sets.

TC-3688: Also detects section-level repetition — H2-delimited content
blocks compared at a lower threshold (0.50) with ``warning`` severity.
This catches cases where entire sections repeat similar content but no
single paragraph pair crosses the paragraph-level threshold.

Grounded in pilot review evidence: same facts repeated 3-8x per file
(e.g., feature.md repeats Border class + NumberFormat between sections,
api-overview.md repeats same 5 facts in every section).

Always-error severity for paragraphs; warning for sections.

Spec: specs/09_validation_gates.md - Quality Content Gates (G2)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Minimum paragraph length (words) to consider for repetition check.
# Short paragraphs (< 15 words) are too small for meaningful similarity.
_MIN_PARAGRAPH_WORDS = 15

# Jaccard similarity threshold above which two paragraphs are "near-duplicate".
_SIMILARITY_THRESHOLD = 0.65

# TC-3688: Section-level thresholds
_SECTION_SIMILARITY_THRESHOLD = 0.50
_MIN_SECTION_WORDS = 30
_MAX_SECTIONS_PER_FILE = 30

# Max paragraphs to compare per file (O(n^2) guard).
_MAX_PARAGRAPHS_PER_FILE = 80

# Max repetition issues per file.
_MAX_ISSUES_PER_FILE = 10

# Tokenizer: split on non-alphanumeric, lowercase.
_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute intra-page repetition detection gate.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, list_of_issues).
    """
    issues: List[Dict[str, Any]] = []

    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))
    if not md_files:
        return True, []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        file_issues = _scan_file(content, md_file)
        issues.extend(file_issues)

    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _tokenize(text: str) -> Set[str]:
    """Extract lowercase word tokens from text."""
    return set(_WORD_RE.findall(text.lower()))


def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union


def _extract_paragraphs(
    content: str,
) -> List[Tuple[int, str]]:
    """Extract paragraphs from markdown, skipping code fences and frontmatter.

    Returns list of (start_line_number, paragraph_text) tuples.
    """
    lines = content.splitlines()
    paragraphs: List[Tuple[int, str]] = []
    in_fence = False
    in_frontmatter = False
    current_para_lines: List[str] = []
    current_para_start = 0

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Frontmatter detection (first --- ... --- block)
        if line_num == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # Code fence tracking
        if stripped.startswith("```"):
            in_fence = not in_fence
            # Flush current paragraph before fence
            if current_para_lines:
                para_text = " ".join(current_para_lines)
                paragraphs.append((current_para_start, para_text))
                current_para_lines = []
            continue

        if in_fence:
            continue

        # Skip headings (they're structural, not content)
        if stripped.startswith("#"):
            if current_para_lines:
                para_text = " ".join(current_para_lines)
                paragraphs.append((current_para_start, para_text))
                current_para_lines = []
            continue

        # Empty line = paragraph boundary
        if not stripped:
            if current_para_lines:
                para_text = " ".join(current_para_lines)
                paragraphs.append((current_para_start, para_text))
                current_para_lines = []
            continue

        # Accumulate paragraph
        if not current_para_lines:
            current_para_start = line_num
        current_para_lines.append(stripped)

    # Flush remaining
    if current_para_lines:
        para_text = " ".join(current_para_lines)
        paragraphs.append((current_para_start, para_text))

    return paragraphs


def _scan_file(content: str, md_file: Path) -> List[Dict[str, Any]]:
    """Scan a single file for near-duplicate paragraphs and sections."""
    file_issues: List[Dict[str, Any]] = []

    # --- Paragraph-level repetition (original G2) ---
    paragraphs = _extract_paragraphs(content)

    # Filter to paragraphs with enough words
    substantive = [
        (line_num, text, _tokenize(text))
        for line_num, text in paragraphs
        if len(text.split()) >= _MIN_PARAGRAPH_WORDS
    ]

    # Cap to avoid O(n^2) explosion
    substantive = substantive[:_MAX_PARAGRAPHS_PER_FILE]

    # Track already-reported pairs to avoid duplicates
    reported: set = set()

    for i in range(len(substantive)):
        if len(file_issues) >= _MAX_ISSUES_PER_FILE:
            break

        line_a, text_a, tokens_a = substantive[i]

        for j in range(i + 1, len(substantive)):
            if len(file_issues) >= _MAX_ISSUES_PER_FILE:
                break

            line_b, text_b, tokens_b = substantive[j]

            # Deterministic pair key
            pair_key = (line_a, line_b)
            if pair_key in reported:
                continue

            sim = _jaccard_similarity(tokens_a, tokens_b)
            if sim >= _SIMILARITY_THRESHOLD:
                reported.add(pair_key)
                file_issues.append({
                    "issue_id": f"g2_repetition_{md_file.stem}_{line_a}_{line_b}",
                    "gate": "gate_intra_page_repetition",
                    "severity": "error",
                    "message": (
                        f"Near-duplicate paragraphs (Jaccard={sim:.2f}): "
                        f"lines {line_a} and {line_b}"
                    ),
                    "error_code": "G2_INTRA_PAGE_REPEAT",
                    "location": {
                        "path": str(md_file),
                        "line": line_a,
                        "related_line": line_b,
                    },
                    "status": "OPEN",
                })

    # --- TC-3688: Section-level repetition ---
    section_issues = _scan_sections(content, md_file)
    file_issues.extend(section_issues)

    return file_issues


def _extract_sections(content: str) -> List[Tuple[int, str, str]]:
    """Extract H2 sections from markdown, skipping code fences and frontmatter.

    Returns list of (start_line, heading_text, section_body) tuples.
    Each section_body contains all text between this H2 and the next H2
    (excluding code fences and sub-headings).
    """
    lines = content.splitlines()
    sections: List[Tuple[int, str, List[str]]] = []
    in_fence = False
    in_frontmatter = False
    current_heading = ""
    current_start = 0
    current_body: List[str] = []

    h2_re = re.compile(r"^##\s+(.+)$")

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Frontmatter detection
        if line_num == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # Code fence tracking
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # H2 heading starts a new section
        m = h2_re.match(stripped)
        if m and not stripped.startswith("###"):
            # Flush previous section
            if current_heading:
                sections.append((current_start, current_heading, current_body))
            current_heading = m.group(1).strip()
            current_start = line_num
            current_body = []
            continue

        # Skip sub-headings (H3+)
        if stripped.startswith("#"):
            continue

        # Accumulate body text (non-empty lines)
        if stripped and current_heading:
            current_body.append(stripped)

    # Flush last section
    if current_heading:
        sections.append((current_start, current_heading, current_body))

    return [
        (start, heading, " ".join(body))
        for start, heading, body in sections
    ]


def _scan_sections(content: str, md_file: Path) -> List[Dict[str, Any]]:
    """Scan a single file for near-duplicate H2 sections (TC-3688)."""
    section_issues: List[Dict[str, Any]] = []

    sections = _extract_sections(content)

    # Filter to sections with enough words
    substantive = [
        (line_num, heading, text, _tokenize(text))
        for line_num, heading, text in sections
        if len(text.split()) >= _MIN_SECTION_WORDS
    ]

    # Cap
    substantive = substantive[:_MAX_SECTIONS_PER_FILE]

    reported: set = set()

    for i in range(len(substantive)):
        if len(section_issues) >= _MAX_ISSUES_PER_FILE:
            break

        line_a, heading_a, _, tokens_a = substantive[i]

        for j in range(i + 1, len(substantive)):
            if len(section_issues) >= _MAX_ISSUES_PER_FILE:
                break

            line_b, heading_b, _, tokens_b = substantive[j]

            pair_key = (line_a, line_b)
            if pair_key in reported:
                continue

            sim = _jaccard_similarity(tokens_a, tokens_b)
            if sim >= _SECTION_SIMILARITY_THRESHOLD:
                reported.add(pair_key)
                section_issues.append({
                    "issue_id": f"g2_section_{md_file.stem}_{line_a}_{line_b}",
                    "gate": "gate_intra_page_repetition",
                    "severity": "warning",
                    "message": (
                        f"Near-duplicate sections (Jaccard={sim:.2f}): "
                        f"'{heading_a}' (line {line_a}) and "
                        f"'{heading_b}' (line {line_b})"
                    ),
                    "error_code": "G2_SECTION_LEVEL_REPEAT",
                    "location": {
                        "path": str(md_file),
                        "line": line_a,
                        "related_line": line_b,
                    },
                    "status": "OPEN",
                })

    return section_issues
