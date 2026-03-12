"""Test pydantic models validate correctly."""
from __future__ import annotations

import pytest

from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier, ApiSurface
from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.models.page_ir import PageIR, SectionIR, BlockIR, BlockType
from launcher.models.run_config import RunConfig, LLMEndpoint, LLMConfig
from launcher.models.evaluation import EvaluationReport, Verdict, Grade, Finding, PageEvaluation
from launcher.models.content import ContentManifest, GeneratedPage
from launcher.models.understanding import ProductEvidence
from launcher.models.publish import PublishBundle, Patch, PatchAction


class TestProductModels:
    def test_product_identity(self):
        p = ProductIdentity(family="cells", platform="python", display_name="Aspose.Cells FOSS for Python", canonical_import="aspose_cells_foss", repo_url="https://github.com/test/test")
        assert p.family == "cells"

    def test_richness_result(self):
        r = RichnessResult(tier=RichnessTier.A, score=30, reason="Rich docs")
        assert r.tier == RichnessTier.A


class TestClaimModels:
    def test_claim(self):
        c = Claim(claim_id="CLM-001", text="Test claim", kind="feature")
        assert c.visibility == "public"

    def test_evidence_anchor(self):
        e = EvidenceAnchor(source_file="README.md")
        assert e.line_start is None


class TestPageIR:
    def test_block_ir(self):
        b = BlockIR(type=BlockType.paragraph, content="Hello")
        assert b.type == BlockType.paragraph

    def test_section_ir(self):
        s = SectionIR(section_id="s1", heading="Intro", blocks=[BlockIR(type=BlockType.paragraph, content="Hi")])
        assert len(s.blocks) == 1

    def test_page_ir(self):
        p = PageIR(page_id="p1", page_role="landing", title="Test")
        assert p.sections == []


class TestRunConfig:
    def test_minimal(self):
        rc = RunConfig(family="cells", platform="python", repo_url="https://github.com/t/t")
        assert rc.launch_tier == "auto"

    def test_with_llm(self):
        rc = RunConfig(family="cells", platform="python", repo_url="https://github.com/t/t", llm=LLMConfig(primary=LLMEndpoint(base_url="http://localhost:11434/v1", model="test")))
        assert rc.llm.primary.model == "test"


class TestEvaluation:
    def test_evaluation_report(self):
        r = EvaluationReport(verdict=Verdict.GO)
        assert r.verdict == Verdict.GO

    def test_finding(self):
        f = Finding(check="frontmatter", message="Missing title")
        assert f.severity == "medium"


class TestContent:
    def test_manifest(self):
        m = ContentManifest()
        assert m.pages == []

    def test_manifest_default_api_surface(self):
        """TC-HO-09: ContentManifest() without api_surface arg gets empty-but-valid ApiSurface."""
        m = ContentManifest()
        assert m.api_surface.public_classes == []
        assert m.api_surface.import_allowlist == []
        assert m.api_surface.confidence == "low"

    def test_manifest_default_product_evidence(self):
        """TC-HO-09: ContentManifest() without product_evidence arg gets empty ProductEvidence."""
        m = ContentManifest()
        assert m.product_evidence.supported_formats == []
        assert m.product_evidence.limitations == []
        assert m.product_evidence.install_recipe is None

    def test_manifest_with_api_surface(self):
        """TC-HO-09: ContentManifest accepts and round-trips populated ApiSurface."""
        api = ApiSurface(
            public_classes=["MyClass"],
            import_allowlist=["import mylib"],
            confidence="high",
            api_identifiers=["MyClass.method"],
        )
        m = ContentManifest(api_surface=api)
        assert m.api_surface.public_classes == ["MyClass"]
        assert m.api_surface.confidence == "high"
        # Round-trip serialization
        data = m.model_dump(mode="json")
        m2 = ContentManifest.model_validate(data)
        assert m2.api_surface.public_classes == ["MyClass"]

    def test_manifest_with_product_evidence(self):
        """TC-HO-09: ContentManifest accepts and round-trips populated ProductEvidence."""
        pe = ProductEvidence(
            supported_formats=["PDF", "DOCX"],
            input_formats=["PDF"],
            output_formats=["DOCX"],
        )
        m = ContentManifest(product_evidence=pe)
        assert m.product_evidence.supported_formats == ["PDF", "DOCX"]
        # Round-trip serialization
        data = m.model_dump(mode="json")
        m2 = ContentManifest.model_validate(data)
        assert m2.product_evidence.supported_formats == ["PDF", "DOCX"]

    def test_manifest_json_roundtrip_both_fields(self):
        """TC-HO-09: Full round-trip with both api_surface and product_evidence populated."""
        api = ApiSurface(
            public_classes=["FooClass", "BarClass"],
            import_allowlist=["import foo"],
            confidence="medium",
        )
        pe = ProductEvidence(
            supported_formats=["OBJ", "FBX"],
            limitations=[],
        )
        m = ContentManifest(api_surface=api, product_evidence=pe)
        json_str = m.model_dump_json()
        m2 = ContentManifest.model_validate_json(json_str)
        assert m2.api_surface.public_classes == ["FooClass", "BarClass"]
        assert m2.product_evidence.supported_formats == ["OBJ", "FBX"]


class TestPublish:
    def test_patch(self):
        p = Patch(file_path="content/test.md", action=PatchAction.create)
        assert p.content_hash == ""


class TestModelsInit:
    def test_skills_config_importable_from_models(self):
        from launcher.models import SkillsConfig
        cfg = SkillsConfig()
        assert cfg.enabled is True
        assert cfg.path == "skills.md"

    def test_skills_config_disabled(self):
        from launcher.models import SkillsConfig
        cfg = SkillsConfig(enabled=False)
        assert cfg.enabled is False
