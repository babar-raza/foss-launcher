"""CLI subcommands for the intake discovery system."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import typer

logger = logging.getLogger(__name__)


def _emit_intake_event(
    event_type: str,
    data: Dict[str, Any],
    state_dir: Optional[Path] = None,
) -> None:
    """Emit an intake telemetry event to the intake events log.

    Failures are logged but never block CLI operation.
    """
    try:
        from launcher.models.event import Event
        from launcher.state.event_log import append_event, generate_event_id

        target_dir = state_dir or Path("intake")
        target_dir.mkdir(parents=True, exist_ok=True)
        events_file = target_dir / "intake_events.ndjson"

        event = Event(
            event_id=generate_event_id(),
            event_type=event_type,
            run_id="",
            timestamp=datetime.now(timezone.utc).isoformat(),
            worker="intake",
            data=data,
        )
        append_event(events_file, event)
        logger.debug("Intake event emitted: %s", event_type)
    except Exception as exc:
        logger.debug("Intake telemetry failed (non-blocking): %s", exc)

intake_app = typer.Typer(
    name="intake",
    help="GitHub organization monitoring and pilot intake system.",
    add_completion=False,
)


def _repo_root() -> Path:
    """Get repository root directory (3 levels up from src/launcher/cli/intake.py)."""
    return Path(__file__).resolve().parents[3]


def _load_intake_config(config_path: Optional[Path]) -> Optional[Any]:
    """Load intake config from explicit path or auto-detect default location."""
    from launcher.phase1.config_loader import IntakeConfigError, load_intake_config

    if config_path is not None:
        return load_intake_config(config_path)

    default = _repo_root() / "configs" / "intake_config.yaml"
    if default.exists():
        return load_intake_config(default)

    return None


@intake_app.command(name="scan")
def intake_scan(
    orgs: Optional[str] = typer.Option(
        None, "--orgs",
        help="Comma-separated list of GitHub organization names. Overrides config.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print results without persisting state."),
    config: Optional[Path] = typer.Option(
        None, "--config", exists=True, dir_okay=False,
        help="Path to intake config YAML. Auto-detects configs/intake_config.yaml if absent.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Scan GitHub organizations for public repositories."""
    from launcher.phase1.config_loader import IntakeConfigError, resolve_token
    from launcher.intake.org_scanner import ScannerError, scan_orgs

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    t0 = time.monotonic()

    try:
        intake_cfg = _load_intake_config(config)
    except IntakeConfigError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)

    if orgs is not None:
        org_list = [o.strip() for o in orgs.split(",") if o.strip()]
    elif intake_cfg is not None:
        org_list = [org.name for org in intake_cfg.organizations]
    else:
        org_list = []

    if not org_list:
        typer.echo("ERROR: No organizations specified. Provide --orgs or create configs/intake_config.yaml.", err=True)
        raise typer.Exit(1)

    if intake_cfg is not None:
        token = resolve_token(intake_cfg.scanner)
        scanner_cfg = intake_cfg.scanner
    else:
        token = os.environ.get("GITHUB_TOKEN")
        scanner_cfg = None

    state_dir = None if dry_run else (_repo_root() / (intake_cfg.state_dir if intake_cfg else "intake"))

    try:
        kwargs: Dict[str, Any] = {}
        if scanner_cfg is not None:
            kwargs.update(
                per_page=scanner_cfg.per_page,
                max_pages=scanner_cfg.max_pages,
                activity_months=scanner_cfg.activity_months,
                rate_limit_delay_s=scanner_cfg.rate_limit_delay_s,
            )
        repos = scan_orgs(org_list, token=token, state_dir=state_dir, **kwargs)
    except ScannerError as e:
        typer.echo(f"ERROR: Scanner failed: {e}", err=True)
        raise typer.Exit(1)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    typer.echo(f"Scan complete. Discovered {len(repos)} repos from {len(org_list)} org(s).")
    for repo in repos:
        stars = repo.get("stargazers_count", 0)
        typer.echo(f"  - {repo['full_name']} ({stars} stars)")

    _emit_intake_event(
        "intake_scan_complete",
        {
            "org_count": len(org_list),
            "repo_count": len(repos),
            "elapsed_ms": elapsed_ms,
            "dry_run": dry_run,
        },
        state_dir=state_dir,
    )


