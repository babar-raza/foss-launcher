"""TC-480: W9 PRManager worker implementation.

This module implements the W9 PRManager that creates pull requests via the
centralized GitHub commit service with deterministic branching and PR bodies.

W9 PRManager performs:
1. Load patch_bundle.json from TC-450 (W6 LinkerAndPatcher)
2. Load validation_report.json from TC-460 (W7 Validator)
3. Generate deterministic branch name (launch/<product>/<ref>/<run_id>)
4. Build PR title and body (validation summary, diff highlights, evidence)
5. Create commit via commit service client
6. Open PR via commit service client
7. Write pr.json artifact (pr_url, number, rollback metadata)
8. Emit events per worker contracts

Output artifacts:
- pr.json (schema-validated per specs/schemas/pr.schema.json)

Spec references:
- specs/12_pr_and_release.md (PR creation workflow)
- specs/17_github_commit_service.md (Commit service integration)
- specs/21_worker_contracts.md:322-344 (W9 PRManager contract)
- specs/11_state_and_events.md (Event emission)
- specs/10_determinism_and_caching.md (Stable output requirements)

TC-480: W9 PRManager
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)
from ...io.atomic import atomic_write_json, atomic_write_text
from ...util.logging import get_logger
from ...clients.commit_service import CommitServiceClient, CommitServiceError

logger = get_logger()


class PRManagerError(Exception):
    """Base exception for W9 PRManager errors."""
    pass


class PRManagerNoChangesError(PRManagerError):
    """No changes to commit (empty patch bundle)."""
    pass


class PRManagerAuthFailedError(PRManagerError):
    """GitHub authentication failed (401/403)."""
    pass


class PRManagerRateLimitedError(PRManagerError):
    """GitHub rate limit exceeded (429)."""
    pass


class PRManagerBranchExistsError(PRManagerError):
    """Target branch already exists."""
    pass


class PRManagerTimeoutError(PRManagerError):
    """Commit service call exceeded timeout."""
    pass


class PRManagerMissingArtifactError(PRManagerError):
    """Required artifact not found (patch_bundle.json or validation_report.json)."""
    pass


def emit_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Emit a single event to events.ndjson.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type constant
        payload: Event payload
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    event_obj = {
        "event_id": event_id,
        "run_id": run_id,
        "ts": timestamp,
        "type": event_type,
        "trace_id": trace_id,
        "span_id": span_id,
        "payload": payload,
    }

    events_file = run_layout.run_dir / "events.ndjson"
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_obj, ensure_ascii=False, sort_keys=True) + "\n")


def generate_branch_name(product_slug: str, ref: str, run_id: str) -> str:
    """Generate deterministic branch name per specs/12_pr_and_release.md.

    Format: launch/<product_slug>/<github_ref_short>/<run_id_short>

    Args:
        product_slug: Product slug (e.g., aspose-note)
        ref: GitHub ref (e.g., refs/heads/main)
        run_id: Full run ID (e.g., RUN-20260128-120000Z-abc123)

    Returns:
        Deterministic branch name (e.g., launch/aspose-note/main/abc123)
    """
    # Extract short ref (e.g., refs/heads/main -> main)
    ref_short = ref.split("/")[-1] if "/" in ref else ref

    # Extract run_id short (last 6 chars of run_id)
    run_id_short = run_id.split("-")[-1][:6] if "-" in run_id else run_id[:6]

    return f"launch/{product_slug}/{ref_short}/{run_id_short}"


def generate_pr_title(product_slug: str, language: str, validation_ok: bool) -> str:
    """Generate PR title.

    Args:
        product_slug: Product slug (e.g., aspose-note)
        language: Target language (e.g., python)
        validation_ok: Whether all validation gates passed

    Returns:
        PR title string
    """
    status = "Launch" if validation_ok else "Draft Launch"
    product_display = product_slug.replace("-", " ").title()
    return f"{status}: {product_display} FOSS {language.title()}"


def generate_pr_body(
    run_id: str,
    product_slug: str,
    validation_report: Dict[str, Any],
    patch_bundle: Dict[str, Any],
    run_config: Dict[str, Any],
) -> str:
    """Generate PR body with validation summary and diff highlights.

    Args:
        run_id: Run identifier
        product_slug: Product slug
        validation_report: Validation report artifact
        patch_bundle: Patch bundle artifact
        run_config: Run configuration

    Returns:
        PR body markdown string
    """
    # Extract validation summary
    ok = validation_report.get("ok", False)
    profile = validation_report.get("profile", "unknown")
    gates = validation_report.get("gates", [])
    issues = validation_report.get("issues", [])

    gates_passed = sum(1 for g in gates if g.get("ok", False))
    gates_failed = sum(1 for g in gates if not g.get("ok", False))
    blocker_count = sum(1 for i in issues if i.get("severity") == "blocker")

    # Extract patch summary
    patches = patch_bundle.get("patches", [])
    create_count = sum(1 for p in patches if p.get("type") == "create_file")
    update_count = sum(1 for p in patches if p.get("type") in ["update_by_anchor", "update_frontmatter_keys", "update_file_range"])

    # Build PR body
    sections = []

    # Summary
    sections.append("## Summary")
    sections.append(f"Automated FOSS Launcher run for **{product_slug}**.")
    sections.append(f"")
    sections.append(f"- **Run ID**: `{run_id}`")
    sections.append(f"- **Validation Profile**: `{profile}`")
    sections.append(f"- **Gates Passed**: {gates_passed}/{len(gates)}")
    sections.append(f"- **Pages Created**: {create_count}")
    sections.append(f"- **Pages Updated**: {update_count}")
    sections.append("")

    # Validation Status
    sections.append("## Validation Status")
    if ok:
        sections.append("✅ **All validation gates passed**")
    else:
        sections.append(f"⚠️ **{gates_failed} gate(s) failed**")
        if blocker_count > 0:
            sections.append(f"🚨 **{blocker_count} blocker issue(s) found**")
    sections.append("")

    # Gate Results
    sections.append("### Gate Results")
    for gate in sorted(gates, key=lambda g: g.get("name", "")):
        gate_name = gate.get("name", "unknown")
        gate_ok = gate.get("ok", False)
        status_icon = "✅" if gate_ok else "❌"
        sections.append(f"- {status_icon} **{gate_name}**")
    sections.append("")

    # Issues (if any)
    if issues:
        sections.append("### Issues")
        for issue in sorted(issues, key=lambda i: (i.get("severity", ""), i.get("code", ""))):
            severity = issue.get("severity", "unknown")
            code = issue.get("code", "UNKNOWN")
            message = issue.get("message", "")
            severity_icon = "🚨" if severity == "blocker" else "⚠️" if severity == "error" else "ℹ️"
            sections.append(f"- {severity_icon} **[{code}]** {message}")
        sections.append("")

    # Patch Summary
    sections.append("## Changes")
    sections.append(f"- **Files Created**: {create_count}")
    sections.append(f"- **Files Updated**: {update_count}")
    sections.append("")

    # Affected Paths (sorted, first 20)
    affected_paths = sorted([p.get("path", "") for p in patches if p.get("path")])
    if affected_paths:
        sections.append("### Affected Files")
        for path in affected_paths[:20]:
            sections.append(f"- `{path}`")
        if len(affected_paths) > 20:
            sections.append(f"- ... and {len(affected_paths) - 20} more files")
        sections.append("")

    # Footer
    sections.append("---")
    sections.append(f"🤖 Generated by [FOSS Launcher](https://github.com/Aspose/foss-launcher) • Run ID: `{run_id}`")

    return "\n".join(sections)


def extract_affected_paths(patch_bundle: Dict[str, Any]) -> List[str]:
    """Extract affected paths from patch bundle (sorted).

    Args:
        patch_bundle: Patch bundle artifact

    Returns:
        Sorted list of affected file paths
    """
    patches = patch_bundle.get("patches", [])
    paths = [p.get("path", "") for p in patches if p.get("path")]
    return sorted(set(paths))


def generate_rollback_steps(branch_name: str, commit_sha: str) -> List[str]:
    """Generate rollback steps for pr.json.

    Args:
        branch_name: Branch name
        commit_sha: Commit SHA

    Returns:
        List of shell commands for rollback
    """
    return [
        "git fetch origin",
        f"git revert --no-commit {commit_sha}",
        "git commit -m 'Rollback: revert automated launch'",
        "git push origin main",
    ]


def execute_pr_manager(
    run_dir: Path,
    run_config: Dict[str, Any],
    commit_client: Optional[CommitServiceClient] = None,
) -> Dict[str, Any]:
    """Execute W9 PRManager worker.

    This worker creates a pull request via the GitHub commit service.

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary
        commit_client: Optional commit service client (for testing)

    Returns:
        Result dict with:
            - ok: bool (success)
            - pr_url: str (PR URL if created)
            - pr_number: int (PR number if created)
            - commit_sha: str (Commit SHA)
            - artifacts: List[str] (artifact paths)

    Raises:
        PRManagerError: On validation or processing error
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown-run")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    logger.info("pr_manager_started", run_id=run_id, run_dir=str(run_dir))

    # Emit start event
    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_WORK_ITEM_STARTED,
        {"worker": "W9_PRManager", "run_id": run_id},
    )

    try:
        # Load required artifacts
        patch_bundle_path = run_layout.artifacts_dir / "patch_bundle.json"
        validation_report_path = run_layout.artifacts_dir / "validation_report.json"

        if not patch_bundle_path.exists():
            raise PRManagerMissingArtifactError(
                f"patch_bundle.json not found at {patch_bundle_path}"
            )

        if not validation_report_path.exists():
            raise PRManagerMissingArtifactError(
                f"validation_report.json not found at {validation_report_path}"
            )

        with open(patch_bundle_path, "r", encoding="utf-8") as f:
            patch_bundle = json.load(f)

        with open(validation_report_path, "r", encoding="utf-8") as f:
            validation_report = json.load(f)

        # Check for empty patch bundle (no changes)
        patches = patch_bundle.get("patches", [])
        if not patches:
            logger.info("pr_manager_no_changes", run_id=run_id)
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_WORK_ITEM_FINISHED,
                {
                    "worker": "W9_PRManager",
                    "run_id": run_id,
                    "status": "no_changes",
                    "message": "No changes to commit",
                },
            )
            return {
                "ok": True,
                "status": "no_changes",
                "message": "No changes to commit, PR creation skipped",
                "artifacts": [],
            }

        # Extract configuration
        product_slug = run_config.get("product_slug", "unknown-product")
        language = run_config.get("language", "python")
        repo_url = run_config.get("repo_url", "https://github.com/Aspose/aspose.org")
        base_ref = run_config.get("base_ref", "main")
        allowed_paths = run_config.get("allowed_paths", [])

        # Generate branch name (deterministic)
        github_ref = run_config.get("github_ref", "refs/heads/main")
        branch_name = generate_branch_name(product_slug, github_ref, run_id)

        # Generate PR title and body
        validation_ok = validation_report.get("ok", False)
        pr_title = generate_pr_title(product_slug, language, validation_ok)
        pr_body = generate_pr_body(
            run_id, product_slug, validation_report, patch_bundle, run_config
        )

        # Build commit message
        commit_message = f"Launch {product_slug} FOSS {language}"
        commit_body = f"""Automated FOSS Launcher run {run_id}

Validation: {validation_report.get('gates_passed', 0)}/{len(validation_report.get('gates', []))} gates passed
Profile: {validation_report.get('profile', 'unknown')}

Generated by FOSS Launcher
"""

        # Create commit via commit service (construct client if not provided)
        if commit_client is None:
            # Construct commit service client from run_config
            commit_service_config = run_config.get("commit_service", {})
            if not commit_service_config:
                raise PRManagerError(
                    "commit_service configuration missing in run_config"
                )

            # Extract endpoint_url
            base_url = commit_service_config.get("endpoint_url")
            if not base_url:
                raise PRManagerError(
                    "commit_service.endpoint_url missing in run_config"
                )

            # Get GitHub token from environment if specified
            github_token_env = commit_service_config.get("github_token_env", "GITHUB_TOKEN")
            auth_token = os.getenv(github_token_env, "")

            commit_client = CommitServiceClient(
                endpoint_url=base_url,
                auth_token=auth_token,
                timeout=commit_service_config.get("timeout", 30),
                run_dir=run_layout.run_dir,
            )
            logger.info(
                "pr_manager_client_constructed",
                run_id=run_id,
                endpoint_url=base_url,
            )

        # Check for offline mode
        offline_mode = os.getenv("OFFLINE_MODE", "0") == "1"
        if offline_mode:
            logger.info("pr_manager_offline_mode", run_id=run_id)

            # Create offline bundle directory
            offline_bundles_dir = run_layout.run_dir / "offline_bundles"
            offline_bundles_dir.mkdir(parents=True, exist_ok=True)

            # Write offline PR payload
            offline_payload = {
                "run_id": run_id,
                "repo_url": repo_url,
                "base_ref": base_ref,
                "branch_name": branch_name,
                "commit_message": commit_message,
                "commit_body": commit_body,
                "pr_title": pr_title,
                "pr_body": pr_body,
                "patch_bundle": patch_bundle,
                "validation_report": validation_report,
                "allowed_paths": allowed_paths,
                "mode": "offline",
            }

            offline_payload_path = offline_bundles_dir / "pr_payload.json"
            atomic_write_json(offline_payload_path, offline_payload)

            logger.info(
                "pr_manager_offline_bundle_written",
                run_id=run_id,
                path=str(offline_payload_path),
            )

            # Emit success event
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_WORK_ITEM_FINISHED,
                {
                    "worker": "W9_PRManager",
                    "run_id": run_id,
                    "status": "offline_ok",
                    "message": "Offline bundle created",
                },
            )

            return {
                "ok": True,
                "status": "offline_ok",
                "message": "Offline bundle created, network calls skipped",
                "offline_bundle": str(offline_payload_path),
                "artifacts": [str(offline_payload_path)],
            }

        # AG-001 Task A3: Collect branch creation approval metadata
        ai_governance_metadata = None
        approval_marker_path = run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"

        if approval_marker_path.exists():
            # Read approval marker
            try:
                with open(approval_marker_path, "r", encoding="utf-8") as f:
                    approval_source = f.read().strip() or "manual-marker"

                # Build AG-001 approval metadata
                ai_governance_metadata = {
                    "ag001_approval": {
                        "approved": True,
                        "approval_source": approval_source if approval_source in ["interactive-dialog", "manual-marker", "config-override"] else "manual-marker",
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "approver": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
                    }
                }

                logger.info(
                    "pr_manager_ag001_approval_collected",
                    run_id=run_id,
                    approval_source=approval_source,
                )
            except Exception as e:
                logger.warning(
                    "pr_manager_approval_marker_read_failed",
                    run_id=run_id,
                    error=str(e),
                )
        else:
            logger.warning(
                "pr_manager_no_approval_marker",
                run_id=run_id,
                message="AG-001 approval marker not found, commit may be rejected by service",
            )

        try:
            # Create commit
            idempotency_key = str(uuid.uuid4())
            logger.info(
                "pr_manager_creating_commit",
                run_id=run_id,
                branch_name=branch_name,
                idempotency_key=idempotency_key,
                has_governance_metadata=ai_governance_metadata is not None,
            )

            commit_response = commit_client.create_commit(
                run_id=run_id,
                repo_url=repo_url,
                base_ref=base_ref,
                branch_name=branch_name,
                allowed_paths=allowed_paths,
                commit_message=commit_message,
                commit_body=commit_body,
                patch_bundle=patch_bundle,
                idempotency_key=idempotency_key,
                allow_existing_branch=False,
                require_clean_base=True,
                ai_governance_metadata=ai_governance_metadata,
            )

            commit_sha = commit_response.get("commit_sha")
            logger.info(
                "pr_manager_commit_created",
                run_id=run_id,
                commit_sha=commit_sha,
                branch_name=branch_name,
            )

            # Emit commit created event
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "COMMIT_CREATED",
                {
                    "worker": "W9_PRManager",
                    "run_id": run_id,
                    "commit_sha": commit_sha,
                    "branch_name": branch_name,
                },
            )

            # Open PR
            pr_idempotency_key = str(uuid.uuid4())
            logger.info(
                "pr_manager_opening_pr",
                run_id=run_id,
                branch_name=branch_name,
                idempotency_key=pr_idempotency_key,
            )

            pr_response = commit_client.open_pr(
                run_id=run_id,
                repo_url=repo_url,
                base_ref=base_ref,
                head_ref=branch_name,
                title=pr_title,
                body=pr_body,
                idempotency_key=pr_idempotency_key,
                draft=not validation_ok,  # Draft if validation failed
                labels=["foss-launcher", "automated"],
            )

            pr_number = pr_response.get("pr_number")
            pr_url = pr_response.get("pr_html_url") or pr_response.get("pr_url")

            logger.info(
                "pr_manager_pr_opened",
                run_id=run_id,
                pr_number=pr_number,
                pr_url=pr_url,
            )

            # Emit PR opened event
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "PR_OPENED",
                {
                    "worker": "W9_PRManager",
                    "run_id": run_id,
                    "pr_number": pr_number,
                    "pr_url": pr_url,
                    "branch_name": branch_name,
                },
            )

        except CommitServiceError as e:
            # Map commit service errors to PR manager errors
            if e.status_code in [401, 403]:
                logger.error(
                    "pr_manager_auth_failed",
                    run_id=run_id,
                    error_code=e.error_code,
                    status_code=e.status_code,
                )
                emit_event(
                    run_layout,
                    run_id,
                    trace_id,
                    span_id,
                    EVENT_ISSUE_OPENED,
                    {
                        "worker": "W9_PRManager",
                        "severity": "blocker",
                        "code": "PR_MANAGER_AUTH_FAILED",
                        "message": f"GitHub authentication failed: {str(e)}",
                    },
                )
                raise PRManagerAuthFailedError(str(e)) from e

            elif e.status_code == 429:
                logger.error(
                    "pr_manager_rate_limited",
                    run_id=run_id,
                    error_code=e.error_code,
                )
                raise PRManagerRateLimitedError(str(e)) from e

            elif e.error_code == "BRANCH_EXISTS":
                logger.error(
                    "pr_manager_branch_exists",
                    run_id=run_id,
                    branch_name=branch_name,
                )
                raise PRManagerBranchExistsError(
                    f"Branch {branch_name} already exists"
                ) from e

            else:
                logger.error(
                    "pr_manager_commit_service_error",
                    run_id=run_id,
                    error_code=e.error_code,
                    status_code=e.status_code,
                )
                raise PRManagerError(f"Commit service error: {str(e)}") from e

        # Get base_ref SHA (for rollback)
        # In production, this would be fetched from git
        # For now, use a placeholder (will be replaced by actual implementation)
        base_ref_sha = "0" * 40  # Placeholder

        # Extract affected paths
        affected_paths = extract_affected_paths(patch_bundle)

        # Generate rollback steps
        rollback_steps = generate_rollback_steps(branch_name, commit_sha)

        # Build pr.json artifact
        pr_artifact = {
            "schema_version": "1.0",
            "run_id": run_id,
            "base_ref": base_ref_sha,
            "rollback_steps": rollback_steps,
            "affected_paths": affected_paths,
            "pr_number": pr_number,
            "pr_url": pr_url,
            "branch_name": branch_name,
            "commit_shas": [commit_sha],
            "pr_body": pr_body,
            "validation_summary": {
                "ok": validation_ok,
                "profile": validation_report.get("profile", "unknown"),
                "gates_passed": sum(1 for g in validation_report.get("gates", []) if g.get("ok", False)),
                "gates_failed": sum(1 for g in validation_report.get("gates", []) if not g.get("ok", False)),
            },
        }

        # Write pr.json artifact
        pr_artifact_path = run_layout.artifacts_dir / "pr.json"
        atomic_write_json(pr_artifact_path, pr_artifact)
        logger.info("pr_manager_artifact_written", path=str(pr_artifact_path))

        # Emit artifact written event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_ARTIFACT_WRITTEN,
            {
                "worker": "W9_PRManager",
                "artifact_type": "pr_metadata",
                "path": str(pr_artifact_path),
            },
        )

        # Emit completion event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_WORK_ITEM_FINISHED,
            {
                "worker": "W9_PRManager",
                "run_id": run_id,
                "status": "success",
                "pr_url": pr_url,
                "pr_number": pr_number,
            },
        )

        logger.info(
            "pr_manager_completed",
            run_id=run_id,
            pr_url=pr_url,
            pr_number=pr_number,
        )

        return {
            "ok": True,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "branch_name": branch_name,
            "artifacts": [str(pr_artifact_path)],
        }

    except PRManagerError:
        # Re-raise PR manager errors
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "pr_manager_unexpected_error",
            run_id=run_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_RUN_FAILED,
            {
                "worker": "W9_PRManager",
                "run_id": run_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise PRManagerError(f"Unexpected error: {str(e)}") from e
