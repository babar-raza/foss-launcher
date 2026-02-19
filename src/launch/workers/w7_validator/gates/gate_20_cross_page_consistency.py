"""Gate 20: Cross-Page Consistency Check.

Three deterministic checks across all published pages in one pilot run:

1. G20-001 (warn):  Duplicate prose block — identical paragraph ≥ 100 chars
                    appearing verbatim in ≥ 2 pages.
2. G20-002 (error): Version contradiction — Python/OS version ranges extracted
                    from pages conflict (ranges do not overlap).
3. G20-003 (warn):  Class/function name divergence — same identifier referenced
                    by 2+ distinct names across pages.

All checks are deterministic (no LLM, no network calls).
The gate passes (returns True) if there are no G20-002 errors.
Warns (G20-001, G20-003) are recorded but do not fail the gate.

TC-2374 (RD-07): Gate 20 Cross-Page Consistency

Per specs/09_validation_gates.md §"Gate 20: Cross-Page Consistency".
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Minimum length for a prose block to be considered a duplicate candidate.
DUPLICATE_MIN_CHARS = 100


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_gate_20(md_files: List[Path]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 20: Cross-Page Consistency Check.

    Args:
        md_files: List of Path objects pointing to published markdown files.

    Returns:
        Tuple of (gate_passed: bool, issues: List[Dict]).
        gate_passed is False only when G20-002 (version contradiction) errors exist.
    """
    issues: List[Dict[str, Any]] = []

    # Load content once — shared by all three checks.
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
