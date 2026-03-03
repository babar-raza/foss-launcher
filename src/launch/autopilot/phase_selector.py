"""Deterministic PhaseSelector — computes earliest safe pipeline resume point.

TC-3020: Baseline decision engine for autopilot phase selection.
Walks pipeline checkpoints in order; first failure determines start_worker.

No LLM, no network. Purely local file inspection.

Spec references:
- specs/48_autopilot_phase_selection.md (Binding)
- specs/43_resumable_pipeline.md (RESUME_NODE_MAP)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PhaseDecision:
    """Deterministic decision: earliest safe worker to resume from."""

    start_worker: str
    """One of: W1, W3, W4, W5, W8, W9, W10, W11, DONE."""

    reasons: Tuple[str, ...]
    """Machine-readable reason codes (frozen tuple for determinism)."""

    details: Dict[str, str] = field(default_factory=dict)
    """Mapping of reason_code -> human-readable explanation."""


# ── Artifact → schema mapping ────────────────────────────────────────────
# Relative to run_dir for artifacts, relative to repo_root for schemas.
# None means skip schema validation (existence + JSON parse only).

_CHECKPOINT_ARTIFACTS: Dict[str, List[Tuple[str, Optional[str]]]] = {
    "W1": [
        ("artifacts/repo_inventory.json", "specs/schemas/repo_inventory.schema.json"),
    ],
    "W3": [
        ("artifacts/product_facts.json", "specs/schemas/product_facts.schema.json"),
        ("artifacts/snippet_catalog.json", "specs/schemas/snippet_catalog.schema.json"),
    ],
    "W4": [
        ("artifacts/page_plan.json", "specs/schemas/page_plan.schema.json"),
        ("artifacts/shared_facts.json", "specs/schemas/shared_facts.schema.json"),
    ],
    "W5": [
        ("artifacts/draft_manifest.json", None),
    ],
    "W8": [
        ("artifacts/patch_bundle.json", "specs/schemas/patch_bundle.schema.json"),
    ],
    "W9": [
        ("artifacts/validation_report.json", "specs/schemas/validation_report.schema.json"),
    ],
}

_CHECKPOINT_ORDER = ("W1", "W3", "W4", "W5", "W8", "W9")


def _check_json_artifact(
    run_dir: Path,
    artifact_rel: str,
    schema_rel: Optional[str],
    repo_root: Optional[Path],
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Check a single artifact for existence, JSON validity, and optional schema conformance.

    Returns:
        (ok, error_code_or_none, parsed_data_or_none)
    """
    artifact_path = run_dir / artifact_rel
    name = Path(artifact_rel).name

    # 1. Existence
    if not artifact_path.exists():
        return False, f"ARTIFACT_MISSING:{name}", None

    # 2. JSON parse
    try:
        raw = artifact_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return False, f"ARTIFACT_INVALID_JSON:{name}", None

    # 3. Schema validation (optional)
    if schema_rel and repo_root:
        schema_path = repo_root / schema_rel
        if schema_path.exists():
            try:
                from launch.io.schema_validation import load_schema, validate

                schema = load_schema(schema_path)
                validate(data, schema, context=artifact_rel)
            except Exception:
                return False, f"ARTIFACT_SCHEMA_FAIL:{name}", data

    return True, None, data


