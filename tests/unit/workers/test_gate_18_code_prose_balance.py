"""Tests for W9 Gate 18: Code-Prose Balance Check (TC-2371).

For roles requiring code (tutorial, feature_showcase, comprehensive_guide,
api_reference), verifies that there is ≥1 code block per 400 prose words.
"""
from __future__ import annotations

from launch.workers.w9_validator.gates.gate_18_code_prose_balance import run_gate_18


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page(path: str, content: str, role: str) -> dict:
    return {"path": path, "content": content, "page_role": role}


def _prose(words: int) -> str:
    """Generate a body with approximately `words` distinct words."""
    word_list = [f"word{i}" for i in range(words)]
    return " ".join(word_list)


def _code_block(lang: str = "python", lines: int = 3) -> str:
    code = "\n".join(f"line{i} = {i}" for i in range(lines))
    return f"```{lang}\n{code}\n```"


# ---------------------------------------------------------------------------
# Test 1: tutorial with no code blocks → G18-001 warn
# ---------------------------------------------------------------------------

def test_tutorial_no_code_blocks_warns():
    """A 500-word tutorial with 0 code blocks should emit G18-001."""
    content = f"---\ntitle: T\n---\n\n# Tutorial\n\n{_prose(500)}\n"
    pages = [_page("/site/tut/index.md", content, "tutorial")]

    issues = run_gate_18(pages)

    assert len(issues) == 1
    assert issues[0]["error_code"] == "G18-001"
    assert issues[0]["severity"] == "warn"
    assert issues[0]["gate"] == "gate_18_code_prose_balance"
    assert "tutorial" in issues[0]["message"]


# ---------------------------------------------------------------------------
# Test 2: tutorial with adequate code blocks → no issue
# ---------------------------------------------------------------------------

def test_tutorial_adequate_code_blocks_passes():
    """A 500-word tutorial with 2 code blocks (≥1 per 400 words) → no issue."""
    prose_chunk = _prose(250)
    code = _code_block()
    content = (
        f"---\ntitle: T\n---\n\n# Tutorial\n\n"
        f"{prose_chunk}\n\n{code}\n\n{prose_chunk}\n\n{code}\n"
    )
    pages = [_page("/site/tut/index.md", content, "tutorial")]

    issues = run_gate_18(pages)

    assert issues == []


# ---------------------------------------------------------------------------
# Test 3: FAQ page (not in CODE_REQUIRED_ROLES) → no issue
# ---------------------------------------------------------------------------

def test_faq_role_not_checked():
    """FAQ pages are not in CODE_REQUIRED_ROLES — no check performed."""
    content = f"---\ntitle: FAQ\n---\n\n# FAQ\n\n{_prose(600)}\n"
    pages = [_page("/site/faq/index.md", content, "faq")]

    issues = run_gate_18(pages)

    assert issues == []


# ---------------------------------------------------------------------------
# Test 4: short page (< 400 words) → still requires ≥1 code block
# ---------------------------------------------------------------------------

def test_short_page_requires_one_block():
    """Even a 50-word tutorial requires at least 1 code block (min=1 rule)."""
    content = f"---\ntitle: T\n---\n\n# Tutorial\n\n{_prose(50)}\n"
    pages = [_page("/site/tut/short.md", content, "tutorial")]

    issues = run_gate_18(pages)

    assert len(issues) == 1
    assert issues[0]["error_code"] == "G18-001"
    # Verify the required count is 1 (max(1, 50//400) = 1)
    assert "≥1" in issues[0]["message"]
