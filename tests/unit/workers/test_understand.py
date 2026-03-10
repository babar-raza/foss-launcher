"""Comprehensive tests for the Understand worker (Phase 2).

Covers Scout, Extract, Plan, Self-review, and Surface Classifier
without network access or LLM calls.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Any

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.product import (
    ApiSurface,
    ProductIdentity,
    RichnessResult,
    RichnessTier,
)
from launcher.models.run_config import LLMConfig, LLMEndpoint, RunConfig
from launcher.models.understanding import PlannedPage, RepoInfo, UnderstandingBundle
from launcher.orchestrator.worker_contract import SelfReviewResult


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def cells_config() -> RunConfig:
    """RunConfig for cells/python without LLM."""
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
    )


@pytest.fixture
def note_config() -> RunConfig:
    """RunConfig for note/python without LLM."""
    return RunConfig(
        family="note",
        platform="python",
        repo_url="https://github.com/aspose/aspose-note-foss-python",
    )


@pytest.fixture
def cells_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells FOSS for Python",
        canonical_import="aspose_cells_foss",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
    )


@pytest.fixture
def note_product() -> ProductIdentity:
    return ProductIdentity(
        family="note",
        platform="python",
        display_name="Aspose.Note FOSS for Python",
        canonical_import="aspose_note_foss",
        repo_url="https://github.com/aspose/aspose-note-foss-python",
    )


@pytest.fixture
def richness_a() -> RichnessResult:
    return RichnessResult(tier=RichnessTier.A, score=30, reason="rich")


@pytest.fixture
def richness_b() -> RichnessResult:
    return RichnessResult(tier=RichnessTier.B, score=15, reason="moderate")


@pytest.fixture
def richness_c() -> RichnessResult:
    return RichnessResult(tier=RichnessTier.C, score=5, reason="thin")


@pytest.fixture
def sample_claims(cells_product: ProductIdentity) -> list[Claim]:
    """A set of claims covering multiple kinds for plan tests."""
    return [
        Claim(
            claim_id="CLM-cells-001",
            text="Supports reading and writing XLSX spreadsheet files",
            kind="feature",
            evidence=[EvidenceAnchor(source_file="README.md", line_start=10, line_end=10, snippet="XLSX support")],
            visibility="public",
            tier_relevance="all",
        ),
        Claim(
            claim_id="CLM-cells-002",
            text="Install via pip install aspose-cells-foss",
            kind="install",
            evidence=[EvidenceAnchor(source_file="README.md", line_start=5, line_end=5, snippet="pip install")],
            visibility="public",
            tier_relevance="all",
        ),
        Claim(
            claim_id="CLM-cells-003",
            text="WorkbookProcessor class handles cell manipulation",
            kind="api",
            evidence=[EvidenceAnchor(source_file="src/api.py", line_start=1, line_end=20, snippet="class WorkbookProcessor")],
            visibility="public",
            tier_relevance="full",
        ),
        Claim(
            claim_id="CLM-cells-004",
            text="Convert spreadsheets between XLSX and CSV formats",
            kind="format",
            evidence=[EvidenceAnchor(source_file="docs/formats.md", line_start=1, line_end=5, snippet="format conversion")],
            visibility="public",
            tier_relevance="all",
        ),
        Claim(
            claim_id="CLM-cells-005",
            text="Troubleshoot common file loading errors and solutions",
            kind="troubleshoot",
            evidence=[EvidenceAnchor(source_file="docs/troubleshoot.md", line_start=1, line_end=5, snippet="errors")],
            visibility="public",
            tier_relevance="all",
        ),
    ]


@pytest.fixture
def sample_snippets() -> list[Snippet]:
    return [
        Snippet(
            code="from aspose_cells_foss import WorkbookProcessor\nwb = WorkbookProcessor()",
            language="python",
            source_type="extracted",
            claim_ids=["CLM-cells-001", "CLM-cells-003"],
        ),
    ]


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a fake repo directory structure for Scout tests."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # .git directory (should be excluded)
    (repo / ".git").mkdir()
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main")

    # __pycache__ (should be excluded)
    (repo / "src" / "__pycache__").mkdir(parents=True)
    (repo / "src" / "__pycache__" / "module.cpython-311.pyc").write_bytes(b"\x00")

    # Source files
    (repo / "src" / "aspose_cells_foss").mkdir(parents=True)
    (repo / "src" / "aspose_cells_foss" / "__init__.py").write_text(
        'from .core import Workbook\n__all__ = ["Workbook"]\n'
    )
    (repo / "src" / "aspose_cells_foss" / "core.py").write_text(
        textwrap.dedent("""\
        class Workbook:
            \"\"\"Main workbook class.\"\"\"
            def load(self, path: str) -> None:
                pass
        class _Internal:
            pass
        """)
    )

    # README
    (repo / "README.md").write_text("# Aspose.Cells FOSS\n\nA library for spreadsheets.\n" * 40)

    # Doc files
    (repo / "docs").mkdir()
    (repo / "docs" / "guide.md").write_text("# Getting Started\n\n- Install via pip\n- Load a workbook\n")
    (repo / "docs" / "api.rst").write_text("API Reference\n=============\n")

    # Excluded doc files
    (repo / "LICENSE.md").write_text("MIT License")
    (repo / "CHANGELOG.md").write_text("## 1.0.0\n- Initial release")
    (repo / "CONTRIBUTING.md").write_text("# Contributing\n")

    # Example files
    (repo / "examples").mkdir()
    (repo / "examples" / "basic_example.py").write_text(
        "from aspose_cells_foss import Workbook\nwb = Workbook()\n"
    )
    (repo / "examples" / "demo_convert.py").write_text(
        "from aspose_cells_foss import Workbook\nwb = Workbook()\nwb.load('test.xlsx')\n"
    )

    # Test files (should not be in API surface)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_core.py").write_text("def test_load(): pass\n")

    # CI
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")

    return repo


# ===================================================================
# Understand worker repo_dir guard (SR-01)
# ===================================================================


class TestUnderstandWorkerRepoGuard:
    """Test repo_dir validity guard at Understand entry (SR-01 / G-02)."""

    @pytest.mark.asyncio
    async def test_understand_rejects_missing_repo_dir(self, tmp_path: Path) -> None:
        """Stale/missing repo_dir raises ValueError with clear message."""
        from launcher.workers.understand.worker import UnderstandWorker
        from launcher.models.intake import IntakeBundle
        from launcher.orchestrator.worker_contract import WorkerContext

        worker = UnderstandWorker()
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(tmp_path / "nonexistent_repo"),
            repo_sha="a" * 40,
        )
        config = RunConfig(
            family="cells", platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
        )
        context = WorkerContext(
            run_id="test-guard", run_dir=tmp_path, config=config,
        )
        with pytest.raises(ValueError, match="repo_dir does not exist"):
            await worker.run(bundle, context)

    @pytest.mark.asyncio
    async def test_understand_rejects_empty_repo_dir(self, tmp_path: Path) -> None:
        """Empty repo_dir (from clone failure) raises ValueError."""
        from launcher.workers.understand.worker import UnderstandWorker
        from launcher.models.intake import IntakeBundle
        from launcher.orchestrator.worker_contract import WorkerContext

        worker = UnderstandWorker()
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir="",
            repo_sha="",
        )
        config = RunConfig(
            family="cells", platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
        )
        context = WorkerContext(
            run_id="test-guard-empty", run_dir=tmp_path, config=config,
        )
        with pytest.raises(ValueError, match="repo_dir does not exist"):
            await worker.run(bundle, context)


# ===================================================================
# Scout tests
# ===================================================================


class TestScoutWalkFileTree:
    """Test _walk_file_tree with pre-created directories."""

    def test_walk_file_tree_excludes_git(self, fake_repo: Path) -> None:
        """Verify .git and __pycache__ directories are excluded from file tree."""
        from launcher.workers.understand.scout import _walk_file_tree

        tree, file_index = _walk_file_tree(fake_repo)

        # .git contents must not appear
        assert not any(".git/" in p or ".git\\" in p or p == ".git" for p in tree)
        # __pycache__ must not appear
        assert not any("__pycache__" in p for p in tree)
        # Real files should be present
        assert any("README.md" in p for p in tree)
        assert any("core.py" in p for p in tree)

    def test_walk_file_tree_returns_forward_slashes(self, fake_repo: Path) -> None:
        """All paths use forward slashes regardless of OS."""
        from launcher.workers.understand.scout import _walk_file_tree

        tree, _ = _walk_file_tree(fake_repo)
        for p in tree:
            assert "\\" not in p, f"Backslash found in path: {p}"

    def test_walk_file_tree_respects_max_files(self, fake_repo: Path) -> None:
        """max_files parameter caps the number of returned paths."""
        from launcher.workers.understand.scout import _walk_file_tree

        tree, _ = _walk_file_tree(fake_repo, max_files=3)
        assert len(tree) <= 3


class TestFileClassifierDoc:
    """Test classify_file doc detection (replaces old _is_doc_path tests)."""

    def test_doc_markdown(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("docs/guide.md") == FileCategory.doc
        assert classify_file("README.md") == FileCategory.doc

    def test_doc_rst(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("docs/api.rst") == FileCategory.doc

    def test_doc_txt_in_docs_dir(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("docs/notes.txt") == FileCategory.doc

    def test_doc_license_is_doc(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("LICENSE.md") == FileCategory.doc

    def test_doc_changelog_is_doc(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("CHANGELOG.md") == FileCategory.doc

    def test_doc_rejects_python(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("src/module.py") == FileCategory.source

    def test_doc_adoc(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("docs/overview.adoc") == FileCategory.doc


class TestFileClassifierExample:
    """Test classify_file example detection (replaces old _is_example_path tests)."""

    def test_example_dir(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("examples/basic_example.py") == FileCategory.example

    def test_sample_dir(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("samples/sample_usage.py") == FileCategory.example

    def test_demo_dir(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("demo/run_demo.py") == FileCategory.example

    def test_tutorial_dir(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("tutorial/step1.py") == FileCategory.example

    def test_rejects_source(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("src/core.py") == FileCategory.source

    def test_rejects_test(self) -> None:
        from launcher.workers.understand.file_classifier import classify_file
        from launcher.models.understanding import FileCategory

        assert classify_file("tests/test_core.py") == FileCategory.test


class TestScoutReadReadme:
    """Test _read_readme truncation."""

    def test_read_readme_truncates(self, tmp_path: Path) -> None:
        """README content is limited to 4000 chars."""
        from launcher.workers.understand.scout import _read_readme

        repo = tmp_path / "repo"
        repo.mkdir()
        long_readme = "x" * 5000
        (repo / "README.md").write_text(long_readme)

        result = _read_readme(repo)
        assert len(result) == 4000

    def test_read_readme_short_content(self, tmp_path: Path) -> None:
        """Short README is returned in full."""
        from launcher.workers.understand.scout import _read_readme

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("Hello World")

        result = _read_readme(repo)
        assert result == "Hello World"

    def test_read_readme_missing(self, tmp_path: Path) -> None:
        """Missing README returns empty string."""
        from launcher.workers.understand.scout import _read_readme

        repo = tmp_path / "repo"
        repo.mkdir()

        result = _read_readme(repo)
        assert result == ""

    def test_read_readme_case_variants(self, tmp_path: Path) -> None:
        """Finds readme.md (lowercase) variant."""
        from launcher.workers.understand.scout import _read_readme

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "readme.md").write_text("lowercase readme")

        result = _read_readme(repo)
        assert result == "lowercase readme"


# ===================================================================
# Extract tests (no LLM)
# ===================================================================


class TestExtractClaimsDeterministic:
    """Test deterministic claim extraction from markdown."""

    def test_extract_claims_deterministic_headings_and_bullets(
        self, cells_product: ProductIdentity
    ) -> None:
        """Markdown with headings and bullets produces claims."""
        from launcher.workers.understand.extract import _extract_claims_deterministic

        doc_contexts = [
            {
                "path": "README.md",
                "content": textwrap.dedent("""\
                    # Features

                    - Supports reading XLSX files with full fidelity
                    - Handles large spreadsheets with streaming mode
                    - Converts between multiple format types easily

                    # Installation

                    - Install via pip install aspose-cells-foss
                    """),
            }
        ]

        claims = _extract_claims_deterministic(doc_contexts, cells_product)

        assert len(claims) >= 4
        # All claims should have visibility=public
        assert all(c["visibility"] == "public" for c in claims)
        # All claims should have claim_id starting with CLM-
        assert all(c["claim_id"].startswith("CLM-") for c in claims)
        # Check kind classification
        kinds = {c["kind"] for c in claims}
        assert "install" in kinds  # the install bullet
        assert "feature" in kinds  # the feature bullets

    def test_extract_claims_skips_short_bullets(
        self, cells_product: ProductIdentity
    ) -> None:
        """Bullets shorter than 10 chars are skipped."""
        from launcher.workers.understand.extract import _extract_claims_deterministic

        doc_contexts = [
            {
                "path": "README.md",
                "content": "# Features\n\n- Short\n- This is a sufficiently long claim text here\n",
            }
        ]

        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        texts = [c["text"] for c in claims]
        assert "Short" not in texts
        assert any("sufficiently long" in t for t in texts)

    def test_extract_claims_paragraphs(
        self, cells_product: ProductIdentity
    ) -> None:
        """Substantial paragraphs under headings are captured."""
        from launcher.workers.understand.extract import _extract_claims_deterministic

        doc_contexts = [
            {
                "path": "docs/guide.md",
                "content": "# Overview\n\nThis library provides comprehensive spreadsheet manipulation capabilities for Python developers.\n",
            }
        ]

        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        assert len(claims) >= 1
        assert any("comprehensive" in c["text"] for c in claims)


class TestExtractValidatePython:
    """Test Python syntax validation."""

    def test_validate_python_syntax_valid(self) -> None:
        from launcher.workers.understand.extract import _validate_python_syntax

        assert _validate_python_syntax("x = 1\nprint(x)") is True

    def test_validate_python_syntax_valid_class(self) -> None:
        from launcher.workers.understand.extract import _validate_python_syntax

        code = textwrap.dedent("""\
            class MyClass:
                def method(self):
                    return 42
            """)
        assert _validate_python_syntax(code) is True

    def test_validate_python_syntax_invalid(self) -> None:
        from launcher.workers.understand.extract import _validate_python_syntax

        assert _validate_python_syntax("def broken(") is False

    def test_validate_python_syntax_invalid_indent(self) -> None:
        from launcher.workers.understand.extract import _validate_python_syntax

        assert _validate_python_syntax("  x = 1\nx = 2") is False

    def test_validate_python_syntax_empty(self) -> None:
        from launcher.workers.understand.extract import _validate_python_syntax

        assert _validate_python_syntax("") is True


class TestExtractClaimIdGeneration:
    """Test stable claim ID generation."""

    def test_claim_id_generation_stable(self, cells_product: ProductIdentity) -> None:
        """Same input produces same CLM-xxx ID across multiple calls."""
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {
                "text": "Supports reading XLSX files",
                "kind": "feature",
                "visibility": "public",
                "evidence": [],
            }
        ]

        result_a = _validate_and_normalize_claims(raw, cells_product, api)
        result_b = _validate_and_normalize_claims(raw, cells_product, api)

        assert len(result_a) == 1
        assert len(result_b) == 1
        assert result_a[0].claim_id == result_b[0].claim_id
        assert result_a[0].claim_id.startswith("CLM-cells-")

    def test_different_text_different_id(self, cells_product: ProductIdentity) -> None:
        """Different claim text produces different IDs."""
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Claim Alpha about reading files", "kind": "feature", "visibility": "public", "evidence": []},
            {"text": "Claim Beta about writing files", "kind": "feature", "visibility": "public", "evidence": []},
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        ids = [c.claim_id for c in result]
        assert len(set(ids)) == len(ids), "Claim IDs should be unique"


class TestExtractClaimDedupJaccard:
    """Test near-duplicate claim merging via Jaccard similarity."""

    def test_claim_dedup_jaccard(self, cells_product: ProductIdentity) -> None:
        """Near-duplicate claims (Jaccard > 0.8) are merged."""
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {
                "text": "This library supports reading and writing XLSX spreadsheet files easily",
                "kind": "feature",
                "visibility": "public",
                "evidence": [],
            },
            {
                # Near-duplicate: only one word different out of many
                "text": "This library supports reading and writing XLSX spreadsheet documents easily",
                "kind": "feature",
                "visibility": "public",
                "evidence": [],
            },
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        # Jaccard > 0.8: 9 shared out of 11 total unique words -> ~0.82
        assert len(result) == 1

    def test_distinct_claims_kept(self, cells_product: ProductIdentity) -> None:
        """Clearly distinct claims are all kept."""
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Install the package via pip for Python projects", "kind": "install", "visibility": "public", "evidence": []},
            {"text": "Convert spreadsheets between XLSX and CSV format types", "kind": "format", "visibility": "public", "evidence": []},
            {"text": "Debug common errors with the troubleshooting guide", "kind": "troubleshoot", "visibility": "public", "evidence": []},
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        assert len(result) == 3

    def test_internal_claims_filtered(self, cells_product: ProductIdentity) -> None:
        """Claims with visibility=internal are removed during normalization."""
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Public feature claim for users", "kind": "feature", "visibility": "public", "evidence": []},
            {"text": "Internal implementation detail claim", "kind": "feature", "visibility": "internal", "evidence": []},
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        assert len(result) == 1
        assert result[0].visibility == "public"


# ===================================================================
# Plan tests
# ===================================================================


class TestPlanEnumerateMandatoryPages:
    """Test mandatory page enumeration from ruleset."""

    def test_enumerate_mandatory_pages(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Correct mandatory pages are produced from the real ruleset."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        page_roles = [p.page_role for p in pages]
        # Should have landing, toc pages, workflow pages, etc.
        assert "landing" in page_roles
        assert "toc" in page_roles
        assert "workflow_page" in page_roles
        assert "faq" in page_roles

        # Check that mandatory pages exist
        mandatory_pages = [p for p in pages if p.mandatory]
        assert len(mandatory_pages) >= 5  # several sections contribute mandatory pages

    def test_tier_minimum_skips_higher_tier_pages(
        self,
        cells_product: ProductIdentity,
        richness_c: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Pages with tier_minimum=core are skipped at Tier C (minimal)."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_c, sample_claims, sample_snippets)

        # Troubleshooting page has tier_minimum: core in ruleset,
        # so it should be absent at Tier C
        page_ids = [p.page_id for p in pages]
        assert "kb/troubleshooting" not in page_ids


class TestPlanFamilyOverride:
    """Test family-specific page overrides."""

    def test_family_override_adds_pages(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Cells family gets spreadsheet-operations and formula-calculation."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        page_ids = [p.page_id for p in pages]
        assert "docs/spreadsheet-operations" in page_ids
        assert "docs/formula-calculation" in page_ids

    def test_note_family_override(
        self,
        note_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Note family gets notebook-manipulation and document-conversion."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(note_product, richness_a, sample_claims, sample_snippets)

        page_ids = [p.page_id for p in pages]
        assert "docs/notebook-manipulation" in page_ids
        assert "docs/document-conversion" in page_ids
        # Cells-specific pages should NOT appear
        assert "docs/spreadsheet-operations" not in page_ids


class TestPlanClaimAssignment:
    """Test claim assignment constraints."""

    def test_claim_assignment_max_2(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """No claim appears on more than 2 pages."""
        from launcher.workers.planner.plan import run_plan

        pages, claim_index = run_plan(
            cells_product, richness_a, sample_claims, sample_snippets
        )

        for claim_id, page_ids in claim_index.items():
            assert len(page_ids) <= 2, (
                f"Claim {claim_id} assigned to {len(page_ids)} pages (max 2): {page_ids}"
            )

    def test_toc_pages_have_no_claims(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """TOC pages should not receive claim assignments."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        toc_pages = [p for p in pages if p.page_role == "toc"]
        for toc in toc_pages:
            assert toc.assigned_claims == [], f"TOC page {toc.page_id} has claims"


