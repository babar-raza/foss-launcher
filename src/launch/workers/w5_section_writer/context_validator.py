"""Pre-generation context sufficiency check for W5 SectionWriter.

TC-2352: Validates that a page has enough claims and snippets to generate
quality content BEFORE invoking the LLM. Pages with insufficient context
are downgraded to a simpler role rather than being generated thin and padded.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum thresholds by page role.
# min_claims: minimum total claims required
# min_snippets: minimum code snippets required
# required_kinds: at least one claim of each listed kind must be present
ROLE_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "tutorial": {
        "min_claims": 3,
        "min_snippets": 1,
        "required_kinds": ["workflow"],
    },
    "faq": {
        "min_claims": 8,
        "min_snippets": 0,
        "required_kinds": [],
    },
    "comprehensive_guide": {
        "min_claims": 5,
        "min_snippets": 0,
        "required_kinds": ["workflow"],
    },
    "feature_showcase": {
        "min_claims": 3,
        "min_snippets": 1,
        "required_kinds": ["feature"],
    },
    "landing": {
        "min_claims": 3,
        "min_snippets": 0,
        "required_kinds": [],
    },
    "workflow_page": {
        "min_claims": 2,
        "min_snippets": 1,
        "required_kinds": ["workflow"],
    },
    "best_practices": {
        "min_claims": 4,
        "min_snippets": 0,
        "required_kinds": ["best_practice"],
    },
    "troubleshooting": {
        "min_claims": 3,
        "min_snippets": 0,
        "required_kinds": [],
    },
}

DEFAULT_THRESHOLD: Dict[str, Any] = {
    "min_claims": 2,
    "min_snippets": 0,
    "required_kinds": [],
}

# Downgrade mapping: role -> simpler role when context is insufficient
DOWNGRADE_MAP: Dict[str, str] = {
    "tutorial": "comprehensive_guide",
    "feature_showcase": "landing",
    "workflow_page": "landing",
    "comprehensive_guide": "landing",
}


def check_context_sufficiency(
    page: Dict[str, Any],
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
) -> Tuple[bool, List[str], Optional[str]]:
    """Check whether context is sufficient for the page role.

    Args:
        page: Page specification dict (must have 'page_role').
        claims: List of claim dicts for this page.
        snippets: List of snippet dicts for this page.

    Returns:
        Tuple of (is_sufficient, reasons, downgrade_role).
        - is_sufficient: True if thresholds are met.
        - reasons: List of human-readable insufficiency reasons.
        - downgrade_role: Suggested alternative role, or None.
    """
    role = page.get("page_role", "default")
    thresholds = ROLE_THRESHOLDS.get(role, DEFAULT_THRESHOLD)

    reasons: List[str] = []

    if len(claims) < thresholds["min_claims"]:
        reasons.append(
            f"Only {len(claims)} claims, need {thresholds['min_claims']}"
        )

    if len(snippets) < thresholds["min_snippets"]:
        reasons.append(
            f"Only {len(snippets)} snippets, need {thresholds['min_snippets']}"
        )

    for kind in thresholds["required_kinds"]:
        if not any(c.get("claim_kind") == kind for c in claims):
            reasons.append(f"No {kind} claims found")

    is_sufficient = len(reasons) == 0
    downgrade = DOWNGRADE_MAP.get(role) if not is_sufficient else None

    return is_sufficient, reasons, downgrade


# ---------------------------------------------------------------------------
# TC-2353: Post-generation page structure validation
# ---------------------------------------------------------------------------

# Required structural elements by role.
# Each entry is (regex_pattern, minimum_count, missing_message).
ROLE_REQUIRED_ELEMENTS: Dict[str, List[Tuple[str, int, str]]] = {
    "tutorial": [
        (r"##\s+.*[Pp]rerequisite", 1, "Missing Prerequisites section"),
        (r"##\s+.*[Ss]tep", 1, "Missing Step-by-step section"),
        (r"```", 1, "Missing code example"),
    ],
    "faq": [
        (r"###\s+Q:", 5, "Need at least 5 '### Q:' blocks"),
    ],
    "comprehensive_guide": [
        (r"^##\s+", 3, "Need at least 3 H2 sections"),
    ],
    "workflow_page": [
        (r"```", 1, "Missing code example"),
        (r"^##\s+", 1, "Missing H2 sections"),
    ],
    "feature_showcase": [
        (r"^##\s+", 2, "Need at least 2 H2 sections"),
        (r"```", 1, "Missing code example"),
    ],
    "troubleshooting": [
        (r"^##\s+", 2, "Need at least 2 H2 sections"),
    ],
    "best_practices": [
        (r"^##\s+", 2, "Need at least 2 H2 sections"),
    ],
    "blog": [
        (r"^##\s+", 1, "Need at least 1 H2 section"),
    ],
    "performance_guide": [
        (r"^##\s+", 2, "Need at least 2 H2 sections"),
        (r"```", 1, "Missing code example"),
    ],
}


def validate_page_structure(content: str, page_role: str) -> List[str]:
    """Validate that generated content has required structural elements.

    TC-2353: Check AFTER generation, BEFORE accepting output.

    Args:
        content: Generated markdown content.
        page_role: Page role string.

    Returns:
        List of human-readable messages for unfulfilled requirements.
        Empty list means content passes validation.
    """
    missing: List[str] = []
    for pattern, min_count, message in ROLE_REQUIRED_ELEMENTS.get(page_role, []):
        count = len(re.findall(pattern, content, re.MULTILINE))
        if count < min_count:
            missing.append(message)
    return missing
