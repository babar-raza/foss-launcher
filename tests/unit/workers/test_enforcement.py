"""Tests for TC-3847 + GE-01: Enforcement Cascade — check_against_spec and enforce_block_spec."""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection
from launcher.workers.generate.section_validator import (
    EnforcementContext,
    check_against_spec,
    deduplicate_sections,
    enforce_block_spec as sv_enforce_block_spec,
)
from launcher.workers.generate.worker import _gap_fill_code_block, enforce_block_spec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(canonical_import: str = "mypackage") -> ProductIdentity:
    return ProductIdentity(
        family="test",
        platform="python",
        display_name="TestProduct",
        canonical_import=canonical_import,
        repo_url="https://github.com/test/repo",
    )


def _make_section(blocks: list[BlockIR] | None = None) -> SectionIR:
    return SectionIR(
        section_id="intro",
        heading="Introduction",
        level=2,
        blocks=blocks or [],
    )


def _make_paragraph_block(text: str) -> BlockIR:
    return BlockIR(type=BlockType.paragraph, content=text)


def _make_code_block(code: str = "x = 1") -> BlockIR:
    return BlockIR(type=BlockType.code, content=code, language="python")


def _make_spec(required_block_types: list[str] | None = None, min_words: int = 0) -> Any:
    spec = MagicMock()
    spec.required_block_types = required_block_types or []
    spec.min_words = min_words
    spec.requires_code = False
    spec.max_retries = 1  # must be int for range() in enforce_block_spec
    return spec


def _make_skel_section(heading: str = "Introduction") -> SkeletonSection:
    return SkeletonSection(
        heading=heading,
        level=2,
        required=False,
        content_hint="",
        min_words=0,
        max_words=0,
    )


