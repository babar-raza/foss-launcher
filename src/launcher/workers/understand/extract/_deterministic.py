"""Deterministic claim extraction: markdown parsing, Python docstrings, error messages."""
from __future__ import annotations

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from launcher.models.claims import Claim, EvidenceAnchor
from launcher.models.product import ProductIdentity
from launcher.workers.understand.extract._filters import _is_junk_claim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claim kind keywords used by the deterministic fallback
# ---------------------------------------------------------------------------
_KIND_PATTERNS: list[tuple[str, list[str]]] = [
    ("install", ["install", "pip ", "setup", "requirements", "dependency"]),
    ("config", ["config", "setting", "option", "parameter", "environment"]),
    ("troubleshoot", ["error", "issue", "workaround", "fix", "debug"]),
    ("performance", ["performance", "benchmark", "speed", "latency", "throughput"]),
    ("license", ["license", "mit", "apache", "gpl", "bsd"]),
    ("format", ["format", "file type", "reads", "writes", "xlsx", "csv", "pdf"]),
    ("integration", ["integrat", "interop", "compat", "plugin", "extension"]),
    ("api", ["class", "function", "method", "property", "interface", "module"]),
    ("example", ["example", "usage", "demo", "sample", "tutorial"]),
    ("feature", []),  # default fallback
]

_SECTION_KIND_MAP: dict[str, str] = {
    "features": "feature", "key features": "feature", "highlights": "feature",
    "supported formats": "format", "file formats": "format", "supported file formats": "format",
    "installation": "install", "getting started": "install", "quick start": "install",
    "requirements": "install", "prerequisites": "install",
    "api reference": "api", "public api": "api",
    "examples": "example", "usage": "example", "code samples": "example",
}


def _extract_error_messages(code_content: str, source_file: str) -> list[Claim]:
    """Extract error messages from raise statements and Error classes.

    Ported from src/launcher/shared/extract_claims.py for v2.
    Extracts troubleshooting content from source code.

    Patterns:
    - raise ValueError("error message")
    - raise CustomError(f"error {variable}")
    - class CustomError(Exception): ...

    Args:
        code_content: Python source code
        source_file: Source file path

    Returns:
        List of troubleshooting Claim objects with error context
    """
    claims: list[Claim] = []

    def _make_id(key: str) -> str:
        digest = hashlib.md5(f"{source_file}:{key}".encode(), usedforsecurity=False).hexdigest()[:8]
        return f"CLM-err-{digest}"

    # Pattern 1: raise statements with string literals
    raise_pattern = r'raise\s+(\w+)\s*\(\s*[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(raise_pattern, code_content):
        error_class = match.group(1)
        error_message = match.group(2)

        # Filter out very short messages and code-like content
        if len(error_message) >= 10 and not re.search(r'[{}\[\]()=]', error_message):
            text = f"Error: {error_message} (raised as {error_class})"
            claims.append(Claim(
                claim_id=_make_id(text),
                text=text,
                kind="troubleshoot",
                visibility="public",
                evidence=[EvidenceAnchor(
                    source_file=source_file,
                    line_start=0,
                    line_end=0,
                    snippet=f'raise {error_class}("{error_message}")',
                )],
            ))

    # Pattern 2: Exception class definitions
    exception_pattern = r'class\s+(\w+Error|\w+Exception)\s*\([^)]*(?:Exception|Error)[^)]*\):'
    for match in re.finditer(exception_pattern, code_content):
        error_class = match.group(1)
        text = f"Custom error type: {error_class} indicates specific failure conditions"
        claims.append(Claim(
            claim_id=_make_id(error_class),
            text=text,
            kind="troubleshoot",
            visibility="public",
            evidence=[EvidenceAnchor(
                source_file=source_file,
                line_start=0,
                line_end=0,
                snippet=f"class {error_class}",
            )],
        ))

    return claims


