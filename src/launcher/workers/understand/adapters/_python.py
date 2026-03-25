"""Python platform adapter — wraps existing AST-based extraction."""
from __future__ import annotations

import ast
import logging
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)

# Directories that are never a Python package root, regardless of contents.
_EXCLUDE_DIRS: frozenset[str] = frozenset({
    "tests", "test", "docs", "doc", "documentation",
    "scripts", "script", "build", "dist", "target",
    ".tox", "venv", ".venv", "env", ".env",
    "node_modules", "__pycache__", ".git",
    "examples", "example", "demo", "samples",
    "ci", ".github", ".circleci",
})


def _is_namespace_init(init_path: Path) -> bool:
    """Return True if __init__.py is empty or a namespace package shim.

    Uses AST parsing: a namespace init has no function/class definitions and no
    non-__future__ imports. More reliable than text-length heuristics which
    misclassify short but real __init__.py files.
    """
    try:
        text = init_path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return True
        tree = ast.parse(text)
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return False
        if isinstance(node, ast.Import):
            return False
        if isinstance(node, ast.ImportFrom):
            # Allow relative imports (from . import submodule) — namespace shim pattern.
            # node.level > 0 means relative; node.module is None for bare `from .`.
            if node.level > 0 and all(alias.name != "*" for alias in (node.names or [])):
                continue
            if node.module and node.module != "__future__":
                return False
    return True


def _derive_product_prefix(product: ProductIdentity) -> str:
    """Derive a filesystem-usable prefix from canonical_import or family.

    For dot-style imports (e.g. ``aspose.email_foss``) uses the first dot-segment.
    For underscore-style imports (e.g. ``aspose_email_foss``) uses the first
    underscore-segment as the namespace prefix (e.g. ``aspose``).  This handles
    PEP 420 namespace packages where the top-level dir has no ``__init__.py``.
    """
    primary = (product.canonical_import or product.family or "").lower()
    if "." in primary:
        first = primary.split(".")[0].replace("-", "_").replace(" ", "_")
    else:
        # Underscore-style: "aspose_email_foss" → namespace prefix "aspose"
        first = primary.split("_")[0].replace("-", "_")
    return first if len(first) > 2 else ""


class PythonExtractor(PlatformExtractor):
    """Python adapter using the built-in AST-based code_analyzer.

    Wraps ``launcher.shared.code_analyzer.analyze_file_safe()`` which
    already produces full MethodSignature, PropertyRecord, and EnumRecord
    data for Python files.

    Package root detection uses a three-strategy cascade:
    1. src/<package>/__init__.py (namespace packages detected via AST)
    2. Root-level <package>/__init__.py
    3. Heuristic fallback: any directory with .py files matching product prefix
    """

    @property
    def platform_id(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> list[str]:
        return [".py", ".pyi"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect Python package root via three-strategy cascade."""
        # Strategy 1: src/<package>/__init__.py (namespace-aware)
        src_dir = repo_dir / "src"
        if src_dir.is_dir():
            for child in sorted(src_dir.iterdir()):
                if not child.is_dir() or child.name in _EXCLUDE_DIRS:
                    continue
                init = child / "__init__.py"
                if init.exists():
                    if _is_namespace_init(init):
                        for subpkg in sorted(child.iterdir()):
                            if subpkg.is_dir() and (subpkg / "__init__.py").exists():
                                return f"src/{child.name}/{subpkg.name}"
                    return f"src/{child.name}"

        # Strategy 2: Root-level package with __init__.py
        for child in sorted(repo_dir.iterdir()):
            if not child.is_dir() or child.name in _EXCLUDE_DIRS:
                continue
            if (child / "__init__.py").exists():
                return child.name

        # Strategy 3: Heuristic fallback — any dir with .py files matching product prefix
        product_prefix = _derive_product_prefix(product)
        if product_prefix:
            for child in sorted(repo_dir.iterdir()):
                if not child.is_dir() or child.name in _EXCLUDE_DIRS:
                    continue
                if child.name.lower().startswith(product_prefix):
                    py_files = list(child.rglob("*.py"))[:1]
                    if py_files:
                        rel = str(child.relative_to(repo_dir)).replace("\\", "/")
                        logger.warning(
                            "[Python] No __init__.py found; using heuristic package root: %s "
                            "(strategy 3 — confidence is lower than __init__.py detection)",
                            rel,
                        )
                        return rel

        logger.warning(
            "[Python] Could not detect package root for %s/%s — API surface will be empty",
            getattr(product, "family", "?"),
            getattr(product, "platform", "?"),
        )
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
        classes = result.get("classes", [])
        for cls in classes:
            if not cls.get("method_details"):
                logger.debug(
                    "[Python] Class %r in %s has no method_details (stub or property-only class)",
                    cls.get("name", "?"),
                    file_path.name,
                )
        return classes

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
    """Extract allowlist from Python __init__.py using cumulative strategies.

    Strategy 1: __all__ — explicit public API declaration.
    Strategy 2: ImportFrom — always applied in addition to __all__ (cumulative).
    Both strategies run regardless; results are deduplicated.
    """
    allowlist: list[str] = []
    seen: set[str] = set()
    try:
        source = init_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return allowlist

    base = package_root.replace("src/", "").replace("/", ".")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                entry = f"{base}.{elt.value}"
                                if entry not in seen:
                                    allowlist.append(entry)
                                    seen.add(entry)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.names:
            for alias in node.names:
                if alias.name and not alias.name.startswith("_"):
                    entry = f"{base}.{alias.name}"
                    if entry not in seen:
                        allowlist.append(entry)
                        seen.add(entry)

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
