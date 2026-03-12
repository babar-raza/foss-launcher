"""Java platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class JavaExtractor(PlatformExtractor):
    """Java adapter using tree-sitter Java grammar.

    Detects package root from Maven/Gradle conventions, builds
    package-based import allowlist, and delegates class extraction
    to code_analyzer.
    """

    @property
    def platform_id(self) -> str:
        return "java"

    @property
    def file_extensions(self) -> list[str]:
        return [".java"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect Java source root from Maven/Gradle conventions."""
        # Maven: src/main/java
        java_root = repo_dir / "src" / "main" / "java"
        if java_root.is_dir():
            return "src/main/java"

        # Gradle: may use same convention or app/src/main/java
        app_java = repo_dir / "app" / "src" / "main" / "java"
        if app_java.is_dir():
            return "app/src/main/java"

        # Fallback: src/ with .java files
        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(src_dir.rglob("*.java")):
            return "src"

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Extract typed class details from Java source files.

        Explicitly dispatches to ts_analyzer with language="java" so typed
        method signatures, typed properties, and enum records are populated
        from the tree-sitter Java grammar — not dependent on file-extension
        dispatch in code_analyzer.

        Falls back to code_analyzer.analyze_file_safe() when ts_analyzer
        returns no classes (e.g. grammar unavailable or empty file).
        """
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            result = _ts_analyzer.analyze_file(file_path, language="java", repo_dir=repo_dir)
            if result.classes:
                return result.classes
        except Exception:
            logger.debug("ts_analyzer failed for %s, falling back to code_analyzer", file_path)

        # Fallback: code_analyzer.analyze_file_safe() delegates to ts_analyzer
        # internally with .java → "java" mapping.
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
        """Build import allowlist from Java package declarations."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        if not package_root:
            return allowlist

        src_root = repo_dir / package_root
        if not src_root.is_dir():
            return allowlist

        # Extract package declarations from .java files
        for java_file in sorted(src_root.rglob("*.java"))[:50]:
            try:
                content = java_file.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^package\s+([\w.]+)\s*;", content, re.MULTILINE)
                if match:
                    pkg = match.group(1)
                    if pkg not in allowlist:
                        allowlist.append(pkg)
                    break  # One package is usually the base
            except Exception:
                continue

        return allowlist
