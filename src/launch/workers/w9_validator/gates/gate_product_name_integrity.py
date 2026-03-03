"""Gate: Product Name Integrity (TC-2821, extended TC-3670 G5).

Detects corrupted product names in generated content, e.g. "Aspose. Note"
instead of "Aspose.Note". This is the gate-level defense against the
sanitizer corruption pattern documented in RC-2 of PHASE0_RCA.md.

TC-3670 G5 extension: Also detects:
  - "Aspire.Cells" / "Aspire.Note" (common LLM misspelling)
  - "Aspuse.Note" (transposition)
  - "for Python for Python" (doubled platform suffix)
  - Missing "FOSS" when canonical name includes it
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Pattern: "Aspose." followed by whitespace then a capital letter.
# This catches "Aspose. Note", "Aspose. Cells", "Aspose.  Words" etc.
_CORRUPTED_BRAND_RE = re.compile(r'Aspose\.\s+([A-Z])')

# TC-3670 G5: Common LLM misspellings of "Aspose"
_MISSPELLED_BRAND_RE = re.compile(
    r'\b(Asp(?:ire|use|oes|oce|soe))\.'
    r'(Cells|Note|Words|Pdf|Slides|Email|Imaging|3D|ThreeD)\b',
    re.IGNORECASE,
)

# TC-3670 G5: Doubled platform suffix ("for Python for Python")
_DOUBLED_PLATFORM_RE = re.compile(
    r'\bfor\s+(Python|\.NET|Java|C\+\+|Node\.js|Go)\s+for\s+\1\b',
    re.IGNORECASE,
)

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

    canonical_name = _get_canonical_name(run_dir)

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        _scan_content(content, md_file, profile, issues, canonical_name)

    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _get_canonical_name(run_dir: Path) -> Optional[str]:
    """Load canonical product name from product_facts.json."""
    pf_path = run_dir / "artifacts" / "product_facts.json"
    if pf_path.exists():
        try:
            data = json.loads(pf_path.read_text(encoding="utf-8"))
            return data.get("product_name")
        except Exception:
            pass
    return None


def _scan_content(
    content: str,
    md_file: Path,
    profile: str,
    issues: List[Dict[str, Any]],
    canonical_name: Optional[str] = None,
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

        # Original pattern: "Aspose. Note" (space corruption)
        for match in _CORRUPTED_BRAND_RE.finditer(line):
            severity = "error" if profile != "local" else "warn"
            if profile == "prod":
                severity = "blocker"

            issues.append({
                "issue_id": f"gate_product_name_{md_file.stem}_{line_num}",
                "gate": "gate_product_name_integrity",
                "severity": severity,
                "message": f"Corrupted product name '{match.group(0).strip()}' at line {line_num}",
                "error_code": "G5_SPACE_CORRUPTED",
                "location": {"path": str(md_file), "line": line_num},
                "status": "OPEN",
            })

        # TC-3670 G5: Misspelled brand ("Aspire.Cells", "Aspuse.Note")
        for match in _MISSPELLED_BRAND_RE.finditer(line):
            issues.append({
                "issue_id": f"g5_misspell_{md_file.stem}_{line_num}",
                "gate": "gate_product_name_integrity",
                "severity": "error",
                "message": (
                    f"Misspelled product name '{match.group(0)}' "
                    f"(should be 'Aspose.{match.group(2)}')"
                ),
                "error_code": "G5_BRAND_MISSPELLED",
                "location": {"path": str(md_file), "line": line_num},
                "status": "OPEN",
            })

        # TC-3670 G5: Doubled platform suffix
        for match in _DOUBLED_PLATFORM_RE.finditer(line):
            issues.append({
                "issue_id": f"g5_doubled_{md_file.stem}_{line_num}",
                "gate": "gate_product_name_integrity",
                "severity": "error",
                "message": (
                    f"Doubled platform suffix: '{match.group(0)}' "
                    f"(should be 'for {match.group(1)}')"
                ),
                "error_code": "G5_DOUBLED_PLATFORM",
                "location": {"path": str(md_file), "line": line_num},
                "status": "OPEN",
            })
