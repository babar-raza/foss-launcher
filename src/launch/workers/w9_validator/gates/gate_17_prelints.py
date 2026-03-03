"""Deterministic pre-lints for Gate 17 FQ defect codes.

Handles FQ-1, FQ-2, FQ-4, FQ-5, FQ-6, FQ-7a, FQ-8, FQ-9 via regex.
FQ-3 (truncated) and FQ-7b (narrative flow) require LLM -- not handled here.

TC-2522: FQ-7 split into FQ-7a (deterministic heading hierarchy) and
FQ-7b (LLM narrative flow, handled in gate_17_formatting_quality.py).
TC-2892: FQ-8 adjacent same-language fence detection (safety net for merger).
TC-2893: FQ-9 limitations dump-shape detection (anti-dump guardrail).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from launch.workers._shared.content_sanitizer import validate_heading_hierarchy


# CommonMark: a fence closes ONLY when the line contains backticks + optional
# whitespace and NO info string (e.g. "```" or "````" but NOT "```python").
# Using this for all fence-tracking loops prevents false-positive FQ-1 reports
# for code inside ```python blocks. (TC-3629)
_FENCE_CLOSER_RE = re.compile(r"^```+\s*$")

# FQ-1: Code patterns outside fences
_CODE_PATTERNS = re.compile(
    r"^(?:import |from .+ import |def |class |    (?:def |class |return |if |for |while )|"
    r"(?:self|cls)\.|print\(|raise |try:|except |with )",
    re.MULTILINE,
)

# FQ-2: FAQ concat (answer text immediately before ### Q:)
_FAQ_CONCAT_RE = re.compile(r"\S[^\n]*###\s+Q:", re.MULTILINE)

# FQ-4: Double heading (heading + text on same line without newline)
_DOUBLE_HEADING_RE = re.compile(r"^(#{1,6}\s+.+?)(#{1,6}\s+)", re.MULTILINE)

# FQ-5: Keywords with colons (in frontmatter)
_KEYWORD_COLON_RE = re.compile(r':\s*$|:\s+"')

# FQ-6: Claim comments in body
_CLAIM_COMMENT_RE = re.compile(r"<!--\s*claim:\s*[a-zA-Z0-9_-]+\s*-->")

# FQ-9: Limitations dump-shape detection (TC-2893)
FQ9_MAX_BULLETS = 10   # MAX_CURATED_BULLETS (6) + 4 buffer
FQ9_MAX_LINE_LEN = 220  # MAX_BULLET_LEN (170) + 50 buffer

_FQ9_SECTION_RE = re.compile(r'^##\s+(?:Known\s+)?Limitations\s*$', re.MULTILINE)

_FQ9_DUMP_INDICATORS = re.compile(
    r"(?:"
    r"claim_text[:\s]"                    # raw claim field name
    r'|"claim_id"'                        # JSON claim ID key
    r"|evidence_score"                    # pipeline internal key
    r"|/[\w./]+\.py\b"                    # Unix file path
    r"|\\[\w\\]+\.py\b"                   # Windows file path
    r"|^\s*-\s*[\[{]"                     # bullet starting with JSON array/object
    r"|^\s*-\s*import\s+\w+"              # bullet with import statement
    r"|^\s*-\s*def\s+\w+\("              # bullet with function definition
    r"|^\s*-\s*class\s+\w+"              # bullet with class definition
    r"|^\s*-\s*from\s+\w+.*import"        # bullet with from...import
    r")",
    re.MULTILINE,
)


def lint_fq1_naked_code(content: str, path: Path) -> List[Dict]:
    """Detect code-like lines outside code fences."""
    issues = []
    in_fence = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            if in_fence:
                # CommonMark: only a bare ``` (no info string) closes a fence
                if _FENCE_CLOSER_RE.match(stripped):
                    in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            continue
        if _CODE_PATTERNS.match(line):
            issues.append({
                "issue_id": f"gate17_fq1_{path.stem}_{lineno}",
                "gate": "gate_17_formatting_quality",
                "severity": "error",
                "error_code": "G17-FQ-1",
                "message": f"Code outside fence at line {lineno}: {stripped[:60]}",
                "location": {"path": str(path), "line": lineno},
                "status": "OPEN",
            })
    return issues


def lint_fq2_faq_concat(content: str, path: Path) -> List[Dict]:
    """Detect ### Q: on same line as preceding answer."""
    issues = []
    for m in _FAQ_CONCAT_RE.finditer(content):
        lineno = content[:m.start()].count("\n") + 1
        issues.append({
            "issue_id": f"gate17_fq2_{path.stem}_{lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "warn",
            "error_code": "G17-FQ-2",
            "message": f"FAQ answer and question concatenated at line {lineno}",
            "location": {"path": str(path), "line": lineno},
            "status": "OPEN",
        })
    return issues


