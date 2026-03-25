"""TC-PLT-213: Platform Parity tests.

Covers:
- 3a: extraction_degraded field in UnderstandingBundle
- 3b: Multi-platform private API filter
- 3b: Namespace stripping for C++/Java/.NET
- 3c: Platform-aware code block language defaults
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


# ── 3a: UnderstandingBundle extraction_degraded field ───────────────────


class TestExtractionDegradedField:
    """TC-PLT-213 Phase 3a: extraction_degraded exists with correct default."""

    def test_field_exists_with_default_false(self):
        from launcher.models.understanding import UnderstandingBundle
        fields = UnderstandingBundle.model_fields
        assert "extraction_degraded" in fields
        assert fields["extraction_degraded"].default is False

    def test_field_can_be_set_true(self):
        from launcher.models.understanding import UnderstandingBundle
        # Just verify the field accepts True (via model_fields check, not full construction)
        field = UnderstandingBundle.model_fields["extraction_degraded"]
        assert field.annotation is bool or field.annotation == bool


# ── 3b: Multi-platform private API filter ───────────────────────────────


def _make_product(platform="python"):
    return SimpleNamespace(
        family="cells",
        platform=platform,
        display_name=f"Aspose.Cells FOSS for {platform}",
        canonical_import="aspose_cells_foss",
        runtime_import="",
    )


class TestPrivateApiFilter:
    """TC-PLT-213 Phase 3b: _references_private_api works across platforms."""

    def _check(self, text, platform):
        from launcher.workers.understand.extract._validation import _references_private_api
        return _references_private_api(text, _make_product(platform))

    def test_python_underscore_detected(self):
        assert self._check("Uses _internal_method for processing", "python")

    def test_python_public_passes(self):
        assert not self._check("Uses Workbook class for spreadsheets", "python")

    def test_cpp_underscore_class_detected(self):
        assert self._check("Uses _InternalHelper class", "cpp")

    def test_cpp_public_passes(self):
        assert not self._check("Uses Presentation class", "cpp")

    def test_dotnet_underscore_detected(self):
        assert self._check("Access _DetailImpl for internals", "dotnet")

    def test_dotnet_public_passes(self):
        assert not self._check("Uses ThreeD.Scene class", "dotnet")

    def test_java_internal_package_detected(self):
        assert self._check("Uses internal.HelperClass for setup", "java")

    def test_java_impl_package_detected(self):
        assert self._check("Uses impl.CoreProcessor for tasks", "java")

    def test_java_public_passes(self):
        assert not self._check("Uses com.aspose.slides.Presentation", "java")

    def test_unknown_platform_always_passes(self):
        assert not self._check("Uses _internal_thing", "ruby")

    def test_backward_compat_alias(self):
        """_references_private_python_api still works as alias."""
        from launcher.workers.understand.extract._validation import _references_private_python_api
        assert _references_private_python_api("Uses _helper", _make_product("python"))


# ── 3b: Namespace stripping ─────────────────────────────────────────────


class TestStripNamespace:
    """TC-PLT-213 Phase 3b: _strip_namespace handles platform separators."""

    def _strip(self, name, platform):
        from launcher.workers.understand.extract._linking import _strip_namespace
        return _strip_namespace(name, platform)

    def test_python_no_change(self):
        assert self._strip("Workbook", "python") == "Workbook"

    def test_python_dotted_no_change(self):
        assert self._strip("Workbook.save", "python") == "Workbook.save"

    def test_cpp_strips_namespace(self):
        assert self._strip("Aspose::Slides::Presentation", "cpp") == "Presentation"

    def test_cpp_single_name_unchanged(self):
        assert self._strip("Presentation", "cpp") == "Presentation"

    def test_java_strips_package(self):
        assert self._strip("com.aspose.slides.Presentation", "java") == "Presentation"

    def test_java_preserves_class_method(self):
        assert self._strip("Workbook.save", "java") == "Workbook.save"

    def test_dotnet_strips_namespace(self):
        assert self._strip("Aspose.ThreeD.Scene", "dotnet") == "Scene"

    def test_dotnet_preserves_class_method(self):
        assert self._strip("Scene.Open", "dotnet") == "Scene.Open"

    def test_unknown_platform_no_change(self):
        assert self._strip("Foo::Bar", "rust") == "Foo::Bar"


# ── 3c: Platform-aware code language defaults ───────────────────────────


class TestNormalizeCodeLanguages:
    """TC-PLT-213 Phase 3c: _normalize_code_languages uses platform defaults."""

    def _normalize(self, blocks, platform="python"):
        from launcher.workers.generate.worker import _normalize_code_languages
        return _normalize_code_languages(blocks, platform=platform)

    def _code_block(self, content="x = 1", language=None):
        from launcher.models.page_ir import BlockIR, BlockType
        return BlockIR(type=BlockType.code, content=content, language=language or "")

    def test_python_default(self):
        result = self._normalize([self._code_block()], "python")
        assert result[0].language == "python"

    def test_dotnet_default(self):
        result = self._normalize([self._code_block("var x = 1;")], "dotnet")
        assert result[0].language == "csharp"

    def test_java_default(self):
        result = self._normalize([self._code_block("int x = 1;")], "java")
        assert result[0].language == "java"

    def test_cpp_default(self):
        result = self._normalize([self._code_block("int x = 1;")], "cpp")
        assert result[0].language == "cpp"

    def test_shell_detected_across_platforms(self):
        for platform in ("python", "dotnet", "java", "cpp"):
            result = self._normalize([self._code_block("pip install foo")], platform)
            assert result[0].language == "bash", f"Failed for {platform}"

    def test_dotnet_shell_detected(self):
        result = self._normalize([self._code_block("dotnet add package Aspose.ThreeD")], "dotnet")
        assert result[0].language == "bash"

    def test_mvn_shell_detected(self):
        result = self._normalize([self._code_block("mvn dependency:resolve -Dartifact=foo")], "java")
        assert result[0].language == "bash"

    def test_existing_language_preserved(self):
        block = self._code_block("some code")
        block = block.model_copy(update={"language": "xml"})
        result = self._normalize([block], "java")
        assert result[0].language == "xml"

    def test_wrong_tag_on_shell_corrected(self):
        """A csharp-tagged block with 'dotnet add' should be corrected to bash."""
        block = self._code_block("dotnet add package Foo")
        block = block.model_copy(update={"language": "csharp"})
        result = self._normalize([block], "dotnet")
        assert result[0].language == "bash"
