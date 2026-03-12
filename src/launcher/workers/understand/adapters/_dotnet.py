""".NET/C# platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class DotNetExtractor(PlatformExtractor):
    """.NET/C# adapter using tree-sitter C# grammar.

    Detects package root from .csproj files, builds namespace-based
    import allowlist, and delegates class extraction to code_analyzer.
    """

    @property
    def platform_id(self) -> str:
        return "dotnet"

    @property
    def file_extensions(self) -> list[str]:
        return [".cs"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect package root from .csproj file location."""
        csproj_files = list(repo_dir.glob("**/*.csproj"))
        if csproj_files:
            # Use first .csproj location as package root
            return str(csproj_files[0].parent.relative_to(repo_dir))

        # Fallback: src/ directory with .cs files
        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(src_dir.rglob("*.cs")):
            return "src"

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Extract typed class details from C# source files.

        Explicitly dispatches to ts_analyzer with language="csharp".  In
        ts_analyzer._LANG_PACK_ALIASES, "csharp" maps to the sentinel
        "_c_sharp_separate", which loads the ``tree_sitter_c_sharp`` package
        (installed separately from tree-sitter-language-pack).

        This ensures typed method signatures, typed properties, and enum records
        are populated from the tree-sitter C# grammar rather than relying on
        file-extension dispatch.

        Falls back to code_analyzer.analyze_file_safe() when ts_analyzer
        returns no classes (e.g. grammar unavailable or empty file).
        """
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            # "csharp" resolves via _LANG_PACK_ALIASES to "_c_sharp_separate"
            # which uses the tree_sitter_c_sharp package.
            result = _ts_analyzer.analyze_file(file_path, language="csharp", repo_dir=repo_dir)
            if result.classes:
                return result.classes
        except Exception:
            logger.debug("ts_analyzer failed for %s, falling back to code_analyzer", file_path)

        # Fallback: code_analyzer.analyze_file_safe() delegates to ts_analyzer
        # internally with .cs → "csharp" mapping.
        from launcher.shared.code_analyzer import analyze_file_safe
        result_dict = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not result_dict:
            return []
        return result_dict.get("classes", [])

    def build_import_allowlist(
        self,
        repo_dir: Path,
        package_root: str,
        product: ProductIdentity,
    ) -> list[str]:
        """Build import allowlist from C# namespace declarations."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        if not package_root:
            return allowlist

        src_root = repo_dir / package_root
        if not src_root.is_dir():
            return allowlist

        # Extract namespace declarations from .cs files
        for cs_file in sorted(src_root.rglob("*.cs"))[:50]:
            try:
                content = cs_file.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
                if match:
                    ns = match.group(1)
                    if ns not in allowlist:
                        allowlist.append(ns)
                    break  # One namespace is usually enough
            except Exception:
                continue

        return allowlist
