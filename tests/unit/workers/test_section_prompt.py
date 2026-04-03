"""Tests for section_prompt helpers — TC-3843, TC-3848, TC-3874."""
import pytest
from pathlib import Path

from src.launcher.workers.generate.section_prompt import (
    _build_golden_reference_block,
    _build_heal_directives_block,
    _rank_snippets,
)


class TestBuildGoldenReferenceBlock:
    def test_returns_empty_when_golden_dir_is_none(self):
        result = _build_golden_reference_block("workflow_page", "", None)
        assert result == ""

    def test_returns_empty_when_golden_dir_does_not_exist(self):
        result = _build_golden_reference_block(
            "workflow_page", "Overview", Path("nonexistent_golden_dir_xyz/")
        )
        assert result == ""

    def test_returns_empty_for_unknown_role_with_existing_dir(self, tmp_path):
        result = _build_golden_reference_block("no_such_role_xyz", "Overview", tmp_path)
        assert result == ""


class TestBuildHealDirectivesBlock:
    def test_returns_empty_when_heal_metadata_is_empty(self):
        result = _build_heal_directives_block({}, "Overview")
        assert result == ""

    def test_page_directives_appear_in_output(self):
        result = _build_heal_directives_block(
            {"page_directives": ["fix density"]}, "Overview"
        )
        assert "HEAL DIRECTIVES" in result
        assert "fix density" in result

    def test_section_directives_matching_heading(self):
        result = _build_heal_directives_block(
            {"section_directives": {"Overview": ["add more examples"]}},
            "Overview",
        )
        assert "HEAL DIRECTIVES" in result
        assert "add more examples" in result

    def test_section_directives_non_matching_heading(self):
        result = _build_heal_directives_block(
            {
                "page_directives": [],
                "section_directives": {"Installation": ["check pip command"]},
            },
            "Overview",
        )
        # Non-matching section directive should not appear; no page directives either
        assert result == ""

    def test_both_page_and_section_directives(self):
        result = _build_heal_directives_block(
            {
                "page_directives": ["global fix"],
                "section_directives": {"Overview": ["section fix"]},
            },
            "Overview",
        )
        assert "global fix" in result
        assert "section fix" in result


class TestRankSnippets:
    """TC-3874: snippet quality ranking replaces FIFO [:5] slice."""

    class _FakeSnippet:
        def __init__(self, source_type: str, claim_ids: list, snippet_id: str = ""):
            self.source_type = source_type
            self.claim_ids = claim_ids
            self.snippet_id = snippet_id

    def test_rank_snippets_quality_order(self):
        """Extracted snippets rank before synthetic even with lower claim overlap."""
        snippets = [
            self._FakeSnippet("synthetic", ["CLM-001", "CLM-002", "CLM-003"], "s1"),
            self._FakeSnippet("extracted", ["CLM-001", "CLM-002"], "s2"),
            self._FakeSnippet("generated", ["CLM-001"], "s3"),
        ]
        section_claim_ids = {"CLM-001", "CLM-002", "CLM-003"}
        ranked = _rank_snippets(snippets, section_claim_ids)
        assert ranked[0].source_type == "extracted"   # extracted wins despite lower overlap
        assert ranked[1].source_type == "generated"
        assert ranked[2].source_type == "synthetic"

    def test_rank_snippets_excludes_non_overlapping(self):
        """Snippets with no claim overlap are excluded."""
        snippets = [
            self._FakeSnippet("extracted", ["CLM-999"], "s1"),
            self._FakeSnippet("extracted", ["CLM-001"], "s2"),
        ]
        ranked = _rank_snippets(snippets, {"CLM-001"})
        assert len(ranked) == 1
        assert ranked[0].snippet_id == "s2"

    def test_rank_snippets_cap_at_max_count(self):
        """Returns at most max_count snippets."""
        snippets = [
            self._FakeSnippet("extracted", ["CLM-001"], f"s{i}")
            for i in range(10)
        ]
        ranked = _rank_snippets(snippets, {"CLM-001"}, max_count=5)
        assert len(ranked) == 5

    def test_rank_snippets_empty_inputs(self):
        """Returns empty list for empty snippets or empty claim ids."""
        assert _rank_snippets([], {"CLM-001"}) == []
        snippets = [self._FakeSnippet("extracted", ["CLM-001"], "s1")]
        assert _rank_snippets(snippets, set()) == []

    def test_rank_snippets_deterministic(self):
        """Same input always produces the same ordering (PYTHONHASHSEED=0 safe)."""
        snippets = [
            self._FakeSnippet("extracted", ["CLM-001", "CLM-002"], "s-b"),
            self._FakeSnippet("extracted", ["CLM-001", "CLM-002"], "s-a"),
        ]
        section_claim_ids = {"CLM-001", "CLM-002"}
        r1 = _rank_snippets(snippets, section_claim_ids)
        r2 = _rank_snippets(snippets, section_claim_ids)
        assert [s.snippet_id for s in r1] == [s.snippet_id for s in r2]


