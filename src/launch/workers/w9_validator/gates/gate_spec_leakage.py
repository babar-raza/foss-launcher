"""Gate G7: Spec Leakage Detection (TC-3670).

Detects internal specification / binary format content on user-facing pages.
Reference pages (api_reference, reference_object_page) are allowed to discuss
internal structures; user-facing pages (landing, faq, tutorial, howto_article,
feature_showcase, etc.) must not expose binary format internals.

Grounded in pilot review evidence:
  - CompactID / CompactIDResolutionError on how-to pages
  - rgIndents / unsigned 8-bit integer on how-to pages
  - Hashed chunk list / transaction logs on api-overview
  - RFC 4122 / C706 GUID internals on user pages

Always-error severity: no profile demotion.

Spec: specs/09_validation_gates.md - Quality Content Gates (G7)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# Page roles that are ALLOWED to contain spec/internal content
_REFERENCE_ROLES: FrozenSet[str] = frozenset({
    "api_reference",
    "reference_object_page",
})

# Binary/spec term patterns to detect on user-facing pages.
# Each tuple: (compiled_regex, term_label)
_SPEC_LEAK_PATTERNS: List[tuple] = [
    # Binary format structures
    (re.compile(r"\bJCID\b"), "JCID"),
    (re.compile(r"\bFNDX?\b"), "FNDX"),
    (re.compile(r"\bCompactID\b"), "CompactID"),
    (re.compile(r"\brgIndents\b"), "rgIndents"),
    (re.compile(r"\bObjectDeclaration\b"), "ObjectDeclaration"),
    (re.compile(r"\bObject\s+Data\s+BLOB\b", re.IGNORECASE), "ObjectDataBLOB"),
    (re.compile(r"\bRgOutlineIndentDistance\b"), "RgOutlineIndentDistance"),
    # Transaction / storage internals
    (re.compile(r"\btransaction\s+log\b", re.IGNORECASE), "transaction_log"),
    (re.compile(r"\bfree\s+chunk\s+list\b", re.IGNORECASE), "free_chunk_list"),
    (re.compile(r"\bhashed\s+chunk\s+list\b", re.IGNORECASE), "hashed_chunk_list"),
    # Encoding / byte-level details
    (re.compile(r"\blittle[\s-]endian\b", re.IGNORECASE), "little_endian"),
    (re.compile(r"\bbig[\s-]endian\b", re.IGNORECASE), "big_endian"),
    (re.compile(r"\bcp1252\b", re.IGNORECASE), "cp1252"),
    # Hex constants (4+ hex digits: 0xABCD)
    (re.compile(r"\b0x[0-9A-Fa-f]{4,}\b"), "hex_constant"),
    # Spec section references
    (re.compile(r"\bsection\s+\d+\.\d+\.\d+", re.IGNORECASE), "spec_section_ref"),
    # Patent / spec authorship
    (re.compile(r"iplg@microsoft\.com", re.IGNORECASE), "patent_email"),
    # RFC / protocol internals on non-reference pages
    (re.compile(r"\bRFC\s+4122\b"), "RFC_4122"),
    (re.compile(r"\bC706\b"), "C706"),
    # Binary field descriptors
    (re.compile(r"\bunsigned\s+\d+-bit\s+integer\b", re.IGNORECASE), "binary_field_desc"),
    (re.compile(r"\bIsFileData\b"), "IsFileData"),
]

# Max issues per file
_MAX_ISSUES_PER_FILE = 15


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute spec leakage detection gate.

    Scans user-facing markdown files for internal spec terminology.
    Reference pages are skipped (they may legitimately reference internals).

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

    # Load page_plan for page_role filtering
    page_roles = _load_page_roles(run_dir)

    md_files = sorted(site_dir.rglob("*.md"))
    if not md_files:
        return True, []

    for md_file in md_files:
        # Determine page role for this file
        role = _get_page_role(md_file, page_roles, run_dir)

        # Skip reference pages — they may legitimately discuss internals
        if role in _REFERENCE_ROLES:
            continue

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


def _load_page_roles(run_dir: Path) -> Dict[str, str]:
    """Load page_role mapping from page_plan.json.

    Returns dict mapping output_path -> page_role.
    """
    pp_path = run_dir / "artifacts" / "page_plan.json"
    if not pp_path.exists():
        return {}

    try:
        data = json.loads(pp_path.read_text(encoding="utf-8"))
        pages = data.get("pages", [])
        result = {}
        for page in pages:
            output_path = page.get("output_path", "")
            role = page.get("page_role", "")
            if output_path and role:
                result[output_path] = role
        return result
    except Exception:
        return {}


def _get_page_role(
    md_file: Path, page_roles: Dict[str, str], run_dir: Path
) -> Optional[str]:
    """Determine the page_role for a given markdown file.

    Tries to match the file's relative path against page_plan output_path entries.
    Falls back to checking frontmatter machine_readable.page_role.
    """
    # Try page_plan lookup
    try:
        rel = md_file.relative_to(run_dir / "work" / "site")
        rel_str = str(rel).replace("\\", "/")
        if rel_str in page_roles:
            return page_roles[rel_str]
        # Try with content/ prefix stripped
        if rel_str.startswith("content/"):
            stripped = rel_str[len("content/"):]
            if stripped in page_roles:
                return page_roles[stripped]
    except ValueError:
        pass

    # Fallback: read frontmatter page_role
    try:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        # Quick YAML parse for page_role
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).splitlines():
                if "page_role:" in line:
                    role = line.split("page_role:", 1)[1].strip().strip("'\"")
                    return role if role else None
    except Exception:
        pass

    return None


def _scan_file(content: str, md_file: Path) -> List[Dict[str, Any]]:
    """Scan a user-facing file for spec leakage terms, skipping code fences."""
    file_issues: List[Dict[str, Any]] = []
    lines = content.splitlines()
    in_fence = False
    in_frontmatter = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip frontmatter
        if line_num == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # Skip code fences (code examples may legitimately reference internals)
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for pattern, term_label in _SPEC_LEAK_PATTERNS:
            if pattern.search(line):
                file_issues.append({
                    "issue_id": f"g7_spec_leak_{md_file.stem}_{line_num}_{term_label}",
                    "gate": "gate_spec_leakage",
                    "severity": "error",
                    "message": (
                        f"Spec/internal term '{term_label}' on user-facing page: "
                        f"'{stripped[:80]}'"
                    ),
                    "error_code": "G7_SPEC_LEAKAGE",
                    "location": {"path": str(md_file), "line": line_num},
                    "status": "OPEN",
                })
                break  # One issue per line

        if len(file_issues) >= _MAX_ISSUES_PER_FILE:
            break

    return file_issues
