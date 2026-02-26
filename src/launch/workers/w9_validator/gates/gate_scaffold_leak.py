"""Gate: Scaffold/Prompt Leak Detection (TC-2850).

Blocks publication when scaffolding, LLM meta-commentary, or pipeline
diagnostics remain in generated content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Compiled patterns for scaffold/prompt leak detection
_LEAK_PATTERNS: List[tuple] = [
    # LLM completion scaffolding
    (re.compile(r"You now have a (?:complete|working|full)", re.IGNORECASE), "LLM_SCAFFOLD"),
    (re.compile(r"Here(?:'s| is) a complete", re.IGNORECASE), "LLM_SCAFFOLD"),
    # LLM meta-commentary
    (re.compile(r"As an AI", re.IGNORECASE), "LLM_META"),
    (re.compile(r"I(?:'ll| will) help you", re.IGNORECASE), "LLM_META"),
    (re.compile(r"Let me (?:explain|show|demonstrate)", re.IGNORECASE), "LLM_META"),
    # Pipeline diagnostics
    (re.compile(r"claim_id:\s*[a-f0-9-]+", re.IGNORECASE), "PIPELINE_DIAGNOSTIC"),
    (re.compile(r"evidence_score:\s*\d"), "PIPELINE_DIAGNOSTIC"),
    (re.compile(r"<!--\s*claim\.[A-Z]"), "PIPELINE_DIAGNOSTIC"),
]


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute scaffold leak detection gate.

    Scans all markdown files for scaffold/prompt leak patterns.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))
    MAX_ISSUES_PER_FILE = 10

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = content.splitlines()
        in_fence = False
        file_issues: List[Dict[str, Any]] = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue

            # Check both prose and code fence content
            for pattern, category in _LEAK_PATTERNS:
                if pattern.search(line):
                    severity = _get_severity(category, in_fence, profile)
                    file_issues.append({
                        "issue_id": f"scaffold_leak_{md_file.stem}_{line_num}_{category}",
                        "gate": "gate_scaffold_leak",
                        "severity": severity,
                        "message": f"Scaffold leak ({category}): '{line.strip()[:80]}'",
                        "error_code": f"SCAFFOLD_{category}",
                        "location": {"path": str(md_file), "line": line_num},
                        "status": "OPEN",
                    })
                    break  # Only report first pattern match per line

            if len(file_issues) >= MAX_ISSUES_PER_FILE:
                break

        issues.extend(file_issues)

    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _get_severity(category: str, in_fence: bool, profile: str) -> str:
    """Determine severity based on category, context, and profile.

    Pipeline diagnostics in code fences are warn (may be intentional comments).
    LLM scaffold/meta in prose is error (prod: blocker).
    """
    if category == "PIPELINE_DIAGNOSTIC" and in_fence:
        return "warn"

    if profile == "local":
        return "warn"
    if profile == "prod":
        return "blocker"
    return "error"
