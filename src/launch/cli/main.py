"""Main CLI entrypoint for FOSS Launcher.

Provides command-line interface for:
- launch run <product> - Start a new documentation run
- launch resume --run-dir ... --from-worker W5 - Resume from a worker
- launch phase --config ... --phase-start P1 --phase-end P3 - Run bounded phases
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
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
from launch.util.path_validation import PathValidationError, validate_run_dir_under_runs

app = typer.Typer(
    name="launch",
    help="FOSS Launcher - Automated documentation generation system",
    add_completion=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Intake sub-app (TC-2544)
# ---------------------------------------------------------------------------
intake_app = typer.Typer(
    name="intake",
    help="GitHub organization monitoring and pilot intake system.",
    add_completion=False,
)
app.add_typer(intake_app, name="intake")


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
    live: bool = typer.Option(False, "--live", help="Show real-time event progress during execution"),
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

    try:
        run_dir = validate_run_dir_under_runs(run_dir)
    except PathValidationError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

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

    tailer = None
    if live:
        from launch.monitoring.event_tailer import EventTailer
        tailer = EventTailer(run_dir / "events.ndjson", console, verbose=verbose)
        tailer.start()

    try:
        result = execute_run(run_id, run_dir, run_config)
        console.print(f"\n[green]Run completed:[/green] {result.final_state}")
        console.print(f"Exit code: {result.exit_code}")
        raise typer.Exit(result.exit_code)
    except (SystemExit, typer.Exit):
        raise
    except Exception as e:
        console.print(f"\n[red]Run failed:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(2)
    finally:
        if tailer:
            tailer.stop()


@app.command()
def resume(
    run_dir: Path = typer.Option(
        ..., "--run-dir", exists=True, file_okay=False, readable=True,
        help="Existing run directory (runs/<run_id>/) to resume from",
    ),
    from_worker: str = typer.Option(
        ..., "--from-worker",
        help="Worker to resume from, e.g. W5 or draft_sections. "
             "Valid aliases: W1–W11 and full node names.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
    live: bool = typer.Option(False, "--live", help="Show real-time event progress during execution"),
) -> None:
    """Resume a run from a specific worker, reusing prior artifacts.

    Re-enters the pipeline at the specified worker using artifacts already produced
    by a prior run. Workers before --from-worker are skipped entirely.

    Example:
        launch resume --run-dir runs/r_20260221T... --from-worker W5

    Exit codes:
        0 - Success (DONE state)
        1 - Validation failure (unknown alias, missing artifacts, bad run-dir)
        2 - Execution failure (graph FAILED state)

    Spec reference: specs/43_resumable_pipeline.md
    """
    import yaml

    from launch.io.run_lock import RunAlreadyActiveError
    from launch.orchestrator.run_loop import RESUME_NODE_MAP, execute_run_from_node
    from launch.util.path_validation import PathValidationError, validate_run_dir_under_runs

    run_dir = run_dir.resolve()

    # Validate run_dir is under runs/ root
    try:
        run_dir = validate_run_dir_under_runs(run_dir)
    except PathValidationError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

    # Load run_config from run_dir
    config_path = run_dir / "run_config.yaml"
    if not config_path.exists():
        console.print(f"[red]ERROR:[/red] run_config.yaml not found in {run_dir}")
        console.print("Ensure --run-dir points to a valid run directory.")
        raise typer.Exit(1)
    try:
        with open(config_path, encoding="utf-8") as f:
            run_config = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] Failed to load run_config.yaml: {e}")
        raise typer.Exit(1)

    run_id = run_dir.name

    # Validate from_worker alias
    if from_worker not in RESUME_NODE_MAP:
        valid_short = sorted(k for k in RESUME_NODE_MAP if k.startswith("W") and k[1:].isdigit())
        console.print(f"[red]ERROR:[/red] Unknown --from-worker alias: '{from_worker}'")
        console.print(f"Valid aliases: {', '.join(valid_short)} (and full node names)")
        raise typer.Exit(1)

    node_name, pre_run_state, _ = RESUME_NODE_MAP[from_worker]
    console.print(f"[blue]Resuming run:[/blue] {run_id}")
    console.print(f"Entry point: {from_worker} → graph node '{node_name}' (state: {pre_run_state})")
    console.print(f"RUN_DIR: {run_dir}")

    tailer = None
    if live:
        from launch.monitoring.event_tailer import EventTailer
        tailer = EventTailer(run_dir / "events.ndjson", console, verbose=verbose)
        tailer.start()

    try:
        result = execute_run_from_node(run_id, run_dir, run_config, from_worker)
        console.print(f"\n[green]Resume completed:[/green] {result.final_state}")
        console.print(f"Exit code: {result.exit_code}")
        raise typer.Exit(result.exit_code)
    except (SystemExit, typer.Exit):
        raise
    except RunAlreadyActiveError as e:
        console.print(f"\n[red]ERROR:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"\n[red]Resume failed:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Resume failed:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(2)
    finally:
        if tailer:
            tailer.stop()


@app.command()
def phase(
    config: Path = typer.Option(
        ..., "--config", exists=True, dir_okay=False, readable=True,
        help="Path to run_config YAML file",
    ),
    phase_start: str = typer.Option(
        "P1", "--phase-start",
        help="First phase to execute (P1-P6)",
    ),
    phase_end: str = typer.Option(
        "P6", "--phase-end",
        help="Last phase to execute (P1-P6)",
    ),
    verify_only: bool = typer.Option(
        False, "--verify-only",
        help="Skip execution, just verify artifacts for the phase range",
    ),
    run_dir: Optional[Path] = typer.Option(
        None, "--run-dir",
        help="Existing run directory (required for --verify-only and for resuming from a later phase)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
    live: bool = typer.Option(False, "--live", help="Show real-time event progress during execution"),
    pause: bool = typer.Option(
        False, "--pause",
        help="Pause after each phase for inspection (implies --live). "
             "Press Enter to continue, 'q' to stop.",
    ),
) -> None:
    """Run a bounded set of pipeline phases with optional verification.

    Executes phases from --phase-start through --phase-end (inclusive), then
    verifies the artifacts produced by each phase.  Use --verify-only to skip
    execution and only check artifacts for an existing run.

    Phase groups:
        P1: W1-W2   (Repo ingestion + facts)
        P2: W3-W4   (Snippets + page planning)
        P3: W5-W6   (Drafting + SEO)
        P4: W7-W8   (Review + linking)
        P5: W9-W10  (Validation + fixing)
        P6: W11     (PR/packaging)

    Examples:
        launch phase --config run_config.pinned.yaml
        launch phase --config run_config.pinned.yaml --phase-start P3 --phase-end P5 --run-dir runs/r_...
        launch phase --config run_config.pinned.yaml --verify-only --run-dir runs/r_... --phase-start P1 --phase-end P2
        launch phase --config run_config.pinned.yaml --phase-start P1 --phase-end P3 --pause

    Exit codes:
        0 - All phases pass (execution + verification)
        1 - Validation/argument failure or verification failure
        2 - Execution failure

    TC-2502
    """
    import time

    from launch.orchestrator.phase_executor import (
        PHASE_GROUPS,
        execute_phase_group,
        execute_phase_range,
    )
    from launch.orchestrator.phase_verifier import verify_phase_range

    if pause:
        live = True  # --pause implies --live

    repo_root = _repo_root()

    # ------------------------------------------------------------------
    # Validate phase identifiers
    # ------------------------------------------------------------------
    for label, pid in (("--phase-start", phase_start), ("--phase-end", phase_end)):
        if pid not in PHASE_GROUPS:
            valid = ", ".join(sorted(PHASE_GROUPS.keys()))
            console.print(
                f"[red]ERROR:[/red] Invalid phase identifier for {label}: '{pid}'. "
                f"Valid phases: {valid}"
            )
            raise typer.Exit(1)

    # Validate ordering (P-number comparison via PHASE_GROUPS key order)
    phase_order = list(PHASE_GROUPS.keys())
    start_idx = phase_order.index(phase_start)
    end_idx = phase_order.index(phase_end)
    if end_idx < start_idx:
        console.print(
            f"[red]ERROR:[/red] --phase-end '{phase_end}' precedes "
            f"--phase-start '{phase_start}'. "
            f"Phase order: {', '.join(phase_order)}"
        )
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Resolve or create run_dir
    # ------------------------------------------------------------------
    if verify_only:
        # --verify-only requires --run-dir
        if run_dir is None:
            console.print(
                "[red]ERROR:[/red] --run-dir is required when --verify-only is set"
            )
            raise typer.Exit(1)
        run_dir = run_dir.resolve()
        if not run_dir.exists():
            console.print(f"[red]ERROR:[/red] --run-dir does not exist: {run_dir}")
            raise typer.Exit(1)
    elif run_dir is not None:
        # Resuming from a later phase — run_dir must exist
        run_dir = run_dir.resolve()
        if not run_dir.exists():
            console.print(f"[red]ERROR:[/red] --run-dir does not exist: {run_dir}")
            raise typer.Exit(1)
    else:
        # Fresh run starting at P1 — create a new run_dir
        from launch.io.run_config import load_and_validate_run_config
        from launch.io.run_layout import create_run_skeleton
        from launch.util.run_id import make_run_id

        try:
            run_config_data = load_and_validate_run_config(repo_root, config)
        except Exception as e:
            console.print(f"[red]ERROR:[/red] Config validation failed: {e}")
            raise typer.Exit(1)

        run_id = make_run_id(
            product_slug=run_config_data["product_slug"],
            github_ref=run_config_data["github_ref"],
            site_ref=run_config_data.get("site_ref", "default_branch"),
            run_config=run_config_data,
        )
        run_dir = _runs_dir() / run_id

        try:
            run_dir = validate_run_dir_under_runs(run_dir)
        except PathValidationError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(1)

        if run_dir.exists():
            console.print(
                f"[yellow]WARNING:[/yellow] RUN_DIR already exists: {run_dir}"
            )
            raise typer.Exit(1)

        console.print(f"Creating RUN_DIR: {run_dir}")
        create_run_skeleton(run_dir)
        (run_dir / "run_config.yaml").write_text(
            config.read_text(encoding="utf-8"), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Load run_config from run_dir (or from the just-copied file)
    # ------------------------------------------------------------------
    import yaml

    config_in_dir = run_dir / "run_config.yaml"
    if not config_in_dir.exists():
        console.print(
            f"[red]ERROR:[/red] run_config.yaml not found in {run_dir}"
        )
        raise typer.Exit(1)
    try:
        with open(config_in_dir, encoding="utf-8") as f:
            run_config = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] Failed to load run_config.yaml: {e}")
        raise typer.Exit(1)

    run_id = run_dir.name

    # ------------------------------------------------------------------
    # Verify-only mode
    # ------------------------------------------------------------------
    if verify_only:
        console.print(f"[blue]Verifying phases {phase_start}..{phase_end}[/blue]")
        console.print(f"RUN_DIR: {run_dir}\n")

        v_results = verify_phase_range(
            run_dir, phase_start, phase_end, repo_root=repo_root,
        )

        _print_verification_summary(v_results)

        all_ok = all(vr.ok for vr in v_results)
        raise typer.Exit(0 if all_ok else 1)

    # ------------------------------------------------------------------
    # Execution mode
    # ------------------------------------------------------------------
    console.print(f"[blue]Executing phases {phase_start}..{phase_end}[/blue]")
    console.print(f"RUN_DIR: {run_dir}\n")

    wall_start = time.monotonic()

    tailer = None
    if live:
        from launch.monitoring.event_tailer import EventTailer
        tailer = EventTailer(run_dir / "events.ndjson", console, verbose=verbose)
        tailer.start()

    try:
        if pause:
            # Per-phase loop with interactive pause between phases
            exec_results = []
            user_stopped = False
            for phase_idx in range(start_idx, end_idx + 1):
                pid = phase_order[phase_idx]
                try:
                    result = execute_phase_group(
                        run_id=run_id,
                        run_dir=run_dir,
                        run_config=run_config,
                        phase_id=pid,
                    )
                except Exception as e:
                    console.print(f"\n[red]Phase {pid} execution error:[/red] {e}")
                    if verbose:
                        import traceback
                        console.print(traceback.format_exc())
                    raise typer.Exit(2)

                exec_results.append(result)

                if not result.ok:
                    console.print(f"\n[red]Phase {pid} FAILED:[/red] {result.error or 'unknown error'}")
                    break

                # Verify this phase immediately
                v_results = verify_phase_range(run_dir, pid, pid, repo_root=repo_root)
                _print_verification_summary(v_results)

                # Pause (unless last phase)
                if phase_idx < end_idx:
                    console.print()
                    try:
                        response = input(
                            f"Phase {pid} done. Enter to continue to "
                            f"{phase_order[phase_idx + 1]}, 'q' to stop: "
                        )
                    except (EOFError, KeyboardInterrupt):
                        response = "q"
                    if response.strip().lower() == "q":
                        console.print("[yellow]Stopped by user.[/yellow]")
                        user_stopped = True
                        break
        else:
            try:
                exec_results = execute_phase_range(
                    run_id=run_id,
                    run_dir=run_dir,
                    run_config=run_config,
                    start_phase=phase_start,
                    end_phase=phase_end,
                )
            except ValueError as e:
                console.print(f"[red]ERROR:[/red] {e}")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"\n[red]Phase execution failed:[/red] {e}")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                raise typer.Exit(2)
            user_stopped = False
    finally:
        if tailer:
            tailer.stop()

    wall_elapsed = time.monotonic() - wall_start

    # Print execution summary
    exec_table = Table(show_header=True, header_style="bold blue", title="Execution")
    exec_table.add_column("Phase")
    exec_table.add_column("Workers")
    exec_table.add_column("Status")
    for er in exec_results:
        status_str = "[green]OK[/green]" if er.ok else f"[red]FAIL[/red] {er.error or ''}"
        exec_table.add_row(er.phase_id, ", ".join(er.workers), status_str)
    console.print(exec_table)
    console.print(f"Total wall time: {wall_elapsed:.1f}s\n")

    exec_ok = all(er.ok for er in exec_results)
    if not exec_ok:
        raise typer.Exit(2)

    if user_stopped:
        # User stopped early — skip post-execution verification for unexecuted phases
        console.print("[yellow]Partial run — skipping remaining verification.[/yellow]")
        raise typer.Exit(0)

    # Post-execution verification
    console.print(f"[blue]Verifying artifacts for {phase_start}..{phase_end}[/blue]\n")
    v_results = verify_phase_range(
        run_dir, phase_start, phase_end, repo_root=repo_root,
    )
    _print_verification_summary(v_results)

    all_ok = all(vr.ok for vr in v_results)
    raise typer.Exit(0 if all_ok else 1)


def _print_verification_summary(
    results: "List",  # List[PhaseVerificationResult] — avoid top-level import
) -> None:
    """Print a rich table summarising phase verification results."""
    table = Table(show_header=True, header_style="bold blue", title="Verification")
    table.add_column("Phase")
    table.add_column("Status")
    table.add_column("Checks")
    table.add_column("Missing")
    table.add_column("Schema Errors")

    for vr in results:
        status_str = "[green]OK[/green]" if vr.ok else "[red]FAIL[/red]"
        table.add_row(
            vr.phase_id,
            status_str,
            str(len(vr.checks)),
            str(len(vr.missing)),
            str(len(vr.schema_errors)),
        )

    console.print(table)

    # Print details for failures
    for vr in results:
        if not vr.ok:
            if vr.missing:
                console.print(f"\n[red]{vr.phase_id} missing artifacts:[/red]")
                for m in vr.missing:
                    console.print(f"  - {m}")
            if vr.schema_errors:
                console.print(f"\n[red]{vr.phase_id} schema errors:[/red]")
                for se in vr.schema_errors:
                    console.print(f"  - {se}")


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


@app.command(name="list")
def list_runs(
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


@app.command()
def monitor(
    run_dir: Path = typer.Option(
        ..., "--run-dir", exists=True, file_okay=False, readable=True,
        help="Run directory to monitor (runs/<run_id>/)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show LLM call events"),
) -> None:
    """Tail events from a run directory in real-time.

    Replays all existing events, then tails for new ones.
    Useful for monitoring a run started in another terminal or for
    inspecting events from a completed run.

    Example:
        launch monitor --run-dir runs/r_20260225T...

    Press Ctrl+C to stop.

    Exit codes:
        0 - Success (stopped by user)
        1 - Invalid run directory
    """
    from launch.monitoring.event_tailer import EventTailer

    run_dir = run_dir.resolve()
    events_path = run_dir / "events.ndjson"

    if not events_path.exists():
        console.print(f"[yellow]WARNING:[/yellow] No events.ndjson found in {run_dir}")
        console.print("The run may not have started yet. Waiting for events...")

    tailer = EventTailer(events_path, console, verbose=verbose)

    # Replay existing events (catch-up display)
    tailer.replay_existing()

    # Tail for new events until Ctrl+C
    console.print("\n[dim]Tailing for new events... (Ctrl+C to stop)[/dim]")
    thread = tailer.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        tailer.stop()
    console.print("\n[dim]Monitoring stopped.[/dim]")


# ---------------------------------------------------------------------------
# Intake commands (TC-2544)
# ---------------------------------------------------------------------------


def _load_intake_config(config_path: Optional[Path]) -> Optional["IntakeConfig"]:
    """Load intake config from explicit path or auto-detect default location.

    Returns None if no config file is found/specified.
    """
    from launch.intake.config_loader import IntakeConfigError, load_intake_config

    if config_path is not None:
        return load_intake_config(config_path)

    # Auto-detect default config
    default = _repo_root() / "configs" / "intake_config.yaml"
    if default.exists():
        return load_intake_config(default)

    return None


@intake_app.command(name="scan")
def intake_scan(
    orgs: Optional[str] = typer.Option(
        None, "--orgs",
        help="Comma-separated list of GitHub organization names to scan. Overrides config file.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print results without persisting state."),
    config: Optional[Path] = typer.Option(
        None, "--config", exists=True, dir_okay=False,
        help="Path to intake config YAML. Auto-detects configs/intake_config.yaml if absent.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Scan GitHub organizations for public repositories.

    Organizations are read from the persistent config file
    (``configs/intake_config.yaml``), or overridden via ``--orgs``.

    All target repos are assumed to be public — no GitHub token is required.
    A token (via ``$GITHUB_TOKEN``) increases the rate limit from 60 to 5000 req/hr.

    Example:
        launch intake scan
        launch intake scan --orgs "aspose-3d-foss,aspose-cells-foss"
        launch intake scan --config path/to/intake_config.yaml --dry-run

    Exit codes:
        0 - Success
        1 - Configuration or API error
    """
    from launch.intake.config_loader import IntakeConfigError, resolve_token
    from launch.intake.org_scanner import ScannerError, scan_orgs

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Load config (if available)
    try:
        intake_cfg = _load_intake_config(config)
    except IntakeConfigError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

    # Determine org list: --orgs flag overrides config file
    if orgs is not None:
        org_list = [o.strip() for o in orgs.split(",") if o.strip()]
    elif intake_cfg is not None:
        org_list = [org.name for org in intake_cfg.organizations]
    else:
        org_list = []

    if not org_list:
        console.print(
            "[red]ERROR:[/red] No organizations specified. "
            "Provide --orgs or create configs/intake_config.yaml."
        )
        raise typer.Exit(1)

    # Resolve token
    if intake_cfg is not None:
        token = resolve_token(intake_cfg.scanner)
        scanner_cfg = intake_cfg.scanner
    else:
        import os
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.info("No GitHub token; using unauthenticated access (60 req/hr)")
        scanner_cfg = None

    state_dir = None if dry_run else (_repo_root() / (intake_cfg.state_dir if intake_cfg else "intake"))

    try:
        kwargs = {}
        if scanner_cfg is not None:
            kwargs.update(
                per_page=scanner_cfg.per_page,
                max_pages=scanner_cfg.max_pages,
                activity_months=scanner_cfg.activity_months,
                rate_limit_delay_s=scanner_cfg.rate_limit_delay_s,
            )
        repos = scan_orgs(
            org_list,
            token=token,
            state_dir=state_dir,
            **kwargs,
        )
    except ScannerError as e:
        console.print(f"[red]ERROR:[/red] Scanner failed: {e}")
        raise typer.Exit(1)

    console.print(f"[green]Scan complete.[/green] Discovered {len(repos)} repos from {len(org_list)} org(s).")
    for repo in repos:
        stars = repo.get("stargazers_count", 0)
        console.print(f"  - {repo['full_name']} ({stars} stars)")


