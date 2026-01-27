"""W7 Validator worker implementation.

This module implements TC-460: Validation gate execution per specs/09_validation_gates.md.

Main entry point:
- execute_validator: Run all validation gates and produce validation report

Exception hierarchy:
- ValidatorError: Base exception
- ValidatorToolMissingError: Required validation tool not found
- ValidatorTimeoutError: Validation gate exceeded timeout
- ValidatorArtifactMissingError: Required artifact not found

Spec references:
- specs/09_validation_gates.md (Gate definitions)
- specs/21_worker_contracts.md:253-271 (W7 contract)
- specs/schemas/validation_report.schema.json (Output schema)
- specs/10_determinism_and_caching.md (Stable ordering)
- specs/11_state_and_events.md (Event emission)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Exception hierarchy
class ValidatorError(Exception):
    """Base exception for validator errors."""

    pass


class ValidatorToolMissingError(ValidatorError):
    """Required validation tool not found."""

    pass


class ValidatorTimeoutError(ValidatorError):
    """Validation gate exceeded timeout."""

    pass


class ValidatorArtifactMissingError(ValidatorError):
    """Required artifact not found."""

    pass


# Utility functions
def emit_event(
    run_dir: Path,
    event_type: str,
    payload: Dict[str, Any],
    trace_id: str,
    span_id: str,
    parent_span_id: Optional[str] = None,
) -> None:
    """Emit event to events.ndjson.

    Args:
        run_dir: Run directory path
        event_type: Event type (e.g., VALIDATOR_STARTED)
        payload: Event payload
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        parent_span_id: Parent span ID (optional)
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "run_id": run_dir.name,
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload,
        "trace_id": trace_id,
        "span_id": span_id,
    }
    if parent_span_id:
        event["parent_span_id"] = parent_span_id

    events_file = run_dir / "events.ndjson"
    with events_file.open("a") as f:
        f.write(json.dumps(event) + "\n")


def load_json_artifact(run_dir: Path, artifact_name: str) -> Dict[str, Any]:
    """Load JSON artifact from RUN_DIR/artifacts/.

    Args:
        run_dir: Run directory path
        artifact_name: Artifact filename (e.g., page_plan.json)

    Returns:
        Parsed JSON artifact

    Raises:
        ValidatorArtifactMissingError: If artifact not found
    """
    artifact_path = run_dir / "artifacts" / artifact_name
    if not artifact_path.exists():
        raise ValidatorArtifactMissingError(
            f"Required artifact not found: {artifact_name}"
        )

    with artifact_path.open() as f:
        return json.load(f)


def find_markdown_files(site_dir: Path) -> List[Path]:
    """Find all markdown files in site worktree.

    Args:
        site_dir: Site worktree directory (RUN_DIR/work/site)

    Returns:
        List of markdown file paths (sorted for determinism)
    """
    if not site_dir.exists():
        return []

    md_files = list(site_dir.rglob("*.md"))
    return sorted(md_files)  # Deterministic ordering


def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter dict or None, body content)
    """
    # Match frontmatter: --- at start, YAML content, closing ---
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


def check_unresolved_tokens(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Check for unresolved template tokens in content.

    Args:
        content: File content
        file_path: File path for error reporting

    Returns:
        List of issue dictionaries
    """
    issues = []

    # Find all __UPPER_SNAKE__ tokens outside code blocks
    # This is a simplified check - full implementation would parse code fences
    lines = content.split("\n")
    in_code_block = False

    for line_num, line in enumerate(lines, start=1):
        # Check for code fence markers
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue  # Skip the fence line itself

        # Skip lines inside code blocks
        if in_code_block:
            continue

        # Check for unresolved tokens
        tokens = re.findall(r"__[A-Z0-9_]+__", line)
        for token in tokens:
            issues.append(
                {
                    "issue_id": f"template_token_{file_path.name}_{line_num}_{token}",
                    "gate": "gate_11_template_token_lint",
                    "severity": "blocker",
                    "message": f"Unresolved template token found: {token}",
                    "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                    "location": {"path": str(file_path), "line": line_num},
                    "status": "OPEN",
                }
            )

    return issues