def lint_fq4_double_heading(content: str, path: Path) -> List[Dict]:
    """Detect heading-in-heading (two headings on same line).

    Skips lines inside code fences to avoid false positives from Python
    comment lines like ``# text# more text`` inside fenced code blocks.
    """
    issues = []
    # Build a set of line numbers that are inside code fences
    in_fence_lines: set = set()
    in_fence = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            if in_fence:
                if _FENCE_CLOSER_RE.match(stripped):
                    in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            in_fence_lines.add(lineno)

    for m in _DOUBLE_HEADING_RE.finditer(content):
        lineno = content[:m.start()].count("\n") + 1
        if lineno in in_fence_lines:
            continue  # skip: inside a code fence
        issues.append({
            "issue_id": f"gate17_fq4_{path.stem}_{lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-4",
            "message": f"Double heading at line {lineno}: {m.group(0)[:60]}",
            "location": {"path": str(path), "line": lineno},
            "status": "OPEN",
        })
    return issues


def lint_fq5_keyword_colon(content: str, path: Path) -> List[Dict]:
    """Detect colons in frontmatter keywords."""
    issues = []
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return issues
    fm = fm_match.group(1)
    kw_match = re.search(r"keywords:\s*\[([^\]]*)\]", fm)
    if not kw_match:
        return issues
    keywords_str = kw_match.group(1)
    if ":" in keywords_str:
        lineno = content[:kw_match.start()].count("\n") + 1
        issues.append({
            "issue_id": f"gate17_fq5_{path.stem}_{lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "warn",
            "error_code": "G17-FQ-5",
            "message": f"Keyword contains colon at line {lineno}",
            "location": {"path": str(path), "line": lineno},
            "status": "OPEN",
        })
    return issues


def lint_fq6_claim_comment(content: str, path: Path) -> List[Dict]:
    """Detect claim comment markers outside code fences."""
    issues = []
    in_fence = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            if in_fence:
                if _FENCE_CLOSER_RE.match(stripped):
                    in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            continue
        for m in _CLAIM_COMMENT_RE.finditer(line):
            issues.append({
                "issue_id": f"gate17_fq6_{path.stem}_{lineno}",
                "gate": "gate_17_formatting_quality",
                "severity": "warn",
                "error_code": "G17-FQ-6",
                "message": f"Claim comment in body at line {lineno}: {m.group(0)}",
                "location": {"path": str(path), "line": lineno},
                "status": "OPEN",
            })
    return issues


def lint_fq7a_heading_hierarchy(content: str, path: Path) -> List[Dict]:
    """Detect heading hierarchy skips (FQ-7a deterministic check, TC-2522).

    Uses ``validate_heading_hierarchy()`` from content_sanitizer to detect
    cases like H1 -> H3 (skipping H2) which indicate incoherent structure.
    """
    errors = validate_heading_hierarchy(content)
    issues = []
    for err in errors:
        # Extract line number from the error string (format: "Heading skip at line N: ...")
        lineno = 0
        m = re.search(r"line (\d+)", err)
        if m:
            lineno = int(m.group(1))
        issues.append({
            "issue_id": f"gate17_fq7a_{path.stem}_{lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-7a",
            "message": f"[FQ-7a] {err[:120]}",
            "location": {"path": str(path), "line": lineno},
            "status": "OPEN",
        })
    return issues


def lint_fq8_adjacent_fences(content: str, path: Path) -> List[Dict]:
    """Detect adjacent code fences with the same language tag (TC-2892).

    Two code fences are "adjacent" when the only content between the
    closing ``` of the first and the opening ``` of the second consists
    of blank lines and/or HTML comments.  If both have the same language
    tag (or one is empty), this indicates a fragmented example that should
    have been merged into a single copy-pasteable block.

    Severity: error -- promoted from warn after bake-in across 3 pilots
    confirmed zero false merges (TC-2892).

    TC-3500: Detection algorithm extracted to _shared/prelint_fq.py for
    reuse by W7 (early detection).
    """
    from launch.workers._shared.prelint_fq import detect_adjacent_same_lang_fences

    detections = detect_adjacent_same_lang_fences(content)
    issues: List[Dict] = []
    for close_lineno, open_lineno, lang_label in detections:
        issues.append({
            "issue_id": f"gate17_fq8_{path.stem}_{open_lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-8",
            "message": (
                f"Adjacent same-language fences at lines "
                f"{close_lineno}/{open_lineno} (lang={lang_label})"
            ),
            "location": {"path": str(path), "line": open_lineno},
            "status": "OPEN",
        })

    return issues