def _make_context(with_llm: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.llm_config = MagicMock() if with_llm else None
    ctx.config = MagicMock()
    ctx.config.golden = {"enabled": False}
    emitted = []
    ctx.emit_event = lambda event_type, data, worker="": emitted.append(
        {"event_type": event_type, "data": data, "worker": worker}
    )
    ctx._emitted = emitted
    return ctx


def _make_pass2_llm_response(word_count: int = 220, include_code: bool = True) -> str:
    """Build a JSON LLM response that will satisfy typical Pass 2 specs."""
    blocks: list[dict] = [
        {"type": "paragraph", "content": " ".join(["word"] * word_count), "claim_ids": []},
    ]
    if include_code:
        blocks.append({"type": "code", "content": "x = 1", "language": "python", "claim_ids": []})
    return json.dumps(blocks)


# ---------------------------------------------------------------------------
# Tests for check_against_spec
# ---------------------------------------------------------------------------

def test_check_against_spec_none_spec_returns_true():
    """Test 1: check_against_spec with spec=None returns True (safe pass-through)."""
    section = _make_section([_make_paragraph_block("hello world")])
    result = check_against_spec(section, None)
    assert result is True


def test_check_against_spec_code_present_and_required_returns_true():
    """Test 2: returns True when code block present and 'code' in required_block_types."""
    spec = _make_spec(required_block_types=["paragraph", "code"], min_words=0)
    section = _make_section([
        _make_paragraph_block("Some text here"),
        _make_code_block("x = 1"),
    ])
    result = check_against_spec(section, spec)
    assert result is True


def test_check_against_spec_code_absent_and_required_returns_false():
    """Test 3: returns False when code block absent and 'code' in required_block_types."""
    spec = _make_spec(required_block_types=["paragraph", "code"], min_words=0)
    section = _make_section([_make_paragraph_block("Some text here")])
    result = check_against_spec(section, spec)
    assert result is False


def test_check_against_spec_word_count_below_min_returns_false():
    """Test 4: returns False when word count is below min_words."""
    words = " ".join(["word"] * 50)  # 50 words
    spec = _make_spec(required_block_types=[], min_words=100)
    section = _make_section([_make_paragraph_block(words)])
    result = check_against_spec(section, spec)
    assert result is False


def test_check_against_spec_word_count_at_or_above_min_returns_true():
    """Test 5: returns True when word count is at or above min_words."""
    words = " ".join(["word"] * 100)  # 100 words
    spec = _make_spec(required_block_types=[], min_words=50)
    section = _make_section([_make_paragraph_block(words)])
    result = check_against_spec(section, spec)
    assert result is True


# ---------------------------------------------------------------------------
# Tests for enforce_block_spec
# ---------------------------------------------------------------------------

def test_enforce_block_spec_golden_index_none_returns_none():
    """Test 6: enforce_block_spec returns (section_ir, 'none') when golden_index is None."""
    section = _make_section([_make_paragraph_block("text")])
    product = _make_product()
    ctx = _make_context()
    skel = _make_skel_section()

    result_ir, pass_used = asyncio.run(enforce_block_spec(
        section, skel, "overview", None, product, [], [], ctx,
    ))
    assert pass_used == "none"
    assert result_ir is section


def test_enforce_block_spec_spec_not_found_returns_none():
    """Test 7: enforce_block_spec returns (section_ir, 'none') when spec not found."""
    section = _make_section([_make_paragraph_block("text")])
    product = _make_product()
    ctx = _make_context()
    skel = _make_skel_section()

    golden_index = MagicMock()
    golden_index.get_spec.return_value = None  # No spec found

    result_ir, pass_used = asyncio.run(enforce_block_spec(
        section, skel, "overview", golden_index, product, [], [], ctx,
    ))
    assert pass_used == "none"
    assert result_ir is section


def test_enforce_block_spec_code_gap_filled_returns_pass1():
    """Test 8: returns (filled_ir, 'pass1') when code required and gap-filled successfully."""
    # Section with only a paragraph (no code)
    section = _make_section([_make_paragraph_block("Some documentation text here")])
    product = _make_product(canonical_import="aspose_cells_foss")
    ctx = _make_context()
    skel = _make_skel_section()

    # Spec requires code and no min_words constraint
    spec = _make_spec(required_block_types=["code"], min_words=0)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    result_ir, pass_used = asyncio.run(enforce_block_spec(
        section, skel, "overview", golden_index, product, [], [], ctx,
    ))
    assert pass_used == "pass1"
    # The returned section should now have a code block
    block_types = [b.type for b in result_ir.blocks]
    assert BlockType.code in block_types


def test_enforce_block_spec_pass1_fails_falls_back_to_pass3():
    """Test 9: returns (fallback_ir, 'pass3') when pass1 fails and LLM unavailable."""
    from launcher.models.claims import Claim, EvidenceAnchor

    # Section with no code and very few words (fails min_words too)
    section = _make_section([_make_paragraph_block("x")])
    product = _make_product(canonical_import="mypkg")
    ctx = _make_context()
    skel = _make_skel_section("Introduction")

    # Spec requires code AND min_words=200 — so gap-fill alone won't satisfy min_words
    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    result_ir, pass_used = asyncio.run(enforce_block_spec(
        section, skel, "overview", golden_index, product, [], [], ctx,
    ))
    # Pass1 would add a code block but min_words=200 won't be satisfied,
    # so it should fall through to pass3
    assert pass_used == "pass3"
    assert isinstance(result_ir, SectionIR)


def test_enforce_block_spec_golden_disabled_no_enforcement_log():
    """Test 10: When golden is disabled, no enforcement_log event is emitted."""
    # Simulate the wiring in _generate_page_ir: if golden is disabled, golden_index=None
    # and enforce_block_spec is not called, so no event should be emitted.
    section = _make_section([_make_paragraph_block("text")])
    product = _make_product()
    ctx = _make_context()
    skel = _make_skel_section()

    # With golden_index=None, enforce_block_spec always returns "none"
    result_ir, pass_used = asyncio.run(enforce_block_spec(
        section, skel, "overview", None, product, [], [], ctx,
    ))
    assert pass_used == "none"
    # No enforcement_log event should be emitted (caller only emits if pass_used != "none")
    enforcement_events = [
        e for e in ctx._emitted if e["event_type"] == "enforcement_log"
    ]
    assert len(enforcement_events) == 0


# ---------------------------------------------------------------------------
# GE-01: Pass 2 — LLM retry enforcement tests
# ---------------------------------------------------------------------------

def test_pass2_called_when_pass1_fails_tier_a():
    """Test 11: Pass 1 fails (code+min_words not both satisfied) and Tier A → Pass 2 called."""
    from launcher.models.claims import Claim, EvidenceAnchor

    section = _make_section([_make_paragraph_block("x")])  # 1 word, no code
    product = _make_product(canonical_import="mypkg")
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Introduction")

    # Spec requires BOTH code AND min_words=200 — gap-fill adds code but words still fail
    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    mock_response = _make_pass2_llm_response(word_count=220, include_code=True)

    with patch(
        "launcher.workers.generate.worker._call_llm",
        new_callable=AsyncMock,
        return_value=(mock_response, ""),
    ):
        result_ir, pass_used = asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt="ORIGINAL PROMPT",
            richness_tier="A",
        ))

    assert pass_used == "pass2_tier_ab", f"Expected pass2_tier_ab, got {pass_used}"
    block_types = {b.type.value for b in result_ir.blocks}
    assert "code" in block_types


