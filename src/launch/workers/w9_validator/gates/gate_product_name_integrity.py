"""Gate: Product Name Integrity (TC-2821).

Detects corrupted product names in generated content, e.g. "Aspose. Note"
instead of "Aspose.Note". This is the gate-level defense against the
sanitizer corruption pattern documented in RC-2 of PHASE0_RCA.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Pattern: "Aspose." followed by whitespace then a capital letter.
# This catches "Aspose. Note", "Aspose. Cells", "Aspose.  Words" etc.
_CORRUPTED_BRAND_RE = re.compile(r'Aspose\.\s+([A-Z])')

# Also check frontmatter title/description specifically
_FRONTMATTER_RE = re.compile(
    r'^---\s*\n(.*?)\n---',
    re.DOTALL,
)


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute product name integrity gate.

    Scans all markdown files for corrupted brand names (e.g. "Aspose. Note").

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
    if not md_files:
        return True, []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            # Skip lines inside code fences
            # (Simple heuristic: track fence state)
            pass

        # Full-content scan (simpler than line-by-line fence tracking)
        _scan_content(content, md_file, profile, issues)

    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _scan_content(
    content: str,
    md_file: Path,
    profile: str,
    issues: List[Dict[str, Any]],
) -> None:
    """Scan content for corrupted brand names, skipping code fences."""
    lines = content.splitlines()
    in_fence = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in _CORRUPTED_BRAND_RE.finditer(line):
            severity = "error" if profile != "local" else "warn"
            if profile == "prod":
                severity = "blocker"

            corrupted = match.group(0) + match.group(1)[0:] if match.group(1) else match.group(0)
            issues.append({
                "issue_id": f"gate_product_name_{md_file.stem}_{line_num}",
                "gate": "gate_product_name_integrity",
                "severity": severity,
                "message": f"Corrupted product name '{match.group(0).strip()}' at line {line_num}",
                "error_code": "PRODUCT_NAME_CORRUPTED",
                "location": {"path": str(md_file), "line": line_num},
                "status": "OPEN",
            })
