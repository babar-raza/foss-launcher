"""Gate 19: Cross-Page Redundancy Check.

Pages within the same section (parent directory) that share more than 60% of their
significant word content (Jaccard similarity, after stripping frontmatter, code
blocks, and stopwords) are flagged with a warn-level G19-001 issue.

This catches LLM paraphrasing: the common problem where the model produces two
pages in the same section that cover identical material in slightly different words.

The gate always passes (warn-only — no blocker/error severity).

TC-2372: Gate 19 Cross-Page Redundancy (RCA Part 4-E)

Per specs/09_validation_gates.md.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


# Jaccard similarity threshold above which pages are flagged as redundant
SIMILARITY_THRESHOLD = 0.6

# Common English words that carry no discriminating signal
STOPWORDS = frozenset({
    "the", "and", "or", "of", "a", "an", "in", "is", "to", "for",
    "with", "that", "this", "are", "be", "have", "from", "by", "at",
    "as", "on", "it", "its", "not", "but", "can", "you", "we",
    "our", "your", "will", "all", "use", "used", "using", "how",
    "when", "what", "where", "which", "then", "also", "more",
    "than", "about", "has", "any", "each", "into", "between",
})


def run_gate_19(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute Gate 19: Cross-Page Redundancy Check.

    Groups pages by their parent directory (section), then performs pairwise
    Jaccard similarity on significant word sets.  Pairs exceeding
    ``SIMILARITY_THRESHOLD`` receive a warn-level G19-001 issue.

    Args:
        pages: List of page dicts with keys ``path``, ``content``, ``page_role``.
               This is the same list built for Gate 16 in worker.py.

    Returns:
        List of issue dicts (severity ``warn`` only — gate always passes).
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
                union_size = len(a | b)
                if union_size == 0:
                    continue
                similarity = len(a & b) / union_size
                if similarity > SIMILARITY_THRESHOLD:
                    path_a = section_pages[i].get("path", "")
                    path_b = section_pages[j].get("path", "")
                    name_a = os.path.basename(path_a)
                    name_b = os.path.basename(path_b)
                    slug_a = _slug(path_a)
                    slug_b = _slug(path_b)
                    issues.append({
                        "issue_id": f"gate19_redundancy_{slug_a}_{slug_b}",
                        "gate": "gate_19_redundancy",
                        "severity": "warn",
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

def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the top of content."""
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    if end == -1:
        return content
    return content[end + 4:]


def _strip_code_blocks(content: str) -> str:
    """Replace fenced code block lines with blank lines."""
    lines = content.split("\n")
    result: List[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_block = not in_block
            result.append("")
        elif in_block:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _tokenize(text: str) -> List[str]:
    """Tokenize text into significant words (lowercase, ≥3 chars, no stopwords)."""
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


def _slug(path: str) -> str:
    """Derive a short deterministic slug from a file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:40]
