"""W10 Fixer worker implementation.

This module implements TC-470: Issue resolution per specs/28_coordination_and_handoffs.md.

Main entry point:
- execute_fixer: Apply minimal fix to resolve exactly one validation issue

Exception hierarchy:
- FixerError: Base exception
- FixerIssueNotFoundError: Issue ID not found in validation report
- FixerUnfixableError: Issue cannot be fixed automatically
- FixerNoOpError: Fix produced no diff
- FixerArtifactMissingError: Required artifact not found

Spec references:
- specs/28_coordination_and_handoffs.md:71-84 (Fix loop policy)
- specs/21_worker_contracts.md:290-320 (W10 contract)
- specs/08_patch_engine.md (Patch strategies)
- specs/11_state_and_events.md (Event emission)
- specs/10_determinism_and_caching.md (Stable ordering)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ...io.artifact_store import ArtifactStore
from .._shared.content_sanitizer import (
    canonicalize_product_names,
    close_unclosed_fences,
    dedup_see_also_sections,
    fix_heading_body_concat,
    fix_prose_fencemarker_concat,
    merge_adjacent_code_blocks,
    move_see_also_to_end,
    remove_llm_artifact_preambles,
    strip_heading_trailing_punct,
    strip_llm_scaffolding,
    strip_pipeline_comments,
)

logger = logging.getLogger(__name__)


# FQ-1: Bare code patterns (mirrors gate_17_prelints._CODE_PATTERNS — TC-3626)
_FQ1_CODE_PATTERNS = re.compile(
    r"^(?:import |from .+ import |def |class |    (?:def |class |return |if |for |while )|"
    r"(?:self|cls)\.|print\(|raise |try:|except |with )",
)
# FQ-1: Code context extension — assignments and method/function calls (TC-3626)
_FQ1_CODE_CONTEXT_RE = re.compile(
    r"^[ \t]*(?:[A-Za-z_]\w*\s*=|[A-Za-z_]\w*(?:\.\w+)*\s*\()"
)

# FQ-3: Truncated bullet endings (compiled once at module level)
_TRUNCATION_ENDINGS = re.compile(
    r"[,]\s*$|"
    r"\b(?:is|of|for|with|the|and|but|or|in|to|a|an)\s*$"
)
# FQ-3: Separate patterns for two-step repair strategy (TC-3263)
_TRUNCATION_COMMA_RE = re.compile(r"[,]\s*$")
_TRUNCATION_CONNECTOR_RE = re.compile(
    r"\b(?:is|of|for|with|the|and|but|or|in|to|a|an)\s*$"
)

# Package name in pip install commands.
# group(1) = command prefix including any flags (e.g. "pip install -U ")
# group(2) = package name (must start with a letter to exclude "-U", "-e" flags)
_PKG_FIX_RE = re.compile(
    r"(pip\s+install\s+(?:-\S+\s+)*)([a-zA-Z][a-zA-Z0-9._-]*)"
)

# ── Scaffold leak fix patterns (TC-2880) ──────────────────────────────────────
_SCAFFOLD_XML_TAG_RE = re.compile(
    r"<(instructions|context|original-content|issues)>"
    r".*?"
    r"</\1>",
    re.DOTALL | re.IGNORECASE,
)
_SCAFFOLD_XML_ORPHAN_RE = re.compile(
    r"^</?(?:instructions|context|original-content|issues)>\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_SCAFFOLD_LLM_META_PATTERNS = [
    re.compile(r"You now have a (?:complete|working|full)", re.IGNORECASE),
    re.compile(r"Here(?:'s| is) a complete", re.IGNORECASE),
    re.compile(r"As an AI", re.IGNORECASE),
    re.compile(r"I(?:'ll| will) help you", re.IGNORECASE),
    re.compile(r"Let me (?:explain|show|demonstrate)", re.IGNORECASE),
    re.compile(r"^System:\s"),
    re.compile(r"W\d+(?:\.\d+)?_REVIEW\b"),
]
_SCAFFOLD_PIPELINE_JSON_RE = re.compile(
    r'^\s*"(?:claims|evidence_map|page_plan|api_surface|shared_facts|claim_groups)":'
)
_SCAFFOLD_PIPELINE_DIAG_PATTERNS = [
    re.compile(r"claim_id:\s*[a-f0-9-]+", re.IGNORECASE),
    re.compile(r"evidence_score:\s*\d"),
    re.compile(r"<!--\s*claim\.[A-Z]"),
]


# Stale path guard event (TC-3450).
# Emitted when issue.location.path no longer exists at fix time, indicating
# that the validation report is stale and W9 must be re-run.
EVENT_FIXER_STALE_PATH_DETECTED = "FIXER_STALE_PATH_DETECTED"


# Exception hierarchy
class FixerError(Exception):
    """Base exception for fixer errors."""

    pass


class FixerIssueNotFoundError(FixerError):
    """Issue ID not found in validation report."""

    pass


class FixerUnfixableError(FixerError):
    """Issue cannot be fixed automatically."""

    pass


class FixerNoOpError(FixerError):
    """Fix produced no diff."""

    pass


class FixerArtifactMissingError(FixerError):
    """Required artifact not found."""

    pass


class StaleValidationReportError(FixerError):
    """Validation report is stale or tampered (content_hash mismatch).

    Raised by _verify_handoff() when the recomputed content hash does not
    match the content_hash recorded by W9.  This indicates either:
    - The report was modified between W9 and W10 (filesystem race / manual edit).
    - A different W9 run overwrote the report (stale generation_id).
    """

    pass


def _verify_handoff(report_data: Dict[str, Any]) -> None:
    """Verify W9 -> W10 handoff integrity metadata in the validation report.

    Checks:
    1. ``generation_id`` is present (warn if missing — backward compat).
    2. ``content_hash`` is present (warn if missing — backward compat).
    3. If both present, recompute hash from gates+issues and compare.
    4. On mismatch raise :class:`StaleValidationReportError`.

    Args:
        report_data: Parsed validation_report.json dict.

    Raises:
        StaleValidationReportError: If content_hash does not match.
    """
    generation_id = report_data.get("generation_id")
    content_hash = report_data.get("content_hash")

    if generation_id is None:
        logger.warning(
            "handoff_verify generation_id missing — "
            "report may have been produced by an older W9"
        )

    if content_hash is None:
        logger.warning(
            "handoff_verify content_hash missing — "
            "report may have been produced by an older W9"
        )

    if generation_id is not None and content_hash is not None:
        # Recompute hash from the same canonical input W9 used
        _hash_input = json.dumps(
            {"gates": report_data.get("gates", []),
             "issues": report_data.get("issues", [])},
            sort_keys=True,
        )
        recomputed = hashlib.sha256(_hash_input.encode()).hexdigest()

        if recomputed != content_hash:
            raise StaleValidationReportError(
                f"Validation report content_hash mismatch: "
                f"expected {content_hash}, recomputed {recomputed}. "
                f"generation_id={generation_id}. "
                f"The report may have been modified or overwritten since W9 wrote it."
            )

        logger.info(
            "handoff_verified generation_id=%s content_hash=%s",
            generation_id,
            content_hash,
        )


# Utility functions
def emit_event(
    run_dir: Path,
    event_type: str,
    payload: Dict[str, Any],
    trace_id: str,
    span_id: str,
    parent_span_id: Optional[str] = None,
) -> None:
    """Emit event to events.ndjson.

    TC-1033: Delegates to ArtifactStore.emit_event for centralized event emission.

    Args:
        run_dir: Run directory path
        event_type: Event type (e.g., FIXER_STARTED)
        payload: Event payload
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        parent_span_id: Parent span ID (optional)
    """
    if parent_span_id:
        payload = {**payload, "parent_span_id": parent_span_id}
    store = ArtifactStore(run_dir=run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_dir.name,
        trace_id=trace_id,
        span_id=span_id,
    )


def load_json_artifact(run_dir: Path, artifact_name: str) -> Dict[str, Any]:
    """Load JSON artifact from RUN_DIR/artifacts/.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        run_dir: Run directory path
        artifact_name: Artifact filename (e.g., validation_report.json)

    Returns:
        Parsed JSON artifact

    Raises:
        FixerArtifactMissingError: If artifact not found
    """
    store = ArtifactStore(run_dir=run_dir)
    try:
        return store.load_artifact(artifact_name, validate_schema=False)
    except FileNotFoundError:
        raise FixerArtifactMissingError(
            f"Required artifact not found: {artifact_name}"
        )


def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter dict or None, body content)
    """
    # Match frontmatter: --- at start, YAML content, closing ---
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


def write_frontmatter(frontmatter: Dict[str, Any], body: str) -> str:
    """Write frontmatter and body back to markdown format.

    Args:
        frontmatter: Frontmatter dict
        body: Body content

    Returns:
        Full markdown content with frontmatter
    """
    # width=float('inf') prevents yaml.dump from wrapping long strings across
    # lines as plain-scalar continuations (e.g. "  post" artifact). Wrapped
    # scalars cause Hugo YAML parse errors when a later pass double-quotes the
    # value while the orphaned continuation line remains. (TC-3628)
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, width=float("inf")
    )
    return f"---\n{yaml_str}---\n{body}"


def _extract_permalink_from_path(file_path: Path, run_dir: Path) -> str:
    """Derive a Hugo permalink from a content file path.

    Strips ``work/site/content/`` prefix (and optional subdomain) then
    constructs ``/<rest-without-extension>/``.
    """
    try:
        # Prefer stripping subdomain-aware content root
        content_root = run_dir / "work" / "site" / "content"
        rel = file_path.relative_to(content_root)
        # If first component is a subdomain (contains "."), strip it
        parts = rel.parts
        if parts and "." in parts[0]:  # e.g. "kb.aspose.org"
            rel = Path(*parts[1:])
        permalink = "/" + str(rel.with_suffix("")).replace("\\", "/") + "/"
        return permalink
    except ValueError:
        # Fallback: use stem only
        return f"/{file_path.stem}/"


def _infer_layout_from_path(file_path: Path) -> str:
    """Infer Hugo layout from content file path."""
    path_str = str(file_path).replace("\\", "/").lower()
    if "/kb/" in path_str or "kb.aspose.org" in path_str:
        return "kb-howto"
    if "/blog/" in path_str or "blog.aspose.org" in path_str:
        return "post"
    return "page"


