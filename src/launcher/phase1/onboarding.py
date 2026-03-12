"""Source-grounded Phase 1 batch onboarding."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from launcher.phase1.classification import ClassificationResult, ClassifierConfig, classify_inspection
from launcher.phase1.config_generator import _extract_platform, check_dedup, write_config
from launcher.phase1.inspection import inspect_repo, write_inspection_artifact

logger = logging.getLogger(__name__)


def _slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "repo"


def _sort_repos(
    repos: Sequence[Dict[str, Any]],
    sort_by: str = "stars",
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    reverse = sort_order == "desc"

    if sort_by == "stars":
        key_fn = lambda r: r.get("stargazers_count", 0)
    elif sort_by == "pushed_at":
        key_fn = lambda r: r.get("pushed_at", "")
    elif sort_by == "name":
        key_fn = lambda r: r.get("full_name", "").lower()
    else:
        logger.warning("Unknown sort_by '%s', defaulting to 'stars'", sort_by)
        key_fn = lambda r: r.get("stargazers_count", 0)

    return sorted(repos, key=key_fn, reverse=reverse)


def _resolve_platform(
    repo: Dict[str, Any],
    *,
    org_configs: Optional[Dict[str, Any]] = None,
    default_platform: str = "python",
) -> str:
    org_name = repo.get("full_name", "").split("/")[0] if "/" in repo.get("full_name", "") else ""
    org_cfg = (org_configs or {}).get(org_name)

    if org_cfg and getattr(org_cfg, "platform_rules", None):
        from launcher.phase1.config_loader import resolve_platform_for_repo

        repo_name = repo.get("name", "")
        resolved = resolve_platform_for_repo(repo_name, org_cfg)
        for rule in org_cfg.platform_rules:
            import fnmatch

            if fnmatch.fnmatch(repo_name.lower(), rule.name_pattern.lower()):
                return resolved

    fallback = org_cfg.default_platform if org_cfg else default_platform
    return _extract_platform(repo, default_platform=fallback)


def schedule(
    repos: Sequence[Dict[str, Any]],
    *,
    output_dir: Path,
    artifact_dir: Path,
    batch_size: int = 5,
    sort_by: str = "stars",
    sort_order: str = "desc",
    dry_run: bool = False,
    classifier_config: Optional[ClassifierConfig] = None,
    template: Optional[Dict[str, Any]] = None,
    state_dir: Optional[Path] = None,
    default_platform: str = "python",
    org_configs: Optional[Dict[str, Any]] = None,
    work_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Inspect, classify, and optionally generate configs for a batch of repos."""
    classifier_config = classifier_config or ClassifierConfig()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    inspection_root = work_dir or artifact_dir.parent / "onboard_work"
    inspection_root.mkdir(parents=True, exist_ok=True)

    classifications: List[Dict[str, Any]] = []
    eligible_repos: List[Dict[str, Any]] = []
    processed: List[Dict[str, Any]] = []
    skipped_dedup: List[str] = []

    eligible_count = 0
    needs_review_count = 0
    ineligible_count = 0

    for repo in repos:
        platform = _resolve_platform(repo, org_configs=org_configs, default_platform=default_platform)
        repo_slug = _slugify_name(repo.get("full_name", repo.get("name", "repo")))
        inspection = inspect_repo(
            repo,
            work_dir=inspection_root / repo_slug,
            platform=platform,
        )
        result = classify_inspection(inspection, config=classifier_config)
        artifact_path = artifact_dir / f"{repo_slug}_onboard.json"
        write_inspection_artifact(artifact_path, inspection=inspection, classification=result.to_dict())

        entry = {
            "full_name": result.full_name,
            "decision": result.decision,
            "reasons": list(result.reasons),
            "platform": inspection.get("platform", platform),
            "artifact_path": str(artifact_path),
        }
        classifications.append(entry)

        if result.decision == "eligible":
            eligible_count += 1
            eligible_repos.append(repo)
        elif result.decision == "needs_review":
            needs_review_count += 1
        else:
            ineligible_count += 1

    sorted_eligible = _sort_repos(eligible_repos, sort_by=sort_by, sort_order=sort_order)
    deduped: List[Dict[str, Any]] = []
    for repo in sorted_eligible:
        if check_dedup(repo, output_dir):
            skipped_dedup.append(repo.get("full_name", "unknown"))
        else:
            deduped.append(repo)

    batch = deduped[:batch_size]

    for repo in batch:
        platform = _resolve_platform(repo, org_configs=org_configs, default_platform=default_platform)
        repo_slug = _slugify_name(repo.get("full_name", repo.get("name", "repo")))
        artifact_path = artifact_dir / f"{repo_slug}_onboard.json"
        item = {
            "full_name": repo.get("full_name", ""),
            "html_url": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "platform": platform,
            "artifact_path": str(artifact_path),
        }
        if dry_run:
            item["action"] = "would_generate"
        else:
            path = write_config(
                repo,
                output_dir,
                template=template,
                platform=platform,
            )
            item["action"] = "generated"
            item["config_path"] = str(path) if path else None
        processed.append(item)

    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "phase1_onboarding",
        "dry_run": dry_run,
        "summary": {
            "total_scanned": len(repos),
            "eligible": eligible_count,
            "needs_review": needs_review_count,
            "ineligible": ineligible_count,
            "skipped_dedup": len(skipped_dedup),
            "batch_size": batch_size,
            "processed": len(processed),
        },
        "classifications": classifications,
        "processed": processed,
        "skipped_dedup": skipped_dedup,
    }

    if state_dir is not None:
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)

        report_path = state_dir / "intake_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

        state_path = state_dir / "schedule_state.json"
        existing_processed: List[str] = []
        if state_path.exists():
            with open(state_path, encoding="utf-8") as f:
                existing_state = json.load(f)
            existing_processed = existing_state.get("processed_repos", [])

        new_processed = existing_processed + [p["full_name"] for p in processed]
        state_data = {
            "last_schedule_ts": datetime.now(timezone.utc).isoformat(),
            "processed_repos": sorted(set(new_processed)),
            "total_processed": len(set(new_processed)),
        }
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, sort_keys=True)

    return report


__all__ = ["_resolve_platform", "_sort_repos", "schedule"]
