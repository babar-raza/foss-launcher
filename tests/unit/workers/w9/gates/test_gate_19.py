"""Tests for W9 Gate 19: Cross-Page Redundancy Check (TC-2372).

Pages in the same section (parent directory) with >60% Jaccard word overlap
are flagged with G19-001 warn.

NOTE: The tokenizer uses r'\\b[a-z]{3,}\\b' so test words must be all-lowercase
      ASCII letters without digits (e.g. "install" not "install2").
"""
from __future__ import annotations

from launch.workers.w9_validator.gates.gate_19_redundancy import run_gate_19


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page(path: str, content: str, role: str = "tutorial") -> dict:
    return {"path": path, "content": content, "page_role": role}


def _body(words: list) -> str:
    return "# Title\n\n" + " ".join(words) + "\n"


# Words that the tokenizer (r'\b[a-z]{3,}\b') will recognise — no digits
_SHARED = [
    "python", "library", "install", "configure", "feature",
    "documentation", "example", "implement", "integrate", "tutorial",
    "create", "enable", "support", "process", "convert",
]  # 15 shared words

_UNIQUE_A = [
    "authenticate", "credential", "session", "token", "encrypt",
    "authorize", "identity", "permission", "certificate", "validate",
]  # 10 words unique to A

_UNIQUE_B = [
    "database", "query", "schema", "migrate", "transaction",
    "connection", "repository", "primary", "aggregate", "relation",
]  # 10 words unique to B


# ---------------------------------------------------------------------------
# Test 1: High overlap same section → G19-001 warn
# ---------------------------------------------------------------------------

def test_high_overlap_same_section_warns():
    """Two pages in the same dir with >60% word overlap → G19-001."""
    # 15 shared + 2 unique each → Jaccard = 15/17 ≈ 0.88 > 0.6
    content_a = _body(_SHARED + _UNIQUE_A[:2])
    content_b = _body(_SHARED + _UNIQUE_B[:2])

    pages = [
        _page("/site/section/page_a.md", content_a),
        _page("/site/section/page_b.md", content_b),
    ]

    issues = run_gate_19(pages)

    redundancy_issues = [i for i in issues if i.get("error_code") == "G19-001"]
    assert len(redundancy_issues) >= 1
    assert redundancy_issues[0]["severity"] == "warn"
    assert redundancy_issues[0]["gate"] == "gate_19_redundancy"
    # At least one page filename should appear in the message
    msg = redundancy_issues[0]["message"]
    assert "page_a" in msg or "page_b" in msg


# ---------------------------------------------------------------------------
# Test 2: Low overlap same section → no issue
# ---------------------------------------------------------------------------

def test_low_overlap_passes():
    """Two pages in the same dir with <60% word overlap → no issue."""
    # 2 shared + 10 unique each → Jaccard ≈ 2/22 ≈ 0.09 < 0.6
    content_a = _body(_SHARED[:2] + _UNIQUE_A)
    content_b = _body(_SHARED[:2] + _UNIQUE_B)

    pages = [
        _page("/site/section/page_a.md", content_a),
        _page("/site/section/page_b.md", content_b),
    ]

    issues = run_gate_19(pages)

    redundancy_issues = [i for i in issues if i.get("error_code") == "G19-001"]
    assert len(redundancy_issues) == 0


# ---------------------------------------------------------------------------
# Test 3: Different sections → not compared even with high overlap
# ---------------------------------------------------------------------------

def test_different_sections_not_compared():
    """Pages in different parent directories are not compared."""
    content_a = _body(_SHARED + _UNIQUE_A[:2])
    content_b = _body(_SHARED + _UNIQUE_B[:2])

    pages = [
        _page("/site/section_a/page.md", content_a),  # different parent dirs
        _page("/site/section_b/page.md", content_b),
    ]

    issues = run_gate_19(pages)

    redundancy_issues = [i for i in issues if i.get("error_code") == "G19-001"]
    assert len(redundancy_issues) == 0


# ---------------------------------------------------------------------------
# Test 4: Single page per section → no issue
# ---------------------------------------------------------------------------

def test_single_page_per_section_passes():
    """One page per section → pairwise comparison never runs → no issue."""
    content = _body(_SHARED)

    pages = [
        _page("/site/sec_a/page.md", content),
        _page("/site/sec_b/page.md", content),  # same content but different dirs
    ]

    issues = run_gate_19(pages)

    redundancy_issues = [i for i in issues if i.get("error_code") == "G19-001"]
    assert len(redundancy_issues) == 0
