"""Generic fallback adapter for unsupported platforms."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class GenericExtractor(PlatformExtractor):
    """Fallback adapter for platforms without a dedicated extractor.

    Uses code_analyzer.analyze_file_safe() which dispatches to regex-based
    extraction for languages without AST/tree-sitter support. Returns
    class names and method names only — no typed members.
    """

    @property
    def platform_id(self) -> str:
        return "generic"

    @property
    def file_extensions(self) -> list[str]:
        return [".java", ".cs", ".go", ".rs", ".rb", ".php", ".cpp", ".h", ".hpp"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Multi-language package root detection fallback."""
        # Go: go.mod
        go_mod = repo_dir / "go.mod"
        if go_mod.exists():
            try:
                content = go_mod.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # Java: src/main/java convention
        java_root = repo_dir / "src" / "main" / "java"
        if java_root.is_dir():
            return "src/main/java"

        # C#: first *.csproj location
        csproj_files = list(repo_dir.glob("**/*.csproj"))
        if csproj_files:
            return str(csproj_files[0].parent.relative_to(repo_dir))

        # Rust: src/lib.rs
        if (repo_dir / "src" / "lib.rs").exists():
            return "src"

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Delegate to code_analyzer.analyze_file_safe() for generic files."""
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
        """Build minimal import allowlist for generic platforms."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        if not package_root:
            return allowlist

        src_root = repo_dir / package_root
        if not src_root.is_dir():
            return allowlist

        # Try tree-sitter exports
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            from launcher.workers.understand.file_classifier import LANG_BY_EXT

            _non_py = set(LANG_BY_EXT.keys()) - {".py", ".pyi"}
            for src_file in sorted(src_root.rglob("*"))[:100]:
                if not src_file.is_file() or src_file.suffix not in _non_py:
                    continue
                file_lang = LANG_BY_EXT.get(src_file.suffix, "")
                if not file_lang:
                    continue
                try:
                    code = src_file.read_text(encoding="utf-8", errors="replace")
                    exports = _ts_analyzer.extract_exports_from_code(code, file_lang)
                    allowlist.extend(exports)
                except Exception:
                    continue
                if len(allowlist) > 10:
                    break
        except ImportError:
            pass

        # Regex fallback for Java package / C# namespace
        if len(allowlist) <= 1:
            for java_file in sorted(src_root.rglob("*.java"))[:50]:
                try:
                    content = java_file.read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"^package\s+([\w.]+)\s*;", content, re.MULTILINE)
                    if match:
                        allowlist.append(match.group(1))
                        break
                except Exception:
                    continue
            for cs_file in sorted(src_root.rglob("*.cs"))[:50]:
                try:
                    content = cs_file.read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
                    if match:
                        allowlist.append(match.group(1))
                        break
                except Exception:
                    continue

        return allowlist
