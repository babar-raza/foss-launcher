"""Gate: KB How-To Structure Validation.

Spec v1.1 J5: Validates that KB how-to draft files exist with correct
heading order and no fragmented code warnings (FQ-1).

TC-2481b: Replaced hardcoded slug frozenset import with dynamic slug discovery
from page_plan.json. This allows evidence-aware slugs (e.g., "how-to-load-3d-
models-python") without breaking gate validation.

Checks:
  1. Draft files exist at ``drafts/kb/{slug}.md`` for each KB how-to slug
     in the page plan
  2. Section heading order in each draft matches spec: Goal → Prerequisites →
     Steps → Code Example → See Also (checks H2 and H3 headings, since W5
     may emit H3 when the page title occupies H2)
  3. No FQ-1 fragmented-code warnings present (``<!-- WARNING: fragmented-code
     detected (FQ-1) -->``)

``graceful_artifact_skip: true`` — skips when ``drafts/kb/`` dir does not exist.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

_FQ1_WARNING = "<!-- WARNING: fragmented-code detected (FQ-1) -->"

# Heading order spec: these heading texts must appear in this relative order.
# Uses case-insensitive substring matching on H2 lines to handle
# "{product_name} Code Example" pattern.
_HEADING_ORDER = ["goal", "prerequisites", "steps", "code example", "see also"]


def _discover_howto_slugs(run_dir: Path) -> Set[str]:
    """Discover KB how-to slugs from page_plan.json dynamically.

    TC-2481b: Replaces hardcoded frozenset import. Allows evidence-aware
    slugs to be validated without code changes.
    """
    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    if not page_plan_path.exists():
        return set()
    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception:
        return set()
    return {
        p.get("slug")
        for p in page_plan.get("pages", [])
        if p.get("section") == "kb"
        and p.get("page_role") in ("howto_article", "how_to", "howto")
        and p.get("slug")
    }


def _extract_h2_headings(content: str) -> List[str]:
    """Extract section heading texts from markdown, lowercased.

    Matches both H2 (``## ...``) and H3 (``### ...``) headings because W5
    may emit H3 when the page title occupies the H2 level.
    """
    headings = []
    for line in content.split("\n"):
        m = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if m:
            headings.append(m.group(1).strip().lower())
    return headings


def _check_heading_order(headings: List[str], slug: str) -> List[str]:
    """Return list of order-violation messages (empty = pass).

    Each required heading must appear AND must come after the previous
    required heading in the document order.
    """
    # Find positions of each required heading (first match via substring)
    positions: Dict[str, int] = {}
    for required in _HEADING_ORDER:
        for i, h in enumerate(headings):
            if required in h:
                positions[required] = i
                break

    violations = []
    last_pos = -1
    last_name = None
    for required in _HEADING_ORDER:
        pos = positions.get(required)
        if pos is None:
            violations.append(
                f"Heading '{required}' missing in draft '{slug}'."
            )
            continue
        if last_pos >= 0 and pos <= last_pos:
            violations.append(
                f"Heading '{required}' appears before '{last_name}' "
                f"in draft '{slug}' — expected order: {_HEADING_ORDER}."
            )
        last_pos = pos
        last_name = required
    return violations


def execute_gate(
    run_dir: Path, profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: KB How-To Structure Validation.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    drafts_kb = run_dir / "drafts" / "kb"
    if not drafts_kb.exists():
        return True, []  # graceful_artifact_skip

    # TC-2481b: Discover slugs from page_plan instead of hardcoded frozenset
    howto_slugs = _discover_howto_slugs(run_dir)
    if not howto_slugs:
        # No page_plan or no KB how-to pages — graceful skip
        return True, []

    # Check 1: draft file existence for discovered slugs
    for slug in sorted(howto_slugs):
        draft = drafts_kb / f"{slug}.md"
        if not draft.exists():
            issues.append({
                "issue_id": f"gate_kb_howto_structure_missing_{slug}",
                "gate": "gate_kb_howto_structure",
                "severity": "error",
                "message": f"Missing KB how-to draft file: drafts/kb/{slug}.md",
                "error_code": "GATE_KB_HOWTO_STRUCTURE_DRAFT_MISSING",
                "status": "OPEN",
            })

    # Check 2 & 3 for each existing draft with a discovered slug
    for slug in sorted(howto_slugs):
        draft = drafts_kb / f"{slug}.md"
        if not draft.exists():
            continue

        try:
            content = draft.read_text(encoding="utf-8")
        except Exception:
            continue

        # Check 2: heading order
        headings = _extract_h2_headings(content)
        for violation in _check_heading_order(headings, slug):
            issues.append({
                "issue_id": f"gate_kb_howto_structure_order_{slug}",
                "gate": "gate_kb_howto_structure",
                "severity": "error",
                "message": violation,
                "error_code": "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
                "status": "OPEN",
            })

        # Check 3: FQ-1 warnings
        if _FQ1_WARNING in content:
            count = content.count(_FQ1_WARNING)
            issues.append({
                "issue_id": f"gate_kb_howto_structure_fq1_{slug}",
                "gate": "gate_kb_howto_structure",
                "severity": "warn",
                "message": (
                    f"Draft 'drafts/kb/{slug}.md' contains {count} "
                    f"fragmented-code warning(s) (FQ-1)."
                ),
                "error_code": "GATE_KB_HOWTO_STRUCTURE_FQ1",
                "status": "OPEN",
            })

    has_errors = any(i["severity"] == "error" for i in issues)
    return (not has_errors), issues
