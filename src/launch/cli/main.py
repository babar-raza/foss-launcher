"""Main CLI entrypoint for FOSS Launcher.

Provides command-line interface for:
- launch run <product> - Start a new documentation run
- launch status <run_id> - Check run status
- launch list - List all runs
- launch validate <run_id> - Run validation gates
- launch cancel <run_id> - Cancel running task
- launch mcp serve - Start MCP server (delegated to launch.mcp.server)

Binding contracts:
- docs/cli_usage.md (CLI command documentation)
- specs/19_toolchain_and_ci.md (Toolchain and CI)
- specs/01_system_contract.md (Exit codes)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="launch",
    help="FOSS Launcher - Automated documentation generation system",
    add_completion=False,
)
console = Console()


def _repo_root() -> Path:
    """Get repository root directory."""
    # src/launch/cli/main.py -> repo root
    return Path(__file__).resolve().parents[3]


def _runs_dir() -> Path:
    """Get runs directory."""
    return _repo_root() / "runs"


def _load_snapshot(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load snapshot.json if it exists."""
    snapshot_path = run_dir / "snapshot.json"
    if not snapshot_path.exists():
        return None
    try:
        with open(snapshot_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_run_config(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load run_config.yaml if it exists."""
    import yaml

    config_path = run_dir / "run_config.yaml"
    if not config_path.exists():
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _format_timestamp(ts: Optional[str]) -> str:
    """Format ISO timestamp for display."""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True,
                                help="Path to run_config YAML file"),
    run_dir: Optional[Path] = typer.Option(None, "--run_dir", help="Target RUN_DIR (runs/<run_id>)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate config without executing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Start a new documentation run.

    Example:
        launch run --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml

    Exit codes:
        0 - Success
        1 - Validation failure
        2 - Execution failure
    """
    from launch.io.run_config import load_and_validate_run_config
    from launch.io.run_layout import create_run_skeleton
    from launch.orchestrator.run_loop import execute_run
    from launch.util.run_id import make_run_id

    repo_root = _repo_root()

    # Load and validate config
    try:
        run_config = load_and_validate_run_config(repo_root, config)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] Config validation failed: {e}")
        raise typer.Exit(1)

    # Generate run_id if not provided
    if run_dir is None:
        run_id = make_run_id(
            product_slug=run_config["product_slug"],
            github_ref=run_config["github_ref"],
            site_ref=run_config.get("site_ref", "default_branch"),
            run_config=run_config,
        )
        run_dir = _runs_dir() / run_id
    else:
        run_dir = run_dir.resolve()
        run_id = run_dir.name

    # Check if run already exists
    if run_dir.exists():
        console.print(f"[yellow]WARNING:[/yellow] RUN_DIR already exists: {run_dir}")
        console.print("Use 'launch status <run_id>' to check existing run status")
        raise typer.Exit(1)

    if dry_run:
        console.print("[green]Config validation passed[/green]")
        console.print(f"Would create RUN_DIR: {run_dir}")
        console.print(f"Run ID: {run_id}")
        return

    # Create run skeleton
    console.print(f"Creating RUN_DIR: {run_dir}")
    create_run_skeleton(run_dir)

    # Copy run_config to RUN_DIR
    (run_dir / "run_config.yaml").write_text(config.read_text(encoding="utf-8"), encoding="utf-8")

    # Execute run
    console.print(f"[blue]Starting run:[/blue] {run_id}")
    console.print(f"Product: {run_config['product_slug']}")
    console.print(f"GitHub ref: {run_config['github_ref']}")

    try:
        result = execute_run(run_id, run_dir, run_config)
        console.print(f"\n[green]Run completed:[/green] {result.final_state}")
        console.print(f"Exit code: {result.exit_code}")
        raise typer.Exit(result.exit_code)
    except Exception as e:
        console.print(f"\n[red]Run failed:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(2)


@app.command()
def status(
    run_id: str = typer.Argument(..., help="Run ID to check"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
) -> None:
    """Check run status.

    Example:
        launch status aspose-note-foss-python-main-20260128

    Exit codes:
        0 - Success
        1 - Run not found
    """
    runs_dir = _runs_dir()
    run_dir = runs_dir / run_id

    if not run_dir.exists():
        console.print(f"[red]ERROR:[/red] Run not found: {run_id}")
        console.print(f"Available runs: {len(list(runs_dir.iterdir()))} total")
        raise typer.Exit(1)

    # Load snapshot
    snapshot = _load_snapshot(run_dir)
    run_config = _load_run_config(run_dir)

    # Display status
    console.print(f"\n[blue]Run Status:[/blue] {run_id}")
    console.print(f"RUN_DIR: {run_dir}")

    if snapshot:
        console.print(f"\nState: [bold]{snapshot['run_state']}[/bold]")
        console.print(f"Schema version: {snapshot.get('schema_version', 'N/A')}")

        # Show work items if verbose
        if verbose and snapshot.get("work_items"):
            console.print("\n[blue]Work Items:[/blue]")
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Worker")
            table.add_column("Status")
            table.add_column("Attempt")
            table.add_column("Started")
            table.add_column("Finished")

            for item in snapshot["work_items"]:
                table.add_row(
                    item["worker"],
                    item["status"],
                    str(item["attempt"]),
                    _format_timestamp(item.get("started_at")),
                    _format_timestamp(item.get("finished_at")),
                )
            console.print(table)

        # Show issues
        if snapshot.get("issues"):
            console.print(f"\n[yellow]Issues:[/yellow] {len(snapshot['issues'])} found")
            if verbose:
                for issue in snapshot["issues"]:
                    console.print(f"  - [{issue.get('severity', 'unknown')}] {issue.get('message', 'N/A')}")

        # Show artifacts
        artifacts_index = snapshot.get("artifacts_index")
        if artifacts_index is None:
            artifacts_index = {}
        if verbose and artifacts_index:
            console.print(f"\n[blue]Artifacts:[/blue] {len(artifacts_index)} total")
            artifact_keys = list(artifacts_index.keys())
            for path in artifact_keys[:5]:
                console.print(f"  - {path}")
            if len(artifact_keys) > 5:
                console.print(f"  ... and {len(artifact_keys) - 5} more")
    else:
        console.print("\n[yellow]No snapshot found[/yellow]")

    # Show config info
    if run_config:
        console.print(f"\n[blue]Configuration:[/blue]")
        console.print(f"Product: {run_config.get('product_slug', 'N/A')}")
        console.print(f"GitHub ref: {run_config.get('github_ref', 'N/A')}")
        console.print(f"Site ref: {run_config.get('site_ref', 'N/A')}")


@app.command()
def list(
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of runs to show"),
    all: bool = typer.Option(False, "--all", "-a", help="Show all runs (ignore limit)"),
) -> None:
    """List all runs.

    Example:
        launch list
        launch list --limit 50
        launch list --all

    Exit codes:
        0 - Success
    """
    runs_dir = _runs_dir()

    if not runs_dir.exists():
        console.print("[yellow]No runs directory found[/yellow]")
        console.print(f"Expected: {runs_dir}")
        return

    # Get all run directories
    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not run_dirs:
        console.print("[yellow]No runs found[/yellow]")
        return

    # Apply limit
    display_runs = run_dirs if all else run_dirs[:limit]

    # Create table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Run ID")
    table.add_column("State")
    table.add_column("Product")
    table.add_column("Modified")

    for run_dir in display_runs:
        snapshot = _load_snapshot(run_dir)
        run_config = _load_run_config(run_dir)

        state = snapshot["run_state"] if snapshot else "UNKNOWN"
        product = run_config.get("product_slug", "N/A") if run_config else "N/A"
        modified = datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        table.add_row(run_dir.name, state, product, modified)

    console.print(table)
    console.print(f"\nShowing {len(display_runs)} of {len(run_dirs)} total runs")


@app.command()
def validate(
    run_id: str = typer.Argument(..., help="Run ID to validate"),
    profile: str = typer.Option("local", "--profile", help="Validation profile (local/ci/prod)"),
) -> None:
    """Run validation gates on a run.

    Example:
        launch validate aspose-note-foss-python-main-20260128 --profile ci

    Exit codes:
        0 - All gates pass
        1 - One or more gates fail
    """
    from launch.validators.cli import validate as run_validate

    runs_dir = _runs_dir()
    run_dir = runs_dir / run_id

    if not run_dir.exists():
        console.print(f"[red]ERROR:[/red] Run not found: {run_id}")
        raise typer.Exit(1)

    console.print(f"[blue]Validating run:[/blue] {run_id}")
    console.print(f"Profile: {profile}")
    console.print(f"RUN_DIR: {run_dir}\n")

    try:
        run_validate(run_dir, profile)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def cancel(
    run_id: str = typer.Argument(..., help="Run ID to cancel"),
    force: bool = typer.Option(False, "--force", help="Force cancellation without confirmation"),
) -> None:
    """Cancel a running task.

    Example:
        launch cancel aspose-note-foss-python-main-20260128

    Exit codes:
        0 - Success
        1 - Run not found or already completed
    """
    runs_dir = _runs_dir()
    run_dir = runs_dir / run_id

    if not run_dir.exists():
        console.print(f"[red]ERROR:[/red] Run not found: {run_id}")
        raise typer.Exit(1)

    # Load snapshot
    snapshot = _load_snapshot(run_dir)
    if not snapshot:
        console.print(f"[red]ERROR:[/red] Cannot load snapshot for run: {run_id}")
        raise typer.Exit(1)

    current_state = snapshot["run_state"]

    # Check if run is already completed
    if current_state in ["DONE", "FAILED", "CANCELLED"]:
        console.print(f"[yellow]Run already in terminal state:[/yellow] {current_state}")
        raise typer.Exit(1)

    # Confirm cancellation
    if not force:
        confirm = typer.confirm(f"Cancel run {run_id} (current state: {current_state})?")
        if not confirm:
            console.print("Cancellation aborted")
            return

    # Update snapshot to CANCELLED state
    from launch.state.snapshot_manager import write_snapshot
    from launch.models.state import Snapshot, RUN_STATE_CANCELLED

    snapshot_obj = Snapshot.from_dict(snapshot)
    snapshot_obj.run_state = RUN_STATE_CANCELLED

    snapshot_path = run_dir / "snapshot.json"
    write_snapshot(snapshot_path, snapshot_obj)

    # Emit cancellation event
    from launch.state.event_log import append_event, generate_event_id, generate_span_id, generate_trace_id
    from launch.models.event import Event

    cancel_event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type="RUN_CANCELLED",
        payload={"reason": "User requested cancellation via CLI"},
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
    )
    append_event(run_dir / "events.ndjson", cancel_event)

    console.print(f"[green]Run cancelled:[/green] {run_id}")
    console.print(f"State updated: {current_state} -> CANCELLED")


def main() -> None:
    """Main entrypoint for launch CLI."""
    app(prog_name="launch")


if __name__ == "__main__":
    main()
