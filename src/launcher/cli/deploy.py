"""CLI subcommands for deploy promotion."""

from __future__ import annotations

from pathlib import Path

import typer

from launcher.models.evaluation import Grade

deploy_app = typer.Typer(name="deploy", help="Deploy promotion commands.")


def _parse_grade(min_grade: str) -> Grade:
    """Parse a grade string into a Grade enum, or exit with an error."""
    try:
        return Grade(min_grade.upper())
    except ValueError:
        typer.echo(f"Error: invalid grade '{min_grade}'. Use A, B, C, D, or F.", err=True)
        raise typer.Exit(code=1)


@deploy_app.command(name="promote")
def promote(
    run_dir: Path = typer.Argument(..., help="Path to the run directory to promote from"),
    deploy_dir: Path = typer.Option("deploy", help="Deploy directory"),
    min_grade: str = typer.Option("C", help="Minimum grade to promote (A, B, C, D, F)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Promote qualifying pages from a run to deploy/."""
    import logging

    from launcher.deploy.promoter import promote_run

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    grade = _parse_grade(min_grade)

    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        typer.echo(f"Error: run directory not found: {run_dir}", err=True)
        raise typer.Exit(code=1)

    resolved_deploy = deploy_dir.resolve()
    report = promote_run(run_dir, resolved_deploy, min_grade=grade, dry_run=dry_run)

    if not dry_run and report.promoted > 0:
        from launcher.io.atomic import atomic_write_json

        report_path = resolved_deploy / "promotion_report.json"
        atomic_write_json(report_path, report.model_dump(mode="json"), validate_boundary=resolved_deploy)

    prefix = "[DRY RUN] " if dry_run else ""
    typer.echo(f"{prefix}Run: {report.run_id}")
    typer.echo(f"{prefix}Pages in run: {report.total_pages_in_run}")
    typer.echo(f"{prefix}Promoted: {report.promoted}")
    typer.echo(f"{prefix}Skipped (grade < {min_grade.upper()}): {report.skipped_grade_low}")
    typer.echo(f"{prefix}Skipped (no improvement): {report.skipped_no_improvement}")
    typer.echo(f"{prefix}Skipped (same content): {report.skipped_same_hash}")
    typer.echo(f"{prefix}Skipped (file missing): {report.skipped_missing_file}")

    if verbose:
        for d in report.details:
            grade_info = d.new_grade
            if d.old_grade:
                grade_info = f"{d.old_grade} -> {d.new_grade}"
            typer.echo(f"  [{d.action.value}] {d.content_path} ({grade_info})")


@deploy_app.command(name="backfill")
def backfill(
    family: str = typer.Option(..., help="Product family (e.g., cells)"),
    platform: str = typer.Option(..., help="Platform (e.g., python)"),
    runs_root: Path = typer.Option("runs", help="Root directory containing runs"),
    deploy_dir: Path = typer.Option("deploy", help="Deploy directory"),
    min_grade: str = typer.Option("C", help="Minimum grade to promote (A, B, C, D, F)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
) -> None:
    """Backfill deploy/ from all existing runs for a family/platform."""
    from launcher.deploy.promoter import backfill_runs

    grade = _parse_grade(min_grade)

    reports = backfill_runs(
        runs_root.resolve(), family, platform, deploy_dir.resolve(),
        min_grade=grade, dry_run=dry_run,
    )

    prefix = "[DRY RUN] " if dry_run else ""
    total_promoted = sum(r.promoted for r in reports)
    typer.echo(f"{prefix}Scanned {len(reports)} complete run(s) for {family}/{platform}")
    typer.echo(f"{prefix}Total pages promoted: {total_promoted}")

    for r in reports:
        if r.promoted > 0:
            typer.echo(f"  {r.run_id}: +{r.promoted} page(s)")


@deploy_app.command(name="status")
def status(
    deploy_dir: Path = typer.Option("deploy", help="Deploy directory"),
) -> None:
    """Show current deploy manifest summary."""
    from launcher.deploy.manifest import load_manifest

    manifest_path = deploy_dir.resolve() / "manifest.json"
    if not manifest_path.exists():
        typer.echo("No deploy manifest found. Run 'deploy promote' first.")
        raise typer.Exit()

    manifest = load_manifest(manifest_path)
    typer.echo(f"Deploy directory: {deploy_dir.resolve()}")
    typer.echo(f"Total pages: {len(manifest.pages)}")
    typer.echo(f"Promotions: {manifest.promotion_count}")
    typer.echo(f"Last promotion: {manifest.last_promotion or 'never'}")

    # Grade distribution
    grade_counts: dict[str, int] = {}
    for page in manifest.pages.values():
        g = page.grade.value
        grade_counts[g] = grade_counts.get(g, 0) + 1
    if grade_counts:
        typer.echo("Grade distribution:")
        for g in ["A", "B", "C", "D", "F"]:
            if g in grade_counts:
                typer.echo(f"  {g}: {grade_counts[g]}")

    # Source runs
    run_ids = {p.source_run_id for p in manifest.pages.values()}
    typer.echo(f"Source runs: {len(run_ids)}")


@deploy_app.command(name="snapshot-promote")
def snapshot_promote(
    run_dir: Path = typer.Argument(..., help="Path to the run directory"),
    snapshots_dir: Path = typer.Option("snapshots", help="Snapshots store directory"),
    phase_store_dir: Path = typer.Option("phase_store", help="Phase store directory"),
    family: str = typer.Option("", help="Product family (e.g. cells). Auto-detected from run_config.json if omitted."),
    platform: str = typer.Option("", help="Platform (e.g. python). Auto-detected from run_config.json if omitted."),
    min_grade: str = typer.Option("C", help="Minimum grade to promote (A, B, C, D, F)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Promote IR snapshots from a run to snapshots/ (and phase_store/).

    Auto-detects family/platform from run_config.json if not provided.
    """
    import logging

    from launcher.deploy.phase_promoter import promote_phase_snapshots

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    grade = _parse_grade(min_grade)

    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        typer.echo(f"Error: run directory not found: {run_dir}", err=True)
        raise typer.Exit(code=1)

    # Auto-detect family/platform from run_config.json
    if not family or not platform:
        import json
        rc_path = run_dir / "run_config.json"
        if rc_path.exists():
            try:
                rc = json.loads(rc_path.read_text(encoding="utf-8"))
                family = family or rc.get("family", "")
                platform = platform or rc.get("platform", "")
            except Exception:
                pass

    if not family or not platform:
        typer.echo("Error: --family and --platform are required (or provide run_config.json)", err=True)
        raise typer.Exit(code=1)

    report = promote_phase_snapshots(
        run_dir=run_dir,
        snapshots_dir=snapshots_dir.resolve(),
        phase_store_dir=phase_store_dir.resolve(),
        family=family,
        platform=platform,
        min_grade=grade,
        dry_run=dry_run,
    )

    prefix = "[DRY RUN] " if dry_run else ""
    typer.echo(f"{prefix}Run: {report.run_id}")
    typer.echo(f"{prefix}Pages in run: {report.total_pages_in_run}")
    typer.echo(f"{prefix}IR promoted: {report.ir_promoted}")
    typer.echo(f"{prefix}Skipped (grade < {min_grade.upper()}): {report.ir_skipped_grade_low}")
    typer.echo(f"{prefix}Skipped (no improvement): {report.ir_skipped_no_improvement}")
    typer.echo(f"{prefix}Skipped (same content): {report.ir_skipped_same_hash}")
    typer.echo(f"{prefix}Skipped (missing IR): {report.ir_skipped_missing_ir}")
    typer.echo(f"{prefix}Phase JSONs updated: {report.phase_jsons_updated}")

    if verbose:
        for d in report.details:
            grade_info = d.new_grade
            if d.old_grade:
                grade_info = f"{d.old_grade} -> {d.new_grade}"
            typer.echo(f"  [{d.action.value}] {d.content_path} ({grade_info})")


@deploy_app.command(name="snapshot-regen")
def snapshot_regen(
    snapshots_dir: Path = typer.Option("snapshots", help="Snapshots store directory"),
    output_dir: Path = typer.Option("regen", help="Output directory for regenerated .md files"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Regenerate .md files from snapshots/ IR store (zero LLM calls).

    Reads every *.ir.json in snapshots/, renders to .md via ir_renderer,
    and writes to output_dir preserving the exact path structure.
    """
    import logging

    from launcher.shared.ir_regenerate import regenerate_from_snapshots

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    written = regenerate_from_snapshots(
        snapshots_dir=snapshots_dir.resolve(),
        output_dir=output_dir.resolve(),
    )

    typer.echo(f"Regenerated {len(written)} .md file(s) → {output_dir.resolve()}")
    if verbose:
        for p in written:
            typer.echo(f"  {p}")


@deploy_app.command(name="push")
def push(
    deploy_dir: Path = typer.Option("deploy", help="Deploy directory to push from"),
    branch: str = typer.Option("", help="Git branch name (default: launch/deploy/<timestamp>)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Copy files but skip git/gh operations"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Push deploy/ contents to content repos and open pull requests.

    Reads ASPOSE_ORG_CONTENT_REPO (and ASPOSE_NET_CONTENT_REPO) from the environment.
    Pages are grouped by TLD extracted from their content_path and routed to the
    matching repo root. A single branch + PR is opened per repo.

    Example:
        launch deploy push
        launch deploy push --deploy-dir deploy/ --dry-run
    """
    import asyncio
    import logging
    import os
    from datetime import datetime, timezone

    from launcher.deploy.promoter import PromotionAction, PromotionReport, PagePromotionResult
    from launcher.workers.publish._git_publisher import (
        copy_to_content_repo,
        gh_create_pr,
        git_add_and_commit,
        git_create_branch,
        git_push,
        resolve_content_repo_dir,
    )

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    resolved_deploy = deploy_dir.resolve()
    if not resolved_deploy.is_dir():
        typer.echo(f"Error: deploy directory not found: {resolved_deploy}", err=True)
        raise typer.Exit(code=1)

    # Build content_repo_map from env
    content_repo_map: dict[str, str] = {}
    for tld, env_var in [("aspose.org", "ASPOSE_ORG_CONTENT_REPO"), ("aspose.net", "ASPOSE_NET_CONTENT_REPO")]:
        val = os.environ.get(env_var, "")
        if val:
            content_repo_map[tld] = val

    if not content_repo_map:
        typer.echo(
            "Error: no content repo configured. Set ASPOSE_ORG_CONTENT_REPO "
            "(and/or ASPOSE_NET_CONTENT_REPO) environment variables.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Collect all .md files from deploy/ as content paths
    all_paths = [
        f.relative_to(resolved_deploy).with_suffix("").as_posix()
        for f in resolved_deploy.rglob("*.md")
    ]
    if not all_paths:
        typer.echo("No .md files found in deploy/.")
        raise typer.Exit()

    typer.echo(f"Found {len(all_paths)} pages in {resolved_deploy}")

    # Group by TLD
    by_tld: dict[str, list[str]] = {}
    for cp in all_paths:
        subdomain = cp.split("/")[0]
        parts = subdomain.split(".")
        tld_key = ".".join(parts[-2:]) if len(parts) >= 2 else subdomain
        by_tld.setdefault(tld_key, []).append(cp)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    default_branch = f"launch/deploy/{ts}"
    branch_name = branch or default_branch

    for tld_key, paths in by_tld.items():
        repo_raw = content_repo_map.get(tld_key, "")
        if not repo_raw:
            typer.echo(f"  [{tld_key}] No repo configured -skipping {len(paths)} page(s)")
            continue

        content_repo_dir = resolve_content_repo_dir(repo_raw)
        if not content_repo_dir.is_dir():
            typer.echo(f"  [{tld_key}] Repo not found: {content_repo_dir} -skipping", err=True)
            continue

        typer.echo(f"  [{tld_key}] Copying {len(paths)} page(s) to {content_repo_dir}")
        written = copy_to_content_repo(resolved_deploy, content_repo_dir, paths)
        if not written:
            typer.echo(f"  [{tld_key}] No files written -skipping")
            continue

        if dry_run:
            typer.echo(f"  [{tld_key}] DRY RUN -skipping git/gh operations ({len(written)} files staged)")
            continue

        try:
            git_create_branch(content_repo_dir, branch_name)
            git_add_and_commit(content_repo_dir, written, f"docs: push deploy/ content ({ts})")
            git_push(content_repo_dir, branch_name)
            pr_url = gh_create_pr(
                content_repo_dir,
                f"[foss-launcher] deploy push {ts}",
                f"Pushed {len(written)} pages from deploy/ via `launch deploy push`.",
            )
            typer.echo(f"  [{tld_key}] PR: {pr_url} (branch: {branch_name}, files: {len(written)})")
        except Exception as exc:
            typer.echo(f"  [{tld_key}] Failed: {exc}", err=True)


@deploy_app.command(name="diff")
def diff(
    run_dir: Path = typer.Argument(..., help="Run directory to diff against deploy/"),
    deploy_dir: Path = typer.Option("deploy", help="Deploy directory"),
    min_grade: str = typer.Option("C", help="Minimum grade (A, B, C, D, F)"),
) -> None:
    """Preview what would change if a run were promoted (always dry-run)."""
    from launcher.deploy.promoter import PromotionAction, promote_run

    grade = _parse_grade(min_grade)

    report = promote_run(run_dir.resolve(), deploy_dir.resolve(), min_grade=grade, dry_run=True)

    if report.promoted == 0:
        typer.echo("No pages would be promoted.")
    else:
        typer.echo(f"{report.promoted} page(s) would be promoted:")
        for d in report.details:
            if d.action == PromotionAction.PROMOTED:
                if d.old_grade:
                    typer.echo(f"  [UPGRADE {d.old_grade}->{d.new_grade}] {d.content_path}")
                else:
                    typer.echo(f"  [NEW {d.new_grade}] {d.content_path}")
