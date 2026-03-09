"""API surface extraction: AST-based public class and import allowlist discovery."""
from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path

from launcher.models.product import ApiSurface, ClassBrief, ProductIdentity

logger = logging.getLogger(__name__)


_INTERNAL_CLASS_MARKERS = {
    "FND", "FNDX", "Chunk", "Reference32", "Reference64",
    "GlobalIdTable", "Hashed", "BinaryReader", "BinaryWriter",
    "FileNode", "TransactionEntry", "ObjectSpace",
}


def _is_internal_class(cls_name: str, export_allowlist: frozenset[str] | None = None) -> bool:
    """Heuristic: class names containing implementation markers are internal.

    When export_allowlist is provided and non-empty, a class not present
    in the exported symbol set is also considered internal (GAP-06: works
    for any Python product, not just Aspose).
    Marker check is always applied as a fast fallback.
    """
    for marker in _INTERNAL_CLASS_MARKERS:
        if marker in cls_name:
            return True
    if export_allowlist and cls_name not in export_allowlist:
        return True
    return False


def _extract_exported_names(init_path: Path) -> frozenset[str]:
    """Extract bare exported symbol names from a Python __init__.py.

    Strategy 1: use __all__ (high-confidence).
    Strategy 2: use re-exported names from ``from X import Y`` statements.
    Returns empty frozenset when neither is available (no filtering applied).
    """
    names: set[str] = set()
    try:
        source = init_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return frozenset()

    # Strategy 1: __all__
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.add(elt.value)

    # Strategy 2: re-exports (only when __all__ absent)
    if not names:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.names:
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name and not name.startswith("_"):
                        names.add(name)

    return frozenset(names)


def _is_submodule_only_allowlist(allowlist: frozenset[str], package_root_dir: Path) -> bool:
    """Return True if every name in the allowlist is a subdirectory of package_root_dir.

    Used to detect Python namespace packages where __init__.py exports submodule
    names (e.g. frozenset({'threed'})) rather than class names.
    """
    if not allowlist:
        return False
    return all((package_root_dir / name).is_dir() for name in allowlist)


def _file_under_package_root(src_file: Path, repo_dir: Path, package_root: str) -> bool:
    """Check if a source file is under the detected package root.

    Also excludes _internal directories anywhere in the path (AQ-healing).
    Returns False when no package root is detected — prevents example-only
    repos from polluting the API surface.
    """
    if not package_root:
        return False  # no root detected → reject all (prevents example-repo contamination)
    try:
        rel = src_file.relative_to(repo_dir)
        rel_str = str(rel).replace("\\", "/")
        if not rel_str.startswith(package_root.replace("\\", "/")):
            return False
        # Exclude _internal, _private, internal directories
        parts = rel.parts
        if any(part.startswith("_internal") or part == "internal" for part in parts):
            return False
        return True
    except ValueError:
        return False


