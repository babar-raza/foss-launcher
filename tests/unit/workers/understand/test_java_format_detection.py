"""TC-JAVA-402: Validate Strategy 5 format detection for Java enums."""
from __future__ import annotations

import pytest

from launcher.models.product import (
    ApiSurface,
    ClassBrief,
    EnumMember,
    EnumRecord,
    ProductIdentity,
)
from launcher.workers.understand.extract._deterministic import extract_format_matrix


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="slides",
        platform="java",
        display_name="Aspose.Slides",
        canonical_import="com.aspose.slides",
        repo_url="https://github.com/aspose/slides-foss-java",
    )


def _make_api_surface_with_save_format() -> ApiSurface:
    """Build ApiSurface with a Java-style SaveFormat enum."""
    members = [
        EnumMember(name="PPTX"),
        EnumMember(name="PDF"),
        EnumMember(name="HTML"),
        EnumMember(name="ODP"),
        EnumMember(name="TIFF"),
    ]
    save_format = ClassBrief(
        name="SaveFormat",
        enums=[EnumRecord(name="SaveFormat", members=members)],
    )
    return ApiSurface(
        public_classes=["SaveFormat", "Presentation", "Slide"],
        import_allowlist=["com.aspose.slides"],
        confidence="high",
        class_briefs=[save_format],
    )


class TestJavaFormatDetectionStrategy5:
    """TC-JAVA-402: Validate that Strategy 5 works for Java SaveFormat/LoadFormat enums."""

    def test_java_save_format_enum_produces_records(self, tmp_path):
        """Java SaveFormat enum members appear as FormatRecords."""
        product = _make_product()
        api_surface = _make_api_surface_with_save_format()
        records = extract_format_matrix(tmp_path, product, api_surface=api_surface)
        names = {r.name for r in records}
        assert "PPTX" in names, f"PPTX should be in records; got {names}"
        assert "PDF" in names, f"PDF should be in records; got {names}"
        assert "HTML" in names, f"HTML should be in records; got {names}"

    def test_java_save_format_source_evidence(self, tmp_path):
        """FormatRecords from SaveFormat enum have correct source_evidence."""
        product = _make_product()
        api_surface = _make_api_surface_with_save_format()
        records = extract_format_matrix(tmp_path, product, api_surface=api_surface)
        pptx_rec = next((r for r in records if r.name == "PPTX"), None)
        assert pptx_rec is not None, "PPTX record must exist"
        assert pptx_rec.source_evidence.startswith("enum_member"), (
            f"source_evidence should start with 'enum_member'; got {pptx_rec.source_evidence!r}"
        )
        assert "SaveFormat" in pptx_rec.source_evidence, (
            f"source_evidence should reference SaveFormat; got {pptx_rec.source_evidence!r}"
        )

    def test_java_save_format_can_export_true(self, tmp_path):
        """SaveFormat enum members get can_export=True."""
        product = _make_product()
        api_surface = _make_api_surface_with_save_format()
        records = extract_format_matrix(tmp_path, product, api_surface=api_surface)
        pdf_rec = next((r for r in records if r.name == "PDF"), None)
        assert pdf_rec is not None
        assert pdf_rec.can_export, "PDF from SaveFormat must have can_export=True"

    def test_java_load_format_can_import_true(self, tmp_path):
        """LoadFormat enum members get can_import=True."""
        members = [
            EnumMember(name="PPTX"),
            EnumMember(name="ODP"),
            EnumMember(name="PPT"),
        ]
        load_format = ClassBrief(
            name="LoadFormat",
            enums=[EnumRecord(name="LoadFormat", members=members)],
        )
        api_surface = ApiSurface(
            public_classes=["LoadFormat"],
            import_allowlist=["com.aspose.slides"],
            confidence="high",
            class_briefs=[load_format],
        )
        product = _make_product()
        records = extract_format_matrix(tmp_path, product, api_surface=api_surface)
        odp_rec = next((r for r in records if r.name == "ODP"), None)
        assert odp_rec is not None, "ODP from LoadFormat must appear"
        assert odp_rec.can_import, "ODP from LoadFormat must have can_import=True"
        assert odp_rec.source_evidence == "enum_member:LoadFormat", (
            f"source_evidence should be 'enum_member:LoadFormat'; got {odp_rec.source_evidence!r}"
        )

    def test_no_format_enum_strategy5_produces_nothing(self, tmp_path):
        """When ApiSurface has no SaveFormat/LoadFormat class, Strategy 5 adds no records."""
        presentation = ClassBrief(
            name="Presentation",
            enums=[],
        )
        api_surface = ApiSurface(
            public_classes=["Presentation"],
            import_allowlist=["com.aspose.slides"],
            confidence="high",
            class_briefs=[presentation],
        )
        product = _make_product()
        records = extract_format_matrix(tmp_path, product, api_surface=api_surface)
        enum_records = [r for r in records if "enum_member" in (r.source_evidence or "")]
        assert len(enum_records) == 0, (
            f"No enum-derived records expected without SaveFormat/LoadFormat; got {len(enum_records)}"
        )