def _extract_claims_deterministic(
    doc_contexts: list[dict[str, str]],
    product: ProductIdentity,
) -> list[dict[str, Any]]:
    """Deterministic fallback: parse markdown headings, bullets, and paragraphs as claims.

    Headings determine the claim ``kind``; bullet points under them become
    individual claim texts.  Paragraphs directly under headings are also
    captured as single claims.  Python docstrings from example files are
    also extracted.
    """
    claims: list[dict[str, Any]] = []
    family_slug = re.sub(r"[^a-z0-9]", "-", product.family.lower()).strip("-")
    seq = 0

    for ctx in doc_contexts:
        content = ctx["content"]
        source_file = ctx["path"]

        # For Python files, extract docstrings as claims
        if source_file.endswith(".py"):
            seq = _extract_claims_from_python(
                content, source_file, family_slug, seq, claims,
            )
            # Also mine error messages from Python source
            try:
                err_claims = _extract_error_messages(content, source_file)
                for claim in err_claims:
                    claims.append({
                        "claim_id": claim.claim_id,
                        "text": claim.text,
                        "kind": claim.kind,
                        "evidence": [
                            {
                                "source_file": ev.source_file,
                                "line_start": ev.line_start,
                                "line_end": ev.line_end,
                                "snippet": ev.snippet,
                            }
                            for ev in claim.evidence
                        ],
                        "visibility": claim.visibility,
                        "tier_relevance": "all",
                    })
                if err_claims:
                    logger.debug("error_message_claims=%d from %s", len(err_claims), source_file)
            except Exception:
                logger.warning("_extract_error_messages failed for %s", source_file, exc_info=True)
            continue

        lines = content.split("\n")
        current_heading = ""
        current_kind = "feature"
        in_code_fence = False

        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Track code fences — skip content inside them
            if stripped.startswith("```"):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence:
                continue

            # Detect headings
            heading_match = re.match(r"^(#{1,4})\s+(.+)", stripped)
            if heading_match:
                current_heading = heading_match.group(2).strip()
                current_kind = _classify_kind_from_text(current_heading)
                continue

            # Extract bullet points as claims
            bullet_match = re.match(r"^[-*+]\s+(.+)", stripped)
            if bullet_match:
                claim_text = bullet_match.group(1).strip()
                if _is_junk_claim(claim_text):
                    continue
                # Skip link-only bullets like "[text](url)"
                if re.match(r"^\[.*\]\(.*\)$", claim_text):
                    continue
                seq += 1
                claims.append({
                    "claim_id": f"CLM-{family_slug}-{seq:03d}",
                    "text": claim_text,
                    "kind": current_kind,
                    "evidence": [{
                        "source_file": source_file,
                        "line_start": line_idx,
                        "line_end": line_idx,
                        "snippet": stripped,
                    }],
                    "visibility": "public",
                    "tier_relevance": "all",
                })
                continue

            # Extract from markdown tables (feature tables in READMEs)
            table_match = re.match(r"^\|(.+)\|$", stripped)
            if table_match and current_heading:
                cells = [c.strip() for c in table_match.group(1).split("|")]
                cells = [c for c in cells if c and not re.match(r"^[-:]+$", c) and len(c) > 5]
                combined = " -- ".join(cells)
                if len(combined) >= 25 and not _is_junk_claim(combined):
                    seq += 1
                    claims.append({
                        "claim_id": f"CLM-{family_slug}-{seq:03d}",
                        "text": combined,
                        "kind": current_kind,
                        "evidence": [{"source_file": source_file, "line_start": line_idx, "line_end": line_idx, "snippet": stripped}],
                        "visibility": "public",
                        "tier_relevance": "all",
                    })
                continue

            # Extract substantial paragraphs (non-empty, non-heading, >= 30 chars)
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith("```")
                and not stripped.startswith("[")  # skip link lines
                and len(stripped) >= 30
                and current_heading
            ):
                # Split on sentence boundaries and extract individual claims
                sentences = re.split(r"\.\s+", stripped)
                for sent in sentences:
                    sent = sent.strip().rstrip(".")
                    if len(sent) >= 20 and not _is_junk_claim(sent):
                        seq += 1
                        claims.append({
                            "claim_id": f"CLM-{family_slug}-{seq:03d}",
                            "text": sent,
                            "kind": current_kind,
                            "evidence": [{
                                "source_file": source_file,
                                "line_start": line_idx,
                                "line_end": line_idx,
                                "snippet": stripped,
                            }],
                            "visibility": "public",
                            "tier_relevance": "all",
                        })

    # If no claims found from docs, extract from README summary as last resort
    if not claims:
        logger.warning("No claims from docs; extracting from README headings")
        for ctx in doc_contexts:
            if "readme" in ctx["path"].lower():
                lines = ctx["content"].split("\n")
                for line_idx, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    heading_match = re.match(r"^(#{1,4})\s+(.+)", stripped)
                    if heading_match:
                        heading_text = heading_match.group(2).strip()
                        if len(heading_text) >= 10:
                            seq += 1
                            claims.append({
                                "claim_id": f"CLM-{family_slug}-{seq:03d}",
                                "text": heading_text,
                                "kind": _classify_kind_from_text(heading_text),
                                "evidence": [{"source_file": ctx["path"], "line_start": line_idx, "line_end": line_idx, "snippet": stripped}],
                                "visibility": "public",
                                "tier_relevance": "all",
                            })

    return claims


