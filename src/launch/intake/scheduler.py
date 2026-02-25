"""Intake scheduler with priority queue, batch mode, and dry-run support.

Sorts eligible repositories by priority (stars, activity, name) and
processes them in configurable batch sizes.  Supports dry-run mode
that emits an ``intake_report.json`` without creating config files.

Spec reference: specs/49_github_intake.md  Section 7
TC: TC-2543
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from launch.intake.config_generator import _extract_platform, check_dedup, write_config
from launch.intake.config_loader import OrgConfig, resolve_platform_for_repo
from launch.intake.repo_classifier import ClassificationResult, ClassifierConfig, classify_repo

logger = logging.getLogger(__name__)


def _sort_repos(
    repos: Sequence[Dict[str, Any]],
    sort_by: str = "stars",
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    """Sort repos by the given criterion.

    Args:
        repos: List of slim repo dicts.
        sort_by: Sort key -- "stars", "pushed_at", or "name".
        sort_order: "asc" or "desc".

    Returns:
        Sorted list of repo dicts.
    """
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
    org_configs: Optional[Dict[str, OrgConfig]] = None,
    default_platform: str = "python",
) -> str:
    """Resolve platform for a repo using org config overrides then auto-detection.

    Priority:
    1. ``platform_rules`` from the org's config (if any rules match)
    2. Auto-detection via ``_extract_platform()`` (repo name, language, topics)
    3. ``default_platform`` from org config or caller fallback

    Args:
        repo: Slim repo dict.
        org_configs: Mapping of org name → OrgConfig for rule-based overrides.
        default_platform: Fallback when nothing else matches.

    Returns:
        Platform identifier string.
    """
    org_name = repo.get("full_name", "").split("/")[0] if "/" in repo.get("full_name", "") else ""
    org_cfg = (org_configs or {}).get(org_name)

    if org_cfg and org_cfg.platform_rules:
        repo_name = repo.get("name", "")
        resolved = resolve_platform_for_repo(repo_name, org_cfg)
        # resolve_platform_for_repo returns org default_platform when no rule matches.
        # If a rule matched (resolved differs from org default), use it directly.
        # Otherwise, fall through to auto-detection which is more capable.
        for rule in org_cfg.platform_rules:
            import fnmatch
            if fnmatch.fnmatch(repo_name.lower(), rule.name_pattern.lower()):
                return resolved  # A rule explicitly matched

    # Auto-detect from repo metadata (handles all 12 platforms)
    fallback = org_cfg.default_platform if org_cfg else default_platform
    return _extract_platform(repo, default_platform=fallback)


def schedule(
    repos: Sequence[Dict[str, Any]],
    *,
    output_dir: Path,
    batch_size: int = 5,
    sort_by: str = "stars",
    sort_order: str = "desc",
    dry_run: bool = False,
    classifier_config: Optional[ClassifierConfig] = None,
    template: Optional[Dict[str, Any]] = None,
    state_dir: Optional[Path] = None,
    default_platform: str = "python",
    org_configs: Optional[Dict[str, OrgConfig]] = None,
) -> Dict[str, Any]:
    """Schedule and process eligible repos.

    1. Classify all repos.
    2. Filter to eligible.
    3. Sort by priority.
    4. Process top ``batch_size`` repos (or all if batch_size >= total).
    5. In dry-run mode, emit report instead of writing configs.

    Args:
        repos: List of slim repo dicts from org scanner.
        output_dir: Directory for generated pilot configs.
        batch_size: Max repos to process in this run.
        sort_by: Sort criterion.
        sort_order: Sort direction.
        dry_run: If True, only emit report without writing.
        classifier_config: Config for classification.
        template: Base config template.
        state_dir: Directory for schedule_state.json persistence.
        default_platform: Fallback platform for config generation.
        org_configs: Mapping of org name → OrgConfig.  When an org has
            ``platform_rules``, those are tried first; auto-detection
            (repo name / language / topics) is the fallback.

    Returns:
        Report dict with classification summary and processed repos.
    """
    # Step 1: Classify
    classifications: List[ClassificationResult] = []
    eligible_repos: List[Dict[str, Any]] = []
    needs_review_repos: List[Dict[str, Any]] = []
    ineligible_repos: List[Dict[str, Any]] = []

    for repo in repos:
        result = classify_repo(repo, config=classifier_config)
        classifications.append(result)
        if result.decision == "eligible":
            eligible_repos.append(repo)
        elif result.decision == "needs_review":
            needs_review_repos.append(repo)
        else:
            ineligible_repos.append(repo)

    # Step 2: Sort eligible repos
    sorted_eligible = _sort_repos(eligible_repos, sort_by=sort_by, sort_order=sort_order)

    # Step 3: Dedup against existing configs
    deduped: List[Dict[str, Any]] = []
    skipped_dedup: List[str] = []
    for repo in sorted_eligible:
        if check_dedup(repo, output_dir):
            skipped_dedup.append(repo.get("full_name", "unknown"))
            logger.info("Skipping duplicate: %s", repo.get("full_name"))
        else:
            deduped.append(repo)

    # Step 4: Batch
    batch = deduped[:batch_size]

    # Step 5: Process or report
    processed: List[Dict[str, Any]] = []
    if dry_run:
        for repo in batch:
            platform = _resolve_platform(
                repo, org_configs=org_configs, default_platform=default_platform,
            )
            processed.append({
                "full_name": repo.get("full_name", ""),
                "html_url": repo.get("html_url", ""),
                "stars": repo.get("stargazers_count", 0),
                "platform": platform,
                "action": "would_generate",
            })
    else:
        for repo in batch:
            platform = _resolve_platform(
                repo, org_configs=org_configs, default_platform=default_platform,
            )
            path = write_config(
                repo, output_dir, template=template, platform=platform,
            )
            processed.append({
                "full_name": repo.get("full_name", ""),
                "html_url": repo.get("html_url", ""),
                "stars": repo.get("stargazers_count", 0),
                "platform": platform,
                "action": "generated",
                "config_path": str(path) if path else None,
            })

    # Build report
    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "summary": {
            "total_scanned": len(repos),
            "eligible": len(eligible_repos),
            "needs_review": len(needs_review_repos),
            "ineligible": len(ineligible_repos),
            "skipped_dedup": len(skipped_dedup),
            "batch_size": batch_size,
            "processed": len(processed),
        },
        "classifications": [c.to_dict() for c in classifications],
        "processed": processed,
        "skipped_dedup": skipped_dedup,
    }

    # Persist state
    if state_dir is not None:
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)

        # Write report
        report_path = state_dir / "intake_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        logger.info("Wrote intake report: %s", report_path)

        # Update schedule state
        state_path = state_dir / "schedule_state.json"
        existing_processed: List[str] = []
        if state_path.exists():
            with open(state_path, encoding="utf-8") as f:
                existing_state = json.load(f)
            existing_processed = existing_state.get("processed_repos", [])

        new_processed = existing_processed + [
            p["full_name"] for p in processed
        ]
        state_data = {
            "last_schedule_ts": datetime.now(timezone.utc).isoformat(),
            "processed_repos": sorted(set(new_processed)),
            "total_processed": len(set(new_processed)),
        }
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, sort_keys=True)
        logger.info("Updated schedule state: %s", state_path)

    return report