@intake_app.command(name="classify")
def intake_classify(
    repo_url: str = typer.Option(
        ..., "--repo",
        help="GitHub repository URL to classify.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Classify a single repository for pipeline eligibility."""
    from launcher.phase1.classification import classify_inspection
    from launcher.intake.org_scanner import ScannerError, scan_org
    from launcher.phase1.inspection import inspect_repo, write_inspection_artifact

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?", repo_url)
    if not match:
        typer.echo(f"ERROR: Invalid GitHub URL: {repo_url}", err=True)
        raise typer.Exit(1)

    org_name, repo_name = match.group(1), match.group(2)
    token = os.environ.get("GITHUB_TOKEN")

    try:
        repos = scan_org(org_name, token=token, max_pages=5)
    except ScannerError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)

    target = None
    for r in repos:
        if r.get("name", "").lower() == repo_name.lower():
            target = r
            break

    if target is None:
        typer.echo(f"WARNING: Repo '{repo_name}' not found in org '{org_name}' scan results.", err=True)
        raise typer.Exit(1)

    inspection = inspect_repo(target, work_dir=_repo_root() / "intake" / "classify_work")
    result = classify_inspection(inspection)
    artifact_path = _repo_root() / "intake" / "phase1_artifacts" / f"{org_name}_{repo_name}_classify.json"
    write_inspection_artifact(artifact_path, inspection=inspection, classification=result.to_dict())
    typer.echo(f"{result.decision}: {result.full_name}")
    for reason in result.reasons:
        typer.echo(f"  - {reason}")
    typer.echo(f"  - artifact: {artifact_path}")


@intake_app.command(name="generate")
def intake_generate(
    repo_url: str = typer.Option(
        ..., "--repo",
        help="GitHub repository URL to generate config for.",
    ),
    output: Path = typer.Option(
        "configs/pilots", "--output",
        help="Output directory for the generated config.",
    ),
    platform: Optional[str] = typer.Option(
        None, "--platform",
        help="Override auto-detected platform (e.g. python, java, dotnet).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
    force: bool = typer.Option(False, "--force", "-f", help="Force generation for needs_review repos."),
) -> None:
    """Generate a pilot config YAML for a repository."""
    from launcher.phase1.classification import classify_inspection
    from launcher.phase1.config_generator import check_dedup, write_config
    from launcher.intake.org_scanner import ScannerError, scan_org
    from launcher.phase1.inspection import inspect_repo, write_inspection_artifact

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?", repo_url)
    if not match:
        typer.echo(f"ERROR: Invalid GitHub URL: {repo_url}", err=True)
        raise typer.Exit(1)

    org_name, repo_name = match.group(1), match.group(2)
    token = os.environ.get("GITHUB_TOKEN")

    try:
        repos = scan_org(org_name, token=token, max_pages=5)
    except ScannerError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)

    target = None
    for r in repos:
        if r.get("name", "").lower() == repo_name.lower():
            target = r
            break

    if target is None:
        typer.echo(f"WARNING: Repo '{repo_name}' not found.", err=True)
        raise typer.Exit(1)

    output_dir = Path(output).resolve() if not Path(output).is_absolute() else Path(output)

    if check_dedup(target, output_dir):
        typer.echo(f"Skipping: Config already exists for {target.get('full_name', repo_url)}")
        return

    inspection = inspect_repo(
        target,
        work_dir=_repo_root() / "intake" / "generate_work",
        platform=platform,
    )
    classification = classify_inspection(inspection)
    artifact_path = _repo_root() / "intake" / "phase1_artifacts" / f"{org_name}_{repo_name}_generate.json"
    write_inspection_artifact(artifact_path, inspection=inspection, classification=classification.to_dict())
    if classification.decision == "needs_review" and force:
        typer.echo(f"[force-generated] Overriding needs_review for {classification.full_name}")
    elif classification.decision != "eligible":
        typer.echo(f"Not generated: {classification.decision} for {classification.full_name}")
        for reason in classification.reasons:
            typer.echo(f"  - {reason}")
        typer.echo(f"  - artifact: {artifact_path}")
        raise typer.Exit(1)

    path = write_config(target, output_dir, platform=platform)
    if path:
        typer.echo(f"Generated: {path}")
        typer.echo(f"Inspection artifact: {artifact_path}")
    else:
        typer.echo("No config generated (dedup).")


@intake_app.command(name="onboard")
def intake_onboard(
    orgs: Optional[str] = typer.Option(
        None, "--orgs",
        help="Comma-separated list of GitHub organization names. Overrides config.",
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", exists=True, dir_okay=False,
        help="Path to intake config YAML. Auto-detects configs/intake_config.yaml if absent.",
    ),
    batch_size: int = typer.Option(
        0, "--batch-size",
        help="Max repos to process (0 = all eligible).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing config files."),
    output: Path = typer.Option(
        "configs/pilots", "--output",
        help="Output directory for generated pilot configs.",
    ),
    template: Optional[Path] = typer.Option(
        None, "--template", exists=True, dir_okay=False,
        help="Custom base template YAML for generated configs.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Scan, classify, and generate pilot configs for all eligible repos."""
    import yaml as _yaml

    from launcher.phase1.config_loader import IntakeConfigError, resolve_token
    from launcher.intake.org_scanner import ScannerError, scan_orgs
    from launcher.phase1.classification import ClassifierConfig
    from launcher.intake.scheduler import schedule

    t0 = time.monotonic()

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Load intake config
    try:
        intake_cfg = _load_intake_config(config)
    except IntakeConfigError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1)

    # Determine org list
    if orgs is not None:
        org_list = [o.strip() for o in orgs.split(",") if o.strip()]
    elif intake_cfg is not None:
        org_list = [org.name for org in intake_cfg.organizations]
    else:
        org_list = []

    if not org_list:
        typer.echo("ERROR: No organizations specified. Provide --orgs or create configs/intake_config.yaml.", err=True)
        raise typer.Exit(1)

    # Resolve token
    if intake_cfg is not None:
        token = resolve_token(intake_cfg.scanner)
        scanner_cfg = intake_cfg.scanner
    else:
        token = os.environ.get("GITHUB_TOKEN")
        scanner_cfg = None

    # Scan
    state_dir = None if dry_run else (_repo_root() / (intake_cfg.state_dir if intake_cfg else "intake"))

    try:
        scan_kwargs: Dict[str, Any] = {}
        if scanner_cfg is not None:
            scan_kwargs.update(
                per_page=scanner_cfg.per_page,
                max_pages=scanner_cfg.max_pages,
                activity_months=scanner_cfg.activity_months,
                rate_limit_delay_s=scanner_cfg.rate_limit_delay_s,
            )
        repos = scan_orgs(org_list, token=token, state_dir=state_dir, **scan_kwargs)
    except ScannerError as e:
        typer.echo(f"ERROR: Scanner failed: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Scanned {len(org_list)} org(s), discovered {len(repos)} repo(s).")

    if not repos:
        typer.echo("No repos discovered. Nothing to onboard.")
        return

    # Build classifier config
    classifier_config = None
    if intake_cfg is not None:
        cls = intake_cfg.classifier
        kwargs_cls: Dict[str, Any] = {
            "min_stars": cls.min_stars,
            "require_readme": cls.require_readme,
            "require_python": cls.require_python,
            "require_license": cls.require_license,
        }
        if cls.allowed_licenses is not None:
            kwargs_cls["allowed_licenses"] = frozenset(cls.allowed_licenses)
        classifier_config = ClassifierConfig(**kwargs_cls)

    # Build org_configs for platform resolution
    org_configs = None
    if intake_cfg is not None:
        org_configs = {org.name: org for org in intake_cfg.organizations}

    # Load custom template
    template_dict = None
    if template is not None:
        try:
            template_dict = _yaml.safe_load(template.read_text(encoding="utf-8"))
            if not isinstance(template_dict, dict):
                typer.echo("ERROR: Template must be a YAML mapping.", err=True)
                raise typer.Exit(1)
        except _yaml.YAMLError as e:
            typer.echo(f"ERROR: Invalid template YAML: {e}", err=True)
            raise typer.Exit(1)

    # Resolve output directory
    output_dir = Path(output).resolve() if not Path(output).is_absolute() else Path(output)

    # Effective batch_size (0 = all)
    effective_batch_size = batch_size if batch_size > 0 else len(repos)

    # Scheduling params from config
    sort_by = "stars"
    sort_order = "desc"
    if intake_cfg is not None:
        sort_by = intake_cfg.scheduler.sort_by
        sort_order = intake_cfg.scheduler.sort_order

    artifact_dir = _repo_root() / "intake" / "phase1_artifacts"

    # Schedule
    report = schedule(
        repos,
        output_dir=output_dir,
        artifact_dir=artifact_dir,
        batch_size=effective_batch_size,
        sort_by=sort_by,
        sort_order=sort_order,
        dry_run=dry_run,
        classifier_config=classifier_config,
        template=template_dict,
        state_dir=state_dir,
        org_configs=org_configs,
    )

    # Print summary
    summary = report["summary"]
    typer.echo(f"\n{'Metric':<20} {'Count':>6}")
    typer.echo(f"{'-'*20} {'-'*6}")
    typer.echo(f"{'Total scanned':<20} {summary['total_scanned']:>6}")
    typer.echo(f"{'Eligible':<20} {summary['eligible']:>6}")
    typer.echo(f"{'Needs review':<20} {summary['needs_review']:>6}")
    typer.echo(f"{'Ineligible':<20} {summary['ineligible']:>6}")
    typer.echo(f"{'Skipped (dedup)':<20} {summary['skipped_dedup']:>6}")
    typer.echo(f"{'Processed':<20} {summary['processed']:>6}")

    if report["processed"]:
        typer.echo(f"\n{'Repo':<50} {'Platform':<12} {'Stars':>5} {'Action'}")
        typer.echo(f"{'-'*50} {'-'*12} {'-'*5} {'-'*15}")
        for item in report["processed"]:
            typer.echo(
                f"{item['full_name']:<50} {item['platform']:<12} {item['stars']:>5} {item['action']}"
            )
            typer.echo(f"  artifact: {item['artifact_path']}")

    if dry_run:
        typer.echo("\nDry-run mode: no config files were written.")
    else:
        typer.echo(f"\nSuccess: {summary['processed']} config(s) generated in {output_dir}")

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    _emit_intake_event(
        "intake_onboard_complete",
        {
            "org_count": len(org_list),
            "total_scanned": summary["total_scanned"],
            "eligible": summary["eligible"],
            "needs_review": summary["needs_review"],
            "ineligible": summary["ineligible"],
            "skipped_dedup": summary["skipped_dedup"],
            "processed": summary["processed"],
            "elapsed_ms": elapsed_ms,
            "dry_run": dry_run,
        },
        state_dir=state_dir,
    )


@intake_app.command(name="sync")
def intake_sync(
    output: Path = typer.Option(
        "configs/pilots", "--output",
        help="Output directory for generated pilot configs.",
    ),
    scan_state_file: Path = typer.Option(
        "intake/scan_state.json", "--scan-state",
        help="Path to scan_state.json (populated by intake scan or intake onboard).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing config files."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Generate pilot configs for all repos in scan_state.json that have no existing config."""
    from launcher.phase1.classification import classify_inspection
    from launcher.phase1.config_generator import check_dedup, write_config
    from launcher.intake.org_scanner import ScannerError, scan_org
    from launcher.phase1.inspection import inspect_repo, write_inspection_artifact

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Resolve scan_state path
    ss_path = Path(scan_state_file)
    if not ss_path.is_absolute():
        ss_path = _repo_root() / ss_path

    if not ss_path.exists():
        typer.echo(f"ERROR: scan_state.json not found at {ss_path}", err=True)
        raise typer.Exit(1)

    with open(ss_path, encoding="utf-8") as f:
        state = json.load(f)

    seen_repos: list = state.get("seen_repos", [])
    if not seen_repos:
        typer.echo("No repos in scan_state.json. Nothing to sync.")
        return

    output_dir = Path(output).resolve() if not Path(output).is_absolute() else Path(output)
    token = os.environ.get("GITHUB_TOKEN")
    artifact_dir = _repo_root() / "intake" / "phase1_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    counts: Dict[str, int] = {
        "generated": 0,
        "already_exists": 0,
        "needs_review": 0,
        "ineligible": 0,
        "error": 0,
    }

    typer.echo(f"Syncing {len(seen_repos)} repo(s) from scan_state.json...")

    for slug in seen_repos:
        # Parse "org/repo" slug
        parts = slug.split("/", 1)
        if len(parts) != 2:
            typer.echo(f"  [error]     {slug!r}: invalid slug format — skipped")
            counts["error"] += 1
            continue

        org_name, repo_name = parts
        html_url = f"https://github.com/{slug}"

        # Build minimal repo dict for the dedup check (avoids a GitHub API call when config exists)
        minimal_repo: Dict[str, Any] = {
            "full_name": slug,
            "name": repo_name,
            "owner": {"login": org_name},
            "html_url": html_url,
        }

        if check_dedup(minimal_repo, output_dir):
            typer.echo(f"  [exists]    {slug}")
            counts["already_exists"] += 1
            continue

        # Config missing — fetch full metadata from GitHub for inspection + generation
        try:
            repos = scan_org(org_name, token=token, max_pages=5)
        except ScannerError as e:
            typer.echo(f"  [error]     {slug}: GitHub scan failed: {e}")
            counts["error"] += 1
            continue

        target = None
        for r in repos:
            if r.get("name", "").lower() == repo_name.lower():
                target = r
                break

        if target is None:
            typer.echo(f"  [error]     {slug}: repo not found in org scan")
            counts["error"] += 1
            continue

        # Inspect and classify
        inspection = inspect_repo(
            target,
            work_dir=_repo_root() / "intake" / "sync_work",
        )
        classification = classify_inspection(inspection)

        artifact_slug = re.sub(r"[^a-z0-9]+", "_", slug.lower())
        artifact_path = artifact_dir / f"{artifact_slug}_sync.json"
        write_inspection_artifact(
            artifact_path, inspection=inspection, classification=classification.to_dict()
        )

        if classification.decision == "needs_review":
            reasons = "; ".join(classification.reasons)
            typer.echo(f"  [needs_review] {slug}: {reasons}")
            counts["needs_review"] += 1
            continue

        if classification.decision != "eligible":
            reasons = "; ".join(classification.reasons)
            typer.echo(f"  [ineligible]   {slug}: {reasons}")
            counts["ineligible"] += 1
            continue

        if dry_run:
            typer.echo(f"  [would generate] {slug}")
            counts["generated"] += 1
        else:
            path = write_config(target, output_dir)
            if path:
                typer.echo(f"  [generated]  {slug} → {path.name}")
                counts["generated"] += 1
            else:
                typer.echo(f"  [exists]     {slug} (dedup during write)")
                counts["already_exists"] += 1

    # Print summary
    typer.echo(f"\n{'Metric':<22} {'Count':>6}")
    typer.echo(f"{'-'*22} {'-'*6}")
    typer.echo(f"{'Generated':<22} {counts['generated']:>6}")
    typer.echo(f"{'Already exists':<22} {counts['already_exists']:>6}")
    typer.echo(f"{'Needs review':<22} {counts['needs_review']:>6}")
    typer.echo(f"{'Ineligible':<22} {counts['ineligible']:>6}")
    typer.echo(f"{'Error':<22} {counts['error']:>6}")
    if dry_run:
        typer.echo("\nDry-run mode: no config files were written.")
