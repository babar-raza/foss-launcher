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

# No typer app - we'll use a single function as the main entrypoint


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
    error_code: Optional[str] = None,
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
    if error_code:
        out["error_code"] = error_code
    if files:
        out["files"] = files
    if location:
        out["location"] = location
    if suggested_fix:
        out["suggested_fix"] = suggested_fix
    return out


def validate(
    run_dir: Path,
    profile: str = "local",
) -> None:
    import os

    repo_root = _repo_root()
    run_dir = run_dir.resolve()

    # Resolve profile per specs/09_validation_gates.md precedence:
    # 1. run_config.validation_profile
    # 2. --profile CLI argument
    # 3. LAUNCH_VALIDATION_PROFILE env var
    # 4. default "local"
    resolved_profile = profile  # Start with CLI arg (already defaulted to "local")

    # Check env var (lower precedence than CLI arg)
    env_profile = os.environ.get("LAUNCH_VALIDATION_PROFILE")
    if env_profile and profile == "local":  # Only use env if CLI was defaulted
        resolved_profile = env_profile

    # Check run_config (highest precedence)
    run_config_path = run_dir / "run_config.yaml"
    if run_config_path.exists():
        try:
            import yaml
            run_config = yaml.safe_load(run_config_path.read_text(encoding="utf-8"))
            if "validation_profile" in run_config:
                resolved_profile = run_config["validation_profile"]
        except Exception:
            pass  # If run_config is malformed, fall back to CLI/env/default

    # Validate resolved profile
    if resolved_profile not in ("local", "ci", "prod"):
        typer.echo(f"ERROR: Invalid profile '{resolved_profile}'. Must be: local, ci, or prod")
        raise typer.Exit(1)

    profile = resolved_profile

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
                error_code="GATE_RUN_LAYOUT_MISSING_PATHS",
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
                error_code="GATE_TOOLCHAIN_LOCK_FAILED",
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
                error_code="SCHEMA_VALIDATION_FAILED",
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
                error_code="SCHEMA_VALIDATION_FAILED",
                message="One or more artifacts failed schema validation",
                files=[str(p) for p in artifacts],
                suggested_fix="Regenerate artifacts using the full launcher; ensure each artifact matches its schema.",
            )
        )

    gates.append({"name": "schema_validation", "ok": artifact_ok, "log_path": str(schema_log)})
    atomic_write_text(schema_log, "\n".join(["OK" if artifact_ok else "ERROR"] + errors) + "\n")

    # Remaining gates are not implemented in the scaffold.
    # Per Guarantee E (no false passes), these gates MUST report as FAILED (ok=False)
    # in production profile to prevent misleading results.
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
        # In prod profile, NOT_IMPLEMENTED gates are BLOCKERS (fail the run)
        # In non-prod profiles, they are warnings (don't fail but are visible)
        sev = "blocker" if profile == "prod" else "warn"
        issues.append(
            _issue(
                issue_id=f"iss_not_implemented_{gate_name}",
                gate=gate_name,
                severity=sev,
                error_code=f"GATE_NOT_IMPLEMENTED" if sev == "blocker" else None,
                message=f"Gate not implemented (no false pass: marked as FAILED per Guarantee E)",
                suggested_fix="Implement this gate per specs/19_toolchain_and_ci.md or accept blocker in prod profile.",
            )
        )
        gate_log = run_dir / "logs" / f"gate_{gate_name}.log"
        # Mark as failed (ok=False) to prevent false passes
        gates.append({"name": gate_name, "ok": False, "log_path": str(gate_log)})
        atomic_write_text(
            gate_log,
            f"NOT_IMPLEMENTED\n\nThis gate is not yet implemented.\n"
            f"Per Guarantee E (specs/34_strict_compliance_guarantees.md),\n"
            f"production code MUST NOT produce false passes.\n\n"
            f"This gate is marked as FAILED until fully implemented.\n"
        )

    ok = all(g["ok"] for g in gates)
    report = {
        "schema_version": "1.0",
        "ok": ok,
        "profile": profile,
        "gates": gates,
        "issues": issues,
    }

    atomic_write_json(artifacts_dir / "validation_report.json", report)

    if ok:
        typer.echo("Validation OK")
        raise typer.Exit(0)

    typer.echo("Validation FAILED")
    raise typer.Exit(2)


def main() -> None:
    """Main entrypoint for launch_validate CLI.

    Canonical interface per specs/19_toolchain_and_ci.md:
        launch_validate --run_dir runs/<run_id> --profile <local|ci|prod>
    """
    typer.run(validate)


if __name__ == "__main__":
    main()