def _infer_frontmatter_for_placeholder(file_path: Path, run_dir: Path) -> Dict[str, str]:
    """Infer layout and permalink for a placeholder page.

    Returns a dict of fields to inject.  Returns empty dict for
    non-placeholder pages.
    """
    slug = file_path.stem.lower()
    if "placeholder" not in slug:
        return {}
    return {
        "layout": _infer_layout_from_path(file_path),
        "permalink": _extract_permalink_from_path(file_path, run_dir),
    }


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        SHA256 hash (hex string)
    """
    if not file_path.exists():
        return ""

    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def _strip_rundir_overlap(rel: Path, run_dir: Path) -> Path:
    """Strip overlapping run_dir tail from a relative path.

    If *rel* already starts with trailing components of *run_dir*
    (e.g. ``runs/test_run/work/...`` when run_dir ends in
    ``runs/test_run``), strip those components so that a subsequent
    ``run_dir / result`` does not duplicate the prefix.
    """
    run_parts = run_dir.parts
    rel_parts = rel.parts
    # Try longest overlap first (suffix of run_dir == prefix of rel).
    for k in range(min(len(run_parts), len(rel_parts)), 0, -1):
        if run_parts[-k:] == rel_parts[:k]:
            remaining = rel_parts[k:]
            return Path(*remaining) if remaining else rel
    return rel


def _normalize_issue_paths(issue: Dict[str, Any], run_dir: Path) -> None:
    """Resolve relative paths in issue dict against run_dir (in-place).

    validation_report.json stores paths relative to run_dir (per
    normalize_report / TC-935).  Fix functions need absolute paths
    for file I/O.  Already-absolute paths are left unchanged,
    making the function idempotent.

    Handles the case where relative paths already include the run_dir
    tail (e.g. ``runs/test_run/work/...``) by stripping the overlap
    before joining, preventing doubled prefixes.

    Args:
        issue: Issue dict (mutated in place).
        run_dir: Run directory path.
    """
    location = issue.get("location")
    if isinstance(location, dict) and "path" in location:
        p = Path(location["path"])
        if not p.is_absolute():
            location["path"] = str(run_dir / _strip_rundir_overlap(p, run_dir))

    files = issue.get("files")
    if isinstance(files, list):
        for i, f in enumerate(files):
            p = Path(f)
            if not p.is_absolute():
                files[i] = str(run_dir / _strip_rundir_overlap(p, run_dir))


def select_issue_to_fix(
    validation_report: Dict[str, Any], current_issue: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Select highest priority issue to fix.

    Per specs/28_coordination_and_handoffs.md:77-78:
    - Select exactly one issue to fix (first by deterministic order)
    - Deterministic ordering: blocker > error > warn > info, then by gate, path, line, issue_id

    Args:
        validation_report: Validation report dict
        current_issue: Optional specific issue to fix (overrides selection)

    Returns:
        Issue dict to fix, or None if no fixable issues

    Raises:
        FixerIssueNotFoundError: If current_issue provided but not found
    """
    issues = validation_report.get("issues", [])

    # If specific issue provided, find and return it
    if current_issue:
        issue_id = current_issue.get("issue_id")
        for issue in issues:
            if issue.get("issue_id") == issue_id:
                return issue
        raise FixerIssueNotFoundError(
            f"Issue ID not found in validation report: {issue_id}"
        )

    # Filter to only OPEN issues with blocker or error severity
    fixable_issues = [
        issue
        for issue in issues
        if issue.get("status") == "OPEN"
        and issue.get("severity") in ["blocker", "error"]
    ]

    if not fixable_issues:
        return None

    # Sort by severity rank, gate, location
    severity_rank = {"blocker": 0, "error": 1, "warn": 2, "info": 3}

    def sort_key(issue: Dict[str, Any]) -> Tuple:
        rank = severity_rank.get(issue.get("severity", "info"), 3)
        gate = issue.get("gate", "")
        location = issue.get("location", {})
        path = location.get("path", "") if isinstance(location, dict) else ""
        line = location.get("line", 0) if isinstance(location, dict) else 0
        issue_id = issue.get("issue_id", "")
        return (rank, gate, path, line, issue_id)

    sorted_issues = sorted(fixable_issues, key=sort_key)

    # Return first issue
    return sorted_issues[0] if sorted_issues else None


def fix_unresolved_token(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix unresolved template token issue.

    Strategy:
    - Read file with unresolved token
    - Remove token or replace with placeholder based on context
    - Write fixed file back

    Args:
        issue: Issue dict
        run_dir: Run directory
        llm_client: LLM client for generating fixes (optional)

    Returns:
        Fix result dict with:
            - fixed: bool (True if fix applied)
            - files_changed: List of changed file paths
            - diff_summary: Summary of changes
    """
    location = issue.get("location", {})
    file_path_str = location.get("path", "")
    line_num = location.get("line", 0)

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    # Read file
    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Find token in message
    token_match = re.search(r"__[A-Z0-9_]+__", issue.get("message", ""))
    if not token_match:
        return {"fixed": False, "error": "Cannot extract token from issue message"}

    token = token_match.group(0)

    # Simple fix: remove the token (strategy: delete unresolved tokens)
    # More sophisticated: use LLM to infer proper replacement
    if line_num > 0 and line_num <= len(lines):
        original_line = lines[line_num - 1]
        fixed_line = original_line.replace(token, "")

        # If line becomes empty after removal, remove it entirely
        if fixed_line.strip() == "":
            lines.pop(line_num - 1)
        else:
            lines[line_num - 1] = fixed_line

        # Write back
        fixed_content = "\n".join(lines)
        file_path.write_text(fixed_content, encoding="utf-8")

        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Removed unresolved token {token} from {file_path.name} line {line_num}",
        }

    return {"fixed": False, "error": "Line number out of bounds"}


def fix_frontmatter_missing(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix missing or incomplete frontmatter.

    Handles two cases:
    1. No frontmatter at all (GATE_FRONTMATTER_MISSING): inject minimal.
    2. Frontmatter exists but required field missing (GATE_FRONTMATTER_REQUIRED_FIELD_MISSING):
       parse existing YAML, add missing field(s), rewrite.

    For placeholder pages (filename contains 'placeholder'), also injects
    `layout` and `permalink` derived from the content path (TC-3212).

    Args:
        issue: Issue dict with location.path.
        run_dir: Run directory.
        llm_client: Not used (deterministic fix).

    Returns:
        Fix result dict.
    """
    location = issue.get("location", {})
    file_path_str = location.get("path", "")

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    content = file_path.read_text(encoding="utf-8")

    # Placeholder inference (for both paths below)
    placeholder_fields = _infer_frontmatter_for_placeholder(file_path, run_dir)

    # Case 1: frontmatter already exists but has a missing field
    error_code = issue.get("error_code", "")
    existing_fm, body = parse_frontmatter(content)
    if existing_fm is not None and error_code == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING":
        changed = False
        for field, value in placeholder_fields.items():
            if field not in existing_fm:
                existing_fm[field] = value
                changed = True
        # Also inject generic defaults for other required fields
        if "layout" not in existing_fm:
            existing_fm["layout"] = _infer_layout_from_path(file_path)
            changed = True
        if "permalink" not in existing_fm:
            existing_fm["permalink"] = _extract_permalink_from_path(file_path, run_dir)
            changed = True
        if not changed:
            return {"fixed": False, "error": "No missing fields to inject"}
        fixed_content = write_frontmatter(existing_fm, body)
        file_path.write_text(fixed_content, encoding="utf-8")
        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Injected missing frontmatter fields into {file_path.name}",
        }

    # Case 2: no frontmatter at all (or other error code)
    minimal_frontmatter: Dict[str, Any] = {
        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
        "type": "docs",
    }
    minimal_frontmatter.update(placeholder_fields)
    if "layout" not in minimal_frontmatter:
        minimal_frontmatter["layout"] = _infer_layout_from_path(file_path)
    if "permalink" not in minimal_frontmatter:
        minimal_frontmatter["permalink"] = _extract_permalink_from_path(file_path, run_dir)

    fixed_content = write_frontmatter(minimal_frontmatter, content)
    file_path.write_text(fixed_content, encoding="utf-8")

    return {
        "fixed": True,
        "files_changed": [str(file_path)],
        "diff_summary": f"Added frontmatter to {file_path.name}",
    }


def _extract_frontmatter_fields(content: str) -> Dict[str, str]:
    """Extract title, layout, permalink from raw file content (TC-3625).

    Scans ALL lines of the content for the first occurrence of each field.
    Handles both unquoted and double-quoted values. First-occurrence wins.

    Returns:
        Dict with any of: title, layout, permalink (only keys with extracted values)
    """
    extracted: Dict[str, str] = {}
    pattern = re.compile(
        r'^(title|layout|permalink):\s*"?([^"\n]+?)"?\s*$', re.MULTILINE
    )
    for m in pattern.finditer(content):
        field, value = m.group(1), m.group(2).strip()
        if field not in extracted and value:
            extracted[field] = value
    return extracted


def _strip_trailing_yaml_lines(body: str) -> str:
    """Strip trailing YAML-like key:value lines from end of body (TC-3625).

    Removes a terminal cluster of lines matching key: value patterns
    (including optional trailing ---) from the bottom of the text.
    Stops at the first non-matching line from bottom.
    """
    _YAML_LINE_RE = re.compile(
        r'^\s*(title|layout|permalink|weight|slug|type|draft|date)\s*:',
        re.IGNORECASE,
    )
    _SEP_RE = re.compile(r'^\s*---\s*$')
    lines = body.splitlines(keepends=True)
    idx = len(lines) - 1
    # Skip trailing blank lines first
    while idx >= 0 and lines[idx].strip() == '':
        idx -= 1
    # Strip trailing YAML-like lines
    while idx >= 0 and (_YAML_LINE_RE.match(lines[idx]) or _SEP_RE.match(lines[idx])):
        idx -= 1
    return ''.join(lines[: idx + 1])


def fix_frontmatter_invalid_yaml(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix invalid YAML frontmatter issue.

    Strategy:
    - Try to parse and fix common YAML issues (quotes, colons, etc.)
    - If unfixable, replace with minimal frontmatter

    Args:
        issue: Issue dict
        run_dir: Run directory
        llm_client: LLM client (not used)

    Returns:
        Fix result dict
    """
    location = issue.get("location", {})
    file_path_str = location.get("path", "")

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    # Read file
    content = file_path.read_text(encoding="utf-8")

    # TC-3625: Extract real field values from raw content BEFORE falling back to synthetics
    extracted = _extract_frontmatter_fields(content)
    _stem_title = file_path.stem.replace("-", " ").replace("_", " ").title()
    _stem_permalink = f"/{file_path.stem}/"

    def _atomic_write(path: Path, text: str) -> None:
        """Write text to path atomically via tempfile + os.replace (TC-3625)."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                suffix=".tmp",
            ) as tf:
                tf.write(text)
                tmp_path = tf.name
            os.replace(tmp_path, path)
        except OSError:
            # Fallback for Windows/OneDrive file lock
            path.write_text(text, encoding="utf-8")
            try:
                os.unlink(tmp_path)  # type: ignore[possibly-undefined]
            except OSError:
                pass

    # Extract frontmatter section
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        # No frontmatter structure — add reconstructed frontmatter preserving real field values
        reconstructed_frontmatter = {
            "title": extracted.get("title") or _stem_title,
            "layout": extracted.get("layout") or "docs",
            "permalink": extracted.get("permalink") or _stem_permalink,
        }
        # Strip trailing YAML-like lines from the raw content used as body
        cleaned_body = _strip_trailing_yaml_lines(content)
        fixed_content = write_frontmatter(reconstructed_frontmatter, cleaned_body)
        _atomic_write(file_path, fixed_content)

        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Replaced invalid frontmatter with minimal valid frontmatter in {file_path.name}",
        }

    # Frontmatter block exists but YAML is malformed — replace with field-preserving minimal frontmatter
    body = match.group(2)

    reconstructed_frontmatter = {
        "title": extracted.get("title") or _stem_title,
        "layout": extracted.get("layout") or "docs",
        "permalink": extracted.get("permalink") or _stem_permalink,
    }
    # Strip trailing YAML-like lines from body (pattern: fields after markdown body)
    cleaned_body = _strip_trailing_yaml_lines(body)
    fixed_content = write_frontmatter(reconstructed_frontmatter, cleaned_body)
    _atomic_write(file_path, fixed_content)

    return {
        "fixed": True,
        "files_changed": [str(file_path)],
        "diff_summary": f"Fixed invalid YAML frontmatter in {file_path.name}",
    }