def _extract_claims_from_python(
    content: str,
    source_file: str,
    family_slug: str,
    seq: int,
    claims: list[dict[str, Any]],
) -> int:
    """Extract claims from Python file docstrings, comments, and filenames."""
    # Extract claim from descriptive filename (e.g. "ConvertToPDF.py" -> feature claim)
    filename = Path(source_file).stem
    if filename and not filename.startswith("_") and len(filename) >= 8:
        # Convert CamelCase to readable text
        readable = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", filename)
        readable = readable.replace("_", " ").strip()
        if len(readable) >= 10:
            seq += 1
            kind = _classify_kind_from_text(readable)
            claims.append({
                "claim_id": f"CLM-{family_slug}-{seq:03d}",
                "text": f"The library supports: {readable}",
                "kind": kind,
                "evidence": [{"source_file": source_file, "line_start": 1, "line_end": 1, "snippet": filename}],
                "visibility": "public",
                "tier_relevance": "all",
            })

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return seq

    for node in ast.walk(tree):
        docstring = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            docstring = ast.get_docstring(node)

        if docstring and len(docstring) >= 20:
            # Use first sentence as claim text
            first_line = docstring.split("\n")[0].strip()
            if len(first_line) >= 15:
                kind = "example"
                if isinstance(node, ast.ClassDef):
                    kind = "api"
                seq += 1
                claims.append({
                    "claim_id": f"CLM-{family_slug}-{seq:03d}",
                    "text": first_line,
                    "kind": kind,
                    "evidence": [{
                        "source_file": source_file,
                        "line_start": getattr(node, "lineno", 0),
                        "line_end": getattr(node, "end_lineno", 0),
                        "snippet": first_line,
                    }],
                    "visibility": "public",
                    "tier_relevance": "all",
                })

    return seq


# ---------------------------------------------------------------------------
# Format matrix extraction (TC-HYBRID-03)
# ---------------------------------------------------------------------------

