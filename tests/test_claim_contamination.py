"""Tests for claim contamination filtering (TC-3782)."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.product import ProductIdentity
from launcher.workers.understand.extract import _filter_contaminated_claims
from launcher.workers.understand.file_classifier import is_vendored


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells FOSS for Python",
        canonical_import="aspose_cells_foss",
        repo_url="https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET",
    )


def _claim(claim_id: str, text: str, kind: str = "feature") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind)


# ── is_vendored tests ────────────────────────────────────────────────

class TestIsVendored:
    """Verify vendored path detection including integration directories."""

    def test_mainstream_framework_integration_django(self):
        assert is_vendored("Mainstream Framework Integration/Django/README.md")

    def test_mainstream_framework_integration_flask(self):
        assert is_vendored("Mainstream Framework Integration/Flask/ReadMe.md")

    def test_mainstream_framework_integration_scikit(self):
        assert is_vendored("Mainstream Framework Integration/Scikit-learn/ReadMe.md")

    def test_mainstream_framework_integration_tensorflow(self):
        assert is_vendored("Mainstream Framework Integration/TensorFlow/ReadMe.md")

    def test_plugin_docling(self):
        assert is_vendored("Plugin/docling/CHANGELOG.md")

    def test_plugin_markitdown(self):
        assert is_vendored("Plugin/markitdown-aspose-cells-plugin/tests/__init__.py")

    def test_example_not_vendored(self):
        assert not is_vendored("Example/ConvertToDataFrame.py")

    def test_readme_not_vendored(self):
        assert not is_vendored("README.md")

    def test_docs_not_vendored(self):
        assert not is_vendored("docs/getting-started.md")

    def test_src_not_vendored(self):
        assert not is_vendored("src/main.py")

    def test_case_insensitive(self):
        assert is_vendored("mainstream framework integration/django/readme.md")

    def test_backslash_path(self):
        assert is_vendored("Mainstream Framework Integration\\Django\\README.md")

    def test_vendor_dir(self):
        assert is_vendored("vendor/lib/module.py")

    def test_third_party_dir(self):
        assert is_vendored("third_party/some_lib/init.py")


# ── Contamination filter tests ───────────────────────────────────────

class TestFilterContaminatedClaims:
    """Verify claim contamination filter removes off-topic claims."""

    def test_removes_docling_claims(self, product):
        claims = [
            _claim("CLM-1", "fix single-formatted headings in docling"),
            _claim("CLM-2", "Aspose.Cells supports XLSX format"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1
        assert result[0].claim_id == "CLM-2"

    def test_removes_django_claims(self, product):
        claims = [
            _claim("CLM-1", "Run the Django development server"),
            _claim("CLM-2", "create Excel files programmatically"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1
        assert result[0].claim_id == "CLM-2"

    def test_removes_sklearn_claims(self, product):
        claims = [
            _claim("CLM-1", "Scikit-learn is an open-source Machine Learning library for Python"),
            _claim("CLM-2", "export spreadsheets to PDF"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1
        assert result[0].claim_id == "CLM-2"

    def test_keeps_product_with_framework(self, product):
        """Claims mentioning both product and third-party tech are kept."""
        claims = [
            _claim("CLM-1", "Use Django with Aspose.Cells to generate Excel reports"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1

    def test_keeps_clean_claims(self, product):
        claims = [
            _claim("CLM-1", "create, read, and modify Excel files programmatically"),
            _claim("CLM-2", "export to PDF and images"),
            _claim("CLM-3", "formula calculation engine"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 3

    def test_removes_changelog_entries(self, product):
        claims = [
            _claim("CLM-1", "HTML: Parse footer tag as a group (#2106)"),
            _claim("CLM-2", "support new mlx-vlm module [#2001](https://github.com/docling)"),
            _claim("CLM-3", "Aspose.Cells supports chart rendering"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1
        assert result[0].claim_id == "CLM-3"

    def test_empty_claims(self, product):
        result = _filter_contaminated_claims([], product)
        assert result == []

    def test_all_contaminated(self, product):
        claims = [
            _claim("CLM-1", "docling converts PDFs to markdown"),
            _claim("CLM-2", "flask web server for Python"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 0

    def test_product_family_name_kept(self, product):
        """Claims mentioning the product family are kept even with contaminants."""
        claims = [
            _claim("CLM-1", "integrate Aspose.Cells with TensorFlow for data export"),
        ]
        result = _filter_contaminated_claims(claims, product)
        assert len(result) == 1
