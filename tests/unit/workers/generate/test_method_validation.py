"""Tests for TC-3817: Post-LLM method name validation (Change F)."""

from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.page_ir import BlockIR, BlockType
from launcher.models.product import ProductIdentity


class TestValidateIdentifiers:
    """Change F: Strip backticked identifiers not in api_identifiers."""

    def test_known_identifiers_kept(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Use `Document` to load files with `load()`."),
        ]
        api_ids = {"Document", "load"}
        result = _validate_identifiers(blocks, api_ids)
        assert "`Document`" in result[0].content
        assert "`load()`" in result[0].content

    def test_unknown_identifiers_stripped(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Use `Document` and `export_pdf()` to process."),
        ]
        api_ids = {"Document"}
        result = _validate_identifiers(blocks, api_ids)
        assert "`Document`" in result[0].content
        # export_pdf should have backticks removed but text preserved
        assert "export_pdf()" in result[0].content
        assert "`export_pdf()`" not in result[0].content

    def test_code_blocks_not_modified(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.code, content="result = obj.fake_method()", language="python"),
        ]
        api_ids = {"Document"}
        result = _validate_identifiers(blocks, api_ids)
        assert result[0].content == "result = obj.fake_method()"

    def test_empty_api_identifiers(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Use `Document` to load."),
        ]
        result = _validate_identifiers(blocks, set())
        # All backticked identifiers stripped (Document not a builtin)
        assert "`Document`" not in result[0].content
        assert "Document" in result[0].content

    # AQ-04: Builtin identifier allowlist tests

    def test_builtin_str_preserved(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Use `str` to convert the value."),
        ]
        result = _validate_identifiers(blocks, set())
        assert "`str`" in result[0].content

    def test_builtin_path_preserved(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Pass a `Path` object to load."),
        ]
        result = _validate_identifiers(blocks, set())
        assert "`Path`" in result[0].content

    def test_builtin_none_preserved(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Returns `None` if not found."),
        ]
        result = _validate_identifiers(blocks, set())
        assert "`None`" in result[0].content

    def test_non_builtin_non_api_stripped(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(type=BlockType.paragraph, content="Call `FakeMethod()` to proceed."),
        ]
        result = _validate_identifiers(blocks, set())
        assert "`FakeMethod()`" not in result[0].content
        assert "FakeMethod()" in result[0].content

    def test_builtins_and_api_ids_both_preserved(self):
        from launcher.workers.generate.worker import _validate_identifiers

        blocks = [
            BlockIR(
                type=BlockType.paragraph,
                content="Use `Document` with `str` and `int` but not `export_pdf()`."),
        ]
        result = _validate_identifiers(blocks, {"Document"})
        assert "`Document`" in result[0].content
        assert "`str`" in result[0].content
        assert "`int`" in result[0].content
        assert "`export_pdf()`" not in result[0].content
        assert "export_pdf()" in result[0].content


# ===========================================================================
# GAP-11: _filter_api_surface simplified (AQ-05)
# ===========================================================================


def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="cells",
        platform="python",
        display_name="Aspose.Cells",
        canonical_import="aspose.cells",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


class TestFilterApiSurfaceSimplified:
    """GAP-11: _filter_api_surface no longer applies third-party prefix list."""

    def test_all_classes_kept_when_no_claims(self):
        """Without claims, all classes pass through (no third-party prefix filter)."""
        from launcher.workers.generate.worker import _filter_api_surface

        product = _make_product()
        result = _filter_api_surface(["Workbook", "DjangoHelper", "FlaskApp"], product, [])
        assert "Workbook" in result
        assert "DjangoHelper" in result
        assert "FlaskApp" in result

    def test_empty_input_returns_empty(self):
        """Empty public_classes returns empty list."""
        from launcher.workers.generate.worker import _filter_api_surface

        product = _make_product()
        result = _filter_api_surface([], product, [])
        assert result == []

    def test_family_match_always_kept(self):
        """Classes containing the family name are always kept."""
        from launcher.workers.generate.worker import _filter_api_surface

        product = _make_product(family="cells")
        result = _filter_api_surface(["CellsWorkbook", "OtherClass"], product, [])
        assert "CellsWorkbook" in result

    def test_claim_mentioned_class_kept(self):
        """A class mentioned in claims is kept regardless of name."""
        from launcher.workers.generate.worker import _filter_api_surface

        product = _make_product()
        claims = [Claim(claim_id="C1", text="Use Workbook to open spreadsheets.", kind="api", evidence=[])]
        result = _filter_api_surface(["Workbook", "OtherClass"], product, claims)
        assert "Workbook" in result
        assert "OtherClass" in result  # also kept (no filtering on non-match)
