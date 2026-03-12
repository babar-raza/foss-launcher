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
    ("computation", ["formula", "calculate", "compute", "math", "sum"]),
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
                claim_source="deterministic",
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
            claim_source="deterministic",
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
                        "claim_source": claim.claim_source,
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

    # TC-4082: Structured method-level docstring claims in "ClassName.method: desc" format.
    # This ensures thin repos (1 public class) produce N claims where N = documented public methods.
    seq = _extract_method_docstring_claims(content, source_file, family_slug, seq, claims)

    return seq


def _extract_method_docstring_claims(
    content: str,
    source_file: str,
    family_slug: str,
    seq: int,
    claims: list[dict[str, Any]],
) -> int:
    """Extract structured claims from public method docstrings (TC-4082).

    Produces claims in the format 'ClassName.method_name: first_sentence_of_docstring'.
    Only includes:
    - Public methods (name does not start with '_')
    - Docstrings longer than 50 characters
    - Methods on public classes (class name does not start with '_')

    This supplements the generic docstring extraction in _extract_claims_from_python
    by producing per-method claims with class context, improving coverage for thin
    Python repos where only 1-2 public classes exist.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return seq

    seen_texts: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        cls_name = node.name
        if cls_name.startswith("_"):
            continue

        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            method_name = child.name
            if method_name.startswith("_"):
                continue  # skip private/dunder methods

            docstring = ast.get_docstring(child)
            if not docstring or len(docstring) < 50:
                continue

            first_line = docstring.split("\n")[0].strip()
            if len(first_line) < 20:
                # Fall back to first 200 chars of docstring collapsed to one line
                first_line = " ".join(docstring.split())[:200].strip()

            claim_text = f"{cls_name}.{method_name}: {first_line}"

            if _is_junk_claim(claim_text):
                continue

            # Deduplicate within this file
            if claim_text in seen_texts:
                continue
            seen_texts.add(claim_text)

            seq += 1
            claims.append({
                "claim_id": f"CLM-{family_slug}-{seq:03d}",
                "text": claim_text,
                "kind": "api",
                "evidence": [{
                    "source_file": source_file,
                    "line_start": getattr(child, "lineno", 0),
                    "line_end": getattr(child, "end_lineno", 0),
                    "snippet": first_line[:100],
                }],
                "visibility": "public",
                "tier_relevance": "all",
                "claim_source": "deterministic",
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

# TC-4103 Strategy 4: detect format-specific class names (e.g. FbxSaveOptions, ObjLoadOptions)
# used by Python SDKs that expose format options via typed classes rather than FileFormat enums.
_FORMAT_OPTIONS_PATTERN = re.compile(
    r'\b(fbx|obj|gltf|glb|stl|dae|collada|3ds|usd|usda|usdc|usdz|dxf|dwg|ifc|'
    r'step|iges|ply|x3d|draco|amf|pdf|docx|doc|xlsx|xls|pptx|ppt|html|rtf|csv|'
    r'ods|odt|png|jpeg|jpg|bmp|tiff|gif|svg|webp|one)'
    r'(Save|Load|Import|Export)Options\b',
    re.IGNORECASE,
)

_README_POSITIVE_RE = re.compile(r'[✓✔✅]|yes|supported|true', re.IGNORECASE)
_README_NEGATIVE_RE = re.compile(r'[✗✘❌]|no|unsupported|false', re.IGNORECASE)

# TC-4092: Negative context signals — when these appear near a format mention,
# it indicates the format is NOT supported (documentation of limitations).
# Used to suppress false positives from string-scan strategies (2 and 3) when
# there is no Strategy 1 (enum reference) evidence for the format.
_FORMAT_NEGATIVE_CTX_RE = re.compile(
    r'\bnot\s+support|\bunsupported\b|\bno\s+support\b|'
    r'\bcannot\s+(?:export|import|load|save|read|write)\b|'
    r'\bdoes\s+not\s+(?:support|implement)\b|'
    r'\bnot\s+(?:implement|available)\b',
    re.IGNORECASE,
)


def extract_format_matrix(
    repo_dir: Path,
    product: ProductIdentity,
) -> "list[FormatRecord]":
    """Scan test files and README tables to build a format capability matrix.

    Strategy:
    1. Scan test/example files for ``FileFormat.XXX`` patterns → count references
       (tracked separately as ``enum_counts``) and use context keywords to determine
       import/export capability.
    2. Scan README format tables for explicit can_import/can_export signals.
    3. Scan source/doc files for file-extension string literals (e.g. ``"output.fbx"``)
       and bare format name strings (e.g. ``"FBX"``).
    4. Merge: source-code evidence beats README when both present.

    TC-4092 — Negative context filter:
    Formats detected ONLY by string-scan strategies (2/3) with no Strategy 1 (enum
    reference) evidence are suppressed when their context lines match
    ``_FORMAT_NEGATIVE_CTX_RE`` (e.g., "PDF is not supported"). This prevents false
    positives where error messages or documentation mentioning unsupported formats
    are picked up by string scans.

    Returns a list of :class:`FormatRecord` instances.
    On any error: returns empty list (never raises).
    """
    from launcher.models.product import FormatRecord

    format_counts: dict[str, int] = {}
    format_context: dict[str, list[str]] = {}
    # TC-4092: Track Strategy 1 (enum reference) hits separately so the negative
    # context filter can distinguish "seen only in string scans" from "has real code evidence".
    enum_counts: dict[str, int] = {}

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
                # TC-4092: Track enum-reference hits separately (Strategy 1 only)
                enum_counts[fmt] = enum_counts.get(fmt, 0) + 1
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
    # TC-4103: options_can_import/export initialised here so they are always defined
    # even if the try block raises before Strategy 4 runs.
    options_can_import: dict[str, bool] = {}
    options_can_export: dict[str, bool] = {}
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
                # TC-4096: Skip URL-embedded extensions (hyperlink targets, not format I/O).
                # e.g. "file:///C:/Documents/report.pdf" — the .pdf extension is a link
                # target, not evidence that the library reads/writes PDF files.
                if re.search(r'(?:file|http|https|ftp)://', _m.group(0), re.IGNORECASE):
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

        # Strategy 4 (TC-4103): scan for format-specific class names like FbxSaveOptions,
        # ObjLoadOptions. Used by Python SDKs that expose typed options classes rather than
        # FileFormat.XXX enum references (e.g. aspose-3d-foss Python).
        options_can_import = {}
        options_can_export = {}
        for _sf in _src_files:
            try:
                _content = _sf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for _m in _FORMAT_OPTIONS_PATTERN.finditer(_content):
                _fmt = _m.group(1).upper()
                _cap = _m.group(2).lower()  # "save", "load", "import", "export"
                if _cap in ("save", "export"):
                    options_can_export[_fmt] = True
                elif _cap in ("load", "import"):
                    options_can_import[_fmt] = True
        if options_can_import or options_can_export:
            logger.info(
                "extract_format_matrix: Strategy 4 found %d can_import + %d can_export formats",
                len(options_can_import), len(options_can_export),
            )
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
    all_formats = (
        set(format_counts.keys()) | set(readme_caps.keys())
        | set(options_can_import.keys()) | set(options_can_export.keys())
    )
    records: list[FormatRecord] = []

    for fmt in sorted(all_formats):
        test_count = format_counts.get(fmt, 0)
        ctx_lines = format_context.get(fmt, [])
        combined_ctx = " ".join(ctx_lines).lower()

        # TC-4092: Skip formats that have no Strategy 1 (enum reference) evidence AND
        # whose captured context lines contain negative signals (e.g. "PDF is not supported").
        # This eliminates false positives where Strategy 2/3 string scans match format names
        # in comments, error messages, or documentation describing unsupported formats.
        has_code_enum_evidence = enum_counts.get(fmt, 0) > 0
        if not has_code_enum_evidence and fmt not in readme_caps:
            if ctx_lines and any(_FORMAT_NEGATIVE_CTX_RE.search(line) for line in ctx_lines):
                logger.debug(
                    "extract_format_matrix: skipping %s — string-scan-only with negative context",
                    fmt,
                )
                continue

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
            can_export = readme_caps[fmt]["can_export"] or can_export_from_code or options_can_export.get(fmt, False)
            can_import = readme_caps[fmt]["can_import"] or can_import_from_code or options_can_import.get(fmt, False)
        else:
            can_export = can_export_from_code or options_can_export.get(fmt, False)
            can_import = can_import_from_code or options_can_import.get(fmt, False)

        # Skip formats with zero evidence
        if test_count == 0 and fmt not in readme_caps and fmt not in options_can_import and fmt not in options_can_export:
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
    shared_facts: "Any | None" = None,
) -> "Any | None":
    """Extract platform-appropriate install command from project manifest files.

    TC-4084: Dispatches to platform-specific extractors first, then falls back
    to Python strategies. This removes the Python bias in naming and coverage.

    Platform dispatch order:
    - TypeScript/JavaScript/Node → _extract_node_recipe (package.json → npm install)
    - Java → _extract_java_recipe (pom.xml → mvn dependency:get)
    - .NET → _extract_dotnet_recipe (*.csproj → dotnet add package)
    - Go → _extract_go_recipe (go.mod → go get)
    - Rust → _extract_rust_recipe (Cargo.toml → cargo add)
    - Ruby → _extract_ruby_recipe (Gemfile/gemspec → gem install)
    - PHP → _extract_php_recipe (composer.json → composer require)
    - Python or unknown → pyproject.toml / setup.cfg / setup.py / requirements.txt

    TC-4030: Pass shared_facts (from Scout's SharedFacts) to skip pyproject.toml disk read
    when the package name was already extracted by Scout in Phase A.

    Returns an InstallRecipe or None on complete failure. Never raises.
    """
    try:
        from launcher.models.understanding import InstallRecipe
    except ImportError:
        return None

    platform = getattr(product, "platform", "") or ""

    # TC-4084: Platform dispatch — non-Python platforms get their own extractor
    if platform in ("typescript", "javascript", "node"):
        recipe = _extract_node_recipe(repo_dir, product, shared_facts)
        if recipe:
            return recipe
    elif platform == "java":
        recipe = _extract_java_recipe(repo_dir, product)
        if recipe:
            return recipe
    elif platform in ("dotnet", "csharp", "net"):
        recipe = _extract_dotnet_recipe(repo_dir, product)
        if recipe:
            return recipe
    elif platform == "go":
        recipe = _extract_go_recipe(repo_dir, product)
        if recipe:
            return recipe
    elif platform == "rust":
        recipe = _extract_rust_recipe(repo_dir, product)
        if recipe:
            return recipe
    elif platform == "ruby":
        recipe = _extract_ruby_recipe(repo_dir, product)
        if recipe:
            return recipe
    elif platform == "php":
        recipe = _extract_php_recipe(repo_dir, product)
        if recipe:
            return recipe

    # Python or unknown → original strategies
    package_name = ""
    version_constraint = ""
    source_file = ""

    # TC-4030: Use cached SharedFacts from Scout if available (skip Strategy 1 disk read)
    if shared_facts is not None and getattr(shared_facts, "package_name", ""):
        package_name = shared_facts.package_name
        # TC-4084: Fix source_file label — use platform-appropriate file name
        if platform in ("typescript", "javascript", "node"):
            source_file = "package.json (cached)"
        else:
            source_file = "pyproject.toml (cached)"
        cached_ver = getattr(shared_facts, "version", "")
        if cached_ver:
            version_constraint = f">={cached_ver}"

    # Strategy 1: pyproject.toml (only if not already populated from shared_facts)
    if not package_name:
        pyproject_path = repo_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8", errors="replace")
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

    install_cmd = f"pip install {package_name}"
    if version_constraint:
        install_cmd = f"pip install {package_name}{version_constraint}"

    # Use runtime_import for Python verification code when available. The install
    # command remains package-oriented, but the verification snippet must reflect
    # the actual import path the generated code and evaluator expect.
    _verify_pkg = product.runtime_import or product.canonical_import or product.family
    verification = (
        f"import {_verify_pkg}\n"
        f"print('Installation successful')"
    ) if _verify_pkg else ""

    logger.info("extract_install_recipe: package=%s source=%s", package_name, source_file)
    return InstallRecipe(
        install_command=install_cmd,
        package_name=package_name,
        version_constraint=version_constraint,
        verification_code=verification,
        source_file=source_file,
    )


# ---------------------------------------------------------------------------
# TC-4084: Platform-specific install recipe extractors
# ---------------------------------------------------------------------------


def _extract_node_recipe(
    repo_dir: "Path",
    product: "ProductIdentity",
    shared_facts: "Any | None" = None,
) -> "Any | None":
    """Extract npm install recipe from package.json (TypeScript/JavaScript/Node)."""
    try:
        from launcher.models.understanding import InstallRecipe
        import json as _json

        # Use cached package_name from shared_facts if available
        if shared_facts and getattr(shared_facts, "package_name", ""):
            pkg_name = shared_facts.package_name
            install_cmd = f"npm install {pkg_name}"
            canonical = getattr(product, "canonical_import", "") or ""
            verification = f"const pkg = require('{canonical}');" if canonical else ""
            logger.info("extract_install_recipe(node): package=%s source=package.json (cached)", pkg_name)
            return InstallRecipe(
                install_command=install_cmd,
                package_name=pkg_name,
                verification_code=verification,
                source_file="package.json (cached)",
            )

        pkg_json = repo_dir / "package.json"
        if not pkg_json.exists():
            return None
        data = _json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
        pkg_name = data.get("name", "")
        if not pkg_name:
            return None
        version = data.get("version", "")
        version_constraint = f">={version}" if version else ""
        install_cmd = f"npm install {pkg_name}"
        canonical = getattr(product, "canonical_import", "") or pkg_name
        verification = f"const pkg = require('{canonical}');"
        logger.info("extract_install_recipe(node): package=%s source=package.json", pkg_name)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=pkg_name,
            version_constraint=version_constraint,
            verification_code=verification,
            source_file="package.json",
        )
    except Exception:
        logger.debug("_extract_node_recipe failed", exc_info=True)
        return None


def _extract_java_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract Maven install recipe from pom.xml."""
    try:
        from launcher.models.understanding import InstallRecipe
        import xml.etree.ElementTree as ET

        pom = repo_dir / "pom.xml"
        if not pom.exists():
            return None
        content = pom.read_text(encoding="utf-8", errors="replace")
        # Strip namespace for simple parsing
        content_no_ns = re.sub(r' xmlns(?::[^=]*)?\s*=\s*["\'][^"\']*["\']', '', content)
        try:
            root = ET.fromstring(content_no_ns)
        except ET.ParseError:
            return None
        group_id = (root.findtext("groupId") or "").strip()
        artifact_id = (root.findtext("artifactId") or "").strip()
        version = (root.findtext("version") or "").strip()
        if not group_id or not artifact_id:
            return None
        pkg_name = f"{group_id}:{artifact_id}"
        artifact_spec = f"{group_id}:{artifact_id}:{version}" if version else pkg_name
        install_cmd = f"mvn dependency:get -Dartifact={artifact_spec}"
        version_constraint = version if version else ""
        canonical = getattr(product, "canonical_import", "") or pkg_name
        verification = f"// Import {canonical} in your project"
        logger.info("extract_install_recipe(java): artifact=%s source=pom.xml", artifact_spec)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=pkg_name,
            version_constraint=version_constraint,
            verification_code=verification,
            source_file="pom.xml",
        )
    except Exception:
        logger.debug("_extract_java_recipe failed", exc_info=True)
        return None


