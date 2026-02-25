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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ...io.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)


# FQ-3: Truncated bullet endings (compiled once at module level)
_TRUNCATION_ENDINGS = re.compile(
    r"[,]\s*$|"
    r"\b(?:is|of|for|with|the|and|but|or|in|to|a|an)\s*$"
)


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
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body}"


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
    """Fix missing frontmatter issue.

    Strategy:
    - Read file without frontmatter
    - Generate minimal frontmatter based on page plan
    - Add frontmatter to file

    Args:
        issue: Issue dict
        run_dir: Run directory
        llm_client: LLM client (not used for this heuristic fix)

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

    # Generate minimal frontmatter
    minimal_frontmatter = {
        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
        "type": "docs",
    }

    # Add frontmatter
    fixed_content = write_frontmatter(minimal_frontmatter, content)
    file_path.write_text(fixed_content, encoding="utf-8")

    return {
        "fixed": True,
        "files_changed": [str(file_path)],
        "diff_summary": f"Added minimal frontmatter to {file_path.name}",
    }


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

    # Extract frontmatter section
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        # No frontmatter structure - add minimal
        minimal_frontmatter = {
            "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
            "type": "docs",
        }
        fixed_content = write_frontmatter(minimal_frontmatter, content)
        file_path.write_text(fixed_content, encoding="utf-8")

        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Replaced invalid frontmatter with minimal valid frontmatter in {file_path.name}",
        }

    # Try to fix common YAML issues (this is heuristic)
    # For production, would use LLM to fix
    # For now, just replace with minimal frontmatter
    yaml_content = match.group(1)
    body = match.group(2)

    # Replace with minimal frontmatter
    minimal_frontmatter = {
        "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
        "type": "docs",
    }

    fixed_content = write_frontmatter(minimal_frontmatter, body)
    file_path.write_text(fixed_content, encoding="utf-8")

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


def fix_formatting_defect(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix formatting defects reported by Gate 17.

    Handles:
    - G17-FQ-4: Insert blank line between adjacent headings
    - G17-FQ-7: Normalize code fences (re-run fence sanitizers)
    - G17-FQ-1: Fix bare code blocks (add language tag)
    - G17-FQ-3: Fix indented code not in fence

    Args:
        issue: Issue dict with error_code and location
        run_dir: Run directory
        llm_client: LLM client (not used for deterministic fixes)

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

    content = file_path.read_text(encoding="utf-8")
    original_content = content

    if "FQ-4" in error_code or "FQ4" in error_code:
        # Fix: Insert blank line between adjacent headings
        content = re.sub(
            r"(^#{1,6}\s+[^\n]+\n)(#{1,6}\s+)",
            r"\1\n\2",
            content,
            flags=re.MULTILINE,
        )

    if "FQ-7" in error_code or "FQ7" in error_code:
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

    if "FQ-1" in error_code or "FQ1" in error_code:
        # Fix: Add language tag to bare code blocks
        content = re.sub(
            r"^```\s*$",
            "```text",
            content,
            flags=re.MULTILINE,
        )

    if "FQ-3" in error_code or "FQ3" in error_code:
        # Fix: Trim truncated bullets that end mid-sentence
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if (stripped.startswith("- ") or stripped.startswith("* ")):
                if _TRUNCATION_ENDINGS.search(stripped):
                    words = stripped.rsplit(maxsplit=1)
                    if len(words) > 1:
                        lines[i] = words[0].rstrip(",").rstrip() + "."
        content = "\n".join(lines)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return {
            "fixed": True,
            "files_changed": [str(file_path)],
            "diff_summary": f"Fixed formatting defect {error_code} in {file_path.name}",
        }

    return {"fixed": False, "error": f"No formatting changes needed for {error_code}"}


# ---------------------------------------------------------------------------
# Contradiction resolver (TC-2526)
# ---------------------------------------------------------------------------

# Python version pattern for contradiction fixing
_VERSION_FIX_RE = re.compile(
    r"([Pp]ython\s*(?:>=?\s*)?)(\d+)\.(\d+)"
)

# Package name in pip install commands
_PKG_FIX_RE = re.compile(
    r"(pip\s+install\s+)([a-zA-Z0-9._-]+)"
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
        def _fix_pkg(m: re.Match) -> str:
            prefix = m.group(1)
            found_pkg = m.group(2)
            # Strip version specifiers to compare base name
            base_found = re.split(r"[>=<!\[]", found_pkg)[0]
            if base_found and base_found != canonical_pkg:
                corrections.append(
                    f"package: {base_found} -> {canonical_pkg}"
                )
                # Preserve any version specifier that was attached
                suffix = found_pkg[len(base_found):]
                return f"{prefix}{canonical_pkg}{suffix}"
            return m.group(0)

        result = _PKG_FIX_RE.sub(_fix_pkg, result)

    return result, corrections


def fix_contradiction(
    issue: Dict[str, Any], run_dir: Path, llm_client: Any
) -> Dict[str, Any]:
    """Fix G20-004/G20-005 contradiction issues using shared_facts as source of truth.

    Loads shared_facts.json and applies ``_resolve_contradictions()`` to the
    affected page file.

    Args:
        issue: Issue dict (must have location.path).
        run_dir: Run directory.
        llm_client: LLM client (not used -- deterministic fix).

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

    # Load shared_facts (graceful skip when absent)
    sf_path = run_dir / "artifacts" / "shared_facts.json"
    if not sf_path.exists():
        logger.info("W10 contradiction resolver: shared_facts.json not found, skipping")
        return {"fixed": False, "error": "shared_facts.json not available"}

    try:
        shared_facts = json.loads(sf_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"fixed": False, "error": f"Failed to load shared_facts: {e}"}

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

    # Route to appropriate fix function
    if "TEMPLATE_TOKEN" in error_code:
        return fix_unresolved_token(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_MISSING":
        return fix_frontmatter_missing(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_INVALID_YAML":
        return fix_frontmatter_invalid_yaml(issue, run_dir, llm_client)
    elif "CONSISTENCY" in error_code:
        return fix_consistency_mismatch(issue, run_dir, llm_client)
    elif error_code in ("G20-004", "G20-005"):
        # TC-2526: Contradiction resolver for version/package issues
        return fix_contradiction(issue, run_dir, llm_client)
    elif "G17" in error_code or "FORMATTING" in error_code:
        return fix_formatting_defect(issue, run_dir, llm_client)
    elif error_code == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING":
        return fix_frontmatter_missing(issue, run_dir, llm_client)
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
        run_config: Run configuration dictionary
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
