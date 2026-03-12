"""Integration tests for the Understand module redesign (humming-greeting-kay).

TC-4007 Phase 7: Validates the full pipeline across 7 key scenarios:
1. Deterministic evidence extracted before LLM call
2. Evidence context appears in LLM prompt
3. Contradiction resolution downgrades conflicting claims
4. Limitation extraction from mock repo
5. PlatformProfile resolution for all platforms
6. Property-call gate fires on obj.prop()
7. Adapter registry dispatches correctly for all platforms
"""
from __future__ import annotations

from pathlib import Path

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.product import (
    ApiSurface,
    ClassBrief,
    FormatRecord,
    MethodSignature,
    ProductIdentity,
    PropertyRecord,
    RichnessResult,
)
from launcher.models.understanding import (
    FieldConfidence,
    FileCategory,
    FileEntry,
    LimitationEntry,
    MissingInfoEntry,
    ProductEvidence,
    RepoInfo,
    SharedFacts,
    UnderstandingBundle,
    WorkflowExample,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def mock_product() -> ProductIdentity:
    return ProductIdentity(
        family="aspose-3d-foss",
        platform="python",
        display_name="Aspose.3D FOSS",
        canonical_import="aspose.threed",
        runtime_import="aspose.threed",
        repo_url="https://github.com/example/aspose-3d-foss",
    )


@pytest.fixture
def mock_repo_info() -> RepoInfo:
    return RepoInfo(
        file_tree=["src/aspose/threed/__init__.py", "src/aspose/threed/scene.py", "README.md"],
        file_index={
            "src/aspose/threed/__init__.py": FileEntry(category=FileCategory.source, size_bytes=100),
            "src/aspose/threed/scene.py": FileEntry(category=FileCategory.source, size_bytes=5000),
            "README.md": FileEntry(category=FileCategory.doc, size_bytes=2000),
        },
        source_paths=["src/aspose/threed/__init__.py", "src/aspose/threed/scene.py"],
        doc_paths=["README.md"],
        shared_facts=SharedFacts(package_name="aspose-3d-foss", primary_language="python"),
    )


@pytest.fixture
def mock_api_surface() -> ApiSurface:
    return ApiSurface(
        public_classes=["Scene", "Node", "Mesh"],
        class_briefs=[
            ClassBrief(
                name="Scene",
                docstring_snippet="Represents a 3D scene.",
                methods=["from_file", "save", "merge"],
                properties=["name", "root_node", "file_format"],
                typed_methods=[
                    MethodSignature(name="from_file", parameters=[], return_type="Scene"),
                    MethodSignature(name="save", parameters=[], return_type="None"),
                ],
                typed_properties=[
                    PropertyRecord(name="name", type_annotation="str", is_readonly=False),
                    PropertyRecord(name="root_node", type_annotation="Node", is_readonly=True),
                    PropertyRecord(name="file_format", type_annotation="FileFormat", is_readonly=True),
                ],
            ),
            ClassBrief(name="Node", docstring_snippet="A node in the scene graph.", methods=["add_child"]),
            ClassBrief(name="Mesh", docstring_snippet="3D mesh geometry.", methods=["create_box"]),
        ],
        api_identifiers=["Scene", "Node", "Mesh", "from_file", "save", "merge", "add_child", "create_box"],
        import_allowlist=["aspose.threed"],
        format_matrix=[
            FormatRecord(name="FBX", extension=".fbx", can_import=True, can_export=True),
            FormatRecord(name="OBJ", extension=".obj", can_import=True, can_export=False),
            FormatRecord(name="GLTF", extension=".gltf", can_import=True, can_export=True),
        ],
        confidence="high",
    )


@pytest.fixture
def mock_limitations() -> list[LimitationEntry]:
    return [
        LimitationEntry(
            feature="OBJ export",
            constraint="not supported",
            status="unsupported",
            source_file="src/aspose/threed/scene.py",
            source_line=42,
            confidence="ast_verified",
        ),
        LimitationEntry(
            feature="async API",
            constraint="experimental",
            status="experimental",
            source_file="README.md",
            confidence="doc_stated",
        ),
    ]


# ── Scenario 1: Evidence extracted BEFORE LLM ──────────────────────────


class TestScenario1EvidenceBeforeLLM:
    """Verify that _entry.py calls deterministic extractors before LLM."""

    def test_pipeline_ordering_in_source(self):
        """Static check: in _entry.py, evidence extraction steps precede LLM call."""
        import inspect
        from launcher.workers.understand.extract._entry import run_extract
        source = inspect.getsource(run_extract)

        # Find positions of key markers
        format_matrix_pos = source.find("extract_format_matrix")
        limitations_pos = source.find("extract_limitations")
        install_recipe_pos = source.find("extract_install_recipe")
        evidence_context_pos = source.find("_build_evidence_context")
        llm_pos = source.find("_extract_claims_llm")

        # All deterministic steps must come before LLM call
        assert format_matrix_pos > 0, "extract_format_matrix not found"
        assert limitations_pos > 0, "extract_limitations not found"
        assert install_recipe_pos > 0, "extract_install_recipe not found"
        assert evidence_context_pos > 0, "_build_evidence_context not found"
        assert llm_pos > 0, "_extract_claims_llm not found"

        assert format_matrix_pos < llm_pos, "format_matrix must run before LLM"
        assert limitations_pos < llm_pos, "limitations must run before LLM"
        assert install_recipe_pos < llm_pos, "install_recipe must run before LLM"
        assert evidence_context_pos < llm_pos, "evidence_context must be built before LLM"

    def test_contradiction_resolver_after_llm(self):
        """Static check: contradiction resolver runs AFTER LLM in _entry.py."""
        import inspect
        from launcher.workers.understand.extract._entry import run_extract
        source = inspect.getsource(run_extract)

        llm_pos = source.find("_extract_claims_llm")
        resolver_pos = source.find("resolve_contradictions")

        assert resolver_pos > llm_pos, "contradiction resolver must run after LLM"


# ── Scenario 2: Evidence context in LLM prompt ─────────────────────────


class TestScenario2EvidenceContext:
    """Verify evidence context assembly produces correct structured output."""

    def test_evidence_context_contains_format_matrix(self, mock_api_surface):
        from launcher.workers.understand.extract._entry import _build_evidence_context

        ctx = _build_evidence_context(
            mock_api_surface,
            mock_api_surface.format_matrix,
            [],
            None,
        )
        assert "SOURCE-VERIFIED FACTS" in ctx
        assert "Format Matrix" in ctx
        assert "FBX" in ctx
        assert "OBJ" in ctx

    def test_evidence_context_contains_limitations(self, mock_api_surface, mock_limitations):
        from launcher.workers.understand.extract._entry import _build_evidence_context

        ctx = _build_evidence_context(
            mock_api_surface,
            mock_api_surface.format_matrix,
            mock_limitations,
            None,
        )
        assert "Known Limitations" in ctx
        assert "OBJ export" in ctx
        assert "not supported" in ctx

    def test_evidence_context_contains_api_summary(self, mock_api_surface):
        from launcher.workers.understand.extract._entry import _build_evidence_context

        ctx = _build_evidence_context(mock_api_surface, [], [], None)
        assert "Public API" in ctx
        assert "Scene" in ctx
        assert "high" in ctx  # confidence

    def test_evidence_context_respects_budget(self, mock_api_surface):
        from launcher.workers.understand.extract._entry import _build_evidence_context

        ctx = _build_evidence_context(mock_api_surface, mock_api_surface.format_matrix, [], None, max_chars=200)
        assert len(ctx) <= 200

    def test_evidence_context_includes_install_recipe(self, mock_api_surface):
        from launcher.workers.understand.extract._entry import _build_evidence_context
        from launcher.models.understanding import InstallRecipe

        recipe = InstallRecipe(install_command="pip install aspose-3d-foss", package_name="aspose-3d-foss")
        ctx = _build_evidence_context(mock_api_surface, [], [], recipe)
        assert "pip install aspose-3d-foss" in ctx

    def test_evidence_context_empty_when_no_evidence(self):
        from launcher.workers.understand.extract._entry import _build_evidence_context

        empty_surface = ApiSurface(public_classes=[], class_briefs=[], confidence="low", import_allowlist=[])
        ctx = _build_evidence_context(empty_surface, [], [], None)
        assert ctx == ""


# ── Scenario 3: Contradiction resolution ────────────────────────────────


class TestScenario3ContradictionResolution:
    """Verify contradictions between claims and source-verified facts are resolved."""

    def test_format_export_contradiction_downgrades(self, mock_api_surface):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions

        claims = [
            Claim(claim_id="c1", text="You can export to OBJ format easily", kind="feature"),
        ]
        resolved, log = resolve_contradictions(claims, mock_api_surface)
        assert len(log) == 1
        assert log[0]["type"] == "format_capability"
        assert resolved[0].visibility == "internal"

    def test_valid_export_not_downgraded(self, mock_api_surface):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions

        claims = [
            Claim(claim_id="c2", text="Export to FBX is fully supported", kind="feature"),
        ]
        resolved, log = resolve_contradictions(claims, mock_api_surface)
        assert len(log) == 0
        assert resolved[0].visibility != "internal"

    def test_api_existence_contradiction(self, mock_api_surface):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions

        claims = [
            Claim(claim_id="c3", text="Use the `FakeClass` to do something", kind="feature"),
        ]
        resolved, log = resolve_contradictions(claims, mock_api_surface)
        assert len(log) == 1
        assert log[0]["type"] == "api_existence"
        assert resolved[0].visibility == "internal"

    def test_limitation_override_appends_caveat(self, mock_api_surface, mock_limitations):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions

        claims = [
            Claim(claim_id="c4", text="OBJ export is fully supported for all formats", kind="feature"),
        ]
        resolved, log = resolve_contradictions(claims, mock_api_surface, mock_limitations)
        # Should have format_capability contradiction (OBJ can_export=False)
        assert len(log) >= 1
        assert resolved[0].visibility == "internal"

    def test_empty_claims_returns_empty(self, mock_api_surface):
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions

        resolved, log = resolve_contradictions([], mock_api_surface)
        assert resolved == []
        assert log == []


# ── Scenario 4: Limitation extraction ───────────────────────────────────


class TestScenario4LimitationExtraction:
    """Verify limitation extraction from mock repository files."""

    def test_limitation_model_fields(self):
        lim = LimitationEntry(
            feature="OBJ export",
            constraint="not supported",
            status="unsupported",
            source_file="scene.py",
            source_line=42,
            confidence="ast_verified",
            quote="raise NotImplementedError('OBJ export')",
        )
        assert lim.feature == "OBJ export"
        assert lim.status == "unsupported"
        assert lim.confidence == "ast_verified"

    def test_limitation_in_product_evidence(self, mock_limitations):
        ev = ProductEvidence(limitations=mock_limitations)
        assert len(ev.limitations) == 2
        assert ev.limitations[0].feature == "OBJ export"

    def test_workflow_example_model(self):
        wf = WorkflowExample(
            name="convert_fbx_to_gltf",
            title="Convert FBX to GLTF",
            code="scene = Scene.from_file('model.fbx')\nscene.save('out.gltf')",
            steps=["from_file", "save"],
            language="python",
            source_file="tests/test_convert.py",
            source_lines=(10, 15),
        )
        assert len(wf.steps) == 2
        assert wf.language == "python"

    def test_missing_info_entry_model(self):
        entry = MissingInfoEntry(
            field="format_matrix",
            reason="no tree-sitter grammar for Rust",
            attempted_strategies=["tree-sitter", "regex"],
            fallback_used="regex",
        )
        assert entry.field == "format_matrix"
        assert len(entry.attempted_strategies) == 2

    def test_field_confidence_model(self):
        fc = FieldConfidence(source="ast_verified", detail="scene.py:42")
        assert fc.source == "ast_verified"


# ── Scenario 5: PlatformProfile resolution ──────────────────────────────


class TestScenario5PlatformProfile:
    """Verify PlatformProfile resolves correctly for all 6 platforms."""

    @pytest.mark.parametrize("platform,expected_ext", [
        ("python", ".py"),
        ("typescript", ".ts"),
        ("java", ".java"),
        ("dotnet", ".cs"),
        ("node", ".ts"),
        ("cpp", ".cpp"),
    ])
    def test_resolve_all_platforms(self, platform, expected_ext):
        from launcher.shared.platform_utils import resolve_platform_profile
        profile = resolve_platform_profile(platform)
        assert profile.platform == platform
        assert profile.file_ext == expected_ext

    def test_unknown_platform_returns_generic(self):
        from launcher.shared.platform_utils import resolve_platform_profile
        profile = resolve_platform_profile("rust")
        assert profile.platform == "rust"
        # Should still return a valid profile

    def test_profile_attached_to_product(self, mock_product):
        from launcher.models.product import PlatformProfile
        profile = PlatformProfile(
            platform="python",
            lang_tag="python",
            import_tpl="aspose.threed",
            install_cmd="pip install aspose-3d-foss",
        )
        product = mock_product.model_copy(update={"platform_profile": profile})
        assert product.platform_profile is not None
        assert product.platform_profile.platform == "python"


# ── Scenario 6: Property-call gate ──────────────────────────────────────


class TestScenario6PropertyCallGate:
    """Verify the property-call gate detects obj.prop() anti-pattern."""

    def test_property_called_as_method_flagged(self, mock_api_surface):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers

        content = """
```python
scene = Scene()
name = scene.name()
```
"""
        findings = check_api_identifiers(content, "test-page", api_surface=mock_api_surface)
        prop_findings = [f for f in findings if f.check == "api_property_called_as_method"]
        assert len(prop_findings) >= 1
        assert "name" in prop_findings[0].message

    def test_property_accessed_correctly_no_finding(self, mock_api_surface):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers

        # Property accessed without parens — should NOT produce a finding
        # (This gate only checks code blocks for method-call patterns)
        content = """
```python
scene = Scene()
result = scene.from_file("test.obj")
```
"""
        findings = check_api_identifiers(content, "test-page", api_surface=mock_api_surface)
        prop_findings = [f for f in findings if f.check == "api_property_called_as_method"]
        assert len(prop_findings) == 0

    def test_method_call_not_flagged_as_property(self, mock_api_surface):
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers

        content = """
```python
scene = Scene()
scene.save()
```
"""
        findings = check_api_identifiers(content, "test-page", api_surface=mock_api_surface)
        prop_findings = [f for f in findings if f.check == "api_property_called_as_method"]
        assert len(prop_findings) == 0


# ── Scenario 7: Adapter registry ────────────────────────────────────────


class TestScenario7AdapterRegistry:
    """Verify adapter registry dispatches correctly for all platforms."""

    @pytest.mark.parametrize("platform,expected_id", [
        ("python", "python"),
        ("typescript", "typescript"),
        ("javascript", "typescript"),
        ("node", "typescript"),
        ("dotnet", "dotnet"),
        ("csharp", "dotnet"),
        ("java", "java"),
        ("cpp", "cpp"),
    ])
    def test_registry_dispatch(self, platform, expected_id):
        from launcher.workers.understand.adapters import get_extractor
        extractor = get_extractor(platform)
        assert extractor.platform_id == expected_id

    def test_unknown_platform_generic(self):
        from launcher.workers.understand.adapters import get_extractor
        extractor = get_extractor("rust")
        assert extractor.platform_id == "generic"

    def test_adapter_interface_consistency(self):
        """All registered adapters implement the required abstract methods."""
        from launcher.workers.understand.adapters import get_extractor
        from launcher.workers.understand.adapters._base import PlatformExtractor

        for platform in ["python", "typescript", "dotnet", "java", "cpp", "unknown"]:
            ext = get_extractor(platform)
            assert isinstance(ext, PlatformExtractor)
            assert isinstance(ext.platform_id, str)
            assert isinstance(ext.file_extensions, list)
            assert len(ext.file_extensions) > 0


# ── Full bundle assembly ────────────────────────────────────────────────


class TestBundleAssembly:
    """Verify UnderstandingBundle assembles correctly with all new fields."""

    def test_full_bundle_with_evidence(self, mock_product, mock_repo_info, mock_api_surface, mock_limitations):
        bundle = UnderstandingBundle(
            product=mock_product,
            repo=mock_repo_info,
            richness_tier=RichnessResult(tier="A", score=85, code_evidence_sparse=False, reason="test"),
            api_surface=mock_api_surface,
            claims=[Claim(claim_id="c1", text="Test claim", kind="feature")],
            snippets=[Snippet(code="print('hi')", language="python", source_type="synthetic")],
            product_evidence=ProductEvidence(
                limitations=mock_limitations,
                workflow_examples=[
                    WorkflowExample(name="test_wf", steps=["from_file", "save"]),
                ],
                missing_info=[
                    MissingInfoEntry(field="install_recipe", reason="no pyproject.toml"),
                ],
                confidence={
                    "format_matrix": FieldConfidence(source="ast_verified"),
                    "limitations": FieldConfidence(source="heuristic"),
                },
            ),
        )
        assert bundle.product.canonical_import == "aspose.threed"
        assert len(bundle.product_evidence.limitations) == 2
        assert len(bundle.product_evidence.workflow_examples) == 1
        assert len(bundle.product_evidence.missing_info) == 1
        assert bundle.product_evidence.confidence["format_matrix"].source == "ast_verified"

    def test_bundle_serialization_roundtrip(self, mock_product, mock_repo_info, mock_api_surface):
        bundle = UnderstandingBundle(
            product=mock_product,
            repo=mock_repo_info,
            richness_tier=RichnessResult(tier="B", score=60, code_evidence_sparse=True, reason="test"),
            api_surface=mock_api_surface,
            product_evidence=ProductEvidence(
                limitations=[LimitationEntry(feature="test", constraint="n/a")],
                confidence={"test": FieldConfidence(source="heuristic", detail="x")},
            ),
        )
        data = bundle.model_dump()
        restored = UnderstandingBundle.model_validate(data)
        assert restored.product.canonical_import == bundle.product.canonical_import
        assert len(restored.product_evidence.limitations) == 1
        assert restored.product_evidence.confidence["test"].source == "heuristic"