@intake_app.command(name="classify")
def intake_classify(
    repo_url: str = typer.Option(
        ..., "--repo",
        help="GitHub repository URL to classify.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Increase logging verbosity"),
) -> None:
    """Classify a single repository for pipeline eligibility.

    No GitHub token required — all target repos are public.

    Example:
        launch intake classify --repo https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python

    Exit codes:
        0 - Success
        1 - API error
    """
    import os
    import re

    from launch.intake.org_scanner import ScannerError, scan_org
    from launch.intake.repo_classifier import classify_repo

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Parse org and repo from URL
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?", repo_url)
    if not match:
        console.print(f"[red]ERROR:[/red] Invalid GitHub URL: {repo_url}")
        raise typer.Exit(1)

    org_name, repo_name = match.group(1), match.group(2)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.info("No GitHub token; using unauthenticated access (60 req/hr)")

    try:
        repos = scan_org(org_name, token=token, max_pages=5)
    except ScannerError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

    # Find the specific repo
    target = None
    for r in repos:
        if r.get("name", "").lower() == repo_name.lower():
            target = r
            break

    if target is None:
        console.print(f"[yellow]WARNING:[/yellow] Repo '{repo_name}' not found in org '{org_name}' scan results.")
        raise typer.Exit(1)

    result = classify_repo(target)
    color = {"eligible": "green", "needs_review": "yellow", "ineligible": "red"}.get(result.decision, "white")
    console.print(f"[{color}]{result.decision}[/{color}]: {result.full_name}")
    for reason in result.reasons:
        console.print(f"  - {reason}")


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
) -> None:
    """Generate a pilot config YAML for a repository.

    Platform is auto-detected from the repo name and metadata.
    Use ``--platform`` to override.

    No GitHub token required — all target repos are public.

    Example:
        launch intake generate --repo https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python --output configs/pilots/

    Exit codes:
        0 - Success
        1 - Error or duplicate
    """
    import os
    import re

    from launch.intake.config_generator import check_dedup, write_config

    from launch.intake.org_scanner import ScannerError, scan_org

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?", repo_url)
    if not match:
        console.print(f"[red]ERROR:[/red] Invalid GitHub URL: {repo_url}")
        raise typer.Exit(1)

    org_name, repo_name = match.group(1), match.group(2)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.info("No GitHub token; using unauthenticated access (60 req/hr)")

    try:
        repos = scan_org(org_name, token=token, max_pages=5)
    except ScannerError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

    target = None
    for r in repos:
        if r.get("name", "").lower() == repo_name.lower():
            target = r
            break

    if target is None:
        console.print(f"[yellow]WARNING:[/yellow] Repo '{repo_name}' not found.")
        raise typer.Exit(1)

    output_dir = Path(output).resolve() if not Path(output).is_absolute() else Path(output)

    if check_dedup(target, output_dir):
        console.print(f"[yellow]Skipping:[/yellow] Config already exists for {target.get('full_name', repo_url)}")
        return

    path = write_config(target, output_dir, platform=platform)
    if path:
        console.print(f"[green]Generated:[/green] {path}")
    else:
        console.print("[yellow]No config generated (dedup).[/yellow]")


