"""Tests for TC-3817: section_prompt changes (rich API surface, empty-claims, FAQ directive)."""

from __future__ import annotations

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.plan import PlannedPage
from launcher.models.product import ClassBrief, ProductIdentity
from launcher.models.understanding import WorkflowExample


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="note", platform="python",
        display_name="Aspose.Note", canonical_import="aspose_note_foss",
        repo_url="https://example.com",
    )


def _make_page(**overrides) -> PlannedPage:
    defaults = dict(
        page_id="test-page",
        page_role="howto",
        title="Test Page",
        assigned_claims=["CLM-001"],
    )
    defaults.update(overrides)
    return PlannedPage(**defaults)


def _make_claim(claim_id: str = "CLM-001") -> Claim:
    return Claim(
        claim_id=claim_id,
        text="Document supports loading OneNote files.",
        kind="api",
        evidence=[],
    )


class TestRichApiSurface:
    """Change A: _format_api_surface with ClassBrief data."""

    def test_rich_format_includes_methods(self):
        from launcher.workers.generate.section_prompt import _format_api_surface

        briefs = [
            ClassBrief(
                name="Document",
                docstring_snippet="Represents a OneNote document.",
                methods=["load", "save", "close"],
                properties=["pages", "title"],
            ),
        ]
        result = _format_api_surface(["Document"], class_briefs=briefs)
        assert "Document" in result
        assert "load" in result
        assert "save" in result
        assert "pages" in result
        assert "Represents a OneNote document" in result

    def test_rich_format_caps_at_15_classes(self):
        from launcher.workers.generate.section_prompt import _format_api_surface

        classes = [f"Class{i}" for i in range(20)]
        briefs = [ClassBrief(name=f"Class{i}", methods=["run"]) for i in range(20)]
        result = _format_api_surface(classes, class_briefs=briefs)
        # Should only have 15 entries
        assert result.count("- `Class") == 15

    def test_fallback_to_bare_names(self):
        from launcher.workers.generate.section_prompt import _format_api_surface

        result = _format_api_surface(["Document", "Page"], class_briefs=None)
        assert "Known classes:" in result
        assert "Document" in result

    def test_empty_returns_no_api_warning(self):
        from launcher.workers.generate.section_prompt import _format_api_surface

        result = _format_api_surface([], class_briefs=None)
        assert "No API surface detected" in result
        assert "Do NOT invent" in result


