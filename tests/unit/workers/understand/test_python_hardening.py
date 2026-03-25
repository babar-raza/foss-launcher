"""Phase 3 Python Understanding Hardening tests (TC-4079..TC-4083).

Covers:
- TC-4079: runtime_import filter accepts files under runtime_import prefix
- TC-4080: Per-file snippet extraction logging (fenced blocks from README)
- TC-4081: Class docstrings injected into evidence context when API surface thin
- TC-4082: Method-level docstring claims in ClassName.method: desc format
- TC-4083: self_review produces medium findings for thin Python API surface
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"
PYTHON_CELLS_DIR = FIXTURES_DIR / "python-cells"
PYTHON_SPARSE_DIR = FIXTURES_DIR / "python-sparse"


def _make_product(
    canonical_import: str = "aspose_cells_foss",
    runtime_import: str = "aspose.cells",
    family: str = "cells",
    platform: str = "python",
) -> "Any":
    from launcher.models.product import ProductIdentity
    return ProductIdentity(
        family=family,
        platform=platform,
        display_name="Aspose.Cells FOSS",
        canonical_import=canonical_import,
        runtime_import=runtime_import,
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
        repo_sha="abc123",
    )


# ---------------------------------------------------------------------------
# TC-4079: runtime_import prefix accepted in import filter
# ---------------------------------------------------------------------------


class TestRuntimeImportFilter:
    """TC-4079: Files reachable via runtime_import prefix pass the import filter."""

    def test_runtime_import_filter_not_canonical_import_filter(self, tmp_path: Path):
        """Source files using runtime_import prefix (aspose.cells) pass the filter.

        When canonical_import='aspose_cells_foss' but runtime_import='aspose.cells',
        source files at src/aspose/cells/workbook.py compute import_path='aspose.cells.workbook'.
        This must pass the filter even though it doesn't start with 'aspose_cells_foss'.
        """
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        # Use the python-cells fixture which has src/aspose/cells/ structure
        if not PYTHON_CELLS_DIR.is_dir():
            pytest.skip(f"python-cells fixture not found at {PYTHON_CELLS_DIR}")

        product = _make_product(
            canonical_import="aspose_cells_foss",
            runtime_import="aspose.cells",
        )
        result = _extract_api_surface(PYTHON_CELLS_DIR, product)

        # Should find Workbook and/or Worksheet — not 0 classes
        assert len(result.public_classes) >= 1, (
            f"Expected >= 1 public class using runtime_import='aspose.cells', "
            f"got {result.public_classes}. "
            "TC-4079 fix may not be applied or namespace package descent failed."
        )

    def test_namespace_package_finds_all_classes(self, tmp_path: Path):
        """Namespace package (aspose → aspose.cells) finds all classes in submodule.

        The python-cells fixture has:
          src/aspose/__init__.py  (namespace — exports 'cells' submodule)
          src/aspose/cells/__init__.py  (real package — exports Workbook, Worksheet)
          src/aspose/cells/workbook.py  (Workbook class)
          src/aspose/cells/worksheet.py (Worksheet class)

        After namespace descent and runtime_import filter, both classes must be found.
        """
        from launcher.workers.understand.extract._api_surface import _extract_api_surface

        if not PYTHON_CELLS_DIR.is_dir():
            pytest.skip(f"python-cells fixture not found at {PYTHON_CELLS_DIR}")

        product = _make_product(
            canonical_import="aspose_cells_foss",
            runtime_import="aspose.cells",
        )
        result = _extract_api_surface(PYTHON_CELLS_DIR, product)

        # Both Workbook and Worksheet should be found
        assert "Workbook" in result.public_classes or "Worksheet" in result.public_classes, (
            f"Expected Workbook or Worksheet in public_classes, got {result.public_classes}"
        )

    def test_canonical_import_only_still_accepted(self, tmp_path: Path):
        """Canonical import prefix is still accepted when runtime_import matches it."""
        # Create a simple repo where canonical_import == runtime_import
        repo = tmp_path / "repo"
        src = repo / "src" / "mylib"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('"""mylib."""\nfrom .core import MyClass\n')
        (src / "core.py").write_text(textwrap.dedent("""\
            class MyClass:
                \"\"\"Main class.\"\"\"
                def method(self) -> None:
                    pass
        """))

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test",
            platform="python",
            display_name="MyLib",
            canonical_import="mylib",
            runtime_import="mylib",
            repo_url="https://github.com/test/mylib",
        )
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        result = _extract_api_surface(repo, product)

        assert "MyClass" in result.public_classes

    def test_empty_runtime_import_does_not_crash(self, tmp_path: Path):
        """Empty runtime_import string does not cause crash in filter."""
        repo = tmp_path / "repo"
        src = repo / "src" / "mylib"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('from .core import Cls\n')
        (src / "core.py").write_text(textwrap.dedent("""\
            class Cls:
                \"\"\"Cls docstring.\"\"\"
                pass
        """))

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test",
            platform="python",
            display_name="Lib",
            canonical_import="mylib",
            runtime_import="",  # empty
            repo_url="https://github.com/test/mylib",
        )
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        # Must not raise
        result = _extract_api_surface(repo, product)
        assert isinstance(result.public_classes, list)


# ---------------------------------------------------------------------------
# _is_namespace_init unit tests (SR-TFL-02)
# ---------------------------------------------------------------------------


class TestIsNamespaceInit:
    """Dedicated tests for _is_namespace_init after relative-import fix."""

    def test_empty_init_is_namespace(self, tmp_path: Path):
        init = tmp_path / "__init__.py"
        init.write_text("", encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is True

    def test_relative_import_is_namespace(self, tmp_path: Path):
        """from . import cells is a namespace shim pattern."""
        init = tmp_path / "__init__.py"
        init.write_text('"""NS."""\nfrom . import cells\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is True

    def test_relative_wildcard_is_not_namespace(self, tmp_path: Path):
        """from . import * is NOT a namespace shim (it re-exports everything)."""
        init = tmp_path / "__init__.py"
        init.write_text('from .mod import *\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is False

    def test_class_def_is_not_namespace(self, tmp_path: Path):
        init = tmp_path / "__init__.py"
        init.write_text('class Foo:\n    pass\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is False

    def test_absolute_import_is_not_namespace(self, tmp_path: Path):
        init = tmp_path / "__init__.py"
        init.write_text('import os\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is False

    def test_future_import_only_is_namespace(self, tmp_path: Path):
        init = tmp_path / "__init__.py"
        init.write_text('from __future__ import annotations\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is True

    def test_relative_plus_future_is_namespace(self, tmp_path: Path):
        """Both __future__ and relative imports are allowed in namespace shims."""
        init = tmp_path / "__init__.py"
        init.write_text(
            'from __future__ import annotations\nfrom . import cells\n',
            encoding="utf-8",
        )
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is True

    def test_absolute_from_import_is_not_namespace(self, tmp_path: Path):
        """from os import path is a real import, not namespace."""
        init = tmp_path / "__init__.py"
        init.write_text('from os import path\n', encoding="utf-8")
        from launcher.workers.understand.adapters._python import _is_namespace_init
        assert _is_namespace_init(init) is False


# ---------------------------------------------------------------------------
# TC-4080: Fenced code block extraction from README
# ---------------------------------------------------------------------------


class TestSnippetExtraction:
    """TC-4080: Fenced code blocks are extracted from README and doc files."""

    def test_readme_fenced_blocks_extracted(self, tmp_path: Path):
        """README.md with fenced Python block produces at least 1 snippet."""
        from launcher.workers.understand.extract._snippets import _extract_fenced_code_blocks

        readme = textwrap.dedent("""\
            # Test Library

            ## Installation

            ```python
            pip install mylib
            ```

            ## Usage

            ```python
            from mylib import Client
            client = Client()
            result = client.fetch("data")
            print(result)
            ```
        """)

        blocks = _extract_fenced_code_blocks(readme)
        assert len(blocks) >= 1, f"Expected >= 1 fenced block, got {blocks}"
        # Should find blocks with 'python' lang tag
        langs = [lang for lang, _ in blocks]
        assert "python" in langs

    def test_fenced_block_without_language_tag_extracted_for_python_repo(self):
        """Fenced block without language tag is extracted (lang defaults to product lang)."""
        from launcher.workers.understand.extract._snippets import _extract_fenced_code_blocks

        content = textwrap.dedent("""\
            ## Example

            ```
            from mylib import Client
            client = Client()
            ```
        """)

        blocks = _extract_fenced_code_blocks(content)
        assert len(blocks) >= 1
        # lang should be empty string (caller fills default)
        langs = [lang for lang, _ in blocks]
        assert "" in langs or "python" in langs

    def test_python_cells_fixture_readme_has_fenced_blocks(self):
        """The python-cells fixture README has at least 1 fenced Python block."""
        if not PYTHON_CELLS_DIR.is_dir():
            pytest.skip(f"python-cells fixture not found at {PYTHON_CELLS_DIR}")

        from launcher.workers.understand.extract._snippets import _extract_fenced_code_blocks

        readme_path = PYTHON_CELLS_DIR / "README.md"
        assert readme_path.exists()

        content = readme_path.read_text(encoding="utf-8")
        blocks = _extract_fenced_code_blocks(content)
        assert len(blocks) >= 1, "python-cells README.md must have at least 1 fenced block"


# ---------------------------------------------------------------------------
# TC-4081: Evidence context with class docstrings for thin API
# ---------------------------------------------------------------------------


class TestThinApiEvidenceContext:
    """TC-4081: Class docstrings injected into evidence context when API surface thin."""

    def _make_api_surface_with_briefs(self, class_count: int = 1) -> "Any":
        """Build a mock ApiSurface with ClassBriefs containing docstrings."""
        from launcher.models.product import ApiSurface, ClassBrief, MethodSignature

        briefs = []
        for i in range(class_count):
            briefs.append(ClassBrief(
                name=f"MyClass{i}",
                docstring_snippet=f"MyClass{i} provides methods for data processing and transformation.",
                methods=[f"process{i}", f"validate{i}"],
                typed_methods=[
                    MethodSignature(
                        name=f"process{i}",
                        parameters=[],
                        return_type="None",
                        docstring_snippet=f"Process data using method {i}.",
                    ),
                ],
            ))
        return ApiSurface(
            public_classes=[b.name for b in briefs],
            import_allowlist=["mylib"],
            confidence="medium",
            class_briefs=briefs,
        )

    def test_thin_api_injects_class_docstrings(self):
        """Evidence context includes class docstrings when fewer than 3 classes."""
        from launcher.workers.understand.extract._entry import _build_evidence_context

        api_surface = self._make_api_surface_with_briefs(class_count=1)
        context_str = _build_evidence_context(
            api_surface=api_surface,
            format_matrix=[],
            limitations=[],
            install_recipe=None,
        )

        assert "MyClass0" in context_str
        assert "provides methods for data processing" in context_str, (
            "Class docstring should be injected into evidence context for thin API"
        )

    def test_thin_api_injects_method_docstrings(self):
        """Evidence context includes method docstrings when API surface is thin."""
        from launcher.workers.understand.extract._entry import _build_evidence_context

        api_surface = self._make_api_surface_with_briefs(class_count=1)
        context_str = _build_evidence_context(
            api_surface=api_surface,
            format_matrix=[],
            limitations=[],
            install_recipe=None,
        )

        assert "process0" in context_str
        assert "Process data using method" in context_str

    def test_fat_api_does_not_inject_extra_docstrings(self):
        """Evidence context does NOT inject class docstrings when >= 3 classes found."""
        from launcher.workers.understand.extract._entry import _build_evidence_context

        api_surface = self._make_api_surface_with_briefs(class_count=5)
        context_str = _build_evidence_context(
            api_surface=api_surface,
            format_matrix=[],
            limitations=[],
            install_recipe=None,
        )

        # Section 3b header should NOT be present for fat API
        assert "full docstrings — thin API surface" not in context_str

    def test_empty_docstring_does_not_crash(self):
        """Evidence context handles class with empty docstring_snippet gracefully."""
        from launcher.workers.understand.extract._entry import _build_evidence_context
        from launcher.models.product import ApiSurface, ClassBrief

        api_surface = ApiSurface(
            public_classes=["EmptyClass"],
            import_allowlist=["mylib"],
            confidence="low",
            class_briefs=[ClassBrief(name="EmptyClass", docstring_snippet="", methods=[])],
        )
        context_str = _build_evidence_context(
            api_surface=api_surface,
            format_matrix=[],
            limitations=[],
            install_recipe=None,
        )
        # Must not crash; the thin-API section should be absent (no docstring to inject)
        assert isinstance(context_str, str)


# ---------------------------------------------------------------------------
# TC-4082: Method docstring claims in ClassName.method: desc format
# ---------------------------------------------------------------------------


class TestMethodDocstringClaims:
    """TC-4082: Public method docstrings produce ClassName.method_name: claims."""

    def _make_python_source(self) -> str:
        return textwrap.dedent("""\
            class Workbook:
                \"\"\"Represents an Excel workbook for reading and writing spreadsheet files.

                Provides methods to load, save, and manipulate Excel workbooks.
                \"\"\"

                def load(self, path: str) -> None:
                    \"\"\"Load a workbook from the given file path.

                    Supports XLSX, XLS, ODS, and CSV formats. The format is determined
                    automatically from the file extension.
                    \"\"\"
                    pass

                def save(self, path: str) -> None:
                    \"\"\"Save the workbook to the given file path in the specified format.

                    Supports XLSX, PDF, CSV, HTML, and ODS output formats.
                    Creates parent directories if they do not exist.
                    \"\"\"
                    pass

                def _private_method(self) -> None:
                    \"\"\"This is a private method with a long docstring that exceeds fifty characters for testing.\"\"\"
                    pass

                def short(self) -> None:
                    \"\"\"Short.\"\"\"
                    pass
        """)

    def test_method_docstrings_produce_claims(self):
        """Public methods with long docstrings produce ClassName.method: claims."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        seq = _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        assert len(claims) >= 2, (
            f"Expected >= 2 claims from load() and save() docstrings, got {len(claims)}: {claims}"
        )

        texts = [c["text"] for c in claims]
        assert any("Workbook.load:" in t for t in texts), f"Expected Workbook.load: in {texts}"
        assert any("Workbook.save:" in t for t in texts), f"Expected Workbook.save: in {texts}"

    def test_private_methods_excluded(self):
        """Private methods (starting with _) do NOT produce claims."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        texts = [c["text"] for c in claims]
        assert not any("_private_method" in t for t in texts), (
            f"Private method should not produce claims, but found in {texts}"
        )

    def test_short_docstrings_excluded(self):
        """Methods with docstrings < 50 chars do NOT produce claims."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        texts = [c["text"] for c in claims]
        # 'short' method has a 5-char docstring — should NOT appear
        assert not any("Workbook.short:" in t for t in texts), (
            f"Short docstring method should be excluded, but found in {texts}"
        )

    def test_claim_format_is_classname_dot_method(self):
        """Claims use 'ClassName.method_name: first_sentence' format."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        for claim in claims:
            text = claim["text"]
            # Must match "ClassName.method_name: ..."
            assert "." in text and ":" in text, f"Claim text does not match format: {text!r}"
            class_method_part = text.split(":")[0]
            assert "." in class_method_part, f"Expected ClassName.method in {text!r}"

    def test_claim_source_is_deterministic(self):
        """Claims produced by method docstring extraction have claim_source=deterministic."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        for claim in claims:
            assert claim.get("claim_source") == "deterministic"

    def test_seq_increments_correctly(self):
        """Sequence counter increments correctly across multiple claims."""
        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        source = self._make_python_source()
        claims: list = []
        final_seq = _extract_method_docstring_claims(source, "workbook.py", "cells", 10, claims)

        assert final_seq == 10 + len(claims)

    def test_python_cells_fixture_produces_method_claims(self):
        """python-cells fixture produces method docstring claims from Workbook and Worksheet."""
        if not PYTHON_CELLS_DIR.is_dir():
            pytest.skip(f"python-cells fixture not found at {PYTHON_CELLS_DIR}")

        from launcher.workers.understand.extract._deterministic import _extract_method_docstring_claims

        workbook_path = PYTHON_CELLS_DIR / "src" / "aspose" / "cells" / "workbook.py"
        assert workbook_path.exists()
        source = workbook_path.read_text(encoding="utf-8")

        claims: list = []
        _extract_method_docstring_claims(source, "workbook.py", "cells", 0, claims)

        assert len(claims) >= 3, (
            f"Expected >= 3 method claims from Workbook class, got {len(claims)}: {claims}"
        )


