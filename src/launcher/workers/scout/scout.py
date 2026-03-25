"""Phase A — Scout: fingerprint files, extract basic structure.

Scout receives a pre-cloned repo_dir (cloned by Intake) and performs:
- File classification and binary detection (multi-platform)
- Bulk file reading (everything under budget)
- Multi-platform manifest parsing
"""
from __future__ import annotations

import json
import logging
import re as _re
import tomllib
import xml.etree.ElementTree as _ET
from pathlib import Path
from typing import Any

from launcher.models.understanding import (
    FileCategory,
    FileEntry,
    RepoInfo,
    SharedFacts,
)
from launcher.shared.input_sanitizer import sanitize_input
from launcher.workers.understand.file_classifier import (
    LANG_BY_EXT,
    classify_file,
    detect_language,
    has_example_dir,
    is_binary,
    is_excluded_dir,
    is_vendored,
)

logger = logging.getLogger(__name__)

# Maximum number of budget_log entries retained in memory.
# On a 10K-file repo with early budget exhaustion, the log could grow to ~9,950
# entries without this cap. Entries beyond the cap are counted but not stored.
_BUDGET_LOG_MAX = 500

# ===================================================================
# Public entry point
# ===================================================================


async def run_scout(
    repo_dir: Path,
    platform: str = "",  # SR-03: drives platform-aware budget selection
    canonical_import: str = "",  # TC-5189: threaded to csproj selection
) -> tuple[RepoInfo, dict[str, str], list[dict], int]:
    """Fingerprint a pre-cloned repository and extract structural metadata.

    Parameters
    ----------
    repo_dir:
        Path to the cloned repository (provided by Intake worker).
    platform:
        Optional platform string (e.g. ``"cpp"``, ``"java"``, ``"dotnet"``).
        Used to select a platform-appropriate content budget via
        ``_PLATFORM_BUDGETS``. Unknown values fall back to the 1 MB default.
    canonical_import:
        Optional canonical import string (e.g. ``"Aspose.ThreeD"``).
        TC-5189: Used for canonical_import-aware .csproj selection in
        multi-project .NET repos.

    Returns
    -------
    tuple of (RepoInfo, repo_content)
        - RepoInfo with file_tree, file_index, categorized paths, shared_facts
        - repo_content: dict[rel_path, content] for all text files under budget
    """
    # SR-03: select budget based on platform; unknown platform → 1 MB default
    budget_bytes = _PLATFORM_BUDGETS.get(platform, _DEFAULT_BUDGET_BYTES)
    logger.info("[Scout] budget=%d bytes for platform=%r", budget_bytes, platform)

    # 1. Walk file tree with classification
    file_tree, file_index = _walk_file_tree(repo_dir)

    # TC-FIX-01: Detect whether this is a cloned external product repo so the
    # exact-name meta-doc filter is scoped correctly (see _doc_skip_reason).
    _is_external_repo = ".clone_cache" in str(repo_dir).replace("\\", "/")

    # 2. Bulk read everything under budget (README will be read here, sanitized)
    repo_content, sanitize_redactions, sanitize_truncated, budget_log, budget_log_overflow, dropped_by_category, important_skipped = _read_repo_content(
        repo_dir, file_index, budget_bytes=budget_bytes, is_external_repo=_is_external_repo
    )

    # 3. Selected evidence paths
    doc_paths = [
        p for p, e in file_index.items()
        if e.category == FileCategory.doc and p in repo_content
        and not _doc_skip_reason(p, is_external_repo=_is_external_repo)
    ]
    example_paths = [
        p for p, e in file_index.items()
        if e.category == FileCategory.example and p in repo_content and not _example_skip_reason(p)
    ]
    source_paths = [p for p, e in file_index.items() if e.category == FileCategory.source]
    test_paths = [p for p, e in file_index.items() if e.category == FileCategory.test]
    config_paths = [p for p, e in file_index.items() if e.category == FileCategory.config]

    # P1-A: Extract sanitized README from repo_content (already sanitized by _read_repo_content)
    # This replaces the previous _read_readme() call which did a plain read_text() with NO
    # sanitization, causing unsanitized secrets in README to leak through readme_summary.
    readme_summary = ""
    for _readme_name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        for _key in repo_content:
            if _key.lower() == _readme_name.lower():
                readme_summary = _extract_readme_summary(repo_content[_key])
                break
        if readme_summary:
            break

    # 5. Extract shared facts (multi-platform)
    shared_facts = _extract_shared_facts(repo_dir, file_tree, file_index, canonical_import=canonical_import)

    # TC-4056 Fix 7: Collect truly-skipped paths (budget exhausted, not just truncated).
    # Files with reason "per_file_cap" ARE in repo_content (just shortened) — exclude those.
    _SKIP_REASONS = frozenset({
        "budget_exceeded", "doc_cap_reached", "source_reserve",
        "file_too_large_for_remaining_budget", "doc_ineligible_meta",
        "example_scaffold",
    })
    skipped_paths = [
        entry["path"]
        for entry in budget_log
        if entry.get("reason") in _SKIP_REASONS
    ]

    repo_info = RepoInfo(
        file_tree=file_tree,
        file_index=file_index,
        doc_paths=doc_paths,
        example_paths=example_paths,
        source_paths=source_paths,
        test_paths=test_paths,
        config_paths=config_paths,
        readme_summary=readme_summary,
        shared_facts=shared_facts,
        content_budget_used=sum(len(c.encode("utf-8", errors="replace")) for c in repo_content.values()),
        content_files_read=len(repo_content),
        skipped_paths=skipped_paths,
        important_files_skipped=important_skipped,
    )

    logger.info(
        "[Scout] %d files, %d read (%.1f KB) sanitize_redactions=%d files_truncated=%d "
        "budget_log_entries=%d budget_log_overflow=%d dropped_by_category=%s",
        len(file_tree),
        len(repo_content),
        repo_info.content_budget_used / 1024,
        sanitize_redactions,
        sanitize_truncated,
        len(budget_log),
        budget_log_overflow,
        dropped_by_category,
    )

    return repo_info, repo_content, budget_log, budget_log_overflow


# ===================================================================
# Reviewable inventory artifact
# ===================================================================


