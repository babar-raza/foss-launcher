"""C++ platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class CppExtractor(PlatformExtractor):
    """C++ adapter for header/source extraction.

    Detects package root from CMakeLists.txt or include/ directories,
    builds header-based import allowlist, and delegates class extraction
    to code_analyzer (regex fallback for C++ since tree-sitter C++ may
    not be available).
    """

    @property
    def platform_id(self) -> str:
        return "cpp"

    @property
    def file_extensions(self) -> list[str]:
        return [".cpp", ".hpp", ".h", ".cc", ".cxx", ".hxx"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect C++ source root from common project layouts."""
        # include/ directory (header-only or library)
        include_dir = repo_dir / "include"
        if include_dir.is_dir():
            return "include"

        # src/ with C++ files
        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(
            src_dir.rglob(f"*{ext}") for ext in (".cpp", ".hpp", ".h", ".cc")
        ):
            return "src"

        # Rust-style: src/lib.rs equivalent — not applicable for C++
        # CMakeLists.txt at root suggests root is the package
        cmake = repo_dir / "CMakeLists.txt"
        if cmake.exists():
            return ""  # root itself is the package

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Delegate to code_analyzer for C++ files."""
        from launcher.shared.code_analyzer import analyze_file_safe

        result = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not result:
            return []
        return result.get("classes", [])

    def build_import_allowlist(
        self,
        repo_dir: Path,
        package_root: str,
        product: ProductIdentity,
    ) -> list[str]:
        """Build import allowlist from C++ header file names."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        if not package_root:
            return allowlist

        src_root = repo_dir / package_root
        if not src_root.is_dir():
            return allowlist

        # Collect public header names as import identifiers
        for header in sorted(src_root.rglob("*.h"))[:50]:
            try:
                rel = header.relative_to(repo_dir)
                # Convert to include path: include/aspose/scene.h → aspose/scene.h
                allowlist.append(str(rel).replace("\\", "/"))
                if len(allowlist) > 10:
                    break
            except ValueError:
                continue

        return allowlist
