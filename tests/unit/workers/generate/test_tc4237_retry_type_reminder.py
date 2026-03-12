"""Tests for TC-4237: type-field reminder in generate worker retry paths.

Verifies that both retry paths in worker.py explicitly include the
'type' field reminder so the LLM cannot miss it when re-prompted:
  - enforce_block_spec Pass 2 (ENFORCEMENT OVERRIDE prepend)
  - _generate_section quality-check retry (_retry_additions)
"""
from __future__ import annotations

import asyncio
import inspect
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection
from launcher.workers.generate.worker import enforce_block_spec

# ─────────────────────────────────────────────────────────────────────────────
# Helpers (mirror test_enforcement.py helpers to avoid cross-file coupling)
# ─────────────────────────────────────────────────────────────────────────────

_TYPE_REMINDER_ENFORCE = (
    '- CRITICAL: Every block MUST include a "type" field'
)
_TYPE_REMINDER_QUALITY = (
    'CRITICAL: Every block in your JSON array MUST include a "type" field'
)
# In the raw source file the double-quotes around "type" are escaped as \"type\".
# Use a substring that is unambiguous in the raw source text.
_TYPE_REMINDER_QUALITY_SRC = (
    "Every block in your JSON array MUST include a"
)


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="test",
        platform="python",
        display_name="TestProduct",
        canonical_import="mypkg",
        repo_url="https://github.com/test/repo",
    )


def _make_section(blocks: list[BlockIR] | None = None) -> SectionIR:
    return SectionIR(
        section_id="intro",
        heading="Introduction",
        level=2,
        blocks=blocks or [BlockIR(type=BlockType.paragraph, content="x")],
    )


def _make_skel() -> SkeletonSection:
    return SkeletonSection(
        heading="Introduction",
        level=2,
        required=False,
        content_hint="",
        min_words=0,
        max_words=0,
    )


def _make_spec(required_block_types: list[str] | None = None, min_words: int = 0) -> MagicMock:
    spec = MagicMock()
    spec.required_block_types = required_block_types or []
    spec.min_words = min_words
    spec.requires_code = False
    spec.max_retries = 1
    return spec


def _make_context_with_llm() -> MagicMock:
    ctx = MagicMock()
    ctx.llm_config = MagicMock()
    ctx.config = MagicMock()
    ctx.config.golden = {"enabled": False}
    emitted: list = []
    ctx.emit_event = lambda event_type, data, worker="": emitted.append(
        {"event_type": event_type, "data": data, "worker": worker}
    )
    ctx._emitted = emitted
    return ctx


def _good_response(word_count: int = 220, include_code: bool = True) -> str:
    blocks = [
        {"type": "paragraph", "content": " ".join(["word"] * word_count), "claim_ids": []},
    ]
    if include_code:
        blocks.append({"type": "code", "content": "x = 1", "language": "python", "claim_ids": []})
    return json.dumps(blocks)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Change 2: enforce_block_spec Pass 2 prepend contains type reminder
# ─────────────────────────────────────────────────────────────────────────────

