"""Gate G6: Permalink Uniqueness (TC-3670, TC-3685).

Detects permalink/URL collisions in frontmatter across all markdown files
within a run. Two or more files **in the same Hugo section** with the same
permalink produce a build collision and broken navigation.

TC-3685: Collision detection is now scoped by Hugo section (subdomain).
W4 (TC-969) explicitly allows the same url_path across sections because
sections map to different subdomains (docs.aspose.org vs kb.aspose.org).
Cross-section same permalink is NOT a collision.

Grounded in pilot review evidence:
  - /cells/python/ used by 4 different _index.md files (cross-section, OK)
  - /cells/python/howto/ used by howto.md and howto-2.md (same-section, error)
  - Doubled URL segments: /python/python/ (always error)

Always-error severity: no profile demotion.

Spec: specs/09_validation_gates.md - Quality Content Gates (G6)
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Frontmatter extraction
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Permalink field in frontmatter
_PERMALINK_RE = re.compile(r"^\s*permalink:\s*(.+)$", re.MULTILINE)

# Doubled path segments (e.g., /python/python/)
_DOUBLED_SEGMENT_RE = re.compile(r"/(\w+)/\1/")


def _infer_section(md_file: Path, site_dir: Path) -> str:
    """Infer Hugo section (subdomain) from file path.

    TC-3685: Files live under ``work/site/content/<subdomain>/...``.
    Extract the first path component after ``content/`` as the section.

    Falls back to ``"_global"`` if the path doesn't follow convention.
    """
    try:
        rel = md_file.relative_to(site_dir)
    except ValueError:
        return "_global"

    parts = rel.parts
    # Expected: content / <subdomain> / ...
    if len(parts) >= 2 and parts[0] == "content":
        return parts[1]

    return "_global"


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute permalink uniqueness gate.

    Collects all permalink values from frontmatter across the site and
    reports collisions **within the same Hugo section** (subdomain).
    Cross-section same-permalink is allowed per W4 TC-969.

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

    # TC-3685: Scope collisions by (section, permalink) — same key as W4
    permalink_map: Dict[Tuple[str, str], List[Tuple[Path, int]]] = defaultdict(list)

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        permalink, line_num = _extract_permalink(content)
        if permalink:
            # Normalize: lowercase, strip trailing/leading whitespace
            normalized = permalink.strip().strip("'\"").lower()
            section = _infer_section(md_file, site_dir)
            permalink_map[(section, normalized)].append((md_file, line_num))

            # Check for doubled segments (always error, regardless of section)
            match = _DOUBLED_SEGMENT_RE.search(normalized)
            if match:
                issues.append({
                    "issue_id": f"g6_doubled_{md_file.stem}_{line_num}",
                    "gate": "gate_permalink_uniqueness",
                    "severity": "error",
                    "message": (
                        f"Doubled URL segment '/{match.group(1)}/{match.group(1)}/' "
                        f"in permalink '{permalink.strip()}'"
                    ),
                    "error_code": "G6_DOUBLED_SEGMENT",
                    "location": {"path": str(md_file), "line": line_num},
                    "status": "OPEN",
                })

    # Report collisions (sorted by key for determinism)
    for (section, permalink) in sorted(permalink_map.keys()):
        files = permalink_map[(section, permalink)]
        if len(files) <= 1:
            continue

        # Sort files by path for deterministic issue ordering
        files_sorted = sorted(files, key=lambda x: str(x[0]))

        # Report collision on all files except the first
        for file_path, line_num in files_sorted[1:]:
            first_file = files_sorted[0][0]
            issues.append({
                "issue_id": f"g6_collision_{file_path.stem}_{line_num}",
                "gate": "gate_permalink_uniqueness",
                "severity": "error",
                "message": (
                    f"Permalink collision in section '{section}': "
                    f"'{permalink}' also used by '{first_file.name}'"
                ),
                "error_code": "G6_PERMALINK_COLLISION",
                "location": {
                    "path": str(file_path),
                    "line": line_num,
                    "collides_with": str(first_file),
                },
                "status": "OPEN",
            })

    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _extract_permalink(content: str) -> Tuple[str, int]:
    """Extract permalink value and its line number from frontmatter.

    Returns ("", 0) if no permalink found.
    """
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        return "", 0

    fm_text = fm_match.group(1)
    # Find the permalink line within frontmatter
    for idx, line in enumerate(fm_text.splitlines()):
        pm = _PERMALINK_RE.match(line)
        if pm:
            # Line number is idx + 2 (1-indexed, +1 for the opening ---)
            return pm.group(1).strip(), idx + 2

    return "", 0