def select_phase(
    run_dir: Path,
    target_repo_sha: str,
    *,
    repo_root: Optional[Path] = None,
    goal: str = "draft",
    validation_summary: Optional[Dict[str, Any]] = None,
) -> PhaseDecision:
    """Return the earliest safe worker to start from.

    Deterministic, no LLM, no network. Purely local file inspection.

    Args:
        run_dir: Path to the run directory containing artifacts/.
        target_repo_sha: Expected repo SHA (from run_config github_ref resolution).
        repo_root: Repository root for locating schema files. None to skip schema checks.
        goal: One of "draft", "validate", "pr". Controls terminal decisions.
        validation_summary: Optional dict with "fixable_count" and "blocker_count"
            from a prior validation run.

    Returns:
        PhaseDecision with start_worker and reasons.
    """
    reasons: List[str] = []
    details: Dict[str, str] = {}

    # ── Checkpoint 1: W1 (repo clone + inventory) ────────────────────────
    # Check work/repo/ directory exists
    repo_dir = run_dir / "work" / "repo"
    if not repo_dir.is_dir():
        reasons.append("REPO_DIR_MISSING")
        details["REPO_DIR_MISSING"] = f"work/repo/ directory not found in {run_dir}"
        return PhaseDecision(start_worker="W1", reasons=tuple(reasons), details=details)

    # TC-3642: Verify actual clone (not empty skeleton from create_run_skeleton)
    if not (repo_dir / ".git").exists():
        reasons.append("REPO_NOT_CLONED")
        details["REPO_NOT_CLONED"] = "work/repo/.git not found — directory exists but is not a git clone"
        return PhaseDecision(start_worker="W1", reasons=tuple(reasons), details=details)

    # Check repo_inventory.json
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W1"]:
        ok, err, data = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W1", reasons=tuple(reasons), details=details)

        # SHA match check (repo_inventory contains repo_sha)
        if ok and data and artifact_rel == "artifacts/repo_inventory.json":
            stored_sha = data.get("repo_sha", "") or data.get("fingerprint", {}).get(
                "repo_sha", ""
            )
            if stored_sha and stored_sha != target_repo_sha:
                reasons.append("REPO_SHA_MISMATCH")
                details["REPO_SHA_MISMATCH"] = (
                    f"Stored repo_sha {stored_sha!r} != target {target_repo_sha!r}"
                )
                return PhaseDecision(
                    start_worker="W1", reasons=tuple(reasons), details=details
                )

    # ── Checkpoint 2: W3 (facts + snippets) ──────────────────────────────
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W3"]:
        ok, err, _ = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W3", reasons=tuple(reasons), details=details)

    # ── Checkpoint 3: W4 (planning) ──────────────────────────────────────
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W4"]:
        ok, err, _ = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W4", reasons=tuple(reasons), details=details)

    # ── Checkpoint 4: W5 (drafts) ────────────────────────────────────────
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W5"]:
        ok, err, _ = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W5", reasons=tuple(reasons), details=details)

    # Also check for actual draft markdown files
    drafts_dir = run_dir / "drafts"
    if not drafts_dir.is_dir() or not any(drafts_dir.rglob("*.md")):
        reasons.append("DRAFTS_EMPTY")
        details["DRAFTS_EMPTY"] = "No .md files found under drafts/"
        return PhaseDecision(start_worker="W5", reasons=tuple(reasons), details=details)

    # ── Checkpoint 5: W8 (linking + patching) ────────────────────────────
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W8"]:
        ok, err, _ = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W8", reasons=tuple(reasons), details=details)

    # ── Checkpoint 6: W9 (validation) ────────────────────────────────────
    validation_data: Optional[Dict[str, Any]] = None
    for artifact_rel, schema_rel in _CHECKPOINT_ARTIFACTS["W9"]:
        ok, err, data = _check_json_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        if not ok and err:
            reasons.append(err)
            details[err] = f"{artifact_rel} failed check"
            return PhaseDecision(start_worker="W9", reasons=tuple(reasons), details=details)
        if ok:
            validation_data = data

    # ── Post-validation decisions ────────────────────────────────────────
    # Auto-derive fixable summary from validation_report when caller omits it.
    # Caller-provided validation_summary always takes precedence (backward compat).
    if validation_summary is None and validation_data:
        issues = validation_data.get("issues", [])
        blocker_count = sum(
            1 for i in issues if isinstance(i, dict) and i.get("severity") == "blocker"
        )
        error_count = sum(
            1 for i in issues if isinstance(i, dict) and i.get("severity") == "error"
        )
        fixable_count = blocker_count + error_count
        if fixable_count > 0:
            validation_summary = {"fixable_count": fixable_count, "blocker_count": blocker_count}

    # Check if validation report has fixable issues
    if validation_summary:
        fixable = validation_summary.get("fixable_count", 0)
        blockers = validation_summary.get("blocker_count", 0)
        if fixable > 0 or blockers > 0:
            reasons.append("VALIDATION_HAS_FIXABLE")
            details["VALIDATION_HAS_FIXABLE"] = (
                f"{fixable} fixable issue(s), {blockers} blocker(s)"
            )
            return PhaseDecision(
                start_worker="W10", reasons=tuple(reasons), details=details
            )

    # Check goal for PR
    if goal == "pr":
        reasons.append("ALL_PASSED")
        details["ALL_PASSED"] = "All artifacts ready, goal=pr"
        return PhaseDecision(start_worker="W11", reasons=tuple(reasons), details=details)

    # Everything is ready
    reasons.append("DONE")
    details["DONE"] = "All pre-validation and validation artifacts present and valid"
    return PhaseDecision(start_worker="DONE", reasons=tuple(reasons), details=details)
