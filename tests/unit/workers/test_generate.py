"""Comprehensive tests for the Generate worker (W3).

Covers section prompt building, section validation, deterministic fallback
rendering, template selection, self-review, and integration-like tests that
exercise the full page-generation path without any network or LLM calls.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.content import (
    ContentManifest,
    CrossLink,
    GeneratedPage,
    GenerationStats,
)
from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.models.product import (
    ApiSurface,
    ProductIdentity,
    RichnessTier,
    RichnessResult,
)
from launcher.models.run_config import RunConfig
from launcher.models.plan import PlanBundle, PlannedPage
from launcher.models.understanding import RepoInfo, UnderstandingBundle
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS, SkeletonSection
from launcher.workers.generate.fallback import (
    render_page_deterministic,
    render_section_deterministic,
)
from launcher.workers.generate.section_prompt import (
    _HEADING_ALIASES,
    _STRUCTURE_DIRECTIVES,
    _get_structure_directive,
    build_section_prompt,
)
from launcher.workers.generate.section_validator import (
    _backtick_api_names,
    _compile_api_pattern,
    _extract_json_array,
    _strip_claim_citations,
    parse_and_validate_blocks,
)
from launcher.shared.linker import infer_section
from launcher.workers.generate.worker import (
    GenerateWorker,
    _count_prose_words,
    _MAX_SECTION_RETRIES,
    _MIN_SECTION_PROSE_WORDS,
    create_worker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells for Python",
        canonical_import="aspose.cells",
        repo_url="https://github.com/aspose-cells/aspose-cells-python",
        repo_sha="abc123",
    )


@pytest.fixture()
def sample_claims() -> list[Claim]:
    return [
        Claim(
            claim_id="C001",
            text="Aspose.Cells supports reading XLSX files",
            kind="capability",
            evidence=[EvidenceAnchor(source_file="src/reader.py", line_start=10)],
        ),
        Claim(
            claim_id="C002",
            text="Worksheets can be created programmatically",
            kind="capability",
            evidence=[EvidenceAnchor(source_file="src/worksheet.py")],
        ),
        Claim(
            claim_id="C003",
            text="Export to PDF is supported via the save method",
            kind="capability",
            evidence=[EvidenceAnchor(source_file="src/export.py", line_start=42)],
        ),
        Claim(
            claim_id="C004",
            text="Cell formatting includes bold, italic, and color",
            kind="feature",
            evidence=[],
        ),
        Claim(
            claim_id="C005",
            text="Charts can be added from data ranges",
            kind="feature",
            evidence=[EvidenceAnchor(source_file="src/charts.py")],
        ),
        Claim(
            claim_id="C006",
            text="Formula evaluation engine supports 300+ functions",
            kind="specification",
            evidence=[],
        ),
    ]


@pytest.fixture()
def sample_snippets(sample_claims: list[Claim]) -> list[Snippet]:
    return [
        Snippet(
            code="import aspose.cells\nwb = aspose.cells.Workbook('test.xlsx')",
            language="python",
            source_type="extracted",
            claim_ids=["C001"],
        ),
        Snippet(
            code="ws = wb.worksheets.add('Sheet1')\nws.cells.get('A1').value = 'Hello'",
            language="python",
            source_type="extracted",
            claim_ids=["C002", "C004"],
        ),
        Snippet(
            code="wb.save('output.pdf', aspose.cells.SaveFormat.PDF)",
            language="python",
            source_type="generated",
            claim_ids=["C003"],
        ),
    ]


@pytest.fixture()
def sample_page_plan() -> PlannedPage:
    return PlannedPage(
        page_id="docs-workflow-export-pdf",
        page_role="workflow_page",
        title="Export Workbook to PDF",
        skeleton=["Overview", "Key Features", "Prerequisites", "Code Examples", "Notes and Best Practices", "See Also"],
        assigned_claims=["C001", "C002", "C003", "C004", "C005"],
        assigned_snippets=[0, 1, 2],
        frontmatter={
            "slug": "export-pdf",
            "section": "docs",
            "title": "Export Workbook to PDF",
            "type": "workflow_page",
            "url": "/cells/python/export-pdf/",
            "weight": 2,
            "family": "cells",
            "platform": "python",
            "page_role": "workflow_page",
            "robots": "index, follow",
        },
        seo_keywords=["aspose cells pdf export", "python xlsx to pdf"],
        mandatory=True,
    )


@pytest.fixture()
def sample_understanding_bundle(
    sample_product: ProductIdentity,
    sample_claims: list[Claim],
    sample_snippets: list[Snippet],
) -> UnderstandingBundle:
    return UnderstandingBundle(
        product=sample_product,
        repo=RepoInfo(
            file_tree=["src/reader.py", "src/worksheet.py"],
            doc_paths=["docs/readme.md"],
            example_paths=["examples/hello.py"],
            readme_summary="Aspose.Cells for Python",
        ),
        richness_tier=RichnessResult(
            tier=RichnessTier.A,
            score=85,
            reason="Rich API surface with many public classes",
        ),
        api_surface=ApiSurface(
            public_classes=["Workbook", "Worksheet", "Cell"],
            import_allowlist=["aspose.cells", "aspose.cells.drawing"],
            confidence="high",
        ),
        claims=sample_claims,
        snippets=sample_snippets,
    )


@pytest.fixture()
def sample_plan_bundle(sample_page_plan: PlannedPage) -> PlanBundle:
    toc_page = PlannedPage(
        page_id="docs-toc",
        page_role="toc",
        title="Documentation",
        skeleton=["Overview", "Pages in This Section"],
        assigned_claims=[],
        assigned_snippets=[],
        frontmatter={
            "slug": "docs-toc",
            "title": "Documentation",
            "type": "toc",
            "url": "/cells/python/docs-toc/",
            "weight": 1,
            "family": "cells",
            "platform": "python",
            "page_role": "toc",
            "robots": "noindex, follow",
        },
    )
    overview_page = PlannedPage(
        page_id="docs-overview",
        page_role="landing",
        title="Aspose.Cells for Python Overview",
        skeleton=["Overview", "Key Features", "Quick Start", "See Also"],
        assigned_claims=["C005", "C006"],
        assigned_snippets=[],
        frontmatter={
            "slug": "overview",
            "title": "Aspose.Cells for Python Overview",
            "type": "landing",
            "url": "/cells/python/overview/",
            "weight": 3,
            "family": "cells",
            "platform": "python",
            "page_role": "landing",
            "robots": "index, follow",
        },
    )
    return PlanBundle(
        pages=[toc_page, sample_page_plan, overview_page],
    )


def _make_no_llm_context(tmp_path: Path) -> WorkerContext:
    """Build a WorkerContext with llm_config=None so fallback is always used."""
    run_dir = tmp_path / "runs" / "test-gen"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=None,
    )
    return WorkerContext(
        run_id="test-gen-001",
        run_dir=run_dir,
        config=config,
        llm_config=None,
    )


# ===========================================================================
# Section Prompt tests
# ===========================================================================


class TestSectionPrompt:

    def test_build_section_prompt_contains_product_name(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        prompt = build_section_prompt(
            skeleton[0], 0, len(skeleton),
            sample_page_plan, sample_product, sample_claims, sample_snippets,
        )
        assert sample_product.display_name in prompt

    def test_build_section_prompt_contains_section_heading(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        section = skeleton[2]  # "Prerequisites"
        prompt = build_section_prompt(
            section, 2, len(skeleton),
            sample_page_plan, sample_product, sample_claims, sample_snippets,
        )
        assert section.heading in prompt

    def test_build_section_prompt_distributes_claims(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        """TC-3879 Wave 1 (Gap1): When claims < sections, all claims appear in all sections.
        This ensures no section is left with 0 unique claims, which previously caused
        boilerplate-only output and density HIGH findings."""
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        total = len(skeleton)
        prompts = [
            build_section_prompt(
                skeleton[i], i, total,
                sample_page_plan, sample_product, sample_claims, sample_snippets,
            )
            for i in range(total)
        ]
        # Every prompt should contain all assigned claim IDs
        all_claim_ids = set(sample_page_plan.assigned_claims)
        for i, p in enumerate(prompts):
            found = {cid for cid in all_claim_ids if cid in p}
            assert found == all_claim_ids, (
                f"Section {i} is missing claims: {all_claim_ids - found}"
            )

    def test_build_section_prompt_includes_snippets(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        """If a section has claims linked to snippets, the snippet code appears."""
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        # Section 0 gets claims at indices 0, 4 (mod 4). Claim C001 at idx 0
        # has snippet[0] linked via claim_ids=["C001"].
        prompt = build_section_prompt(
            skeleton[0], 0, len(skeleton),
            sample_page_plan, sample_product, sample_claims, sample_snippets,
        )
        assert "aspose.cells.Workbook" in prompt or "import aspose.cells" in prompt

    def test_build_section_prompt_no_claims(
        self, sample_product: ProductIdentity,
    ) -> None:
        """Page with no assigned claims still produces a valid prompt."""
        page = PlannedPage(
            page_id="docs-empty",
            page_role="landing",
            title="Empty Page",
            assigned_claims=[],
            assigned_snippets=[],
        )
        skeleton = PAGE_ROLE_SKELETONS["landing"]
        prompt = build_section_prompt(
            skeleton[0], 0, len(skeleton),
            page, sample_product, [], [],
        )
        # Prompt should still be a non-empty string containing the product name
        assert isinstance(prompt, str) and len(prompt) > 0
        assert sample_product.display_name in prompt

    def test_install_reference_excluded_from_non_install_page(self) -> None:
        """TC-4254: install_recipe must not leak into non-install page prompts."""
        from launcher.models.understanding import InstallRecipe

        product = ProductIdentity(
            family="3d",
            platform="python",
            display_name="Aspose.3D for Python",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
            repo_url="https://github.com/aspose-free/aspose-3d-python",
            repo_sha="abc123",
        )
        page = PlannedPage(
            page_id="kb-optimize-meshes",
            page_role="workflow_page",
            title="Optimize 3D Meshes",
            assigned_claims=[],
            assigned_snippets=[],
        )
        section = SkeletonSection("Overview", 2, True, "Summary", 30, 120)
        prompt = build_section_prompt(
            section,
            0,
            1,
            page,
            product,
            [],
            [],
            install_recipe=InstallRecipe(
                install_command="pip install aspose-3d-foss",
                verification_code="import aspose.threed\nprint('Installation successful')",
            ),
        )
        assert "## INSTALL REFERENCE" not in prompt
        assert "pip install aspose-3d-foss" not in prompt

    def test_install_reference_included_for_getting_started_page(self) -> None:
        """TC-4254: install_recipe stays available on getting-started pages."""
        from launcher.models.understanding import InstallRecipe

        product = ProductIdentity(
            family="3d",
            platform="python",
            display_name="Aspose.3D for Python",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
            repo_url="https://github.com/aspose-free/aspose-3d-python",
            repo_sha="abc123",
        )
        page = PlannedPage(
            page_id="docs-getting-started",
            page_role="getting_started",  # TC-5196: canonical underscore form
            title="Getting Started",
            assigned_claims=[],
            assigned_snippets=[],
        )
        section = SkeletonSection("Prerequisites", 2, True, "Setup steps", 30, 120)
        prompt = build_section_prompt(
            section,
            0,
            1,
            page,
            product,
            [],
            [],
            install_recipe=InstallRecipe(
                install_command="pip install aspose-3d-foss",
                verification_code="import aspose.threed\nprint('Installation successful')",
            ),
        )
        assert "## INSTALL REFERENCE" in prompt
        assert "pip install aspose-3d-foss" in prompt
        assert "import aspose.threed" in prompt


# ===========================================================================
# Section Validator tests
# ===========================================================================


class TestSectionValidator:

    def test_parse_valid_json_blocks(self, sample_product: ProductIdentity) -> None:
        raw = json.dumps([
            {"type": "paragraph", "content": "Hello world.", "claim_ids": ["C001"]},
            {"type": "code", "content": "x = 1", "language": "python", "claim_ids": []},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, {"C001", "C002"}, ["aspose.cells"],
        )
        assert blocks is not None
        assert len(blocks) == 2
        assert blocks[0].type == BlockType.paragraph
        assert blocks[1].type == BlockType.code

    def test_parse_json_with_markdown_fences(self, sample_product: ProductIdentity) -> None:
        raw = '```json\n[{"type": "paragraph", "content": "Hi"}]\n```'
        blocks = parse_and_validate_blocks(
            raw, sample_product, set(), ["aspose.cells"],
        )
        assert blocks is not None
        assert len(blocks) == 1
        assert blocks[0].content == "Hi"

    def test_parse_invalid_json_returns_none(self, sample_product: ProductIdentity) -> None:
        raw = "this is not json at all {{{"
        result = parse_and_validate_blocks(
            raw, sample_product, set(), [],
        )
        assert result is None

    def test_parse_filters_invalid_block_types(self, sample_product: ProductIdentity) -> None:
        raw = json.dumps([
            {"type": "paragraph", "content": "Valid"},
            {"type": "nonexistent_type", "content": "Invalid"},
            {"type": "code", "content": "x=1", "language": "python"},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, set(), [],
        )
        assert blocks is not None
        assert len(blocks) == 2
        assert all(b.type in BlockType for b in blocks)

    def test_parse_filters_invalid_claim_ids(self, sample_product: ProductIdentity) -> None:
        raw = json.dumps([
            {"type": "paragraph", "content": "Test",
             "claim_ids": ["C001", "BOGUS", "C002"]},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, {"C001", "C002"}, [],
        )
        assert blocks is not None
        assert blocks[0].claim_ids == ["C001", "C002"]
        assert "BOGUS" not in blocks[0].claim_ids

    def test_extract_json_array_nested(self) -> None:
        text = 'Here is the output:\n[{"a": [1, 2]}, {"b": [3]}]'
        result = _extract_json_array(text)
        assert result is not None
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["a"] == [1, 2]


# ===========================================================================
# Fallback Renderer tests
# ===========================================================================


class TestFallbackRenderer:

    def test_render_section_deterministic_with_claims(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
    ) -> None:
        skel = SkeletonSection("Key Features", 2, True, "Feature list", 50, 300)
        section_ir = render_section_deterministic(
            skel, sample_claims[:3], [], sample_product,
        )
        # TC-4031 Wave 3C: claims produce a paragraph from first 2 claims + list for rest.
        para_blocks = [b for b in section_ir.blocks if b.type == BlockType.paragraph]
        list_blocks = [b for b in section_ir.blocks if b.type == BlockType.list]
        # First 2 claims become a paragraph
        assert para_blocks, "Expected paragraph block from first 2 claims"
        assert "C001" in para_blocks[-1].claim_ids
        # Third claim becomes a single-item list
        assert len(list_blocks) == 1
        assert len(list_blocks[0].items) == 1
        assert list_blocks[0].claim_ids == ["C003"]

    def test_render_section_deterministic_with_snippets(
        self, sample_product: ProductIdentity, sample_snippets: list[Snippet],
    ) -> None:
        skel = SkeletonSection("Code Examples", 2, True, "Code samples", 30, 200)
        section_ir = render_section_deterministic(
            skel, [], sample_snippets[:2], sample_product,
        )
        code_blocks = [b for b in section_ir.blocks if b.type == BlockType.code]
        assert len(code_blocks) == 2
        assert code_blocks[0].language == "python"
        assert "aspose.cells" in code_blocks[0].content

    def test_render_section_deterministic_empty(
        self, sample_product: ProductIdentity,
    ) -> None:
        skel = SkeletonSection("Overview", 2, True, "Product overview", 50, 150)
        section_ir = render_section_deterministic(skel, [], [], sample_product)
        # Should produce at least a minimal paragraph
        assert len(section_ir.blocks) >= 1
        para_blocks = [b for b in section_ir.blocks if b.type == BlockType.paragraph]
        assert len(para_blocks) >= 1
        assert sample_product.display_name in para_blocks[-1].content

    def test_render_page_deterministic_distributes_claims(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        sections = render_page_deterministic(
            "test-page", "workflow_page", "Test",
            skeleton, sample_claims, sample_snippets, sample_product,
        )
        assert len(sections) == len(skeleton)
        # Claims should be spread across sections (not all in one)
        claim_counts = []
        for s in sections:
            n_claims = sum(len(b.claim_ids) for b in s.blocks)
            claim_counts.append(n_claims)
        # At least two sections should have claims
        assert sum(1 for c in claim_counts if c > 0) >= 2

    def test_render_section_has_correct_heading(
        self, sample_product: ProductIdentity,
    ) -> None:
        skel = SkeletonSection("Prerequisites", 3, True, "Required setup", 30, 100)
        section_ir = render_section_deterministic(skel, [], [], sample_product)
        assert section_ir.heading == "Prerequisites"
        assert section_ir.level == 3
        assert section_ir.section_id == "prerequisites"


# ===========================================================================
# Template Selector tests
# ===========================================================================


class TestTemplateSelector:

    def test_resolve_template_tier_a(self) -> None:
        from launcher.workers.generate.template_selector import resolve_template

        _, variant = resolve_template("products", "landing", "cells", RichnessTier.A)
        assert variant == "standard"

    def test_resolve_template_tier_c(self) -> None:
        from launcher.workers.generate.template_selector import resolve_template

        _, variant = resolve_template("products", "landing", "cells", RichnessTier.C)
        assert variant == "minimal"

    def test_resolve_template_unknown_section(self) -> None:
        from launcher.workers.generate.template_selector import resolve_template

        path, _ = resolve_template(
            "nonexistent_section_xyz", "nonexistent_role_xyz",
            "nonexistent_family", RichnessTier.B,
        )
        assert path == ""


# ===========================================================================
# Self-review tests
# ===========================================================================


class TestSelfReview:

    @pytest.fixture()
    def worker(self) -> GenerateWorker:
        return create_worker()

    @pytest.fixture()
    def valid_manifest(self) -> ContentManifest:
        return ContentManifest(
            pages=[
                GeneratedPage(
                    slug="overview",
                    page_role="landing",
                    section="docs",
                    word_count=200,
                    code_block_count=1,
                ),
                GeneratedPage(
                    slug="workflow-export-pdf",
                    page_role="workflow_page",
                    section="docs",
                    word_count=350,
                    code_block_count=3,
                ),
            ],
            generation_stats=GenerationStats(
                total_pages=2,
                llm_calls=8,
                fallback_count=0,
                duration_seconds=12.5,
            ),
        )

    @pytest.mark.asyncio()
    async def test_self_review_passes_valid_manifest(
        self, worker: GenerateWorker, valid_manifest: ContentManifest,
    ) -> None:
        result = await worker.self_review(valid_manifest)
        assert result.passed is True
        assert result.metrics["total_pages"] == 2

    @pytest.mark.asyncio()
    async def test_self_review_catches_empty_pages(
        self, worker: GenerateWorker,
    ) -> None:
        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="empty-page",
                    page_role="landing",
                    section="docs",
                    word_count=0,
                    code_block_count=0,
                ),
            ],
            generation_stats=GenerationStats(total_pages=1),
        )
        result = await worker.self_review(manifest)
        assert result.passed is False
        assert any(f["category"] == "empty_page" for f in result.findings)

    @pytest.mark.asyncio()
    async def test_self_review_catches_missing_code_in_workflow(
        self, worker: GenerateWorker,
    ) -> None:
        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="workflow-no-code",
                    page_role="workflow_page",
                    section="docs",
                    word_count=150,
                    code_block_count=0,  # workflow page with no code
                ),
            ],
            generation_stats=GenerationStats(total_pages=1),
        )
        result = await worker.self_review(manifest)
        # Missing code is medium severity, so still passes but has findings
        assert any(f["category"] == "missing_code" for f in result.findings)

    @pytest.mark.asyncio()
    async def test_self_review_non_manifest_fails(
        self, worker: GenerateWorker, sample_product: ProductIdentity,
    ) -> None:
        result = await worker.self_review(sample_product)
        assert result.passed is False
        assert any("ContentManifest" in f["message"] for f in result.findings)


# ===========================================================================
# Integration-like tests (no network)
# ===========================================================================


class TestIntegrationNoNetwork:

    @pytest.mark.asyncio()
    async def test_generate_page_deterministic_fallback(
        self,
        tmp_path: Path,
        sample_understanding_bundle: UnderstandingBundle,
        sample_plan_bundle: PlanBundle,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Full Generate worker run with llm_config=None uses fallback for every section."""
        # Monkeypatch model_dump_json to avoid sort_keys incompatibility
        # in the base model — this is a known Pydantic version issue.
        from launcher.models.base import LauncherBaseModel
        _orig = LauncherBaseModel.model_dump_json

        def _patched(self: Any, **kwargs: Any) -> str:
            kwargs.pop("sort_keys", None)
            from pydantic import BaseModel
            return BaseModel.model_dump_json(self, **kwargs)

        monkeypatch.setattr(LauncherBaseModel, "model_dump_json", _patched)

        ctx = _make_no_llm_context(tmp_path)

        # Write understanding checkpoint so Generate can load it
        checkpoint_path = ctx.run_dir / "understand_checkpoint.json"
        checkpoint_path.write_text(
            sample_understanding_bundle.model_dump_json(),
            encoding="utf-8",
        )

        worker = create_worker()

        manifest = await worker.run(sample_plan_bundle, ctx)

        assert isinstance(manifest, ContentManifest)
        assert manifest.generation_stats.total_pages == len(sample_plan_bundle.pages)
        # All sections should have fallen back (no LLM)
        assert manifest.generation_stats.llm_calls == 0
        assert manifest.generation_stats.fallback_count > 0
        # Every page should have some content
        for page in manifest.pages:
            assert page.word_count > 0

    def test_infer_section_from_page_id(self) -> None:
        assert infer_section("docs-workflow-export-pdf") == "docs"

        assert infer_section("overview", {"section": "products"}) == "products"

        # Falls back to "docs" default
        assert infer_section("standalone") == "docs"