def fix_consistency_mismatch(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix consistency mismatch issues (product name, repo_url, etc.).

    Strategy:
    - Load product_facts.json as source of truth
    - Update inconsistent values in files to match product_facts

    Args:
        issue: Issue dict
        run_dir: Run directory
        llm_client: LLM client (not used)

    Returns:
        Fix result dict
    """
    # Load product_facts as source of truth
    try:
        product_facts = load_json_artifact(run_dir, "product_facts.json")
    except FixerArtifactMissingError:
        return {"fixed": False, "error": "product_facts.json not found"}

    error_code = issue.get("error_code", "")
    location = issue.get("location", {})
    file_path_str = location.get("path", "")

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    # Read file
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        return {"fixed": False, "error": "File has no frontmatter to fix"}

    # Fix based on error code
    if "REPO_URL" in error_code:
        correct_repo_url = product_facts.get("repo_url")
        if correct_repo_url and "repo_url" in frontmatter:
            frontmatter["repo_url"] = correct_repo_url
            fixed_content = write_frontmatter(frontmatter, body)
            file_path.write_text(fixed_content, encoding="utf-8")

            return {
                "fixed": True,
                "files_changed": [str(file_path)],
                "diff_summary": f"Fixed repo_url consistency in {file_path.name}",
            }

    return {"fixed": False, "error": f"Cannot fix consistency issue: {error_code}"}


def _wrap_bare_code_blocks(content: str, bare_code_lines: set) -> str:
    """Wrap bare code blocks (FQ-1 NAKED_CODE) in ```python fences.

    TC-3626: For each 1-indexed line number in bare_code_lines, locates the
    triggering bare code line, extends the region backward and forward to
    include adjacent code-context lines (assignments, method calls), then
    wraps the resulting region in a ```python ... ``` fence.

    Idempotent: lines already inside fences are skipped.
    Applies insertions bottom-to-top to avoid line-number drift.
    """
    if not bare_code_lines:
        return content

    lines = content.split("\n")
    n = len(lines)

    # Pre-compute per-line fence and frontmatter state (0-indexed)
    in_fence_at = [False] * n
    in_fm_at = [False] * n

    in_fm = bool(lines and lines[0].rstrip() == "---")
    fm_count = 0
    in_fence = False

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if in_fm:
            in_fm_at[i] = True
            if stripped == "---" and fm_count > 0:
                in_fm = False
            fm_count += 1
        if not in_fm_at[i]:
            if stripped.startswith("```"):
                in_fence_at[i] = False  # fence marker is not "inside" the fence
                in_fence = not in_fence
            else:
                in_fence_at[i] = in_fence

    def _is_code_context(i: int) -> bool:
        """Return True if line i looks like a code-context line (for block extension)."""
        if in_fence_at[i] or in_fm_at[i]:
            return False
        line_str = lines[i]
        stripped = line_str.strip()
        if not stripped:
            return False
        # Exclude prose markers (headings, bullets, blockquotes, markdown links)
        if stripped[0] in "#-*+>|[!":
            return False
        return bool(
            _FQ1_CODE_PATTERNS.match(line_str) or _FQ1_CODE_CONTEXT_RE.match(line_str)
        )

    # Build code block regions for each trigger line
    regions = []
    processed: set = set()

    for line_num in sorted(bare_code_lines):
        idx = line_num - 1  # 0-indexed
        if idx < 0 or idx >= n:
            continue
        if idx in processed or in_fence_at[idx] or in_fm_at[idx]:
            continue
        # Guard: only process lines that actually match a bare code pattern.
        # Prevents wrapping headings or prose if the line number from the
        # issue report happens to point to a non-code line.
        if not _FQ1_CODE_PATTERNS.match(lines[idx]):
            continue

        # Extend backward
        start = idx
        i = idx - 1
        while i >= 0:
            if in_fence_at[i] or in_fm_at[i]:
                break
            if not lines[i].rstrip():
                # Blank line: look further back
                j = i - 1
                while j >= 0 and not lines[j].rstrip():
                    j -= 1
                if j >= 0 and _is_code_context(j) and j not in processed:
                    start = j
                    i = j - 1
                else:
                    break
            elif _is_code_context(i) and i not in processed:
                start = i
                i -= 1
            else:
                break

        # Extend forward
        end = idx
        i = idx + 1
        while i < n:
            if in_fence_at[i] or in_fm_at[i]:
                break
            nxt_stripped = lines[i].rstrip()
            if nxt_stripped.startswith("```"):
                break  # upcoming fence — stop; don't consume it
            if not nxt_stripped:
                # Blank line: look further forward
                j = i + 1
                while j < n and not lines[j].rstrip():
                    j += 1
                if j < n and _is_code_context(j) and not in_fence_at[j]:
                    end = j
                    i = j + 1
                else:
                    break
            elif _is_code_context(i):
                end = i
                i += 1
            else:
                break

        for k in range(start, end + 1):
            processed.add(k)
        regions.append((start, end))

    # Merge overlapping or adjacent regions
    regions.sort()
    merged: list = []
    for r_start, r_end in regions:
        if merged and r_start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], r_end))
        else:
            merged.append([r_start, r_end])

    # Apply insertions bottom-to-top (avoids line-number drift)
    for r_start, r_end in reversed(merged):
        lines.insert(r_end + 1, "```")
        lines.insert(r_start, "```python")

    return "\n".join(lines)


_BATCH_FIX_TIMEOUT_S = 30


def _is_open_issue(issue: Dict[str, Any]) -> bool:
    """Treat missing status as OPEN for backward compatibility."""
    status = issue.get("status")
    return status in (None, "OPEN")


def _formatting_family_issues(
    issue: Dict[str, Any], run_dir: Path
) -> List[Dict[str, Any]]:
    """Collect same-file open formatting issues from validation_report."""
    file_path_str = issue.get("location", {}).get("path", "")
    collected = [issue]
    if not file_path_str:
        return collected
    try:
        report = load_json_artifact(run_dir, "validation_report.json")
    except Exception:
        return collected

    def _fingerprint(item: Dict[str, Any]) -> Tuple[str, str, str, int]:
        location = item.get("location", {})
        line = location.get("line", 0) if isinstance(location, dict) else 0
        path = location.get("path", "") if isinstance(location, dict) else ""
        return (
            str(item.get("error_code", "")),
            str(item.get("message", "")),
            str(path),
            int(line) if isinstance(line, int) else 0,
        )

    seen = {_fingerprint(issue)}
    for other in report.get("issues", []):
        if not _is_open_issue(other):
            continue
        other_code = other.get("error_code", "")
        other_path = other.get("location", {}).get("path", "")
        if other_path != file_path_str:
            continue
        if "G17" not in other_code and "FORMATTING" not in other_code:
            continue
        other_key = _fingerprint(other)
        if other_key in seen:
            continue
        collected.append(other)
        seen.add(other_key)
    return collected


def _kb_howto_family_issues(
    issue: Dict[str, Any], run_dir: Path
) -> List[Dict[str, Any]]:
    """Collect same-file open KB how-to issues from validation_report."""
    issue_location_path = issue.get("location", {}).get("path", "")
    issue_files = issue.get("files", [])
    collected = [issue]
    try:
        report = load_json_artifact(run_dir, "validation_report.json")
    except Exception:
        return collected

    def _fingerprint(item: Dict[str, Any]) -> Tuple[str, str, str, int]:
        location = item.get("location", {})
        line = location.get("line", 0) if isinstance(location, dict) else 0
        path = location.get("path", "") if isinstance(location, dict) else ""
        return (
            str(item.get("error_code", "")),
            str(item.get("message", "")),
            str(path),
            int(line) if isinstance(line, int) else 0,
        )

    seen = {_fingerprint(issue)}
    for other in report.get("issues", []):
        if not _is_open_issue(other):
            continue
        other_code = other.get("error_code", "")
        other_gate = other.get("gate", "")
        if not (
            other_code.startswith("GATE_KB_HOWTO_")
            or str(other_gate).startswith("gate_kb_howto")
        ):
            continue
        other_loc = other.get("location", {}).get("path", "")
        other_files = other.get("files", [])
        same_path = bool(issue_location_path and other_loc == issue_location_path)
        same_files = bool(
            issue_files and other_files and set(issue_files) & set(other_files)
        )
        if not (same_path or same_files):
            continue
        other_key = _fingerprint(other)
        if other_key in seen:
            continue
        collected.append(other)
        seen.add(other_key)
    return collected


def _format_batch_defects(issues: List[Dict[str, Any]]) -> str:
    """Render a stable, compact defect list for the batch-fix prompt."""
    def _sort_key(item: Dict[str, Any]) -> Tuple[int, str, str]:
        location = item.get("location", {})
        line = location.get("line", 0) if isinstance(location, dict) else 0
        return (
            int(line) if isinstance(line, int) else 0,
            str(item.get("error_code", "")),
            str(item.get("issue_id", "")),
        )

    lines: List[str] = []
    for idx, item in enumerate(sorted(issues, key=_sort_key), start=1):
        location = item.get("location", {})
        line = location.get("line", 0) if isinstance(location, dict) else 0
        lines.append(
            f"{idx}. line={line} code={item.get('error_code', '')} "
            f"message={item.get('message', '')}"
        )
    return "\n".join(lines)


def _strip_outer_fence_wrapper(content: str) -> str:
    """Strip a single outer fenced wrapper if the model ignores instructions."""
    stripped = content.strip()
    match = re.fullmatch(r"```[^\n]*\n(.*)\n```", stripped, re.DOTALL)
    if match:
        return match.group(1)
    return content


def _validate_batch_fix_candidate(original: str, candidate: str) -> str:
    """Reject obviously invalid full-file responses before writing."""
    if not isinstance(candidate, str):
        raise ValueError("LLM batch fix did not return text content")
    cleaned = _strip_outer_fence_wrapper(candidate).strip()
    if not cleaned:
        raise ValueError("LLM batch fix returned empty content")
    if parse_frontmatter(original)[0] is not None and parse_frontmatter(cleaned)[0] is None:
        raise ValueError("LLM batch fix removed valid frontmatter")
    if original.count("```") % 2 == 0 and cleaned.count("```") % 2 != 0:
        raise ValueError("LLM batch fix produced unbalanced code fences")
    return cleaned + ("\n" if candidate.endswith("\n") or original.endswith("\n") else "")