class TestEnforceBlockSpecTypeReminder:
    """TC-4237 Change 2: enforce_block_spec Pass 2 retry_prompt must contain type-field reminder."""

    def test_pass2_retry_prompt_contains_type_reminder_with_block_type_violation(self) -> None:
        """When spec requires 'code' and only paragraph present, Pass 2 prompt has type reminder."""
        section = _make_section()  # only paragraph block
        product = _make_product()
        ctx = _make_context_with_llm()
        skel = _make_skel()

        # Spec requires code AND min_words — gap-fill alone won't satisfy min_words
        spec = _make_spec(required_block_types=["code"], min_words=200)
        golden_index = MagicMock()
        golden_index.get_spec.return_value = spec

        captured: list[str] = []

        async def _capture_llm(prompt: str, context: object) -> str:
            captured.append(prompt)
            return _good_response()

        with patch("launcher.workers.generate.worker._call_llm", side_effect=_capture_llm):
            asyncio.run(enforce_block_spec(
                section, skel, "overview", golden_index, product, [], [], ctx,
                original_prompt="ORIGINAL PROMPT",
                richness_tier="A",
            ))

        assert len(captured) == 1, "Pass 2 LLM should have been called once"
        retry_prompt = captured[0]
        assert _TYPE_REMINDER_ENFORCE in retry_prompt, (
            f"Type-field reminder not found in Pass 2 retry_prompt.\n"
            f"Expected substring: {_TYPE_REMINDER_ENFORCE!r}\n"
            f"Prompt (first 500 chars): {retry_prompt[:500]!r}"
        )

    def test_pass2_retry_prompt_contains_type_reminder_with_only_minwords_violation(self) -> None:
        """When only min_words fails (no block type violation), type reminder is still present."""
        # Build a section with code but not enough words
        section = _make_section(blocks=[
            BlockIR(type=BlockType.paragraph, content="short"),
            BlockIR(type=BlockType.code, content="x = 1", language="python"),
        ])
        product = _make_product()
        ctx = _make_context_with_llm()
        skel = _make_skel()

        # Spec requires code (present) + min_words=500 (fail) — only word count violation
        spec = _make_spec(required_block_types=["code"], min_words=500)
        golden_index = MagicMock()
        golden_index.get_spec.return_value = spec

        captured: list[str] = []

        async def _capture_llm(prompt: str, context: object) -> str:
            captured.append(prompt)
            return _good_response()

        with patch("launcher.workers.generate.worker._call_llm", side_effect=_capture_llm):
            asyncio.run(enforce_block_spec(
                section, skel, "overview", golden_index, product, [], [], ctx,
                original_prompt="ORIGINAL PROMPT",
                richness_tier="B",
            ))

        assert len(captured) == 1
        retry_prompt = captured[0]
        assert _TYPE_REMINDER_ENFORCE in retry_prompt, (
            f"Type-field reminder must be present even when only min_words fails.\n"
            f"Expected substring: {_TYPE_REMINDER_ENFORCE!r}\n"
            f"Prompt (first 500 chars): {retry_prompt[:500]!r}"
        )

    def test_pass2_enforcement_override_header_not_truncated_by_cap(self) -> None:
        """REQUIRED FOR THIS RETRY instruction is not truncated by the prepend cap (500 chars)."""
        section = _make_section()
        product = _make_product()
        ctx = _make_context_with_llm()
        skel = _make_skel()

        spec = _make_spec(required_block_types=["code"], min_words=200)
        golden_index = MagicMock()
        golden_index.get_spec.return_value = spec

        captured: list[str] = []

        async def _capture_llm(prompt: str, context: object) -> str:
            captured.append(prompt)
            return _good_response()

        with patch("launcher.workers.generate.worker._call_llm", side_effect=_capture_llm):
            asyncio.run(enforce_block_spec(
                section, skel, "overview", golden_index, product, [], [], ctx,
                original_prompt="ORIGINAL PROMPT",
                richness_tier="A",
            ))

        assert len(captured) == 1
        retry_prompt = captured[0]
        assert "REQUIRED FOR THIS RETRY" in retry_prompt, (
            "Cap truncation removed 'REQUIRED FOR THIS RETRY' from prepend — raise cap further"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Guard test for Change 1: quality-check retry _retry_additions type reminder
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityRetryTypeReminderGuard:
    """TC-4237 Change 1: quality-check retry additions always contain type-field reminder.

    _generate_section is a complex async private function; we use source
    inspection as a guard to ensure the TC-4237 reminder string is present.
    """

    def test_quality_retry_type_reminder_string_present_in_source(self) -> None:
        """Source guard: TC-4237 type reminder string must exist in _generate_section source.

        Uses a raw-source-safe substring (no escaped-quote ambiguity).
        """
        import launcher.workers.generate.worker as w
        src = inspect.getsource(w)
        assert _TYPE_REMINDER_QUALITY_SRC in src, (
            f"TC-4237 quality-retry type reminder not found in worker.py source.\n"
            f"Expected substring: {_TYPE_REMINDER_QUALITY_SRC!r}"
        )

    def test_quality_retry_type_reminder_associated_with_tc4237_comment(self) -> None:
        """Source guard: TC-4237 comment must accompany the type-reminder addition."""
        import launcher.workers.generate.worker as w
        src = inspect.getsource(w)
        # Both the comment and the reminder must coexist
        assert "TC-4237" in src, "TC-4237 comment must be present in worker.py"
        assert _TYPE_REMINDER_QUALITY_SRC in src, (
            "TC-4237 type reminder must be present alongside the comment"
        )