_FORMAT_EXTENSIONS: dict[str, str] = {
    # 3D formats
    "OBJ": ".obj", "FBX": ".fbx", "GLTF": ".gltf", "GLB": ".glb",
    "STL": ".stl", "DAE": ".dae", "COLLADA": ".dae", "3DS": ".3ds",
    "USD": ".usd", "USDA": ".usda", "USDC": ".usdc", "USDZ": ".usdz",
    "DXF": ".dxf", "DWG": ".dwg", "IFC": ".ifc", "STEP": ".step",
    "IGES": ".iges", "PLY": ".ply", "X3D": ".x3d",
    # Document formats
    "PDF": ".pdf", "DOCX": ".docx", "DOC": ".doc", "XLSX": ".xlsx",
    "XLS": ".xls", "PPTX": ".pptx", "PPT": ".ppt",
    "HTML": ".html", "MHTML": ".mhtml", "RTF": ".rtf", "TXT": ".txt",
    "CSV": ".csv", "TSV": ".tsv", "ODS": ".ods", "ODT": ".odt",
    # Image formats
    "PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg", "BMP": ".bmp",
    "TIFF": ".tiff", "GIF": ".gif", "SVG": ".svg", "WEBP": ".webp",
    # Note formats
    "ONE": ".one", "ONETOC2": ".onetoc2",
}

# Header words to skip in README table parsing
_README_TABLE_SKIP_NAMES = frozenset({
    "FORMAT", "NAME", "TYPE", "EXT", "EXTENSION", "DESCRIPTION",
    "FILE", "FORMATS", "STATUS", "SUPPORT", "NOTES",
})

_FORMAT_REF_PATTERN = re.compile(
    r'\b(?:FileFormat|SaveFormat|LoadFormat|ExportFormat|ImportFormat)'
    r'\s*\.\s*([A-Z][A-Z0-9_]{1,15})\b'
)

# HG-12: Pattern to detect format names as string literals (e.g. "output.fbx", "model.obj")
# Matches quoted strings ending with a known file extension.
_FORMAT_STRING_PATTERN = re.compile(
    r'''["'](?:[^"']*\.)(fbx|obj|gltf|glb|stl|dae|3ds|usd|usda|usdc|usdz|dxf|dwg|ifc|
        step|iges|ply|x3d|pdf|docx|xlsx|pptx|html|rtf|csv|ods|odt|
        png|jpeg|jpg|bmp|tiff|gif|svg|webp|one)["']''',
    re.IGNORECASE | re.VERBOSE,
)

# HG-12: Pattern to detect format enum names as bare strings (e.g. "FBX", "OBJ")
_FORMAT_BARE_PATTERN = re.compile(
    r'["\'](FBX|OBJ|GLTF|GLB|STL|DAE|COLLADA|3DS|USD|USDA|DXF|DWG|IFC|STEP|IGES|PLY|X3D|'
    r'PDF|DOCX|XLSX|HTML|CSV|PNG|JPEG|JPG|BMP|TIFF)["\']'
)

_README_POSITIVE_RE = re.compile(r'[✓✔✅]|yes|supported|true', re.IGNORECASE)
_README_NEGATIVE_RE = re.compile(r'[✗✘❌]|no|unsupported|false', re.IGNORECASE)