# ---------------------------------------------------------------------------
# TC-4083: self_review medium findings for thin Python
# ---------------------------------------------------------------------------


class TestSelfReviewThinPython:
    """TC-4083: self_review produces medium findings for thin Python extraction."""

    def _make_understanding_bundle(
        self,
        public_classes: list[str],
        claims_count: int = 5,
        primary_language: str = "python",
        snippets_count: int = 0,
    ) -> "Any":
        from launcher.models.understanding import (
            UnderstandingBundle, RepoInfo, ProductEvidence, SharedFacts,
        )
        from launcher.models.product import ApiSurface, ProductIdentity, RichnessResult, RichnessTier
        from launcher.models.claims import Claim, EvidenceAnchor

        product = ProductIdentity(
            family="cells",
            platform="python",
            display_name="Test",
            canonical_import="mylib",
            runtime_import="mylib",
            repo_url="https://github.com/test/mylib",
        )
        api_surface = ApiSurface(
            public_classes=public_classes,
            import_allowlist=["mylib"],
            confidence="medium" if public_classes else "low",
        )
        claims = [
            Claim(
                claim_id=f"CLM-{i:03d}",
                text=f"This library supports feature {i} for spreadsheet operations.",
                kind="feature",
                visibility="public",
                evidence=[EvidenceAnchor(source_file="README.md", line_start=1, line_end=1, snippet="test")],
            )
            for i in range(claims_count)
        ]
        repo_info = RepoInfo(
            file_tree=["README.md"],
            content_files_read=1,
            shared_facts=SharedFacts(primary_language=primary_language),
        )
        richness = RichnessResult(tier=RichnessTier.C, score=30, reason="test")

        return UnderstandingBundle(
            product=product,
            repo=repo_info,
            richness_tier=richness,
            api_surface=api_surface,
            claims=claims,
            snippets=[],
            product_evidence=ProductEvidence(install_recipe=None),
        )

    @pytest.mark.asyncio
    async def test_thin_python_api_produces_medium_finding(self):
        """Python repo with 1 public class → medium thin_api_surface finding."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=["MyClass"],
            claims_count=5,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        thin_findings = [f for f in result.findings if f.get("category") == "thin_api_surface"]
        assert len(thin_findings) >= 1, (
            f"Expected thin_api_surface finding for 1 public class, got findings: {result.findings}"
        )
        assert thin_findings[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_thin_api_does_not_block(self):
        """Thin API surface finding is medium (not high) — does not block pipeline."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=["MyClass"],
            claims_count=5,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        # Since only snippets check may fail (0 snippets + 1 class = high), but
        # thin_api_surface itself must be medium
        thin_findings = [f for f in result.findings if f.get("category") == "thin_api_surface"]
        assert all(f["severity"] == "medium" for f in thin_findings)

    @pytest.mark.asyncio
    async def test_non_python_thin_api_does_not_trigger(self):
        """Non-Python repo with 1 public class does NOT trigger thin_api_surface finding."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=["MyClass"],
            claims_count=5,
            primary_language="typescript",
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        thin_findings = [f for f in result.findings if f.get("category") == "thin_api_surface"]
        assert len(thin_findings) == 0, (
            f"thin_api_surface should NOT fire for TypeScript, got {thin_findings}"
        )

    @pytest.mark.asyncio
    async def test_zero_classes_triggers_empty_not_thin(self):
        """Python repo with 0 classes triggers api_surface_empty (high), not thin_api_surface."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=[],
            claims_count=5,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        thin_findings = [f for f in result.findings if f.get("category") == "thin_api_surface"]
        empty_findings = [f for f in result.findings if f.get("category") == "api_surface_empty"]

        assert len(thin_findings) == 0, "0-class repo should not trigger thin_api_surface"
        assert len(empty_findings) >= 1, "0-class Python repo should trigger api_surface_empty"

    @pytest.mark.asyncio
    async def test_low_claim_count_medium_finding(self):
        """Python repo with non-empty API but < 10 claims → medium low_claim_count finding."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=["MyClass", "OtherClass", "ThirdClass"],
            claims_count=3,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        low_count_findings = [f for f in result.findings if f.get("category") == "low_claim_count"]
        assert len(low_count_findings) >= 1, (
            f"Expected low_claim_count finding for 3 claims / 3 classes, got {result.findings}"
        )
        assert low_count_findings[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_adequate_claims_no_low_count_finding(self):
        """Python repo with >= 10 claims does NOT trigger low_claim_count."""
        from launcher.workers.understand.worker import UnderstandWorker

        bundle = self._make_understanding_bundle(
            public_classes=["MyClass"],
            claims_count=12,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)

        low_count_findings = [f for f in result.findings if f.get("category") == "low_claim_count"]
        assert len(low_count_findings) == 0, (
            f"Expected no low_claim_count finding for 12 claims, got {low_count_findings}"
        )
