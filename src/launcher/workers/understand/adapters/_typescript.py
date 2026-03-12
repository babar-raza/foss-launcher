"""TypeScript/JavaScript platform adapter — wraps existing tree-sitter extraction."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)

# Directories to probe for *.d.ts files when no explicit "types" field exists.
_DTS_PROBE_DIRS = ("types", "dist/types", "lib", "dist")


def _find_dts_root(repo_dir: Path, package_json_path: Path) -> list[Path]:
    """Discover TypeScript declaration (.d.ts) files for a package.

    Resolution order:
    1. ``package.json`` ``"types"`` or ``"typings"`` field (authoritative published entry).
    2. ``index.d.ts`` at the same directory as ``package.json``.
    3. ``index.d.ts`` inside a ``src/`` sub-directory.
    4. Any ``*.d.ts`` files found in standard output directories:
       ``types/``, ``dist/types/``, ``lib/``, ``dist/`` (relative to ``repo_dir``).

    Returns a de-duplicated list of existing ``.d.ts`` ``Path`` objects, or an
    empty list when none are found.  Never raises.
    """
    pkg_dir = package_json_path.parent
    found: list[Path] = []
    seen: set[Path] = set()

    def _add(p: Path) -> None:
        resolved = p.resolve()
        if resolved not in seen and p.exists():
            seen.add(resolved)
            found.append(p)

    # 1. Explicit "types" / "typings" field in package.json
    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8", errors="replace"))
        types_field = data.get("types") or data.get("typings")
        if types_field and isinstance(types_field, str):
            candidate = pkg_dir / types_field
            _add(candidate)
    except Exception:
        pass

    # 2. index.d.ts at package root
    _add(pkg_dir / "index.d.ts")

    # 3. index.d.ts inside src/
    _add(pkg_dir / "src" / "index.d.ts")

    # 4. Probe standard output directories for any *.d.ts files
    for probe in _DTS_PROBE_DIRS:
        probe_dir = repo_dir / probe
        if probe_dir.is_dir():
            for dts_file in sorted(probe_dir.rglob("*.d.ts")):
                _add(dts_file)

    return found


class TypeScriptExtractor(PlatformExtractor):
    """TypeScript/JS adapter wrapping the existing ts_analyzer.

    In Phase 2 this is a thin wrapper with no behavior change.
    Phase 3 enhances extraction depth (typed methods, properties, enums).
    Phase 4 (TC-4243) adds .d.ts declaration file support: when a package
    publishes ``.d.ts`` files, those are used as the authoritative API source
    instead of raw ``.ts`` implementation files.
    """

    @property
    def platform_id(self) -> str:
        return "typescript"

    @property
    def file_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".js", ".jsx", ".mjs"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect package root from package.json main/module field."""
        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                main = data.get("main", "") or data.get("module", "")
                if main:
                    candidate = str(Path(main).parent) if "/" in main else ""
                    if candidate and (repo_dir / candidate).is_dir():
                        return candidate
                    # Fallback: src/ directory
                    src_dir = repo_dir / "src"
                    if src_dir.is_dir() and any(src_dir.rglob("*.ts")):
                        return "src"
            except Exception:
                pass

        # Fallback: src/ if it has TS files
        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(src_dir.rglob("*.ts")):
            return "src"

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Extract typed class details from TypeScript/JavaScript source files.

        TC-4243: When the package publishes ``.d.ts`` declaration files, those
        are parsed first as the authoritative public API surface.  Only when no
        ``.d.ts`` files are found does the adapter fall back to parsing the raw
        ``.ts`` / ``.js`` implementation file passed in ``file_path``.

        Phase 3: explicitly dispatches to ts_analyzer with language="typescript"
        so typed method signatures, typed properties, and enum records are always
        populated from the tree-sitter AST — not dependent on file-extension dispatch.

        Falls back to code_analyzer.analyze_file_safe() when ts_analyzer returns
        no classes (e.g. grammar unavailable or empty file).
        """
        # TC-4243: Check for .d.ts declaration files first.
        # package.json may live at repo_dir/package.json or alongside file_path.
        pkg_json = repo_dir / "package.json"
        if not pkg_json.exists():
            # Try finding package.json in the same directory as file_path
            candidate = file_path.parent / "package.json"
            if candidate.exists():
                pkg_json = candidate

        dts_files: list[Path] = []
        if pkg_json.exists():
            dts_files = _find_dts_root(repo_dir, pkg_json)

        if dts_files:
            # Parse the first (most authoritative) .d.ts file, then merge any
            # additional ones.  All use language="typescript" — .d.ts files
            # are valid TypeScript syntax understood by the tree-sitter grammar.
            all_classes: list[dict] = []
            seen_names: set[str] = set()
            try:
                from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
                for dts_path in dts_files:
                    try:
                        result = _ts_analyzer.analyze_file(
                            dts_path, language="typescript", repo_dir=repo_dir
                        )
                        for cls in result.classes:
                            name = cls.get("name", "")
                            if name and name not in seen_names:
                                seen_names.add(name)
                                all_classes.append(cls)
                    except Exception:
                        logger.debug(
                            "ts_analyzer failed for .d.ts file %s, skipping", dts_path
                        )
            except Exception:
                logger.debug("ts_analyzer unavailable for .d.ts parsing")

            if all_classes:
                return all_classes
            # If .d.ts parsing yielded nothing, fall through to normal path below.

        # Determine language from file extension (tsx/jsx treated as typescript)
        suffix = file_path.suffix.lower()
        language = "typescript" if suffix in (".ts", ".tsx", ".d.ts") else "javascript"

        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            result = _ts_analyzer.analyze_file(file_path, language=language, repo_dir=repo_dir)
            if result.classes:
                return result.classes
        except Exception:
            logger.debug("ts_analyzer failed for %s, falling back to code_analyzer", file_path)

        # Fallback: code_analyzer.analyze_file_safe() also delegates to ts_analyzer
        # internally but handles edge cases and extension-to-language mapping.
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
        """Build import allowlist from package.json exports."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

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
