"""Gate G1: LLM Artifact Phrases (TC-3670).

Detects LLM-generated boilerplate and preamble spam in content.
Patterns are grounded in pilot review evidence (reviews/pilot_content_review_summary.md):
  - "When working with..." preamble (~90% of files)
  - Filler transitions ("It's worth noting", "In conclusion")
  - Template-driven placeholder descriptions
  - Hedging language ("It should be noted")

Always-error severity: no profile demotion. Content with LLM artifacts
is never publication-ready regardless of validation profile.

Spec: specs/09_validation_gates.md - Quality Content Gates (G1)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# --- LLM artifact phrase patterns ---
# Each tuple: (compiled_regex, error_code_suffix, human_description)
# Patterns are line-anchored or word-boundary-anchored to reduce false positives.
_ARTIFACT_PATTERNS: List[tuple] = [
    # Preamble spam (the #1 defect: ~90% of pilot files)
    (
        re.compile(r"^\s*When\s+working\s+with\b", re.IGNORECASE),
        "PREAMBLE_WHEN_WORKING",
        "LLM preamble: 'When working with...'",
    ),
    (
        re.compile(
            r"^\s*(?:In\s+this\s+(?:article|guide|tutorial|section|document),?\s+(?:we|you)\s+will)",
            re.IGNORECASE,
        ),
        "PREAMBLE_IN_THIS",
        "LLM preamble: 'In this article/guide...'",
    ),
    (
        re.compile(
            r"^\s*(?:This\s+(?:article|guide|tutorial|section|document)\s+(?:covers|explains|describes|shows|demonstrates|walks\s+you))",
            re.IGNORECASE,
        ),
        "PREAMBLE_THIS_ARTICLE",
        "LLM preamble: 'This article covers/explains...'",
    ),
    # Filler transitions
    (
        re.compile(r"\bIt(?:'s|\s+is)\s+worth\s+noting\s+that\b", re.IGNORECASE),
        "FILLER_WORTH_NOTING",
        "LLM filler: 'It's worth noting that...'",
    ),
    (
        re.compile(r"\bIt\s+should\s+be\s+noted\s+that\b", re.IGNORECASE),
        "FILLER_SHOULD_BE_NOTED",
        "LLM filler: 'It should be noted that...'",
    ),
    (
        re.compile(r"^\s*In\s+conclusion,?\s", re.IGNORECASE),
        "FILLER_IN_CONCLUSION",
        "LLM filler: 'In conclusion...'",
    ),
    (
        re.compile(r"^\s*To\s+summarize,?\s", re.IGNORECASE),
        "FILLER_TO_SUMMARIZE",
        "LLM filler: 'To summarize...'",
    ),
    (
        re.compile(r"^\s*As\s+(?:we\s+)?(?:mentioned|discussed|noted)\s+(?:earlier|above|previously)\b", re.IGNORECASE),
        "FILLER_AS_MENTIONED",
        "LLM filler: 'As mentioned earlier...'",
    ),
    # Hedging / vague authority
    (
        re.compile(r"\bIt(?:'s|\s+is)\s+important\s+to\s+(?:note|understand|remember|mention)\s+that\b", re.IGNORECASE),
        "FILLER_IMPORTANT_TO_NOTE",
        "LLM filler: 'It's important to note that...'",
    ),
    # Placeholder / template-driven descriptions (pilot evidence: title = code comment)
    (
        re.compile(r"^\s*(?:This\s+is\s+a\s+placeholder|Template-driven\s+docs?\s+page)", re.IGNORECASE),
        "PLACEHOLDER_TEXT",
        "Placeholder/template text in published content",
    ),
]

# Max issues per file to avoid flooding
_MAX_ISSUES_PER_FILE = 20


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute LLM artifact phrase detection gate.

    Scans all markdown files for LLM-generated boilerplate phrases,
    skipping content inside code fences.

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


def _scan_file(content: str, md_file: Path) -> List[Dict[str, Any]]:
    """Scan a single file for LLM artifact phrases, skipping code fences."""
    file_issues: List[Dict[str, Any]] = []
    lines = content.splitlines()
    in_fence = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track code fence state
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue

        # Skip content inside code fences
        if in_fence:
            continue

        # Skip frontmatter (between --- delimiters at file start)
        # Simple heuristic: frontmatter is handled by other gates
        if line_num <= 1 and stripped == "---":
            continue

        for pattern, error_suffix, description in _ARTIFACT_PATTERNS:
            if pattern.search(line):
                file_issues.append({
                    "issue_id": f"g1_artifact_{md_file.stem}_{line_num}",
                    "gate": "gate_llm_artifact_phrases",
                    "severity": "error",
                    "message": f"{description}: '{stripped[:80]}'",
                    "error_code": f"G1_{error_suffix}",
                    "location": {"path": str(md_file), "line": line_num},
                    "status": "OPEN",
                })
                break  # One issue per line

        if len(file_issues) >= _MAX_ISSUES_PER_FILE:
            break

    return file_issues