def _extract_api_surface(repo_dir: Path, product: ProductIdentity) -> ApiSurface:
    """Extract API surface from source files (multi-language).

    Uses code_analyzer.analyze_file_safe() which dispatches to the right
    parser per language (Python AST, JS/TS/Go/C# regex).

    Applies three contamination filters:
    1. Package-path: only files under package_root
    2. Canonical-import prefix: module import path must start with product prefix
    3. Internal-class heuristic: FND/Chunk/Reference markers excluded

    Returns an ApiSurface with public_classes, class_briefs, and import_allowlist.
    """
    from launcher.shared.code_analyzer import analyze_file_safe, _compute_import_path, _first_sentence

    public_classes: list[str] = []
    class_briefs: list[ClassBrief] = []
    api_identifiers: set[str] = set()
    import_allowlist: list[str] = []
    confidence: str = "low"

    source_files = _find_source_files(repo_dir)
    if not source_files:
        return ApiSurface(
            public_classes=public_classes,
            import_allowlist=import_allowlist,
            confidence="low",
        )

    package_root = _detect_package_root(repo_dir)

    # Build export allowlist from __init__.py for product-agnostic internal-class detection (GAP-06)
    _export_allowlist: frozenset[str] | None = None
    if package_root:
        _init_path = repo_dir / package_root / "__init__.py"
        if _init_path.exists():
            _export_allowlist = _extract_exported_names(_init_path) or None

        # Bug 1a fix: namespace package — allowlist contains submodule names, not class names.
        # Example: aspose/__init__.py exports {'threed'}; recurse into aspose/threed/__init__.py.
        # while loop with depth cap 3 handles multi-level nesting.
        if _export_allowlist:
            _pkg_root_path = repo_dir / package_root
            _depth = 0
            while _depth < 3 and _is_submodule_only_allowlist(_export_allowlist, _pkg_root_path):
                _first_submod = next(iter(sorted(_export_allowlist)))  # sorted for determinism
                _sub_dir = _pkg_root_path / _first_submod
                _sub_init = _sub_dir / "__init__.py"
                if not _sub_init.exists():
                    break
                _deeper = _extract_exported_names(_sub_init)
                if not _deeper:
                    break
                _export_allowlist = _deeper
                _pkg_root_path = _sub_dir
                _depth += 1

    # Derive canonical prefix for import-path filtering
    # e.g. "aspose.cells" → "aspose", "aspose_note_foss" → "aspose_note_foss"
    canonical_prefix = product.canonical_import.split(".")[0] if product.canonical_import else ""
    # Also accept underscore variant: aspose.cells → aspose_cells
    canonical_prefix_underscore = canonical_prefix.replace(".", "_") if canonical_prefix else ""

    # Determine source roots for _compute_import_path
    source_roots = ["src/"] if (repo_dir / "src").is_dir() else [""]

    # Two-pass approach: first try with canonical-import filter, fall back if empty
    def _file_passes_filters(src_file: Path, use_import_filter: bool) -> bool:
        if not _file_under_package_root(src_file, repo_dir, package_root):
            return False
        if use_import_filter and src_file.suffix == ".py" and canonical_prefix:
            import_path = _compute_import_path(src_file, repo_dir, source_roots)
            if not (
                import_path.startswith(canonical_prefix)
                or import_path.startswith(canonical_prefix_underscore)
                or import_path.startswith(product.canonical_import)
            ):
                return False
        return True

    # Try strict filtering first; fall back to package-root-only if no files pass
    filtered_files = [f for f in source_files if _file_passes_filters(f, True)]
    if not filtered_files:
        filtered_files = [f for f in source_files if _file_passes_filters(f, False)]

    # Filter stage counters for observability (GAP-08)
    _total_files = len(source_files)
    _package_root_files = sum(1 for f in source_files if _file_passes_filters(f, False))
    _import_filtered_files = len(filtered_files)
    _total_raw_classes = 0
    _internal_filtered_count = 0

    for src_file in filtered_files:
        result = analyze_file_safe(src_file, repo_dir=repo_dir)
        if not result:
            continue
        for cls_entry in result.get("classes", []):
            # classes may be dicts ({"name": ..., ...}) or plain strings
            cls_name = cls_entry["name"] if isinstance(cls_entry, dict) else cls_entry
            if not isinstance(cls_name, str) or cls_name.startswith("_"):
                continue

            _total_raw_classes += 1

            # Filter 3: Internal-class heuristic (markers + export reachability when available)
            if _is_internal_class(cls_name, _export_allowlist):
                _internal_filtered_count += 1
                continue

            public_classes.append(cls_name)
            api_identifiers.add(cls_name)

            # Build ClassBrief from rich analyzer data
            if isinstance(cls_entry, dict):
                methods: list[str] = []
                for m in cls_entry.get("methods", []):
                    mname = m if isinstance(m, str) else m.get("name", "")
                    if mname and not mname.startswith("_"):
                        api_identifiers.add(mname)
                        methods.append(mname)
                properties: list[str] = []
                for p in cls_entry.get("properties", []):
                    pname = p if isinstance(p, str) else p.get("name", "")
                    if pname and not pname.startswith("_"):
                        api_identifiers.add(pname)
                        properties.append(pname)
                docstring_raw = cls_entry.get("docstring", "")
                docstring_snippet = _first_sentence(docstring_raw) if docstring_raw else ""

                class_briefs.append(ClassBrief(
                    name=cls_name,
                    docstring_snippet=docstring_snippet,
                    methods=methods[:10],
                    properties=properties[:10],
                ))

    # Build import allowlist (platform-aware)
    import_allowlist = _build_import_allowlist(repo_dir, package_root, product)

    # Determine confidence
    if public_classes and import_allowlist:
        confidence = "high"
    elif public_classes or import_allowlist:
        confidence = "medium"
    else:
        confidence = "low"

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_classes: list[str] = []
    for cls in sorted(public_classes):
        if cls not in seen:
            seen.add(cls)
            unique_classes.append(cls)

    # Deduplicate class_briefs by name (keep first occurrence)
    seen_briefs: set[str] = set()
    unique_briefs: list[ClassBrief] = []
    for brief in class_briefs:
        if brief.name not in seen_briefs:
            seen_briefs.add(brief.name)
            unique_briefs.append(brief)

    # Cap api_identifiers to avoid token bloat
    sorted_ids = sorted(api_identifiers)[:500]

    # Filter stage observability log (GAP-08)
    logger.info(
        "api_surface_filter: total_files=%d, package_root_files=%d, import_filtered=%d",
        _total_files, _package_root_files, _import_filtered_files,
    )
    logger.info(
        "api_surface_classes: total=%d, internal_filtered=%d, public=%d, briefs=%d",
        _total_raw_classes, _internal_filtered_count, len(unique_classes), len(unique_briefs),
    )

    return ApiSurface(
        public_classes=unique_classes,
        import_allowlist=sorted(set(import_allowlist)),
        confidence=confidence,
        api_identifiers=sorted_ids,
        class_briefs=unique_briefs,
    )


