"""Phase artifact verifier -- existence and JSON Schema checks per pipeline phase.

Provides ``verify_phase_artifacts()`` which confirms that a phase completed
successfully by checking artifact existence and, where applicable, validating
JSON artifacts against their schemas.

Called between phase group executions (TC-2500) and available standalone
via ``--verify-only`` mode (TC-2502).

Spec references:
- specs/40_storage_model.md  (Artifact registry)
- specs/43_resumable_pipeline.md  (RESUME_NODE_MAP required_paths)
- specs/21_worker_contracts.md  (Worker output contracts)
- specs/schemas/  (JSON Schema files)

TC-2501
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ArtifactCheck:
    """Result of checking a single artifact file."""

    path: str
    """Relative path from run_dir (forward slashes)."""

    exists: bool
    """True if the file exists on disk."""

    valid_json: Optional[bool] = None
    """True if the file is parseable JSON.  None for non-JSON artifacts."""

    schema_valid: Optional[bool] = None
    """True if JSON validates against its schema.  None if no schema or not checked."""

    error: Optional[str] = None
    """Human-readable error description (None when everything is OK)."""

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable dict (for phase_report.json, TC-2504)."""
        return asdict(self)


@dataclass
class PhaseVerificationResult:
    """Aggregate result of verifying all artifacts for one phase."""

    phase_id: str
    """Phase identifier (e.g. ``"P1"``)."""

    ok: bool
    """True when every check passed."""

    checks: List[ArtifactCheck] = field(default_factory=list)
    """Per-artifact check results."""

    missing: List[str] = field(default_factory=list)
    """Paths of artifacts that were expected but not found."""

    schema_errors: List[str] = field(default_factory=list)
    """Paths of artifacts that failed JSON parse or schema validation."""

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable dict (for phase_report.json, TC-2504)."""
        return {
            "phase_id": self.phase_id,
            "ok": self.ok,
            "checks": [c.to_dict() for c in self.checks],
            "missing": self.missing,
            "schema_errors": self.schema_errors,
        }


# ---------------------------------------------------------------------------
# Phase artifact checklist
# ---------------------------------------------------------------------------
# Each entry is (artifact_relative_path, schema_relative_path_or_None).
# Schema paths are relative to the repo root.
# Artifacts are relative to run_dir.

PHASE_ARTIFACT_CHECKLIST: Dict[str, List[Tuple[str, Optional[str]]]] = {
    "P1": [
        ("artifacts/repo_inventory.json", "specs/schemas/repo_inventory.schema.json"),
        ("artifacts/product_facts.json", "specs/schemas/product_facts.schema.json"),
        ("artifacts/snippet_catalog.json", "specs/schemas/snippet_catalog.schema.json"),
    ],
    "P2": [
        ("artifacts/page_plan.json", "specs/schemas/page_plan.schema.json"),
        ("artifacts/shared_facts.json", "specs/schemas/shared_facts.schema.json"),
        # content_policy.json has no formal schema yet (out of scope per TC-2501)
        ("artifacts/content_policy.json", None),
    ],
    "P3": [
        ("artifacts/draft_manifest.json", None),
        # NOTE: Individual markdown files referenced by draft_manifest are
        # verified dynamically inside _check_draft_manifest_pages().
    ],
    "P4": [
        ("artifacts/patch_bundle.json", "specs/schemas/patch_bundle.schema.json"),
    ],
    "P5": [
        ("artifacts/validation_report.json", "specs/schemas/validation_report.schema.json"),
    ],
    "P6": [
        # Packaging/PR artifacts -- existence-only; no schema.
        ("artifacts/patch_bundle.json", None),
    ],
}

PHASE_IDS: Sequence[str] = ("P1", "P2", "P3", "P4", "P5", "P6")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_repo_root() -> Path:
    """Best-effort repo-root discovery (walk up from this file)."""
    candidate = Path(__file__).resolve()
    for parent in candidate.parents:
        if (parent / "specs").is_dir() and (parent / "src").is_dir():
            return parent
    # Fallback: cwd
    return Path.cwd()


def _check_artifact(
    run_dir: Path,
    artifact_rel: str,
    schema_rel: Optional[str],
    repo_root: Optional[Path] = None,
) -> ArtifactCheck:
    """Check a single artifact for existence, JSON validity, and schema conformance.

    Args:
        run_dir: Absolute path to the run directory.
        artifact_rel: Artifact path relative to *run_dir* (forward slashes).
        schema_rel: Schema path relative to *repo_root*, or None to skip.
        repo_root: Repository root for locating schema files.

    Returns:
        Populated ``ArtifactCheck``.
    """
    artifact_path = run_dir / artifact_rel
    is_json = artifact_rel.endswith(".json")

    # 1. Existence
    if not artifact_path.exists():
        return ArtifactCheck(
            path=artifact_rel,
            exists=False,
            valid_json=None if not is_json else False,
            schema_valid=None,
            error=f"Artifact not found: {artifact_rel}",
        )

    # Non-JSON files: existence is sufficient
    if not is_json:
        return ArtifactCheck(path=artifact_rel, exists=True)

    # 2. JSON parse
    try:
        raw = artifact_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ArtifactCheck(
            path=artifact_rel,
            exists=True,
            valid_json=False,
            schema_valid=None,
            error=f"Malformed JSON in {artifact_rel}: {exc}",
        )

    valid_json = True

    # 3. Schema validation (optional)
    if schema_rel is None:
        return ArtifactCheck(
            path=artifact_rel,
            exists=True,
            valid_json=valid_json,
            schema_valid=None,
        )

    if repo_root is None:
        repo_root = _resolve_repo_root()

    schema_path = repo_root / schema_rel
    if not schema_path.exists():
        logger.warning(
            "Schema file not found -- skipping validation: %s", schema_path
        )
        return ArtifactCheck(
            path=artifact_rel,
            exists=True,
            valid_json=valid_json,
            schema_valid=None,
            error=f"Schema file missing: {schema_rel}",
        )

    try:
        from launch.io.schema_validation import load_schema, validate

        schema = load_schema(schema_path)
        validate(data, schema, context=artifact_rel)
    except Exception as exc:
        return ArtifactCheck(
            path=artifact_rel,
            exists=True,
            valid_json=valid_json,
            schema_valid=False,
            error=f"Schema validation failed for {artifact_rel}: {exc}",
        )

    return ArtifactCheck(
        path=artifact_rel,
        exists=True,
        valid_json=valid_json,
        schema_valid=True,
    )


def _check_validation_report_keys(
    run_dir: Path,
) -> Optional[str]:
    """P5 extra check: ``validation_report.json`` must contain ``gates`` and ``issues`` keys.

    Returns:
        Error string if check fails, else None.
    """
    report_path = run_dir / "artifacts" / "validation_report.json"
    if not report_path.exists():
        return None  # existence already caught by _check_artifact

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None  # parse error already caught

    missing_keys = [k for k in ("gates", "issues") if k not in data]
    if missing_keys:
        return (
            f"validation_report.json missing required keys: {', '.join(missing_keys)}"
        )
    return None


def _check_draft_manifest_pages(
    run_dir: Path,
) -> List[ArtifactCheck]:
    """P3 extra check: verify markdown files referenced in ``draft_manifest.json`` exist.

    Returns:
        List of ``ArtifactCheck`` entries for each referenced page.
    """
    manifest_path = run_dir / "artifacts" / "draft_manifest.json"
    if not manifest_path.exists():
        return []

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    checks: List[ArtifactCheck] = []

    # draft_manifest.json typically has a "pages" list with "output_path" entries
    pages = data.get("pages", [])
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict):
                output = page.get("output_path") or page.get("path")
                if output:
                    page_path = run_dir / output
                    checks.append(
                        ArtifactCheck(
                            path=output,
                            exists=page_path.exists(),
                            valid_json=None,
                            schema_valid=None,
                            error=None if page_path.exists() else f"Draft page not found: {output}",
                        )
                    )

    return checks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_phase_artifacts(
    run_dir: Path,
    phase_id: str,
    *,
    repo_root: Optional[Path] = None,
) -> PhaseVerificationResult:
    """Verify all expected artifacts for a given pipeline phase.

    Args:
        run_dir: Absolute path to the run directory.
        phase_id: Phase to verify (``"P1"`` through ``"P6"``).
        repo_root: Repository root for locating schema files.
            Defaults to auto-detection via ``_resolve_repo_root()``.

    Returns:
        ``PhaseVerificationResult`` summarising the verification outcome.

    Raises:
        ValueError: If *phase_id* is not in ``PHASE_ARTIFACT_CHECKLIST``.
    """
    if phase_id not in PHASE_ARTIFACT_CHECKLIST:
        raise ValueError(
            f"Unknown phase_id '{phase_id}'. "
            f"Valid phases: {', '.join(PHASE_IDS)}"
        )

    if repo_root is None:
        repo_root = _resolve_repo_root()

    entries = PHASE_ARTIFACT_CHECKLIST[phase_id]
    checks: List[ArtifactCheck] = []
    missing: List[str] = []
    schema_errors: List[str] = []

    for artifact_rel, schema_rel in entries:
        check = _check_artifact(run_dir, artifact_rel, schema_rel, repo_root)
        checks.append(check)

        if not check.exists:
            missing.append(check.path)
        if check.schema_valid is False or check.valid_json is False:
            schema_errors.append(check.path)

    # Phase-specific extra checks
    if phase_id == "P3":
        page_checks = _check_draft_manifest_pages(run_dir)
        for pc in page_checks:
            checks.append(pc)
            if not pc.exists:
                missing.append(pc.path)

    if phase_id == "P5":
        key_err = _check_validation_report_keys(run_dir)
        if key_err:
            # Attach the error to the existing validation_report check
            for c in checks:
                if c.path == "artifacts/validation_report.json" and c.error is None:
                    c.error = key_err
                    break
            schema_errors.append("artifacts/validation_report.json")

    ok = len(missing) == 0 and len(schema_errors) == 0

    result = PhaseVerificationResult(
        phase_id=phase_id,
        ok=ok,
        checks=checks,
        missing=missing,
        schema_errors=schema_errors,
    )

    if ok:
        logger.info("phase_verification_ok: %s (%d checks)", phase_id, len(checks))
    else:
        logger.warning(
            "phase_verification_failed: %s -- missing=%s, schema_errors=%s",
            phase_id,
            missing,
            schema_errors,
        )

    return result


def verify_phase_range(
    run_dir: Path,
    start_phase: str,
    end_phase: str,
    *,
    repo_root: Optional[Path] = None,
) -> List[PhaseVerificationResult]:
    """Verify all phases in [start_phase .. end_phase] inclusive.

    Args:
        run_dir: Absolute path to the run directory.
        start_phase: First phase to verify (e.g. ``"P1"``).
        end_phase: Last phase to verify (e.g. ``"P5"``).
        repo_root: Repository root for locating schema files.

    Returns:
        List of ``PhaseVerificationResult``, one per phase in range.

    Raises:
        ValueError: If start or end phase is not in ``PHASE_IDS``.
    """
    if start_phase not in PHASE_IDS:
        raise ValueError(f"Unknown start_phase '{start_phase}'. Valid: {', '.join(PHASE_IDS)}")
    if end_phase not in PHASE_IDS:
        raise ValueError(f"Unknown end_phase '{end_phase}'. Valid: {', '.join(PHASE_IDS)}")

    start_idx = PHASE_IDS.index(start_phase)
    end_idx = PHASE_IDS.index(end_phase)

    if start_idx > end_idx:
        raise ValueError(
            f"start_phase '{start_phase}' must come before end_phase '{end_phase}'"
        )

    results: List[PhaseVerificationResult] = []
    for idx in range(start_idx, end_idx + 1):
        results.append(
            verify_phase_artifacts(run_dir, PHASE_IDS[idx], repo_root=repo_root)
        )
    return results