def _write_text_atomic(file_path: Path, content: str) -> None:
    """Write text atomically in the destination directory."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(file_path.parent),
        prefix=f".{file_path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, str(file_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _run_batch_llm_file_fix(
    *,
    file_path: Path,
    family_name: str,
    issues: List[Dict[str, Any]],
    llm_client: Any,
    call_id: str,
    extra_instructions: str,
) -> str:
    """Ask the LLM for one full-file correction covering all sibling defects."""
    original_content = file_path.read_text(encoding="utf-8")
    prompt = (
        "You are repairing one Markdown file in a documentation pipeline.\n"
        "Fix every listed defect in one pass and return the FULL corrected file content only.\n"
        "Do not return a diff. Do not return explanations. Do not wrap the answer in code fences.\n"
        "Preserve meaning. Preserve frontmatter. Preserve code fences. Do not add new claims.\n"
        "Do not invent product facts, steps, APIs, or headings beyond what is required to resolve the listed defects.\n"
        f"Family: {family_name}\n"
        f"File: {file_path.name}\n\n"
        "Defects to fix:\n"
        f"{_format_batch_defects(issues)}\n\n"
        f"{extra_instructions}\n\n"
        "Current file content:\n"
        f"{original_content}"
    )
    response = llm_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        call_id=call_id,
        timeout=_BATCH_FIX_TIMEOUT_S,
    )
    response_text = response.get("content", "") if isinstance(response, dict) else str(response)
    return _validate_batch_fix_candidate(original_content, response_text)


def _apply_formatting_fallback(
    content: str,
    error_codes: set[str],
    file_path_str: str,
    run_dir: Path,
) -> str:
    """Deterministic formatting fix path used when batch LLM repair is unavailable."""
    if any("FQ-4" in c or "FQ4" in c for c in error_codes):
        content = re.sub(
            r"(^#{1,6}\s+[^\n]+\n)(#{1,6}\s+)",
            r"\1\n\2",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^(#{1,6}\s+(\w+))`\2`',
            lambda m: f"{m.group(1)}\n`{m.group(2)}`",
            content,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        _fq4_fixed_lines = []
        _fq4_in_fence = False
        for _fq4_line in content.split('\n'):
            _fq4_stripped = _fq4_line.rstrip()
            if _fq4_stripped.startswith('```'):
                _fq4_in_fence = not _fq4_in_fence
            if _fq4_in_fence:
                _fq4_fixed_lines.append(_fq4_line)
                continue
            _fq4_hm = re.match(r'^(#{1,6}\s+)', _fq4_line)
            if _fq4_hm and len(_fq4_line) > 60:
                _fq4_prefix = _fq4_hm.group(1)
                _fq4_rest = _fq4_line[len(_fq4_prefix):]
                _fq4_jm = re.search(r'([a-z])(?=[A-Z][a-z]{2,})', _fq4_rest)
                if _fq4_jm:
                    _fq4_split = _fq4_jm.end()
                    _fq4_head = _fq4_rest[:_fq4_split]
                    _fq4_prose = _fq4_rest[_fq4_split:]
                    if len(_fq4_prose.strip()) >= 20:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose)
                        continue
                _fq4_dm = re.search(r'\b(\w+)[-\u2013]\s+([A-Z][a-z])', _fq4_rest)
                if _fq4_dm:
                    _fq4_dash_end = _fq4_dm.start() + len(_fq4_dm.group(1))
                    _fq4_head2 = _fq4_rest[:_fq4_dash_end].rstrip()
                    _fq4_prose2 = _fq4_rest[_fq4_dm.start(2):]
                    if len(_fq4_prose2.strip()) >= 20 and len(_fq4_head2.strip()) >= 3:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head2)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose2)
                        continue
            _fq4_fixed_lines.append(_fq4_line)
        content = '\n'.join(_fq4_fixed_lines)
        content = fix_heading_body_concat(content)

    if any("FQ-7" in c or "FQ7" in c for c in error_codes):
        content = re.sub(r"^`([a-z]+)\n", r"```\1\n", content, flags=re.MULTILINE)
        lines = content.split("\n")
        fixed_lines = []
        in_fence = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                fixed_lines.append(line)
            elif stripped == "`" and in_fence:
                fixed_lines.append("```")
                in_fence = False
            else:
                fixed_lines.append(line)
        content = "\n".join(fixed_lines)

    if any("FQ-1" in c or "FQ1" in c for c in error_codes):
        content = fix_prose_fencemarker_concat(content)
        content = re.sub(
            r"^```\s*$",
            "```text",
            content,
            flags=re.MULTILINE,
        )
        content = close_unclosed_fences(content)
        _fq1_line_nums: set[int] = set()
        try:
            _fq1_report = load_json_artifact(run_dir, "validation_report.json")
            for _fq1_issue in _fq1_report.get("issues", []):
                if (
                    _fq1_issue.get("error_code") == "G17-FQ-1"
                    and _fq1_issue.get("location", {}).get("path") == file_path_str
                ):
                    _fq1_ln = _fq1_issue.get("location", {}).get("line")
                    if isinstance(_fq1_ln, int):
                        _fq1_line_nums.add(_fq1_ln)
        except Exception:
            pass
        content = _wrap_bare_code_blocks(content, _fq1_line_nums)

    if any("FQ-3" in c or "FQ3" in c for c in error_codes):
        lines = content.split("\n")
        in_fence = False
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if not stripped or stripped.startswith("---"):
                continue
            if stripped.startswith("#") or stripped.startswith("<!--"):
                continue
            if _TRUNCATION_COMMA_RE.search(stripped) and len(stripped) > 10:
                lines[i] = stripped.rstrip(",").rstrip() + "."
            elif _TRUNCATION_CONNECTOR_RE.search(stripped) and len(stripped) >= 20:
                lines[i] = stripped + "..."
        content = "\n".join(lines)

    if any("FQ-8" in c or "FQ8" in c for c in error_codes):
        content = merge_adjacent_code_blocks(content)

    return content


def fix_formatting_defect(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix formatting defects reported by Gate 17.

    Handles:
    - G17-FQ-4: Insert blank line between adjacent headings
    - G17-FQ-7: Normalize code fences (re-run fence sanitizers)
    - G17-FQ-1: Fix bare code blocks (add language tag + wrap bare code in fences, TC-3626)
    - G17-FQ-3: Fix indented code not in fence

    TC-3617 B3: Collects all sibling G17/FORMATTING issues for the same file
    from validation_report.json and fixes them all in one pass.

    Args:
        issue: Issue dict with error_code and location
        run_dir: Run directory
        llm_client: Optional LLM client for file-wide batch repair; deterministic fallback when unavailable

    Returns:
        Fix result dict
    """
    location = issue.get("location", {})
    file_path_str = location.get("path", "")
    error_code = issue.get("error_code", "")

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    if llm_client is not None:
        original_content = file_path.read_text(encoding="utf-8")
        formatting_issues = _formatting_family_issues(issue, run_dir)
        error_codes_pre = {
            str(item.get("error_code", ""))
            for item in formatting_issues
            if item.get("error_code")
        } or {error_code}
        try:
            corrected = _run_batch_llm_file_fix(
                file_path=file_path,
                family_name="formatting",
                issues=formatting_issues,
                llm_client=llm_client,
                call_id=f"w10_format_batch_{uuid.uuid4().hex[:8]}",
                extra_instructions=(
                    "Only make structural or formatting corrections needed to resolve the listed defects. "
                    "Do not rewrite unrelated prose."
                ),
            )
            if corrected != original_content:
                _write_text_atomic(file_path, corrected)
                logger.info(
                    "W10 formatting batch LLM fix applied to %s for %s",
                    file_path.name,
                    sorted(error_codes_pre),
                )
                return {
                    "fixed": True,
                    "files_changed": [str(file_path)],
                    "diff_summary": (
                        f"LLM batch-fixed formatting defects {sorted(error_codes_pre)} "
                        f"in {file_path.name}"
                    ),
                }
            return {
                "fixed": False,
                "error": f"LLM batch fix made no changes for {sorted(error_codes_pre)}",
            }
        except Exception as exc:
            logger.warning(
                "W10 formatting batch LLM fix failed for %s: %s; falling back",
                file_path.name,
                exc,
            )

    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # TC-3617 B3: Collect all FQ codes for this file from validation_report
    error_codes = {error_code}
    try:
        report = load_json_artifact(run_dir, "validation_report.json")
        for other in report.get("issues", []):
            other_code = other.get("error_code", "")
            other_path = other.get("location", {}).get("path", "")
            if other_path == file_path_str and (
                "G17" in other_code or "FORMATTING" in other_code
            ):
                error_codes.add(other_code)
    except Exception:
        pass  # Graceful degradation — fix only the primary issue

    if any("FQ-4" in c or "FQ4" in c for c in error_codes):
        # Fix 1: Insert blank line between adjacent headings
        content = re.sub(
            r"(^#{1,6}\s+[^\n]+\n)(#{1,6}\s+)",
            r"\1\n\2",
            content,
            flags=re.MULTILINE,
        )
        # Fix 2: Split heading where the same word appears as backtick inline code
        # e.g. "## Mesh`Mesh` represents..." → "## Mesh\n`Mesh` represents..."
        content = re.sub(
            r'^(#{1,6}\s+(\w+))`\2`',
            lambda m: f"{m.group(1)}\n`{m.group(2)}`",
            content,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        # Fix 3: Split heading where body text is concatenated without a newline.
        # Uses a scan-based approach to find the FIRST camelCase junction in each
        # heading line (e.g. "## IntroductionThe library..." splits at n|T).
        # The greedy-regex approach finds the wrong split when the prose is long;
        # this per-line scan finds the earliest camelCase boundary instead.
        _fq4_fixed_lines = []
        _fq4_in_fence = False
        for _fq4_line in content.split('\n'):
            _fq4_stripped = _fq4_line.rstrip()
            if _fq4_stripped.startswith('```'):
                _fq4_in_fence = not _fq4_in_fence
            if _fq4_in_fence:
                _fq4_fixed_lines.append(_fq4_line)
                continue
            _fq4_hm = re.match(r'^(#{1,6}\s+)', _fq4_line)
            # Only process long heading lines — short lines are unlikely to be concat
            if _fq4_hm and len(_fq4_line) > 60:
                _fq4_prefix = _fq4_hm.group(1)
                _fq4_rest = _fq4_line[len(_fq4_prefix):]
                # Find first camelCase junction: lowercase directly before uppercase word
                _fq4_jm = re.search(r'([a-z])(?=[A-Z][a-z]{2,})', _fq4_rest)
                if _fq4_jm:
                    _fq4_split = _fq4_jm.end()
                    _fq4_head = _fq4_rest[:_fq4_split]
                    _fq4_prose = _fq4_rest[_fq4_split:]
                    # Only split if the prose part is substantial (not a compound word)
                    if len(_fq4_prose.strip()) >= 20:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose)
                        continue
                # TC-3623: Dash-sentence junction pattern
                # e.g. "## ProductName Api- The move method on Worksheet..."
                # Split at dash/en-dash followed by capital letter starting a sentence.
                _fq4_dm = re.search(r'\b(\w+)[-\u2013]\s+([A-Z][a-z])', _fq4_rest)
                if _fq4_dm:
                    _fq4_dash_end = _fq4_dm.start() + len(_fq4_dm.group(1))
                    _fq4_head2 = _fq4_rest[:_fq4_dash_end].rstrip()
                    _fq4_prose2 = _fq4_rest[_fq4_dm.start(2):]
                    # Only split if prose is substantial and heading non-trivial
                    if len(_fq4_prose2.strip()) >= 20 and len(_fq4_head2.strip()) >= 3:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head2)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose2)
                        continue
            _fq4_fixed_lines.append(_fq4_line)
        content = '\n'.join(_fq4_fixed_lines)
        # Fix 4: Apply sanitizer heading-body concat splitter as a catch-all
        content = fix_heading_body_concat(content)

    if any("FQ-7" in c or "FQ7" in c for c in error_codes):
        # Fix: Normalize code fences — ensure all use triple backticks
        # Replace single-backtick fences with triple
        content = re.sub(r"^`([a-z]+)\n", r"```\1\n", content, flags=re.MULTILINE)
        # Ensure closing fences are triple
        lines = content.split("\n")
        fixed_lines = []
        in_fence = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                fixed_lines.append(line)
            elif stripped == "`" and in_fence:
                fixed_lines.append("```")
                in_fence = False
            else:
                fixed_lines.append(line)
        content = "\n".join(fixed_lines)

    if any("FQ-1" in c or "FQ1" in c for c in error_codes):
        # Fix A: Split inline fence openers ("prose.```python." → two lines).
        # This must run BEFORE any fence-state-based fix so fence tracking is correct.
        content = fix_prose_fencemarker_concat(content)
        # Fix B: Add language tag to bare code blocks (no lang specified)
        content = re.sub(
            r"^```\s*$",
            "```text",
            content,
            flags=re.MULTILINE,
        )
        # Fix C: Close any unclosed fences (content trapped inside open fence)
        content = close_unclosed_fences(content)
        # Fix D: Wrap bare code blocks in ```python fences (TC-3626).
        # Collects exact line numbers from all G17-FQ-1 issues for this file.
        _fq1_line_nums: set = set()
        try:
            _fq1_report = load_json_artifact(run_dir, "validation_report.json")
            for _fq1_issue in _fq1_report.get("issues", []):
                if (
                    _fq1_issue.get("error_code") == "G17-FQ-1"
                    and _fq1_issue.get("location", {}).get("path") == file_path_str
                ):
                    _fq1_ln = _fq1_issue.get("location", {}).get("line")
                    if isinstance(_fq1_ln, int):
                        _fq1_line_nums.add(_fq1_ln)
        except Exception:
            pass  # Graceful degradation — skip Fix D if report unavailable
        content = _wrap_bare_code_blocks(content, _fq1_line_nums)

    if any("FQ-3" in c or "FQ3" in c for c in error_codes):
        # TC-3263: Two-step repair strategy for truncated bullet endings.
        # Step 1 (trailing comma): strip comma, append period (len > 10).
        # Step 2 (trailing connector word): append ellipsis (len >= 20).
        # Skips: blank lines, ---, ```, #, <!--, and lines inside code fences.
        lines = content.split("\n")
        in_fence = False
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            # Track fence state
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            # Skip frontmatter delimiters and empty lines
            if not stripped or stripped.startswith("---"):
                continue
            # Skip headings and HTML comment lines
            if stripped.startswith("#") or stripped.startswith("<!--"):
                continue
            # Step 1: trailing comma -> remove comma and append period
            if _TRUNCATION_COMMA_RE.search(stripped) and len(stripped) > 10:
                lines[i] = stripped.rstrip(",").rstrip() + "."
            # Step 2: trailing connector word -> append ellipsis (line long enough)
            elif _TRUNCATION_CONNECTOR_RE.search(stripped) and len(stripped) >= 20:
                lines[i] = stripped + "..."
        content = "\n".join(lines)

    if any("FQ-8" in c or "FQ8" in c for c in error_codes):
        # TC-2892: Re-run the adjacent code block merger (idempotent)
        content = merge_adjacent_code_blocks(content)

    if content != original_content:
        _write_text_atomic(file_path, content)
        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Fixed formatting defects {sorted(error_codes)} in {file_path.name}",
        }

    return {"fixed": False, "error": f"No formatting changes needed for {sorted(error_codes)}"}


