"""Verify worker — deterministic drift detection between repo state and knowledge baseline.

TC-5167: VerifyWorker is an optional post-Scout worker that runs in `verify` and
`maintain` pipeline modes. All detection is deterministic — no LLM calls.

Pipeline positions:
  verify mode:   Intake → Scout → Verify  [stops; emits drift_report.json]
  maintain mode: Intake → Scout → Verify → Understand → Planner → …

Verify inputs:  ScoutBundle (from Scout worker)
Verify outputs: ScoutBundle (pass-through, unchanged) + side-effect drift_report.json

The DriftReport is written to run_dir/drift_report.json and optionally to
knowledge/{family}/{platform}/drift_report.json.  The ScoutBundle is returned
unchanged so the Planner/Understand workers can continue in maintain mode.

Spec reference: plans/compressed-splashing-pearl.md  Phase 2
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.scout import ScoutBundle
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class VerifyWorker(WorkerContract):
    """Optional worker: deterministic drift detection between repo truth and knowledge baseline.

    Runs 4 passes (SHA check, claim staleness, new capabilities, code freshness)
    then writes drift_report.json and drift_baseline.yaml.
    """

    @property
    def name(self) -> str:
        return "verify"

    async def run(
        self,
        input_data: LauncherBaseModel,
        context: WorkerContext,
    ) -> ScoutBundle:
        """Execute Verify phase: run 4 drift detection passes, write report and baseline."""
        from launcher.workers.verify.drift_detector import (
            compute_drift_status,
            compute_page_drift_actions,
            pass1_sha_check,
            pass2_claim_staleness,
            pass3_new_capabilities,
            pass4_code_freshness,
            write_drift_baseline,
        )

        # ------------------------------------------------------------------ #
        # 1. Resolve input
        # ------------------------------------------------------------------ #
        if isinstance(input_data, ScoutBundle):
            scout = input_data
        else:
            scout = ScoutBundle.model_validate(input_data.model_dump())

        family = scout.family
        platform = scout.platform
        current_repo_sha = scout.repo_sha or ""

        context.log.info(
            "[Verify] Starting: family=%s platform=%s sha=%s",
            family, platform, current_repo_sha[:12] if current_repo_sha else "(none)",
        )
        context.emit_event("worker_started", {"phase": "verify"}, worker=self.name)

        # TC-5168: In create mode, drift detection is irrelevant — skip all passes.
        # Planner's _apply_maintenance_filter reads drift_report.json; in create mode
        # this file must not exist (absence = all pages get action "create" by default).
        pipeline_mode = getattr(context.config, "pipeline_mode", "create")
        if pipeline_mode == "create":
            context.log.debug("[Verify] pipeline_mode=create — skipping drift detection")
            context.emit_event(
                "worker_completed",
                {"drift_status": "skipped", "pipeline_mode": "create"},
                worker=self.name,
            )
            return scout

        # ------------------------------------------------------------------ #
        # 2. Resolve paths
        # ------------------------------------------------------------------ #
        project_root = Path(context.run_dir).parent.parent
        knowledge_dir = project_root / "knowledge" / family / platform
        clone_cache_dir = project_root / "intake" / ".clone_cache"

        # content_repo_dir from config (optional — needed for pass4 only)
        content_repo_dir: Path | None = None
        output_config = getattr(context.config, "output", None)
        if output_config is not None:
            raw_repo_dir = getattr(output_config, "content_repo_dir", None)
            if raw_repo_dir:
                try:
                    from launcher.workers.publish._git_publisher import resolve_content_repo_dir
                    content_repo_dir = resolve_content_repo_dir(raw_repo_dir)
                except Exception as exc:
                    logger.debug("[Verify] Could not resolve content_repo_dir: %s", exc)

        # ------------------------------------------------------------------ #
        # 3. Pass 1 — SHA check
        # ------------------------------------------------------------------ #
        is_clean, baseline_sha = pass1_sha_check(knowledge_dir, current_repo_sha)

        if is_clean:
            context.log.info(
                "[Verify] SHA unchanged (%s) — emitting clean drift report",
                current_repo_sha[:12],
            )
            drift_report = _build_clean_report(
                family, platform, current_repo_sha, baseline_sha
            )
            _write_drift_report(drift_report, context)
            context.emit_event(
                "worker_completed",
                {"drift_status": "clean", "sha": current_repo_sha[:12]},
                worker=self.name,
            )
            return scout

        # ------------------------------------------------------------------ #
        # 4. Passes 2–4 (SHA changed or no baseline)
        # ------------------------------------------------------------------ #
        baseline_exists = bool(baseline_sha)

        # Pass 2 — Claim staleness
        current_file_tree: list[str] = list(scout.repo_info.file_tree)
        stale_claims = pass2_claim_staleness(
            knowledge_dir, clone_cache_dir, current_file_tree
        )

        # Pass 3 — New capabilities
        # api_surface may come from knowledge/api_surface.json if no live run
        current_api_surface = _load_current_api_surface(knowledge_dir, scout)
        current_format_matrix = _load_current_format_matrix(knowledge_dir)
        new_capabilities = pass3_new_capabilities(
            knowledge_dir, current_api_surface, current_format_matrix
        )

        # Pass 4 — Code freshness (only when content_repo_dir is available)
        outdated_code: list[dict[str, Any]] = []
        if content_repo_dir is not None:
            content_index_path = knowledge_dir / "content_index.yaml"
            import_allowlist: list[str] = current_api_surface.get("import_allowlist", [])
            api_identifiers: list[str] = current_api_surface.get("api_identifiers", [])
            outdated_code = pass4_code_freshness(
                content_index_path,
                content_repo_dir,
                import_allowlist,
                api_identifiers,
            )
        else:
            logger.debug("[Verify] No content_repo_dir — skipping pass4 code freshness")

        # ------------------------------------------------------------------ #
        # 5. Synthesize drift report
        # ------------------------------------------------------------------ #
        drift_status = compute_drift_status(
            baseline_exists, stale_claims, new_capabilities, outdated_code
        )

        # Load content_index for page-level action decisions
        content_index: dict[str, Any] = {}
        content_index_path = knowledge_dir / "content_index.yaml"
        if content_index_path.exists() and _yaml is not None:
            try:
                content_index = (
                    _yaml.safe_load(content_index_path.read_text(encoding="utf-8")) or {}
                )
            except Exception as exc:
                logger.debug("[Verify] Failed to load content_index.yaml: %s", exc)

        page_drift_actions = compute_page_drift_actions(
            content_index, stale_claims, new_capabilities, outdated_code
        )

        drift_report: dict[str, Any] = {
            "family": family,
            "platform": platform,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "repo_sha_before": baseline_sha,
            "repo_sha_after": current_repo_sha,
            "drift_status": drift_status,
            "stale_claims": stale_claims,
            "new_capabilities": new_capabilities,
            "outdated_code_examples": outdated_code,
            "page_drift_actions": page_drift_actions,
        }

        _write_drift_report(drift_report, context)

        context.log.info(
            "[Verify] Done: drift_status=%s stale_claims=%d new_caps=%d outdated_code=%d pages=%d",
            drift_status,
            len(stale_claims),
            len(new_capabilities),
            len(outdated_code),
            len(page_drift_actions),
        )

        # ------------------------------------------------------------------ #
        # 6. Write drift_baseline.yaml + update model.yaml last_verified_at
        # ------------------------------------------------------------------ #
        claims = _load_claims_json(knowledge_dir)
        write_drift_baseline(
            knowledge_dir,
            family,
            platform,
            current_repo_sha,
            claims,
            current_format_matrix,
        )
        _update_model_yaml_verified_at(knowledge_dir)

        context.emit_event(
            "worker_completed",
            {
                "drift_status": drift_status,
                "stale_claims": len(stale_claims),
                "new_capabilities": len(new_capabilities),
                "outdated_code_examples": len(outdated_code),
            },
            worker=self.name,
        )
        return scout

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Self-review for Verify worker — minimal (verify is deterministic)."""
        if not isinstance(output, ScoutBundle):
            return SelfReviewResult(
                passed=False,
                findings=[{"message": "Output is not ScoutBundle"}],
            )
        return SelfReviewResult(passed=True, findings=[], metrics={})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_clean_report(
    family: str, platform: str, current_sha: str, baseline_sha: str
) -> dict[str, Any]:
    """Return a minimal drift_report dict for the SHA-unchanged case."""
    return {
        "family": family,
        "platform": platform,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "repo_sha_before": baseline_sha,
        "repo_sha_after": current_sha,
        "drift_status": "clean",
        "stale_claims": [],
        "new_capabilities": [],
        "outdated_code_examples": [],
        "page_drift_actions": {},
    }