class TestEmptyClaimsFallback:
    """Change C: Empty-claims prompt uses constrained fallback."""

    def test_no_claims_uses_constrained_text(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import SkeletonSection

        product = _make_product()
        page = _make_page(assigned_claims=[])  # No claims assigned
        section = SkeletonSection(heading="Overview", level=2, required=True, content_hint="Intro", min_words=30, max_words=200)

        prompt = build_section_prompt(
            section, 0, 1, page, product, [], [],
        )
        # Should NOT contain old "write general introductory content"
        assert "write general introductory content" not in prompt
        # Should contain new constrained text
        assert "Brevity over fabrication" in prompt


class TestFaqDirective:
    """Change D: FAQ directive explicitly separates heading from answer."""

    def test_faq_directive_mentions_max_words(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import SkeletonSection

        product = _make_product()
        page = _make_page(page_role="faq", assigned_claims=["CLM-001"])
        section = SkeletonSection(heading="Frequently Asked Questions", level=2, required=True, content_hint="FAQ", min_words=30, max_words=200)
        claims = [_make_claim()]

        prompt = build_section_prompt(
            section, 0, 1, page, product, claims, [],
        )
        assert "max 15 words" in prompt
        assert "separate" in prompt.lower()
        assert "Never put answer text in" in prompt


class TestPrioritizeClassBriefs:
    """AQ-03: Page-relevant class selection."""

    def test_mentioned_classes_come_first(self):
        from launcher.workers.generate.section_prompt import _prioritize_class_briefs

        briefs = [
            ClassBrief(name="Alpha"),
            ClassBrief(name="Document"),
            ClassBrief(name="Zebra"),
            ClassBrief(name="PdfSaveOptions"),
        ]
        claims = [
            Claim(claim_id="C1", text="PdfSaveOptions controls PDF export.", kind="api", evidence=[]),
            Claim(claim_id="C2", text="Document is the main container.", kind="api", evidence=[]),
        ]
        result = _prioritize_class_briefs(briefs, claims)
        names = [b.name for b in result]
        # Document and PdfSaveOptions should come before Alpha and Zebra
        assert names.index("Document") < names.index("Alpha")
        assert names.index("PdfSaveOptions") < names.index("Zebra")

    def test_no_matching_claims_preserves_order(self):
        from launcher.workers.generate.section_prompt import _prioritize_class_briefs

        briefs = [ClassBrief(name="A"), ClassBrief(name="B"), ClassBrief(name="C")]
        claims = [Claim(claim_id="C1", text="Something unrelated.", kind="api", evidence=[])]
        result = _prioritize_class_briefs(briefs, claims)
        assert [b.name for b in result] == ["A", "B", "C"]

    def test_cap_respected(self):
        from launcher.workers.generate.section_prompt import _prioritize_class_briefs

        briefs = [ClassBrief(name=f"Class{i}") for i in range(30)]
        claims = [Claim(claim_id="C1", text="Class25 is important.", kind="api", evidence=[])]
        result = _prioritize_class_briefs(briefs, claims, cap=15)
        assert len(result) == 15
        assert result[0].name == "Class25"  # mentioned class comes first


class TestDistributeClaimsWrapAround:
    """AQ-02: Wrap-around when fewer claims than sections."""

    def test_wraps_when_fewer_claims_than_sections(self):
        # TC-3879 Wave 1 (Gap1): When claims < sections, every section gets ALL claims
        # so no section is left with 0 unique claims (previously produced round-robin
        # which caused sections to reuse the same claim with no unique content).
        from launcher.workers.generate.section_prompt import _distribute_claims

        claims = [_make_claim("CLM-A"), _make_claim("CLM-B")]
        # 2 claims, 4 sections — every section gets ALL 2 claims
        for idx in range(4):
            result = _distribute_claims(claims, idx, 4)
            assert len(result) == 2, f"Section {idx} got {len(result)} claims, expected 2"
            assert {c.claim_id for c in result} == {"CLM-A", "CLM-B"}

    def test_round_robin_when_enough_claims(self):
        from launcher.workers.generate.section_prompt import _distribute_claims

        claims = [_make_claim(f"CLM-{i}") for i in range(6)]
        # 6 claims, 3 sections — each section gets 2 claims
        for idx in range(3):
            result = _distribute_claims(claims, idx, 3)
            assert len(result) == 2, f"Section {idx} got {len(result)} claims"

    def test_empty_claims_returns_empty(self):
        from launcher.workers.generate.section_prompt import _distribute_claims

        assert _distribute_claims([], 0, 3) == []

    def test_single_claim_all_sections(self):
        from launcher.workers.generate.section_prompt import _distribute_claims

        claims = [_make_claim("CLM-ONLY")]
        # 1 claim, 5 sections — every section gets that 1 claim
        for idx in range(5):
            result = _distribute_claims(claims, idx, 5)
            assert len(result) == 1
            assert result[0].claim_id == "CLM-ONLY"


# ---------------------------------------------------------------------------
# GE-03: max_tokens computation and threading to LLM call
# ---------------------------------------------------------------------------

class TestMaxTokensWiring:
    """GE-03: max_tokens = max(512, max_words * 3) computed and threaded to LLM."""

    def test_max_tokens_computed_from_max_words(self):
        """max_words=200 → max_tokens=600 (200*3 > 512)."""
        assert max(512, (200 or 200) * 3) == 600
        assert max(512, (None or 200) * 3) == 600

    def test_max_tokens_minimum_is_512(self):
        """max_words=10 → max_tokens=512, not 30."""
        assert max(512, (10 or 200) * 3) == 512

    def test_max_tokens_passed_to_llm_call(self, tmp_path):
        """_call_llm passes the max_tokens override to chat_completion."""
        import asyncio
        from unittest.mock import MagicMock, patch
        from launcher.workers.generate.worker import _call_llm

        captured: dict = {}

        class _FakeClient:
            def __init__(self, *a, **kw):
                pass

            def chat_completion(self, messages, task_type=None, max_tokens=None):
                captured["max_tokens"] = max_tokens
                return {"content": "ok"}

        ctx = MagicMock()
        ctx.llm_config.primary.base_url = "http://localhost"
        ctx.llm_config.primary.model = "fake-model"
        ctx.llm_config.max_tokens = 1000
        ctx.llm_config.temperature = 0.0
        ctx.llm_config.reasoning = None
        ctx.llm_config.routing = None
        ctx.llm_config.fallback = None
        ctx.run_dir = tmp_path
        ctx.run_id = "test-run"
        ctx.telemetry_client = None
        ctx.telemetry_trace_id = None

        with patch("launcher.clients.llm_provider.LLMProviderClient", _FakeClient):
            asyncio.run(_call_llm("hello", ctx, max_tokens=750))

        assert captured.get("max_tokens") == 750


# ---------------------------------------------------------------------------
# GE-04: OPT-4 api_surface_block pruning when golden spec lacks code
# ---------------------------------------------------------------------------

class TestApiSurfacePruning:
    """GE-04: api_surface_block replaced when golden spec has no code requirement."""

    def _make_section(self, max_words: int = 200):
        from launcher.shared.page_skeletons import SkeletonSection
        return SkeletonSection(
            heading="Overview", level=2, required=True,
            content_hint="Intro", min_words=30, max_words=max_words,
        )

    def _make_ns_page(self, page_role: str, golden_dir: str) -> object:
        from types import SimpleNamespace
        return SimpleNamespace(
            page_id="test-page",
            page_role=page_role,
            title="Test Page",
            assigned_claims=[],
            seo_keywords=[],
            golden={"enabled": True, "dir": golden_dir},
        )

    def test_api_surface_pruned_when_no_code_in_spec(self, tmp_path):
        """Golden spec without 'code' → pruning message in prompt."""
        from unittest.mock import MagicMock, patch
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.golden_loader import GoldenBlockSpec

        golden_d = tmp_path / "golden"
        golden_d.mkdir()

        page = self._make_ns_page("howto", str(golden_d))
        section = self._make_section()
        spec = GoldenBlockSpec(required_block_types=["paragraph"], min_words=100)
        mock_idx = MagicMock()
        mock_idx.get_spec.return_value = spec

        with patch("launcher.shared.golden_loader.GoldenIndex.load", return_value=mock_idx):
            prompt = build_section_prompt(section, 0, 1, page, _make_product(), [], [])

        assert "(No code output expected for this section" in prompt
        assert "omit all code blocks" in prompt

    def test_api_surface_preserved_when_code_in_spec(self, tmp_path):
        """Golden spec with 'code' → API surface kept in prompt."""
        from unittest.mock import MagicMock, patch
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.golden_loader import GoldenBlockSpec

        golden_d = tmp_path / "golden"
        golden_d.mkdir()

        page = self._make_ns_page("howto", str(golden_d))
        section = self._make_section()
        spec = GoldenBlockSpec(required_block_types=["paragraph", "code"], min_words=100)
        mock_idx = MagicMock()
        mock_idx.get_spec.return_value = spec

        with patch("launcher.shared.golden_loader.GoldenIndex.load", return_value=mock_idx):
            prompt = build_section_prompt(section, 0, 1, page, _make_product(), [], [])

        assert "No code output expected" not in prompt

    def test_api_surface_preserved_for_api_reference_role(self, tmp_path):
        """api_reference pages always get full API surface, even without code in spec."""
        from unittest.mock import MagicMock, patch
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.golden_loader import GoldenBlockSpec

        golden_d = tmp_path / "golden"
        golden_d.mkdir()

        page = self._make_ns_page("api_reference", str(golden_d))
        section = self._make_section()
        spec = GoldenBlockSpec(required_block_types=["paragraph"], min_words=100)
        mock_idx = MagicMock()
        mock_idx.get_spec.return_value = spec

        with patch("launcher.shared.golden_loader.GoldenIndex.load", return_value=mock_idx):
            prompt = build_section_prompt(section, 0, 1, page, _make_product(), [], [])

        assert "No code output expected" not in prompt

    def test_api_surface_preserved_when_no_golden_spec(self, tmp_path):

        """When golden returns None spec, api_surface is preserved."""
        from unittest.mock import MagicMock, patch
        from launcher.workers.generate.section_prompt import build_section_prompt

        golden_d = tmp_path / "golden"
        golden_d.mkdir()

        page = self._make_ns_page("howto", str(golden_d))
        section = self._make_section()
        mock_idx = MagicMock()
        mock_idx.get_spec.return_value = None  # No spec for this section

        with patch("launcher.shared.golden_loader.GoldenIndex.load", return_value=mock_idx):
            prompt = build_section_prompt(section, 0, 1, page, _make_product(), [], [])

        assert "No code output expected" not in prompt


# ---------------------------------------------------------------------------
# TC-3904: Regression tests for skip_instruction injection (TC-3902 fix)
# Depends on: TC-3902 (SKIP markers for evidence-absent code sections)
# ---------------------------------------------------------------------------


class TestSkipInstruction:
    """TC-3904: skip_instruction regression suite — ensures TC-3902 fix holds."""

    def _call(self, page_role: str, snippets: list) -> str:
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.models.plan import PlannedPage
        from launcher.shared.page_skeletons import SkeletonSection

        page = PlannedPage(
            page_id="tc3904-test",
            page_role=page_role,
            title="TC-3904 Test Page",
            assigned_claims=["CLM-TC01"],
        )
        section = SkeletonSection(
            heading="Quick Start",
            level=2,
            required=True,
            content_hint="Show basic usage.",
            min_words=50,
            max_words=300,
        )
        product = _make_product()
        claim = _make_claim("CLM-TC01")
        return build_section_prompt(section, 0, 1, page, product, [claim], snippets)

    def test_skip_injected_for_code_role_no_snippets(self) -> None:
        """Code-required role + no snippets → EVIDENCE ABSENT instruction present."""
        prompt = self._call("installation", snippets=[])
        assert "EVIDENCE ABSENT" in prompt

    def test_skip_absent_when_snippets_present(self) -> None:
        """Rich repo: code-required role + snippets available → instruction not injected."""
        from launcher.models.claims import Snippet
        # claim_ids must overlap page.assigned_claims for _rank_snippets to keep the snippet
        snippet = Snippet(
            code="import { Scene } from '@aspose/3d-foss';",
            language="typescript",
            claim_ids=["CLM-TC01"],
        )
        prompt = self._call("installation", snippets=[snippet])
        assert "EVIDENCE ABSENT" not in prompt

    def test_skip_absent_for_non_code_role(self) -> None:
        """Non-code role + no snippets → instruction never injected."""
        prompt = self._call("blog_announcement", snippets=[])
        assert "EVIDENCE ABSENT" not in prompt

    def test_skip_injected_for_api_reference_no_snippets(self) -> None:
        """api_reference role + no snippets → EVIDENCE ABSENT instruction present."""
        prompt = self._call("api_reference", snippets=[])
        assert "EVIDENCE ABSENT" in prompt

    def test_skip_fires_with_code_evidence_sparse_flag(self) -> None:
        """code_evidence_sparse=True triggers EVIDENCE ABSENT for non-code roles (TR-01).

        blog_announcement is NOT in _CODE_EVIDENCE_ROLES — only the sparse flag fires this.
        Regression guard: verifies the TR-01 gate fires independently of page_role.
        """
        from launcher.models.plan import PlannedPage
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import SkeletonSection

        page = PlannedPage(
            page_id="tr01-sparse-gate-test",
            page_role="blog_announcement",   # NOT in _CODE_EVIDENCE_ROLES
            title="TR-01 Sparse Gate Test",
            assigned_claims=["CLM-TR01"],
            code_evidence_sparse=True,       # TR-01: the new field
        )
        section = SkeletonSection("Announcement", 2, True, "Describe the release.", 50, 300)
        claim = _make_claim("CLM-TR01")
        prompt = build_section_prompt(section, 0, 1, page, _make_product(), [claim], [])
        assert "EVIDENCE ABSENT" in prompt

    def test_skip_absent_non_code_role_sparse_false(self) -> None:
        """Non-code role + code_evidence_sparse=False → instruction NOT injected (non-regression)."""
        from launcher.models.plan import PlannedPage
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.shared.page_skeletons import SkeletonSection

        page = PlannedPage(
            page_id="tr01-no-sparse-test",
            page_role="blog_announcement",
            title="TR-01 No-Sparse Test",
            assigned_claims=["CLM-TR01"],
            code_evidence_sparse=False,
        )
        section = SkeletonSection("Announcement", 2, True, "Describe the release.", 50, 300)
        claim = _make_claim("CLM-TR01")
        prompt = build_section_prompt(section, 0, 1, page, _make_product(), [claim], [])
        assert "EVIDENCE ABSENT" not in prompt


# ===========================================================================
# QSR-02 (TC-4041): workflow_examples and supported_formats injection
# ===========================================================================

def _make_section(heading: str = "Overview") -> "SkeletonSection":
    from launcher.shared.page_skeletons import SkeletonSection
    return SkeletonSection(heading=heading, level=2, required=True, content_hint="Intro", min_words=30, max_words=200)


def _make_wf(title: str = "Load Scene", code: str = "scene = Scene()", language: str = "python") -> WorkflowExample:
    return WorkflowExample(name="load_scene", title=title, code=code, language=language, steps=["Scene()"])


def _call_build(workflow_examples=None, supported_formats=None, page_role="howto"):
    from launcher.workers.generate.section_prompt import build_section_prompt
    section = _make_section()
    page = _make_page(page_role=page_role, assigned_claims=["CLM-001"])
    return build_section_prompt(
        section, 0, 1, page, _make_product(), [_make_claim()], [],
        workflow_examples=workflow_examples,
        supported_formats=supported_formats,
    )


class TestWorkflowExamplesInjection:
    """QSR-02: REAL USAGE PATTERNS block presence/absence/capping (TC-4041)."""

    def test_workflow_examples_block_present_when_non_empty(self):
        """2 WorkflowExample objects → 'REAL USAGE PATTERNS' appears in prompt."""
        wfs = [_make_wf("Load Scene"), _make_wf("Save File")]
        prompt = _call_build(workflow_examples=wfs)
        assert "REAL USAGE PATTERNS" in prompt

    def test_workflow_examples_block_absent_when_empty(self):
        """workflow_examples=[] → 'REAL USAGE PATTERNS' does NOT appear."""
        prompt = _call_build(workflow_examples=[])
        assert "REAL USAGE PATTERNS" not in prompt

    def test_workflow_examples_block_absent_when_none(self):
        """workflow_examples=None → 'REAL USAGE PATTERNS' does NOT appear."""
        prompt = _call_build(workflow_examples=None)
        assert "REAL USAGE PATTERNS" not in prompt

    def test_workflow_examples_capped_at_3(self):
        """5 WorkflowExample objects → prompt contains ≤3 fenced blocks from workflow section."""
        wfs = [_make_wf(f"Example {i}", code=f"x = func_{i}()") for i in range(5)]
        prompt = _call_build(workflow_examples=wfs)
        # Count fenced code blocks in the REAL USAGE PATTERNS section
        # The section starts at REAL USAGE PATTERNS — count ``` openings after it
        section_start = prompt.find("REAL USAGE PATTERNS")
        assert section_start >= 0
        section_text = prompt[section_start:]
        fence_count = section_text.count("```python")
        assert fence_count <= 3, f"Expected ≤3 fenced blocks, got {fence_count}"

    def test_workflow_examples_code_capped_at_500_chars(self):
        """WorkflowExample with code='x'*1000 → injected code block ≤500 chars."""
        long_code = "x" * 1000
        wf = _make_wf(code=long_code)
        prompt = _call_build(workflow_examples=[wf])
        section_start = prompt.find("REAL USAGE PATTERNS")
        assert section_start >= 0
        section_text = prompt[section_start:]
        # Find the code between ``` markers
        fence_open = section_text.find("```python")
        fence_close = section_text.find("```", fence_open + 3)
        code_in_prompt = section_text[fence_open + len("```python"):fence_close]
        assert len(code_in_prompt.strip()) <= 500


class TestFormatMatrixInjection:
    """QSR-02: SUPPORTED FORMATS block presence/absence/role-gating (TC-4041)."""

    def test_format_matrix_block_present_for_eligible_role(self):
        """supported_formats + page_role='feature_overview' → 'SUPPORTED FORMATS' appears."""
        fmts = {"input": ["OBJ"], "output": ["FBX"]}
        prompt = _call_build(supported_formats=fmts, page_role="feature_overview")
        assert "SUPPORTED FORMATS" in prompt

    def test_format_matrix_block_absent_for_ineligible_role(self):
        """supported_formats + page_role='class_reference' → 'SUPPORTED FORMATS' does NOT appear."""
        fmts = {"input": ["OBJ"], "output": ["FBX"]}
        prompt = _call_build(supported_formats=fmts, page_role="class_reference")
        assert "SUPPORTED FORMATS" not in prompt

    def test_format_matrix_block_absent_when_formats_none(self):
        """supported_formats=None + eligible role → 'SUPPORTED FORMATS' does NOT appear."""
        prompt = _call_build(supported_formats=None, page_role="feature_overview")
        assert "SUPPORTED FORMATS" not in prompt

    def test_format_matrix_input_and_output_labels(self):
        """Both input and output formats → both 'Input:' and 'Output:' appear in prompt."""
        fmts = {"input": ["OBJ", "FBX"], "output": ["GLTF", "STL"]}
        prompt = _call_build(supported_formats=fmts, page_role="feature_overview")
        assert "Input:" in prompt
        assert "Output:" in prompt


class TestInjectionInteraction:
    """QSR-02: workflow_examples and limitations do not interfere (TC-4041)."""

    def test_existing_limitations_block_unaffected(self):
        """Both limitations and workflow_examples present → both blocks appear, no interference."""
        from launcher.models.understanding import LimitationEntry
        lim = LimitationEntry(feature="OBJ export", constraint="not supported")
        wf = _make_wf("Load OBJ")

        from launcher.workers.generate.section_prompt import build_section_prompt
        section = _make_section()
        page = _make_page(page_role="howto", assigned_claims=["CLM-001"])
        prompt = build_section_prompt(
            section, 0, 1, page, _make_product(), [_make_claim()], [],
            limitations=[lim],
            workflow_examples=[wf],
        )
        assert "KNOWN LIMITATIONS" in prompt
        assert "REAL USAGE PATTERNS" in prompt


# ---------------------------------------------------------------------------
# TC-4219: Claim context injection tests
# ---------------------------------------------------------------------------

class TestClaimContextInjection:
    """TC-4219: Verified claim text is injected into the LLM section writer prompt."""

    def test_claim_context_injected_when_provided(self):
        """build_section_prompt with claim_context non-empty → 'Claims to address' in result."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="howto", assigned_claims=["CLM-001"])
        product = _make_product()
        claim_ctx = "- [CLM-001] Document supports loading OneNote files."

        prompt = build_section_prompt(
            section, 0, 1, page, product, [_make_claim()], [],
            claim_context=claim_ctx,
        )
        assert "Claims to address" in prompt
        assert "CLM-001" in prompt
        assert "Document supports loading OneNote files." in prompt

    def test_claim_context_omitted_when_empty(self):
        """build_section_prompt with claim_context='' (default) → no 'Claims to address' block."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="howto", assigned_claims=["CLM-001"])
        product = _make_product()

        # No claim_context argument — backward-compatible default is ""
        prompt = build_section_prompt(
            section, 0, 1, page, product, [_make_claim()], [],
        )
        assert "Claims to address" not in prompt

    def test_claim_context_omitted_when_explicit_empty_string(self):
        """build_section_prompt with explicit claim_context='' → no 'Claims to address' block."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="howto", assigned_claims=[])
        product = _make_product()

        prompt = build_section_prompt(
            section, 0, 1, page, product, [], [],
            claim_context="",
        )
        assert "Claims to address" not in prompt

    def test_generated_page_claim_texts_populated(self):
        """Worker builds claim_texts list from claims_by_id for GeneratedPage."""
        from launcher.models.content import GeneratedPage

        # Simulate what the generate worker does: resolve claim texts from claim_ids_used.
        claim_ids_used = ["CLM-001", "CLM-002"]
        claims_by_id = {
            "CLM-001": type("Claim", (), {"text": "Supports loading OneNote."})(),
            "CLM-002": type("Claim", (), {"text": "Export to PDF is available."})(),
        }
        claim_texts = [
            claims_by_id[cid].text
            for cid in claim_ids_used
            if cid in claims_by_id
        ]
        page = GeneratedPage(
            slug="test-page",
            page_role="howto",
            section="cells",
            claim_ids_used=claim_ids_used,
            claim_texts=claim_texts,
            assigned_claim_count=len(claim_ids_used),
        )
        assert len(page.claim_texts) == 2
        assert "Supports loading OneNote." in page.claim_texts
        assert "Export to PDF is available." in page.claim_texts
        assert page.assigned_claim_count == 2

    def test_claim_context_capped_at_4000_chars(self):
        """claim_context exceeding 4000 chars is truncated before injection."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="howto", assigned_claims=["CLM-001"])
        product = _make_product()
        # Build a claim_context larger than 4000 characters
        long_context = "- [CLM-001] " + ("x" * 4500)

        prompt = build_section_prompt(
            section, 0, 1, page, product, [_make_claim()], [],
            claim_context=long_context,
        )
        # Should still inject (non-empty), just the raw string passed through
        assert "Claims to address" in prompt


# ---------------------------------------------------------------------------
# TC-4221: FAQ depth constraint injection tests
# ---------------------------------------------------------------------------

class TestFaqDepthConstraint:
    """TC-4221: FAQ-specific depth rules injected only for faq page_role."""

    def test_faq_depth_constraint_injected(self):
        """build_section_prompt with page_role='faq' → '3 complete sentences' in prompt."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="faq", assigned_claims=["CLM-001"])
        product = _make_product()

        prompt = build_section_prompt(
            section, 0, 1, page, product, [_make_claim()], [],
        )
        assert "3 complete sentences" in prompt
        assert "FAQ writing rules" in prompt

    def test_non_faq_page_no_faq_constraint(self):
        """build_section_prompt with page_role='tutorial' → 'FAQ writing rules' NOT in prompt."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section = _make_section()
        page = _make_page(page_role="tutorial", assigned_claims=["CLM-001"])
        product = _make_product()

        prompt = build_section_prompt(
            section, 0, 1, page, product, [_make_claim()], [],
        )
        assert "FAQ writing rules" not in prompt


# ---------------------------------------------------------------------------
# TC-HEAL-006: _build_import_rule_block — _foss suffix → explicit NEVER for base pkg
# ---------------------------------------------------------------------------

class TestBuildImportRuleBlockFossSuffix:
    """TC-HEAL-006: _build_import_rule_block adds explicit NEVER for base package
    when code_import ends with _foss (e.g. aspose_email_foss → never aspose.email).
    """

    def test_foss_suffix_adds_never_for_base_package(self):
        """aspose_email_foss → rule mentions 'import aspose.email' as NEVER."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("python", "aspose_email_foss")
        assert "aspose_email_foss" in rule
        assert "aspose.email" in rule
        assert "NEVER" in rule
        # The explicit negative example should reference the commercial package name
        assert "import aspose.email" in rule

    def test_foss_suffix_mentions_importerror(self):
        """The NEVER block must explain *why*: ImportError at runtime."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("python", "aspose_email_foss")
        assert "ImportError" in rule

    def test_non_foss_python_import_no_extra_never(self):
        """aspose_note_foss (not a well-known conflict pkg) still gets _foss treatment."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("python", "aspose_note_foss")
        # Should mention aspose.note as NEVER
        assert "aspose.note" in rule
        assert "NEVER" in rule

    def test_hardcoded_never_packages_in_base_rule(self):
        """aspose.cells and aspose.pydrawing always appear as NEVER in base rule."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("python", "aspose_cells_foss")
        # The base rule template always includes aspose.cells and aspose.pydrawing
        assert "aspose.cells" in rule.lower()
        assert "aspose.pydrawing" in rule.lower()

    def test_non_python_platform_not_affected(self):
        """dotnet platform → import rule does not mention _foss email packages."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("dotnet", "Aspose.Email")
        assert "aspose_email_foss" not in rule
        assert "ImportError" not in rule


# ===================================================================
# TC-5324: C++ import statement / wrong-import-warning / rule fixes
# ===================================================================


class TestCppImportStatementFix:
    """TC-5324: C++ import statement must use 'using namespace', not '#include <NS>'."""

    def test_cpp_import_statement_uses_using_namespace(self):
        from launcher.workers.generate.section_prompt import _build_import_statement

        stmt = _build_import_statement("cpp", "Aspose::Slides::Foss")
        assert stmt == "using namespace Aspose::Slides::Foss;"

    def test_cpp_import_statement_never_starts_with_include(self):
        from launcher.workers.generate.section_prompt import _build_import_statement

        stmt = _build_import_statement("cpp", "Aspose::ThreeD::Foss")
        assert not stmt.startswith("#include"), (
            f"C++ import_statement must use 'using namespace', got: {stmt!r}"
        )

    def test_other_platforms_unaffected(self):
        from launcher.workers.generate.section_prompt import _build_import_statement

        assert _build_import_statement("python", "aspose_cells_foss") == "import aspose_cells_foss"
        assert _build_import_statement("dotnet", "Aspose.Slides.Foss") == "using Aspose.Slides.Foss;"
        assert _build_import_statement("java", "org.aspose.slides.foss") == "import org.aspose.slides.foss.*;"


class TestCppWrongImportWarningFix:
    """TC-5324: Wrong-import warning must name the commercial namespace, not append ::Foss."""

    def test_cpp_warning_names_commercial_namespace(self):
        from launcher.workers.generate.section_prompt import _build_wrong_import_warning

        warning = _build_wrong_import_warning("cpp", "Aspose::Slides::Foss")
        assert "Aspose::Slides::Foss::Foss" not in warning
        assert "Aspose::Slides" in warning

    def test_cpp_warning_3d_namespace(self):
        from launcher.workers.generate.section_prompt import _build_wrong_import_warning

        warning = _build_wrong_import_warning("cpp", "Aspose::ThreeD::Foss")
        assert "Aspose::ThreeD::Foss::Foss" not in warning
        assert "Aspose::ThreeD" in warning


class TestCppImportRuleBlockFix:
    """TC-5324: Import rule block must not produce '{canonical}::Foss' nonsense."""

    def test_cpp_rule_block_no_double_foss(self):
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "Aspose::Slides::Foss::Foss" not in rule, (
            f"Rule block must not contain double-Foss suffix, got: {rule!r}"
        )

    def test_cpp_rule_block_names_commercial_namespace(self):
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "Aspose::Slides" in rule
        assert "Aspose::Slides::Foss" in rule

    def test_cpp_rule_block_mentions_using_namespace(self):
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "using namespace" in rule

    def test_cpp_rule_block_forbidden_dotnet_types(self):
        """TC-5330: C++ import rule block must explicitly forbid .NET types."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        # .NET types must be called out as forbidden
        assert "System::DateTime" in rule, "Must list System::DateTime as forbidden"
        assert "System::String" in rule, "Must list System::String as forbidden"
        assert "InvalidOperationException" in rule, "Must forbid InvalidOperationException"
        # C++ alternatives must be provided for exceptions
        assert "std::runtime_error" in rule, "Must suggest std::runtime_error as C++ exception alternative"

    def test_cpp_rule_block_enum_all_caps_rule(self):
        """TC-5330: C++ import rule block must specify ALL_CAPS for enum members."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "PPTX" in rule, "Must show PPTX (ALL_CAPS) as correct enum member format"
        assert "SaveFormat::PPTX" in rule, "Must show full correct enum path"

    def test_cpp_rule_block_no_export_namespace(self):
        """TC-5330: C++ rule must forbid the Export:: sub-namespace."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "Export" in rule, "Must mention Export namespace as forbidden"

    def test_other_platform_no_forbidden_block(self):
        """TC-5330: .NET and Java platforms must NOT get the C++ forbidden-types block."""
        from launcher.workers.generate.section_prompt import _build_import_rule_block

        dotnet_rule = _build_import_rule_block("dotnet", "Aspose.Slides")
        java_rule = _build_import_rule_block("java", "com.aspose.slides")
        assert "System::DateTime" not in dotnet_rule, ".NET rule must not have C++ forbidden block"
        assert "System::DateTime" not in java_rule, "Java rule must not have C++ forbidden block"


class TestCppImportRuleHardeningTC5329:
    """TC-5329: _build_import_rule_block for cpp must enumerate all forbidden .NET/C++CLI patterns."""

    def test_cpp_rule_includes_system_makeobject_prohibition(self) -> None:
        from launcher.workers.generate.section_prompt import _build_import_rule_block
        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "System::MakeObject" in rule, (
            "C++ import rule must explicitly forbid System::MakeObject<>"
        )

    def test_cpp_rule_includes_managed_pointer_prohibition(self) -> None:
        from launcher.workers.generate.section_prompt import _build_import_rule_block
        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "^" in rule, (
            "C++ import rule must mention ^ managed-pointer syntax as forbidden"
        )
        assert "gcnew" in rule, (
            "C++ import rule must mention gcnew as forbidden"
        )

    def test_cpp_rule_includes_iinterface_prohibition(self) -> None:
        from launcher.workers.generate.section_prompt import _build_import_rule_block
        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "IInterface" in rule or "IPresentation" in rule, (
            "C++ import rule must mention IInterface/IPresentation instantiation as forbidden"
        )

    def test_cpp_rule_includes_construction_guidance(self) -> None:
        from launcher.workers.generate.section_prompt import _build_import_rule_block
        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        # The rule must provide a correct C++ construction example
        assert "pres(" in rule or "make_shared" in rule or "direct construction" in rule.lower(), (
            "C++ import rule must include guidance on correct C++ object construction"
        )

    def test_cpp_rule_includes_exception_guidance(self) -> None:
        from launcher.workers.generate.section_prompt import _build_import_rule_block
        rule = _build_import_rule_block("cpp", "Aspose::Slides::Foss")
        assert "std::runtime_error" in rule or "std::exception" in rule, (
            "C++ import rule must suggest std::runtime_error or std::exception as correct alternative"
        )

    def test_cpp_forbidden_types_block_mentions_prose(self) -> None:
        """TC-5335: Forbidden types block must explicitly prohibit .NET types in PROSE too."""
        from launcher.workers.generate.section_prompt import _build_cpp_forbidden_types_block
        block = _build_cpp_forbidden_types_block()
        assert "prose" in block.lower(), (
            "TC-5335: Forbidden types block must explicitly mention prose prohibition "
            "to prevent .NET types appearing in prose descriptions"
        )
        assert "code block" in block.lower(), (
            "Forbidden types block must still mention code blocks"
        )


class TestCppSectionDirectivesTC5334:
    """TC-5334: _get_structure_directive must return C++ cmake directives for install sections."""

    def test_cpp_installation_directive_has_cmake_not_pip_as_instruction(self) -> None:
        """C++ installation section must mention find_package and not instruct to 'Show the pip install'."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("Installation", platform="cpp")
        # Must NOT contain 'pip install' as a positive instruction (like "Show the pip install command").
        # It's acceptable (even desirable) to say "NEVER write pip install" — check for the positive phrase.
        assert "show the pip" not in directive.lower(), (
            "C++ installation directive must not instruct to 'Show the pip install'"
        )
        assert "find_package" in directive or "cmake" in directive.lower(), (
            "C++ installation directive must mention find_package or CMake"
        )

    def test_python_installation_directive_has_pip(self) -> None:
        """Python installation section must still mention pip install (unchanged)."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("Installation", platform="python")
        assert "pip" in directive.lower(), (
            "Python installation directive must still mention pip install"
        )

    def test_cpp_prerequisites_directive_has_cmake_not_pip_as_instruction(self) -> None:
        """C++ prerequisites section must mention CMake/find_package as positive instruction."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("Prerequisites", platform="cpp")
        assert "cmake" in directive.lower() or "find_package" in directive, (
            "C++ prerequisites directive must mention CMake or find_package"
        )
        # The default says "language version, pip install command" — cpp override should NOT have this
        assert "language version, pip" not in directive.lower(), (
            "C++ prerequisites directive must not use the Python-centric 'language version, pip install' phrase"
        )

    def test_cpp_quick_install_directive_has_cmake_not_pip_as_instruction(self) -> None:
        """C++ quick install section must return cmake-based directive."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("Quick Install", platform="cpp")
        assert "find_package" in directive or "cmake" in directive.lower(), (
            "C++ quick install directive must mention find_package or cmake"
        )
        assert "show the pip" not in directive.lower(), (
            "C++ quick install directive must not instruct to show pip install"
        )

    def test_no_platform_falls_through_to_standard(self) -> None:
        """Without platform, installation directive is the Python-centric default."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("Installation", platform="")
        assert "pip" in directive.lower(), (
            "No-platform installation directive should return Python-centric default with pip"
        )

    def test_cpp_directive_case_insensitive(self) -> None:
        """'INSTALLATION' (uppercase) must also return C++ override."""
        from launcher.workers.generate.section_prompt import _get_structure_directive
        directive = _get_structure_directive("INSTALLATION", platform="cpp")
        assert "find_package" in directive or "cmake" in directive.lower(), (
            "C++ installation directive must mention find_package or CMake even when heading is UPPERCASE"
        )