def test_pass2_allowed_for_tier_c():
    """Test 12: TC-3881 G4: Tier C now allowed 1 LLM retry in Pass 2."""
    section = _make_section([_make_paragraph_block("x")])
    product = _make_product(canonical_import="mypkg")
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Introduction")

    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    mock_response = _make_pass2_llm_response(word_count=220, include_code=True)

    with patch(
        "launcher.workers.generate.worker._call_llm",
        new_callable=AsyncMock,
        return_value=(mock_response, ""),
    ) as mock_llm:
        result_ir, pass_used = asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt="ORIGINAL PROMPT",
            richness_tier="C",
        ))

    # Pass 2 must have been called (Tier C now allowed)
    mock_llm.assert_called_once()
    assert pass_used == "pass2_tier_c", f"Expected pass2_tier_c, got {pass_used}"


def test_pass2_satisfies_spec_returns_pass2():
    """Test 13: When Pass 2 retry LLM response satisfies spec, returns (retry_ir, 'pass2')."""
    section = _make_section([_make_paragraph_block("x")])
    product = _make_product(canonical_import="mypkg")
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Overview")

    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    mock_response = _make_pass2_llm_response(word_count=220, include_code=True)

    with patch(
        "launcher.workers.generate.worker._call_llm",
        new_callable=AsyncMock,
        return_value=(mock_response, ""),
    ):
        result_ir, pass_used = asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt="ORIGINAL",
            richness_tier="B",
        ))

    assert pass_used == "pass2_tier_ab"
    assert isinstance(result_ir, SectionIR)
    assert len(result_ir.blocks) >= 2  # paragraph + code from retry


def test_pass2_fails_falls_through_to_pass3():
    """Test 14: When Pass 2 LLM response still fails spec, falls through to Pass 3."""
    section = _make_section([_make_paragraph_block("x")])
    product = _make_product()
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Overview")

    # spec requires code + 200 words; mock returns only a short paragraph (no code)
    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    bad_response = json.dumps([{"type": "paragraph", "content": "too short", "claim_ids": []}])

    with patch(
        "launcher.workers.generate.worker._call_llm",
        new_callable=AsyncMock,
        return_value=(bad_response, ""),
    ):
        result_ir, pass_used = asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt="ORIGINAL",
            richness_tier="B",
        ))

    assert pass_used == "pass3", f"Expected pass3 after bad Pass 2 response, got {pass_used}"
    assert isinstance(result_ir, SectionIR)