def _write_drift_report(report: dict[str, Any], context: WorkerContext) -> None:
    """Write drift_report.json to the run directory."""
    try:
        context.store.write_json("drift_report.json", report)
        context.log.info("[Verify] drift_report.json written")
    except Exception as exc:
        context.log.warning("[Verify] Failed to write drift_report.json: %s", exc)


def _load_current_api_surface(
    knowledge_dir: Path, scout: ScoutBundle
) -> dict[str, Any]:
    """Load current api_surface from knowledge/api_surface.json.

    Falls back to an empty dict if not found.  In a full maintain-mode run,
    the Understand worker would have written this after Scout; in verify-only
    mode we use the snapshot from the last understand run.
    """
    api_path = knowledge_dir / "api_surface.json"
    if api_path.exists():
        try:
            return json.loads(api_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("[Verify] Failed to load api_surface.json: %s", exc)
    return {}


def _load_current_format_matrix(knowledge_dir: Path) -> list[dict[str, Any]]:
    """Load the current format_matrix from knowledge/api_surface.json.

    Returns the ``format_matrix`` array or an empty list.
    """
    api_path = knowledge_dir / "api_surface.json"
    if api_path.exists():
        try:
            data = json.loads(api_path.read_text(encoding="utf-8"))
            fm = data.get("format_matrix", [])
            if isinstance(fm, list):
                return fm
        except Exception as exc:
            logger.debug("[Verify] Failed to load format_matrix: %s", exc)
    return []


def _load_claims_json(knowledge_dir: Path) -> list[dict[str, Any]]:
    """Load claims.json from knowledge_dir for use in drift_baseline fingerprints."""
    claims_path = knowledge_dir / "claims.json"
    if claims_path.exists():
        try:
            data = json.loads(claims_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.debug("[Verify] Failed to load claims.json: %s", exc)
    return []


def _update_model_yaml_verified_at(knowledge_dir: Path) -> None:
    """Update last_verified_at in model.yaml using regex to preserve comments/formatting.

    Uses a regex line replacement rather than a YAML round-trip to avoid
    silently destroying inline comments and custom formatting in model.yaml.

    If last_verified_at does not exist, it is appended at the end of the file.
    No-ops silently if model.yaml does not exist.
    """
    import re

    model_path = knowledge_dir / "model.yaml"
    if not model_path.exists():
        return
    try:
        ts = f"'{datetime.now(timezone.utc).isoformat()}'"
        text = model_path.read_text(encoding="utf-8")

        # Replace existing last_verified_at line (preserves trailing comment if any)
        updated, n_replacements = re.subn(
            r"(?m)^(last_verified_at:\s*).*$",
            rf"\g<1>{ts}",
            text,
        )
        if n_replacements == 0:
            # Field not present → append at end of file
            updated = text.rstrip() + f"\nlast_verified_at: {ts}\n"

        model_path.write_text(updated, encoding="utf-8")
        logger.debug("[Verify] Updated model.yaml last_verified_at (regex in-place)")
    except Exception as exc:
        logger.warning("[Verify] Failed to update model.yaml: %s", exc)


def create_worker() -> VerifyWorker:
    return VerifyWorker()
