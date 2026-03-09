"""FOSS Launcher v2 CLI."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from launcher.cli.deploy import deploy_app
from launcher.cli.heal import heal_app
from launcher.cli.intake import intake_app

logger = logging.getLogger(__name__)

app = typer.Typer(name="launch", help="FOSS Launcher v2 — publication-ready content generation")
app.add_typer(intake_app, name="intake")
app.add_typer(deploy_app, name="deploy")
app.add_typer(heal_app, name="heal")


_VALID_WORKERS = ["intake", "understand", "planner", "generate", "evaluate", "publish"]


def _print_worker_summary(worker_name: str, output: dict) -> None:
    """Print a human-readable summary for a single worker's output."""
    typer.echo(f"\n--- {worker_name.upper()} ---")

    if worker_name == "intake":
        typer.echo(f"  Family:    {output.get('family', '?')}")
        typer.echo(f"  Platform:  {output.get('platform', '?')}")
        typer.echo(f"  Display:   {output.get('display_name', '?')}")
        typer.echo(f"  Import:    {output.get('canonical_import', '?')}")
        typer.echo(f"  Tier:      {output.get('launch_tier', '?')}")
        typer.echo(f"  SHA:       {(output.get('repo_sha') or '?')[:12]}")

    elif worker_name == "understand":
        claims = output.get("claims", [])
        snippets = output.get("snippets", [])
        pages = output.get("pages", [])
        tier = output.get("richness_tier", {})
        api = output.get("api_surface", {})
        repo = output.get("repo", {})
        mandatory = sum(1 for p in pages if p.get("mandatory"))
        optional = len(pages) - mandatory
        typer.echo(f"  Tier:      {tier.get('tier', '?')} (score={tier.get('score', '?')})")
        typer.echo(f"  Claims:    {len(claims)}")
        typer.echo(f"  Snippets:  {len(snippets)}")
        typer.echo(f"  Pages:     {len(pages)} ({mandatory} mandatory, {optional} optional)")
        typer.echo(f"  API:       {len(api.get('public_classes', []))} public classes")
        typer.echo(f"  Files:     {repo.get('content_files_read', '?')} read ({(repo.get('content_budget_used') or 0) / 1024:.1f} KB)")

    elif worker_name == "planner":
        pages = output.get("pages", [])
        mandatory = sum(1 for p in pages if p.get("mandatory"))
        typer.echo(f"  Pages:     {len(pages)} ({mandatory} mandatory, {len(pages) - mandatory} optional)")

    elif worker_name == "generate":
        pages = output.get("pages", [])
        stats = output.get("generation_stats", {})
        typer.echo(f"  Pages:     {len(pages)}")
        typer.echo(f"  LLM calls: {stats.get('llm_calls', 0)}")
        typer.echo(f"  Fallbacks: {stats.get('fallback_count', 0)}")
        typer.echo(f"  Duration:  {stats.get('duration_seconds', 0):.1f}s")

    elif worker_name == "evaluate":
        typer.echo(f"  Verdict:   {output.get('verdict', '?')}")
        quality = output.get("quality", {})
        if quality.get("pages_by_grade"):
            typer.echo(f"  Grades:    {quality['pages_by_grade']}")
        for c in output.get("go_criteria", []):
            status = "PASS" if c.get("passed") else "FAIL"
            typer.echo(f"  [{status}] {c.get('criterion', '?')}: {c.get('actual', '?')} (threshold: {c.get('threshold', '?')})")

    elif worker_name == "publish":
        patches = output.get("patches", [])
        pr = output.get("pr", {})
        typer.echo(f"  Patches:   {len(patches)}")
        typer.echo(f"  PR:        {pr.get('url', 'none')} ({pr.get('state', '?')})")


@app.command()
def run(
    config: Path = typer.Argument(..., help="Path to run config YAML"),
    resume_from: str = typer.Option("", help="Resume from worker (e.g., 'generate')"),
    stop_after: str = typer.Option("", help="Stop after worker (e.g., 'understand')"),
    run_id: str = typer.Option("", help="Explicit run ID to reuse (for resume)"),
    dry_run: bool = typer.Option(False, help="Validate config without running"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
    stream: bool = typer.Option(False, "--stream", help="Print per-worker progress to stderr"),
) -> None:
    """Execute a content generation pipeline run."""
    from launcher.io.run_config import _apply_llm_defaults
    from launcher.io.yamlio import load_yaml
    from launcher.models.run_config import RunConfig

    if stop_after and stop_after not in _VALID_WORKERS:
        typer.echo(f"Error: --stop-after must be one of {_VALID_WORKERS}", err=True)
        raise typer.Exit(code=1)

    if stop_after and resume_from:
        try:
            stop_idx = _VALID_WORKERS.index(stop_after)
            resume_idx = _VALID_WORKERS.index(resume_from)
        except ValueError:
            typer.echo(
                f"Error: --resume-from must be one of {_VALID_WORKERS}", err=True,
            )
            raise typer.Exit(code=1)
        if resume_idx >= stop_idx:
            typer.echo(
                f"Error: --resume-from '{resume_from}' must come before "
                f"--stop-after '{stop_after}' in pipeline order",
                err=True,
            )
            raise typer.Exit(code=1)

    if run_id and not resume_from:
        typer.echo(
            "Error: --run-id requires --resume-from (to avoid corrupting an existing run)",
            err=True,
        )
        raise typer.Exit(code=1)

    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    raw = load_yaml(config)
    raw = _apply_llm_defaults(raw, Path.cwd())
    run_config = RunConfig(**raw)

    if dry_run:
        typer.echo(f"Config valid: {run_config.family}/{run_config.platform}")
        typer.echo(f"LLM: {run_config.llm.primary.model if run_config.llm else 'none'}")
        raise typer.Exit()

    from launcher.orchestrator.run_loop import execute_run

    result = asyncio.run(execute_run(
        run_config,
        resume_from=resume_from,
        stop_after=stop_after,
        run_id=run_id,
        source_config_path=str(config),
        stream_progress=stream,
    ))

    # Print per-worker summaries in pipeline order
    for wname in _VALID_WORKERS:
        if wname in result.worker_outputs:
            _print_worker_summary(wname, result.worker_outputs[wname])

    typer.echo(f"\nRun dir: {result.run_dir}")

    if result.report is not None:
        typer.echo(f"Verdict: {result.report.verdict.value}")
    elif stop_after:
        typer.echo(f"Pipeline stopped after: {stop_after}")


@app.command()
def validate(
    config: Path = typer.Argument(..., help="Path to run config YAML"),
) -> None:
    """Validate a run config without executing."""
    from launcher.io.run_config import _apply_llm_defaults
    from launcher.io.yamlio import load_yaml
    from launcher.models.run_config import RunConfig

    raw = load_yaml(config)
    raw = _apply_llm_defaults(raw, Path.cwd())
    run_config = RunConfig(**raw)
    typer.echo(f"Valid: {run_config.family}/{run_config.platform} tier={run_config.launch_tier}")
    if run_config.llm:
        typer.echo(f"Primary LLM: {run_config.llm.primary.model} @ {run_config.llm.primary.base_url}")
        if run_config.llm.fallback:
            typer.echo(f"Fallback LLM: {run_config.llm.fallback.model} @ {run_config.llm.fallback.base_url}")


if __name__ == "__main__":
    app()
