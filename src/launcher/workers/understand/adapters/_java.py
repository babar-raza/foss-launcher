"""Java platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TC-JAVA-401: Javadoc extraction helpers
# ---------------------------------------------------------------------------

# Matches a Java annotation line (e.g. @Deprecated, @Override, @SuppressWarnings(...))
# but NOT Javadoc tags inside a comment block (those start with * @param, etc.)
_JAVA_ANNOTATION_RE = re.compile(r"^\s*@[A-Z]")

# Javadoc tag lines to strip from extracted text
_JAVADOC_TAG_RE = re.compile(
    r"^\s*@(?:param|return|returns|throws|exception|see|since|deprecated|author|version|serial|link)\b"
)


def _count_params_in_line(line: str) -> int:
    """Count the number of parameters in a Java method declaration line.

    TC-JAVA-411: Extracts the text between the first ``(`` and its matching
    ``)`` and counts parameters by splitting on commas (accounting for
    generics nesting like ``Map<K, V>``).  Returns -1 if the parentheses
    cannot be found, signalling the caller to fall back to name-only matching.
    """
    open_idx = line.find("(")
    if open_idx < 0:
        return -1
    # Find matching close paren, respecting angle-bracket nesting
    depth = 0
    close_idx = -1
    for i in range(open_idx + 1, len(line)):
        ch = line[i]
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == ")" and depth <= 0:
            close_idx = i
            break
    if close_idx < 0:
        return -1
    inner = line[open_idx + 1 : close_idx].strip()
    if not inner:
        return 0
    # Split on commas that are NOT inside angle brackets
    count = 1
    depth = 0
    for ch in inner:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "," and depth <= 0:
            count += 1
    return count


def _extract_javadoc_comment(lines: list[str], declaration_line_idx: int) -> str:
    """Extract ``/** ... */`` Javadoc comment preceding a declaration.

    TC-JAVA-401: Walks backwards from *declaration_line_idx - 1*,
    skipping blank lines and Java annotation lines (``@Deprecated`` etc.),
    looking for a ``*/`` ... ``/**`` block.  Strips Javadoc delimiters,
    leading ``*``, and Javadoc tag lines (``@param``, ``@return``, etc.).
    Returns clean plain text or empty string if no Javadoc found.
    """
    if declaration_line_idx <= 0:
        return ""

    scan_limit = max(0, declaration_line_idx - 30)

    # Phase 1: skip annotations and blank lines to find the closing */
    block_end_idx = -1
    for i in range(declaration_line_idx - 1, scan_limit - 1, -1):
        stripped = lines[i].strip()
        if stripped == "" or _JAVA_ANNOTATION_RE.match(lines[i]):
            continue
        if stripped.endswith("*/"):
            block_end_idx = i
            break
        # Not blank, not annotation, not end-of-block — no Javadoc
        return ""

    if block_end_idx < 0:
        return ""

    # Phase 2: collect lines from block_end_idx backward until we find /**
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

    # Phase 3: strip delimiters and clean up
    cleaned: list[str] = []
    for line in collected:
        s = line.strip()
        # Strip opening delimiter
        if s.startswith("/**"):
            s = s[3:]
        # Strip closing delimiter
        if s.endswith("*/"):
            s = s[:-2]
        # Strip leading * (continuation lines)
        if s.startswith("*"):
            s = s[1:]
        s = s.strip()
        # Skip Javadoc tag lines
        if _JAVADOC_TAG_RE.match(s):
            continue
        if s:
            cleaned.append(s)

    if not cleaned:
        return ""

    raw = " ".join(cleaned)
    # Collapse whitespace
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


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
        """Detect Java source root from Maven/Gradle conventions.

        SR-07: For multi-module Maven repos, returns the module root whose
        pom.xml <artifactId> best matches canonical_import. Falls back to
        the shortest path (closest to repo root) when no match found.
        """
        # Find all src/main/java directories (multi-module support)
        all_java_roots = sorted(repo_dir.glob("**/src/main/java"))

        if all_java_roots:
            if len(all_java_roots) == 1:
                result = str(all_java_roots[0].relative_to(repo_dir)).replace("\\", "/")
                logger.debug("[Java] detect_package_root: 1 candidate, selected %s", result)
                return result

            # Multi-module: rank by pom.xml artifactId match to canonical_import
            canonical = (product.canonical_import or "").lower().replace("-", ".").replace("_", ".")
            scored: list[tuple[int, str]] = []
            for java_root in all_java_roots:
                rel = str(java_root.relative_to(repo_dir)).replace("\\", "/")
                score = 0
                # Check for sibling pom.xml (three levels up: src/main/java → module root)
                module_dir = java_root.parent.parent.parent
                pom = module_dir / "pom.xml"
                if pom.exists():
                    try:
                        pom_content = pom.read_text(encoding="utf-8", errors="replace")
                        artifact_m = re.search(r"<artifactId>\s*([^<]+)\s*</artifactId>", pom_content)
                        if artifact_m:
                            artifact = artifact_m.group(1).strip().lower().replace("-", ".").replace("_", ".")
                            if canonical and (canonical in artifact or artifact in canonical):
                                score += 10
                    except Exception:
                        pass
                # Prefer shorter paths (closer to repo root)
                score -= len(java_root.parts)
                scored.append((score, rel))

            scored.sort(key=lambda x: (-x[0], x[1]))
            result = scored[0][1]
            logger.debug("[Java] detect_package_root: %d candidates, selected %s", len(all_java_roots), result)
            return result

        # Gradle: app/src/main/java
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

        TC-JAVA-401: Enriches results with full Javadoc comments on both paths.
        """
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            result = _ts_analyzer.analyze_file(file_path, language="java", repo_dir=repo_dir)
            if result.classes:
                return self._enrich_with_javadoc_comments(file_path, result.classes)
        except Exception:
            logger.warning("ts_analyzer failed for %s, falling back to code_analyzer", file_path)

        # Fallback: code_analyzer.analyze_file_safe() delegates to ts_analyzer
        # internally with .java → "java" mapping.
        from launcher.shared.code_analyzer import analyze_file_safe
        result_dict = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not result_dict:
            return []
        classes = result_dict.get("classes", [])
        return self._enrich_with_javadoc_comments(file_path, classes)

    def _enrich_with_javadoc_comments(
        self,
        file_path: Path,
        classes: list[dict],
    ) -> list[dict]:
        """TC-JAVA-401: Populate ``docstring`` from ``/** ... */`` Javadoc blocks.

        Reads the source file, locates each class/interface/enum declaration,
        and extracts the preceding Javadoc block.  Only enriches classes/methods
        that don't already have a non-empty docstring.  Mirrors the .NET
        adapter's ``_enrich_with_xml_doc_comments()`` pattern (UND-02).
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
            r'(?:public|protected|private)\s+'
            r'(?:(?:static|final|abstract|strictfp)\s+)*'
            r'(?:class|interface|enum)\s+([A-Z]\w*)'
        )
        name_to_line: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = _decl_re.search(line)
            if m:
                name = m.group(1)
                if name not in name_to_line:
                    name_to_line[name] = i

        # Map method names to line indices (for method docstring enrichment)
        _method_re = re.compile(
            r'(?:public|protected|private)\s+'
            r'(?:(?:static|final|abstract|synchronized|native)\s+)*'
            r'(?:[\w<>\[\],\s]+?)\s+(\w+)\s*\('
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
                    doc = _extract_javadoc_comment(lines, line_idx)
                    if doc:
                        cls["docstring"] = doc
                        enriched += 1

            # Enrich method docstrings
            # TC-JAVA-411: use parameter-count matching for overloaded methods
            for md in cls.get("method_details", []):
                if md.get("docstring_snippet") or md.get("docstring"):
                    continue
                mname = md.get("name", "")
                if not mname:
                    continue
                candidates = method_lines.get(mname, [])
                expected_params = len(md.get("parameters", []))

                # First pass: find candidate whose param count matches
                best_doc = ""
                fallback_doc = ""
                for ml in candidates:
                    doc = _extract_javadoc_comment(lines, ml)
                    if not doc:
                        continue
                    if not fallback_doc:
                        fallback_doc = doc
                    line_param_count = _count_params_in_line(lines[ml])
                    if line_param_count >= 0 and line_param_count == expected_params:
                        best_doc = doc
                        break

                chosen = best_doc or fallback_doc
                if chosen:
                    md["docstring"] = chosen
                    md["docstring_snippet"] = chosen
                    enriched += 1

        if enriched:
            logger.info(
                "javadoc_comments [TC-JAVA-401]: enriched %d items with docstrings from %s",
                enriched, file_path.name,
            )

        return classes

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

        # SR-05: collect all distinct package declarations — remove the `break`
        # that previously returned only the first package found.
        _MAX_JAVA_PACKAGES = 20
        for java_file in sorted(src_root.rglob("*.java"))[:50]:
            try:
                content = java_file.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^package\s+([\w.]+)\s*;", content, re.MULTILINE)
                if match:
                    pkg = match.group(1)
                    if pkg not in allowlist:
                        allowlist.append(pkg)
                    if len(allowlist) >= _MAX_JAVA_PACKAGES:
                        break
            except Exception:
                continue

        return allowlist