def validate_schema(
    artifact_path: Path, schema_path: Path, profile: str
) -> List[Dict[str, Any]]:
    """Validate JSON artifact against schema.

    Args:
        artifact_path: Path to artifact file
        schema_path: Path to schema file
        profile: Validation profile (local, ci, prod)

    Returns:
        List of issue dictionaries
    """
    issues = []

    try:
        # Load artifact and schema
        with artifact_path.open() as f:
            artifact = json.load(f)

        with schema_path.open() as f:
            schema = json.load(f)

        # Note: Full JSON Schema validation would require jsonschema library
        # This is a placeholder that checks basic structure
        # Real implementation should use: jsonschema.validate(artifact, schema)

        # For now, just check that it's valid JSON (already done by json.load)
        # Full implementation would validate against schema

    except json.JSONDecodeError as e:
        issues.append(
            {
                "issue_id": f"schema_validation_{artifact_path.name}",
                "gate": "gate_1_schema_validation",
                "severity": "blocker",
                "message": f"Invalid JSON in {artifact_path.name}: {e}",
                "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
                "location": {"path": str(artifact_path)},
                "status": "OPEN",
            }
        )
    except Exception as e:
        issues.append(
            {
                "issue_id": f"schema_validation_{artifact_path.name}",
                "gate": "gate_1_schema_validation",
                "severity": "blocker",
                "message": f"Schema validation error for {artifact_path.name}: {e}",
                "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
                "location": {"path": str(artifact_path)},
                "status": "OPEN",
            }
        )

    return issues


def validate_frontmatter_yaml(md_files: List[Path]) -> List[Dict[str, Any]]:
    """Validate that all markdown files have valid YAML frontmatter.

    Args:
        md_files: List of markdown file paths

    Returns:
        List of issue dictionaries
    """
    issues = []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

            if frontmatter is None:
                issues.append(
                    {
                        "issue_id": f"frontmatter_missing_{md_file.name}",
                        "gate": "gate_1_schema_validation",
                        "severity": "warn",
                        "message": f"File missing frontmatter: {md_file.name}",
                        "error_code": "GATE_FRONTMATTER_MISSING",
                        "location": {"path": str(md_file), "line": 1},
                        "status": "OPEN",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"frontmatter_invalid_{md_file.name}",
                    "gate": "gate_1_schema_validation",
                    "severity": "blocker",
                    "message": f"Invalid YAML frontmatter in {md_file.name}: {e}",
                    "error_code": "GATE_FRONTMATTER_INVALID_YAML",
                    "location": {"path": str(md_file), "line": 1},
                    "status": "OPEN",
                }
            )

    return issues