def extract_format_matrix(
    repo_dir: Path,
    product: ProductIdentity,
) -> "list[FormatRecord]":
    """Scan test files and README tables to build a format capability matrix.

    Strategy:
    1. Scan test/example files for ``FileFormat.XXX`` patterns → count references
       and use context keywords to determine import/export capability.
    2. Scan README format tables for explicit can_import/can_export signals.
    3. Merge: source-code evidence beats README when both present.

    Returns a list of :class:`FormatRecord` instances.
    On any error: returns empty list (never raises).
    """
    from launcher.models.product import FormatRecord

    format_counts: dict[str, int] = {}
    format_context: dict[str, list[str]] = {}

    # Strategy 1: scan test/example files
    try:
        candidate_dirs = [
            repo_dir / "tests",
            repo_dir / "test",
            repo_dir / "examples",
            repo_dir / "samples",
            repo_dir / "demo",
        ]
        test_files: list[Path] = []
        for td in candidate_dirs:
            if td.is_dir():
                for ext in (".py", ".ts", ".cs", ".java"):
                    test_files.extend(sorted(td.rglob(f"*{ext}"))[:30])

        for tf in test_files[:80]:
            try:
                content = tf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in _FORMAT_REF_PATTERN.finditer(content):
                fmt = m.group(1).upper()
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
                # Capture surrounding line for context
                line_start = content.rfind("\n", 0, m.start()) + 1
                line_end = content.find("\n", m.end())
                if line_end < 0:
                    line_end = len(content)
                ctx_line = content[line_start:line_end].lower()
                format_context.setdefault(fmt, []).append(ctx_line)
    except Exception:
        logger.warning("extract_format_matrix: test scan failed", exc_info=True)

    # Strategy 3 (HG-12): scan source + doc files for file-extension string literals.
    # Handles Python SDKs that use extension strings like scene.save("output.fbx")
    # rather than FileFormat.FBX enum references.
    try:
        _ext_to_fmt: dict[str, str] = {
            v.lstrip(".").upper(): k for k, v in _FORMAT_EXTENSIONS.items()
            if v  # skip empty extensions
        }
        _src_candidate_dirs = [
            repo_dir / "src", repo_dir / "lib", repo_dir,
            repo_dir / "tests", repo_dir / "test",
            repo_dir / "examples", repo_dir / "samples",
            repo_dir / "docs",
        ]
        _src_files: list[Path] = []
        for _sd in _src_candidate_dirs:
            if not _sd.is_dir():
                continue
            for _ext in (".py", ".md", ".rst"):
                _src_files.extend(sorted(_sd.rglob(f"*{_ext}"))[:20])
        _src_files = list(dict.fromkeys(_src_files))[:120]  # deduplicate, cap at 120

        for _sf in _src_files:
            try:
                _content = _sf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            # Match extension-based string literals like "output.fbx"
            for _m in _FORMAT_STRING_PATTERN.finditer(_content):
                _ext_str = _m.group(1).upper()
                _fmt = _ext_to_fmt.get(_ext_str)
                if not _fmt:
                    continue
                format_counts[_fmt] = format_counts.get(_fmt, 0) + 1
                # Capture surrounding line for save/load context
                _ls = _content.rfind("\n", 0, _m.start()) + 1
                _le = _content.find("\n", _m.end())
                if _le < 0:
                    _le = len(_content)
                _ctx = _content[_ls:_le].lower()
                format_context.setdefault(_fmt, []).append(_ctx)
            # Match bare format name strings like "FBX", "OBJ"
            for _m in _FORMAT_BARE_PATTERN.finditer(_content):
                _fmt = _m.group(1).upper()
                if _fmt not in _FORMAT_EXTENSIONS:
                    continue
                format_counts[_fmt] = format_counts.get(_fmt, 0) + 1
                _ls = _content.rfind("\n", 0, _m.start()) + 1
                _le = _content.find("\n", _m.end())
                if _le < 0:
                    _le = len(_content)
                _ctx = _content[_ls:_le].lower()
                format_context.setdefault(_fmt, []).append(_ctx)
    except Exception:
        logger.warning("extract_format_matrix: source string scan failed", exc_info=True)

    # Strategy 2: README format table scanning
    readme_caps: dict[str, dict[str, bool]] = {}
    try:
        for readme_name in ("README.md", "README.rst", "docs/formats.md", "FORMATS.md"):
            readme_path = repo_dir / readme_name
            if not readme_path.exists():
                continue
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("|"):
                    continue
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                if len(cells) < 2:
                    continue
                fmt_name = cells[0].upper().replace(".", "").strip()
                # Skip header rows and known non-format names
                if fmt_name in _README_TABLE_SKIP_NAMES:
                    continue
                if re.match(r"^[-:=]+$", fmt_name):
                    continue
                if len(fmt_name) < 2 or len(fmt_name) > 12:
                    continue
                # Only accept known format names or short uppercase names
                if fmt_name not in _FORMAT_EXTENSIONS and not re.match(r"^[A-Z0-9]{2,8}$", fmt_name):
                    continue
                # Determine can_import from cells[1], can_export from cells[2]
                can_import = bool(_README_POSITIVE_RE.search(cells[1])) if len(cells) > 1 else False
                can_export = bool(_README_POSITIVE_RE.search(cells[2])) if len(cells) > 2 else False
                if can_import or can_export:
                    readme_caps[fmt_name] = {"can_import": can_import, "can_export": can_export}
    except Exception:
        logger.warning("extract_format_matrix: README scan failed", exc_info=True)

    # Build FormatRecord list
    all_formats = set(format_counts.keys()) | set(readme_caps.keys())
    records: list[FormatRecord] = []

    for fmt in sorted(all_formats):
        test_count = format_counts.get(fmt, 0)
        ctx_lines = format_context.get(fmt, [])
        combined_ctx = " ".join(ctx_lines).lower()

        # Heuristic: save/export/write context → can_export
        can_export_from_code = test_count > 0 and any(
            kw in combined_ctx for kw in ("save", "export", "write", "tosave")
        )
        # Heuristic: load/import/read/open context → can_import
        can_import_from_code = test_count > 0 and any(
            kw in combined_ctx for kw in ("load", "import", "read", "open", "from_file", "fromfile")
        )

        if fmt in readme_caps:
            # README explicit capability + code context as tiebreaker
            can_export = readme_caps[fmt]["can_export"] or can_export_from_code
            can_import = readme_caps[fmt]["can_import"] or can_import_from_code
        else:
            can_export = can_export_from_code
            can_import = can_import_from_code

        # Skip formats with zero evidence
        if test_count == 0 and fmt not in readme_caps:
            continue

        records.append(FormatRecord(
            name=fmt,
            extension=_FORMAT_EXTENSIONS.get(fmt, ""),
            can_import=can_import,
            can_export=can_export,
            test_count=test_count,
            source_evidence=str(repo_dir),
        ))

    logger.info(
        "extract_format_matrix: %d format records extracted for %s",
        len(records),
        product.family,
    )
    return records


