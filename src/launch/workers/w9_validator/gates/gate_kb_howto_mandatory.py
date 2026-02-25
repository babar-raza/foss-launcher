"""Gate: KB How-To Mandatory Pages.

Spec v1.1 J3: Validates that the KB section of page_plan.json contains all
mandatory how-to topic categories defined in the active ruleset.

TC-2481b: Replaced literal slug matching with ``topic_category``-based coverage
check. Each mandatory how-to topic category (load_file, save_file,
convert_formats, troubleshoot, optimize_performance) must have at least one
KB how-to page in page_plan. Additionally, >=5 KB how-to pages must exist.

When ``topic_category`` is not set on pages (legacy page plans), the gate
falls back to inferring categories from slug text.

A ``graceful_artifact_skip: true`` entry in the registry means this gate is
skipped if ``page_plan.json`` does not exist (offline / pre-W4 runs).

TC-2601: ``_SLUG_CATEGORY_MAP`` and ``_REQUIRED_TOPIC_CATEGORIES`` now
imported from ``_shared.slug_constants`` to eliminate duplication.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from ..._shared.slug_constants import (
    REQUIRED_TOPIC_CATEGORIES as _REQUIRED_TOPIC_CATEGORIES,
    TOPIC_CATEGORY_MAP as _SLUG_CATEGORY_MAP,
)

# Minimum number of KB how-to pages required
_MIN_HOWTO_COUNT = 5


def _infer_category_from_slug(slug: str) -> str:
    """Infer topic_category from slug text when field is not set."""
    slug_lower = slug.lower()
    for keyword, category in _SLUG_CATEGORY_MAP.items():
        if keyword in slug_lower:
            return category
    return ""


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: KB How-To Mandatory Pages.

    Validates:
    1. At least 5 KB how-to pages exist in page_plan.
    2. All mandatory topic categories are covered (each has >=1 page).

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    if not page_plan_path.exists():
        # graceful_artifact_skip: true — skip if no page_plan
        return True, []

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception as e:
        issues.append({
            "issue_id": "gate_kb_howto_page_plan_invalid",
            "gate": "gate_kb_howto_mandatory",
            "severity": "error",
            "message": f"Failed to load page_plan.json: {e}",
            "error_code": "GATE_KB_HOWTO_PAGE_PLAN_INVALID",
            "status": "OPEN",
        })
        return False, issues

    # Collect topic categories and count for KB how-to pages
    kb_howto_topics: Set[str] = set()
    kb_howto_slugs: Set[str] = set()
    kb_howto_count = 0

    for page in page_plan.get("pages", []):
        if (
            page.get("section") == "kb"
            and page.get("page_role") in ("howto_article", "how_to", "howto")
        ):
            kb_howto_count += 1
            slug = page.get("slug", "")
            if slug:
                kb_howto_slugs.add(slug)

            # Prefer explicit topic_category; fall back to slug inference
            tc = page.get("topic_category", "")
            if not tc and slug:
                tc = _infer_category_from_slug(slug)
                if tc:
                    # TC-2612: Deprecation warning for legacy page plans without
                    # explicit topic_category. All new page plans should include it.
                    warnings.warn(
                        f"Slug-based topic_category inference is deprecated. "
                        f"Set explicit topic_category on page slug='{slug}'. "
                        f"Inferred: '{tc}'. "
                        f"Legacy support will be removed in a future release.",
                        DeprecationWarning,
                        stacklevel=1,
                    )
            if tc:
                kb_howto_topics.add(tc)

    # Check 1: minimum count
    if kb_howto_count < _MIN_HOWTO_COUNT:
        issues.append({
            "issue_id": "gate_kb_howto_mandatory_count",
            "gate": "gate_kb_howto_mandatory",
            "severity": "error",
            "message": (
                f"KB section has {kb_howto_count} how-to pages, "
                f"minimum required is {_MIN_HOWTO_COUNT}."
            ),
            "error_code": "GATE_KB_HOWTO_MANDATORY_COUNT",
            "status": "OPEN",
        })

    # Check 2: topic coverage
    missing_topics = sorted(_REQUIRED_TOPIC_CATEGORIES - kb_howto_topics)
    if missing_topics:
        issues.append({
            "issue_id": "gate_kb_howto_mandatory_topic_missing",
            "gate": "gate_kb_howto_mandatory",
            "severity": "error",
            "message": (
                f"KB section is missing mandatory topic categories: {missing_topics}. "
                f"Found topics: {sorted(kb_howto_topics)}. "
                f"Found KB how-to slugs: {sorted(kb_howto_slugs)}."
            ),
            "error_code": "GATE_KB_HOWTO_MANDATORY_TOPIC_MISSING",
            "status": "OPEN",
        })

    has_errors = any(i["severity"] == "error" for i in issues)
    return (not has_errors), issues
