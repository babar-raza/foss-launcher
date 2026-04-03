"""C++ platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TC-CPP-402: Doxygen comment extraction helpers
# ---------------------------------------------------------------------------

# Matches C++ Doxygen triple-slash lines: /// text
_DOXYGEN_TRIPLE_RE = re.compile(r"^\s*///\s?(.*)")

# Doxygen command tags to strip entirely (content not useful for docstring)
_DOXYGEN_TAG_RE = re.compile(
    r"^\s*[@\\](?:param|return|returns|throws|exception|see|since|deprecated|"
    r"note|warning|author|version|details|remark|sa|retval|tparam)\b"
)


def _extract_doxygen_comment(lines: list[str], declaration_line_idx: int) -> str:
    """Extract Doxygen comment (``///`` or ``/** */``) preceding a declaration.

    TC-CPP-402: Handles both triple-slash and block-style Doxygen comments.
    Strips Doxygen command tags (``@brief``, ``\\param``, etc.) and returns
    clean plain text.  Returns empty string if no Doxygen comment found.
    """
    if declaration_line_idx <= 0:
        return ""

    scan_limit = max(0, declaration_line_idx - 30)

    # Try triple-slash (///) first — walk backward collecting consecutive lines
    triple_collected: list[str] = []
    for i in range(declaration_line_idx - 1, scan_limit - 1, -1):
        m = _DOXYGEN_TRIPLE_RE.match(lines[i])
        if m:
            triple_collected.append(m.group(1))
        else:
            stripped = lines[i].strip()
            if stripped == "":
                continue
            break

    if triple_collected:
        triple_collected.reverse()
        cleaned: list[str] = []
        for line in triple_collected:
            s = line.strip()
            if _DOXYGEN_TAG_RE.match(s):
                continue
            # Strip leading @brief or \brief
            s = re.sub(r"^[@\\]brief\s+", "", s)
            if s:
                cleaned.append(s)
        if cleaned:
            raw = " ".join(cleaned)
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            return raw

    # Try block-style (/** ... */) — same algorithm as Java's _extract_javadoc_comment
    block_end_idx = -1
    for i in range(declaration_line_idx - 1, scan_limit - 1, -1):
        stripped = lines[i].strip()
        if stripped == "":
            continue
        if stripped.endswith("*/"):
            block_end_idx = i
            break
        return ""

    if block_end_idx < 0:
        return ""

    collected: list[str] = []
    found_start = False
    for i in range(block_end_idx, scan_limit - 1, -1):
        line = lines[i]
        collected.append(line)
        if "/**" in line:
            found_start = True
            break

    if not found_start:
        return ""

    collected.reverse()
    cleaned_block: list[str] = []
    for line in collected:
        s = line.strip()
        if s.startswith("/**"):
            s = s[3:]
        if s.endswith("*/"):
            s = s[:-2]
        if s.startswith("*"):
            s = s[1:]
        s = s.strip()
        # Strip Doxygen tags
        if _DOXYGEN_TAG_RE.match(s):
            continue
        s = re.sub(r"^[@\\]brief\s+", "", s)
        if s:
            cleaned_block.append(s)

    if not cleaned_block:
        return ""

    raw = " ".join(cleaned_block)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw

# SR-09: C++ namespace extraction pattern
_NS_RE = re.compile(r"\bnamespace\s+([\w:]+)\s*\{")

# SR-11: Format keywords for C++ document capability detection
_CPP_FORMAT_KEYWORDS: list[str] = [
    "PPTX", "PPT", "ODP", "POTX", "PPSX",          # Presentation
    "XLSX", "XLS", "CSV", "ODS",                     # Spreadsheet
    "DOCX", "DOC", "RTF", "ODT",                     # Word
    "PDF", "XPS", "TIFF", "PNG", "JPG", "JPEG", "SVG", "BMP", "GIF",  # Output
    "HTML", "MHTML", "EPS",                          # Web/other
    "FBX", "GLTF", "GLB", "OBJ", "STL", "3MF", "U3D",  # 3D
]


# SC-03 (TC-5323): Namespace suffixes that indicate internal/implementation detail.
# Namespaces matching these patterns must never appear in the public import allowlist.
_INTERNAL_NS_SUFFIXES: tuple[str, ...] = (
    "::Internal", "::Detail", "::Impl", "::Private", "::details",
)


def _is_internal_namespace(ns: str) -> bool:
    """Return True if a C++ namespace segment is implementation-internal (not public API)."""
    return any(
        ns == suffix.lstrip(":") or ns.endswith(suffix)
        for suffix in _INTERNAL_NS_SUFFIXES
    )


def _extract_cpp_namespace(header_path: Path) -> str:
    """Extract the first qualified namespace from a C++ header file.

    Returns a double-colon-separated namespace string (e.g. 'Aspose::Slides')
    or an empty string if no namespace is found.
    """
    try:
        content = header_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    namespaces = _NS_RE.findall(content)
    if not namespaces:
        return ""
    # Filter anonymous/internal namespaces and ALL_CAPS macro guards
    filtered = [
        ns for ns in namespaces
        if ns not in {"detail", "impl", "internal", "anonymous"}
        and not (ns == ns.upper() and len(ns) > 6)  # skip MACRO_STYLE identifiers
    ]
    if not filtered:
        return ""
    # If first two are simple (no "::"), join them as qualified namespace
    if len(filtered) >= 2 and "::" not in filtered[0]:
        return f"{filtered[0]}::{filtered[1]}"
    return filtered[0]


class CppExtractor(PlatformExtractor):
    """C++ adapter for header/source extraction.

    Detects package root from CMakeLists.txt or include/ directories,
    builds header-based import allowlist, and delegates class extraction
    to tree-sitter (TC-4031) with code_analyzer regex as a fallback.
    """

    @property
    def platform_id(self) -> str:
        return "cpp"

    @property
    def file_extensions(self) -> list[str]:
        return [".cpp", ".hpp", ".h", ".cc", ".cxx", ".hxx"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect C++ source root from common project layouts.

        TC-CPP-405: For multi-module repos (multiple CMakeLists.txt), ranks
        by project_name/library_target match to canonical_import. Excludes
        test/example/build directories. Falls back to include/ or src/.
        """
        # TC-CPP-405: Multi-module CMake ranking
        _EXCLUDE_DIRS = {"test", "tests", "example", "examples", "sample",
                         "samples", "build", "cmake", "third_party", "thirdparty"}
        cmake_files = sorted(repo_dir.glob("**/CMakeLists.txt"))
        # Filter out excluded directories
        cmake_files = [
            f for f in cmake_files
            if not any(part.lower() in _EXCLUDE_DIRS for part in f.relative_to(repo_dir).parts[:-1])
        ]

        if len(cmake_files) > 1:
            from launcher.workers.scout.scout import _parse_cmake

            # Normalize for fuzzy matching: strip all separators
            def _norm(s: str) -> str:
                return s.lower().replace("::", "").replace(".", "").replace("-", "").replace("_", "")

            canonical = _norm(product.canonical_import or "")
            scored: list[tuple[int, str, Path]] = []
            for cmake in cmake_files:
                parsed = _parse_cmake(cmake)
                if not parsed:
                    continue
                score = 0
                project_name = _norm(parsed.get("project_name", ""))
                library_target = _norm(parsed.get("library_target", ""))
                if canonical and (
                    (project_name and (canonical in project_name or project_name in canonical))
                    or (library_target and (canonical in library_target or library_target in canonical))
                ):
                    score += 10
                # Prefer shorter paths (closer to root)
                rel = cmake.relative_to(repo_dir)
                score -= len(rel.parts)
                scored.append((score, str(rel), cmake))

            if scored:
                scored.sort(key=lambda x: (-x[0], x[1]))
                best_cmake = scored[0][2]
                best_dir = best_cmake.parent
                # Check for include/ or src/ relative to the best CMakeLists.txt
                inc = best_dir / "include"
                if inc.is_dir():
                    try:
                        return str(inc.relative_to(repo_dir)).replace("\\", "/")
                    except ValueError:
                        return "include"
                src = best_dir / "src"
                if src.is_dir():
                    try:
                        return str(src.relative_to(repo_dir)).replace("\\", "/")
                    except ValueError:
                        return "src"
                # Root of the best module
                try:
                    return str(best_dir.relative_to(repo_dir)).replace("\\", "/") or ""
                except ValueError:
                    return ""

        # Single CMake or no CMake: fall back to simple detection
        include_dir = repo_dir / "include"
        if include_dir.is_dir():
            return "include"

        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(
            src_dir.rglob(f"*{ext}") for ext in (".cpp", ".hpp", ".h", ".cc")
        ):
            return "src"

        cmake = repo_dir / "CMakeLists.txt"
        if cmake.exists():
            return ""

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """TC-4031/TC-CPP-402: Try tree-sitter C++ first; fall back to code_analyzer regex.

        Enriches results with full Doxygen comments on both paths.
        """
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts
            result = _ts.analyze_file(str(file_path), language="cpp", repo_dir=str(repo_dir))
            if result and result.classes:
                return self._enrich_with_doxygen_comments(file_path, result.classes)
        except Exception:
            logger.warning("cpp_ts_analyzer_failed, falling back to code_analyzer", exc_info=True)

        from launcher.shared.code_analyzer import analyze_file_safe
        raw = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not raw:
            return []
        classes = raw.get("classes", [])
        return self._enrich_with_doxygen_comments(file_path, classes)

    def _enrich_with_doxygen_comments(
        self,
        file_path: Path,
        classes: list[dict],
    ) -> list[dict]:
        """TC-CPP-402: Populate ``docstring`` from Doxygen ``///`` or ``/** */`` blocks.

        Reads the source file, locates each class/struct/enum declaration,
        and extracts the preceding Doxygen block. Only enriches items that
        don't already have a non-empty docstring. Mirrors the .NET adapter's
        ``_enrich_with_xml_doc_comments()`` pattern (UND-02).
        """
        if not classes:
            return classes

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return classes

        lines = content.splitlines()

        # Map class names to declaration line indices
        _decl_re = re.compile(
            r'(?:class|struct|enum\s+class|enum)\s+([A-Z]\w*)'
        )
        name_to_line: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = _decl_re.search(line)
            if m:
                name = m.group(1)
                if name not in name_to_line:
                    name_to_line[name] = i

        # Map method names to line indices (public methods)
        _method_re = re.compile(
            r'(?:virtual\s+|static\s+|inline\s+|constexpr\s+)*'
            r'(?:[\w:*&<>\s]+?)\s+(\w+)\s*\('
        )
        method_lines: dict[str, list[int]] = {}
        for i, line in enumerate(lines):
            m = _method_re.search(line)
            if m:
                mname = m.group(1)
                method_lines.setdefault(mname, []).append(i)

        enriched = 0
        for cls in classes:
            name = cls.get("name", "")
            # Enrich class docstring
            if name and not cls.get("docstring"):
                line_idx = name_to_line.get(name)
                if line_idx is not None:
                    doc = _extract_doxygen_comment(lines, line_idx)
                    if doc:
                        cls["docstring"] = doc
                        enriched += 1

            # Enrich method docstrings
            for md in cls.get("method_details", []):
                if md.get("docstring_snippet") or md.get("docstring"):
                    continue
                mname = md.get("name", "")
                if not mname:
                    continue
                candidates = method_lines.get(mname, [])
                for ml in candidates:
                    doc = _extract_doxygen_comment(lines, ml)
                    if doc:
                        md["docstring"] = doc
                        md["docstring_snippet"] = doc
                        enriched += 1
                        break

        if enriched:
            logger.info(
                "doxygen_comments [TC-CPP-402]: enriched %d items with docstrings from %s",
                enriched, file_path.name,
            )

        return classes

    def build_import_allowlist(
        self,
        repo_dir: Path,
        package_root: str,
        product: ProductIdentity,
    ) -> list[str]:
        """Build import allowlist from C++ namespace declarations and header files.

        SR-09/SR-10:
        - Extracts semantic namespace (e.g. Aspose::Slides) from public headers
        - Cap raised from 10 to 30; paths stripped of leading include/ prefix
        """
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        if not package_root:
            return allowlist

        src_root = repo_dir / package_root
        if not src_root.is_dir():
            return allowlist

        # Step 1: extract product namespace from .h then .hpp files.
        # SC-03 (TC-5323): Stop scanning as soon as we confirm the canonical namespace
        # is present — prevents accidentally adding ::Internal subnamespaces discovered
        # by scanning further headers just to find something "new" in the allowlist.
        # Also explicitly blocks any internal namespace variant.
        namespace = ""
        canonical_ns = product.canonical_import or ""

        def _try_add_namespace(ns: str) -> tuple[bool, bool]:
            """Returns (should_break, was_added).
            Break when canonical namespace is confirmed (even if already in list).
            Skip internal namespaces entirely.
            """
            nonlocal namespace
            if not ns:
                return False, False
            if _is_internal_namespace(ns):
                return False, False
            # Canonical namespace confirmed — stop scanning regardless
            if canonical_ns and (ns == canonical_ns or ns.startswith(canonical_ns + "::")):
                if ns not in allowlist:
                    allowlist.append(ns)
                namespace = ns
                return True, True
            if ns not in allowlist:
                allowlist.append(ns)
                namespace = ns
                return True, True
            return False, False

        for header in sorted(src_root.rglob("*.h"))[:10]:
            should_break, _ = _try_add_namespace(_extract_cpp_namespace(header))
            if should_break:
                break
        if not namespace:
            for header in sorted(src_root.rglob("*.hpp"))[:10]:
                should_break, _ = _try_add_namespace(_extract_cpp_namespace(header))
                if should_break:
                    break
        if namespace:
            logger.debug("[Cpp] namespace=%s in allowlist", namespace)

        # Step 2: canonical header include paths — strip include/ prefix
        # SR-02/TC-5312: Skip headers under _internal/ directories — they are not public API.
        for header in sorted(src_root.rglob("*.h"))[:50]:
            if len(allowlist) >= 30:
                break
            try:
                rel = header.relative_to(src_root)
                include_path = str(rel).replace("\\", "/")
                if "_internal/" in include_path or include_path.startswith("_internal"):
                    continue
                if include_path not in allowlist:
                    allowlist.append(include_path)
            except ValueError:
                continue

        return allowlist

    def detect_supported_formats_from_docs(
        self,
        readme_summary: str,
        doc_contents: list[str],
    ) -> list[str]:
        """SR-11: Detect supported file formats from README and doc text.

        Scans for known format identifiers (PPTX, PDF, etc.) in the provided
        text content. Returns a deduplicated list of detected format strings
        in uppercase.
        """
        combined = " ".join([readme_summary or ""] + (doc_contents or [])).upper()
        found: list[str] = []
        for fmt in _CPP_FORMAT_KEYWORDS:
            if fmt in combined and fmt not in found:
                found.append(fmt)
        return found