def _classify_kind_from_text(text: str) -> str:
    """Map heading/claim text to a claim kind.

    Checks exact section heading matches first (via _SECTION_KIND_MAP),
    then falls back to keyword matching (via _KIND_PATTERNS).
    """
    lower = text.lower()
    # Exact heading match (strip leading # and whitespace)
    section_key = lower.strip("# ").strip()
    if section_key in _SECTION_KIND_MAP:
        return _SECTION_KIND_MAP[section_key]
    # Keyword fallback
    for kind, keywords in _KIND_PATTERNS:
        if keywords and any(kw in lower for kw in keywords):
            return kind
    return "feature"


# ---------------------------------------------------------------------------
# Install recipe extraction (TC-HYBRID-04)
# ---------------------------------------------------------------------------


def extract_install_recipe(
    repo_dir: "Path",
    product: "ProductIdentity",
) -> "Any | None":
    """Extract pip install command from project config files.

    Strategy (in priority order):
    1. pyproject.toml [project].name + version
    2. setup.cfg [metadata].name + version
    3. setup.py name=... argument
    4. requirements.txt — line matching canonical_import pattern
    5. Fallback — derive from canonical_import (aspose_3d_foss → aspose-3d-foss)

    Returns an InstallRecipe or None on complete failure.
    Never raises.
    """
    try:
        from launcher.models.understanding import InstallRecipe
    except ImportError:
        return None

    package_name = ""
    version_constraint = ""
    source_file = ""

    # Strategy 1: pyproject.toml
    pyproject_path = repo_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8", errors="replace")
            # Match [project] section, then name = "..." on following lines
            name_m = re.search(
                r'\[project\][^\[]*?\bname\s*=\s*["\']([^"\']+)["\']',
                content, re.DOTALL,
            )
            if name_m:
                package_name = name_m.group(1).strip()
                source_file = "pyproject.toml"
                ver_m = re.search(
                    r'\[project\][^\[]*?\bversion\s*=\s*["\']([^"\']+)["\']',
                    content, re.DOTALL,
                )
                if ver_m:
                    version_constraint = f">={ver_m.group(1).strip()}"
        except Exception:
            logger.debug("extract_install_recipe: pyproject.toml failed", exc_info=True)

    # Strategy 2: setup.cfg
    if not package_name:
        setupcfg = repo_dir / "setup.cfg"
        if setupcfg.exists():
            try:
                content = setupcfg.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'^name\s*=\s*(.+)$', content, re.MULTILINE)
                if m:
                    package_name = m.group(1).strip()
                    source_file = "setup.cfg"
                vm = re.search(r'^version\s*=\s*(.+)$', content, re.MULTILINE)
                if vm:
                    version_constraint = f">={vm.group(1).strip()}"
            except Exception:
                logger.debug("extract_install_recipe: setup.cfg failed", exc_info=True)

    # Strategy 3: setup.py
    if not package_name:
        setup_py = repo_dir / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    package_name = m.group(1).strip()
                    source_file = "setup.py"
            except Exception:
                logger.debug("extract_install_recipe: setup.py failed", exc_info=True)

    # Strategy 4: requirements.txt
    if not package_name and product.canonical_import:
        req = repo_dir / "requirements.txt"
        if req.exists():
            try:
                content = req.read_text(encoding="utf-8", errors="replace")
                slug = product.canonical_import.replace("_", "-").lower()
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if slug in line.lower().replace("_", "-"):
                        package_name = re.split(r"[>=<!]", line)[0].strip()
                        source_file = "requirements.txt"
                        break
            except Exception:
                logger.debug("extract_install_recipe: requirements.txt failed", exc_info=True)

    # Strategy 5: derive from canonical_import
    if not package_name and product.canonical_import:
        package_name = product.canonical_import.replace("_", "-")
        source_file = "derived"

    if not package_name:
        return None

    pip_cmd = f"pip install {package_name}"
    if version_constraint:
        pip_cmd = f"pip install {package_name}{version_constraint}"

    # Verification code
    runtime = getattr(product, "runtime_import", "") or product.canonical_import
    verification = f"import {runtime}\nprint('Installation successful')" if runtime else ""

    logger.info("extract_install_recipe: package=%s source=%s", package_name, source_file)
    return InstallRecipe(
        pip_command=pip_cmd,
        package_name=package_name,
        version_constraint=version_constraint,
        verification_code=verification,
        source_file=source_file,
    )


