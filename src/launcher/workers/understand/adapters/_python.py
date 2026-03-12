"""Python platform adapter — wraps existing AST-based extraction."""
from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class PythonExtractor(PlatformExtractor):
    """Python adapter using the built-in AST-based code_analyzer.

    Wraps ``launcher.shared.code_analyzer.analyze_file_safe()`` which
    already produces full MethodSignature, PropertyRecord, and EnumRecord
    data for Python files.
    """

    @property
    def platform_id(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py", ".pyi"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect Python package root via __init__.py heuristic."""
        # src/<package>/__init__.py
        src_dir = repo_dir / "src"
        if src_dir.is_dir():
            for child in sorted(src_dir.iterdir()):
                if child.is_dir() and (child / "__init__.py").exists():
                    return f"src/{child.name}"

        # Root-level package with __init__.py
        for child in sorted(repo_dir.iterdir()):
            if child.is_dir() and child.name != "tests" and (child / "__init__.py").exists():
                return child.name

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Delegate to code_analyzer.analyze_file_safe() for Python files."""
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
        """Build Python import allowlist from __init__.py."""
        allowlist: list[str] = []
        primary_import = product.runtime_import or product.canonical_import
        if primary_import:
            allowlist.append(primary_import)

        if not package_root:
            return _normalize_runtime_imports(allowlist, product)

        init_path = repo_dir / package_root / "__init__.py"
        if init_path.exists():
            allowlist.extend(_python_allowlist_from_init(init_path, package_root))

        return _normalize_runtime_imports(allowlist, product)


def _python_allowlist_from_init(init_path: Path, package_root: str) -> list[str]:
    """Extract allowlist from Python __init__.py."""
    allowlist: list[str] = []
    try:
        source = init_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return allowlist

    base = package_root.replace("src/", "").replace("/", ".")

    # Strategy 1: parse __all__
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                allowlist.append(f"{base}.{elt.value}")

    # Strategy 2: ImportFrom targets
    if not allowlist:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.names:
                for alias in node.names:
                    if alias.name and not alias.name.startswith("_"):
                        allowlist.append(f"{base}.{alias.name}")

    return allowlist


def _normalize_runtime_imports(allowlist: list[str], product: ProductIdentity) -> list[str]:
    """Rewrite Python allowlist entries to runtime_import when one is defined."""
    runtime_import = product.runtime_import or ""
    canonical_import = product.canonical_import or ""
    if not runtime_import:
        return allowlist

    normalized: list[str] = []
    seen: set[str] = set()
    for entry in allowlist:
        if not entry:
            continue
        rewritten = entry
        if canonical_import and (entry == canonical_import or entry.startswith(f"{canonical_import}.")):
            rewritten = runtime_import + entry[len(canonical_import):]
        if rewritten not in seen:
            normalized.append(rewritten)
            seen.add(rewritten)
    return normalized