class TestPlanFrontmatter:
    """Test frontmatter generation."""

    def test_frontmatter_has_required_fields(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Every page's frontmatter contains slug, title, and url."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        for page in pages:
            fm = page.frontmatter
            assert "slug" in fm, f"Page {page.page_id} missing 'slug' in frontmatter"
            assert "title" in fm, f"Page {page.page_id} missing 'title' in frontmatter"
            assert "url" in fm, f"Page {page.page_id} missing 'url' in frontmatter"
            # URL should start and end with /
            assert fm["url"].startswith("/"), f"URL should start with /: {fm['url']}"
            assert fm["url"].endswith("/"), f"URL should end with /: {fm['url']}"

    def test_frontmatter_family_and_platform(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """Frontmatter carries family and platform from product identity."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        for page in pages:
            fm = page.frontmatter
            assert fm.get("family") == "cells"
            assert fm.get("platform") == "python"


class TestPlanPermalinkUniqueness:
    """Test permalink/slug uniqueness."""

    def test_permalink_uniqueness(
        self,
        cells_product: ProductIdentity,
        richness_a: RichnessResult,
        sample_claims: list[Claim],
        sample_snippets: list[Snippet],
    ) -> None:
        """No duplicate slugs/URLs across all pages."""
        from launcher.workers.planner.plan import run_plan

        pages, _ = run_plan(cells_product, richness_a, sample_claims, sample_snippets)

        urls = [p.frontmatter["url"] for p in pages]
        assert len(urls) == len(set(urls)), (
            f"Duplicate URLs found: {[u for u in urls if urls.count(u) > 1]}"
        )

        page_ids = [p.page_id for p in pages]
        assert len(page_ids) == len(set(page_ids)), "Duplicate page_ids found"


# ===================================================================
# Self-review tests
# ===================================================================


class TestSelfReview:
    """Test UnderstandWorker.self_review()."""

    def _make_bundle(
        self,
        claims: list[Claim],
        snippets: list[Snippet] | None = None,
    ) -> UnderstandingBundle:
        """Helper to build a minimal UnderstandingBundle."""
        return UnderstandingBundle(
            product=ProductIdentity(
                family="cells",
                platform="python",
                display_name="Aspose.Cells FOSS for Python",
                canonical_import="aspose_cells_foss",
                repo_url="https://github.com/test/repo",
            ),
            repo=RepoInfo(file_tree=[], doc_paths=[], example_paths=[], readme_summary=""),
            richness_tier=RichnessResult(tier=RichnessTier.B, score=15, reason="test"),
            api_surface=ApiSurface(public_classes=[], import_allowlist=[], confidence="low"),
            claims=claims,
            snippets=snippets or [],
        )

    @pytest.mark.asyncio
    async def test_self_review_passes_clean_bundle(self) -> None:
        """A valid bundle with all public claims passes self-review."""
        from launcher.workers.understand.worker import UnderstandWorker

        worker = UnderstandWorker()

        claims = [
            Claim(claim_id="CLM-001", text="Valid claim", kind="feature", visibility="public"),
        ]
        bundle = self._make_bundle(claims)

        result = await worker.self_review(bundle)
        assert result.passed is True
        assert result.metrics["total_claims"] == 1

    @pytest.mark.asyncio
    async def test_self_review_tracks_internal_claims(self) -> None:
        """Internal claims are tracked in metrics (not a blocking finding)."""
        from launcher.workers.understand.worker import UnderstandWorker

        worker = UnderstandWorker()

        claims = [
            Claim(claim_id="CLM-001", text="Internal detail", kind="feature", visibility="internal"),
        ]
        bundle = self._make_bundle(claims)

        result = await worker.self_review(bundle)
        # Internal claims are expected from claim classifier — not a blocking error
        assert result.metrics.get("internal_claims_filtered") == 1

    @pytest.mark.asyncio
    async def test_self_review_catches_bad_python_snippets(self) -> None:
        """Invalid Python snippets produce a code_syntax finding."""
        from launcher.workers.understand.worker import UnderstandWorker

        worker = UnderstandWorker()

        claims = [
            Claim(claim_id="CLM-001", text="A claim", kind="feature", visibility="public"),
        ]
        bad_snippets = [
            Snippet(code="def broken(", language="python", source_type="extracted"),
        ]
        bundle = self._make_bundle(claims, snippets=bad_snippets)

        result = await worker.self_review(bundle)
        syntax_findings = [f for f in result.findings if f["category"] == "code_syntax"]
        assert len(syntax_findings) == 1
        assert result.metrics["bad_snippets"] == 1

    @pytest.mark.asyncio
    async def test_self_review_non_bundle_fails(self) -> None:
        """Passing a non-UnderstandingBundle object fails immediately."""
        from launcher.workers.understand.worker import UnderstandWorker
        from launcher.models.run_config import RunConfig

        worker = UnderstandWorker()
        config = RunConfig(
            family="cells", platform="python",
            repo_url="https://github.com/test/repo",
        )

        result = await worker.self_review(config)
        assert result.passed is False


# ===================================================================
# Surface classifier tests
# ===================================================================


class TestSurfaceClassifier:
    """Test richness classification."""

    def test_classify_rich_repo(self) -> None:
        """Many docs + examples + tests + CI -> Tier A."""
        from launcher.shared.surface_classifier import classify_richness_with_surface

        repo_info = RepoInfo(
            file_tree=[
                "README.md",
                "docs/guide1.md", "docs/guide2.md", "docs/guide3.md",
                "docs/guide4.md", "docs/guide5.md", "docs/guide6.md",
                "docs/guide7.md", "docs/guide8.md", "docs/guide9.md",
                "docs/guide10.md",
                "examples/ex1.py", "examples/ex2.py", "examples/ex3.py",
                "examples/ex4.py", "examples/ex5.py", "examples/ex6.py",
                "examples/ex7.py", "examples/ex8.py", "examples/ex9.py",
                "examples/ex10.py",
                "tests/test_core.py",
                ".github/workflows/ci.yml",
                "src/core.py",
            ],
            doc_paths=[
                "README.md",
                "docs/guide1.md", "docs/guide2.md", "docs/guide3.md",
                "docs/guide4.md", "docs/guide5.md", "docs/guide6.md",
                "docs/guide7.md", "docs/guide8.md", "docs/guide9.md",
                "docs/guide10.md",
            ],
            example_paths=[
                "examples/ex1.py", "examples/ex2.py", "examples/ex3.py",
                "examples/ex4.py", "examples/ex5.py", "examples/ex6.py",
                "examples/ex7.py", "examples/ex8.py", "examples/ex9.py",
                "examples/ex10.py",
            ],
            readme_summary="x" * 600,  # > 500 chars
        )

        result = classify_richness_with_surface(
            repo_info,
            api_confidence="high",
            public_class_count=25,
        )

        assert result.tier == RichnessTier.A
        assert result.score >= 25

    def test_classify_thin_repo(self) -> None:
        """No docs, no examples, no tests -> Tier C."""
        from launcher.shared.surface_classifier import classify_richness_with_surface

        repo_info = RepoInfo(
            file_tree=["setup.py", "src/module.py"],
            doc_paths=[],
            example_paths=[],
            readme_summary="short",
        )

        result = classify_richness_with_surface(
            repo_info,
            api_confidence="low",
            public_class_count=2,
        )

        assert result.tier == RichnessTier.C
        assert result.score < 12

    def test_classify_medium_repo(self) -> None:
        """Moderate content -> Tier B."""
        from launcher.shared.surface_classifier import classify_richness_with_surface

        repo_info = RepoInfo(
            file_tree=[
                "README.md",
                "docs/guide.md", "docs/api.md", "docs/install.md",
                "examples/sample.py",
                "tests/test_core.py",
                "src/module.py",
            ],
            doc_paths=["README.md", "docs/guide.md", "docs/api.md", "docs/install.md"],
            example_paths=["examples/sample.py"],
            readme_summary="x" * 600,
        )

        result = classify_richness_with_surface(
            repo_info,
            api_confidence="medium",
            public_class_count=5,
        )

        assert result.tier == RichnessTier.B
        assert 12 <= result.score < 25

    def test_api_confidence_high_adds_10_points(self) -> None:
        """High API confidence adds 10 points to the score."""
        from launcher.shared.surface_classifier import (
            classify_richness,
            classify_richness_with_surface,
        )

        repo_info = RepoInfo(
            file_tree=["src/module.py"],
            doc_paths=[],
            example_paths=[],
            readme_summary="",
        )

        base = classify_richness(repo_info)
        with_surface = classify_richness_with_surface(
            repo_info, api_confidence="high", public_class_count=0,
        )

        assert with_surface.score == base.score + 10


# ===================================================================
# Additional extract helper tests
# ===================================================================


class TestExtractFencedCodeBlocks:
    """Test fenced code block extraction from markdown."""

    def test_extracts_python_block(self) -> None:
        from launcher.workers.understand.extract import _extract_fenced_code_blocks

        content = "Some text\n```python\nx = 1\n```\nMore text\n"
        blocks = _extract_fenced_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0][0] == "python"
        assert "x = 1" in blocks[0][1]

    def test_extracts_multiple_blocks(self) -> None:
        from launcher.workers.understand.extract import _extract_fenced_code_blocks

        content = "```python\na = 1\n```\n\n```bash\necho hi\n```\n"
        blocks = _extract_fenced_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "bash"

    def test_no_blocks(self) -> None:
        from launcher.workers.understand.extract import _extract_fenced_code_blocks

        blocks = _extract_fenced_code_blocks("No code here.\n")
        assert blocks == []


class TestExtractClassifyKind:
    """Test claim kind classification from text."""

    def test_install_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Installation Guide") == "install"

    def test_config_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Configuration Options") == "config"

    def test_performance_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Performance Benchmarks") == "performance"

    def test_default_feature_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Some Random Heading") == "feature"

    def test_troubleshoot_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Common Error Messages") == "troubleshoot"

    def test_license_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("License Information") == "license"

    def test_api_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Class Reference") == "api"

    def test_integration_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Integration with Django") == "integration"

    def test_example_kind(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Usage Examples") == "example"


class TestPlanTitleGeneration:
    """Test title generation from slugs."""

    def test_index_slug_title(self) -> None:
        from launcher.workers.planner.plan import _generate_title

        assert _generate_title("_index", "landing") == "Overview"
        assert _generate_title("_index", "toc") == "Table of Contents"

    def test_hyphenated_slug(self) -> None:
        from launcher.workers.planner.plan import _generate_title

        title = _generate_title("how-to-open-a-file", "howto_article")
        assert title == "How to Open a File"

    def test_small_words_lowercase(self) -> None:
        from launcher.workers.planner.plan import _generate_title

        title = _generate_title("guide-for-the-api", "workflow_page")
        # "for" and "the" should be lowercase (not first/last)
        assert "for" in title.split()
        assert "the" in title.split()
        # First word should be capitalized
        assert title.startswith("Guide")


# ===================================================================
# CQ-08: Tests for Claim Extraction Quality & Quantity Overhaul
# ===================================================================


class TestIsVendoredExpanded:
    """CQ-01: Verify expanded vendored directory detection."""

    def test_plugin_dir_detected(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("Plugin/docling/README.md") is True

    def test_plugins_dir_detected(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("plugins/foo/bar.md") is True

    def test_submodules_dir_detected(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("submodules/lib/README.md") is True

    def test_existing_vendor_still_works(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("vendor/lib/foo.py") is True

    def test_non_vendored_passes(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("src/plugin_loader.py") is False

    def test_root_readme_not_vendored(self) -> None:
        from launcher.workers.understand.file_classifier import is_vendored

        assert is_vendored("README.md") is False


class TestScoreDocPath:
    """CQ-02: Verify relevance scoring."""

    def test_root_readme_highest(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("README.md") == 100

    def test_nested_readme(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("examples/README.md") == 70

    def test_root_doc(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("INSTALL.md") == 90

    def test_docs_dir(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("docs/api.md") == 80

    def test_example_doc(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("examples/demo/guide.md") == 60

    def test_other_doc(self) -> None:
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("tools/notes.md") == 40

    def test_ordering(self) -> None:
        """Root README > root doc > docs dir > nested readme > example > other."""
        from launcher.workers.understand.extract import _score_doc_path

        assert _score_doc_path("README.md") > _score_doc_path("INSTALL.md")
        assert _score_doc_path("INSTALL.md") > _score_doc_path("docs/api.md")
        assert _score_doc_path("docs/api.md") > _score_doc_path("sub/README.md")


class TestBuildDocContextsFiltering:
    """CQ-02: Verify _build_doc_contexts excludes vendored and changelog paths."""

    def test_excludes_vendored_paths(self, tmp_path: Path) -> None:
        from launcher.workers.understand.extract import _build_doc_contexts

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Project\nA real readme.\n")
        (repo / "vendor").mkdir()
        (repo / "vendor" / "lib.md").write_text("vendored content")
        (repo / "plugins").mkdir()
        (repo / "plugins" / "info.md").write_text("plugin content")

        repo_info = RepoInfo(
            file_tree=["README.md", "vendor/lib.md", "plugins/info.md"],
            doc_paths=["README.md", "vendor/lib.md", "plugins/info.md"],
            example_paths=[],
            readme_summary="A project",
        )

        contexts = _build_doc_contexts(repo, repo_info)
        paths = [c["path"] for c in contexts]
        assert "README.md" in paths
        assert "vendor/lib.md" not in paths
        assert "plugins/info.md" not in paths

    def test_excludes_changelog_files(self, tmp_path: Path) -> None:
        from launcher.workers.understand.extract import _build_doc_contexts

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Project\nA real readme.\n")
        (repo / "CHANGELOG.md").write_text("## 1.0.0\n- Initial release")

        repo_info = RepoInfo(
            file_tree=["README.md", "CHANGELOG.md"],
            doc_paths=["README.md", "CHANGELOG.md"],
            example_paths=[],
            readme_summary="A project",
        )

        contexts = _build_doc_contexts(repo, repo_info)
        paths = [c["path"] for c in contexts]
        assert "README.md" in paths
        assert "CHANGELOG.md" not in paths


class TestIsJunkClaim:
    """CQ-03: Verify junk claim filtering."""

    @pytest.mark.parametrize("text", [
        "short",                                    # too short
        "**Python**",                               # bold-only
        "pip install aspose-cells",                  # install command
        "New formula model (#2042)",                # PR reference
        "v2.5.0",                                   # version string
        "Merge pull request #123",                  # merge commit
        "import os",                                # code
        "from pathlib import Path",                 # code import
        "---",                                      # horizontal rule
        "![badge](https://img.shields.io/foo)",     # badge
    ])
    def test_rejects_junk(self, text: str) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim(text) is True

    @pytest.mark.parametrize("text", [
        "Aspose.Cells supports loading XLSX files via the Workbook class",
        "The library provides chart creation and pivot table manipulation",
        "Formula calculation engine supports built-in and custom formulas",
        "API offers Excel file creation, manipulation, conversion and rendering",
    ])
    def test_keeps_good_claims(self, text: str) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim(text) is False


class TestDeterministicExtractorTables:
    """CQ-04: Verify table row extraction produces claims."""

    def test_table_rows_produce_claims(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        doc_contexts = [
            {
                "path": "README.md",
                "content": textwrap.dedent("""\
                    # Supported Formats

                    | Format | Read | Write |
                    |--------|------|-------|
                    | XLSX spreadsheet format | Yes | Yes |
                    | CSV comma-separated values | Yes | Yes |
                    | PDF portable document format | No | Yes |
                """),
            }
        ]

        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        # The separator row (|---|---|---) should be skipped; data rows should produce claims
        texts = [c["text"] for c in claims]
        assert len(claims) >= 2
        # At least one claim should mention a format
        assert any("XLSX" in t or "CSV" in t or "PDF" in t for t in texts)


class TestDeterministicExtractorSectionKind:
    """CQ-04: Verify heading-to-kind mapping via _SECTION_KIND_MAP."""

    def test_supported_formats_gets_format_kind(
        self, cells_product: ProductIdentity
    ) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        doc_contexts = [
            {
                "path": "README.md",
                "content": textwrap.dedent("""\
                    # Supported Formats

                    - Read and write XLSX spreadsheet files natively
                    - Convert CSV files to Excel workbooks easily

                    # Installation

                    - Install the library using pip install aspose-cells
                """),
            }
        ]

        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        # Claims under "Supported Formats" should have kind="format"
        format_claims = [c for c in claims if c["kind"] == "format"]
        assert len(format_claims) >= 1

        # Claims under "Installation" should have kind="install"
        install_claims = [c for c in claims if c["kind"] == "install"]
        assert len(install_claims) >= 1


class TestJsonRepair:
    """CQ-05: Verify JSON repair."""

    def test_trailing_comma_array(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        result = _repair_json('[{"a": 1}, {"b": 2},]')
        assert _json.loads(result) == [{"a": 1}, {"b": 2}]

    def test_trailing_comma_object(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        result = _repair_json('{"a": 1, "b": 2,}')
        assert _json.loads(result) == {"a": 1, "b": 2}

    def test_js_comments_at_line_start(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        result = _repair_json('[\n// comment\n{"a": 1}\n]')
        assert _json.loads(result) == [{"a": 1}]

    def test_clean_json_unchanged(self) -> None:
        from launcher.workers.understand.extract import _repair_json

        clean = '[{"a": 1}]'
        assert _repair_json(clean) == clean


class TestParseClaimsJsonWithRepair:
    """CQ-05: Verify _parse_claims_json uses repair for malformed JSON."""

    def test_trailing_comma_repaired(self) -> None:
        from launcher.workers.understand.extract import _parse_claims_json

        malformed = '[{"text": "claim one", "kind": "feature"},]'
        result = _parse_claims_json(malformed, None)
        assert len(result) == 1
        assert result[0]["text"] == "claim one"

    def test_js_comment_repaired(self) -> None:
        from launcher.workers.understand.extract import _parse_claims_json

        malformed = '[\n// note about claims\n{"text": "claim A"}\n]'
        result = _parse_claims_json(malformed, None)
        assert len(result) == 1

    def test_clean_json_works(self) -> None:
        from launcher.workers.understand.extract import _parse_claims_json

        clean = '[{"text": "clean claim", "kind": "feature"}]'
        result = _parse_claims_json(clean, None)
        assert len(result) == 1


class TestValidateAndNormalizeMinQuality:
    """CQ-07: Verify min quality gate in _validate_and_normalize_claims."""

    def test_short_claims_filtered(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _validate_and_normalize_claims
        from launcher.models.product import ApiSurface

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Too short", "kind": "feature", "visibility": "public", "evidence": []},
            {"text": "This is a valid claim with enough length to pass the filter", "kind": "feature", "visibility": "public", "evidence": []},
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        texts = [c.text for c in result]
        assert "Too short" not in texts
        assert any("valid claim" in t for t in texts)

    def test_junk_claims_filtered(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _validate_and_normalize_claims
        from launcher.models.product import ApiSurface

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Merge pull request #456 from branch", "kind": "feature", "visibility": "public", "evidence": []},
            {"text": "Aspose.Cells provides chart rendering and data visualization", "kind": "feature", "visibility": "public", "evidence": []},
        ]

        result = _validate_and_normalize_claims(raw, cells_product, api)
        texts = [c.text for c in result]
        assert not any("Merge pull" in t for t in texts)
        assert any("chart rendering" in t for t in texts)


class TestPromptFileExists:
    """CQ-06: Verify improved claim_extractor prompt file exists."""

    def test_claim_extractor_prompt_exists(self) -> None:
        prompt_path = Path(__file__).resolve().parents[3] / "src" / "launcher" / "prompts" / "claim_extractor.txt"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"
        content = prompt_path.read_text(encoding="utf-8")
        assert len(content) > 100, "Prompt file appears too short"


# ===================================================================
# HQ-01: _repair_json URL preservation + emoji + backtick fixes
# ===================================================================


class TestRepairJsonUrlPreservation:
    """HQ-01/G1: _repair_json must not corrupt URLs in JSON strings."""

    def test_url_in_json_preserved(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        raw = '{"url": "https://example.com/path", "name": "test"}'
        result = _repair_json(raw)
        parsed = _json.loads(result)
        assert parsed["url"] == "https://example.com/path"

    def test_multiple_urls_preserved(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        raw = '[{"a": "https://foo.com/bar"}, {"b": "http://baz.org/qux"}]'
        result = _repair_json(raw)
        parsed = _json.loads(result)
        assert parsed[0]["a"] == "https://foo.com/bar"
        assert parsed[1]["b"] == "http://baz.org/qux"

    def test_line_start_comment_removed(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        raw = '[\n// this is a comment\n{"a": 1}\n]'
        result = _repair_json(raw)
        parsed = _json.loads(result)
        assert parsed == [{"a": 1}]

    def test_indented_comment_removed(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        raw = '[\n  // indented comment\n  {"a": 1}\n]'
        result = _repair_json(raw)
        parsed = _json.loads(result)
        assert parsed == [{"a": 1}]

    def test_inline_url_not_corrupted_by_comment_removal(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        raw = '[{"url": "https://docs.aspose.com/cells/python"}]'
        result = _repair_json(raw)
        parsed = _json.loads(result)
        assert parsed[0]["url"] == "https://docs.aspose.com/cells/python"


class TestIsJunkClaimEmojiFixed:
    """HQ-01/G2: Emoji detection uses unicodedata, not ord() threshold."""

    def test_emoji_leading_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim("\u2728 Run the server and check output")  # sparkles

    def test_umlaut_not_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        # German umlaut should NOT be detected as emoji
        assert not _is_junk_claim("Konig-class battleship documentation and specs")

    def test_cjk_not_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        # Must be >= 20 chars to avoid the min-length filter
        assert not _is_junk_claim("\u4e2d\u6587\u6587\u6863\u5904\u7406\u548c\u6570\u636e\u5206\u6790\u529f\u80fd\u652f\u6301\u7cfb\u7edf\u6a21\u5757\u7684\u4f7f\u7528")  # Chinese text 22 chars

    def test_accented_latin_not_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert not _is_junk_claim("\u00c9l\u00e8ve documentation processor for advanced users")

    def test_checkmark_emoji_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim("\u2705 All tests passed successfully now")

    def test_ascii_text_not_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert not _is_junk_claim("Aspose.Cells for Python via .NET")


class TestIsJunkClaimBacktick:
    """HQ-01/G3: Backtick-wrapped install commands are rejected."""

    def test_backtick_pip_install(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim("`pip install aspose-cells-python`")

    def test_backtick_npm_install(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim("`npm install some-package-name`")

    def test_bare_pip_install_still_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert _is_junk_claim("pip install aspose-cells-python")

    def test_non_command_with_backtick_not_rejected(self) -> None:
        from launcher.workers.understand.extract import _is_junk_claim

        assert not _is_junk_claim("`Workbook` class provides spreadsheet manipulation features")


# ===================================================================
# HQ-02: Product-relevance filtering (_is_off_topic)
# ===================================================================


class TestIsOffTopic:
    """HQ-02/G4: Third-party claims without product mentions are off-topic."""

    def test_sklearn_only_is_off_topic(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        assert _is_off_topic("Scikit-learn is a machine learning library", cells_product)

    def test_sklearn_with_product_not_off_topic(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        assert not _is_off_topic("Using Scikit-learn with Aspose.Cells for reports", cells_product)

    def test_no_third_party_not_off_topic(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        assert not _is_off_topic("The library supports XLSX format", cells_product)

    def test_django_only_is_off_topic(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        assert _is_off_topic("Django provides web framework capabilities for Python", cells_product)

    def test_pandas_with_cells_not_off_topic(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        assert not _is_off_topic("Convert pandas DataFrame to Excel using Aspose Cells", cells_product)

    def test_product_keywords_derived_from_identity(self) -> None:
        from launcher.workers.understand.extract import _is_off_topic

        custom_product = ProductIdentity(
            family="note",
            platform="python",
            display_name="Aspose.Note FOSS for Python",
            canonical_import="aspose_note_foss",
            repo_url="https://github.com/aspose/aspose-note-foss-python",
        )
        # Should not be off-topic because "note" is a product keyword
        assert not _is_off_topic("Note file format conversion capabilities", custom_product)

    def test_off_topic_claim_gets_internal_visibility(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _validate_and_normalize_claims

        api = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        raw = [
            {"text": "Scikit-learn is a powerful machine learning library for Python", "kind": "feature", "visibility": "public", "evidence": []},
            {"text": "Aspose.Cells provides comprehensive spreadsheet manipulation", "kind": "feature", "visibility": "public", "evidence": []},
        ]
        result = _validate_and_normalize_claims(raw, cells_product, api)
        # The sklearn claim should be internal, the product claim should be public
        sklearn_claims = [c for c in result if "scikit" in c.text.lower() or "machine learning" in c.text.lower()]
        product_claims = [c for c in result if "spreadsheet" in c.text.lower()]
        if sklearn_claims:
            assert all(c.visibility == "internal" for c in sklearn_claims)
        assert all(c.visibility == "public" for c in product_claims)


# ===================================================================
# HQ-03: Code fence tracking tests
# ===================================================================


class TestCodeFenceTracking:
    """HQ-03/G5: Content inside code fences must NOT be extracted."""

    def test_code_inside_fences_skipped(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        md = textwrap.dedent("""\
            # Features
            - Real feature claim about spreadsheet processing
            ```python
            - This bullet inside code should NOT be a claim
            worksheet = workbook.worksheets[0]
            ```
            - Another real feature about data export
        """)
        doc_contexts = [{"path": "README.md", "content": md}]
        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        texts = [c["text"] for c in claims]
        assert any("spreadsheet" in t for t in texts)
        assert any("data export" in t for t in texts)
        assert not any("inside code" in t for t in texts)
        assert not any("worksheet" in t for t in texts)

    def test_content_outside_fences_kept(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        md = textwrap.dedent("""\
            # Usage
            - Before the code fence this is real content
            ```
            some code here
            ```
            - After the code fence this is also real content
        """)
        doc_contexts = [{"path": "README.md", "content": md}]
        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        texts = [c["text"] for c in claims]
        assert any("Before the code fence" in t for t in texts)
        assert any("After the code fence" in t for t in texts)

    def test_nested_fences_stay_in_fence_mode(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        md = textwrap.dedent("""\
            # Features
            - Real claim about file format support
            ```python
            code block line one
            ```
            ```javascript
            another code block line two
            ```
            - Another real claim about conversion
        """)
        doc_contexts = [{"path": "README.md", "content": md}]
        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        texts = [c["text"] for c in claims]
        assert any("file format" in t for t in texts)
        assert any("conversion" in t for t in texts)
        assert not any("code block" in t for t in texts)

    def test_mismatched_fence_blocks_remaining(self, cells_product: ProductIdentity) -> None:
        from launcher.workers.understand.extract import _extract_claims_deterministic

        md = textwrap.dedent("""\
            # Features
            - Claim before mismatched fence here
            ```python
            This is inside a never-closed fence
            - This bullet should not appear as claim
        """)
        doc_contexts = [{"path": "README.md", "content": md}]
        claims = _extract_claims_deterministic(doc_contexts, cells_product)
        texts = [c["text"] for c in claims]
        assert any("before mismatched" in t for t in texts)
        assert not any("should not appear" in t for t in texts)


# ===================================================================
# HQ-03: JSON repair with real error patterns
# ===================================================================


class TestParseClaimsJsonRealErrors:
    """HQ-03/G6: JSON repair handles real pilot error patterns."""

    def test_trailing_comma_real_pattern(self) -> None:
        from launcher.workers.understand.extract import _parse_claims_json

        # Pattern from actual pilot: trailing comma before ]
        malformed = '[{"text": "claim one", "kind": "feature"}, {"text": "claim two", "kind": "api"},]'
        result = _parse_claims_json(malformed, None)
        assert len(result) == 2

    def test_json_with_url_preserved_after_repair(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _parse_claims_json

        # JSON containing URLs should survive repair
        with_url = '[{"text": "See https://docs.aspose.com/cells for docs", "kind": "feature"}]'
        result = _parse_claims_json(with_url, None)
        assert len(result) == 1
        assert "https://docs.aspose.com/cells" in result[0]["text"]

    def test_js_comments_in_json_repaired(self) -> None:
        from launcher.workers.understand.extract import _parse_claims_json

        malformed = '[\n// First claim\n{"text": "claim A", "kind": "feature"}\n]'
        result = _parse_claims_json(malformed, None)
        assert len(result) == 1

    def test_double_repair_idempotent(self) -> None:
        import json as _json
        from launcher.workers.understand.extract import _repair_json

        clean = '[{"a": 1, "url": "https://example.com"}]'
        once = _repair_json(clean)
        twice = _repair_json(once)
        assert _json.loads(once) == _json.loads(twice)


# ===================================================================
# HQ-04: Merged _classify_kind_from_text
# ===================================================================


class TestClassifyKindMerged:
    """HQ-04/G8: _classify_kind_from_text handles exact headings + keyword fallback."""

    def test_exact_heading_match(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("Supported Formats") == "format"
        assert _classify_kind_from_text("Key Features") == "feature"
        assert _classify_kind_from_text("Installation") == "install"
        assert _classify_kind_from_text("API Reference") == "api"

    def test_keyword_fallback(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("How to install the library") == "install"
        assert _classify_kind_from_text("Performance benchmarks") == "performance"

    def test_default_to_feature(self) -> None:
        from launcher.workers.understand.extract import _classify_kind_from_text

        assert _classify_kind_from_text("About This Project") == "feature"


# ===================================================================
# TS-05: Allowlist tests for HC-01 (TreeSitter export extraction)
# ===================================================================


class TestAllowlistPython:
    """HC-01: Python repos must use __init__.py, not TreeSitter."""

    def test_allowlist_python_uses_init_not_treesitter(self, tmp_path):
        """Python repo with __init__.py → uses __all__, returns early."""
        from launcher.workers.understand.extract import _build_import_allowlist

        pkg = tmp_path / "aspose_cells"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__all__ = ["Workbook", "Worksheet"]')

        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="python",
            canonical_import="aspose.cells",
            repo_url="https://example.com/cells",
        )
        result = _build_import_allowlist(tmp_path, "aspose_cells", product)
        assert "aspose_cells.Workbook" in result
        assert "aspose_cells.Worksheet" in result

    def test_allowlist_empty_lang_tag_python_repo(self, tmp_path):
        """Python repo with empty lang_tag still uses __init__.py path."""
        from launcher.workers.understand.extract import _build_import_allowlist

        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__all__ = ["MyClass"]')

        product = ProductIdentity(
            display_name="MyLib",
            family="cells",
            platform="python",
            canonical_import="mylib",
            repo_url="https://example.com/mylib",
        )
        # Even with no lang_tag, Python __init__.py must be used
        result = _build_import_allowlist(tmp_path, "mylib", product)
        assert any("MyClass" in name for name in result)


class TestAllowlistTreeSitter:
    """HC-01: Non-Python repos use TreeSitter for export extraction."""

    def test_allowlist_java_uses_treesitter_exports(self, tmp_path):
        """Java repo → TreeSitter extracts public class names."""
        from launcher.workers.understand.extract import _build_import_allowlist

        pkg = tmp_path / "src"
        pkg.mkdir()
        (pkg / "Workbook.java").write_text(
            "package com.aspose.cells;\npublic class Workbook {\n"
            "    public void save() {}\n}\n"
        )

        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="java",
            canonical_import="com.aspose.cells",
            repo_url="https://example.com/cells",
        )
        result = _build_import_allowlist(tmp_path, "src", product)
        assert "Workbook" in result

    def test_allowlist_csharp_uses_treesitter_exports(self, tmp_path):
        """C# repo → TreeSitter extracts public class names."""
        from launcher.workers.understand.extract import _build_import_allowlist

        pkg = tmp_path / "src"
        pkg.mkdir()
        (pkg / "Document.cs").write_text(
            "namespace Aspose.Note {\n"
            "    public class Document {\n"
            "        public void Save() {}\n"
            "    }\n}\n"
        )

        product = ProductIdentity(
            display_name="Aspose.Note",
            family="note",
            platform="csharp",
            canonical_import="Aspose.Note",
            repo_url="https://example.com/note",
        )
        result = _build_import_allowlist(tmp_path, "src", product)
        assert "Document" in result

    def test_allowlist_fallback_to_regex_when_treesitter_unavailable(self, tmp_path, monkeypatch):
        """When TreeSitter is unavailable, regex fallback extracts Java package."""
        from launcher.workers.understand.extract import _build_import_allowlist

        pkg = tmp_path / "src"
        pkg.mkdir()
        (pkg / "Workbook.java").write_text("package com.aspose.cells;\npublic class Workbook {}\n")

        product = ProductIdentity(
            display_name="Aspose.Cells",
            family="cells",
            platform="java",
            canonical_import="com.aspose.cells",
            repo_url="https://example.com/cells",
        )

        # Make ts_analyzer import fail inside the function
        import sys
        monkeypatch.delitem(sys.modules, "launcher.shared.ts_analyzer", raising=False)
        original_import = __import__
        def _mock_import(name, *args, **kwargs):
            if "ts_analyzer" in name:
                raise ImportError("mocked")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)
        result = _build_import_allowlist(tmp_path, "src", product)
        assert "com.aspose.cells" in result


# ---------------------------------------------------------------------------
# BT-05: _extract_api_surface api_identifiers tests
# ---------------------------------------------------------------------------


class TestExtractApiSurfaceIdentifiers:
    """BT-05: Verify api_identifiers collection in _extract_api_surface."""

    def test_class_methods_properties_collected(self, tmp_path, monkeypatch):
        """Classes, methods, and properties should all appear in api_identifiers."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com",
        )

        # Create a Python file with a class
        src = tmp_path / "src" / "workbook.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "class Workbook:\n"
            "    @property\n"
            "    def active_sheet(self): pass\n"
            "    def save(self, path): pass\n"
            "    def _internal(self): pass\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "__init__.py").touch()

        result = _extract_api_surface(tmp_path, product)
        ids = set(result.api_identifiers)
        assert "Workbook" in ids
        assert "save" in ids
        assert "active_sheet" in ids
        # Private methods excluded
        assert "_internal" not in ids

    def test_private_methods_excluded(self, tmp_path):
        """Methods starting with _ should not appear in api_identifiers."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com",
        )

        src = tmp_path / "src" / "hidden.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "class _PrivateClass:\n"
            "    def _helper(self): pass\n"
            "    def __init__(self): pass\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "__init__.py").touch()

        result = _extract_api_surface(tmp_path, product)
        ids = set(result.api_identifiers)
        assert "_PrivateClass" not in ids
        assert "_helper" not in ids
        assert "__init__" not in ids

    def test_empty_repo_returns_empty_identifiers(self, tmp_path):
        """Empty repo should produce empty api_identifiers."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com",
        )

        result = _extract_api_surface(tmp_path, product)
        assert result.api_identifiers == []

    def test_identifiers_capped_at_500(self, tmp_path):
        """More than 500 unique identifiers should be capped."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com",
        )

        # Create a file with many classes
        lines = []
        for i in range(510):
            lines.append(f"class Cls{i:04d}:\n    pass\n")
        src = tmp_path / "src" / "many.py"
        src.parent.mkdir(parents=True)
        src.write_text("\n".join(lines), encoding="utf-8")
        (tmp_path / "src" / "__init__.py").touch()

        result = _extract_api_surface(tmp_path, product)
        assert len(result.api_identifiers) <= 500

    def test_backward_compat_missing_field(self):
        """ApiSurface created without api_identifiers should default to []."""
        surface = ApiSurface(
            public_classes=["Workbook"],
            import_allowlist=["aspose_cells_foss"],
            confidence="high",
        )
        assert surface.api_identifiers == []

    def test_deduplication(self, tmp_path):
        """Duplicate identifiers across files should be deduplicated."""
        from launcher.workers.understand.extract import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
            repo_url="https://example.com",
        )

        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").touch()
        # Two files, both define Workbook
        (src_dir / "a.py").write_text("class Workbook:\n    def save(self): pass\n", encoding="utf-8")
        (src_dir / "b.py").write_text("class Workbook:\n    def save(self): pass\n", encoding="utf-8")

        result = _extract_api_surface(tmp_path, product)
        # Each identifier appears at most once
        assert len(result.api_identifiers) == len(set(result.api_identifiers))


# ===================================================================
# TC-HYBRID-03: Format matrix extraction
# ===================================================================


class TestFormatMatrix:
    """Tests for extract_format_matrix()."""

    def test_extract_format_matrix_from_test_files(self, tmp_path):
        """FormatRecord populated from test files with FileFormat.OBJ patterns."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_save.py").write_text(
            "scene.save('out.obj', FileFormat.OBJ)  # save to file\n"
        )
        (test_dir / "test_load.py").write_text(
            "scene = Scene.from_file('input.fbx', FileFormat.FBX)  # load\n"
        )
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "OBJ" in names
        assert "FBX" in names

    def test_can_export_false_when_only_load_context(self, tmp_path):
        """FormatRecord.can_export=False when format only appears in load context."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_load_only.py").write_text(
            "scene = Scene.from_file('input.obj', FileFormat.OBJ)  # load only\n"
        )
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        obj = next((r for r in result if r.name == "OBJ"), None)
        assert obj is not None
        assert obj.can_import is True
        assert obj.can_export is False

    def test_format_matrix_empty_on_no_test_files(self, tmp_path):
        """Returns empty list when no test files or README exist."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        assert result == []

    def test_format_record_test_count(self, tmp_path):
        """test_count reflects number of test file references."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._deterministic import extract_format_matrix

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_a.py").write_text("scene.save(FileFormat.FBX)  # save\n")
        (test_dir / "test_b.py").write_text("scene.save(FileFormat.FBX)  # save\n")
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        fbx = next((r for r in result if r.name == "FBX"), None)
        assert fbx is not None
        assert fbx.test_count == 2


# ===================================================================
# TC-HYBRID-02: Typed API Surface
# ===================================================================


class TestTypedApiSurface:
    def test_typed_methods_populated_from_method_details(self, tmp_path):
        """ClassBrief.typed_methods populated when analyze_file_safe returns method_details."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Test", canonical_import="mylib",
            repo_url="file://" + str(tmp_path),
        )
        # Package name must not start with "test" — _find_source_files filters those out
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text(
            'class Widget:\n'
            '    """A widget."""\n'
            '    def save(self, path: str) -> bool:\n'
            '        """Save widget."""\n'
            '        return True\n'
        )
        result = _extract_api_surface(tmp_path, product)
        assert len(result.class_briefs) > 0
        brief = next((b for b in result.class_briefs if b.name == "Widget"), None)
        assert brief is not None
        assert "save" in brief.methods
        # typed_methods should also be populated
        assert any(m.name == "save" for m in brief.typed_methods)
        save_sig = next(m for m in brief.typed_methods if m.name == "save")
        assert save_sig.return_type == "bool"

    def test_typed_methods_param_types(self, tmp_path):
        """MethodSignature.parameters populated with type annotations."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Test", canonical_import="mylib",
            repo_url="file://" + str(tmp_path),
        )
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text(
            'class Renderer:\n'
            '    def render(self, path: str, quality: int) -> None:\n'
            '        pass\n'
        )
        result = _extract_api_surface(tmp_path, product)
        brief = next((b for b in result.class_briefs if b.name == "Renderer"), None)
        assert brief is not None
        render_sig = next((m for m in brief.typed_methods if m.name == "render"), None)
        assert render_sig is not None
        param_names = [p.name for p in render_sig.parameters]
        assert "path" in param_names
        assert "quality" in param_names
        path_param = next(p for p in render_sig.parameters if p.name == "path")
        assert path_param.type_annotation == "str"

    def test_backward_compat_methods_list_still_populated(self, tmp_path):
        """ClassBrief.methods (name list) still populated — backward compat."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Test", canonical_import="mylib",
            repo_url="file://" + str(tmp_path),
        )
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "grid.py").write_text(
            'class Grid:\n'
            '    def render(self): pass\n'
            '    def clear(self): pass\n'
        )
        result = _extract_api_surface(tmp_path, product)
        brief = next((b for b in result.class_briefs if b.name == "Grid"), None)
        assert brief is not None
        assert "render" in brief.methods
        assert "clear" in brief.methods

    def test_enum_class_detected(self, tmp_path):
        """Enum classes are detected and reported in ApiSurface.enums."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Test", canonical_import="mylib",
            repo_url="file://" + str(tmp_path),
        )
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "formats.py").write_text(
            'from enum import Enum\n'
            'class FileFormat(Enum):\n'
            '    """Supported file formats."""\n'
            '    OBJ = 1\n'
            '    FBX = 2\n'
            '    GLTF = 3\n'
        )
        result = _extract_api_surface(tmp_path, product)
        assert len(result.enums) > 0
        enum_rec = next((e for e in result.enums if e.name == "FileFormat"), None)
        assert enum_rec is not None
        member_names = [m.name for m in enum_rec.members]
        assert "OBJ" in member_names
        assert "FBX" in member_names

    def test_typed_properties_populated(self, tmp_path):
        """ClassBrief.typed_properties populated from @property methods."""
        from launcher.models.product import ProductIdentity
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        product = ProductIdentity(
            family="cells", platform="python",
            display_name="Test", canonical_import="mylib",
            repo_url="file://" + str(tmp_path),
        )
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "node.py").write_text(
            'class Node:\n'
            '    @property\n'
            '    def width(self) -> int:\n'
            '        """Width in pixels."""\n'
            '        return self._w\n'
        )
        result = _extract_api_surface(tmp_path, product)
        brief = next((b for b in result.class_briefs if b.name == "Node"), None)
        assert brief is not None
        assert "width" in brief.properties
        # typed_properties should also be populated
        prop_rec = next((p for p in brief.typed_properties if p.name == "width"), None)
        assert prop_rec is not None
        assert prop_rec.type_annotation == "int"
        assert prop_rec.is_readonly is True


# ===================================================================
# TC-HYBRID-04: InstallRecipe extraction
# ===================================================================


class TestInstallRecipe:
    """Unit tests for extract_install_recipe() and InstallRecipe model."""

    def test_extract_from_pyproject_toml(self, tmp_path):
        """extract_install_recipe returns correct pip_command from pyproject.toml."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-3d-foss"\nversion = "1.2.0"\n'
        )
        product = ProductIdentity(
            family="3d",
            platform="python",
            display_name="Aspose.3D",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert recipe.package_name == "aspose-3d-foss"
        assert "aspose-3d-foss" in recipe.pip_command
        assert recipe.source_file == "pyproject.toml"

    def test_fallback_to_canonical_import(self, tmp_path):
        """extract_install_recipe falls back to canonical_import when no config files."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert "aspose-cells-foss" in recipe.pip_command
        assert recipe.source_file == "derived"

    def test_none_on_no_canonical_import(self, tmp_path):
        """Returns None when no config files and no canonical_import."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        product = ProductIdentity(
            family="unknown",
            platform="python",
            display_name="Unknown",
            canonical_import="",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is None

    def test_extract_from_setup_cfg(self, tmp_path):
        """extract_install_recipe parses setup.cfg when no pyproject.toml."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        (tmp_path / "setup.cfg").write_text(
            "[metadata]\nname = aspose-words-foss\nversion = 2.0.0\n"
        )
        product = ProductIdentity(
            family="words",
            platform="python",
            display_name="Aspose.Words",
            canonical_import="aspose_words_foss",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert recipe.package_name == "aspose-words-foss"
        assert recipe.source_file == "setup.cfg"
        assert "aspose-words-foss" in recipe.pip_command

    def test_install_recipe_model_defaults(self):
        """InstallRecipe fields all default to empty string (no breaking changes)."""
        from launcher.models.understanding import InstallRecipe

        recipe = InstallRecipe()
        assert recipe.pip_command == ""
        assert recipe.package_name == ""
        assert recipe.version_constraint == ""
        assert recipe.verification_code == ""
        assert recipe.source_file == ""

    def test_product_evidence_install_recipe_defaults_to_none(self):
        """ProductEvidence.install_recipe defaults to None (backwards compat)."""
        from launcher.models.understanding import ProductEvidence

        evidence = ProductEvidence()
        assert evidence.install_recipe is None

    def test_version_constraint_appended_to_pip_command(self, tmp_path):
        """When version is found, pip command includes version constraint."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-pdf-foss"\nversion = "3.5.1"\n'
        )
        product = ProductIdentity(
            family="pdf",
            platform="python",
            display_name="Aspose.PDF",
            canonical_import="aspose_pdf_foss",
            repo_url="file://" + str(tmp_path),
        )
        recipe = extract_install_recipe(tmp_path, product)
        assert recipe is not None
        assert ">=3.5.1" in recipe.pip_command
        assert recipe.version_constraint == ">=3.5.1"


# ---------------------------------------------------------------------------
# Phase 1 Regression Tests (TC-4002 / humming-greeting-kay)
# ---------------------------------------------------------------------------


class TestPhase1LimitationModel:
    """TC-4002: LimitationEntry model serialization."""

    def test_limitation_roundtrip(self):
        from launcher.models.understanding import LimitationEntry
        lim = LimitationEntry(
            feature="OBJ export",
            constraint="not supported",
            status="unsupported",
            source_file="src/formats.py",
            source_line=42,
            confidence="ast_verified",
        )
        data = lim.model_dump()
        assert data["feature"] == "OBJ export"
        assert data["status"] == "unsupported"
        restored = LimitationEntry.model_validate(data)
        assert restored.feature == lim.feature


class TestPhase1WorkflowModel:
    """TC-4002: WorkflowExample model serialization."""

    def test_workflow_roundtrip(self):
        from launcher.models.understanding import WorkflowExample
        wf = WorkflowExample(
            name="test_convert",
            title="Convert FBX to GLTF",
            code="scene.save('out.gltf')",
            steps=["open", "save"],
            language="python",
            source_file="tests/test_convert.py",
            source_lines=(10, 20),
        )
        data = wf.model_dump()
        assert data["name"] == "test_convert"
        assert data["steps"] == ["open", "save"]
        restored = WorkflowExample.model_validate(data)
        assert restored.source_lines == (10, 20)


class TestPhase1ProductEvidenceWithNewFields:
    """TC-4002: ProductEvidence now has limitations and workflow_examples."""

    def test_product_evidence_defaults(self):
        from launcher.models.understanding import ProductEvidence
        pe = ProductEvidence()
        assert pe.limitations == []
        assert pe.workflow_examples == []

    def test_product_evidence_with_limitations(self):
        from launcher.models.understanding import ProductEvidence, LimitationEntry
        pe = ProductEvidence(
            limitations=[LimitationEntry(feature="async", constraint="not supported")],
        )
        assert len(pe.limitations) == 1
        data = pe.model_dump()
        assert len(data["limitations"]) == 1


class TestPhase1ExtractLimitations:
    """TC-4002: extract_limitations() finds limitation markers."""

    def test_finds_not_supported_in_docs(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_limitations
        from launcher.models.understanding import RepoInfo

        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        (doc_dir / "limitations.md").write_text(
            "# Limitations\n\nOBJ export is not supported in version 1.0\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(doc_paths=["docs/limitations.md"])
        results = extract_limitations(tmp_path, repo_info)
        assert len(results) >= 1
        assert any("not supported" in l.constraint.lower() for l in results)

    def test_finds_not_implemented_in_source(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_limitations
        from launcher.models.understanding import RepoInfo

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "api.py").write_text(
            "def export_obj():\n    raise NotImplementedError('OBJ export')\n",
            encoding="utf-8",
        )
        repo_info = RepoInfo(source_paths=["src/api.py"])
        results = extract_limitations(tmp_path, repo_info)
        assert len(results) >= 1
        assert any(l.status == "unsupported" for l in results)


class TestPhase1ExtractWorkflows:
    """TC-4002: extract_workflow_examples() extracts test functions."""

    def test_extracts_test_with_api_refs(self, tmp_path):
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        from launcher.models.understanding import RepoInfo
        from launcher.models.product import ApiSurface, ClassBrief

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_scene.py").write_text(textwrap.dedent("""\
            def test_load_and_save():
                \"\"\"Load a scene and save it.\"\"\"
                scene = Scene()
                scene.open("input.obj")
                scene.save("output.gltf")
                assert scene is not None
        """), encoding="utf-8")

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene", docstring_snippet="3D scene")],
            import_allowlist=[],
            confidence="high",
        )
        repo_info = RepoInfo(test_paths=["tests/test_scene.py"])
        results = extract_workflow_examples(tmp_path, repo_info, surface)
        assert len(results) >= 1
        assert results[0].name == "test_load_and_save"


class TestPhase1EvidenceContext:
    """TC-4002: _build_evidence_context() assembles structured block."""

    def test_builds_format_matrix_block(self):
        from launcher.workers.understand.extract._entry import _build_evidence_context
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=True, can_export=False),
                FormatRecord(name="FBX", can_import=True, can_export=True),
            ],
        )
        ctx = _build_evidence_context(surface, surface.format_matrix, [], None)
        assert "SOURCE-VERIFIED FACTS" in ctx
        assert "OBJ" in ctx
        assert "| No |" in ctx  # OBJ can_export=False

    def test_respects_char_budget(self):
        from launcher.workers.understand.extract._entry import _build_evidence_context
        from launcher.models.product import ApiSurface

        surface = ApiSurface(
            public_classes=[], class_briefs=[], import_allowlist=[], confidence="low",
        )
        ctx = _build_evidence_context(surface, [], [], None, max_chars=100)
        assert len(ctx) <= 100

    def test_includes_limitations(self):
        from launcher.workers.understand.extract._entry import _build_evidence_context
        from launcher.models.product import ApiSurface
        from launcher.models.understanding import LimitationEntry

        surface = ApiSurface(
            public_classes=[], class_briefs=[], import_allowlist=[], confidence="low",
        )
        lims = [LimitationEntry(feature="OBJ export", constraint="not supported", source_file="api.py")]
        ctx = _build_evidence_context(surface, [], lims, None)
        assert "OBJ export" in ctx
        assert "not supported" in ctx


class TestPhase1ContradictionResolver:
    """TC-4002: resolve_contradictions() downgrades conflicting claims."""

    def test_downgrades_format_export_contradiction(self):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions
        from launcher.models.claims import Claim
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[], class_briefs=[], import_allowlist=[],
            confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=True, can_export=False),
            ],
        )
        claims = [
            Claim(claim_id="CLM-001", text="You can export OBJ files easily", kind="format"),
        ]
        resolved, log = resolve_contradictions(claims, surface)
        assert resolved[0].visibility == "internal"
        assert len(log) == 1
        assert log[0]["type"] == "format_capability"

    def test_keeps_valid_claims(self):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions
        from launcher.models.claims import Claim
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[], class_briefs=[], import_allowlist=[],
            confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=True, can_export=True),
            ],
        )
        claims = [
            Claim(claim_id="CLM-002", text="You can export OBJ files", kind="format"),
        ]
        resolved, log = resolve_contradictions(claims, surface)
        assert resolved[0].visibility != "internal"
        assert len(log) == 0

    def test_empty_claims_no_error(self):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions
        resolved, log = resolve_contradictions([], None)
        assert resolved == []
        assert log == []


# ===================================================================
# Phase 2 regression tests — PlatformProfile + adapter infrastructure
# ===================================================================


class TestPhase2PlatformProfileModel:
    """TC-4003: PlatformProfile model serialization."""

    def test_platform_profile_roundtrip(self):
        from launcher.models.product import PlatformProfile
        profile = PlatformProfile(
            platform="python",
            lang_tag="python",
            import_tpl="aspose_{family}_foss",
            install_cmd="pip install aspose-{family}-foss",
            file_ext=".py",
            doc_comment="docstring",
            ast_parser="python_ast",
            package_name="aspose_3d_foss",
            import_path="aspose.threed",
            install_command="pip install aspose-3d-foss",
        )
        data = profile.model_dump()
        restored = PlatformProfile.model_validate(data)
        assert restored.platform == "python"
        assert restored.package_name == "aspose_3d_foss"
        assert restored.import_path == "aspose.threed"

    def test_platform_profile_defaults(self):
        from launcher.models.product import PlatformProfile
        profile = PlatformProfile(
            platform="test",
            lang_tag="test",
            import_tpl="",
            install_cmd="",
        )
        assert profile.file_ext == ".py"
        assert profile.doc_comment == "docstring"
        assert profile.ast_parser == "python_ast"
        assert profile.runtime_import_overrides == {}


class TestPhase2ResolvePlatformProfile:
    """TC-4003: resolve_platform_profile() for all platforms."""

    def test_resolve_python(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("python", "cells")
        assert p.platform == "python"
        assert p.lang_tag == "python"
        assert p.package_name == "aspose_cells_foss"
        assert p.install_command == "pip install aspose-cells-foss"
        assert p.file_ext == ".py"

    def test_resolve_python_3d_override(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("python", "3d")
        assert p.import_path == "aspose.threed"
        assert p.package_name == "aspose_3d_foss"

    def test_resolve_dotnet(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("dotnet", "cells")
        assert p.lang_tag == "csharp"
        assert p.file_ext == ".cs"
        assert p.ast_parser == "tree_sitter"

    def test_resolve_node(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("node", "cells")
        assert p.lang_tag == "javascript"
        assert p.file_ext == ".ts"

    def test_resolve_java(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("java", "cells")
        assert p.lang_tag == "java"
        assert p.file_ext == ".java"

    def test_resolve_unknown_falls_back(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        p = resolve_platform_profile("unknown_platform", "cells")
        # Should not crash — falls back to python defaults
        assert p.platform == "unknown_platform"
        assert p.lang_tag == "python"

    def test_resolve_with_families_yaml(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        config = {
            "platforms": {
                "rust": {
                    "lang_tag": "rust",
                    "import_tpl": "aspose-{family}",
                    "install_cmd": "cargo add aspose-{family}",
                    "file_ext": ".rs",
                    "ast_parser": "tree_sitter",
                }
            }
        }
        p = resolve_platform_profile("rust", "cells", families_config=config)
        assert p.lang_tag == "rust"
        assert p.file_ext == ".rs"
        assert p.install_command == "cargo add aspose-cells"


class TestPhase2AdapterRegistry:
    """TC-4003: Adapter registry and dispatch."""

    def test_python_adapter_resolves(self):
        from launcher.workers.understand.adapters import get_extractor
        e = get_extractor("python")
        assert e.platform_id == "python"
        assert ".py" in e.file_extensions

    def test_typescript_adapter_resolves(self):
        from launcher.workers.understand.adapters import get_extractor
        e = get_extractor("typescript")
        assert e.platform_id == "typescript"
        assert ".ts" in e.file_extensions

    def test_node_maps_to_typescript(self):
        from launcher.workers.understand.adapters import get_extractor
        e = get_extractor("node")
        assert e.platform_id == "typescript"

    def test_unknown_falls_back_to_generic(self):
        from launcher.workers.understand.adapters import get_extractor
        e = get_extractor("rust")
        assert e.platform_id == "generic"

    def test_python_detect_package_root(self, tmp_path):
        from launcher.workers.understand.adapters import get_extractor
        # Create src/mypackage/__init__.py
        pkg_dir = tmp_path / "src" / "mypackage"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")
        e = get_extractor("python")
        product = ProductIdentity(
            family="test", platform="python", display_name="Test",
            canonical_import="mypackage", repo_url="",
        )
        root = e.detect_package_root(tmp_path, product)
        assert root == "src/mypackage"

    def test_generic_detect_java_root(self, tmp_path):
        from launcher.workers.understand.adapters import get_extractor
        java_dir = tmp_path / "src" / "main" / "java"
        java_dir.mkdir(parents=True)
        e = get_extractor("java")
        product = ProductIdentity(
            family="test", platform="java", display_name="Test",
            canonical_import="com.test", repo_url="",
        )
        root = e.detect_package_root(tmp_path, product)
        assert root == "src/main/java"

    def test_old_facade_functions_still_work(self):
        from launcher.shared.platform_utils import get_lang_tag, get_install_cmd, format_import
        assert get_lang_tag("python") == "python"
        assert get_lang_tag("dotnet") == "csharp"
        assert "pip install" in get_install_cmd("python", "test-pkg")
        assert "import" in format_import("python", "cells")