def lint_fq9_limitations_dump_shape(content: str, path: Path) -> List[Dict]:
    """Detect dump-shaped Limitations sections (TC-2893).

    Flags:
    - Too many bullet lines (> FQ9_MAX_BULLETS)
    - Overly long bullet lines (> FQ9_MAX_LINE_LEN)
    - Dump shape indicators (file paths, JSON blobs, code patterns, raw claim fields)

    Fence-aware: bullets inside code fences are not flagged.
    Section-scoped: only scans lines under ## Limitations or ## Known Limitations.
    """
    issues: List[Dict] = []
    lines = content.splitlines()

    # Find ## Limitations or ## Known Limitations section
    section_start = None
    section_end = None
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if section_start is None:
            if _FQ9_SECTION_RE.match(stripped):
                section_start = lineno
        else:
            # Next ## heading ends the section
            if re.match(r'^##\s+', stripped) and lineno > section_start:
                section_end = lineno
                break

    if section_start is None:
        return issues

    if section_end is None:
        section_end = len(lines) + 1

    # Extract bullet lines (fence-aware)
    in_fence = False
    bullet_lines: List[Tuple[int, str]] = []
    for lineno in range(section_start + 1, section_end):
        if lineno > len(lines):
            break
        line = lines[lineno - 1]  # 0-indexed
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                if _FENCE_CLOSER_RE.match(stripped):
                    in_fence = False
            else:
                in_fence = True
            continue
        if in_fence:
            continue
        if stripped.startswith("- "):
            bullet_lines.append((lineno, stripped))

    # Check 1: Too many bullets
    if len(bullet_lines) > FQ9_MAX_BULLETS:
        issues.append({
            "issue_id": f"gate17_fq9_{path.stem}_count",
            "gate": "gate_17_formatting_quality",
            "severity": "warn",
            "error_code": "G17-FQ-9",
            "message": (
                f"Limitations section has {len(bullet_lines)} bullets "
                f"(threshold: {FQ9_MAX_BULLETS})"
            ),
            "location": {"path": str(path), "line": section_start},
            "status": "OPEN",
        })

    # Check 2 & 3: Per-bullet analysis
    for lineno, text in bullet_lines:
        # Overly long bullet
        if len(text) > FQ9_MAX_LINE_LEN:
            issues.append({
                "issue_id": f"gate17_fq9_{path.stem}_{lineno}_len",
                "gate": "gate_17_formatting_quality",
                "severity": "warn",
                "error_code": "G17-FQ-9",
                "message": (
                    f"Limitations bullet too long at line {lineno}: "
                    f"{len(text)} chars (threshold: {FQ9_MAX_LINE_LEN})"
                ),
                "location": {"path": str(path), "line": lineno},
                "status": "OPEN",
            })

        # Dump shape indicators
        if _FQ9_DUMP_INDICATORS.search(text):
            issues.append({
                "issue_id": f"gate17_fq9_{path.stem}_{lineno}_dump",
                "gate": "gate_17_formatting_quality",
                "severity": "warn",
                "error_code": "G17-FQ-9",
                "message": (
                    f"Limitations bullet has dump-shape indicators at line {lineno}: "
                    f"{text[:80]}"
                ),
                "location": {"path": str(path), "line": lineno},
                "status": "OPEN",
            })

    return issues


_ALL_LINTS = [
    lint_fq1_naked_code,
    lint_fq2_faq_concat,
    lint_fq4_double_heading,
    lint_fq5_keyword_colon,
    lint_fq6_claim_comment,
    lint_fq7a_heading_hierarchy,
    lint_fq8_adjacent_fences,
    lint_fq9_limitations_dump_shape,  # TC-2893
]

_ERROR_CODES = frozenset({"G17-FQ-1", "G17-FQ-4", "G17-FQ-7a", "G17-FQ-8"})


def run_deterministic_prelints(md_path: Path) -> Tuple[List[Dict], bool]:
    """Run all deterministic pre-lints on a markdown file.

    Returns:
        Tuple of (issues, has_errors) where has_errors indicates gate-failing issues.
    """
    content = md_path.read_text(encoding="utf-8")
    issues: List[Dict] = []
    for lint_fn in _ALL_LINTS:
        issues.extend(lint_fn(content, md_path))
    has_errors = any(i["error_code"] in _ERROR_CODES for i in issues)
    return issues, has_errors
