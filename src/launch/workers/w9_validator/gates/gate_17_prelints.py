"""Deterministic pre-lints for Gate 17 FQ defect codes.

Handles FQ-1, FQ-2, FQ-4, FQ-5, FQ-6, FQ-7a via regex.
FQ-3 (truncated) and FQ-7b (narrative flow) require LLM -- not handled here.

TC-2522: FQ-7 split into FQ-7a (deterministic heading hierarchy) and
FQ-7b (LLM narrative flow, handled in gate_17_formatting_quality.py).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from launch.workers._shared.content_sanitizer import validate_heading_hierarchy


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


def lint_fq1_naked_code(content: str, path: Path) -> List[Dict]:
    """Detect code-like lines outside code fences."""
    issues = []
    in_fence = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
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
        })
    return issues


def lint_fq4_double_heading(content: str, path: Path) -> List[Dict]:
    """Detect heading-in-heading (two headings on same line)."""
    issues = []
    for m in _DOUBLE_HEADING_RE.finditer(content):
        lineno = content[:m.start()].count("\n") + 1
        issues.append({
            "issue_id": f"gate17_fq4_{path.stem}_{lineno}",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-4",
            "message": f"Double heading at line {lineno}: {m.group(0)[:60]}",
            "location": {"path": str(path), "line": lineno},
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
        })
    return issues


def lint_fq6_claim_comment(content: str, path: Path) -> List[Dict]:
    """Detect claim comment markers outside code fences."""
    issues = []
    in_fence = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
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
        })
    return issues


_ALL_LINTS = [
    lint_fq1_naked_code,
    lint_fq2_faq_concat,
    lint_fq4_double_heading,
    lint_fq5_keyword_colon,
    lint_fq6_claim_comment,
    lint_fq7a_heading_hierarchy,
]

_ERROR_CODES = frozenset({"G17-FQ-1", "G17-FQ-4", "G17-FQ-7a"})


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