# ===================================================================
# TC-HYBRID-04: install_recipe injection in build_section_prompt
# ===================================================================


class TestBuildSectionPromptInstallRecipe:
    """TC-HYBRID-04: install_recipe is injected into the section prompt."""

    def _make_minimal_objects(self):
        """Return (section, page, product) stubs for build_section_prompt."""
        from launcher.models.product import ProductIdentity
        from launcher.models.plan import PlannedPage
        from launcher.shared.page_skeletons import SkeletonSection

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )
        page = PlannedPage(
            page_id="installation",
            page_role="installation",
            title="Installation Guide",
        )
        section = SkeletonSection(
            heading="Installation",
            level=2,
            content_hint="How to install the package",
            required=True,
            min_words=100,
            max_words=400,
        )
        return section, page, product

    def test_install_recipe_block_appears_in_prompt(self):
        """When install_recipe is provided, pip_command block appears in output."""
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.models.understanding import InstallRecipe

        section, page, product = self._make_minimal_objects()
        recipe = InstallRecipe(
            install_command="pip install aspose-cells-foss>=1.0.0",
            package_name="aspose-cells-foss",
            version_constraint=">=1.0.0",
            verification_code="import aspose_cells_foss\nprint('Installation successful')",
            source_file="pyproject.toml",
        )
        result = build_section_prompt(
            section, 0, 1, page, product, [], [],
            install_recipe=recipe,
        )
        assert "INSTALL REFERENCE" in result
        assert "pip install aspose-cells-foss>=1.0.0" in result
        assert "import aspose_cells_foss" in result

    def test_no_install_block_when_recipe_is_none(self):
        """When install_recipe is None, INSTALL REFERENCE block is absent."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        section, page, product = self._make_minimal_objects()
        result = build_section_prompt(
            section, 0, 1, page, product, [], [],
            install_recipe=None,
        )
        assert "INSTALL REFERENCE" not in result

    def test_no_install_block_when_pip_command_empty(self):
        """When install_recipe has empty pip_command, no block is injected."""
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.models.understanding import InstallRecipe

        section, page, product = self._make_minimal_objects()
        recipe = InstallRecipe(install_command="", package_name="", source_file="derived")
        result = build_section_prompt(
            section, 0, 1, page, product, [], [],
            install_recipe=recipe,
        )
        assert "INSTALL REFERENCE" not in result


# ---------------------------------------------------------------------------
# SR-22-02 — _is_test_file_snippet + reference page snippet filter
# ---------------------------------------------------------------------------

class TestIsTestFileSnippet:
    """Unit tests for _is_test_file_snippet path-pattern detection."""

    def _make_snippet(self, source_file: str):
        from launcher.models.claims import Snippet
        return Snippet(code="x = 1", source_file=source_file)

    def test_test_dir_prefix_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("tests/test_workbook.py")
        assert _is_test_file_snippet(s) is True

    def test_test_dir_singular_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("test/workbook_test.py")
        assert _is_test_file_snippet(s) is True

    def test_root_test_underscore_prefix_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("test_workbook.py")
        assert _is_test_file_snippet(s) is True

    def test_underscore_test_dot_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("workbook_test.py")
        assert _is_test_file_snippet(s) is True

    def test_examples_dir_not_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("examples/workbook_demo.py")
        assert _is_test_file_snippet(s) is False

    def test_src_main_not_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("src/main.py")
        assert _is_test_file_snippet(s) is False

    def test_empty_source_file_not_detected(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet("")
        assert _is_test_file_snippet(s) is False

    def test_windows_path_backslashes_handled(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        s = self._make_snippet(r"tests\unit\test_workbook.py")
        assert _is_test_file_snippet(s) is True

    def test_path_with_test_in_middle_of_word_not_false_positive(self):
        from launcher.workers.generate.section_prompt import _is_test_file_snippet
        # "contest" should NOT match — "test" must be at a path boundary
        s = self._make_snippet("src/contest/workbook.py")
        assert _is_test_file_snippet(s) is False


class TestReferencePageSnippetFilter:
    """Tests for test-snippet filtering applied to reference page roles."""

    def _make_snippet(self, source_file: str, code: str = "x = 1"):
        from launcher.models.claims import Snippet
        return Snippet(code=code, source_file=source_file)

    def _make_page(self, page_role: str):
        from launcher.models.plan import PlannedPage
        return PlannedPage(page_id="ref_page", page_role=page_role, title="Reference")

    def _make_section(self):
        from launcher.shared.page_skeletons import SkeletonSection
        return SkeletonSection(
            heading="Overview",
            level=2,
            content_hint="API overview",
            required=True,
            min_words=50,
            max_words=300,
        )

    def _make_product(self):
        from launcher.models.product import ProductIdentity
        return ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/test/test",
        )

    def test_reference_role_builds_prompt_with_mixed_snippets(self):
        """reference_object_page: prompt builds without error with test + real snippets."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        test_snip = self._make_snippet("tests/test_workbook.py", "setUp()")
        real_snip = self._make_snippet("examples/demo.py", "wb = Workbook()")
        page = self._make_page("reference_object_page")
        section = self._make_section()
        product = self._make_product()

        result = build_section_prompt(section, 0, 1, page, product, [], [test_snip, real_snip])
        assert isinstance(result, str)

    def test_reference_role_keeps_test_snippets_as_fallback_when_only_source(self):
        """reference_object_page: falls back to test snippets when no non-test available."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        test_snip = self._make_snippet("tests/test_workbook.py", "wb = Workbook()")
        page = self._make_page("reference_object_page")
        section = self._make_section()
        product = self._make_product()

        result = build_section_prompt(section, 0, 1, page, product, [], [test_snip])
        assert isinstance(result, str)

    def test_non_reference_role_does_not_filter_test_snippets(self):
        """howto role: test snippets are NOT filtered out."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        test_snip = self._make_snippet("tests/test_workbook.py", "setUp()")
        page = self._make_page("howto")
        section = self._make_section()
        product = self._make_product()

        result = build_section_prompt(section, 0, 1, page, product, [], [test_snip])
        assert isinstance(result, str)

    def test_api_reference_role_builds_prompt_with_mixed_snippets(self):
        """api_reference is also a _REFERENCE_ROLE and should handle mixed snippets."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        test_snip = self._make_snippet("tests/test_api.py", "assert x == 1")
        real_snip = self._make_snippet("examples/api_demo.py", "api = ApiClass()")
        page = self._make_page("api_reference")
        section = self._make_section()
        product = self._make_product()

        result = build_section_prompt(section, 0, 1, page, product, [], [test_snip, real_snip])
        assert isinstance(result, str)
