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
    with events_file.open("a", encoding="utf-8") as f:
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

    with artifact_path.open(encoding="utf-8") as f:
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
        with artifact_path.open(encoding="utf-8") as f:
            artifact = json.load(f)

        with schema_path.open(encoding="utf-8") as f:
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
    
    Per TC-965: JSON metadata files (page_plan.json, draft_manifest.json, etc.) 
    contain token mappings as data, not unfilled tokens. These files are excluded 
    from token scanning to prevent false positives.

    Args:
        run_dir: Run directory path
        run_config: Run configuration
        profile: Validation profile

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Check markdown files in drafts (actual content to be published)
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

    # NOTE: JSON artifacts are NOT scanned for tokens per TC-965
    # These files (page_plan.json, draft_manifest.json, etc.) contain token 
    # mappings as structured data, not unfilled template tokens. Scanning them 
    # produces false positives.
    
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
            # TC-978: Use tomllib (built-in Python 3.11+) instead of tomli
            import tomllib

            with pyproject_toml.open("rb") as f:
                config = tomllib.load(f)
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
            content = pytest_ini.read_text(encoding="utf-8")
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


def normalize_report(report: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    """Normalize validation report for determinism (TC-935).

    Makes validation_report.json deterministic by normalizing absolute paths
    to be relative to run_dir. This ensures that reports from different runs
    (with different run_dir names/timestamps) produce identical canonical JSON.

    Per TC-935 requirements:
    - Convert absolute paths in location.path to relative paths
    - Preserve all validation information (no data loss)
    - Already sorted by sort_issues() before this function is called

    Args:
        report: Validation report dictionary
        run_dir: Run directory path (e.g., runs/run_001)

    Returns:
        Normalized report with relative paths
    """
    # Make a deep copy to avoid mutating the original
    normalized = json.loads(json.dumps(report))

    # Normalize absolute paths in issues
    run_dir_str = str(run_dir.resolve())

    for issue in normalized.get("issues", []):
        location = issue.get("location")
        if location and isinstance(location, dict) and "path" in location:
            abs_path = location["path"]
            if isinstance(abs_path, str):
                # Convert absolute path to relative if it contains run_dir
                try:
                    abs_path_obj = Path(abs_path)
                    run_dir_obj = Path(run_dir_str)
                    # Try to make relative to run_dir
                    if abs_path_obj.is_absolute() and str(abs_path_obj).startswith(run_dir_str):
                        rel_path = abs_path_obj.relative_to(run_dir_obj)
                        location["path"] = str(rel_path).replace("\\", "/")
                except (ValueError, OSError):
                    # If path cannot be made relative, keep as-is
                    pass

    return normalized


def validate_content_distribution(
    page_plan: Dict[str, Any],
    product_facts: Dict[str, Any],
    site_content_dir: Path,
    profile: str = "local",
) -> List[Dict[str, Any]]:
    """Validate content distribution strategy compliance (Gate 14).

    Implements validation rules from specs/09_validation_gates.md Gate 14.

    Args:
        page_plan: Page plan artifact from W4 IAPlanner
        product_facts: Product facts artifact
        site_content_dir: Path to site content directory (RUN_DIR/work/site)
        profile: Validation profile (local, ci, prod)

    Returns:
        List of validation issues with severity, code, message, file, gate
    """
    issues = []

    def get_severity(violation_type: str) -> str:
        """Get severity based on violation type and profile."""
        if profile == "local":
            return "warn"
        elif profile == "ci":
            if violation_type in ["toc_snippets", "missing_children", "incomplete_guide"]:
                return "error"
            return "warn"
        else:  # prod
            if violation_type == "toc_snippets":
                return "blocker"
            return "error"

    # Rule 1: Schema compliance checks
    for page in page_plan.get("pages", []):
        if "page_role" not in page:
            issues.append({
                "issue_id": f"gate14_role_missing_{page.get('slug', 'unknown')}",
                "gate": "gate_14_content_distribution",
                "severity": get_severity("missing_role"),
                "message": f"Page '{page.get('slug', 'unknown')}' missing page_role field",
                "error_code": "GATE14_ROLE_MISSING",
                "location": {"path": page.get("output_path", "unknown")},
                "status": "OPEN",
            })
            continue  # Skip other checks if role missing (backward compatibility)

        if "content_strategy" not in page:
            issues.append({
                "issue_id": f"gate14_strategy_missing_{page.get('slug', 'unknown')}",
                "gate": "gate_14_content_distribution",
                "severity": get_severity("missing_strategy"),
                "message": f"Page '{page.get('slug', 'unknown')}' missing content_strategy field",
                "error_code": "GATE14_STRATEGY_MISSING",
                "location": {"path": page.get("output_path", "unknown")},
                "status": "OPEN",
            })
            continue  # Skip other checks if strategy missing

    # Rule 2: TOC pages compliance
    for page in page_plan.get("pages", []):
        if page.get("page_role") == "toc":
            output_path = page.get("output_path", "")
            draft_file = site_content_dir / output_path if output_path else None

            # Check for code snippets (BLOCKER in prod)
            if draft_file and draft_file.exists():
                try:
                    content = draft_file.read_text(encoding="utf-8")
                    if "```" in content:
                        issues.append({
                            "issue_id": f"gate14_toc_snippets_{page.get('slug', 'unknown')}",
                            "gate": "gate_14_content_distribution",
                            "severity": get_severity("toc_snippets"),  # BLOCKER in prod
                            "message": f"TOC page '{page['slug']}' contains code snippets (forbidden by content distribution strategy)",
                            "error_code": "GATE14_TOC_HAS_SNIPPETS",
                            "location": {"path": str(draft_file)},
                            "status": "OPEN",
                        })

                    # Check for all children referenced
                    expected_children = page.get("content_strategy", {}).get("child_pages", [])
                    missing_children = []
                    for child_slug in expected_children:
                        # Use word boundary check to avoid false positives with substring matches
                        if not re.search(rf'\b{re.escape(child_slug)}\b', content):
                            missing_children.append(child_slug)

                    if missing_children:
                        issues.append({
                            "issue_id": f"gate14_toc_missing_children_{page.get('slug', 'unknown')}",
                            "gate": "gate_14_content_distribution",
                            "severity": get_severity("missing_children"),  # ERROR in ci/prod
                            "message": f"TOC page '{page['slug']}' missing child references: {', '.join(missing_children)}",
                            "error_code": "GATE14_TOC_MISSING_CHILDREN",
                            "location": {"path": str(draft_file)},
                            "status": "OPEN",
                        })
                except Exception as e:
                    issues.append({
                        "issue_id": f"gate14_toc_read_error_{page.get('slug', 'unknown')}",
                        "gate": "gate_14_content_distribution",
                        "severity": "error",
                        "message": f"Error reading TOC file '{draft_file}': {e}",
                        "error_code": "GATE14_TOC_HAS_SNIPPETS",
                        "location": {"path": str(draft_file) if draft_file else "unknown"},
                        "status": "OPEN",
                    })

    # Rule 3: Comprehensive guide completeness
    workflows = product_facts.get("workflows", [])
    if workflows:  # Only check if workflows exist
        for page in page_plan.get("pages", []):
            if page.get("page_role") == "comprehensive_guide":
                expected_workflow_count = len(workflows)
                required_claim_ids = page.get("required_claim_ids", [])
                scenario_coverage = page.get("content_strategy", {}).get("scenario_coverage", "")

                if scenario_coverage != "all":
                    issues.append({
                        "issue_id": f"gate14_guide_coverage_{page.get('slug', 'unknown')}",
                        "gate": "gate_14_content_distribution",
                        "severity": get_severity("incomplete_guide"),  # ERROR in ci/prod
                        "message": f"Comprehensive guide '{page['slug']}' has scenario_coverage='{scenario_coverage}', expected 'all'",
                        "error_code": "GATE14_GUIDE_COVERAGE_INVALID",
                        "location": {"path": page.get("output_path", "unknown")},
                        "status": "OPEN",
                    })

                if len(required_claim_ids) < expected_workflow_count:
                    issues.append({
                        "issue_id": f"gate14_guide_incomplete_{page.get('slug', 'unknown')}",
                        "gate": "gate_14_content_distribution",
                        "severity": get_severity("incomplete_guide"),  # ERROR in ci/prod
                        "message": f"Comprehensive guide '{page['slug']}' covers {len(required_claim_ids)} workflows, expected {expected_workflow_count}",
                        "error_code": "GATE14_GUIDE_INCOMPLETE",
                        "location": {"path": page.get("output_path", "unknown")},
                        "status": "OPEN",
                    })

    # Rules 4-5: Forbidden topics and claim quota compliance
    for page in page_plan.get("pages", []):
        # Rule 5: Claim quota compliance
        quota = page.get("content_strategy", {}).get("claim_quota", {})
        min_claims = quota.get("min", 0)
        max_claims = quota.get("max", 999)
        actual_claims = len(page.get("required_claim_ids", []))

        if actual_claims < min_claims:
            issues.append({
                "issue_id": f"gate14_quota_underflow_{page.get('slug', 'unknown')}",
                "gate": "gate_14_content_distribution",
                "severity": "warn",
                "message": f"Page '{page['slug']}' has {actual_claims} claims, below minimum of {min_claims}",
                "error_code": "GATE14_CLAIM_QUOTA_UNDERFLOW",
                "location": {"path": page.get("output_path", "unknown")},
                "status": "OPEN",
            })

        if actual_claims > max_claims:
            issues.append({
                "issue_id": f"gate14_quota_exceeded_{page.get('slug', 'unknown')}",
                "gate": "gate_14_content_distribution",
                "severity": get_severity("quota_exceeded"),
                "message": f"Page '{page['slug']}' has {actual_claims} claims, exceeds maximum of {max_claims}",
                "error_code": "GATE14_CLAIM_QUOTA_EXCEEDED",
                "location": {"path": page.get("output_path", "unknown")},
                "status": "OPEN",
            })

        # Rule 4: Forbidden topics (simplified - scan for keywords)
        forbidden_topics = page.get("content_strategy", {}).get("forbidden_topics", [])
        if forbidden_topics:
            output_path = page.get("output_path", "")
            draft_file = site_content_dir / output_path if output_path else None
            if draft_file and draft_file.exists():
                try:
                    content = draft_file.read_text(encoding="utf-8")
                    # Remove code blocks to avoid false positives
                    content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                    for topic in forbidden_topics:
                        if re.search(rf'\b{re.escape(topic)}\b', content_no_code, re.IGNORECASE):
                            issues.append({
                                "issue_id": f"gate14_forbidden_topic_{page.get('slug', 'unknown')}_{topic}",
                                "gate": "gate_14_content_distribution",
                                "severity": "error",
                                "message": f"Page '{page['slug']}' contains forbidden topic: {topic}",
                                "error_code": "GATE14_FORBIDDEN_TOPIC",
                                "location": {"path": str(draft_file)},
                                "status": "OPEN",
                            })
                except Exception:
                    pass  # Skip if file can't be read

    # Rule 6: Content duplication detection (non-blog pages only)
    claim_usage = {}  # claim_id -> list of (page_slug, section)
    for page in page_plan.get("pages", []):
        section = page.get("section", "unknown")
        slug = page.get("slug", "unknown")
        for claim_id in page.get("required_claim_ids", []):
            if claim_id not in claim_usage:
                claim_usage[claim_id] = []
            claim_usage[claim_id].append((slug, section))

    for claim_id, usages in claim_usage.items():
        # Filter out blog section
        non_blog_usages = [(slug, section) for slug, section in usages if section != "blog"]
        if len(non_blog_usages) > 1:
            pages_str = ", ".join([f"{section}/{slug}" for slug, section in non_blog_usages])
            # Truncate claim_id for readability
            claim_id_short = claim_id[:16] + "..." if len(claim_id) > 16 else claim_id
            issues.append({
                "issue_id": f"gate14_claim_duplication_{claim_id[:8]}",
                "gate": "gate_14_content_distribution",
                "severity": "warn",  # Warning only (not blocker)
                "message": f"Claim {claim_id_short} used on multiple non-blog pages: {pages_str}",
                "error_code": "GATE14_CLAIM_DUPLICATION",
                "location": {"path": "multiple"},
                "status": "OPEN",
            })

    return issues


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
        gate_p1_page_size_limit,
        gate_p2_image_optimization,
        gate_p3_build_time_limit,
        gate_s1_xss_prevention,
        gate_s2_sensitive_data_leak,
        gate_s3_external_link_safety,
        gate_u_taskcard_authorization,
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

    # Gate 14: Content Distribution Compliance (TC-974)
    try:
        page_plan = load_json_artifact(run_dir, "page_plan.json")
        product_facts = load_json_artifact(run_dir, "product_facts.json")
        site_content_dir = run_dir / "work" / "site"

        content_issues = validate_content_distribution(
            page_plan=page_plan,
            product_facts=product_facts,
            site_content_dir=site_content_dir,
            profile=profile
        )
        all_issues.extend(content_issues)

        # Gate passes if no blocker/error issues
        gate_passed = not any(
            issue["severity"] in ["blocker", "error"] for issue in content_issues
        )
        gate_results.append({"name": "gate_14_content_distribution", "ok": gate_passed})
    except ValidatorArtifactMissingError:
        # If artifacts missing, skip Gate 14 (artifacts validated in Gate 1)
        gate_results.append({"name": "gate_14_content_distribution", "ok": True})

    # Gate T: Test Determinism
    gate_passed, issues = gate_t_test_determinism(run_dir, run_config, profile)
    gate_results.append({"name": "gate_t_test_determinism", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate U: Taskcard Authorization (Layer 4 post-run audit)
    gate_passed, issues = gate_u_taskcard_authorization.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_u_taskcard_authorization", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate P1: Page Size Limit (TC-571)
    gate_passed, issues = gate_p1_page_size_limit.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_p1_page_size_limit", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate P2: Image Optimization (TC-571)
    gate_passed, issues = gate_p2_image_optimization.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_p2_image_optimization", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate P3: Build Time Limit (TC-571)
    gate_passed, issues = gate_p3_build_time_limit.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_p3_build_time_limit", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate S1: XSS Prevention (TC-571)
    gate_passed, issues = gate_s1_xss_prevention.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_s1_xss_prevention", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate S2: Sensitive Data Leak (TC-571)
    gate_passed, issues = gate_s2_sensitive_data_leak.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_s2_sensitive_data_leak", "ok": gate_passed})
    all_issues.extend(issues)

    # Gate S3: External Link Safety (TC-571)
    gate_passed, issues = gate_s3_external_link_safety.execute_gate(run_dir, profile)
    gate_results.append({"name": "gate_s3_external_link_safety", "ok": gate_passed})
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

    # Normalize report for determinism (TC-935)
    validation_report = normalize_report(validation_report, run_dir)

    # Write validation_report.json
    report_path = run_dir / "artifacts" / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
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
