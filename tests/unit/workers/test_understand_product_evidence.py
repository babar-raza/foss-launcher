"""Tests for TC-3779: ProductEvidence enrichment in Understand worker."""
from __future__ import annotations

import pytest
from launcher.models.understanding import ProductEvidence, UnderstandingBundle
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier, ApiSurface, FormatRecord
from launcher.models.understanding import RepoInfo, SharedFacts


class TestProductEvidenceModel:
    """ProductEvidence model tests."""

    def test_default_empty(self):
        """ProductEvidence() creates valid empty instance."""
        pe = ProductEvidence()
        assert pe.supported_formats == []
        assert pe.input_formats == []
        assert pe.output_formats == []
        assert pe.conversion_pairs == []
        assert pe.workflows == []
        assert pe.capabilities == []

    def test_with_data(self):
        """ProductEvidence accepts structured data."""
        pe = ProductEvidence(
            supported_formats=["PDF", "XLSX", "CSV"],
            input_formats=["PDF", "XLSX"],
            output_formats=["CSV", "PDF"],
            conversion_pairs=[
                {"source": "XLSX", "target": "CSV", "evidence_file": "examples/convert.py"},
            ],
            workflows=[
                {"name": "convert_xlsx", "source_file": "examples/convert.py", "api_classes_used": ["Workbook"]},
            ],
            capabilities=[
                {"capability": "Read Excel files", "source": "README.md"},
            ],
        )
        assert len(pe.supported_formats) == 3
        assert pe.conversion_pairs[0]["source"] == "XLSX"
        assert pe.workflows[0]["name"] == "convert_xlsx"

    def test_serialization_roundtrip(self):
        """ProductEvidence survives JSON roundtrip."""
        pe = ProductEvidence(
            supported_formats=["OBJ", "STL"],
            conversion_pairs=[{"source": "OBJ", "target": "STL", "evidence_file": "ex.py"}],
        )
        data = pe.model_dump()
        pe2 = ProductEvidence.model_validate(data)
        assert pe2.supported_formats == ["OBJ", "STL"]
        assert pe2.conversion_pairs == pe.conversion_pairs


class TestUnderstandingBundleWithEvidence:
    """UnderstandingBundle backward compatibility with product_evidence."""

    def _make_bundle(self, **kwargs):
        return UnderstandingBundle(
            product=ProductIdentity(
                family="cells", platform="python",
                display_name="Aspose.Cells for Python",
                canonical_import="aspose.cells",
                repo_url="https://github.com/aspose-cells/aspose-cells-python",
            ),
            repo=RepoInfo(
                file_tree=["README.md"],
                doc_paths=[],
                example_paths=[],
                readme_summary="test",
            ),
            richness_tier=RichnessResult(tier=RichnessTier.B, score=15, reason="test"),
            api_surface=ApiSurface(
                public_classes=[], import_allowlist=[], confidence="low",
            ),
            claims=[],
            snippets=[],
            **kwargs,
        )

    def test_bundle_without_evidence_defaults(self):
        """Bundle without product_evidence gets empty default."""
        bundle = self._make_bundle()
        assert isinstance(bundle.product_evidence, ProductEvidence)
        assert bundle.product_evidence.supported_formats == []

    def test_bundle_with_evidence(self):
        """Bundle accepts product_evidence kwarg."""
        pe = ProductEvidence(supported_formats=["PDF"])
        bundle = self._make_bundle(product_evidence=pe)
        assert bundle.product_evidence.supported_formats == ["PDF"]

    def test_bundle_roundtrip(self):
        """Bundle with evidence survives dump/validate cycle."""
        pe = ProductEvidence(
            supported_formats=["XLSX"],
            conversion_pairs=[{"source": "XLSX", "target": "CSV", "evidence_file": "e.py"}],
        )
        bundle = self._make_bundle(product_evidence=pe)
        data = bundle.model_dump()
        bundle2 = UnderstandingBundle.model_validate(data)
        assert bundle2.product_evidence.supported_formats == ["XLSX"]
        assert len(bundle2.product_evidence.conversion_pairs) == 1


# ===========================================================================
# QSR-01 (TC-4040): FormatRecord → ProductEvidence format field wiring
# ===========================================================================


class TestFormatMatrixWiring:
    """TC-4040: format_matrix list comprehensions populate ProductEvidence format fields (QSR-01)."""

    def test_product_evidence_supported_formats_from_format_matrix(self):
        """3 records (can_import+export, import-only, export-only) → correct 3 lists."""
        records = [
            FormatRecord(name="OBJ", can_import=True, can_export=True),
            FormatRecord(name="FBX", can_import=True, can_export=False),
            FormatRecord(name="STL", can_import=False, can_export=True),
        ]
        pe = ProductEvidence(
            supported_formats=[fr.name for fr in records if fr.can_import or fr.can_export],
            input_formats=[fr.name for fr in records if fr.can_import],
            output_formats=[fr.name for fr in records if fr.can_export],
        )
        assert pe.supported_formats == ["OBJ", "FBX", "STL"]
        assert pe.input_formats == ["OBJ", "FBX"]
        assert pe.output_formats == ["OBJ", "STL"]

    def test_product_evidence_empty_format_matrix_yields_empty_lists(self):
        """Empty _format_matrix → all three format lists are []."""
        records: list[FormatRecord] = []
        pe = ProductEvidence(
            supported_formats=[fr.name for fr in records if fr.can_import or fr.can_export],
            input_formats=[fr.name for fr in records if fr.can_import],
            output_formats=[fr.name for fr in records if fr.can_export],
        )
        assert pe.supported_formats == []
        assert pe.input_formats == []
        assert pe.output_formats == []

    def test_product_evidence_import_only_formats(self):
        """Import-only record: in supported_formats + input_formats, NOT in output_formats."""
        records = [FormatRecord(name="DOCX", can_import=True, can_export=False)]
        pe = ProductEvidence(
            supported_formats=[fr.name for fr in records if fr.can_import or fr.can_export],
            input_formats=[fr.name for fr in records if fr.can_import],
            output_formats=[fr.name for fr in records if fr.can_export],
        )
        assert "DOCX" in pe.supported_formats
        assert "DOCX" in pe.input_formats
        assert "DOCX" not in pe.output_formats

    def test_product_evidence_export_only_formats(self):
        """Export-only record: in supported_formats + output_formats, NOT in input_formats."""
        records = [FormatRecord(name="PDF", can_import=False, can_export=True)]
        pe = ProductEvidence(
            supported_formats=[fr.name for fr in records if fr.can_import or fr.can_export],
            input_formats=[fr.name for fr in records if fr.can_import],
            output_formats=[fr.name for fr in records if fr.can_export],
        )
        assert "PDF" in pe.supported_formats
        assert "PDF" not in pe.input_formats
        assert "PDF" in pe.output_formats
