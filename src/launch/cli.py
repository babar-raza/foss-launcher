"""FOSS Launcher CLI (scaffold).

This repo is primarily a spec pack. The full orchestrator/workers are implemented later
by an implementation agent.

What *is* implemented here:
- config schema validation
- deterministic-ish run directory scaffolding (RUN_DIR layout)

What is *not* implemented here:
- repo ingestion, orchestrator graph execution, writing content, opening PRs

Binding contracts:
- specs/29_project_repo_structure.md
- specs/schemas/run_config.schema.json
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .io.run_config import load_and_validate_run_config
from .io.run_layout import create_run_skeleton
from .util.run_id import make_run_id, stable_config_hash8

app = typer.Typer(add_completion=False)


def _repo_root() -> Path:
    # src/launch/cli.py -> repo root
    return Path(__file__).resolve().parents[2]


@app.command()
def run(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False, readable=True),
    run_dir: Path | None = typer.Option(None, "--run_dir", help="Target RUN_DIR (runs/<run_id>)"),
) -> None:
    """Validate a run_config and scaffold RUN_DIR."""
    repo_root = _repo_root()
    run_config = load_and_validate_run_config(repo_root, config)

    if run_dir is None:
        run_id = make_run_id(
            product_slug=run_config["product_slug"],
            github_ref=run_config["github_ref"],
            site_ref=run_config.get("site_ref", "default_branch"),
            run_config=run_config,
        )
        run_dir = repo_root / "runs" / run_id
    else:
        run_dir = run_dir.resolve()

    run_dir.parent.mkdir(parents=True, exist_ok=True)
    layout = create_run_skeleton(run_dir)

    # Copy the validated config verbatim.
    (layout.run_dir / "run_config.yaml").write_text(config.read_text(encoding="utf-8"), encoding="utf-8")

    # Emit a minimal local event for traceability.
    event = {
        "event_type": "RUN_CREATED",
        "run_id": layout.run_dir.name,
        "product_slug": run_config["product_slug"],
        "config_hash8": stable_config_hash8(run_config),
    }
    (layout.run_dir / "events.ndjson").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    typer.echo(f"RUN_DIR created: {layout.run_dir}")


def main() -> None:
    app(prog_name="launch_run")


if __name__ == "__main__":
    main()