# ===========================================================================
# Template integration tests
# ===========================================================================


class TestTemplateIntegration:

    def test_extract_template_sections_from_real_template(self) -> None:
        from launcher.content.template_loader import extract_template_sections

        template = (
            "---\ntitle: \"__TITLE__\"\ntype: docs\n---\n\n"
            "## Overview\n\n__BODY_INTRO__\n\n"
            "## Key Features\n\n__BODY_KEY_FEATURES__\n\n"
            "## See Also\n\n__BODY_SEE_ALSO__\n"
        )
        sections = extract_template_sections(template)
        assert len(sections) == 3
        assert sections[0].heading == "Overview"
        assert sections[0].required is True
        assert sections[1].heading == "Key Features"
        assert sections[1].required is True
        assert sections[2].heading == "See Also"
        assert sections[2].required is False  # See Also is optional

    def test_extract_template_frontmatter_strips_placeholders(self) -> None:
        from launcher.content.template_loader import extract_template_frontmatter

        template = (
            "---\n"
            "# Template comment\n"
            "title: \"__TITLE__\"\n"
            "layout: \"reference-single\"\n"
            "type: topic\n"
            "categories:\n"
            "  - \"__CATEGORY_1__\"\n"
            "---\n\n## Overview\n"
        )
        fm, required_keys = extract_template_frontmatter(template)
        assert "title" not in fm  # placeholder stripped → in required_keys
        assert "title" in required_keys
        assert fm["layout"] == "reference-single"
        assert fm["type"] == "topic"
        assert "categories" not in fm  # all-placeholder list stripped → in required_keys
        assert "categories" in required_keys

    def test_role_template_name_mapping(self) -> None:
        from launcher.content.template_loader import select_template

        # api_reference should find reference.variant-standard.md
        path = select_template("reference", "api_reference", "A")
        assert path is not None
        assert "reference" in path.name

    def test_duplicate_heading_stripped_by_validator(
        self, sample_product: ProductIdentity,
    ) -> None:
        raw = json.dumps([
            {"type": "heading", "content": "Overview", "level": 2, "claim_ids": []},
            {"type": "paragraph", "content": "Hello world.", "claim_ids": ["C001"]},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, {"C001"}, [],
            section_heading="Overview",
        )
        assert blocks is not None
        # The heading block matching "Overview" should be stripped
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.paragraph

    def test_duplicate_heading_not_stripped_when_different(
        self, sample_product: ProductIdentity,
    ) -> None:
        raw = json.dumps([
            {"type": "heading", "content": "Subsection Detail", "level": 3, "claim_ids": []},
            {"type": "paragraph", "content": "Hello world.", "claim_ids": ["C001"]},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, {"C001"}, [],
            section_heading="Overview",
        )
        assert blocks is not None
        assert len(blocks) == 2  # heading kept (different text)

    def test_section_prompt_includes_structure_directive(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        """FAQ-like sections should get Q&A structural guidance in the prompt."""
        faq_section = SkeletonSection(
            "Frequently Asked Questions", 2, True,
            "Q&A pairs as H3 sub-sections", 100, 600,
        )
        faq_page = PlannedPage(
            page_id="kb-faq",
            page_role="faq",
            title="FAQ",
            assigned_claims=["C001"],
            assigned_snippets=[],
        )
        prompt = build_section_prompt(
            faq_section, 0, 1,
            faq_page, sample_product, sample_claims, sample_snippets,
        )
        assert "Q&A pairs" in prompt
        assert "H3 heading" in prompt

    def test_section_prompt_includes_content_hint(
        self, sample_product: ProductIdentity, sample_claims: list[Claim],
        sample_snippets: list[Snippet], sample_page_plan: PlannedPage,
    ) -> None:
        """The content_hint from the skeleton should appear in the prompt."""
        skeleton = PAGE_ROLE_SKELETONS["workflow_page"]
        prompt = build_section_prompt(
            skeleton[0], 0, len(skeleton),
            sample_page_plan, sample_product, sample_claims, sample_snippets,
        )
        assert skeleton[0].content_hint in prompt


# ===========================================================================
# SR-07: Expanded template-directive system tests
# ===========================================================================


class TestStructureDirectives:
    """Comprehensive tests for the _STRUCTURE_DIRECTIVES system."""

    @pytest.mark.parametrize(
        "heading",
        list(_STRUCTURE_DIRECTIVES.keys()),
        ids=list(_STRUCTURE_DIRECTIVES.keys()),
    )
    def test_all_directives_appear_in_prompt(
        self, heading: str, sample_product: ProductIdentity,
        sample_claims: list[Claim], sample_snippets: list[Snippet],
    ) -> None:
        """Each entry in _STRUCTURE_DIRECTIVES should appear in the built prompt."""
        section = SkeletonSection(heading, 2, True, "Test hint", 30, 200)
        page = PlannedPage(
            page_id="test-page",
            page_role="landing",
            title="Test Page",
            assigned_claims=[c.claim_id for c in sample_claims[:1]],
            assigned_snippets=[],
        )
        prompt = build_section_prompt(
            section, 0, 1,
            page, sample_product, sample_claims, sample_snippets,
        )
        directive_text = _STRUCTURE_DIRECTIVES[heading]
        assert directive_text in prompt, (
            f"Directive for '{heading}' not found in prompt"
        )

    def test_empty_directive_fallback(
        self, sample_product: ProductIdentity,
        sample_claims: list[Claim], sample_snippets: list[Snippet],
    ) -> None:
        """TC-3879 Wave 1 (F3): A heading NOT in _STRUCTURE_DIRECTIVES should produce
        a valid prompt using the generic structural fallback directive (not empty string)."""
        section = SkeletonSection(
            "Nonexistent Heading XYZ", 2, True, "Test hint", 30, 200,
        )
        page = PlannedPage(
            page_id="test-page",
            page_role="landing",
            title="Test Page",
            assigned_claims=[],
            assigned_snippets=[],
        )
        prompt = build_section_prompt(
            section, 0, 1,
            page, sample_product, [], [],
        )
        assert isinstance(prompt, str) and len(prompt) > 0
        # The unknown heading should still appear in the prompt
        assert "Nonexistent Heading XYZ" in prompt
        # TC-3879 Wave 1 (F3): Unknown headings now get the generic structural fallback,
        # not an empty string — so the LLM always has structural guidance.
        directive = _get_structure_directive("Nonexistent Heading XYZ")
        assert isinstance(directive, str) and len(directive) > 0

    def test_steps_directive_content(self) -> None:
        """The 'steps' directive should contain 'numbered step-by-step'."""
        directive = _get_structure_directive("steps")
        assert "numbered step-by-step" in directive

    def test_properties_directive_content(self) -> None:
        """The 'properties' directive should contain 'markdown table'."""
        directive = _get_structure_directive("properties")
        assert "markdown table" in directive

    def test_see_also_directive_content(self) -> None:
        """The 'see also' directive should contain 'list block'."""
        directive = _get_structure_directive("see also")
        assert "list block" in directive

    def test_directive_lookup_is_case_insensitive(self) -> None:
        """_get_structure_directive should match case-insensitively."""
        for heading in list(_STRUCTURE_DIRECTIVES.keys())[:5]:
            lower = _get_structure_directive(heading.lower())
            upper = _get_structure_directive(heading.upper())
            mixed = _get_structure_directive(heading.title())
            assert lower == upper == mixed, (
                f"Case-insensitive mismatch for '{heading}'"
            )


class TestHeadingStripping:
    """Tests for heading-block stripping in parse_and_validate_blocks."""

    def test_heading_strip_case_insensitive(
        self, sample_product: ProductIdentity,
    ) -> None:
        """A heading block matching section_heading in different case is stripped."""
        raw = json.dumps([
            {"type": "heading", "content": "overview", "level": 2},
            {"type": "paragraph", "content": "Content here."},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, set(), [],
            section_heading="Overview",
        )
        assert blocks is not None
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.paragraph

    def test_heading_strip_with_md_prefix(
        self, sample_product: ProductIdentity,
    ) -> None:
        """A heading block with markdown prefix '## Overview' and
        section_heading='Overview' should be stripped."""
        raw = json.dumps([
            {"type": "heading", "content": "## Overview", "level": 2},
            {"type": "paragraph", "content": "Content here."},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, set(), [],
            section_heading="Overview",
        )
        assert blocks is not None
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.paragraph

    def test_heading_strip_partial_no_match(
        self, sample_product: ProductIdentity,
    ) -> None:
        """A heading 'Overview of Features' with section_heading='Overview'
        should NOT be stripped (partial match only)."""
        raw = json.dumps([
            {"type": "heading", "content": "Overview of Features", "level": 2},
            {"type": "paragraph", "content": "Content here."},
        ])
        blocks = parse_and_validate_blocks(
            raw, sample_product, set(), [],
            section_heading="Overview",
        )
        assert blocks is not None
        assert len(blocks) == 2
        assert blocks[0].type == BlockType.heading
        assert blocks[0].content == "Overview of Features"


class TestSkeletonDirectiveCoverage:
    """Verify skeleton headings have directive coverage."""

    @pytest.mark.parametrize(
        "role_heading",
        [
            (role, section.heading)
            for role, sections in PAGE_ROLE_SKELETONS.items()
            for section in sections
        ],
        ids=[
            f"{role}:{section.heading}"
            for role, sections in PAGE_ROLE_SKELETONS.items()
            for section in sections
        ],
    )
    def test_all_skeleton_headings_have_directives(
        self, role_heading: tuple[str, str],
    ) -> None:
        """Every heading defined in PAGE_ROLE_SKELETONS should have a
        matching _STRUCTURE_DIRECTIVES entry (lookup is case-insensitive)."""
        role, heading = role_heading
        directive = _get_structure_directive(heading)
        assert directive != "", (
            f"No structure directive for heading '{heading}' "
            f"(used by page role '{role}'). "
            f"Add an entry to _STRUCTURE_DIRECTIVES in section_prompt.py."
        )


# ===========================================================================
# SR-07 (expanded): Heading aliases & key-role directive coverage
# ===========================================================================


class TestHeadingAliases:
    """Tests for the _HEADING_ALIASES normalization system."""

    @pytest.mark.parametrize(
        "alias,canonical",
        list(_HEADING_ALIASES.items()),
        ids=list(_HEADING_ALIASES.keys()),
    )
    def test_alias_resolves_to_canonical(self, alias: str, canonical: str) -> None:
        """Every alias must resolve to the same directive as its canonical key."""
        alias_directive = _get_structure_directive(alias)
        canonical_directive = _get_structure_directive(canonical)
        assert alias_directive != "", (
            f"Alias '{alias}' -> canonical '{canonical}' produced empty directive"
        )
        assert alias_directive == canonical_directive, (
            f"Alias '{alias}' produced different directive than canonical '{canonical}'"
        )

    @pytest.mark.parametrize(
        "alias",
        list(_HEADING_ALIASES.keys()),
        ids=list(_HEADING_ALIASES.keys()),
    )
    def test_alias_canonical_exists_in_directives(self, alias: str) -> None:
        """Every alias's canonical target must exist in _STRUCTURE_DIRECTIVES."""
        canonical = _HEADING_ALIASES[alias]
        assert canonical in _STRUCTURE_DIRECTIVES, (
            f"Alias '{alias}' maps to '{canonical}' which is missing from "
            f"_STRUCTURE_DIRECTIVES"
        )

    def test_alias_case_insensitive(self) -> None:
        """Aliases should work regardless of case."""
        for alias in _HEADING_ALIASES:
            lower = _get_structure_directive(alias.lower())
            upper = _get_structure_directive(alias.upper())
            title = _get_structure_directive(alias.title())
            assert lower == upper == title, (
                f"Alias '{alias}' does not match case-insensitively"
            )

    def test_alias_with_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped before alias lookup."""
        for alias in _HEADING_ALIASES:
            padded = f"  {alias}  "
            assert _get_structure_directive(padded) == _get_structure_directive(alias), (
                f"Whitespace-padded alias '{padded}' produced different result"
            )


_KEY_PAGE_ROLES = [
    "landing",
    "workflow_page",
    "api_reference",
    "tutorial",
    "troubleshooting",
    "faq",
    "feature_showcase",
    "comprehensive_guide",
]


class TestKeyRoleDirectiveCoverage:
    """Verify that the most important page roles have full directive coverage."""

    @pytest.mark.parametrize("role", _KEY_PAGE_ROLES, ids=_KEY_PAGE_ROLES)
    def test_key_role_exists_in_skeletons(self, role: str) -> None:
        """Each key role must be present in PAGE_ROLE_SKELETONS."""
        assert role in PAGE_ROLE_SKELETONS, (
            f"Key role '{role}' missing from PAGE_ROLE_SKELETONS"
        )

    @pytest.mark.parametrize("role", _KEY_PAGE_ROLES, ids=_KEY_PAGE_ROLES)
    def test_key_role_all_headings_have_directives(self, role: str) -> None:
        """Every heading in a key role's skeleton must have a directive."""
        sections = PAGE_ROLE_SKELETONS[role]
        missing = []
        for section in sections:
            directive = _get_structure_directive(section.heading)
            if not directive:
                missing.append(section.heading)
        assert not missing, (
            f"Role '{role}' has headings without directives: {missing}"
        )

    @pytest.mark.parametrize(
        "role,heading",
        [
            ("landing", "Overview"),
            ("landing", "Key Features"),
            ("landing", "Quick Start"),
            ("workflow_page", "Overview"),
            ("workflow_page", "Prerequisites"),
            ("workflow_page", "Code Examples"),
            ("api_reference", "Overview"),
            ("api_reference", "Constructors"),
            ("api_reference", "Properties"),
            ("api_reference", "Methods"),
            ("tutorial", "Overview"),
            ("tutorial", "Step-by-Step Guide"),
            ("tutorial", "Code Examples"),
            ("troubleshooting", "Overview"),
            ("troubleshooting", "Common Issues"),
            ("faq", "Frequently Asked Questions"),
        ],
        ids=[
            "landing:Overview",
            "landing:Key Features",
            "landing:Quick Start",
            "workflow_page:Overview",
            "workflow_page:Prerequisites",
            "workflow_page:Code Examples",
            "api_reference:Overview",
            "api_reference:Constructors",
            "api_reference:Properties",
            "api_reference:Methods",
            "tutorial:Overview",
            "tutorial:Step-by-Step Guide",
            "tutorial:Code Examples",
            "troubleshooting:Overview",
            "troubleshooting:Common Issues",
            "faq:Frequently Asked Questions",
        ],
    )
    def test_critical_heading_returns_nonempty_directive(
        self, role: str, heading: str,
    ) -> None:
        """Critical headings for key page roles must return non-empty directives."""
        directive = _get_structure_directive(heading)
        assert directive, (
            f"Critical heading '{heading}' for role '{role}' returned empty directive"
        )
        assert len(directive) > 20, (
            f"Directive for '{heading}' is suspiciously short ({len(directive)} chars)"
        )


class TestDirectiveQuality:
    """Validate directive content quality constraints."""

    @pytest.mark.parametrize(
        "heading",
        list(_STRUCTURE_DIRECTIVES.keys()),
        ids=list(_STRUCTURE_DIRECTIVES.keys()),
    )
    def test_directive_is_nonempty_string(self, heading: str) -> None:
        """Every directive value must be a non-empty string."""
        directive = _STRUCTURE_DIRECTIVES[heading]
        assert isinstance(directive, str)
        assert len(directive.strip()) > 0

    @pytest.mark.parametrize(
        "heading",
        list(_STRUCTURE_DIRECTIVES.keys()),
        ids=list(_STRUCTURE_DIRECTIVES.keys()),
    )
    def test_directive_minimum_length(self, heading: str) -> None:
        """Directives should be descriptive enough (at least 20 chars)."""
        directive = _STRUCTURE_DIRECTIVES[heading]
        assert len(directive) >= 20, (
            f"Directive for '{heading}' is too short ({len(directive)} chars): "
            f"'{directive}'"
        )

    def test_unknown_heading_returns_generic_fallback(self) -> None:
        """TC-3879 Wave 1 (F3): Completely unknown headings return the generic structural
        fallback directive (not empty string). Empty/whitespace strings still return ""."""
        # Truly unknown heading → generic fallback (non-empty)
        result = _get_structure_directive("zzz_nonexistent_heading_zzz")
        assert isinstance(result, str) and len(result) > 0
        # Empty / whitespace → still returns "" (no directive makes sense for no heading)
        assert _get_structure_directive("") == ""
        assert _get_structure_directive("   ") == ""

    def test_directive_count_minimum(self) -> None:
        """There should be a healthy number of directive entries."""
        assert len(_STRUCTURE_DIRECTIVES) >= 30, (
            f"Only {len(_STRUCTURE_DIRECTIVES)} directives defined; expected >= 30"
        )


# ===================================================================
# TS-05: Section validator multi-language normalization tests (HC-03)
# ===================================================================


class TestSectionValidatorNormalization:
    """HC-03: Verify non-Python code blocks dispatch to ts_analyzer.normalize_imports."""

    def test_section_validator_normalizes_java_imports(self):
        """Java code block with Aspose import should be normalized."""
        import json as _json
        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="java",
            canonical_import="com.aspose.cells_foss",
            repo_url="https://example.com/cells",
        )
        blocks_json = _json.dumps([{
            "type": "code",
            "content": "import com.aspose.cells.Workbook;\nWorkbook wb = new Workbook();",
            "language": "java",
            "claim_ids": [],
        }])
        result = parse_and_validate_blocks(blocks_json, product, set(), set())
        assert result is not None
        assert "cells_foss" in result[0].content

    def test_section_validator_skips_python_for_ts_normalize(self):
        """Python code blocks must NOT go through ts_analyzer."""
        import json as _json
        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="python",
            canonical_import="aspose.cells",
            repo_url="https://example.com/cells",
        )
        blocks_json = _json.dumps([{
            "type": "code",
            "content": "import aspose.cells\nwb = aspose.cells.Workbook()",
            "language": "python",
            "claim_ids": [],
        }])
        result = parse_and_validate_blocks(blocks_json, product, set(), set())
        assert result is not None
        # Python path uses _normalize_imports, not ts_normalize
        assert "aspose.cells" in result[0].content

    def test_section_validator_graceful_when_ts_unavailable(self, monkeypatch):
        """If ts_analyzer can't be imported, Java code stays unchanged."""
        import json as _json
        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="java",
            canonical_import="com.aspose.cells_foss",
            repo_url="https://example.com/cells",
        )
        blocks_json = _json.dumps([{
            "type": "code",
            "content": "import com.aspose.cells.Workbook;",
            "language": "java",
            "claim_ids": [],
        }])

        original_import = __import__
        def _mock_import(name, *args, **kwargs):
            if "ts_analyzer" in name:
                raise ImportError("mocked")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)
        result = parse_and_validate_blocks(blocks_json, product, set(), set())
        assert result is not None
        # Should not crash; content unchanged (no normalization applied)
        assert "com.aspose.cells" in result[0].content


# ---------------------------------------------------------------------------
# TC-3785: _strip_claim_citations tests
# ---------------------------------------------------------------------------


class TestStripClaimCitations:
    """Tests for _strip_claim_citations — removes [CLM-xxx] from prose."""

    def test_single_citation_at_end(self):
        text = "formats like PDF and JSON [CLM-cells-2c8d56]."
        assert _strip_claim_citations(text) == "formats like PDF and JSON."

    def test_multiple_citations(self):
        text = "supports charts [CLM-cells-0e7be6, CLM-cells-a53530]."
        assert _strip_claim_citations(text) == "supports charts."

    def test_no_citations_unchanged(self):
        text = "This is clean prose with no claim IDs."
        assert _strip_claim_citations(text) == text

    def test_non_clm_brackets_preserved(self):
        text = "See [documentation] for details [CLM-cells-abc123]."
        assert _strip_claim_citations(text) == "See [documentation] for details."

    def test_mid_sentence_citation(self):
        text = "The library [CLM-cells-abc] provides fast I/O."
        assert _strip_claim_citations(text) == "The library provides fast I/O."

    def test_citation_only(self):
        text = "[CLM-cells-abc]"
        assert _strip_claim_citations(text) == ""

    def test_parse_and_validate_strips_paragraph_citations(self):
        """Integration: parse_and_validate_blocks strips citations from paragraphs."""
        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {
                "type": "paragraph",
                "content": "Install the package [CLM-cells-abc, CLM-cells-def].",
                "claim_ids": ["CLM-cells-abc", "CLM-cells-def"],
            }
        ])
        result = parse_and_validate_blocks(
            blocks_json, product, {"CLM-cells-abc", "CLM-cells-def"}, [],
        )
        assert result is not None
        assert "[CLM-" not in result[0].content
        assert result[0].content == "Install the package."
        assert result[0].claim_ids == ["CLM-cells-abc", "CLM-cells-def"]

    def test_parse_and_validate_strips_list_item_citations(self):
        """Integration: list item citations are stripped."""
        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {
                "type": "list",
                "content": "",
                "items": [
                    "Fast I/O [CLM-cells-abc]",
                    "Clean API",
                ],
                "claim_ids": ["CLM-cells-abc"],
            }
        ])
        result = parse_and_validate_blocks(
            blocks_json, product, {"CLM-cells-abc"}, [],
        )
        assert result is not None
        assert result[0].items == ["Fast I/O", "Clean API"]

    def test_code_blocks_have_citations_stripped(self):
        """Code blocks strip both claim comments AND bracket citations (TC-3821)."""
        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {
                "type": "code",
                "content": "# some [CLM-cells-abc] in a comment\nprint('hello')",
                "language": "python",
                "claim_ids": ["CLM-cells-abc"],
            }
        ])
        result = parse_and_validate_blocks(
            blocks_json, product, {"CLM-cells-abc"}, [],
        )
        assert result is not None
        # Code content should have bracket citations stripped (defense-in-depth)
        assert "[CLM-cells-abc]" not in result[0].content
        assert "print('hello')" in result[0].content

    # --- CL-04: Expanded block type + edge case tests ---

    def test_heading_block_citations_stripped(self):
        """Heading blocks should have bracket citations removed."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {"type": "heading", "content": "Features [CLM-cells-abc]", "level": 2},
        ])
        result = parse_and_validate_blocks(blocks_json, product, {"CLM-cells-abc"}, [])
        assert result is not None
        assert "[CLM-" not in result[0].content

    def test_table_block_citations_stripped(self):
        """Table block content should have bracket citations removed."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {"type": "table", "content": "| Feature | Status [CLM-cells-abc] |\n|---|---|"},
        ])
        result = parse_and_validate_blocks(blocks_json, product, {"CLM-cells-abc"}, [])
        assert result is not None
        assert "[CLM-" not in result[0].content

    def test_callout_block_citations_stripped(self):
        """Callout block content should have bracket citations removed."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {"type": "callout", "content": "Note: this is important [CLM-cells-abc]."},
        ])
        result = parse_and_validate_blocks(blocks_json, product, {"CLM-cells-abc"}, [])
        assert result is not None
        assert "[CLM-" not in result[0].content
        assert result[0].content == "Note: this is important."

    def test_adjacent_citations_both_removed(self):
        """Adjacent bracket citations [CLM-a][CLM-b] should both be removed."""
        text = "Feature supported[CLM-cells-a][CLM-cells-b]."
        assert _strip_claim_citations(text) == "Feature supported."

    def test_trailing_whitespace_not_introduced(self):
        """Stripping should not leave trailing whitespace."""
        text = "End of line [CLM-cells-abc]"
        result = _strip_claim_citations(text)
        assert result == "End of line"
        assert not result.endswith(" ")

    def test_mixed_list_items_citation_stripped(self):
        """String list items have citations stripped; all items remain strings."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        blocks_json = json.dumps([
            {"type": "list", "content": "", "items": ["first [CLM-cells-abc]", "second"]},
        ])
        result = parse_and_validate_blocks(blocks_json, product, {"CLM-cells-abc"}, [])
        assert result is not None
        assert result[0].items == ["first", "second"]

    # --- CL-01: Logging observability tests ---

    def test_logging_when_citations_stripped(self, caplog):
        """DEBUG log should be emitted when citations are stripped."""
        import logging
        with caplog.at_level(logging.DEBUG, logger="launcher.workers.generate.section_validator"):
            _strip_claim_citations("text [CLM-cells-abc].")
        assert any("Stripped claim citations" in r.message for r in caplog.records)

    def test_no_logging_when_no_citations(self, caplog):
        """DEBUG log should NOT be emitted when no citations present."""
        import logging
        with caplog.at_level(logging.DEBUG, logger="launcher.workers.generate.section_validator"):
            _strip_claim_citations("clean text with no claims.")
        assert not any("Stripped claim citations" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# BT-04: _backtick_api_names tests
# ---------------------------------------------------------------------------


class TestBacktickApiNames:
    """Tests for _backtick_api_names() disambiguation and wrapping."""

    def test_basic_wrapping(self):
        result = _backtick_api_names("Use Workbook to open files", {"Workbook"}, "Aspose.Cells")
        assert result == "Use `Workbook` to open files"

    def test_already_backticked(self):
        result = _backtick_api_names("Use `Workbook` to open", {"Workbook"}, "Aspose.Cells")
        assert result == "Use `Workbook` to open"

    def test_display_name_protection(self):
        """'Cells' inside 'Aspose.Cells' must not be backticked."""
        result = _backtick_api_names("Aspose.Cells provides APIs", {"Cells"}, "Aspose.Cells")
        assert "`Cells`" not in result
        assert "Aspose.Cells" in result

    def test_case_sensitive_lowercase_skipped(self):
        """Lowercase 'cells' must not match identifier 'Cells'."""
        result = _backtick_api_names("The cells are empty", {"Cells"}, "Aspose.Cells")
        assert result == "The cells are empty"

    def test_longest_first_matching(self):
        """'CellArea' must match before 'Cell' to avoid partial wrapping."""
        result = _backtick_api_names("CellArea and Cell", {"CellArea", "Cell"}, "Aspose.Cells")
        assert "`CellArea`" in result
        assert "`Cell`" in result
        # CellArea should NOT be wrapped as `Cell`Area
        assert "`Cell`Area" not in result

    def test_markdown_link_protection(self):
        result = _backtick_api_names("[Workbook](https://example.com)", {"Workbook"}, "Aspose.Cells")
        assert "`Workbook`" not in result

    def test_empty_content(self):
        result = _backtick_api_names("", {"Workbook"}, "Aspose.Cells")
        assert result == ""

    def test_empty_identifiers(self):
        result = _backtick_api_names("Use Workbook", set(), "Aspose.Cells")
        assert result == "Use Workbook"

    def test_none_identifiers(self):
        # Passing None shouldn't crash — function checks truthiness
        result = _backtick_api_names("Use Workbook", None, "Aspose.Cells")
        assert result == "Use Workbook"

    def test_table_cell_content(self):
        result = _backtick_api_names("| Workbook | open |", {"Workbook"}, "Aspose.Cells")
        assert "`Workbook`" in result

    def test_longest_first_prevents_partial(self):
        """AnnotatedTextList must not be partially matched as AnnotatedText."""
        result = _backtick_api_names(
            "AnnotatedTextList has items",
            {"AnnotatedTextList", "AnnotatedText"},
            "Aspose.Note",
        )
        assert "`AnnotatedTextList`" in result
        assert "`AnnotatedText`List" not in result

    def test_multiple_matches(self):
        result = _backtick_api_names(
            "Use Workbook and Worksheet",
            {"Workbook", "Worksheet"},
            "Aspose.Cells",
        )
        assert "`Workbook`" in result
        assert "`Worksheet`" in result

    def test_snake_case_identifier(self):
        result = _backtick_api_names("Use get_cell method", {"get_cell"}, "Aspose.Cells")
        assert "`get_cell`" in result


class TestCompileApiPatternCache:
    """Tests for _compile_api_pattern() caching behavior."""

    def test_cache_hit(self):
        _compile_api_pattern.cache_clear()
        ids = ("Workbook", "Worksheet")
        p1 = _compile_api_pattern(ids)
        p2 = _compile_api_pattern(ids)
        assert p1 is p2
        assert _compile_api_pattern.cache_info().hits >= 1

    def test_cache_miss_on_different_input(self):
        _compile_api_pattern.cache_clear()
        p1 = _compile_api_pattern(("Workbook",))
        p2 = _compile_api_pattern(("Worksheet",))
        assert p1 is not p2


class TestTableBlockBacktickOrdering:
    """BT-01: Verify backticks survive table content restructuring."""

    def test_json_table_content_gets_backticked(self):
        """Table with JSON array content: backticks applied after restructure."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose.cells",
            repo_url="https://example.com", repo_sha="abc",
        )
        raw_response = json.dumps([{
            "type": "table",
            "content": '[{"Class": "Workbook", "Description": "Main entry point"}]',
            "claim_ids": [],
        }])
        blocks = parse_and_validate_blocks(
            raw_response, product, set(), [],
            api_identifiers={"Workbook"},
        )
        assert blocks is not None
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.table
        # Content should be pipe-delimited AND have Workbook backticked
        assert "|" in blocks[0].content
        assert "`Workbook`" in blocks[0].content

    def test_pipe_table_content_gets_backticked(self):
        """Table already pipe-delimited: backticks applied correctly."""
        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose.cells",
            repo_url="https://example.com", repo_sha="abc",
        )
        raw_response = json.dumps([{
            "type": "table",
            "content": "| Class | Desc |\n| --- | --- |\n| Workbook | Entry |",
            "claim_ids": [],
        }])
        blocks = parse_and_validate_blocks(
            raw_response, product, set(), [],
            api_identifiers={"Workbook"},
        )
        assert blocks is not None
        assert "`Workbook`" in blocks[0].content


# ===========================================================================
# TC-4220: Prose word counter and section retry tests
# ===========================================================================


class TestCountProseWords:
    """TC-4220: Unit tests for _count_prose_words helper."""

    def test_count_prose_words_excludes_headings_and_bullets(self):
        """Headings, bullets, code fences excluded; 5 prose words counted."""
        text = (
            "## Overview\n"
            "- bullet one\n"
            "- bullet two\n"
            "```python\nprint('hello')\n```\n"
            "This is prose text here."
        )
        # "This is prose text here." → 5 words
        assert _count_prose_words(text) == 5

    def test_count_prose_words_code_fence_excluded(self):
        """A section with only fenced code and no prose returns 0."""
        text = (
            "```python\n"
            "import aspose.cells\n"
            "wb = aspose.cells.Workbook()\n"
            "wb.save('out.xlsx')\n"
            "```"
        )
        assert _count_prose_words(text) == 0

    def test_section_retry_capped_at_max(self, tmp_path: Path):
        """TC-4220: LLM always returns thin content; _call_llm called exactly
        (MAX_SECTION_RETRIES+1) * num_sections times total.

        Uses the 'faq' page role which has exactly 2 required sections, so
        expected total = 2 * (1 initial + 2 retries) = 6 LLM calls.
        """
        import asyncio
        from unittest.mock import patch

        from launcher.models.run_config import LLMConfig, LLMEndpoint
        from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS
        from launcher.workers.generate.worker import _generate_page

        # Thin response: only a bullet list block — 0 prose words
        thin_response = json.dumps([
            {"type": "list", "items": ["step one", "step two"], "claim_ids": []},
        ])

        page_role = "faq"
        num_sections = len(PAGE_ROLE_SKELETONS[page_role])  # 2 sections

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose.cells",
            repo_url="https://github.com/test/cells", repo_sha="abc123",
        )
        page_plan = PlannedPage(
            page_id="docs-test-retry",
            page_role=page_role,
            title="Test Retry Page",
            skeleton=[s.heading for s in PAGE_ROLE_SKELETONS[page_role]],
            assigned_claims=[],
            assigned_snippets=[],
            frontmatter={
                "slug": "test-retry",
                "title": "Test Retry Page",
                "type": page_role,
                "url": f"/cells/python/test-retry/",
                "weight": 1,
                "family": "cells",
                "platform": "python",
                "page_role": page_role,
                "robots": "index, follow",
            },
        )

        run_dir = tmp_path / "runs" / "retry-test"
        run_dir.mkdir(parents=True, exist_ok=True)
        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/cells",
            llm=LLMConfig(
                primary=LLMEndpoint(
                    base_url="http://localhost:11434/v1",
                    model="test-model",
                ),
            ),
        )
        context = WorkerContext(
            run_id="retry-test-001",
            run_dir=run_dir,
            config=config,
            llm_config=config.llm,
        )

        call_count = 0

        async def mock_call_llm(prompt, ctx, max_tokens=None, _override_temperature=None):
            nonlocal call_count
            call_count += 1
            return thin_response, ""

        with patch("launcher.workers.generate.worker._call_llm", side_effect=mock_call_llm):
            from launcher.models.product import ApiSurface
            api_surface = ApiSurface(
                public_classes=[],
                import_allowlist=["aspose.cells"],
                confidence="high",
            )
            asyncio.run(_generate_page(
                page_plan, product, [], [],
                ["aspose.cells"], context,
                api_surface=api_surface,
            ))

        # GEN-6 (TC-5204): "See Also" sections bypass LLM entirely; only count
        # sections that are NOT in _SKIP_LLM_HEADINGS for expected call count.
        from launcher.workers.generate.worker import _SKIP_LLM_HEADINGS
        llm_sections = [
            s for s in PAGE_ROLE_SKELETONS[page_role]
            if s.heading.lower().strip() not in _SKIP_LLM_HEADINGS
        ]
        num_llm_sections = len(llm_sections)

        # Each LLM section: 1 initial + MAX_SECTION_RETRIES retries
        calls_per_section = _MAX_SECTION_RETRIES + 1
        expected_calls = calls_per_section * num_llm_sections
        assert call_count == expected_calls, (
            f"Expected {expected_calls} LLM calls "
            f"({calls_per_section} per section × {num_llm_sections} LLM sections"
            f" of {num_sections} total, GEN-6 bypasses 'See Also'), "
            f"got {call_count}"
        )