def test_pass2_prepend_capped_at_300_chars():
    """Test 15: Retry prompt prepend is capped at 500 chars regardless of violations length."""
    section = _make_section([_make_paragraph_block("x")])
    product = _make_product()
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Overview")

    spec = _make_spec(required_block_types=["code"], min_words=200)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    original_prompt = "ORIGINAL_PROMPT_SENTINEL"
    captured_prompts: list[str] = []

    async def _capture_llm(prompt: str, ctx_: object) -> str | None:
        captured_prompts.append(prompt)
        return None  # return None so pass2 fails and falls to pass3

    with patch("launcher.workers.generate.worker._call_llm", side_effect=_capture_llm):
        asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt=original_prompt,
            richness_tier="A",
        ))

    assert captured_prompts, "Pass 2 should have called _call_llm"
    retry_prompt = captured_prompts[0]
    assert retry_prompt.endswith(original_prompt), "original_prompt appended at end"
    prepend_part = retry_prompt[: len(retry_prompt) - len(original_prompt)]
    assert len(prepend_part) <= 500, (
        f"Prepend length {len(prepend_part)} exceeds 500 char cap"
    )


# ---------------------------------------------------------------------------
# GE-02: Section-level asyncio.gather parallelism tests
# ---------------------------------------------------------------------------

class TestSectionGather:
    """GE-02: Per-page section loop uses asyncio.gather with _SECTION_CONCURRENCY."""

    def _make_page_plan(self) -> object:
        from launcher.models.plan import PlannedPage
        return PlannedPage(page_id="test-page", page_role="howto", title="Test Page")

    def _make_product(self) -> object:
        from launcher.models.product import ProductIdentity
        return ProductIdentity(
            family="test", platform="python",
            display_name="TestProduct", canonical_import="testpkg",
            repo_url="https://example.com",
        )

    def _make_ctx(self) -> object:
        ctx = MagicMock()
        ctx.llm_config = None  # No LLM → all sections use deterministic fallback
        ctx.config = MagicMock()
        ctx.config.golden = {"enabled": False}
        ctx.emit_event = MagicMock()
        ctx.run_dir = None
        ctx.run_id = "test"
        ctx.telemetry_client = None
        ctx.telemetry_trace_id = None
        ctx.heal_target_pages = None
        return ctx

    def test_sections_gathered_in_order(self):
        """Output section order matches skeleton section order."""
        from launcher.workers.generate.worker import _generate_page
        from launcher.shared.page_skeletons import resolve_skeleton

        page_plan = self._make_page_plan()
        product = self._make_product()
        ctx = self._make_ctx()

        page_ir, _, _, _, _, _ = asyncio.run(
            _generate_page(page_plan, product, [], [], [], ctx)
        )

        expected = resolve_skeleton("howto", "default")
        assert len(page_ir.sections) == len(expected)
        for sec, skel in zip(page_ir.sections, expected):
            assert sec.heading == skel.heading

    def test_one_section_failure_does_not_abort_page(self):
        """One section failure produces a fallback; other sections succeed."""
        from unittest.mock import patch as _patch
        from launcher.workers.generate.worker import _generate_page
        from launcher.shared.page_skeletons import resolve_skeleton
        from launcher.workers.generate import fallback as _fb_mod

        page_plan = self._make_page_plan()
        product = self._make_product()
        ctx = self._make_ctx()

        call_count = [0]
        orig_render = _fb_mod.render_section_deterministic

        def patched_render(skel_section, claims, snippets, prod):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Simulated section failure")
            return orig_render(skel_section, claims, snippets, prod)

        with _patch("launcher.workers.generate.fallback.render_section_deterministic", patched_render):
            page_ir, _, _, _, _, _ = asyncio.run(
                _generate_page(page_plan, product, [], [], [], ctx)
            )

        expected = resolve_skeleton("howto", "default")
        assert len(page_ir.sections) == len(expected)

    def test_section_concurrency_constant_defined(self):
        """_SECTION_CONCURRENCY module constant is defined and >= 1."""
        from launcher.workers.generate.worker import _SECTION_CONCURRENCY
        assert isinstance(_SECTION_CONCURRENCY, int)
        assert _SECTION_CONCURRENCY >= 1

    def test_cross_section_results_assembled_post_gather(self):
        """All sections assembled after gather; headings are non-empty strings."""
        from launcher.workers.generate.worker import _generate_page

        page_plan = self._make_page_plan()
        product = self._make_product()
        ctx = self._make_ctx()

        page_ir, _, _, _, _, _ = asyncio.run(
            _generate_page(page_plan, product, [], [], [], ctx)
        )

        for sec in page_ir.sections:
            assert isinstance(sec.heading, str) and sec.heading


