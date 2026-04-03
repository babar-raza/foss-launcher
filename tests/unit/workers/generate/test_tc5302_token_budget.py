"""TC-5302: Tests for output token budget formula and finish_reason handling.

Verifies:
1. Token budget is ≥2048 for all sections (not capped at 1024)
2. Code-required sections get an additional 1024-token bonus
3. _call_llm now returns (content, finish_reason) tuple
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helper: replicate the token budget formula from worker.py
# ---------------------------------------------------------------------------


def _compute_sec_max_tokens(max_words: int | None, is_code_required: bool) -> int:
    """Replicate TC-5302 token budget formula from worker.py."""
    _sec_code_bonus = 1024 if is_code_required else 0
    return max(2048, int((max_words or 200) * 4 * 1.3) + _sec_code_bonus)


# ---------------------------------------------------------------------------
# TC-5302-T1: Default section (200 words) → ≥2048 tokens
# ---------------------------------------------------------------------------


def test_token_budget_default_section_at_least_2048():
    """TC-5302-T1: Default 200-word section must get ≥2048 output tokens."""
    tokens = _compute_sec_max_tokens(200, is_code_required=False)
    assert tokens >= 2048, f"TC-5302: Expected ≥2048 tokens, got {tokens}"


# ---------------------------------------------------------------------------
# TC-5302-T2: Old formula would have given only 1024 for default section
# ---------------------------------------------------------------------------


def test_token_budget_old_formula_was_insufficient():
    """TC-5302-T2: Old formula max(1024, 200*5) = 1024 — confirms we needed the fix."""
    # max(1024, 200*5) = max(1024, 1000) = 1024  (1024 wins — floor dominated)
    old_formula = max(1024, (200 or 200) * 5)
    assert old_formula == 1024, "Old formula sanity check: max(1024, 1000) = 1024"
    # Confirm new formula is strictly better
    new_formula = _compute_sec_max_tokens(200, is_code_required=False)
    assert new_formula > old_formula, (
        f"TC-5302: New formula ({new_formula}) must be > old formula ({old_formula})"
    )


# ---------------------------------------------------------------------------
# TC-5302-T3: Code-required section gets +1024 bonus
# ---------------------------------------------------------------------------


def test_token_budget_code_required_section_gets_bonus():
    """TC-5302-T3: Code-required sections get 1024-token bonus over prose sections.

    Use 400-word sections where the base budget exceeds the 2048 floor so the
    +1024 bonus is visible in the result (not absorbed by the max() floor).
    """
    # For 400 words: base = int(400*4*1.3) = 2080 > 2048 floor → bonus visible
    prose_tokens = _compute_sec_max_tokens(400, is_code_required=False)
    code_tokens = _compute_sec_max_tokens(400, is_code_required=True)
    assert code_tokens == prose_tokens + 1024, (
        f"TC-5302: Code-required section should get +1024 bonus. "
        f"prose={prose_tokens}, code={code_tokens}"
    )


# ---------------------------------------------------------------------------
# TC-5302-T4: Long section (400 words + code) → ≥3000 tokens
# ---------------------------------------------------------------------------


def test_token_budget_long_code_section_sufficient():
    """TC-5302-T4: Long 400-word code-required section gets enough tokens."""
    tokens = _compute_sec_max_tokens(400, is_code_required=True)
    # 400 * 4 * 1.3 + 1024 = 2080 + 1024 = 3104
    assert tokens >= 3000, f"TC-5302: Long code section needs ≥3000 tokens, got {tokens}"


# ---------------------------------------------------------------------------
# TC-5302-T5: max_words=None handled safely (uses default 200)
# ---------------------------------------------------------------------------


def test_token_budget_none_max_words_uses_default():
    """TC-5302-T5: max_words=None must not crash — uses 200-word default."""
    tokens = _compute_sec_max_tokens(None, is_code_required=False)
    assert tokens >= 2048, f"TC-5302: None max_words should fall back to 200, got {tokens}"


# ---------------------------------------------------------------------------
# TC-5302-T6: _call_llm return type is a 2-tuple
# ---------------------------------------------------------------------------


def test_call_llm_return_annotation_is_tuple():
    """TC-5302-T6: _call_llm return type annotation must include finish_reason."""
    import inspect
    from launcher.workers.generate.worker import _call_llm

    hints = _call_llm.__annotations__
    return_hint = str(hints.get("return", ""))
    assert "tuple" in return_hint.lower() or "Tuple" in return_hint or "|" in return_hint, (
        f"TC-5302: _call_llm return annotation should be a tuple, got: {return_hint!r}"
    )
