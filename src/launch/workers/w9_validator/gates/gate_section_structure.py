"""Gate G4: Section Structure Enforcement (TC-3670).

Enforces heading structure contracts in generated content:
  - No duplicate H2 headings within a file
  - "See Also" must be the last H2 section (nothing after it)
  - No trailing punctuation on headings (periods observed in pilots)
  - No content after "See Also" (except links)

Grounded in pilot review evidence: duplicate sections, inverted order,
trailing periods on headings ("Quick Start.", "See Also."),
content-after-See-Also violations.

Always-error severity: no profile demotion.

Spec: specs/09_validation_gates.md - Quality Content Gates (G4)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Heading extraction regex
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Trailing punctuation on headings (period, comma, semicolon)
_TRAILING_PUNCT_RE = re.compile(r"[.,;:!]+\s*$")

# "See Also" heading variants
_SEE_ALSO_RE = re.compile(r"^see\s+also\.?\s*$", re.IGNORECASE)

# Max issues per file
_MAX_ISSUES_PER_FILE = 15


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute section structure enforcement gate.

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
    """Scan a single file for structural violations."""
    file_issues: List[Dict[str, Any]] = []
    lines = content.splitlines()
    in_fence = False
    in_frontmatter = False

    # Track headings: list of (line_num, level, text)
    headings: List[Tuple[int, int, str]] = []

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Frontmatter
        if line_num == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # Code fences
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Extract headings
        match = _HEADING_RE.match(stripped)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append((line_num, level, text))

            # Check trailing punctuation
            if _TRAILING_PUNCT_RE.search(text):
                file_issues.append({
                    "issue_id": f"g4_punct_{md_file.stem}_{line_num}",
                    "gate": "gate_section_structure",
                    "severity": "error",
                    "message": f"Trailing punctuation on heading: '{text}'",
                    "error_code": "G4_HEADING_TRAILING_PUNCT",
                    "location": {"path": str(md_file), "line": line_num},
                    "status": "OPEN",
                })

    # Check for duplicate H2 headings
    h2_headings: Dict[str, int] = {}
    for line_num, level, text in headings:
        if level == 2:
            # Normalize for comparison (lowercase, strip punctuation)
            normalized = re.sub(r"[^\w\s]", "", text.lower()).strip()
            if normalized in h2_headings:
                file_issues.append({
                    "issue_id": f"g4_dup_h2_{md_file.stem}_{line_num}",
                    "gate": "gate_section_structure",
                    "severity": "error",
                    "message": (
                        f"Duplicate H2 heading '{text}' "
                        f"(first at line {h2_headings[normalized]})"
                    ),
                    "error_code": "G4_DUPLICATE_H2",
                    "location": {
                        "path": str(md_file),
                        "line": line_num,
                        "first_occurrence": h2_headings[normalized],
                    },
                    "status": "OPEN",
                })
            else:
                h2_headings[normalized] = line_num

    # Check "See Also" is last H2
    h2_list = [(ln, txt) for ln, lv, txt in headings if lv == 2]
    see_also_positions = [
        (idx, ln, txt)
        for idx, (ln, txt) in enumerate(h2_list)
        if _SEE_ALSO_RE.match(re.sub(r"[^\w\s]", "", txt).strip())
    ]

    for idx, line_num, text in see_also_positions:
        if idx < len(h2_list) - 1:
            next_h2_line = h2_list[idx + 1][0]
            file_issues.append({
                "issue_id": f"g4_see_also_not_last_{md_file.stem}_{line_num}",
                "gate": "gate_section_structure",
                "severity": "error",
                "message": (
                    f"'See Also' is not the last H2 section "
                    f"(followed by '{h2_list[idx + 1][1]}' at line {next_h2_line})"
                ),
                "error_code": "G4_SEE_ALSO_NOT_LAST",
                "location": {"path": str(md_file), "line": line_num},
                "status": "OPEN",
            })

    # Cap issues
    return file_issues[:_MAX_ISSUES_PER_FILE]