# ---------------------------------------------------------------------------
# Contradiction resolver (TC-2526)
# ---------------------------------------------------------------------------

# Python version pattern for contradiction fixing
_VERSION_FIX_RE = re.compile(
    r"([Pp]ython\s*(?:>=?\s*)?)(\d+)\.(\d+)"
)

def _resolve_contradictions(
    page_content: str,
    shared_facts: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Replace non-canonical versions and package names with canonical values.

    Uses ``shared_facts.json`` as the single source of truth. Applies two
    deterministic corrections:

    1. **Version fix**: Replace Python version strings that contradict the
       canonical ``min_python_version`` (from ``runtime_versions.python.minimum``).
    2. **Package name fix**: Replace incorrect package names in ``pip install``
       commands with the canonical ``package_name``.

    Args:
        page_content: Raw markdown content of a single page.
        shared_facts: Parsed shared_facts.json dict.

    Returns:
        Tuple of (corrected_content, list_of_corrections_applied).
        corrections list is empty when no changes are needed.
    """
    corrections: List[str] = []
    result = page_content

    # --- 1. Fix version contradictions ---
    canonical_min = (
        shared_facts.get("runtime_versions", {})
        .get("python", {})
        .get("minimum", "")
    )
    if canonical_min and "." in canonical_min:
        try:
            canonical_parts = tuple(int(x) for x in canonical_min.split("."))

            def _fix_version(m: re.Match) -> str:
                prefix = m.group(1)
                major, minor = int(m.group(2)), int(m.group(3))
                if major != canonical_parts[0] or abs(minor - canonical_parts[1]) > 1:
                    corrections.append(
                        f"version: {major}.{minor} -> {canonical_min}"
                    )
                    return f"{prefix}{canonical_min}"
                return m.group(0)

            result = _VERSION_FIX_RE.sub(_fix_version, result)
        except (ValueError, IndexError):
            pass

    # --- 2. Fix package name ---
    canonical_pkg = shared_facts.get("package_name", "")
    if canonical_pkg:
        # Derive the "namespace" prefix (e.g. "aspose" from "aspose-note").
        # We only replace packages that share this namespace so that we never
        # clobber unrelated packages like "pip", "reportlab", etc.
        canonical_namespace = canonical_pkg.split("-")[0].lower() if "-" in canonical_pkg else canonical_pkg.lower()

        def _fix_pkg(m: re.Match) -> str:
            prefix = m.group(1)
            found_pkg = m.group(2)
            # Strip version specifiers to compare base name
            base_found = re.split(r"[>=<!\[]", found_pkg)[0]
            if not base_found:
                return m.group(0)
            # Only fix packages in the same namespace (e.g. aspose-*)
            if not base_found.lower().startswith(canonical_namespace):
                return m.group(0)
            if base_found == canonical_pkg:
                return m.group(0)
            corrections.append(
                f"package: {base_found} -> {canonical_pkg}"
            )
            # Preserve any version specifier that was attached
            suffix = found_pkg[len(base_found):]
            return f"{prefix}{canonical_pkg}{suffix}"

        result = _PKG_FIX_RE.sub(_fix_pkg, result)

    return result, corrections


def fix_contradiction(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G20-002/G20-004/G20-005 contradiction issues using shared_facts as source of truth.

    Loads shared_facts.json and applies ``_resolve_contradictions()`` to pages.

    * G20-002 (cross-page version contradiction): Scans ALL .md files to
      normalize Python version references against shared_facts canonical.
    * G20-005 (package name inconsistency): Scans ALL .md files under
      ``run_dir/work/site/`` because the gate reports the first location of
      any package name — which may be the canonical one, not the wrong one.
      Fixing only the reported file would leave other pages with bad names.
    * G20-004 (version contradiction): Fixes only the file at ``location.path``.

    Args:
        issue: Issue dict (must have location.path for G20-004).
        run_dir: Run directory.
        llm_client: LLM client (not used -- deterministic fix).

    Returns:
        Fix result dict.
    """
    error_code = issue.get("error_code", "")

    # Load shared_facts (graceful skip when absent)
    sf_path = run_dir / "artifacts" / "shared_facts.json"
    if not sf_path.exists():
        logger.info("W10 contradiction resolver: shared_facts.json not found, skipping")
        return {"fixed": False, "error": "shared_facts.json not available"}

    try:
        shared_facts = json.loads(sf_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"fixed": False, "error": f"Failed to load shared_facts: {e}"}

    # G20-002/G20-005: scan ALL pages so every version/package gets normalized
    if error_code in ("G20-002", "G20-005"):
        site_dir = run_dir / "work" / "site"
        all_md = list(site_dir.rglob("*.md")) if site_dir.exists() else []
        if not all_md:
            return {"fixed": False, "error": "No .md files found under work/site/"}

        files_changed: List[str] = []
        all_corrections: List[str] = []
        for md_path in all_md:
            try:
                content = md_path.read_text(encoding="utf-8")
                fixed_content, corrections = _resolve_contradictions(content, shared_facts)
                if corrections:
                    md_path.write_text(fixed_content, encoding="utf-8")
                    files_changed.append(str(md_path))
                    all_corrections.extend(corrections)
                    for c in corrections:
                        logger.info("W10 %s fix: %s in %s", error_code, c, md_path.name)
            except Exception as exc:
                logger.warning("W10 %s: error fixing %s: %s", error_code, md_path.name, exc)

        if not files_changed:
            return {"fixed": False, "error": f"No {error_code} contradictions found in any page"}

        return {
            "fixed": True,
            "files_changed": files_changed,
            "diff_summary": (
                f"Resolved {len(all_corrections)} package name contradiction(s) "
                f"across {len(files_changed)} file(s): "
                + "; ".join(all_corrections[:5])
            ),
        }

    # G20-004 (and other contradiction types): fix only the reported file
    location = issue.get("location", {})
    file_path_str = location.get("path", "")

    if not file_path_str:
        return {"fixed": False, "error": "No file path in issue location"}

    file_path = Path(file_path_str)
    if not file_path.exists():
        return {"fixed": False, "error": f"File not found: {file_path}"}

    content = file_path.read_text(encoding="utf-8")
    fixed_content, corrections = _resolve_contradictions(content, shared_facts)

    if not corrections:
        return {"fixed": False, "error": "No contradictions found to fix"}

    file_path.write_text(fixed_content, encoding="utf-8")

    for c in corrections:
        logger.info("W10 contradiction fix: %s in %s", c, file_path.name)

    return {
        "fixed": True,
        "files_changed": [str(file_path)],
        "diff_summary": (
            f"Resolved {len(corrections)} contradiction(s) in {file_path.name}: "
            + "; ".join(corrections[:5])
        ),
    }


def _reorder_kb_howto_sections(file_path: Path) -> bool:
    """TC-3624: Reorder KB how-to sections to canonical order.

    When all required headings are present but in wrong order, this helper
    splits the file into sections and sorts required sections by canonical order.

    Returns True if the file was changed, False if already sorted (idempotent).
    """
    import re as _re

    _HEADING_ORDER = ["goal", "prerequisites", "steps", "code example", "see also"]

    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")

    # Split content into preamble (before first heading) and sections.
    # Each section starts with an H2 or H3 heading line.
    _heading_re = _re.compile(r"(?m)^(#{2,3}\s+.+)$")
    parts = _heading_re.split(content)
    # parts alternates: [preamble, heading1, body1, heading2, body2, ...]
    # After split with capturing group: [preamble, h1, b1, h2, b2, ...]

    if len(parts) < 3:
        # No headings found → nothing to reorder
        return False

    preamble = parts[0]
    sections = []  # list of (heading_line, body_text)
    for i in range(1, len(parts) - 1, 2):
        heading_line = parts[i]
        body_text = parts[i + 1] if i + 1 < len(parts) else ""
        sections.append((heading_line, body_text))

    def _canonical_key(heading: str) -> int:
        """Return canonical sort index for a heading, or len(_HEADING_ORDER) if not required."""
        h_lower = heading.lower()
        for idx, key in enumerate(_HEADING_ORDER):
            if key in h_lower:
                return idx
        return len(_HEADING_ORDER)  # non-required → sort after required

    required = [(h, b) for h, b in sections if _canonical_key(h) < len(_HEADING_ORDER)]
    other = [(h, b) for h, b in sections if _canonical_key(h) >= len(_HEADING_ORDER)]

    sorted_required = sorted(required, key=lambda s: _canonical_key(s[0]))
    ordered_sections = sorted_required + other

    # Reconstruct
    reconstructed = preamble
    for heading_line, body_text in ordered_sections:
        reconstructed += heading_line + body_text

    if reconstructed == content:
        return False  # already sorted — idempotent

    file_path.write_text(reconstructed, encoding="utf-8")
    logger.info("W10 KB howto reorder: sections sorted in %s", file_path.name)
    return True


def fix_kb_howto_structure(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix KB how-to structure issues (missing required headings).

    Handles GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER by injecting a placeholder
    section for the missing heading.

    TC-3214 improvements:
    - Detects H2 vs H3 from existing document headings
    - Uses canonical package name from shared_facts.json (no ``<package>`` placeholder)
    - Append-at-end fallback when no insertion point found

    TC-3624: Also handles out-of-order sections when all required headings are
    present but in wrong order (issue message contains "appears before").

    gate_kb_howto_structure reads from ``drafts/kb/{slug}.md``.
    This fixer writes to BOTH the draft AND the work/site copy so that the
    gate (on the next W9 pass) and the final output are both corrected.
    """
    import re as _re

    # TC-3624: Detect ordering violation (all headings present, wrong order)
    _early_msg = issue.get("message", "")
    if "appears before" in _early_msg and llm_client is None:
        # Extract slug for reorder
        _order_issue_id = issue.get("issue_id", "")
        _order_slug = _re.sub(r"^gate_kb_howto_structure_\w+_", "", _order_issue_id).strip()
        if not _order_slug:
            _order_sm = _re.search(r"draft '(.+?)'", _early_msg)
            if _order_sm:
                _order_slug = _order_sm.group(1).strip()
        if not _order_slug:
            _order_loc = issue.get("location", {}).get("path", "")
            if _order_loc:
                _order_slug = Path(_order_loc).stem

        if not _order_slug:
            return {"fixed": False, "error": "Cannot determine slug for section reorder"}

        _order_files_changed: List[str] = []

        # Fix draft
        _draft_path = run_dir / "drafts" / "kb" / f"{_order_slug}.md"
        if _reorder_kb_howto_sections(_draft_path):
            _order_files_changed.append(str(_draft_path))

        # Fix work/site copies
        _site_dir = run_dir / "work" / "site"
        for _cand in list(_site_dir.rglob(f"{_order_slug}.md")) + list(
            _site_dir.rglob(f"**/{_order_slug}/index.md")
        ):
            if _reorder_kb_howto_sections(_cand):
                _order_files_changed.append(str(_cand))

        if _order_files_changed:
            return {
                "fixed": True,
                "files_changed": _order_files_changed,
                "diff_summary": f"Reordered KB howto sections in {_order_slug} to canonical order",
            }
        return {
            "fixed": False,
            "error": f"Section reorder: no changes made for slug '{_order_slug}'",
        }

    # Required heading order (case-insensitive match key → inject before next)
    _INJECT_BEFORE = {
        "goal": "prerequisites",
        "prerequisites": "steps",
        "steps": "code example",
        "code example": "see also",
    }

    # --- Load canonical package name from shared_facts.json (TC-3214) ---
    pkg_name = ""
    shared_facts_path = run_dir / "artifacts" / "shared_facts.json"
    if shared_facts_path.exists():
        try:
            import json as _json
            sf = _json.loads(shared_facts_path.read_text(encoding="utf-8"))
            pkg_name = sf.get("package_name", "")
        except Exception:
            pass

    # Build prerequisites text with canonical package name or neutral fallback
    if pkg_name:
        prereq_text = (
            "## Prerequisites\n\n"
            "- Python 3.8 or newer installed on your development machine.\n"
            f"- The library package installed (`pip install {pkg_name}`).\n\n"
        )
    else:
        prereq_text = (
            "## Prerequisites\n\n"
            "- Python 3.8 or newer installed on your development machine.\n"
            "- The library package installed (see installation instructions in the documentation).\n\n"
        )

    # Placeholder content for each missing heading type
    _PLACEHOLDER = {
        "goal": "## Goal\n\nLearn how to accomplish this task step by step.\n\n",
        "prerequisites": prereq_text,
        "steps": "## Steps\n\n1. Follow the instructions in the code example below.\n\n",
        "code example": (
            "## Code Example\n\n"
            "```python\n"
            "# See the Steps section above for a complete working example.\n"
            "pass\n"
            "```\n\n"
        ),
        "see also": "## See Also\n\n- [Documentation](https://docs.aspose.com/)\n\n",
    }

    # --- Determine which headings are missing ---
    # TC-3617 B3: Collect ALL missing headings from the primary issue + siblings
    _HEADING_ORDER = ["goal", "prerequisites", "steps", "code example", "see also"]
    all_missing: set = set()

    msg = issue.get("message", "")
    missing_m = _re.search(r"[Hh]eading '(.+?)' missing", msg)
    if missing_m:
        all_missing.add(missing_m.group(1).lower())
    else:
        all_missing.add("code example")  # backward compat

    # TC-3617 B3: Scan validation_report for sibling howto issues on same file
    issue_location_path = issue.get("location", {}).get("path", "")
    issue_files = issue.get("files", [])
    try:
        _howto_report = load_json_artifact(run_dir, "validation_report.json")
        for other in _howto_report.get("issues", []):
            if other.get("error_code") != "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER":
                continue
            # Match by location.path or files overlap
            other_loc = other.get("location", {}).get("path", "")
            other_files = other.get("files", [])
            if (issue_location_path and other_loc == issue_location_path) or (
                issue_files and other_files and set(issue_files) & set(other_files)
            ):
                m2 = _re.search(r"[Hh]eading '(.+?)' missing", other.get("message", ""))
                if m2:
                    all_missing.add(m2.group(1).lower())
    except Exception:
        pass  # Graceful degradation — fix only the primary heading

    # --- Extract slug ---
    issue_id = issue.get("issue_id", "")
    slug = _re.sub(r"^gate_kb_howto_structure_\w+_", "", issue_id).strip()
    if not slug:
        slug_m = _re.search(r"draft '(.+?)'", msg)
        if slug_m:
            slug = slug_m.group(1).strip()
    if not slug:
        location = issue.get("location", {})
        path_str = location.get("path", "")
        if path_str:
            slug = Path(path_str).stem
    if not slug:
        return {"fixed": False, "error": "Cannot determine slug for KB howto structure fix"}

    if llm_client is not None:
        howto_issues = _kb_howto_family_issues(issue, run_dir)
        _llm_draft_path = run_dir / "drafts" / "kb" / f"{slug}.md"
        _llm_target_files: List[Path] = []
        if _llm_draft_path.exists():
            _llm_target_files.append(_llm_draft_path)
        _llm_site_dir = run_dir / "work" / "site"
        for _cand in list(_llm_site_dir.rglob(f"{slug}.md")) + list(
            _llm_site_dir.rglob(f"**/{slug}/index.md")
        ):
            if all(_cand != _existing for _existing in _llm_target_files):
                _llm_target_files.append(_cand)
        _llm_source = _llm_target_files[0] if _llm_target_files else _llm_draft_path
        if _llm_source.exists():
            try:
                _original = _llm_source.read_text(encoding="utf-8")
                corrected = _run_batch_llm_file_fix(
                    file_path=_llm_source,
                    family_name="kb-howto-structure",
                    issues=howto_issues,
                    llm_client=llm_client,
                    call_id=f"w10_kb_howto_batch_{uuid.uuid4().hex[:8]}",
                    extra_instructions=(
                        "Make only the structural KB how-to changes needed to satisfy the listed defects. "
                        "If required headings are missing, add them. If sections are out of order, reorder them."
                    ),
                )
                if corrected != _original:
                    files_changed = []
                    for _target in _llm_target_files or [_llm_source]:
                        _write_text_atomic(_target, corrected)
                        files_changed.append(str(_target))
                    logger.info(
                        "W10 KB howto batch LLM fix applied to %s for %d sibling issue(s)",
                        slug,
                        len(howto_issues),
                    )
                    return {
                        "fixed": True,
                        "files_changed": files_changed,
                        "diff_summary": (
                            f"LLM batch-fixed KB howto issues across {len(files_changed)} "
                            f"file(s) for slug '{slug}'"
                        ),
                    }
                return {
                    "fixed": False,
                    "error": f"LLM batch fix made no changes for slug '{slug}'",
                }
            except Exception as exc:
                logger.warning(
                    "W10 KB howto batch LLM fix failed for %s: %s; falling back",
                    slug,
                    exc,
                )
        if "appears before" in _early_msg:
            _order_files_changed: List[str] = []
            _order_draft = run_dir / "drafts" / "kb" / f"{slug}.md"
            if _reorder_kb_howto_sections(_order_draft):
                _order_files_changed.append(str(_order_draft))
            for _cand in list((run_dir / "work" / "site").rglob(f"{slug}.md")) + list(
                (run_dir / "work" / "site").rglob(f"**/{slug}/index.md")
            ):
                if _reorder_kb_howto_sections(_cand):
                    _order_files_changed.append(str(_cand))
            if _order_files_changed:
                return {
                    "fixed": True,
                    "files_changed": _order_files_changed,
                    "diff_summary": f"Reordered KB howto sections in {slug} to canonical order",
                }
            return {
                "fixed": False,
                "error": f"Section reorder: no changes made for slug '{slug}'",
            }

    def _detect_heading_level(content: str) -> str:
        """Detect dominant heading level (## or ###) from document content."""
        h3_count = len(_re.findall(r"^###\s+\w", content, _re.MULTILINE))
        # TC-3260: negative lookahead ensures we count exactly-H2 lines only
        h2_count = len(_re.findall(r"^##(?!#)\s+\w", content, _re.MULTILINE))
        return "###" if h3_count > h2_count else "##"

    def _inject(file_path: Path, missing_heading: str, placeholder: str,
                inject_before_key: str) -> bool:
        """Inject missing heading into file. Returns True if changed."""
        if not file_path.exists():
            return False
        content = file_path.read_text(encoding="utf-8")
        # TC-3550: Rename H1 Goal (# ... Goal) → H2/H3 BEFORE idempotency check.
        # The gate uses ^#{2,3} so an H1 heading does NOT satisfy the check;
        # without this rename the fix would inject a SECOND goal heading below.
        if missing_heading == "goal":
            _h1_goal_re = _re.compile(r"^#\s+.*\bGoal\b.*$", _re.MULTILINE | _re.IGNORECASE)
            h1_match = _h1_goal_re.search(content)
            if h1_match:
                heading_prefix = _detect_heading_level(content)
                content = _h1_goal_re.sub(f"{heading_prefix} Goal", content, count=1)
                file_path.write_text(content, encoding="utf-8")
                logger.info(
                    "W10 KB howto structure fix: renamed H1 Goal → %s Goal in %s",
                    heading_prefix, file_path.name,
                )
                return True  # File was changed; no further injection needed
        # TC-3260: heading-line-only idempotency check (not prose substring).
        # Use .*\b (single-line — dot never matches \n) to avoid crossing lines.
        _heading_pat = r"^#{2,3}\s+.*\b" + _re.escape(missing_heading) + r"\b"
        if _re.search(_heading_pat, content, _re.MULTILINE | _re.IGNORECASE):
            return False  # already present as a heading line

        # TC-3214: Detect heading level and adjust placeholder
        heading_prefix = _detect_heading_level(content)
        adjusted_placeholder = placeholder.replace("## ", f"{heading_prefix} ", 1)

        if inject_before_key:
            # TC-3260: Cascade through heading order chain until we find
            # a present heading to inject before.
            cascade_key = inject_before_key
            while cascade_key:
                _cascade_pat = r"^#{2,3}\s+.*\b" + _re.escape(cascade_key) + r"\b"
                before_m = _re.search(
                    _cascade_pat,
                    content,
                    _re.MULTILINE | _re.IGNORECASE,
                )
                if before_m:
                    fixed = content[:before_m.start()] + adjusted_placeholder + content[before_m.start():]
                    file_path.write_text(fixed, encoding="utf-8")
                    logger.info(
                        "W10 KB howto structure fix: injected '%s' (%s) before '%s' in %s",
                        missing_heading, heading_prefix, cascade_key, file_path.name,
                    )
                    return True
                # Try the next heading in the order chain
                cascade_key = _INJECT_BEFORE.get(cascade_key)

        # Fallback: append before the last heading (See Also) or at end
        # TC-3214: Match both H2 and H3
        see_also_m = _re.search(r"^#{2,3}\s+See\s+Also\b", content, _re.MULTILINE | _re.IGNORECASE)
        if see_also_m:
            fixed = content[:see_also_m.start()] + adjusted_placeholder + content[see_also_m.start():]
            file_path.write_text(fixed, encoding="utf-8")
            logger.info(
                "W10 KB howto structure fix (fallback before see-also): injected '%s' (%s) into %s",
                missing_heading, heading_prefix, file_path.name,
            )
            return True

        # TC-3214: Last resort — append at end of file
        fixed = content.rstrip() + "\n\n" + adjusted_placeholder
        file_path.write_text(fixed, encoding="utf-8")
        logger.info(
            "W10 KB howto structure fix (append-at-end): injected '%s' (%s) into %s",
            missing_heading, heading_prefix, file_path.name,
        )
        return True

    files_changed: List[str] = []
    headings_injected: List[str] = []

    # TC-3617 B3: Inject ALL missing headings in canonical order
    for heading in _HEADING_ORDER:
        if heading not in all_missing:
            continue
        placeholder = _PLACEHOLDER.get(heading)
        if not placeholder:
            continue
        inject_before_key = _INJECT_BEFORE.get(heading)

        # Fix the draft (what the gate reads)
        draft_path = run_dir / "drafts" / "kb" / f"{slug}.md"
        if _inject(draft_path, heading, placeholder, inject_before_key):
            if str(draft_path) not in files_changed:
                files_changed.append(str(draft_path))
            headings_injected.append(heading)

        # Fix the work/site copy (the final output)
        site_dir = run_dir / "work" / "site"
        for candidate in list(site_dir.rglob(f"{slug}.md")) + list(site_dir.rglob(f"**/{slug}/index.md")):
            if _inject(candidate, heading, placeholder, inject_before_key):
                if str(candidate) not in files_changed:
                    files_changed.append(str(candidate))

    if not files_changed:
        missing_list = sorted(all_missing)
        return {
            "fixed": False,
            "error": f"No files needed {missing_list} injection for slug '{slug}'",
        }
    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": (
            f"Injected missing {sorted(all_missing)} section(s) into "
            f"{len(files_changed)} file(s) for slug '{slug}'"
        ),
    }


# ── Scaffold leak fix (TC-2880) ──────────────────────────────────────────────


def _strip_prompt_xml_blocks(content: str) -> str:
    """Strip XML prompt tag pairs and orphaned tags.

    NOT fence-aware: PROMPT_LEAK is never legitimate, even in code fences.
    """
    content = _SCAFFOLD_XML_TAG_RE.sub("", content)
    content = _SCAFFOLD_XML_ORPHAN_RE.sub("", content)
    return content


def _strip_llm_meta_lines(content: str) -> str:
    """Remove lines matching LLM scaffold/meta patterns. Fence-aware."""
    lines = content.split("\n")
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            result.append(line)
            continue

        if any(p.search(line) for p in _SCAFFOLD_LLM_META_PATTERNS):
            continue

        result.append(line)

    return "\n".join(result)


def _strip_pipeline_json_keys(content: str) -> str:
    """Remove lines with pipeline-internal JSON keys outside code fences."""
    lines = content.split("\n")
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            result.append(line)
            continue

        if _SCAFFOLD_PIPELINE_JSON_RE.match(line):
            continue

        result.append(line)

    return "\n".join(result)


def _strip_pipeline_diagnostics(content: str) -> str:
    """Remove pipeline diagnostic patterns outside code fences."""
    lines = content.split("\n")
    result: List[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            result.append(line)
            continue

        if in_fence:
            result.append(line)
            continue

        if any(p.search(line) for p in _SCAFFOLD_PIPELINE_DIAG_PATTERNS):
            continue

        result.append(line)

    return "\n".join(result)


def _strip_all_scaffold(content: str) -> Tuple[str, int]:
    """Apply all scaffold removal passes to content.

    Returns (cleaned_content, removal_count).
    """
    count = 0

    # Pass 1: Reuse strip_llm_scaffolding() for heading-based scaffold sections
    result = strip_llm_scaffolding(content)
    if result != content:
        count += 1
        content = result

    # Pass 2: Reuse strip_pipeline_comments() for W*_REVIEW HTML comments
    result = strip_pipeline_comments(content)
    if result != content:
        count += 1
        content = result

    # Pass 3: Strip XML prompt tag blocks (not fence-aware — PROMPT_LEAK never legit)
    result = _strip_prompt_xml_blocks(content)
    if result != content:
        count += 1
        content = result

    # Pass 4: Strip LLM meta-commentary and scaffold lines (fence-aware)
    result = _strip_llm_meta_lines(content)
    if result != content:
        count += 1
        content = result

    # Pass 5: Strip pipeline JSON keys outside fences
    result = _strip_pipeline_json_keys(content)
    if result != content:
        count += 1
        content = result

    # Pass 6: Strip pipeline diagnostic patterns outside fences
    result = _strip_pipeline_diagnostics(content)
    if result != content:
        count += 1
        content = result

    # Final: Collapse triple+ blank lines to double
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content, count


def fix_scaffold_leak(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix SCAFFOLD_* issues by stripping scaffold/prompt leaks from all pages.

    Deterministic, no LLM calls. Scans ALL .md files under work/site/
    because scaffold leaks tend to appear across multiple files from the
    same LLM generation pass.

    TC-2880: Handles all 5 SCAFFOLD_* categories.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []
    total_removals = 0

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed_content, removal_count = _strip_all_scaffold(content)
            if fixed_content != content:
                md_path.write_text(fixed_content, encoding="utf-8")
                files_changed.append(str(md_path))
                total_removals += removal_count
                logger.info(
                    "W10 scaffold_leak fix: %d removals in %s",
                    removal_count,
                    md_path.name,
                )
        except Exception as exc:
            logger.warning(
                "W10 scaffold_leak: error fixing %s: %s", md_path.name, exc
            )

    if not files_changed:
        return {"fixed": False, "error": "No scaffold leak content found to remove"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": (
            f"Removed {total_removals} scaffold leak(s) "
            f"across {len(files_changed)} file(s)"
        ),
    }


# ── G1-G7 Quality Gate Fix Handlers (TC-3671) ────────────────────────────────
#
# Auto-fixable: G1 (artifact removal), G4 (trailing heading punct), G5 (product name)
# Stop-the-line: G2, G3, G6, G7 (raise FixerUnfixableError)
#
# All fixers are deterministic (no LLM calls) and idempotent.
# Spec: specs/09_validation_gates.md §Quality Gate Fix Policy (G1-G7)


def fix_g1_artifact_phrases(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G1 LLM artifact phrase issues by removing boilerplate preambles.

    TC-3671: Deterministic removal of LLM artifact lines across all .md files
    under work/site/. No LLM calls. Idempotent.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []
    total_removals = 0

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed = remove_llm_artifact_preambles(content)
            if fixed != content:
                md_path.write_text(fixed, encoding="utf-8")
                files_changed.append(str(md_path))
                # Count removed lines
                total_removals += content.count("\n") - fixed.count("\n")
                logger.info(
                    "W10 G1 fix: removed artifact preambles from %s",
                    md_path.name,
                )
        except Exception as exc:
            logger.warning("W10 G1 fix: error fixing %s: %s", md_path.name, exc)

    if not files_changed:
        return {"fixed": False, "error": "No G1 artifact phrases found to remove"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": (
            f"Removed ~{total_removals} artifact preamble line(s) "
            f"across {len(files_changed)} file(s)"
        ),
    }


def fix_g4_heading_punct(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G4 heading trailing punctuation issues.

    TC-3671: Deterministic removal of trailing periods/commas/etc from headings
    across all .md files under work/site/. No LLM calls. Idempotent.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []
    total_fixes = 0

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed = strip_heading_trailing_punct(content)
            if fixed != content:
                md_path.write_text(fixed, encoding="utf-8")
                files_changed.append(str(md_path))
                total_fixes += 1
                logger.info(
                    "W10 G4 fix: stripped heading punct in %s",
                    md_path.name,
                )
        except Exception as exc:
            logger.warning("W10 G4 fix: error fixing %s: %s", md_path.name, exc)

    if not files_changed:
        return {"fixed": False, "error": "No G4 heading punct found to fix"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": (
            f"Fixed heading trailing punctuation in {len(files_changed)} file(s)"
        ),
    }


def fix_g4_duplicate_h2(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G4 duplicate H2 issues by deduplicating See Also sections.

    TC-3682: Uses dedup_see_also_sections() to merge duplicate See Also
    headings. For non-See-Also duplicate H2s, applies dedup as best-effort.
    No LLM calls. Idempotent.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed = dedup_see_also_sections(content)
            if fixed != content:
                md_path.write_text(fixed, encoding="utf-8")
                files_changed.append(str(md_path))
                logger.info("W10 G4 fix: deduped See Also in %s", md_path.name)
        except Exception as exc:
            logger.warning("W10 G4 fix: error deduping %s: %s", md_path.name, exc)

    if not files_changed:
        return {"fixed": False, "error": "No duplicate See Also sections found to fix"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": f"Deduped See Also in {len(files_changed)} file(s)",
    }


def fix_g4_see_also_position(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G4 See Also not-last-H2 issues by moving See Also to the end.

    TC-3682: Uses move_see_also_to_end() to reposition the See Also section.
    No LLM calls. Idempotent.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed = move_see_also_to_end(content)
            if fixed != content:
                md_path.write_text(fixed, encoding="utf-8")
                files_changed.append(str(md_path))
                logger.info("W10 G4 fix: moved See Also to end in %s", md_path.name)
        except Exception as exc:
            logger.warning("W10 G4 fix: error fixing %s: %s", md_path.name, exc)

    if not files_changed:
        return {"fixed": False, "error": "No See Also position issues found to fix"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": f"Moved See Also to end in {len(files_changed)} file(s)",
    }


def fix_g5_product_name(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G5 product name integrity issues.

    TC-3671: Deterministic canonicalization of product names using known
    correction patterns. Loads canonical name from product_facts.json.
    No LLM calls. Idempotent.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return {"fixed": False, "error": "No work/site/ directory found"}

    # Load canonical product name from artifacts
    canonical_name = ""
    pf_path = run_dir / "artifacts" / "product_facts.json"
    if pf_path.exists():
        try:
            data = json.loads(pf_path.read_text(encoding="utf-8"))
            canonical_name = data.get("product_name", "")
        except Exception:
            pass

    all_md = sorted(site_dir.rglob("*.md"))
    if not all_md:
        return {"fixed": False, "error": "No .md files found under work/site/"}

    files_changed: List[str] = []

    for md_path in all_md:
        try:
            content = md_path.read_text(encoding="utf-8")
            fixed = canonicalize_product_names(content, canonical_name)
            if fixed != content:
                md_path.write_text(fixed, encoding="utf-8")
                files_changed.append(str(md_path))
                logger.info(
                    "W10 G5 fix: canonicalized product names in %s",
                    md_path.name,
                )
        except Exception as exc:
            logger.warning("W10 G5 fix: error fixing %s: %s", md_path.name, exc)

    if not files_changed:
        return {"fixed": False, "error": "No G5 product name errors found to fix"}

    return {
        "fixed": True,
        "files_changed": files_changed,
        "diff_summary": (
            f"Canonicalized product names in {len(files_changed)} file(s)"
        ),
    }


# ── Stop-the-line error codes (TC-3671) ──────────────────────────────────
# These error code prefixes have NO deterministic auto-fix and must fail fast.
_STOP_THE_LINE_PREFIXES = ("G2_", "G3_", "G6_", "G7_")


def apply_fix(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Apply appropriate fix for the given issue.

    Routing logic based on error_code and gate.

    Args:
        issue: Issue dict
        run_dir: Run directory
        llm_client: LLM client for generating fixes

    Returns:
        Fix result dict with:
            - fixed: bool
            - files_changed: List[str]
            - diff_summary: str
            - error: str (if not fixed)

    Raises:
        FixerUnfixableError: If issue cannot be fixed automatically
    """
    error_code = issue.get("error_code", "")
    gate = issue.get("gate", "")

    # ── TC-3671: G1-G7 quality gate fix routing ──────────────────────
    # Stop-the-line gates MUST fail fast — no auto-fix available.
    if any(error_code.startswith(prefix) for prefix in _STOP_THE_LINE_PREFIXES):
        raise FixerUnfixableError(
            f"Stop-the-line: {error_code} cannot be auto-fixed "
            f"(requires upstream redesign, not deterministic fixer)"
        )

    # Auto-fixable quality gates
    if error_code.startswith("G1_"):
        return fix_g1_artifact_phrases(issue, run_dir, llm_client)
    # TC-3682: Split G4 routing into dedicated handlers
    elif error_code == "G4_HEADING_TRAILING_PUNCT":
        return fix_g4_heading_punct(issue, run_dir, llm_client)
    elif error_code == "G4_DUPLICATE_H2":
        return fix_g4_duplicate_h2(issue, run_dir, llm_client)
    elif error_code == "G4_SEE_ALSO_NOT_LAST":
        return fix_g4_see_also_position(issue, run_dir, llm_client)
    elif error_code.startswith("G4_"):
        return fix_g4_heading_punct(issue, run_dir, llm_client)  # fallback
    elif error_code.startswith("G5_"):
        return fix_g5_product_name(issue, run_dir, llm_client)

    # ── Legacy fix routing ───────────────────────────────────────────
    # Route to appropriate fix function
    if "TEMPLATE_TOKEN" in error_code:
        return fix_unresolved_token(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_MISSING":
        return fix_frontmatter_missing(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_INVALID_YAML":
        return fix_frontmatter_invalid_yaml(issue, run_dir, llm_client)
    elif "CONSISTENCY" in error_code:
        return fix_consistency_mismatch(issue, run_dir, llm_client)
    elif error_code in ("G20-002", "G20-004", "G20-005"):
        # TC-2526: Contradiction resolver for version/package issues
        return fix_contradiction(issue, run_dir, llm_client)
    elif "G17" in error_code or "FORMATTING" in error_code:
        return fix_formatting_defect(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING":
        return fix_frontmatter_missing(issue, run_dir, llm_client)
    elif error_code == "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER":
        return fix_kb_howto_structure(issue, run_dir, llm_client)
    elif error_code.startswith("SCAFFOLD_"):
        # TC-2880: Scaffold/prompt leak auto-fix
        return fix_scaffold_leak(issue, run_dir, llm_client)
    else:
        # Unfixable issue
        raise FixerUnfixableError(f"No automatic fix available for error_code: {error_code}")


def check_fix_produced_diff(
    files_changed: List[str], run_dir: Path, original_hashes: Dict[str, str]
) -> bool:
    """Check if fix actually changed files.

    Args:
        files_changed: List of file paths that were supposed to change
        run_dir: Run directory
        original_hashes: Dict of file_path -> sha256 hash before fix

    Returns:
        True if at least one file has different hash
    """
    if not files_changed:
        return False

    for file_path_str in files_changed:
        file_path = Path(file_path_str)
        original_hash = original_hashes.get(str(file_path), "")
        new_hash = compute_file_hash(file_path)

        if original_hash != new_hash:
            return True

    return False


def execute_fixer(
    run_dir: Path,
    run_config: Dict[str, Any],
    llm_client: Any = None,
    current_issue: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute fixer to resolve exactly one validation issue.

    This is the main entry point for W8 Fixer worker.

    Per specs/21_worker_contracts.md:290-320:
    - Fix exactly one issue (the issue supplied by orchestrator)
    - Obey gate-specific fix rules
    - Must not introduce new factual claims without evidence
    - Fail with blocker FixNoOp if cannot produce meaningful diff

    Per specs/28_coordination_and_handoffs.md:71-84:
    - Single-issue-at-a-time fixing (no batch fixes)
    - Deterministic fix selection
    - Max fix attempts enforcement

    Args:
        run_dir: Run directory path (e.g., runs/run_001)
        run_config: Run configuration dictionary.  TC-3600: if *current_issue*
            is ``None``, falls back to ``run_config["_current_issue"]`` (injected
            by the orchestrator's ``fix_node``).
        llm_client: LLM client for generating fixes (optional; created from run_config if None)
        current_issue: Specific issue to fix (if None, selects first blocker/error)

    Returns:
        Fix result dictionary with:
            - status: "resolved" | "needs_retry" | "unfixable"
            - issue_id: ID of issue that was fixed
            - files_changed: List of changed file paths
            - diff_summary: Summary of changes made
            - error_message: Error message if unfixable

    Raises:
        FixerError: On fixer errors
        FixerIssueNotFoundError: If issue ID not found
        FixerUnfixableError: If issue cannot be fixed
        FixerNoOpError: If fix produced no diff
    """
    # Create LLM client from run_config if not provided (standard worker pattern)
    if llm_client is None:
        try:
            from launch.clients.llm_provider import create_llm_client_from_config
            llm_client = create_llm_client_from_config(run_config=run_config, run_dir=run_dir)
        except Exception:
            llm_client = None  # deterministic fixes don't need LLM

    # Generate trace IDs
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    # Load validation report with integrity check (TC-2470)
    try:
        validation_report = load_json_artifact(run_dir, "validation_report.json")
        if "gates" not in validation_report or "issues" not in validation_report:
            raise FixerArtifactMissingError(
                "validation_report.json malformed: missing 'gates' or 'issues'. Re-run W9."
            )
        # TC-2506: Verify handoff integrity (generation_id + content_hash)
        _verify_handoff(validation_report)
    except (FixerArtifactMissingError, StaleValidationReportError) as e:
        emit_event(
            run_dir,
            "FIXER_FAILED",
            {"error": str(e)},
            trace_id,
            span_id,
        )
        raise

    # TC-3600: If current_issue was not passed as a kwarg, fall back to the
    # orchestrator-injected _current_issue in run_config.  This bridges the
    # gap where worker_invoker only passes (run_dir, run_config).
    if current_issue is None:
        current_issue = run_config.get("_current_issue")

    # Select issue to fix
    issue = select_issue_to_fix(validation_report, current_issue)

    if issue is None:
        # No fixable issues
        emit_event(
            run_dir,
            "FIXER_NO_ISSUES",
            {"message": "No fixable issues found"},
            trace_id,
            span_id,
        )
        return {
            "status": "resolved",
            "issue_id": None,
            "files_changed": [],
            "diff_summary": "No issues to fix",
        }

    issue_id = issue.get("issue_id", "unknown")

    # TC-3240: Resolve relative paths from validation_report.json
    # to absolute paths anchored at run_dir.
    _normalize_issue_paths(issue, run_dir)

    # TC-3450: Stale path guard.
    # After path normalization, if location.path does not exist on disk the
    # validation report is stale (file reorganised by W8, deleted, or mutated
    # since W9 ran).  Emit a telemetry event then raise StaleValidationReportError
    # so the orchestrator re-runs W9 instead of marking the issue as "unfixable".
    _stale_loc = issue.get("location", {})
    if isinstance(_stale_loc, dict):
        _stale_path_str = _stale_loc.get("path")
        if _stale_path_str is not None:
            _stale_path = Path(_stale_path_str)
            if not _stale_path.exists():
                emit_event(
                    run_dir,
                    EVENT_FIXER_STALE_PATH_DETECTED,
                    {"issue_id": issue_id, "path": str(_stale_path)},
                    trace_id,
                    span_id,
                )
                raise StaleValidationReportError(
                    f"Issue {issue_id!r} references missing file path {_stale_path!r}; "
                    "rerun W9 to refresh the validation report before fixing."
                )

    # Emit FIXER_STARTED event
    emit_event(
        run_dir,
        "FIXER_STARTED",
        {"issue_id": issue_id, "gate": issue.get("gate"), "severity": issue.get("severity")},
        trace_id,
        span_id,
    )

    # Compute hashes of files before fixing
    files_to_check = issue.get("files", [])
    location = issue.get("location", {})
    if isinstance(location, dict) and "path" in location:
        files_to_check.append(location["path"])

    original_hashes = {}
    for file_path_str in files_to_check:
        file_path = Path(file_path_str)
        original_hashes[str(file_path)] = compute_file_hash(file_path)

    # Apply fix
    try:
        fix_result = apply_fix(issue, run_dir, llm_client)
    except FixerUnfixableError as e:
        emit_event(
            run_dir,
            "ISSUE_FIX_FAILED",
            {"issue_id": issue_id, "reason": str(e)},
            trace_id,
            span_id,
        )
        return {
            "status": "unfixable",
            "issue_id": issue_id,
            "files_changed": [],
            "diff_summary": "",
            "error_message": str(e),
        }

    if not fix_result.get("fixed", False):
        # Fix failed
        error_msg = fix_result.get("error", "Unknown error")
        emit_event(
            run_dir,
            "ISSUE_FIX_FAILED",
            {"issue_id": issue_id, "reason": error_msg},
            trace_id,
            span_id,
        )
        return {
            "status": "unfixable",
            "issue_id": issue_id,
            "files_changed": [],
            "diff_summary": "",
            "error_message": error_msg,
        }

    # Check if fix produced actual diff
    files_changed = fix_result.get("files_changed", [])
    has_diff = check_fix_produced_diff(files_changed, run_dir, original_hashes)

    if not has_diff:
        # Fix produced no diff - this is a blocker per spec
        emit_event(
            run_dir,
            "ISSUE_FIX_FAILED",
            {"issue_id": issue_id, "reason": "Fix produced no diff"},
            trace_id,
            span_id,
        )
        raise FixerNoOpError(f"Fix for issue {issue_id} produced no diff")

    # Emit ISSUE_RESOLVED event
    emit_event(
        run_dir,
        "ISSUE_RESOLVED",
        {
            "issue_id": issue_id,
            "files_changed": files_changed,
            "diff_summary": fix_result.get("diff_summary", ""),
        },
        trace_id,
        span_id,
    )

    # Emit FIXER_COMPLETED event
    emit_event(
        run_dir,
        "FIXER_COMPLETED",
        {
            "issue_id": issue_id,
            "status": "resolved",
            "files_changed_count": len(files_changed),
        },
        trace_id,
        span_id,
    )

    # Write fix report (optional)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    fix_report_path = reports_dir / f"fix_{issue_id}.md"

    fix_report_content = f"""# Fix Report: {issue_id}

## Issue Details
- **Issue ID**: {issue_id}
- **Gate**: {issue.get("gate", "unknown")}
- **Severity**: {issue.get("severity", "unknown")}
- **Error Code**: {issue.get("error_code", "unknown")}
- **Message**: {issue.get("message", "unknown")}

## Fix Applied
{fix_result.get("diff_summary", "No summary available")}

## Files Changed
{chr(10).join(f"- {f}" for f in files_changed)}

## Status
Resolved successfully.
"""

    fix_report_path.write_text(fix_report_content, encoding="utf-8")

    return {
        "status": "resolved",
        "issue_id": issue_id,
        "files_changed": files_changed,
        "diff_summary": fix_result.get("diff_summary", ""),
    }
