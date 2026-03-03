"""Validation gate runner — canonical engine delegation.

TC-3616: Routes ``launch validate`` through the canonical
``validation_engine.run_gates()`` (50-gate declarative registry) so that the
CLI entrypoint and the W9 pipeline produce the same ``validation_report.json``
schema from the same code path.

Binding specs:
- specs/29_project_repo_structure.md §Binding-rules Rule 3 (no parallel
  implementations: MCP server and CLI MUST call the same internal services)
- specs/09_validation_gates.md (gate contract and profile semantics)
- specs/34_strict_compliance_guarantees.md §Guarantee-E (no false passes)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict

import typer

from ..io.atomic import atomic_write_json
from ..util.path_validation import PathValidationError, validate_run_dir_under_runs


def validate(
    run_dir: Path,
    profile: str = "local",
) -> None:
    """Run all validation gates on *run_dir* using the canonical engine.

    Profile resolution order (specs/09 §Profile):
      1. ``run_config.yaml`` → ``validation_profile`` field (highest precedence)
      2. ``--profile`` CLI argument
      3. ``LAUNCH_VALIDATION_PROFILE`` environment variable
      4. Hardcoded default: ``"local"``

    Exit codes:
      0  — all gates ok
      1  — bad arguments / run_dir not found
      2  — one or more gates failed
    """
    import os

    import yaml

    try:
        run_dir = validate_run_dir_under_runs(run_dir)
    except PathValidationError as e:
        typer.echo(f"ERROR: {e}")
        raise typer.Exit(1)

    # ── Profile resolution ────────────────────────────────────────────────
    resolved_profile = profile  # start with CLI arg (defaulted to "local")

    env_profile = os.environ.get("LAUNCH_VALIDATION_PROFILE")
    if env_profile and profile == "local":
        resolved_profile = env_profile

    # Load run_config; fall back to empty dict when absent or malformed.
    # run_config is passed to the engine for gates that need it (product_facts,
    # W4/W6 gate context, etc.).  Missing keys are handled gracefully by
    # individual gates.
    run_config: Dict[str, Any] = {}
    run_config_path = run_dir / "run_config.yaml"
    if run_config_path.exists():
        try:
            loaded = yaml.safe_load(run_config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                run_config = loaded
                # run_config.validation_profile has highest precedence
                if "validation_profile" in run_config:
                    resolved_profile = str(run_config["validation_profile"])
        except Exception:
            pass  # malformed run_config — engine gates will surface the error

    if resolved_profile not in ("local", "ci", "prod", "pilot"):
        typer.echo(
            f"ERROR: Invalid profile '{resolved_profile}'. Must be: local, ci, prod, or pilot"
        )
        raise typer.Exit(1)

    # ── Canonical engine delegation (TC-3616) ────────────────────────────
    # run_gates() iterates all 50 gates in gates_registry.yaml order, handles
    # graceful_artifact_skip for absent artifacts, and collects results in the
    # same format as execute_validator() in w9_validator/worker.py.
    from ..validation_engine import run_gates

    gate_results, all_issues = run_gates(run_dir, run_config, resolved_profile)

    ok = all(g.get("ok", False) for g in gate_results)

    # Build report identical in schema to W9's validation_report.json.
    # sort_keys=True guarantees deterministic content_hash across runs.
    _hash_input = json.dumps(
        {"gates": gate_results, "issues": all_issues}, sort_keys=True
    )
    report: Dict[str, Any] = {
        "schema_version": "1.0",
        "ok": ok,
        "profile": resolved_profile,
        "gates": gate_results,
        "issues": all_issues,
        "generation_id": str(uuid.uuid4()),
        "content_hash": hashlib.sha256(_hash_input.encode()).hexdigest(),
    }

    # ── Write canonical path ─────────────────────────────────────────────
    # TC-3580 previously wrote to validation_report.site.json to avoid
    # clobbering W9's report.  TC-3616 supersedes that: both CLI and W9 now
    # produce the same 41-gate canonical report at the same path.
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(artifacts_dir / "validation_report.json", report)

    if ok:
        typer.echo("Validation OK")
        raise typer.Exit(0)

    typer.echo("Validation FAILED")
    raise typer.Exit(2)


def main() -> None:
    """Main entrypoint for ``launch_validate`` CLI.

    Canonical interface per specs/19_toolchain_and_ci.md:
        launch_validate --run_dir runs/<run_id> --profile <local|ci|prod>
    """
    typer.run(validate)


if __name__ == "__main__":
    main()