class TestEnforcementContext:
    """V2SC-07: EnforcementContext dataclass and sv_enforce_block_spec."""

    def _product(self) -> ProductIdentity:
        return ProductIdentity(
            family="test", platform="python",
            display_name="TestProduct", canonical_import="testpkg",
            repo_url="https://github.com/test/repo",
        )

    def test_enforcement_context_instantiates(self) -> None:
        ctx = EnforcementContext(product=self._product())
        assert ctx.max_retries == 1
        assert ctx.section_heading == ""
        assert ctx.spec is None

    def test_enforcement_context_with_spec(self) -> None:
        from launcher.shared.golden_loader import GoldenBlockSpec
        spec = GoldenBlockSpec(required_block_types=["paragraph"], min_words=50, max_retries=3)
        ctx = EnforcementContext(product=self._product(), spec=spec, max_retries=3)
        assert ctx.max_retries == 3

    def test_sv_enforce_returns_blocks_when_spec_none(self) -> None:
        blocks = [BlockIR(type=BlockType.paragraph, content="hello")]
        ctx = EnforcementContext(product=self._product())
        result = sv_enforce_block_spec(blocks, ctx)
        assert result == blocks

    def test_sv_enforce_returns_original_when_no_llm(self) -> None:
        from launcher.shared.golden_loader import GoldenBlockSpec
        spec = GoldenBlockSpec(required_block_types=["code"], min_words=200, max_retries=2)
        blocks = [BlockIR(type=BlockType.paragraph, content="short")]
        ctx = EnforcementContext(product=self._product(), spec=spec, max_retries=2)
        # No _call_llm provided — must return original blocks, not empty
        result = sv_enforce_block_spec(blocks, ctx)
        assert result == blocks


def test_pass2_max_retries_2_calls_llm_twice():
    """V2CP-04: max_retries=2 on spec → Pass 2 loops twice before falling through."""
    from launcher.shared.golden_loader import GoldenBlockSpec

    section = _make_section([_make_paragraph_block("x")])
    product = _make_product(canonical_import="mypkg")
    ctx = _make_context(with_llm=True)
    skel = _make_skel_section("Introduction")

    # spec with max_retries=2 — Pass 2 should run twice
    spec = GoldenBlockSpec(required_block_types=["code"], min_words=200, max_retries=2)
    golden_index = MagicMock()
    golden_index.get_spec.return_value = spec

    # Always return a "bad" response (no code, too short) so Pass 2 loops all retries
    bad_response = json.dumps([{"type": "paragraph", "content": "short", "claim_ids": []}])

    with patch(
        "launcher.workers.generate.worker._call_llm",
        new_callable=AsyncMock,
        return_value=(bad_response, ""),
    ) as mock_llm:
        result_ir, pass_used = asyncio.run(enforce_block_spec(
            section, skel, "overview", golden_index, product, [], [], ctx,
            original_prompt="ORIGINAL PROMPT",
            richness_tier="A",
        ))

    # Should have called LLM exactly 2 times (max_retries=2)
    assert mock_llm.call_count == 2
    assert pass_used == "pass3"  # fell through to pass3 after both retries failed