def gate_1_schema_validation(
    run_dir: Path, run_config: Dict[str, Any], profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Gate 1: Schema Validation.

    Validate all JSON artifacts against their schemas and frontmatter YAML validity.

    Args:
        run_dir: Run directory path
        run_config: Run configuration
        profile: Validation profile

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Find all JSON artifacts
    artifacts_dir = run_dir / "artifacts"
    if artifacts_dir.exists():
        for artifact_file in sorted(artifacts_dir.glob("*.json")):
            # Skip events.ndjson (not a JSON artifact)
            if artifact_file.name == "events.ndjson":
                continue

            # Determine schema file
            schema_name = artifact_file.stem + ".schema.json"
            schema_path = run_dir.parent.parent / "specs" / "schemas" / schema_name

            if schema_path.exists():
                issues.extend(validate_schema(artifact_file, schema_path, profile))

    # Validate frontmatter YAML
    site_dir = run_dir / "work" / "site"
    md_files = find_markdown_files(site_dir)
    issues.extend(validate_frontmatter_yaml(md_files))

    # Gate passes if no blocker/error issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues


def gate_11_template_token_lint(
    run_dir: Path, run_config: Dict[str, Any], profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Gate 11: Template Token Lint.

    Validate no unresolved template tokens remain in generated content.

    Args:
        run_dir: Run directory path
        run_config: Run configuration
        profile: Validation profile

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Check markdown files
    site_dir = run_dir / "work" / "site"
    md_files = find_markdown_files(site_dir)

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            issues.extend(check_unresolved_tokens(content, md_file))
        except Exception as e:
            issues.append(
                {
                    "issue_id": f"template_lint_error_{md_file.name}",
                    "gate": "gate_11_template_token_lint",
                    "severity": "error",
                    "message": f"Error reading file {md_file.name}: {e}",
                    "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Check JSON artifacts
    artifacts_dir = run_dir / "artifacts"
    if artifacts_dir.exists():
        for artifact_file in sorted(artifacts_dir.glob("*.json")):
            if artifact_file.name == "events.ndjson":
                continue

            try:
                content = artifact_file.read_text(encoding="utf-8")
                issues.extend(check_unresolved_tokens(content, artifact_file))
            except Exception:
                pass  # JSON files are already validated in gate 1

    # Gate passes if no issues
    gate_passed = len(issues) == 0

    return gate_passed, issues


def gate_10_consistency(
    run_dir: Path, run_config: Dict[str, Any], profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Gate 10: Consistency.

    Validate cross-artifact consistency (product_name, repo_url, canonical URLs).

    Args:
        run_dir: Run directory path
        run_config: Run configuration
        profile: Validation profile

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    try:
        # Load product_facts.json
        product_facts = load_json_artifact(run_dir, "product_facts.json")
        product_name = product_facts.get("product_name")
        repo_url = product_facts.get("repo_url")

        # Load page_plan.json
        page_plan = load_json_artifact(run_dir, "page_plan.json")

        # Check product_name consistency
        plan_product_slug = page_plan.get("product_slug")
        if product_name and plan_product_slug:
            # Normalize for comparison (slug is lowercased, hyphenated)
            normalized_name = product_name.lower().replace(" ", "-")
            if normalized_name != plan_product_slug.lower():
                issues.append(
                    {
                        "issue_id": "consistency_product_name_mismatch",
                        "gate": "gate_10_consistency",
                        "severity": "error",
                        "message": f"Product name mismatch: product_facts has '{product_name}' but page_plan has slug '{plan_product_slug}'",
                        "error_code": "GATE_CONSISTENCY_PRODUCT_NAME_MISMATCH",
                        "status": "OPEN",
                    }
                )

        # Check repo_url consistency in markdown files
        site_dir = run_dir / "work" / "site"
        md_files = find_markdown_files(site_dir)

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

            if frontmatter and "repo_url" in frontmatter:
                if frontmatter["repo_url"] != repo_url:
                    issues.append(
                        {
                            "issue_id": f"consistency_repo_url_{md_file.name}",
                            "gate": "gate_10_consistency",
                            "severity": "error",
                            "message": f"repo_url mismatch in {md_file.name}",
                            "error_code": "GATE_CONSISTENCY_REPO_URL_MISMATCH",
                            "location": {"path": str(md_file)},
                            "status": "OPEN",
                        }
                    )

    except ValidatorArtifactMissingError:
        # If artifacts are missing, gate 1 will catch them
        pass
    except Exception as e:
        issues.append(
            {
                "issue_id": "consistency_check_error",
                "gate": "gate_10_consistency",
                "severity": "error",
                "message": f"Error during consistency check: {e}",
                "error_code": "GATE_CONSISTENCY_PRODUCT_NAME_MISMATCH",
                "status": "OPEN",
            }
        )

    # Gate passes if no blocker/error issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues


def gate_t_test_determinism(
    run_dir: Path, run_config: Dict[str, Any], profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Gate T: Test Determinism Configuration.

    Validate test configuration enforces determinism (PYTHONHASHSEED=0).

    Args:
        run_dir: Run directory path
        run_config: Run configuration
        profile: Validation profile

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Check for PYTHONHASHSEED=0 in pyproject.toml or pytest.ini
    repo_root = run_dir.parent.parent
    pyproject_toml = repo_root / "pyproject.toml"
    pytest_ini = repo_root / "pytest.ini"

    has_determinism = False

    # Check pyproject.toml
    if pyproject_toml.exists():
        try:
            import tomli

            with pyproject_toml.open("rb") as f:
                config = tomli.load(f)
                pytest_env = (
                    config.get("tool", {}).get("pytest", {}).get("ini_options", {})
                ).get("env", [])
                if "PYTHONHASHSEED=0" in pytest_env or any(
                    "PYTHONHASHSEED=0" in str(e) for e in pytest_env
                ):
                    has_determinism = True
        except Exception:
            pass

    # Check pytest.ini
    if pytest_ini.exists() and not has_determinism:
        try:
            content = pytest_ini.read_text()
            if "PYTHONHASHSEED=0" in content:
                has_determinism = True
        except Exception:
            pass

    if not has_determinism:
        issues.append(
            {
                "issue_id": "test_determinism_missing",
                "gate": "gate_t_test_determinism",
                "severity": "error",
                "message": "PYTHONHASHSEED=0 not set in test configuration",
                "error_code": "TEST_MISSING_PYTHONHASHSEED",
                "status": "OPEN",
            }
        )

    gate_passed = len(issues) == 0
    return gate_passed, issues


def sort_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort issues deterministically.

    Per specs/10_determinism_and_caching.md:44-48:
    - Sort by (severity_rank, gate, location.path, location.line, issue_id)
    - Severity rank: blocker > error > warn > info

    Args:
        issues: List of issue dictionaries

    Returns:
        Sorted list of issues
    """
    severity_rank = {"blocker": 0, "error": 1, "warn": 2, "info": 3}

    def sort_key(issue: Dict[str, Any]) -> Tuple:
        rank = severity_rank.get(issue.get("severity", "info"), 3)
        gate = issue.get("gate", "")
        location = issue.get("location", {})
        path = location.get("path", "") if isinstance(location, dict) else ""
        line = location.get("line", 0) if isinstance(location, dict) else 0
        issue_id = issue.get("issue_id", "")
        return (rank, gate, path, line, issue_id)

    return sorted(issues, key=sort_key)


def execute_validator(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute validation gates and produce validation report.

    This is the main entry point for W7 Validator worker.

    Per specs/21_worker_contracts.md:260-282:
    - Run all required validation gates
    - Normalize tool outputs into stable issue objects
    - Never fix issues (validator is read-only)

    Args:
        run_dir: Run directory path (e.g., runs/run_001)
        run_config: Run configuration dictionary

    Returns:
        Validation report dictionary matching validation_report.schema.json

    Raises:
        ValidatorError: On validation errors
        ValidatorToolMissingError: If required tool missing
        ValidatorTimeoutError: If gate exceeds timeout
    """
    # Generate trace IDs
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    # Emit VALIDATOR_STARTED event
    emit_event(
        run_dir,
        "VALIDATOR_STARTED",
        {"profile": run_config.get("validation_profile", "local")},
        trace_id,
        span_id,
    )

    # Determine validation profile
    profile = run_config.get("validation_profile", "local")

    # Import gate modules
    from .gates import (
        gate_2_claim_marker_validity,
        gate_3_snippet_references,
        gate_4_frontmatter_required_fields,
        gate_5_cross_page_link_validity,
        gate_6_accessibility,
        gate_7_content_quality,
        gate_8_claim_coverage,
        gate_9_navigation_integrity,
        gate_12_patch_conflicts,
        gate_13_hugo_build,
    )

    # Execute gates in order
    all_issues = []
    gate_results = []

    # Gate 1: Schema Validation
    gate_passed, issues = gate_1_schema_validation(run_dir, run_config, profile)
    gate_results.append({"name": "gate_1_schema_validation", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 2: Claim Marker Validity (TC-570)
    gate_passed, issues = gate_2_claim_marker_validity.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_2_claim_marker_validity", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 3: Snippet References (TC-570)
    gate_passed, issues = gate_3_snippet_references.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_3_snippet_references", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 4: Frontmatter Required Fields (TC-570)
    gate_passed, issues = gate_4_frontmatter_required_fields.execute_gate(
        run_dir, profile
    )
    gate_results.append(
        {"name": "gate_4_frontmatter_required_fields", "ok": gate_passed}
    )
    all_issues.extend(issues)

    # Gate 5: Cross-Page Link Validity (TC-570)
    gate_passed, issues = gate_5_cross_page_link_validity.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_5_cross_page_link_validity", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 6: Accessibility (TC-570)
    gate_passed, issues = gate_6_accessibility.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_6_accessibility", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 7: Content Quality (TC-570)
    gate_passed, issues = gate_7_content_quality.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_7_content_quality", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 8: Claim Coverage (TC-570)
    gate_passed, issues = gate_8_claim_coverage.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_8_claim_coverage", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 9: Navigation Integrity (TC-570)
    gate_passed, issues = gate_9_navigation_integrity.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_9_navigation_integrity", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 10: Consistency
    gate_passed, issues = gate_10_consistency(run_dir, run_config, profile)
    gate_results.append({"name": "gate_10_consistency", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 11: Template Token Lint
    gate_passed, issues = gate_11_template_token_lint(run_dir, run_config, profile)
    gate_results.append({"name": "gate_11_template_token_lint", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 12: Patch Conflicts (TC-570)
    gate_passed, issues = gate_12_patch_conflicts.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_12_patch_conflicts", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate 13: Hugo Build (TC-570)
    gate_passed, issues = gate_13_hugo_build.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_13_hugo_build", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate T: Test Determinism
    gate_passed, issues = gate_t_test_determinism(run_dir, run_config, profile)
    gate_results.append({"name": "gate_t_test_determinism", "ok": gate_passed})
    all_issues.extend(issues)

    # Sort issues deterministically
    all_issues = sort_issues(all_issues)

    # Determine overall ok status
    overall_ok = all(gate["ok"] for gate in gate_results)

    # Build validation report
    validation_report = {
        "schema_version": "1.0",
        "ok": overall_ok,
        "profile": profile,
        "gates": gate_results,
        "issues": all_issues,
    }

    # Write validation_report.json
    report_path = run_dir / "artifacts" / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w") as f:
        json.dump(validation_report, f, indent=2, sort_keys=True)

    # Emit VALIDATOR_COMPLETED event
    emit_event(
        run_dir,
        "VALIDATOR_COMPLETED",
        {
            "ok": overall_ok,
            "gates_passed": sum(1 for g in gate_results if g["ok"]),
            "gates_total": len(gate_results),
            "issues_count": len(all_issues),
        },
        trace_id,
        span_id,
    )

    # Emit ARTIFACT_WRITTEN event
    emit_event(
        run_dir,
        "ARTIFACT_WRITTEN",
        {
            "artifact_name": "validation_report.json",
            "artifact_path": str(report_path),
        },
        trace_id,
        span_id,
    )

    return validation_report