@intake_app.command(name="onboard")
def intake_onboard(
    orgs: Optional[str] = typer.Option(
        None, "--orgs",
        help="Comma-separated list of GitHub organization names. Overrides config file.",
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
    """Scan, classify, and generate pilot configs for all eligible repos.

    Combines scan -> classify -> sort -> batch -> generate into one command.
    Organizations are read from the config file or overridden via --orgs.

    Example:
        launch intake onboard
        launch intake onboard --orgs "aspose-3d-foss,aspose-cells-foss" --dry-run
        launch intake onboard --batch-size 10 --output configs/pilots

    Exit codes:
        0 - Success
        1 - Configuration or API error
    """
    import yaml as _yaml

    from launch.intake.config_loader import IntakeConfigError, resolve_token
    from launch.intake.org_scanner import ScannerError, scan_orgs
    from launch.intake.repo_classifier import ClassifierConfig
    from launch.intake.scheduler import schedule

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Step 1: Load intake config
    try:
        intake_cfg = _load_intake_config(config)
    except IntakeConfigError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(1)

    # Step 2: Determine org list
    if orgs is not None:
        org_list = [o.strip() for o in orgs.split(",") if o.strip()]
    elif intake_cfg is not None:
        org_list = [org.name for org in intake_cfg.organizations]
    else:
        org_list = []

    if not org_list:
        console.print(
            "[red]ERROR:[/red] No organizations specified. "
            "Provide --orgs or create configs/intake_config.yaml."
        )
        raise typer.Exit(1)

    # Step 3: Resolve token
    if intake_cfg is not None:
        token = resolve_token(intake_cfg.scanner)
        scanner_cfg = intake_cfg.scanner
    else:
        import os
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.info("No GitHub token; using unauthenticated access (60 req/hr)")
        scanner_cfg = None

    # Step 4: Scan orgs
    state_dir = None if dry_run else (
        _repo_root() / (intake_cfg.state_dir if intake_cfg else "intake")
    )

    try:
        scan_kwargs: Dict[str, Any] = {}
        if scanner_cfg is not None:
            scan_kwargs.update(
                per_page=scanner_cfg.per_page,
                max_pages=scanner_cfg.max_pages,
                activity_months=scanner_cfg.activity_months,
                rate_limit_delay_s=scanner_cfg.rate_limit_delay_s,
            )
        repos = scan_orgs(
            org_list,
            token=token,
            state_dir=state_dir,
            **scan_kwargs,
        )
    except ScannerError as e:
        console.print(f"[red]ERROR:[/red] Scanner failed: {e}")
        raise typer.Exit(1)

    console.print(f"Scanned {len(org_list)} org(s), discovered {len(repos)} repo(s).")

    if not repos:
        console.print("[yellow]No repos discovered. Nothing to onboard.[/yellow]")
        return

    # Step 5: Build classifier config from intake config overrides
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

    # Step 6: Build org_configs for platform resolution
    org_configs = None
    if intake_cfg is not None:
        org_configs = {org.name: org for org in intake_cfg.organizations}

    # Step 7: Load custom template if provided
    template_dict = None
    if template is not None:
        try:
            template_dict = _yaml.safe_load(template.read_text(encoding="utf-8"))
            if not isinstance(template_dict, dict):
                console.print("[red]ERROR:[/red] Template must be a YAML mapping.")
                raise typer.Exit(1)
        except _yaml.YAMLError as e:
            console.print(f"[red]ERROR:[/red] Invalid template YAML: {e}")
            raise typer.Exit(1)

    # Step 8: Resolve output directory
    output_dir = Path(output).resolve() if not Path(output).is_absolute() else Path(output)

    # Step 9: Effective batch_size (0 = all)
    effective_batch_size = batch_size if batch_size > 0 else len(repos)

    # Step 10: Scheduling params from config
    sort_by = "stars"
    sort_order = "desc"
    if intake_cfg is not None:
        sort_by = intake_cfg.scheduler.sort_by
        sort_order = intake_cfg.scheduler.sort_order

    # Step 11: Schedule
    report = schedule(
        repos,
        output_dir=output_dir,
        batch_size=effective_batch_size,
        sort_by=sort_by,
        sort_order=sort_order,
        dry_run=dry_run,
        classifier_config=classifier_config,
        template=template_dict,
        state_dir=state_dir,
        org_configs=org_configs,
    )

    # Step 12: Print Rich summary
    summary = report["summary"]
    table = Table(show_header=True, header_style="bold blue", title="Onboard Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Total scanned", str(summary["total_scanned"]))
    table.add_row("Eligible", str(summary["eligible"]))
    table.add_row("Needs review", str(summary["needs_review"]))
    table.add_row("Ineligible", str(summary["ineligible"]))
    table.add_row("Skipped (dedup)", str(summary["skipped_dedup"]))
    table.add_row("Processed", str(summary["processed"]))
    console.print(table)

    if report["processed"]:
        proc_table = Table(
            show_header=True, header_style="bold blue", title="Processed Repos",
        )
        proc_table.add_column("Repo")
        proc_table.add_column("Platform")
        proc_table.add_column("Stars", justify="right")
        proc_table.add_column("Action")
        for item in report["processed"]:
            proc_table.add_row(
                item["full_name"],
                item["platform"],
                str(item["stars"]),
                item["action"],
            )
        console.print(proc_table)

    if dry_run:
        console.print("[yellow]Dry-run mode:[/yellow] no config files were written.")
    else:
        console.print(
            f"[green]Success:[/green] {summary['processed']} config(s) generated "
            f"in {output_dir}"
        )


def main() -> None:
    """Main entrypoint for launch CLI."""
    app(prog_name="launch")


if __name__ == "__main__":
    main()
