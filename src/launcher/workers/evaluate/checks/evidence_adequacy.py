"""TC-5164: Evidence adequacy attribution check.

Emits a medium-severity finding when a page was planned with insufficient
evidence signals (as recorded by the Understand worker in page_evidence_index).

This check is diagnostic/attributional, not a content quality gate. It helps
operators distinguish between "content was thin because the LLM did poorly"
vs. "content was thin because the repo had insufficient evidence for this page
role." Severity is intentionally medium to avoid penalizing the generator for
upstream evidence deficits.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_MISSING_SHOWN = 3


def check_evidence_adequacy(
    gen_page: Any,
    page_evidence_index: dict[str, Any],
) -> list[dict[str, str]]:
    """Check whether the page role had sufficient evidence when planned.

    Parameters
    ----------
    gen_page:
        GeneratedPage object (duck-typed — needs .slug and .page_role).
    page_evidence_index:
        Dict keyed by page_role, values are PageEvidenceScore dicts or
        objects with evidence_sufficient and missing attributes.

    Returns
    -------
    list[dict]
        Zero or one finding dict with keys: check, message, severity, location.
    """
    if not page_evidence_index:
        return []

    role = getattr(gen_page, "page_role", None)
    if not role:
        return []

    score = page_evidence_index.get(role)
    if score is None:
        return []

    # Support both dict and object (PageEvidenceScore) representations
    if isinstance(score, dict):
        evidence_sufficient = score.get("evidence_sufficient", True)
        missing = score.get("missing", [])
    else:
        evidence_sufficient = getattr(score, "evidence_sufficient", True)
        missing = getattr(score, "missing", [])

    if evidence_sufficient:
        return []

    missing_list = list(missing or [])[:_MAX_MISSING_SHOWN]
    missing_str = ", ".join(missing_list) if missing_list else "unspecified"

    return [{
        "check": "evidence_adequacy",
        "message": (
            f"Page role '{role}' was planned with insufficient evidence "
            f"(evidence_sufficient=False). Missing signals: {missing_str}. "
            "Grade may reflect upstream evidence deficit, not generation quality. "
            "Consider re-running Understand on a richer repository revision."
        ),
        "severity": "medium",
        "location": getattr(gen_page, "slug", role),
    }]