def build_scout_inventory(
    repo_info: RepoInfo,
    repo_content: dict[str, str],
    budget_log: list[dict[str, Any]],
    budget_log_overflow: int,
) -> dict[str, Any]:
    """Build a human-reviewable Scout inventory artifact."""
    cat_counts: dict[str, int] = {}
    for entry in repo_info.file_index.values():
        cat_counts[entry.category.value] = cat_counts.get(entry.category.value, 0) + 1

    skip_reason_counts: dict[str, int] = {}
    reason_by_path: dict[str, str] = {}
    for entry in budget_log:
        reason = entry.get("reason", "unknown")
        skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
        path = entry.get("path")
        if isinstance(path, str) and path not in reason_by_path:
            reason_by_path[path] = reason

    def _selection_rows(category: FileCategory, selected_paths: set[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for rel_path, entry in repo_info.file_index.items():
            if entry.category != category:
                continue
            decision = "kept" if rel_path in selected_paths else "skipped"
            detail = "selected_truncated" if reason_by_path.get(rel_path) == "per_file_cap" and decision == "kept" else (
                "selected" if decision == "kept" else reason_by_path.get(rel_path, "not_selected")
            )
            rows.append({
                "path": rel_path,
                "decision": decision,
                "reason": detail,
                "size_bytes": entry.size_bytes,
                "language": entry.language,
                "importance_rank": _selection_rank(rel_path, entry),
                "readable_in_repo_content": rel_path in repo_content,
            })
        rows.sort(key=lambda item: (item["decision"] != "kept", -item["importance_rank"], item["path"]))
        return rows

    return {
        "files_enumerated": len(repo_info.file_tree),
        "files_read": repo_info.content_files_read,
        "content_used_bytes": repo_info.content_budget_used,
        "by_category": cat_counts,
        "doc_paths": repo_info.doc_paths,
        "example_paths": repo_info.example_paths,
        "skipped_paths": repo_info.skipped_paths,
        "budget_log": budget_log,
        "budget_log_overflow_count": budget_log_overflow,
        "skip_reason_counts": skip_reason_counts,
        "skip_counts_approximate": budget_log_overflow > 0,
        "selected_doc_count": len(repo_info.doc_paths),
        "selected_example_count": len(repo_info.example_paths),
        "doc_selection": _selection_rows(FileCategory.doc, set(repo_info.doc_paths)),
        "example_selection": _selection_rows(FileCategory.example, set(repo_info.example_paths)),
        "truncated_files": [entry for entry in budget_log if entry.get("reason") == "per_file_cap"],
        # TC-5192: Top-level count for quick diagnostics
        "truncated_file_count": skip_reason_counts.get("per_file_cap", 0),
    }


# ===================================================================
# File tree walking with classification (TC-2 + TC-3)
# ===================================================================


def _walk_file_tree(
    repo_dir: Path,
    max_files: int = 10_000,
) -> tuple[list[str], dict[str, FileEntry]]:
    """Walk the repo and return classified file entries.

    Returns (file_tree, file_index) where file_index maps relative paths
    to FileEntry objects with category, size, and language.
    """
    paths: list[str] = []
    index: dict[str, FileEntry] = {}

    for path in sorted(repo_dir.rglob("*")):
        if len(paths) >= max_files:
            break
        if path.is_dir():
            continue

        # Skip excluded directories
        rel = path.relative_to(repo_dir)
        parts = rel.parts
        if any(is_excluded_dir(part) for part in parts):
            continue

        rel_str = str(rel).replace("\\", "/")

        # Skip vendored paths
        if is_vendored(rel_str):
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        category = classify_file(rel_str)
        language = detect_language(rel_str)

        paths.append(rel_str)
        index[rel_str] = FileEntry(
            category=category,
            size_bytes=size,
            language=language,
        )

    return paths, index


# ===================================================================
# Bulk file reading — everything under 5MB (TC-3)
# ===================================================================

_DEFAULT_BUDGET_BYTES = 1_000_000

# SR-03: Platform-aware budget. C++ and large Java repos exceed the 1 MB default;
# increasing the budget prevents core API files from being skipped.
_PLATFORM_BUDGETS: dict[str, int] = {
    "cpp": 4_000_000,        # C++ repos have large .cpp/.hpp files (65 KB+)
    "java": 2_000_000,       # Large Java repos (Presentation.java 36 KB+)
    "dotnet": 2_000_000,     # C# repos similar to Java in file density
    "typescript": 1_500_000, # TS repos with bundled .d.ts files
}

# Priority order for reading files when budget is limited
_CATEGORY_PRIORITY: list[FileCategory] = [
    FileCategory.doc,       # docs are highest priority
    FileCategory.example,   # examples next
    FileCategory.config,    # configs (manifests, build files)
    FileCategory.source,    # source code
    FileCategory.ci,        # CI configs
    FileCategory.test,      # test files
    FileCategory.asset,     # everything else
]

# TC-4056 Fix 6: Within each category, files are sorted by importance rank DESC then
# size ASC. Known-important stem keywords get a high rank; unknown names get rank 0.
# This prevents a 1KB test stub from being read before a 200KB API reference.
_DOC_IMPORTANCE_STEMS: frozenset[str] = frozenset({
    # All entries are pre-normalized (hyphens and underscores stripped, lowercase) to match
    # the stem produced by: Path(p).stem.lower().replace("-", "").replace("_", "")
    "readme", "api", "reference", "guide", "tutorial", "quickstart",
    "gettingstarted", "index", "overview", "introduction",
    "changelog", "contributing", "installation", "install", "usage",
})
_SOURCE_IMPORTANCE_STEMS: frozenset[str] = frozenset({
    # Pre-normalized: "__init__" → "init" after underscore stripping.
    # IU-07: was "__init__" (with underscores) — never matched after normalization.
    # Generic / Python entry points:
    "init", "main", "core", "base", "client", "api", "index",
    # High-value Java / C++ / .NET library class names (SR-04).
    # These appear as top-level public API classes in Aspose-style SDKs;
    # ranking them higher ensures they are read before lower-value files
    # when scout budget is limited.
    "presentation", "workbook", "document", "scene", "spreadsheet",
    "slide", "cell", "email", "message", "shape", "chart", "page",
    "notebook", "drawing", "diagram",
    # Common public-API gateway names across Java / C++ / .NET:
    "factory", "builder", "converter", "loader", "parser", "renderer",
    "exporter", "importer",
})

_STANDARD_DOC_EXTS: frozenset[str] = frozenset({".md", ".rst", ".txt"})
_STANDARD_SRC_EXTS: frozenset[str] = frozenset({
    ".py", ".ts", ".js", ".java", ".cs", ".go", ".rb", ".rs",
    ".php", ".cpp", ".c", ".h", ".kt", ".swift",
})
_SIZE_SIGNAL_MIN: int = 200        # below = stub, no size bonus
_SIZE_SIGNAL_MAX: int = 50_000     # above = likely generated, no size bonus
_EXAMPLE_SCAFFOLD_NAMES: frozenset[str] = frozenset({"__init__.py", "conftest.py"})
# CI/AI meta-files that must never be treated as product evidence in any repo.
# These are operator-instructions files (Claude Code, Copilot, LLMs.txt) added
# to repos as tooling configuration — they contain no product API evidence.
_ALWAYS_SKIP_META_DOCS: frozenset[str] = frozenset({
    "agents.md", "claude.md", "copilot-instructions.md", "llms.md",
})
_META_DOC_EXACT_NAMES: frozenset[str] = frozenset()  # all names promoted to _ALWAYS_SKIP_META_DOCS
_META_DOC_ROOT_KEYWORDS: frozenset[str] = frozenset({
    "readiness", "implementation", "summary", "status", "backlog",
    "roadmap", "plan", "notes",
})


def _normalized_stem(rel_path: str) -> str:
    return Path(rel_path).stem.lower().replace("-", "").replace("_", "")


def _doc_skip_reason(rel_path: str, *, is_external_repo: bool = False) -> str:
    """Return a deterministic skip reason for non-product documentation.

    ``_ALWAYS_SKIP_META_DOCS`` (``agents.md``, ``claude.md``) are excluded from
    all repos — internal and external — because they are foss-launcher operational
    files added to every product repo and contain no product evidence.

    For all other names in ``_META_DOC_EXACT_NAMES``, the filter is only applied
    when ``is_external_repo=False`` (the launcher's own repo), preserving the
    TC-FIX-01 behaviour for the remaining meta-doc names.
    """
    lower = rel_path.lower().replace("\\", "/")
    name = Path(lower).name
    # TC-5170: Always skip launcher-operational meta-docs in every repo.
    if name in _ALWAYS_SKIP_META_DOCS:
        return "doc_ineligible_meta"
    # TC-FIX-01: Skip exact-name filter for external (cloned product) repos.
    if not is_external_repo and name in _META_DOC_EXACT_NAMES:
        return "doc_ineligible_meta"
    if "/" not in lower and _normalized_stem(lower) != "readme":
        if any(keyword in _normalized_stem(lower) for keyword in _META_DOC_ROOT_KEYWORDS):
            return "doc_ineligible_meta"
    return ""


def _example_skip_reason(rel_path: str) -> str:
    """Skip obvious scaffolding inside example trees so usage files win budget."""
    if Path(rel_path.lower()).name in _EXAMPLE_SCAFFOLD_NAMES:
        return "example_scaffold"
    return ""


def _selection_rank(rel_path: str, entry: FileEntry) -> int:
    return _file_importance_rank(rel_path, entry.category) + (
        1 if _SIZE_SIGNAL_MIN <= entry.size_bytes <= _SIZE_SIGNAL_MAX else 0
    )


def _append_budget_event(
    budget_log: list[dict[str, Any]],
    dropped_by_category: dict[str, int],
    budget_log_overflow: int,
    *,
    path: str,
    reason: str,
    category: FileCategory | None = None,
    size_bytes: int | None = None,
    original_size: int | None = None,
    truncated_to: int | None = None,
) -> int:
    event: dict[str, Any] = {"path": path, "reason": reason}
    if category is not None:
        event["category"] = category.value
    if size_bytes is not None:
        event["size_bytes"] = size_bytes
    if original_size is not None:
        event["original_size"] = original_size
    if truncated_to is not None:
        event["truncated_to"] = truncated_to
    if len(budget_log) < _BUDGET_LOG_MAX:
        budget_log.append(event)
        return budget_log_overflow
    budget_log_overflow += 1
    dropped_by_category[reason] = dropped_by_category.get(reason, 0) + 1
    if budget_log_overflow == 1:
        logger.warning(
            "[Scout] Budget log truncated at %d entries. Additional entries will be counted in dropped_by_category.",
            _BUDGET_LOG_MAX,
        )
    return budget_log_overflow


def _file_importance_rank(rel_path: str, category: FileCategory) -> int:
    """Return a priority rank (0–6) for a file within its category tier.

    Higher rank = read earlier. Unknown names at deep paths = rank 0 (lowest).
    TC-4102: uses substring containment (not exact set membership) so that
    compound names like 'api_reference', 'getting-started', 'quick-start'
    are correctly ranked as high importance.

    TC-4234: three additive factors contribute to the rank:
      Factor 1 — Stem keyword match (+3): the file's stem (normalized:
          lowercased, hyphens/underscores stripped) contains a keyword from
          _DOC_IMPORTANCE_STEMS (for doc) or _SOURCE_IMPORTANCE_STEMS (for source).
      Factor 2 — Root-level file (+2): rel_path contains neither '/' nor '\\'
          (i.e. the file lives directly at the repository root).
      Factor 3 — Standard extension for category (+1): '.md', '.rst', '.txt'
          for doc files; '.py', '.ts', '.js', etc. for source files.

    Note: Factor 4 (size signal) is applied inline at sort time in
    _read_repo_content() to avoid making file size a parameter here.
    """
    stem = Path(rel_path).stem.lower().replace("-", "").replace("_", "")
    ext = Path(rel_path).suffix.lower()
    rank = 0

    # Factor 1: Stem keyword match (+3)
    if category == FileCategory.doc and any(s in stem for s in _DOC_IMPORTANCE_STEMS):
        rank += 3
    elif category == FileCategory.source and any(s in stem for s in _SOURCE_IMPORTANCE_STEMS):
        rank += 3

    # Factor 2: Root-level file (+2)
    if "/" not in rel_path and "\\" not in rel_path:
        rank += 2

    # Factor 3: Standard extension for category (+1)
    if category == FileCategory.doc and ext in _STANDARD_DOC_EXTS:
        rank += 1
    elif category == FileCategory.source and ext in _STANDARD_SRC_EXTS:
        rank += 1

    return rank


def _read_repo_content(
    repo_dir: Path,
    file_index: dict[str, FileEntry],
    *,
    budget_bytes: int = _DEFAULT_BUDGET_BYTES,
    is_external_repo: bool = False,
) -> tuple[dict[str, str], int, int, list[dict], int, dict[str, int], int]:
    """Read all text files under the budget.

    Files are read in priority order (docs > examples > configs > source > tests).
    Within each tier, smaller files are read first to maximize file count.
    Binary files are skipped.

    Adaptive budget constraints (TC-B03):
    - Documentation files are capped at 60% of total budget so source
      code is not starved on code-heavy repos.
    - Source code is guaranteed at least 20% of total budget (achieved by
      stopping non-source reads once 80% of the budget is consumed).

    Returns
    -------
    tuple of (content, total_redactions, files_truncated, budget_log, budget_log_overflow,
              dropped_by_category, important_files_skipped)
        - content: dict[rel_path, sanitized_text]
        - total_redactions: sum of redaction_count across all files read
        - files_truncated: number of files that were truncated
        - budget_log: list of dicts describing skipped/truncated files (capped at _BUDGET_LOG_MAX)
        - budget_log_overflow: count of entries beyond the cap
        - dropped_by_category: dict[reason, count] for all overflow entries (TC-4212)
        - important_files_skipped: count of rank>=4 files skipped by budget manager (TC-4236)
    """
    content: dict[str, str] = {}
    used = 0
    total_redactions = 0
    files_truncated = 0
    budget_log: list[dict] = []
    budget_log_overflow = 0  # entries beyond _BUDGET_LOG_MAX
    dropped_by_category: dict[str, int] = {}  # TC-4212: skip-reason counts for overflow entries
    important_files_skipped = 0  # TC-4236: high-rank files skipped by budget

    doc_cap = int(budget_bytes * 0.6)
    source_reserve_threshold = int(budget_bytes * 0.8)  # stop non-source reads here
    category_bytes: dict[FileCategory, int] = {}

    # README always first (regardless of category)
    for readme_name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        if readme_name in file_index or readme_name.lower() in {p.lower() for p in file_index}:
            # Find the actual key (case-insensitive match)
            for key in file_index:
                if key.lower() == readme_name.lower():
                    path = repo_dir / key
                    if path.exists() and not is_binary(path):
                        try:
                            raw = path.read_text(encoding="utf-8", errors="replace")
                            original_len = len(raw)
                            result = sanitize_input(raw, max_chars=100_000)
                            if result.redaction_count:
                                logger.warning(
                                    "[Scout] Sanitized %s: %s",
                                    key, result.redacted_kinds,
                                )
                                total_redactions += result.redaction_count
                            if result.truncated:
                                files_truncated += 1
                                budget_log_overflow = _append_budget_event(
                                    budget_log,
                                    dropped_by_category,
                                    budget_log_overflow,
                                    path=key,
                                    reason="per_file_cap",
                                    original_size=original_len,
                                    truncated_to=len(result.text),
                                )
                            content[key] = result.text
                            file_bytes = len(result.text.encode("utf-8", errors="replace"))
                            used += file_bytes
                            cat = file_index[key].category
                            category_bytes[cat] = category_bytes.get(cat, 0) + file_bytes
                        except (OSError, PermissionError):
                            pass
                    break
            break

    # Read by priority tier
    for category in _CATEGORY_PRIORITY:
        # TC-4056 Fix 6: Sort by (importance rank DESC, size ASC) within each tier.
        # This ensures known-important files (README, API reference, __init__.py)
        # are read before low-importance small stubs.
        tier_files = [
            (rel_path, entry)
            for rel_path, entry in file_index.items()
            if entry.category == category and rel_path not in content
        ]
        tier_files.sort(
            key=lambda x: (
                -(
                    _file_importance_rank(x[0], category)
                    + (1 if _SIZE_SIGNAL_MIN <= x[1].size_bytes <= _SIZE_SIGNAL_MAX else 0)
                ),
                x[1].size_bytes,
            )
        )

        for rel_path, entry in tier_files:
            skip_reason = ""
            if category == FileCategory.doc:
                skip_reason = _doc_skip_reason(rel_path, is_external_repo=is_external_repo)
            elif category == FileCategory.example:
                skip_reason = _example_skip_reason(rel_path)
            if skip_reason:
                budget_log_overflow = _append_budget_event(
                    budget_log,
                    dropped_by_category,
                    budget_log_overflow,
                    path=rel_path,
                    reason=skip_reason,
                    category=category,
                    size_bytes=entry.size_bytes,
                )
                continue

            if used >= budget_bytes:
                # TC-4236: count high-rank files missed by budget exhaustion
                _rank = _selection_rank(rel_path, entry)
                if _rank >= 4:
                    important_files_skipped += 1
                budget_log_overflow = _append_budget_event(
                    budget_log,
                    dropped_by_category,
                    budget_log_overflow,
                    path=rel_path,
                    reason="budget_exceeded",
                    category=category,
                    size_bytes=entry.size_bytes,
                )
                continue

            # Adaptive cap: stop doc reads at 60% of budget
            if category == FileCategory.doc:
                if category_bytes.get(FileCategory.doc, 0) >= doc_cap:
                    budget_log_overflow = _append_budget_event(
                        budget_log,
                        dropped_by_category,
                        budget_log_overflow,
                        path=rel_path,
                        reason="doc_cap_reached",
                        category=category,
                        size_bytes=entry.size_bytes,
                    )
                    continue

            # Source reserve: stop non-source reads at 80% to guarantee 20% for source
            if category != FileCategory.source and used >= source_reserve_threshold:
                budget_log_overflow = _append_budget_event(
                    budget_log,
                    dropped_by_category,
                    budget_log_overflow,
                    path=rel_path,
                    reason="source_reserve",
                    category=category,
                    size_bytes=entry.size_bytes,
                )
                continue

            # Skip files that would blow the remaining budget
            if entry.size_bytes > budget_bytes - used:
                # TC-4236: count high-rank files missed because they're too large for remaining budget
                _rank = _selection_rank(rel_path, entry)
                if _rank >= 4:
                    important_files_skipped += 1
                budget_log_overflow = _append_budget_event(
                    budget_log,
                    dropped_by_category,
                    budget_log_overflow,
                    path=rel_path,
                    reason="file_too_large_for_remaining_budget",
                    category=category,
                    size_bytes=entry.size_bytes,
                )
                continue

            path = repo_dir / rel_path
            if not path.exists() or is_binary(path):
                continue

            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue

            original_len = len(raw)
            result = sanitize_input(raw, max_chars=100_000)
            if result.redaction_count:
                logger.warning(
                    "[Scout] Sanitized %s: %s", rel_path, result.redacted_kinds,
                )
                total_redactions += result.redaction_count
            if result.truncated:
                files_truncated += 1
                budget_log_overflow = _append_budget_event(
                    budget_log,
                    dropped_by_category,
                    budget_log_overflow,
                    path=rel_path,
                    reason="per_file_cap",
                    original_size=original_len,
                    truncated_to=len(result.text),
                )
            content[rel_path] = result.text
            file_bytes = len(result.text.encode("utf-8", errors="replace"))
            used += file_bytes
            category_bytes[category] = category_bytes.get(category, 0) + file_bytes

    # TC-4212: Emit summary WARNING when overflow occurred so operators can
    # see skip-reason distribution without storing thousands of log entries.
    if budget_log_overflow > 0:
        logger.warning(
            "[Scout] Budget log overflow: %d entries dropped. Dropped categories: %s",
            budget_log_overflow,
            dropped_by_category,
        )

    # TC-4236: warn if important files were missed
    if important_files_skipped > 0:
        logger.warning(
            "[Scout] %d high-rank file(s) (rank>=4) skipped by budget manager. "
            "Check repo_info.skipped_paths for details.",
            important_files_skipped,
        )

    return content, total_redactions, files_truncated, budget_log, budget_log_overflow, dropped_by_category, important_files_skipped


def _read_readme(repo_dir: Path) -> str:
    """Read the README file, truncated to 4000 chars.

    # Deprecated: only used by external callers. run_scout() extracts readme_summary
    # from sanitized repo_content instead.
    """
    for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        readme_path = repo_dir / name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                return content[:4000]
            except Exception:
                continue
    return ""


def _extract_readme_summary(raw: str, max_chars: int = 8000) -> str:
    """Extract the most information-dense sections from a README.

    Algorithm:
    1. Extracts pre-heading intro paragraph (always included first).
    2. Splits remaining text by ## or # headings.
    3. Scores each section by heading keywords (high=3, mid=2, other=1).
    4. Greedy-fills budget from highest-score sections.
    5. Truncates last included section at sentence boundary.

    TC-4233: Replaces the blind [:4000] slice in run_scout(). The sanitized
    content from repo_content can be up to 100K chars; this function selects
    the 8000 most information-dense chars instead of the first 4000.
    """
    if not raw:
        return ""
    if len(raw) <= max_chars:
        return raw

    _HIGH_KEYWORDS = frozenset({
        "install", "usage", "api", "feature", "example",
        "format", "getting started", "getting-started", "quickstart",
    })
    _MID_KEYWORDS = frozenset({
        "overview", "introduction", "reference", "guide", "tutorial",
        "requirement", "prerequisite",
    })

    import re as _re2
    heading_re = _re2.compile(r'^#{1,3} .+', _re2.MULTILINE)
    boundaries = [m.start() for m in heading_re.finditer(raw)]

    # Pre-heading intro (always first)
    intro = raw[:boundaries[0]].strip() if boundaries else raw[:max_chars]

    # Parse sections
    sections: list[tuple[int, str]] = []  # (score, text)
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(raw)
        section_text = raw[start:end].strip()
        if not section_text:
            continue
        newline_pos = raw.find('\n', start)
        heading_line = raw[start:newline_pos].lower() if newline_pos > start else raw[start:].lower()
        if any(k in heading_line for k in _HIGH_KEYWORDS):
            score = 3
        elif any(k in heading_line for k in _MID_KEYWORDS):
            score = 2
        else:
            score = 1
        sections.append((score, section_text))

    # Sort by score descending (stable sort preserves order among equal scores)
    sections_sorted = sorted(sections, key=lambda x: -x[0])

    # Greedy fill
    result_parts = [intro] if intro else []
    budget = max_chars - len(intro) - (2 if intro else 0)  # account for \n\n separator

    for score, text in sections_sorted:
        if budget <= 0:
            break
        if len(text) <= budget:
            result_parts.append(text)
            budget -= len(text) + 2  # +2 for \n\n separator
        else:
            # Truncate at sentence boundary
            truncated = text[:budget]
            # Try to find last sentence ending
            last_sentence = max(
                truncated.rfind('. '),
                truncated.rfind('.\n'),
                truncated.rfind('\n\n'),
            )
            if last_sentence > budget // 2:
                truncated = truncated[:last_sentence + 1]
            result_parts.append(truncated)
            budget = 0

    result = '\n\n'.join(result_parts)
    return result[:max_chars]


# ===================================================================
# Multi-platform manifest parsing (TC-4)
# ===================================================================

_BUILD_SYSTEM_MAP: dict[str, str] = {
    "pyproject.toml": "pyproject",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "package.json": "npm",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "Cargo.toml": "cargo",
    "go.mod": "go",
    "composer.json": "composer",
    "Gemfile": "bundler",
    "build.sbt": "sbt",
}

# Maps primary language to install command template
_INSTALL_CMD_MAP: dict[str, str] = {
    "python": "pip install {package}",
    "javascript": "npm install {package}",
    "typescript": "npm install {package}",
    "java": "mvn dependency:get -Dartifact={package}",
    "csharp": "dotnet add package {package}",
    "go": "go get {package}",
    "rust": "cargo add {package}",
    "ruby": "gem install {package}",
    "php": "composer require {package}",
    "cpp": "vcpkg install {package}",
}


# TC-4235: Primary-language-first manifest ordering.
# Each entry lists parser keys tried first for that language.
_LANG_MANIFEST_PRIORITY: dict[str, list[str]] = {
    "python":     ["pyproject", "setup_cfg", "setup_py"],
    "javascript": ["package_json"],
    "typescript": ["package_json"],
    "java":       ["pom_xml"],
    "csharp":     ["csproj"],
    "go":         [],
    "rust":       ["cargo_toml"],
    "ruby":       ["gemspec"],
    "php":        ["composer_json"],
    "cpp":        [],
}
_ALL_MANIFEST_KEYS: list[str] = [
    "pyproject", "setup_cfg", "setup_py", "package_json",
    "cargo_toml", "composer_json", "pom_xml", "csproj", "gemspec",
]


def _extract_shared_facts(
    repo_dir: Path,
    file_tree: list[str],
    file_index: dict[str, FileEntry],
    canonical_import: str = "",
) -> SharedFacts:
    """Extract deterministic facts from repository metadata files (multi-platform)."""
    filenames = {Path(p).name for p in file_tree}

    # Build systems
    build_systems = sorted(
        _BUILD_SYSTEM_MAP[name]
        for name in filenames & set(_BUILD_SYSTEM_MAP)
    )
    # TC-4306: .csproj files have varying names so they can't match via filename set.
    # Detect dotnet build system by extension pattern instead.
    if any(name.endswith(".csproj") for name in file_tree) and "dotnet" not in build_systems:
        build_systems = sorted(set(build_systems) | {"dotnet"})

    # Primary language from file_index (more accurate than just extensions)
    lang_counts: dict[str, int] = {}
    for entry in file_index.values():
        if entry.language and entry.category == FileCategory.source:
            lang_counts[entry.language] = lang_counts.get(entry.language, 0) + 1
    primary_language = ""
    if lang_counts:
        primary_language = max(lang_counts, key=lang_counts.get)  # type: ignore[arg-type]
    elif "pom.xml" in filenames or "build.gradle" in filenames or "build.gradle.kts" in filenames:
        primary_language = "java"
    elif any(name.endswith(".csproj") for name in filenames):
        primary_language = "csharp"
    elif "package.json" in filenames:
        primary_language = "javascript"
    elif "Cargo.toml" in filenames:
        primary_language = "rust"
    elif "composer.json" in filenames:
        primary_language = "php"
    elif "Gemfile" in filenames or any(name.endswith(".gemspec") for name in filenames):
        primary_language = "ruby"

    # Has tests / CI / docs / examples (from file_index categories)
    has_tests = any(e.category == FileCategory.test for e in file_index.values())
    has_ci = any(e.category == FileCategory.ci for e in file_index.values())
    has_docs_folder = any(
        p.startswith("docs/") or "/docs/" in p
        for p, e in file_index.items() if e.category == FileCategory.doc
    )
    has_examples_folder = any(
        p.startswith("examples/") or p.startswith("samples/")
        or "/examples/" in p or "/samples/" in p
        for p in file_tree
    )

    # Multi-platform package metadata extraction (TC-4030: 8-tuple includes extra pyproject fields)
    # TC-4235: pass primary_language so manifest priority order is platform-aware
    (
        package_name, version, license_type, module_path,
        description, python_requires, dependencies, entrypoints,
    ) = _extract_package_metadata(repo_dir, primary_language, canonical_import=canonical_import)

    # SR-08: C++ CMake metadata — fills package_name/version/build_systems when
    # the manifest-based extraction above returns nothing (C++ has no pyproject/pom).
    cmake_path = repo_dir / "CMakeLists.txt"
    if cmake_path.exists():
        cmake_data = _parse_cmake(cmake_path)
        if cmake_data.get("project_name") and (not package_name or package_name == "UNKNOWN"):
            package_name = cmake_data["project_name"]
        if cmake_data.get("version") and not version:
            version = cmake_data["version"]
        if "cmake" not in build_systems:
            build_systems = sorted(set(build_systems) | {"cmake"})

    # SR-12: extract TargetFramework(s) from .csproj for .NET repos
    target_frameworks: list[str] = []
    if primary_language == "csharp" or any(name.endswith(".csproj") for name in file_tree):
        csproj_files = sorted(repo_dir.glob("**/*.csproj"))
        _main_csproj = _select_main_csproj(csproj_files, repo_dir=repo_dir, canonical_import=canonical_import)
        if _main_csproj:
            try:
                _csproj_content = _main_csproj.read_text(encoding="utf-8", errors="replace")
                # <TargetFramework>net6.0</TargetFramework> (single)
                _single_m = _re.search(
                    r"<TargetFramework>\s*([^<\s]+)\s*</TargetFramework>",
                    _csproj_content, _re.IGNORECASE,
                )
                if _single_m:
                    _tf = _single_m.group(1).strip()
                    if not _tf.startswith("$("):  # skip MSBuild variables
                        target_frameworks = [_tf]
                else:
                    # <TargetFrameworks>net6.0;netstandard2.0</TargetFrameworks> (multi)
                    _multi_m = _re.search(
                        r"<TargetFrameworks>\s*([^<]+)\s*</TargetFrameworks>",
                        _csproj_content, _re.IGNORECASE,
                    )
                    if _multi_m:
                        target_frameworks = [
                            f.strip() for f in _multi_m.group(1).split(";")
                            if f.strip() and not f.strip().startswith("$(")
                        ]
                if target_frameworks:
                    logger.debug("[Scout] .NET target_frameworks: %s from %s", target_frameworks, _main_csproj.name)
            except Exception:
                pass

    # Install command from primary language
    install_command = ""
    if package_name and package_name != "UNKNOWN" and primary_language in _INSTALL_CMD_MAP:
        install_command = _INSTALL_CMD_MAP[primary_language].format(package=package_name)
    elif package_name == "UNKNOWN":
        logger.warning(
            "[Scout] install_command: package_name is 'UNKNOWN' for %s — skipping install_command generation",
            repo_dir,
        )

    return SharedFacts(
        package_name=package_name,
        version=version,
        install_command=install_command,
        license_type=license_type,
        primary_language=primary_language,
        build_systems=build_systems,
        has_tests=has_tests,
        has_ci=has_ci,
        has_docs_folder=has_docs_folder,
        has_examples_folder=has_examples_folder,
        module_path=module_path,
        description=description,
        python_requires=python_requires,
        dependencies=dependencies,
        entrypoints=entrypoints,
        target_frameworks=target_frameworks,
    )


def _select_main_csproj(
    csproj_files: list[Path],
    repo_dir: Path | None = None,
    canonical_import: str = "",
) -> Path | None:
    """TC-4306/TC-5189: Select the main library .csproj from a multi-project repo.

    Ranking (highest to lowest priority):
    1. Non-test, non-exe project whose AssemblyName/PackageId matches canonical_import (+10)
    2. Non-test, non-exe project (prefer shortest path)
    3. Any non-test project
    4. First file as last resort

    Uses repo-relative paths for test detection to avoid false positives
    from test-named directories in the filesystem above the repo root.

    Returns None if csproj_files is empty.
    """
    if not csproj_files:
        return None
    if len(csproj_files) == 1:
        return csproj_files[0]

    ci_norm = canonical_import.lower().replace("-", ".").replace("_", ".") if canonical_import else ""

    candidates = []
    for csproj in csproj_files:
        # Use repo-relative path for "test" detection; fall back to filename only.
        try:
            rel = csproj.relative_to(repo_dir) if repo_dir else csproj
        except ValueError:
            rel = csproj
        parts_lower = [p.lower() for p in rel.parts]
        is_test = any("test" in p for p in parts_lower)
        is_exe = False
        content = ""
        try:
            content = csproj.read_text(encoding="utf-8", errors="replace")
            is_exe = bool(_re.search(r"<OutputType>\s*Exe\s*</OutputType>", content, _re.IGNORECASE))
        except Exception:
            pass

        # TC-5189: Score by canonical_import match (mirrors _dotnet.py:detect_package_root)
        ci_score = 0
        if ci_norm and content and not is_test and not is_exe:
            for tag in ("AssemblyName", "PackageId"):
                m = _re.search(rf"<{tag}>\s*([^<]+)\s*</{tag}>", content, _re.IGNORECASE)
                if m:
                    val = m.group(1).strip().lower().replace("-", ".").replace("_", ".")
                    if ci_norm in val or val in ci_norm or ci_norm.startswith(val) or val.startswith(ci_norm):
                        ci_score = 10
                        break

        candidates.append((csproj, is_test, is_exe, ci_score, len(rel.parts)))

    # Prefer non-test, non-exe; fall back to non-test; fall back to all
    lib = [(p, t, e, s, d) for p, t, e, s, d in candidates if not t and not e]
    if not lib:
        lib = [(p, t, e, s, d) for p, t, e, s, d in candidates if not t]
    if not lib:
        lib = candidates

    # Sort by: canonical_import score descending, then path depth ascending, then path alpha
    lib.sort(key=lambda x: (-x[3], x[4], str(x[0])))
    return lib[0][0]


def _parse_csproj_first(
    repo_dir: Path, canonical_import: str = "",
) -> tuple[str, str, str, str, list[str], list[str]]:
    """Find and parse the main *.csproj using TC-4306/TC-5189 ranking, returning a 6-tuple."""
    csproj_files = sorted(repo_dir.glob("**/*.csproj"))
    selected = _select_main_csproj(csproj_files, repo_dir=repo_dir, canonical_import=canonical_import)
    if selected:
        return _parse_csproj(selected)
    return "", "", "", "", [], []


def _parse_gemspec_first(repo_dir: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Find first *.gemspec and parse it, returning a 6-tuple."""
    gemspec_files = list(repo_dir.glob("*.gemspec"))
    if gemspec_files:
        return _parse_gemspec(gemspec_files[0])
    return "", "", "", "", [], []


def _extract_package_metadata(
    repo_dir: Path,
    primary_language: str = "",
    canonical_import: str = "",
) -> tuple[str, str, str, str, str, str, list[str], list[str]]:
    """Try all known manifest formats to extract package metadata.

    Returns: (pkg, ver, lic, module_path, description, python_requires, dependencies, entrypoints)

    TC-4235: Platform-aware dispatch — tries manifests for primary_language first,
    then falls back to all others. Non-Python parsers now populate description,
    dependencies, and entrypoints as well.
    """
    # Go module path is always extracted regardless of priority
    module_path = _parse_go_mod(repo_dir / "go.mod")

    _PARSER_DISPATCH = {
        "pyproject":     lambda: _parse_pyproject(repo_dir / "pyproject.toml"),
        "setup_cfg":     lambda: _parse_setup_cfg(repo_dir / "setup.cfg"),
        "setup_py":      lambda: _parse_setup_py(repo_dir / "setup.py"),
        "package_json":  lambda: _parse_package_json(repo_dir / "package.json"),
        "cargo_toml":    lambda: _parse_cargo_toml(repo_dir / "Cargo.toml"),
        "composer_json": lambda: _parse_composer_json(repo_dir / "composer.json"),
        "pom_xml":       lambda: _parse_pom_xml(repo_dir / "pom.xml"),
        "csproj":        lambda: _parse_csproj_first(repo_dir, canonical_import=canonical_import),
        "gemspec":       lambda: _parse_gemspec_first(repo_dir),
    }

    priority = _LANG_MANIFEST_PRIORITY.get(primary_language, [])
    ordered = priority + [k for k in _ALL_MANIFEST_KEYS if k not in priority]

    pkg = ver = lic = description = python_requires = ""
    dependencies: list[str] = []
    entrypoints: list[str] = []

    for key in ordered:
        result = _PARSER_DISPATCH[key]()
        if key == "pyproject":
            # 7-tuple: (name, ver, lic, desc, python_requires, deps, ep)
            name, v, l, desc, py_req, deps, ep = result
            if name:
                pkg, ver, lic, description, python_requires, dependencies, entrypoints = \
                    name, v, l, desc, py_req, deps, ep
                break
        else:
            # 6-tuple: (name, ver, lic, desc, deps, ep)
            name, v, l, desc, deps, ep = result
            if name:
                pkg, ver, lic, description, dependencies, entrypoints = name, v, l, desc, deps, ep
                break

    # go.mod fallback: use module path as package name if no manifest matched
    if not pkg and module_path:
        pkg = module_path.rsplit("/", 1)[-1]

    if not pkg:
        logger.warning(
            "[Scout] package_name: no manifest recognized in %s — setting sentinel 'UNKNOWN'",
            repo_dir,
        )
        pkg = "UNKNOWN"

    return pkg, ver, lic, module_path, description, python_requires, dependencies, entrypoints


# -- Individual manifest parsers ------------------------------------------


def _parse_pyproject(path: Path) -> tuple[str, str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, python_requires, dependencies, entrypoints
    from pyproject.toml (tomllib stdlib).

    TC-4030: Returns a 7-tuple so Scout caches all relevant fields in SharedFacts,
    eliminating downstream re-reads of pyproject.toml.
    """
    if not path.exists():
        return "", "", "", "", "", [], []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        poetry = data.get("tool", {}).get("poetry", {})
        name = project.get("name", "") or poetry.get("name", "")
        version = project.get("version", "") or poetry.get("version", "")
        lic = project.get("license", "")
        if isinstance(lic, dict):
            lic = lic.get("text", lic.get("file", ""))
        if not lic:
            lic = poetry.get("license", "")
        # TC-4056 Fix 5: guard against dict-valued name/version (e.g. dynamic versioning:
        # `version = {attr = "pkg.__version__"}` is valid TOML but not a plain string).
        if not isinstance(name, str):
            name = ""
        if not isinstance(version, str):
            version = ""
        if not isinstance(lic, str):
            lic = ""
        # TC-4030: additional fields
        description = project.get("description", "") or poetry.get("description", "")
        if not isinstance(description, str):
            description = ""
        python_requires = project.get("requires-python", "")
        if not isinstance(python_requires, str):
            python_requires = ""
        raw_deps = project.get("dependencies", []) or list(poetry.get("dependencies", {}).keys())
        if isinstance(raw_deps, list):
            dependencies = [str(d) for d in raw_deps if isinstance(d, str)]
        elif isinstance(raw_deps, dict):
            # Poetry-style dict: {requests: "^2.0", ...} — exclude "python" key
            dependencies = [k for k in raw_deps if k != "python"]
        else:
            dependencies = []
        entrypoints = list(project.get("scripts", {}).keys())
        return name, version, lic, description, python_requires, dependencies, entrypoints
    except Exception as exc:
        logger.warning(
            "[Scout] pyproject.toml tomllib parse failed for %s (%s) — "
            "falling back to regex; description/python_requires/dependencies/entrypoints will be empty",
            path, exc,
        )
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "", "", "", "", "", [], []
        return (
            _toml_value(content, "name"),
            _toml_value(content, "version"),
            _toml_value(content, "license"),
            _toml_value(content, "description"),  # P1-D: attempt regex extraction
            "",  # python_requires — not regex-extractable reliably
            [],  # dependencies
            [],  # entrypoints
        )


def _parse_setup_cfg(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, deps, entrypoints from setup.cfg.

    TC-4235: Extended from 3-tuple to 6-tuple to match other manifest parsers.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", "", "", "", [], []
    name = _cfg_value(content, "name")
    version = _cfg_value(content, "version")
    lic = _cfg_value(content, "license")
    description = _cfg_value(content, "description")
    # install_requires can be multi-line in setup.cfg
    install_req_match = _re.search(r'install_requires\s*=\s*([\s\S]+?)(?=\n\[|\Z)', content)
    if install_req_match:
        deps = [
            line.strip().rstrip(',')
            for line in install_req_match.group(1).splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
    else:
        deps = []
    # console_scripts entrypoints
    ep_match = _re.search(r'console_scripts\s*=\s*([\s\S]+?)(?=\n\[|\Z)', content)
    if ep_match:
        entrypoints = [
            line.split('=')[0].strip()
            for line in ep_match.group(1).splitlines()
            if '=' in line
        ]
    else:
        entrypoints = []
    return name, version, lic, description, deps, entrypoints


def _parse_setup_py(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description from setup.py via regex (no import).

    Uses pattern matching on the setup() call arguments. Handles both single
    and double quoted values. Returns ("", "", "", "", [], []) on any failure or if the
    file is absent.

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", "", "", "", [], []
    name = _re.search(r"""name\s*=\s*['"]([^'"]+)['"]""", content)
    version = _re.search(r"""version\s*=\s*['"]([^'"]+)['"]""", content)
    license_ = _re.search(r"""license\s*=\s*['"]([^'"]+)['"]""", content)
    description_m = _re.search(r"""description\s*=\s*['"]([^'"]+)['"]""", content)
    return (
        name.group(1) if name else "",
        version.group(1) if version else "",
        license_.group(1) if license_ else "",
        description_m.group(1) if description_m else "",
        [],
        [],
    )


def _parse_package_json(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, deps, entrypoints from package.json.

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return "", "", "", "", [], []
    lic = data.get("license", "")
    if isinstance(lic, dict):
        lic = lic.get("type", "")
    description = data.get("description", "") or ""
    if not isinstance(description, str):
        description = ""
    deps = list((data.get("dependencies") or {}).keys())
    entrypoints = list((data.get("scripts") or {}).keys())
    return data.get("name", ""), data.get("version", ""), lic, description, deps, entrypoints


def _parse_cargo_toml(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, deps, bins from Cargo.toml (tomllib stdlib).

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        pkg = data.get("package", {})
        description = str(pkg.get("description", "") or "")
        deps_dict = data.get("dependencies") or {}
        if isinstance(deps_dict, dict):
            deps = list(deps_dict.keys())
        else:
            deps = []
        bins = [
            b.get("name", "") for b in (data.get("bin") or [])
            if isinstance(b, dict) and b.get("name")
        ]
        return pkg.get("name", ""), pkg.get("version", ""), pkg.get("license", ""), description, deps, bins
    except Exception as exc:
        logger.debug("[Scout] Cargo.toml tomllib parse failed (%s); falling back to regex", exc)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "", "", "", "", [], []
        return (
            _toml_value(content, "name"),
            _toml_value(content, "version"),
            _toml_value(content, "license"),
            "",
            [],
            [],
        )


def _parse_composer_json(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, deps from composer.json.

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return "", "", "", "", [], []
    lic = data.get("license", "")
    if isinstance(lic, list):
        lic = lic[0] if lic else ""
    description = str(data.get("description", "") or "")
    if not isinstance(description, str):
        description = ""
    deps = list((data.get("require") or {}).keys())
    return data.get("name", ""), data.get("version", ""), lic, description, deps, []


# SR-08: C++ CMake metadata constants and parser
_CMAKE_PSEUDO_TARGETS: frozenset[str] = frozenset({
    "INTERFACE", "SHARED", "STATIC", "MODULE", "OBJECT", "ALIAS",
})


def _parse_cmake(cmake_path: Path) -> dict[str, Any]:
    """Parse CMakeLists.txt for C++ library identity information.

    Extracts:
    - project_name: from project(NAME ...) or project(NAME VERSION X)
    - version: from project(... VERSION X.Y.Z) or set_target_properties
    - library_target: first add_library(TARGET ...) target name
    - public_include_dirs: from target_include_directories(... PUBLIC ...)

    Returns an empty dict on any parse failure.
    """
    result: dict[str, Any] = {}
    try:
        content = cmake_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    # project(MyLib VERSION 24.1.0) or project(MyLib)
    m = _re.search(
        r"project\s*\(\s*([A-Za-z_][A-Za-z0-9_.-]*)"
        r"(?:[^)]*VERSION\s+([\d.]+))?",
        content, _re.IGNORECASE,
    )
    if m:
        result["project_name"] = m.group(1).strip()
        if m.group(2):
            result["version"] = m.group(2).strip()

    # add_library(TargetName [SHARED|STATIC|...] ...)
    lib_m = _re.search(
        r"add_library\s*\(\s*([A-Za-z_][A-Za-z0-9_.-]*)",
        content, _re.IGNORECASE,
    )
    if lib_m:
        target_name = lib_m.group(1).strip()
        if target_name.upper() not in _CMAKE_PSEUDO_TARGETS:
            result["library_target"] = target_name

    # target_include_directories(TARGET PUBLIC dir1 dir2)
    inc_m = _re.search(
        r"target_include_directories\s*\([^)]*\bPUBLIC\b([^)]+)\)",
        content, _re.IGNORECASE | _re.DOTALL,
    )
    if inc_m:
        raw_dirs = inc_m.group(1).split()
        public_dirs = [
            d.strip('"') for d in raw_dirs
            if d and d not in {"PRIVATE", "INTERFACE", "PUBLIC"}
            and not d.startswith("$<")  # skip generator expressions
        ]
        if public_dirs:
            result["public_include_dirs"] = public_dirs

    # Version fallback: set_target_properties(TARGET PROPERTIES VERSION X.Y.Z)
    if "version" not in result:
        ver_m = _re.search(
            r"set_target_properties\s*\([^)]*\bVERSION\s+([\d.]+)",
            content, _re.IGNORECASE,
        )
        if ver_m:
            result["version"] = ver_m.group(1).strip()

    logger.debug(
        "[Scout] cmake: project=%s version=%s target=%s",
        result.get("project_name", ""), result.get("version", ""), result.get("library_target", ""),
    )
    return result


def _parse_pom_xml(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract groupId:artifactId, version, license, description, deps from pom.xml.

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        tree = _ET.parse(str(path))
        root = tree.getroot()
        # Strip namespace prefix if present (e.g. {http://maven.apache.org/POM/4.0.0})
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        def _find(tag: str) -> str:
            el = root.find(f"{ns}{tag}")
            return (el.text or "").strip() if el is not None else ""

        group = _find("groupId")
        artifact = _find("artifactId")
        version = _find("version")
        description = _find("description")
        # License name is nested: /licenses/license/name
        lic_el = root.find(f"{ns}licenses/{ns}license/{ns}name")
        license_name = (lic_el.text or "").strip() if lic_el is not None else ""
        pkg = f"{group}:{artifact}" if group and artifact else artifact
        # Find dependencies
        try:
            dep_els = root.findall(f".//{ns}dependency")
            deps = []
            for dep_el in dep_els:
                artifact_id = dep_el.findtext(f"{ns}artifactId") or ""
                group_id = dep_el.findtext(f"{ns}groupId") or ""
                if artifact_id:
                    deps.append(f"{group_id}:{artifact_id}".strip(":") if group_id else artifact_id)
        except Exception:
            deps = []
        return pkg, version, license_name, description, deps, []
    except Exception as exc:
        logger.debug("[Scout] pom.xml ET parse failed (%s); falling back to regex", exc)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "", "", "", "", [], []
        group = _xml_value(content, "groupId")
        artifact = _xml_value(content, "artifactId")
        version = _xml_value(content, "version")
        license_name = _xml_value(content, "name")
        pkg = f"{group}:{artifact}" if group and artifact else artifact
        return pkg, version, license_name, "", [], []


def _parse_csproj(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract PackageId, Version, license, description, deps from *.csproj.

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        tree = _ET.parse(str(path))
        root = tree.getroot()

        def _find_prop(tag: str) -> str:
            for el in root.iter(tag):
                if el.text:
                    return el.text.strip()
            return ""

        pkg = _find_prop("PackageId") or _find_prop("AssemblyName") or path.stem
        version = _find_prop("Version") or _find_prop("PackageVersion")
        lic = _find_prop("PackageLicenseExpression")
        description = _find_prop("Description") or _find_prop("Summary") or ""
        try:
            dep_els = list(root.iter("PackageReference"))
            deps = [el.get("Include", "") for el in dep_els if el.get("Include")]
        except Exception:
            deps = []
        return pkg, version, lic, description, deps, []
    except Exception as exc:
        logger.debug("[Scout] .csproj ET parse failed (%s); falling back to regex", exc)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "", "", "", "", [], []
        pkg = _xml_value(content, "PackageId") or _xml_value(content, "AssemblyName") or path.stem
        version = _xml_value(content, "Version") or _xml_value(content, "PackageVersion")
        lic = _xml_value(content, "PackageLicenseExpression")
        return pkg, version, lic, "", [], []


def _parse_go_mod(path: Path) -> str:
    """Extract module path from go.mod."""
    if not path.exists():
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    match = _re.search(r"^module\s+(\S+)", content, _re.MULTILINE)
    return match.group(1) if match else ""


def _parse_gemspec(path: Path) -> tuple[str, str, str, str, list[str], list[str]]:
    """Extract name, version, license, description, deps from *.gemspec (regex).

    TC-4235: Extended from 3-tuple to 6-tuple.
    """
    if not path.exists():
        return "", "", "", "", [], []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", "", "", "", [], []
    name = _ruby_spec_value(content, "name")
    version = _ruby_spec_value(content, "version")
    lic = _ruby_spec_value(content, "license")
    description = _ruby_spec_value(content, "description") or _ruby_spec_value(content, "summary")
    dep_pattern = _re.compile(r'\.add(?:_runtime)?_dependency\s+[\'"]([^\'"]+)[\'"]')
    deps = dep_pattern.findall(content)
    return name, version, lic, description, deps, []


# -- Parsing helpers -------------------------------------------------------


def _toml_value(content: str, key: str) -> str:
    """Extract a simple string value from TOML content (no full parser)."""
    match = _re.search(rf'^{key}\s*=\s*["\']([^"\']*)["\']', content, _re.MULTILINE)
    return match.group(1) if match else ""


def _cfg_value(content: str, key: str) -> str:
    """Extract a value from setup.cfg INI-style content."""
    match = _re.search(rf"^{key}\s*=\s*(.+)$", content, _re.MULTILINE)
    return match.group(1).strip() if match else ""


def _xml_value(content: str, tag: str, *, section: str = "") -> str:
    """Extract value from an XML tag (simple regex, no full parser)."""
    match = _re.search(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", content)
    return match.group(1) if match else ""


def _ruby_spec_value(content: str, attr: str) -> str:
    """Extract a gemspec attribute value."""
    match = _re.search(rf"\.{attr}\s*=\s*['\"]([^'\"]+)['\"]", content)
    return match.group(1) if match else ""