# ---------------------------------------------------------------------------
# TC-4002: Limitation extraction
# ---------------------------------------------------------------------------

# Patterns that signal a limitation in documentation
_LIMITATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'\b(?:not\s+(?:yet\s+)?(?:support|implement|available))', re.IGNORECASE),
    re.compile(r'\b(?:experimental|deprecated|partial(?:ly)?|unstable)\b', re.IGNORECASE),
    re.compile(r'\b(?:known\s+(?:issue|limitation|bug))', re.IGNORECASE),
    re.compile(r'\b(?:TODO|FIXME|HACK|XXX)\b'),
]

# Patterns in Python source that signal a limitation
_CODE_LIMITATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'raise\s+NotImplementedError'),
    re.compile(r'warnings\.warn\('),
    re.compile(r'#\s*(?:TODO|FIXME|HACK|XXX)\b'),
]


def extract_limitations(
    repo_dir: "Path",
    repo_info: "Any",
) -> "list":
    """Extract verified limitations from documentation and source code.

    Scans doc files for limitation signals and Python source for
    NotImplementedError / warnings.warn patterns.

    Returns list of LimitationEntry dicts (converted to model by caller).
    """
    from launcher.models.understanding import LimitationEntry

    limitations: list[LimitationEntry] = []
    seen: set[str] = set()

    # Scan documentation files
    doc_paths = getattr(repo_info, "doc_paths", []) or []
    for rel_path in doc_paths[:50]:  # cap scan budget
        full_path = repo_dir / rel_path
        if not full_path.exists() or full_path.stat().st_size > 500_000:
            continue
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or len(stripped) < 10:
                continue
            for pat in _LIMITATION_PATTERNS:
                if pat.search(stripped):
                    key = f"{rel_path}:{stripped[:80]}"
                    if key in seen:
                        break
                    seen.add(key)
                    # Extract feature name heuristic: first noun phrase before the trigger
                    feature = stripped[:60].split("not")[0].strip().rstrip(":").strip() or stripped[:40]
                    limitations.append(LimitationEntry(
                        feature=feature[:80],
                        constraint=stripped[:200],
                        status="warning",
                        source_file=rel_path,
                        source_line=i,
                        confidence="doc_stated",
                        quote=stripped[:200],
                    ))
                    break  # one match per line

    # Scan Python source for NotImplementedError / warnings.warn
    source_paths = getattr(repo_info, "source_paths", []) or []
    for rel_path in source_paths[:100]:
        if not rel_path.endswith(".py"):
            continue
        full_path = repo_dir / rel_path
        if not full_path.exists() or full_path.stat().st_size > 500_000:
            continue
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            for pat in _CODE_LIMITATION_PATTERNS:
                if pat.search(stripped):
                    key = f"{rel_path}:{i}"
                    if key in seen:
                        break
                    seen.add(key)
                    limitations.append(LimitationEntry(
                        feature=rel_path.split("/")[-1].replace(".py", ""),
                        constraint=stripped[:200],
                        status="unsupported" if "NotImplementedError" in stripped else "warning",
                        source_file=rel_path,
                        source_line=i,
                        confidence="ast_verified",
                        quote=stripped[:200],
                    ))
                    break

    logger.info("extract_limitations: found %d limitations", len(limitations))
    return limitations[:50]  # cap at 50


