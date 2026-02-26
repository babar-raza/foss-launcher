"""Gate 19: Cross-Page Redundancy Check.

Pages within the same section (parent directory) that share more than 60% of their
significant word content (Jaccard similarity, after stripping frontmatter, code
blocks, and stopwords) are flagged.

Severity is profile-aware (TC-2860):
- prod/ci: >0.70 → error, 0.60-0.70 → warn
- local:   >0.70 → warn,  0.60-0.70 → info

This catches LLM paraphrasing: the common problem where the model produces two
pages in the same section that cover identical material in slightly different words.

TC-2372: Gate 19 Cross-Page Redundancy (RCA Part 4-E)
TC-2860: Profile-aware severity upgrade

Per specs/09_validation_gates.md.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

from launch.workers._shared.jaccard import (
    SIMILARITY_THRESHOLD,
    STOPWORDS,
    _strip_frontmatter,
    _strip_code_blocks,
    _tokenize,
    compute_word_set,
    jaccard_similarity,
)

# High-similarity threshold where severity escalates from warn → error
HIGH_SIMILARITY_THRESHOLD = 0.70


def run_gate_19(
    pages: List[Dict[str, Any]],
    profile: str = "ci",
) -> List[Dict[str, Any]]:
    """Execute Gate 19: Cross-Page Redundancy Check.

    Groups pages by their parent directory (section), then performs pairwise
    Jaccard similarity on significant word sets.  Pairs exceeding thresholds
    receive severity based on the validation profile.

    Args:
        pages: List of page dicts with keys ``path``, ``content``, ``page_role``.
               This is the same list built for Gate 16 in worker.py.
        profile: Validation profile (``local``, ``ci``, ``prod``).

    Returns:
        List of issue dicts with profile-aware severity.
    """
    issues: List[Dict[str, Any]] = []

    # Group pages by parent directory
    sections: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for page in pages:
        parent = str(Path(page.get("path", "")).parent)
        sections[parent].append(page)

    for _section, section_pages in sections.items():
        if len(section_pages) < 2:
            continue

        # Pre-compute word sets
        word_sets: List[Set[str]] = []
        for page in section_pages:
            content = page.get("content", "")
            body = _strip_frontmatter(content)
            body = _strip_code_blocks(body)
            word_sets.append(set(_tokenize(body)))

        # Pairwise Jaccard
        n = len(section_pages)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = word_sets[i], word_sets[j]
                if not a or not b:
                    continue
                similarity = jaccard_similarity(a, b)
                if similarity > SIMILARITY_THRESHOLD:
                    path_a = section_pages[i].get("path", "")
                    path_b = section_pages[j].get("path", "")
                    name_a = os.path.basename(path_a)
                    name_b = os.path.basename(path_b)
                    slug_a = _slug(path_a)
                    slug_b = _slug(path_b)
                    severity = _get_redundancy_severity(similarity, profile)
                    issues.append({
                        "issue_id": f"gate19_redundancy_{slug_a}_{slug_b}",
                        "gate": "gate_19_redundancy",
                        "severity": severity,
                        "message": (
                            f"High content overlap ({similarity:.0%}) between "
                            f"{name_a!r} and {name_b!r}"
                        ),
                        "error_code": "G19-001",
                        "location": {"path": path_a, "line": 1},
                        "status": "OPEN",
                    })

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_redundancy_severity(similarity: float, profile: str) -> str:
    """Determine severity based on similarity score and validation profile.

    Thresholds (TC-2860):
    - >0.70 (high): prod/ci → error, local → warn
    - 0.60-0.70 (moderate): prod/ci → warn, local → info
    """
    if similarity > HIGH_SIMILARITY_THRESHOLD:
        if profile == "local":
            return "warn"
        return "error"
    # SIMILARITY_THRESHOLD < similarity <= HIGH_SIMILARITY_THRESHOLD
    if profile == "local":
        return "info"
    return "warn"


def _slug(path: str) -> str:
    """Derive a short deterministic slug from a file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:40]
