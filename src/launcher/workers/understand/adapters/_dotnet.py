""".NET/C# platform adapter."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


def _extract_xml_doc_comment(lines: list[str], declaration_line_idx: int) -> str:
    """Extract ``/// <summary>`` XML doc comment preceding a declaration.

    UND-02 (UND-G02): Walks backwards from ``declaration_line_idx - 1``,
    collecting consecutive ``///`` lines (up to 30 lines max). Strips XML
    tags and returns clean plain text.  Returns empty string if no doc
    comment is found.
    """
    if declaration_line_idx <= 0:
        return ""

    collected: list[str] = []
    _XML_DOC_RE = re.compile(r"^\s*///\s?(.*)")
    scan_limit = max(0, declaration_line_idx - 30)

    for i in range(declaration_line_idx - 1, scan_limit - 1, -1):
        m = _XML_DOC_RE.match(lines[i])
        if m:
            collected.append(m.group(1))
        else:
            # Allow blank lines or attribute lines between doc comment blocks
            stripped = lines[i].strip()
            if stripped.startswith("[") or stripped == "":
                continue
            break

    if not collected:
        return ""

    collected.reverse()
    raw = " ".join(collected)

    # Strip XML tags: <summary>, </summary>, <para>, <see cref="..."/>, etc.
    raw = re.sub(r"<[^>]+>", " ", raw)
    # Collapse whitespace
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


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
        """Detect package root from .csproj file location.

        TC-4306: Ranks multiple .csproj files to select the main library project:
        1. Exclude .csproj files in paths containing 'test' or 'Test'
        2. Exclude exe projects (<OutputType>Exe</OutputType>)
        3. Prefer <AssemblyName> or <PackageId> matching canonical_import
        4. Fall back to shortest relative path (closest to repo root)
        """
        csproj_files = sorted(repo_dir.glob("**/*.csproj"))
        if not csproj_files:
            # Fallback: src/ directory with .cs files
            src_dir = repo_dir / "src"
            if src_dir.is_dir() and any(src_dir.rglob("*.cs")):
                return "src"
            return ""

        canonical_import = (product.canonical_import or "").lower()

        candidates = []
        for csproj in csproj_files:
            try:
                rel = csproj.relative_to(repo_dir)
            except ValueError:
                rel = csproj
            rel_str = str(rel).replace("\\", "/").lower()

            # Exclude test projects
            parts_lower = [p.lower() for p in rel.parts]
            if any("test" in p for p in parts_lower):
                continue

            # Read csproj content
            try:
                content = csproj.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Exclude exe projects
            if re.search(r"<OutputType>\s*Exe\s*</OutputType>", content, re.IGNORECASE):
                continue

            # Score: higher is better
            score = 0

            # Prefer canonical_import match via AssemblyName or PackageId
            if canonical_import:
                for tag in ("AssemblyName", "PackageId"):
                    m = re.search(rf"<{tag}>\s*([^<]+)\s*</{tag}>", content, re.IGNORECASE)
                    if m:
                        val = m.group(1).strip().lower().replace("-", ".").replace("_", ".")
                        ci = canonical_import.lower().replace("-", ".").replace("_", ".")
                        if ci in val or val in ci or ci.startswith(val) or val.startswith(ci):
                            score += 10
                            break

            # Prefer shorter paths (closer to root)
            score -= len(rel.parts)

            candidates.append((score, rel_str, csproj))

        if not candidates:
            # All projects were test/exe — fall back to shortest non-test path
            for csproj in sorted(csproj_files, key=lambda p: len(p.parts)):
                try:
                    rel = csproj.relative_to(repo_dir)
                except ValueError:
                    rel = csproj
                parts_lower = [p.lower() for p in rel.parts]
                if not any("test" in p for p in parts_lower):
                    return str(rel.parent.relative_to(repo_dir)).replace("\\", "/")
            return str(csproj_files[0].parent.relative_to(repo_dir))

        # Sort by score descending, then by path alphabetically for stability
        candidates.sort(key=lambda x: (-x[0], x[1]))
        best_csproj = candidates[0][2]
        return str(best_csproj.parent.relative_to(repo_dir)).replace("\\", "/")

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Extract typed class details from C# source files.

        Explicitly dispatches to ts_analyzer with language="csharp".
        Filters to public types only and enriches with XML doc comments (UND-02).
        Falls back to code_analyzer.analyze_file_safe() when ts_analyzer
        returns no classes.
        """
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            result = _ts_analyzer.analyze_file(file_path, language="csharp", repo_dir=repo_dir)
            if result.classes:
                # Filter to public types only
                try:
                    src = file_path.read_text(encoding="utf-8", errors="replace")
                    _pub_type_re = re.compile(
                        r'public\s+(?:(?:partial|static|sealed|abstract)\s+)*'
                        r'(?:class|interface|struct|enum|record)\s+([A-Z]\w*)'
                    )
                    public_names = {m.group(1) for m in _pub_type_re.finditer(src)}
                    result_classes = [c for c in result.classes if c.get("name") in public_names]
                except Exception:
                    result_classes = result.classes
                # UND-02: Enrich with XML doc comments
                return self._enrich_with_xml_doc_comments(file_path, result_classes)
        except Exception:
            logger.warning("ts_analyzer failed for %s, falling back to code_analyzer", file_path)

        # Fallback: code_analyzer
        from launcher.shared.code_analyzer import analyze_file_safe
        result_dict = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not result_dict:
            classes: list[dict] = []
        else:
            classes = result_dict.get("classes", [])

        # Filter to public types
        try:
            src = file_path.read_text(encoding="utf-8", errors="replace")
            _pub_type_re = re.compile(
                r'public\s+(?:(?:partial|static|sealed|abstract)\s+)*'
                r'(?:class|interface|struct|enum|record)\s+([A-Z]\w*)'
            )
            public_names = {m.group(1) for m in _pub_type_re.finditer(src)}
            classes = [c for c in classes if c.get("name") in public_names]
        except Exception:
            pass

        # UND-02: Enrich with XML doc comments
        classes = self._enrich_with_xml_doc_comments(file_path, classes)

        return classes

    def _enrich_with_xml_doc_comments(
        self,
        file_path: Path,
        classes: list[dict],
    ) -> list[dict]:
        """UND-02: Populate ``docstring`` field from ``/// <summary>`` comments.

        Reads the source file, locates each class/interface/struct declaration,
        and extracts the preceding XML doc comment block.  Only enriches classes
        that don't already have a non-empty docstring.
        """
        if not classes:
            return classes

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return classes

        lines = content.splitlines()
        _decl_re = re.compile(
            r'(?:public|internal|protected|private)\s+'
            r'(?:(?:partial|static|sealed|abstract)\s+)*'
            r'(?:class|interface|struct|enum|record)\s+([A-Z]\w*)'
        )

        # Map class names to their declaration line indices
        name_to_line: dict[str, int] = {}
        for i, line in enumerate(lines):
            m = _decl_re.search(line)
            if m:
                name = m.group(1)
                if name not in name_to_line:  # first occurrence wins
                    name_to_line[name] = i

        enriched = 0
        for cls in classes:
            name = cls.get("name", "")
            if not name or cls.get("docstring"):
                continue
            line_idx = name_to_line.get(name)
            if line_idx is None:
                continue
            doc = _extract_xml_doc_comment(lines, line_idx)
            if doc:
                cls["docstring"] = doc
                enriched += 1

        if enriched:
            logger.info(
                "xml_doc_comments [UND-02]: enriched %d classes with docstrings from %s",
                enriched, file_path.name,
            )

        return classes

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

        # TC-4306: Extract ALL namespace declarations matching canonical_import prefix.
        canonical_prefix = ""
        if product.canonical_import:
            canonical_prefix = product.canonical_import.split(".")[0]

        for cs_file in sorted(src_root.rglob("*.cs"))[:100]:
            try:
                content = cs_file.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
                if match:
                    ns = match.group(1)
                    if canonical_prefix and not ns.startswith(canonical_prefix):
                        continue
                    if ns not in allowlist:
                        allowlist.append(ns)
            except Exception:
                continue
            if len(allowlist) >= 20:
                break

        return allowlist