def _extract_dotnet_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract dotnet add package recipe from *.csproj files."""
    try:
        from launcher.models.understanding import InstallRecipe

        csproj_files = list(repo_dir.glob("**/*.csproj"))
        if not csproj_files:
            return None
        content = csproj_files[0].read_text(encoding="utf-8", errors="replace")
        # Look for PackageReference to find the actual package name
        canonical = getattr(product, "canonical_import", "")
        pkg_name = canonical or ""
        # Try to extract from PackageReference Include attribute
        m = re.search(r'<PackageReference\s+Include\s*=\s*["\']([^"\']+)["\']', content)
        if m and canonical and canonical.lower() in m.group(1).lower():
            pkg_name = m.group(1).strip()
        if not pkg_name:
            return None
        install_cmd = f"dotnet add package {pkg_name}"
        logger.info("extract_install_recipe(dotnet): package=%s source=*.csproj", pkg_name)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=pkg_name,
            source_file=str(csproj_files[0].name),
        )
    except Exception:
        logger.debug("_extract_dotnet_recipe failed", exc_info=True)
        return None


def _extract_go_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract go get recipe from go.mod."""
    try:
        from launcher.models.understanding import InstallRecipe

        go_mod = repo_dir / "go.mod"
        if not go_mod.exists():
            return None
        content = go_mod.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
        if not m:
            return None
        module_path = m.group(1).strip()
        install_cmd = f"go get {module_path}"
        verification = f'import "{module_path}"'
        logger.info("extract_install_recipe(go): module=%s source=go.mod", module_path)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=module_path,
            verification_code=verification,
            source_file="go.mod",
        )
    except Exception:
        logger.debug("_extract_go_recipe failed", exc_info=True)
        return None