class TestDeduplicateSections:
    """V2CP-03: deduplicate_sections runs on the complete section list post-gather."""

    def _section(self, heading: str, paragraphs: list[str]) -> SectionIR:
        blocks = [
            BlockIR(type=BlockType.paragraph, content=p)
            for p in paragraphs
        ]
        return SectionIR(section_id=heading.lower().replace(" ", "_"), heading=heading, blocks=blocks)

    def test_duplicate_paragraph_removed_from_later_section(self) -> None:
        repeated = "The API converts documents efficiently and accurately into many formats."
        s1 = self._section("Overview", [repeated])
        s2 = self._section("Summary", [repeated])
        result = deduplicate_sections([s1, s2])
        # s1 keeps its paragraph; s2 should not
        assert len(result[0].blocks) == 1
        assert len(result[1].blocks) == 0

    def test_section_order_preserved(self) -> None:
        s1 = self._section("Introduction", ["Unique intro content about the product."] * 1)
        s2 = self._section("Setup", ["Unique setup instructions for installation."] * 1)
        s3 = self._section("Usage", ["Unique usage examples demonstrating features."] * 1)
        result = deduplicate_sections([s1, s2, s3])
        assert [s.heading for s in result] == ["Introduction", "Setup", "Usage"]

    def test_exception_in_one_section_preserved(self) -> None:
        # A section with no model_copy (plain dict-like object) should not break dedup
        class FakeSection:
            def __init__(self, heading: str, content: str):
                self.heading = heading
                self.blocks = [BlockIR(type=BlockType.paragraph, content=content)]
        # Uses code path for non-pydantic sections (no model_copy)
        s1 = FakeSection("A", "Unique content about the installation process here.")
        s2 = FakeSection("B", "Different content about the configuration steps now.")
        result = deduplicate_sections([s1, s2])
        # Both sections should pass through unchanged (not identical)
        assert len(result) == 2
        assert result[0] is s1
        assert result[1] is s2

    def test_code_blocks_never_deduplicated(self) -> None:
        code = "```python\nimport testpkg\nresult = testpkg.process()\n```"
        s1 = self._section("Example 1", [])
        s1 = s1.model_copy(update={"blocks": [BlockIR(type=BlockType.code, content=code, language="python")]})
        s2 = self._section("Example 2", [])
        s2 = s2.model_copy(update={"blocks": [BlockIR(type=BlockType.code, content=code, language="python")]})
        result = deduplicate_sections([s1, s2])
        # Code blocks preserved in both sections
        assert len(result[0].blocks) == 1
        assert len(result[1].blocks) == 1


# ---------------------------------------------------------------------------
# TC-5305: _resolve_input_model wires "verify" → ScoutBundle
# ---------------------------------------------------------------------------

class TestTC5305VerifyInputModel:
    """TC-5305: _resolve_input_model('verify') must return ScoutBundle, not None.

    Before TC-5305 the verify case was missing, causing _resolve_input_model
    to fall through to model=None and wrap the input in _DictProxy instead of
    the validated ScoutBundle type.
    """

    def test_verify_resolves_to_scout_bundle(self):
        """_resolve_input_model('verify') returns ScoutBundle (not None)."""
        from launcher.orchestrator.graph_builder import _resolve_input_model
        from launcher.models.scout import ScoutBundle
        model = _resolve_input_model("verify")
        assert model is ScoutBundle, (
            f"Expected ScoutBundle for 'verify', got {model!r}. "
            "TC-5305: verify worker must be wired to ScoutBundle input model."
        )

    def test_understand_still_resolves_to_scout_bundle(self):
        """Regression guard: 'understand' still resolves to ScoutBundle after TC-5305."""
        from launcher.orchestrator.graph_builder import _resolve_input_model
        from launcher.models.scout import ScoutBundle
        model = _resolve_input_model("understand")
        assert model is ScoutBundle

    def test_verify_model_not_none(self):
        """_resolve_input_model('verify') must not return None."""
        from launcher.orchestrator.graph_builder import _resolve_input_model
        model = _resolve_input_model("verify")
        assert model is not None, (
            "TC-5305: verify worker returned None from _resolve_input_model — "
            "graph builder will wrap input in _DictProxy, bypassing type validation."
        )
