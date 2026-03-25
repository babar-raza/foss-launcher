"""Intake worker - validate RunConfig, acquire repo, produce IntakeBundle."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.intake import IntakeBundle
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult
from launcher.phase1.acquisition import (
    build_repo_signals,
    compute_acquisition_confidence,
    load_allowed_org_prefixes,
    resolve_tier,
)
from launcher.shared.identity import IdentityResolution, _clear_families_cache, resolve_identity
from launcher.workers.intake.clone import clone_repo_cached

logger = logging.getLogger(__name__)

_resolve_identity = resolve_identity
_INTAKE_CONFIG_PATH = Path(__file__).parents[4] / "configs" / "intake_config.yaml"


class IntakeWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "intake"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> IntakeBundle:
        config = context.config

        display_name, canonical_import, runtime_import, provenance = resolve_identity(
            config.family,
            config.platform,
        )
        if config.display_name:
            display_name = config.display_name
            provenance["display_name"] = "config_override"
        if config.canonical_import:
            canonical_import = config.canonical_import
            provenance["canonical_import"] = "config_override"
        if config.runtime_import:
            runtime_import = config.runtime_import
            provenance["runtime_import"] = "config_override"

        bad_provenance = provenance.get("canonical_import") in ("inferred_default", "families_yaml_fallback")
        if config.platform != "python" and bad_provenance:
            logger.warning(
                "[Intake] Platform %r not matched in families.yaml (provenance=%r) - canonical_import %r may be wrong.",
                config.platform,
                provenance.get("canonical_import"),
                canonical_import,
            )

        try:
            allowed_orgs = load_allowed_org_prefixes(_INTAKE_CONFIG_PATH) or None
            # TC-5175: seed mode forces a fresh clone to pre-populate .clone_cache/
            force_seed = getattr(config, "pipeline_mode", "create") == "seed"
            if force_seed:
                logger.info("[Intake] seed mode — forcing fresh clone for %s", config.repo_url)
            repo_dir, repo_sha, is_fresh_clone = clone_repo_cached(
                config.repo_url,
                family=config.family,
                platform=config.platform,
                work_dir=context.run_dir / "work",
                force_refresh=force_seed,
                allowed_org_prefixes=list(allowed_orgs) if allowed_orgs else None,
            )
        except Exception as exc:
            logger.error("[Intake] Clone failed for %s: %s", config.repo_url, exc, exc_info=True)
            raise RuntimeError(
                f"[Intake] Clone failed for {config.repo_url!r}: {exc}. Check repo URL, network access, and disk space."
            ) from exc

        launch_tier = resolve_tier(config.launch_tier)
        artifact = {
            "phase": "phase1_acquisition",
            "family": config.family,
            "platform": config.platform,
            "repo_url": config.repo_url,
            "display_name": display_name,
            "canonical_import": canonical_import,
            "runtime_import": runtime_import,
            "launch_tier": launch_tier,
            "repo_sha": repo_sha,
            "repo_dir": str(repo_dir),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "is_fresh_clone": is_fresh_clone,
            "clone_cache_hit": not is_fresh_clone and bool(repo_sha),
            "field_provenance": provenance,
            "acquisition_confidence": compute_acquisition_confidence(provenance),
            "repo_signals": build_repo_signals(repo_dir),
            "failure_state": "" if repo_dir.is_dir() and any(repo_dir.iterdir()) else "unusable_clone",
        }
        bundle = IntakeBundle(
            family=config.family,
            platform=config.platform,
            repo_url=config.repo_url,
            display_name=display_name,
            canonical_import=canonical_import,
            runtime_import=runtime_import,
            launch_tier=launch_tier,
            repo_sha=repo_sha,
            repo_dir=str(repo_dir),
            discovered_at=artifact["discovered_at"],
        )

        try:
            context.store.write_json("intake_bundle.json", artifact)
            logger.info(
                "[Intake] Acquisition artifact written: confidence=%s readme=%s empty=%s",
                artifact.get("acquisition_confidence"),
                artifact.get("repo_signals", {}).get("readme_present"),
                artifact.get("repo_signals", {}).get("is_empty_clone"),
            )
        except Exception:
            logger.warning("[Intake] Failed to write acquisition artifact", exc_info=True)

        if repo_sha:
            context.emit_event(
                "clone_completed",
                {
                    "repo_sha": repo_sha,
                    "fresh": is_fresh_clone,
                    "repo_dir": str(repo_dir),
                },
                worker=self.name,
            )

        logger.info(
            "[Intake] Resolved: %s | import=%s | runtime=%s | tier=%s | SHA=%s | fresh=%s | provenance=%s",
            display_name,
            canonical_import,
            runtime_import or "(none)",
            artifact["launch_tier"],
            repo_sha[:8] if repo_sha else "(empty)",
            is_fresh_clone,
            provenance,
        )
        return bundle

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        if not isinstance(output, IntakeBundle):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not IntakeBundle"}])

        findings: list[dict[str, Any]] = []
        if not output.display_name:
            findings.append({"category": "identity", "message": "display_name is empty", "severity": "high"})
        if not output.canonical_import:
            findings.append({"category": "identity", "message": "canonical_import is empty", "severity": "high"})
        if output.launch_tier not in ("full", "core", "minimal"):
            findings.append({"category": "tier", "message": f"Invalid launch_tier: {output.launch_tier}", "severity": "high"})
        if not output.repo_dir:
            findings.append({"category": "clone", "message": "repo_dir is empty (clone may have failed)", "severity": "high"})
        if output.repo_dir and not Path(output.repo_dir).is_dir():
            findings.append({"category": "clone", "message": f"repo_dir does not exist: {output.repo_dir}", "severity": "high"})
        if output.repo_dir and Path(output.repo_dir).is_dir():
            try:
                if not any(Path(output.repo_dir).iterdir()):
                    findings.append({
                        "category": "clone",
                        "message": "repo_dir exists but is empty (clone may be corrupt)",
                        "severity": "high",
                    })
            except PermissionError:
                findings.append({
                    "category": "clone",
                    "message": "repo_dir exists but is not readable (permission denied)",
                    "severity": "high",
                })
        if output.platform.lower() != "python" and output.canonical_import.endswith("_foss"):
            findings.append({
                "category": "identity",
                "severity": "high",
                "message": (
                    f"canonical_import '{output.canonical_import}' appears Python-shaped "
                    f"(ends with '_foss') for non-Python platform '{output.platform}'."
                ),
            })
        if output.platform.lower() == "python" and not output.runtime_import:
            findings.append({
                "category": "identity",
                "severity": "medium",
                "message": "runtime_import is empty for Python platform.",
            })
        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings)


def _resolve_tier(launch_tier: str) -> str:
    return resolve_tier(launch_tier)


def _compute_acquisition_confidence(provenance: dict[str, str]) -> str:
    return compute_acquisition_confidence(provenance)


def _build_repo_signals(repo_dir: Path) -> dict[str, Any]:
    return build_repo_signals(repo_dir)


def create_worker() -> IntakeWorker:
    return IntakeWorker()
