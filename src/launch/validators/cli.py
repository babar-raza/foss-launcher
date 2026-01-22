"""Validation gate runner (scaffold).

Binding gate contract:
- specs/09_validation_gates.md
- specs/19_toolchain_and_ci.md

This scaffold implementation performs only the parts that can be validated without
the full launcher implementation:
- toolchain.lock.yaml sentinel check (PIN_ME)
- run_config.yaml schema validation
- JSON schema validation for any artifacts present in RUN_DIR/artifacts/

All remaining gates are recorded as NOT_IMPLEMENTED so reviewers can see the gap
explicitly (instead of getting a false pass).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from ..io.atomic import atomic_write_json, atomic_write_text
from ..io.run_config import load_and_validate_run_config
from ..io.run_layout import required_paths
from ..io.schema_validation import validate_json_file
from ..io.toolchain import load_toolchain_lock
from ..util.errors import ConfigError, ToolchainError

app = typer.Typer(add_completion=False)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _infer_schema_path(repo_root: Path, artifact_path: Path) -> Path:
    schemas_dir = repo_root / "specs" / "schemas"
    schema_name = artifact_path.name.replace(".json", ".schema.json")
    return schemas_dir / schema_name


def _issue(
    *,
    issue_id: str,
    gate: str,
    severity: str,
    message: str,
    status: str = "OPEN",
    files: Optional[List[str]] = None,
    location: Optional[Dict[str, Any]] = None,
    suggested_fix: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "issue_id": issue_id,
        "gate": gate,
        "severity": severity,
        "message": message,
        "status": status,
    }
    if files:
        out["files"] = files
    if location:
        out["location"] = location
    if suggested_fix:
        out["suggested_fix"] = suggested_fix
    return out


@app.command()
def validate(
    run_dir: Path = typer.Option(..., "--run_dir", exists=True, file_okay=False, readable=True),
    profile: str = typer.Option("ci", "--profile", help="ci|prod"),
) -> None:
    repo_root = _repo_root()
    run_dir = run_dir.resolve()

    issues: List[Dict[str, Any]] = []
    gates: List[Dict[str, Any]] = []

    # Gate 0: required paths exist
    missing = [str(p.relative_to(run_dir)) for p in required_paths(run_dir) if not p.exists()]
    run_layout_log = run_dir / "logs" / "gate_run_layout.log"
    if missing:
        issues.append(
            _issue(
                issue_id="iss_missing_paths",
                gate="run_layout",
                severity="blocker",
                message="RUN_DIR missing required paths",
                suggested_fix="Recreate RUN_DIR using `launch_run --config ...` (scaffold) or the full launcher.",
            )
        )
        gates.append({"name": "run_layout", "ok": False, "log_path": str(run_layout_log)})
        atomic_write_text(run_layout_log, "Missing required paths:\n" + "\n".join(missing) + "\n")
    else:
        gates.append({"name": "run_layout", "ok": True, "log_path": str(run_layout_log)})
        atomic_write_text(run_layout_log, "OK\n")

    # Gate 1: toolchain lock sentinel check
    toolchain_log = run_dir / "logs" / "gate_toolchain_lock.log"
    try:
        load_toolchain_lock(repo_root)
        gates.append({"name": "toolchain_lock", "ok": True, "log_path": str(toolchain_log)})
        atomic_write_text(toolchain_log, "OK\n")
    except ToolchainError as e:
        issues.append(
            _issue(
                issue_id="iss_toolchain_lock",
                gate="toolchain_lock",
                severity="blocker",
                message=str(e),
                suggested_fix="Pin all tool versions in config/toolchain.lock.yaml (no PIN_ME).",
            )
        )
        gates.append({"name": "toolchain_lock", "ok": False, "log_path": str(toolchain_log)})
        atomic_write_text(toolchain_log, f"ERROR: {e}\n")

    # Gate 2: run_config schema validation
    run_cfg_log = run_dir / "logs" / "gate_run_config_schema.log"
    try:
        load_and_validate_run_config(repo_root, run_dir / "run_config.yaml")
        gates.append({"name": "run_config_schema", "ok": True, "log_path": str(run_cfg_log)})
        atomic_write_text(run_cfg_log, "OK\n")
    except ConfigError as e:
        issues.append(
            _issue(
                issue_id="iss_run_config",
                gate="run_config_schema",
                severity="blocker",
                message=str(e),
                files=[str(run_dir / "run_config.yaml")],
                suggested_fix="Fix run_config.yaml to conform to specs/schemas/run_config.schema.json.",
            )
        )
        gates.append({"name": "run_config_schema", "ok": False, "log_path": str(run_cfg_log)})
        atomic_write_text(run_cfg_log, f"ERROR: {e}\n")

    # Gate 3: artifact schema validation for any present JSON artifacts
    artifacts_dir = run_dir / "artifacts"
    schema_log = run_dir / "logs" / "gate_schema_validation.log"

    artifacts = sorted(p for p in artifacts_dir.glob("*.json") if p.is_file())
    artifact_ok = True
    errors: List[str] = []

    for artifact in artifacts:
        schema_path = _infer_schema_path(repo_root, artifact)
        if not schema_path.exists():
            artifact_ok = False
            errors.append(f"No schema for {artifact.name} (expected {schema_path.name})")
            continue
        try:
            validate_json_file(artifact, schema_path)
        except Exception as e:
            artifact_ok = False
            errors.append(f"{artifact.name}: {e}")

    if errors:
        issues.append(
            _issue(
                issue_id="iss_artifact_schemas",
                gate="schema_validation",
                severity="blocker",
                message="One or more artifacts failed schema validation",
                files=[str(p) for p in artifacts],
                suggested_fix="Regenerate artifacts using the full launcher; ensure each artifact matches its schema.",
            )
        )

    gates.append({"name": "schema_validation", "ok": artifact_ok, "log_path": str(schema_log)})
    atomic_write_text(schema_log, "\n".join(["OK" if artifact_ok else "ERROR"] + errors) + "\n")

    # Remaining gates are not implemented in the scaffold.
    not_impl = [
        "frontmatter",
        "markdownlint",
        "template_token_lint",
        "hugo_config",
        "hugo_build",
        "internal_links",
        "external_links",
        "snippets",
        "truthlock",
    ]
    for gate_name in not_impl:
        sev = "blocker" if profile == "prod" else "warn"
        issues.append(
            _issue(
                issue_id=f"iss_not_implemented_{gate_name}",
                gate=gate_name,
                severity=sev,
                message="Gate not implemented in scaffold",
                suggested_fix="Implement this gate per specs/19_toolchain_and_ci.md.",
            )
        )
        gate_log = run_dir / "logs" / f"gate_{gate_name}.log"
        gates.append({"name": gate_name, "ok": False, "log_path": str(gate_log)})
        atomic_write_text(gate_log, "NOT_IMPLEMENTED\n")

    ok = all(g["ok"] for g in gates)
    report = {"schema_version": "1.0", "ok": ok, "gates": gates, "issues": issues}

    atomic_write_json(artifacts_dir / "validation_report.json", report)

    if ok:
        typer.echo("Validation OK")
        raise typer.Exit(0)

    typer.echo("Validation FAILED")
    raise typer.Exit(2)


def main() -> None:
    app(prog_name="launch_validate")


if __name__ == "__main__":
    main()