def _extract_rust_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract cargo add recipe from Cargo.toml."""
    try:
        from launcher.models.understanding import InstallRecipe

        cargo_toml = repo_dir / "Cargo.toml"
        if not cargo_toml.exists():
            return None
        content = cargo_toml.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if not m:
            return None
        crate_name = m.group(1).strip()
        install_cmd = f"cargo add {crate_name}"
        logger.info("extract_install_recipe(rust): crate=%s source=Cargo.toml", crate_name)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=crate_name,
            source_file="Cargo.toml",
        )
    except Exception:
        logger.debug("_extract_rust_recipe failed", exc_info=True)
        return None


def _extract_ruby_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract gem install recipe from *.gemspec or Gemfile."""
    try:
        from launcher.models.understanding import InstallRecipe

        # Try gemspec first
        gemspec_files = list(repo_dir.glob("*.gemspec"))
        if gemspec_files:
            content = gemspec_files[0].read_text(encoding="utf-8", errors="replace")
            m = re.search(r'\.name\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                gem_name = m.group(1).strip()
                install_cmd = f"gem install {gem_name}"
                logger.info("extract_install_recipe(ruby): gem=%s source=*.gemspec", gem_name)
                return InstallRecipe(
                    install_command=install_cmd,
                    package_name=gem_name,
                    source_file=str(gemspec_files[0].name),
                )

        # Fall back to canonical_import
        canonical = getattr(product, "canonical_import", "")
        if canonical:
            gem_name = canonical.replace("_", "-")
            install_cmd = f"gem install {gem_name}"
            return InstallRecipe(
                install_command=install_cmd,
                package_name=gem_name,
                source_file="derived",
            )
        return None
    except Exception:
        logger.debug("_extract_ruby_recipe failed", exc_info=True)
        return None


def _extract_php_recipe(repo_dir: "Path", product: "ProductIdentity") -> "Any | None":
    """Extract composer require recipe from composer.json."""
    try:
        from launcher.models.understanding import InstallRecipe
        import json as _json

        composer_json = repo_dir / "composer.json"
        if not composer_json.exists():
            return None
        data = _json.loads(composer_json.read_text(encoding="utf-8", errors="replace"))
        pkg_name = data.get("name", "")
        if not pkg_name:
            return None
        install_cmd = f"composer require {pkg_name}"
        logger.info("extract_install_recipe(php): package=%s source=composer.json", pkg_name)
        return InstallRecipe(
            install_command=install_cmd,
            package_name=pkg_name,
            source_file="composer.json",
        )
    except Exception:
        logger.debug("_extract_php_recipe failed", exc_info=True)
        return None


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
    platform: str = "python",
) -> "list":
    """Extract real workflow patterns from test and example files.

    For Python repos: mines .py test/example files via AST, looking for
    functions with 3+ statements referencing API surface class names.

    For non-Python repos (TC-4087): doc-scan strategy —
    - README.md + docs/*.md: ordered lists (1. 2. 3.) with ≥ 3 steps, ≥ 30 chars each
    - Example source files (.ts .java .cs .go .rs): line-count heuristic (3–100 lines),
      not AST. Language inferred from file extension.

    Falls back to doc-scan if Python AST extraction yields 0 examples.

    Returns list of WorkflowExample.
    """
    import re as _re
    from launcher.models.understanding import WorkflowExample

    examples: list[WorkflowExample] = []

    _NON_PYTHON_EXTS = {".ts", ".java", ".cs", ".go", ".rs", ".cpp", ".c", ".swift", ".kt"}
    _EXT_LANG = {
        ".ts": "typescript", ".java": "java", ".cs": "csharp",
        ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
        ".swift": "swift", ".kt": "kotlin",
    }
    _is_python = platform.lower() in ("python", "")

    def _uses_private_python_api(code: str) -> bool:
        return bool(_re.search(r"\._[A-Za-z]\w*", code))

    # ── Python AST path ───────────────────────────────────────────────────
    if _is_python:
        # Collect API class names for matching
        api_names: set[str] = set()
        if api_surface:
            for cls in getattr(api_surface, "class_briefs", []) or []:
                api_names.add(cls.name.lower())
            for cls_name in getattr(api_surface, "public_classes", []) or []:
                api_names.add(cls_name.lower())

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
                start = node.lineno
                end = node.end_lineno or start + len(node.body)
                if end - start > 50:
                    continue

                lines = source.splitlines()[start - 1:end]
                func_text = "\n".join(lines)
                func_lower = func_text.lower()
                if _uses_private_python_api(func_text):
                    logger.debug(
                        "workflow_example_private_api_invalid [TC-4255]: source=%s name=%s",
                        rel_path,
                        node.name,
                    )
                    continue

                if api_names:
                    refs = sum(1 for name in api_names if name in func_lower)
                    if refs < 1:
                        continue

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

    # ── Doc-scan path (TC-4087): non-Python OR Python fallback with 0 examples ──
    if not examples:
        _ORDERED_STEP_RE = _re.compile(r"^\s*\d+\.\s+(.{30,})", _re.MULTILINE)

        # Gather markdown candidates: README + docs/*.md
        md_candidates: list[str] = []
        for path in getattr(repo_info, "doc_paths", []) or []:
            if path.lower().endswith(".md"):
                md_candidates.append(path)
        # Also check README at root if not already in doc_paths
        for readme_name in ("README.md", "readme.md", "Readme.md"):
            readme_rel = readme_name
            if readme_rel not in md_candidates and (repo_dir / readme_name).exists():
                md_candidates.insert(0, readme_rel)

        for rel_path in md_candidates[:10]:
            full_path = repo_dir / rel_path
            if not full_path.exists() or full_path.stat().st_size > 100_000:
                continue
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            steps_found = _ORDERED_STEP_RE.findall(content)
            if len(steps_found) >= 3:
                # Each step becomes a step label (strip trailing markdown)
                step_labels = [s.rstrip("*_`").strip()[:120] for s in steps_found[:10]]
                slug = Path(rel_path).stem.lower().replace(" ", "_")
                examples.append(WorkflowExample(
                    name=f"workflow_from_{slug}",
                    title=f"Workflow from {Path(rel_path).name}",
                    code="\n".join(f"// Step {i+1}: {s}" for i, s in enumerate(step_labels)),
                    steps=step_labels,
                    language=platform.lower() if platform and platform.lower() != "python" else "text",
                    source_file=rel_path,
                    source_lines=(0, 0),
                ))
                if len(examples) >= 10:
                    break

        # Source-file heuristic: example files with 3–100 lines
        if len(examples) < 10:
            example_paths = list(getattr(repo_info, "example_paths", []) or [])
            for rel_path in example_paths[:30]:
                ext = Path(rel_path).suffix.lower()
                if ext not in _NON_PYTHON_EXTS:
                    continue
                full_path = repo_dir / rel_path
                if not full_path.exists():
                    continue
                try:
                    source_lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
                except Exception:
                    continue
                line_count = len(source_lines)
                if line_count < 3 or line_count > 100:
                    continue
                lang = _EXT_LANG.get(ext, ext.lstrip("."))
                stem = Path(rel_path).stem
                examples.append(WorkflowExample(
                    name=stem,
                    title=stem.replace("_", " ").replace("-", " ").title(),
                    code="\n".join(source_lines),
                    steps=[],
                    language=lang,
                    source_file=rel_path,
                    source_lines=(1, line_count),
                ))
                if len(examples) >= 10:
                    break

    logger.info(
        "extract_workflow_examples: found %d examples (platform=%s)",
        len(examples),
        platform,
    )
    return examples