# -- Source file discovery (multi-language) --------------------------------

_CODE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".mjs", ".ts", ".tsx", ".jsx",
    ".java", ".cs", ".go", ".rs", ".rb", ".php",
}

_EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", "dist", "build", ".eggs", ".mypy_cache", "target",
}


def _find_source_files(repo_dir: Path, max_files: int = 300) -> list[Path]:
    """Discover source files for API surface extraction (all languages)."""
    files: list[Path] = []
    for src_file in sorted(repo_dir.rglob("*")):
        if len(files) >= max_files:
            break
        if src_file.is_dir():
            continue
        if src_file.suffix.lower() not in _CODE_EXTENSIONS:
            continue
        parts = src_file.relative_to(repo_dir).parts
        if any(part in _EXCLUDE_DIRS for part in parts):
            continue
        # Skip test files
        if any(p.startswith("test") or p == "tests" or p == "spec" for p in parts):
            continue
        files.append(src_file)
    return files


# -- Multi-platform package root detection ---------------------------------


def _detect_package_root(repo_dir: Path) -> str:
    """Detect the main package directory (multi-platform).

    Python: __init__.py in src/ or root
    JS/TS: package.json main field
    Go: go.mod module path
    Java: src/main/java/ convention
    C#: *.csproj location
    Rust: src/lib.rs
    """
    # Python: src/<package>/__init__.py
    src_dir = repo_dir / "src"
    if src_dir.is_dir():
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return f"src/{child.name}"

    # Python: root-level package with __init__.py
    for child in sorted(repo_dir.iterdir()):
        if child.is_dir() and child.name != "tests" and (child / "__init__.py").exists():
            return child.name

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

    # Node/TS: package.json main field
    pkg_json = repo_dir / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            main = data.get("main", "") or data.get("module", "")
            if main:
                candidate = str(Path(main).parent) if "/" in main else ""
                if candidate and (repo_dir / candidate).is_dir():
                    return candidate
                # Bug 1b fix: dist/ missing in sparse checkout — fall back to src/
                src_dir = repo_dir / "src"
                if src_dir.is_dir() and any(src_dir.rglob("*.ts")):
                    return "src"
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


# -- Import allowlist (multi-platform) ------------------------------------


def _build_import_allowlist(
    repo_dir: Path,
    package_root: str,
    product: ProductIdentity,
) -> list[str]:
    """Build the import allowlist (multi-platform).

    Python: __init__.py __all__ or re-exports
    JS/TS: package.json exports or main
    Go: go.mod module path
    Java: package declarations
    C#: namespace declarations
    Others: canonical import only
    """
    allowlist: list[str] = []

    # Always include the canonical import
    if product.canonical_import:
        allowlist.append(product.canonical_import)

    if not package_root:
        return allowlist

    # Python: parse __init__.py
    init_path = repo_dir / package_root / "__init__.py"
    if init_path.exists():
        allowlist.extend(_python_allowlist_from_init(init_path, package_root))
        return allowlist

    # Node/TS: package.json exports
    pkg_json = repo_dir / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            name = data.get("name", "")
            if name:
                allowlist.append(name)
            exports = data.get("exports", {})
            if isinstance(exports, dict):
                for key in exports:
                    if key != "." and isinstance(key, str):
                        allowlist.append(f"{name}/{key.lstrip('./')}")
        except Exception:
            pass
        return allowlist

    # Go: module path from go.mod
    go_mod = repo_dir / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
            if match:
                allowlist.append(match.group(1))
        except Exception:
            pass
        return allowlist

    # For other languages (Java, C#, Rust, etc.), use TreeSitter to
    # extract public/exported names.  No lang_tag gate — the Python/JS/Go
    # cascades above already return early for those ecosystems.
    src_root = repo_dir / package_root
    if src_root.is_dir():
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
                # Stop after gathering enough exports (canonical_import + 10)
                if len(allowlist) > 10:
                    break
        except ImportError:
            pass

        # Regex fallback for Java package / C# namespace when TreeSitter
        # yielded nothing beyond canonical_import
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