# ---------------------------------------------------------------------------
# TC-4002: Workflow example extraction
# ---------------------------------------------------------------------------

def extract_workflow_examples(
    repo_dir: "Path",
    repo_info: "Any",
    api_surface: "Any | None" = None,
) -> "list":
    """Extract real workflow patterns from test and example files.

    Looks for functions in test/example files that contain 3+ statements
    referencing API surface class names. Extracts function body as code.

    Returns list of WorkflowExample.
    """
    from launcher.models.understanding import WorkflowExample

    examples: list[WorkflowExample] = []
    # Collect API class names for matching
    api_names: set[str] = set()
    if api_surface:
        for cls in getattr(api_surface, "class_briefs", []) or []:
            api_names.add(cls.name.lower())
        for cls_name in getattr(api_surface, "public_classes", []) or []:
            api_names.add(cls_name.lower())

    # Scan test + example files
    scan_paths = list(getattr(repo_info, "test_paths", []) or [])
    scan_paths.extend(getattr(repo_info, "example_paths", []) or [])

    for rel_path in scan_paths[:50]:
        if not rel_path.endswith(".py"):
            continue
        full_path = repo_dir / rel_path
        if not full_path.exists() or full_path.stat().st_size > 200_000:
            continue
        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if len(node.body) < 3:
                continue
            # Get function source lines
            start = node.lineno
            end = node.end_lineno or start + len(node.body)
            if end - start > 50:
                continue  # skip very long functions

            lines = source.splitlines()[start - 1:end]
            func_text = "\n".join(lines)
            func_lower = func_text.lower()

            # Count API references
            if api_names:
                refs = sum(1 for name in api_names if name in func_lower)
                if refs < 1:
                    continue

            # Extract step names (method calls)
            steps: list[str] = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    steps.append(child.func.attr)

            docstring = ast.get_docstring(node) or ""
            title = docstring.split("\n")[0][:100] if docstring else node.name.replace("_", " ").title()

            examples.append(WorkflowExample(
                name=node.name,
                title=title,
                code=func_text,
                steps=steps[:20],
                language="python",
                source_file=rel_path,
                source_lines=(start, end),
            ))

            if len(examples) >= 10:
                break
        if len(examples) >= 10:
            break

    logger.info("extract_workflow_examples: found %d examples", len(examples))
    return examples
