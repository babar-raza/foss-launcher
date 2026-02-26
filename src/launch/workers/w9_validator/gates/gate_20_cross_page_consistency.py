"""Gate 20: Cross-Page Consistency Check.

Eight deterministic checks across all published pages in one pilot run:

1. G20-001 (warn):  Duplicate prose block -- identical paragraph >= 100 chars
                    appearing verbatim in >= 2 pages.
2. G20-002 (error): Version contradiction -- Python/OS version ranges extracted
                    from pages conflict (ranges do not overlap).
3. G20-003 (warn):  Class/function name divergence -- same identifier referenced
                    by 2+ distinct names across pages.
4. G20-004 (error): Source-of-truth contradiction -- page version references
                    conflict with canonical minimum from shared_facts.json
                    (TC-2479).
5. G20-005 (error): Package name inconsistency -- different pip package names
                    found across pages (TC-2525).
6. G20-006 (warn):  Install command inconsistency -- different pip install
                    extras/version specifiers across pages (TC-2525).
7. G20-007 (warn):  Format claim inconsistency -- format mentions not in
                    canonical format list from shared_facts.json (TC-2525).
8. G20-008 (info):  Slug-evidence consistency -- format tokens in page slugs
                    not found in product_facts supported_formats (TC-2613).

All checks are deterministic (no LLM, no network calls).
The gate passes (returns True) if there are no G20-002/G20-004/G20-005 errors.
Warns (G20-001, G20-003, G20-006, G20-007) and infos (G20-008) are recorded but
do not fail the gate.

TC-2374 (RD-07): Gate 20 Cross-Page Consistency
TC-2479: Source-of-truth check against shared_facts.json
TC-2525: Package name, install command, and format claim consistency
TC-2613: Slug-evidence consistency check

Per specs/09_validation_gates.md S"Gate 20: Cross-Page Consistency".
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Minimum length for a prose block to be considered a duplicate candidate.
DUPLICATE_MIN_CHARS = 100


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_gate_20(
    md_files: List[Path],
    run_dir: Optional[Path] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 20: Cross-Page Consistency Check.

    Args:
        md_files: List of Path objects pointing to published markdown files.
        run_dir: Optional path to run directory (enables G20-004 source-of-truth check).

    Returns:
        Tuple of (gate_passed: bool, issues: List[Dict]).
        gate_passed is False only when G20-002/G20-004 errors exist.
    """
    issues: List[Dict[str, Any]] = []

    # Load content once -- shared by all checks.
    pages: List[Dict[str, Any]] = []
    for path in md_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        body = _strip_frontmatter(content)
        body = _strip_code_blocks(body)
        pages.append({"path": str(path), "content": content, "body": body})

    if len(pages) < 2:
        return True, []

    issues.extend(_find_duplicate_blocks(pages))
    issues.extend(_find_version_contradictions(pages))
    issues.extend(_find_class_name_divergence(pages))

    # G20-004/005/006/007: Checks that use shared_facts (graceful when absent)
    shared_facts_path = run_dir / "artifacts" / "shared_facts.json" if run_dir else None
    shared_facts: Optional[Dict[str, Any]] = None
    if shared_facts_path and shared_facts_path.exists():
        try:
            shared_facts = json.loads(shared_facts_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("G20 shared_facts load failed: %s", e)

    if shared_facts is not None:
        try:
            pages_content = [(Path(p["path"]), p["content"]) for p in pages]
            issues.extend(_check_against_source_of_truth(pages_content, shared_facts))
        except Exception as e:
            logger.warning("G20-004 source check skipped: %s", e)

    # G20-005: Package name consistency (TC-2525)
    issues.extend(_find_package_name_inconsistency(pages))

    # G20-006: Install command consistency (TC-2525)
    issues.extend(_find_install_command_inconsistency(pages))

    # G20-007: Format claim consistency (TC-2525)
    issues.extend(_find_format_claim_inconsistency(pages, shared_facts))

    # G20-008: Slug-evidence consistency (TC-2613)
    # Validates that format tokens referenced in slugs exist in product_facts
    page_plan_path = run_dir / "artifacts" / "page_plan.json" if run_dir else None
    product_facts_path = run_dir / "artifacts" / "product_facts.json" if run_dir else None
    if page_plan_path and page_plan_path.exists() and product_facts_path and product_facts_path.exists():
        try:
            page_plan = json.loads(page_plan_path.read_text(encoding="utf-8"))
            product_facts = json.loads(product_facts_path.read_text(encoding="utf-8"))
            issues.extend(_check_slug_evidence_consistency(page_plan, product_facts))
        except Exception as e:
            logger.warning("G20-008 slug evidence check skipped: %s", e)

    gate_passed = not any(i["severity"] == "error" for i in issues)
    return gate_passed, issues


# ---------------------------------------------------------------------------
# Check 1: Duplicate block detection (G20-001, warn)
# ---------------------------------------------------------------------------

def _find_duplicate_blocks(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect identical prose paragraphs (≥ DUPLICATE_MIN_CHARS) in ≥ 2 pages.

    Uses exact string matching on non-empty paragraphs extracted from the body
    (after stripping frontmatter and code blocks).
    """
    issues: List[Dict[str, Any]] = []

    # paragraph → list of (path, line_number) that contain it
    para_index: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for page in pages:
        body = page["body"]
        # Split into paragraphs on blank lines
        raw_paragraphs = re.split(r"\n{2,}", body)
        for para in raw_paragraphs:
            para = para.strip()
            if len(para) < DUPLICATE_MIN_CHARS:
                continue
            # Find approximate line number in original content
            line_no = _find_line(page["content"], para[:60])
            para_index[para].append((page["path"], line_no))

    seen_pairs: set = set()
    for para, occurrences in para_index.items():
        if len(occurrences) < 2:
            continue
        # Report each unique pair once
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                path_a, line_a = occurrences[i]
                path_b, _ = occurrences[j]
                pair_key = tuple(sorted([path_a, path_b]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                short = para[:80].replace("\n", " ")
                issues.append({
                    "issue_id": f"gate20_duplicate_{_slug(path_a)}_{_slug(path_b)}",
                    "gate": "gate_20_cross_page_consistency",
                    "severity": "warn",
                    "error_code": "G20-001",
                    "message": (
                        f"Duplicate prose block ({len(para)} chars) found in "
                        f"{Path(path_a).name!r} and {Path(path_b).name!r}: "
                        f"\"{short}...\""
                    ),
                    "location": {"path": path_a, "line": line_a},
                    "status": "OPEN",
                })

    return issues


# ---------------------------------------------------------------------------
# Check 2: Version contradiction (G20-002, error)
# ---------------------------------------------------------------------------

# Matches patterns like "Python 3.8", "Python 3.8+", "Python >= 3.10",
# "requires Python 3.9", "Python 3.7 or higher"
_VERSION_RE = re.compile(
    r"[Pp]ython\s*(?:>=?\s*|requires?\s+python\s*)?(\d+)\.(\d+)",
    re.IGNORECASE,
)


def _find_version_contradictions(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect conflicting Python version requirements across pages.

    Extracts all version numbers, computes the effective minimum version per page,
    then checks if any two pages have non-overlapping minimums (difference > 1 minor).
    """
    issues: List[Dict[str, Any]] = []

    # (major, minor) minimum per page
    page_min_versions: List[Tuple[str, Tuple[int, int], int]] = []  # (path, version, line)

    for page in pages:
        matches = list(_VERSION_RE.finditer(page["content"]))
        if not matches:
            continue
        versions = [(int(m.group(1)), int(m.group(2))) for m in matches]
        min_ver = min(versions)
        line_no = _find_line(page["content"], matches[0].group(0))
        page_min_versions.append((page["path"], min_ver, line_no))

    if len(page_min_versions) < 2:
        return issues

    # Compare all pairs: flag if major differs OR minor differs by > 1
    for i in range(len(page_min_versions)):
        for j in range(i + 1, len(page_min_versions)):
            path_a, ver_a, line_a = page_min_versions[i]
            path_b, ver_b, _ = page_min_versions[j]
            if _versions_conflict(ver_a, ver_b):
                issues.append({
                    "issue_id": f"gate20_version_{_slug(path_a)}_{_slug(path_b)}",
                    "gate": "gate_20_cross_page_consistency",
                    "severity": "error",
                    "error_code": "G20-002",
                    "message": (
                        f"Python version contradiction: {Path(path_a).name!r} requires "
                        f"Python {ver_a[0]}.{ver_a[1]}+ but {Path(path_b).name!r} "
                        f"requires Python {ver_b[0]}.{ver_b[1]}+"
                    ),
                    "location": {"path": path_a, "line": line_a},
                    "status": "OPEN",
                })

    return issues


def _versions_conflict(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Return True if two (major, minor) version requirements are incompatible.

    Two versions conflict when their major versions differ, or when their minor
    versions differ by more than 1 (e.g. 3.8 vs 3.10 would conflict, but
    3.8 vs 3.9 is borderline-acceptable and is NOT flagged to reduce noise).
    """
    if a[0] != b[0]:
        return True  # different major
    return abs(a[1] - b[1]) > 1


# ---------------------------------------------------------------------------
# Check 3: Class/function name divergence (G20-003, warn)
# ---------------------------------------------------------------------------

# Matches class/function names in code blocks: `ClassName` or `function_name()`
_IDENTIFIER_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_]{2,})`")


def _find_class_name_divergence(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect the same real-world concept referenced by 2+ names across pages.

    Uses a simple heuristic: if two identifier names share a normalized root
    (first 6+ chars lowercase) but are different, flag as potential divergence.
    Only reports high-confidence cases to keep noise low.
    """
    issues: List[Dict[str, Any]] = []

    # normalized_root → set of (actual_name, path)
    root_names: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for page in pages:
        found = set(_IDENTIFIER_RE.findall(page["content"]))
        for name in found:
            root = name.lower()[:6]
            root_names[root].append((name, page["path"]))

    seen: set = set()
    for root, entries in root_names.items():
        # Get distinct names for this root
        distinct_names = list({e[0] for e in entries})
        if len(distinct_names) < 2:
            continue
        # Only flag if names differ significantly (not just casing of same word)
        normalized = sorted({n.lower() for n in distinct_names})
        if len(normalized) < 2:
            continue
        # Find the first page that uses the first distinct name
        first_path = next(e[1] for e in entries if e[0] == distinct_names[0])
        issue_key = tuple(sorted(distinct_names[:2]))
        if issue_key in seen:
            continue
        seen.add(issue_key)
        line_no = _find_line(
            next(p["content"] for p in [] if False) if False else "",
            distinct_names[0],
        ) or 1
        issues.append({
            "issue_id": f"gate20_divergence_{root}",
            "gate": "gate_20_cross_page_consistency",
            "severity": "warn",
            "error_code": "G20-003",
            "message": (
                f"Possible class/function name divergence: "
                f"{distinct_names[0]!r} vs {distinct_names[1]!r} "
                f"(same root \"{root}\")"
            ),
            "location": {"path": first_path, "line": 1},
            "status": "OPEN",
        })

    return issues


# ---------------------------------------------------------------------------
# Check 4: Source-of-truth contradiction (G20-004, error) — TC-2479
# ---------------------------------------------------------------------------

def _check_against_source_of_truth(
    pages: List[Tuple[Path, str]], shared_facts: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """G20-004: Validate page version references against shared_facts."""
    issues: List[Dict[str, Any]] = []
    canonical_min = (
        shared_facts.get("runtime_versions", {}).get("python", {}).get("minimum", "")
    )
    if not canonical_min:
        return issues

    try:
        canonical_parts = tuple(int(x) for x in canonical_min.split("."))
    except (ValueError, TypeError):
        return issues

    version_re = re.compile(r"[Pp]ython\s*(?:>=?\s*)?(\d+)\.(\d+)")

    for path, content in pages:
        for m in version_re.finditer(content):
            page_major, page_minor = int(m.group(1)), int(m.group(2))
            if (page_major, page_minor) != canonical_parts:
                if abs(page_minor - canonical_parts[1]) > 1 or page_major != canonical_parts[0]:
                    lineno = content[:m.start()].count("\n") + 1
                    issues.append({
                        "issue_id": f"gate20_source_{path.stem}_{m.start()}",
                        "gate": "gate_20_cross_page_consistency",
                        "severity": "error",
                        "error_code": "G20-004",
                        "message": (
                            f"Version {page_major}.{page_minor} in {path.name} "
                            f"contradicts canonical minimum Python {canonical_min}"
                        ),
                        "location": {"path": str(path), "line": lineno},
                    })
    return issues


# ---------------------------------------------------------------------------
# Check 5: Package name consistency (G20-005, error) — TC-2525
# ---------------------------------------------------------------------------

# Matches `pip install <package>` commands; skips flags like -U, -e.
# group(1) = package name (must start with a letter so flags are excluded).
_PIP_INSTALL_PACKAGE_RE = re.compile(
    r"pip\s+install\s+(?:-\S+\s+)*([a-zA-Z][a-zA-Z0-9._-]*)"
)

# Known non-product packages that appear in pip install commands but should
# not be counted as the product package name (pip tool itself, build tools, etc.)
_NON_PRODUCT_PACKAGES = frozenset({
    "pip", "setuptools", "wheel", "build", "twine", "virtualenv",
})


def _find_package_name_inconsistency(
    pages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """G20-005: All pages must reference the same pip package name.

    Scans all generated pages for ``pip install <package>`` commands and
    extracts the base package name. If multiple distinct *product* package names
    are found, emits an error issue.

    Non-product packages (pip, setuptools, reportlab, etc.) and pip flags
    (-U, -e) are excluded from the comparison to avoid false positives.
    """
    issues: List[Dict[str, Any]] = []

    # package_name → list of (page_path, line_no)
    pkg_locations: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for page in pages:
        for m in _PIP_INSTALL_PACKAGE_RE.finditer(page["content"]):
            pkg = m.group(1)
            # Normalize: strip version specifiers that may be attached
            # e.g. "aspose-3d>=24.1" -> base name is "aspose-3d"
            base_pkg = re.split(r"[>=<!\[]", pkg)[0]
            if not base_pkg:
                continue
            # Skip non-product packages (pip tool itself, build tools)
            if base_pkg in _NON_PRODUCT_PACKAGES:
                continue
            # Skip single-word packages with no hyphen or dot — these are standalone
            # dependency names like "reportlab", "pillow", "numpy" rather than the
            # product package name (which always contains a hyphen or dot, e.g.
            # "aspose-note", "aspose.3d").
            if "-" not in base_pkg and "." not in base_pkg:
                continue
            lineno = page["content"][:m.start()].count("\n") + 1
            pkg_locations[base_pkg].append((page["path"], lineno))

    distinct_packages = sorted(pkg_locations.keys())
    if len(distinct_packages) > 1:
        # Report error: multiple distinct package names
        first_pkg = distinct_packages[0]
        first_loc = pkg_locations[first_pkg][0]
        issues.append({
            "issue_id": "gate20_pkg_name_inconsistency",
            "gate": "gate_20_cross_page_consistency",
            "severity": "error",
            "error_code": "G20-005",
            "message": (
                f"Inconsistent pip package names across pages: "
                f"{', '.join(repr(p) for p in distinct_packages)}. "
                f"All pages should use the same package name."
            ),
            "location": {"path": first_loc[0], "line": first_loc[1]},
            "status": "OPEN",
        })

    return issues


# ---------------------------------------------------------------------------
# Check 6: Install command consistency (G20-006, warn) — TC-2525
# ---------------------------------------------------------------------------

# Matches full `pip install <package>[extras]>=version` commands.
_PIP_INSTALL_FULL_RE = re.compile(
    r"pip\s+install\s+([a-zA-Z0-9._\-\[\],>=<! ]+?)(?=\s*[`\n\r\"']|$)"
)


def _find_install_command_inconsistency(
    pages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """G20-006: All pip install commands should use the same form.

    Compares the full ``pip install ...`` commands across pages. If different
    extras or version specifiers are used, emits a warning.
    """
    issues: List[Dict[str, Any]] = []

    # full_command → list of (page_path, line_no)
    cmd_locations: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for page in pages:
        for m in _PIP_INSTALL_FULL_RE.finditer(page["content"]):
            cmd = m.group(1).strip()
            if not cmd:
                continue
            lineno = page["content"][:m.start()].count("\n") + 1
            cmd_locations[cmd].append((page["path"], lineno))

    distinct_cmds = sorted(cmd_locations.keys())
    if len(distinct_cmds) > 1:
        first_cmd = distinct_cmds[0]
        first_loc = cmd_locations[first_cmd][0]
        issues.append({
            "issue_id": "gate20_install_cmd_inconsistency",
            "gate": "gate_20_cross_page_consistency",
            "severity": "warn",
            "error_code": "G20-006",
            "message": (
                f"Inconsistent pip install commands across pages: "
                f"{', '.join(repr(c) for c in distinct_cmds[:4])}. "
                f"Consider unifying version specifiers and extras."
            ),
            "location": {"path": first_loc[0], "line": first_loc[1]},
            "status": "OPEN",
        })

    return issues


# ---------------------------------------------------------------------------
# Check 7: Format claim consistency (G20-007, warn) — TC-2525
# ---------------------------------------------------------------------------

# Matches format names like "XLSX", "PDF", "FBX", "OBJ" etc. in prose
# (uppercase 2-5 letter acronyms likely to be file formats).
_FORMAT_MENTION_RE = re.compile(
    r"\b([A-Z]{2,5})\b"
)

# Common non-format uppercase acronyms to exclude.
_FORMAT_EXCLUSIONS = frozenset({
    "API", "SDK", "CLI", "URL", "HTTP", "HTTPS", "HTML", "CSS", "JSON",
    "YAML", "XML", "REST", "UTF", "ASCII", "IDE", "GUI", "OS", "IO",
    "RAM", "CPU", "GPU", "NPM", "PIP", "GIT", "SSH", "FTP", "DNS",
    "TCP", "UDP", "LLM", "NLP", "SEO", "FAQ", "TODO", "NOTE", "TIP",
    "MIT", "BSD", "GPL", "AWS", "GCP", "ECS", "SQS", "SNS", "IAM",
    "FOSS", "SPA", "MVC", "ORM", "SQL", "AND", "THE", "FOR", "NOT",
    "YOU", "ALL", "ANY", "NEW", "USE", "SET", "GET", "PUT", "END",
    "KEY", "RUN", "ADD", "MAX", "MIN",
})


def _find_format_claim_inconsistency(
    pages: List[Dict[str, Any]],
    shared_facts: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """G20-007: Format mentions should be consistent with canonical format list.

    Cross-checks format mentions in pages against the ``supported_formats``
    list from shared_facts.json. Emits a warning for format-like mentions
    not found in the canonical list.
    """
    issues: List[Dict[str, Any]] = []

    if not shared_facts:
        return issues

    # Build canonical format set from shared_facts
    raw_formats = shared_facts.get("supported_formats", [])
    canonical_formats: set = set()
    for fmt in raw_formats:
        if isinstance(fmt, str):
            canonical_formats.add(fmt.upper())
        elif isinstance(fmt, dict):
            name = fmt.get("format", "")
            if name:
                canonical_formats.add(name.upper())

    if not canonical_formats:
        return issues

    # Collect all format-like mentions across pages
    unknown_formats: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for page in pages:
        body = page["body"]  # Stripped of code blocks and frontmatter
        for m in _FORMAT_MENTION_RE.finditer(body):
            token = m.group(1)
            if token in _FORMAT_EXCLUSIONS:
                continue
            if token in canonical_formats:
                continue
            # Only flag if it looks like a file format (adjacent to "format",
            # "file", "export", "import", "convert", "support")
            context_start = max(0, m.start() - 60)
            context_end = min(len(body), m.end() + 60)
            context = body[context_start:context_end].lower()
            format_keywords = {"format", "file", "export", "import", "convert", "support"}
            if any(kw in context for kw in format_keywords):
                lineno = page["content"][:page["content"].find(token)].count("\n") + 1 if token in page["content"] else 1
                unknown_formats[token].append((page["path"], lineno))

    for fmt_name, locations in sorted(unknown_formats.items()):
        first_loc = locations[0]
        issues.append({
            "issue_id": f"gate20_format_{fmt_name.lower()}",
            "gate": "gate_20_cross_page_consistency",
            "severity": "warn",
            "error_code": "G20-007",
            "message": (
                f"Format {fmt_name!r} mentioned in {Path(first_loc[0]).name!r} "
                f"is not in the canonical format list "
                f"({', '.join(sorted(canonical_formats)[:10])})"
            ),
            "location": {"path": first_loc[0], "line": first_loc[1]},
            "status": "OPEN",
        })

    return issues


# ---------------------------------------------------------------------------
# Check 8: Slug-evidence consistency (G20-008, info) — TC-2613
# ---------------------------------------------------------------------------

# Format-like tokens in slugs: 2-5 lowercase chars that look like file extensions.
_SLUG_FORMAT_RE = re.compile(r"\b([a-z]{2,5})\b")

# Common slug words that are NOT file format names.
_SLUG_STOPWORDS = frozenset({
    "how", "to", "and", "the", "for", "with", "from", "into", "load",
    "save", "open", "fix", "convert", "common", "errors", "python",
    "models", "files", "other", "optimize", "performance", "data",
    "java", "csharp", "javascript", "ruby", "create", "merge",
    "spreadsheets", "documents", "notebooks", "images", "presentations",
    "getting", "started", "guide", "feature", "highlight",
})


def _check_slug_evidence_consistency(
    page_plan: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """G20-008: Validate that format tokens in slugs are evidenced.

    Extracts format-like tokens from page slugs and checks whether they
    appear in ``product_facts["supported_formats"]``. Emits info-level
    issues for unevidenced format tokens (does NOT fail the gate).

    TC-2613: Warn-only sub-check for slug-evidence alignment.
    """
    issues: List[Dict[str, Any]] = []

    # Build supported formats set
    raw_formats = product_facts.get("supported_formats", [])
    supported: set = set()
    for fmt in raw_formats:
        if isinstance(fmt, str):
            supported.add(fmt.lower())
        elif isinstance(fmt, dict):
            name = fmt.get("format", "")
            if name:
                supported.add(name.lower())

    if not supported:
        return issues

    for page in page_plan.get("pages", []):
        slug = page.get("slug", "")
        if not slug:
            continue

        tokens = _SLUG_FORMAT_RE.findall(slug)
        for token in tokens:
            if token in _SLUG_STOPWORDS:
                continue
            if token not in supported:
                issues.append({
                    "issue_id": f"gate20_slug_evidence_{slug}_{token}",
                    "gate": "gate_20_cross_page_consistency",
                    "severity": "info",
                    "error_code": "G20-008",
                    "message": (
                        f"Format token '{token}' in slug '{slug}' is not in "
                        f"supported_formats ({', '.join(sorted(supported)[:8])})"
                    ),
                    "status": "OPEN",
                })

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the top of content."""
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    if end == -1:
        return content
    return content[end + 4:]


def _strip_code_blocks(content: str) -> str:
    """Replace fenced code block lines with blank lines."""
    lines = content.split("\n")
    result: List[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_block = not in_block
            result.append("")
        elif in_block:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _find_line(content: str, fragment: str) -> int:
    """Return 1-based line number of first occurrence of fragment in content."""
    if not fragment:
        return 1
    idx = content.find(fragment[:40])
    if idx == -1:
        return 1
    return content[:idx].count("\n") + 1


def _slug(path: str) -> str:
    """Derive a short deterministic slug from a file path."""
    stem = Path(path).stem
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:40]
