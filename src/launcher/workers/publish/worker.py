"""Publish worker — apply content to site worktree and open PR.

Only runs after Evaluate returns GO. Deterministic, no LLM calls.

1. Collect all generated markdown files from the content bundle.
2. Build patches (create/update actions) with content hashes.
3. If goal=pr, call commit service to create branch + open PR.
4. If goal=draft, write patch bundle to disk (offline mode).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml  # optional — used only for content_index.yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

from launcher.models.base import LauncherBaseModel
from launcher.models.content import ContentManifest, GeneratedPage
from launcher.models.evaluation import EvaluationReport, Verdict
from launcher.models.publish import Patch, PatchAction, PublishBundle, PullRequest
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract

logger = logging.getLogger(__name__)


class PublishWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "publish"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> PublishBundle:
        """Build patches from generated content and optionally open a PR."""
        start_time = time.monotonic()

        context.log.info("[Publish] Starting publish")
        context.emit_event("worker_started", {}, worker=self.name)

        # Load the content manifest from the generate checkpoint
        manifest = _load_content_manifest(context)
        if manifest is None:
            context.log.warning("[Publish] No content manifest found; producing empty bundle")
            return PublishBundle()

        # Build patches from generated files
        patches = _build_patches(manifest, context.run_dir)

        # Determine publish mode
        goal = context.config.output.goal  # "draft" or "pr"

        pr = PullRequest()
        if goal == "pr":
            pr = await _open_pr(patches, manifest, context)
        else:
            # Draft mode: write patch bundle to disk
            _write_patch_bundle(patches, context)

        # Promote to deploy/ staging directory (if configured)
        deployed_count = 0
        promotion_report = None
        if context.config.output.deploy_dir:
            promotion_report, deployed_count = await _promote_to_deploy(context)

        # TC-5166: Write content_index.yaml to knowledge/ for drift detection
        if promotion_report and deployed_count > 0:
            _write_content_index(promotion_report, manifest, context)

        # Copy promoted files to content repo and open MR (if configured)
        merge_request_url = ""
        merge_request_branch = ""
        if promotion_report and deployed_count > 0 and context.config.output.content_repo_map:
            merge_request_url, merge_request_branch = await _push_to_content_repo(
                promotion_report, context,
            )

        elapsed = time.monotonic() - start_time
        published_at = datetime.now(timezone.utc).isoformat()

        bundle = PublishBundle(
            patches=patches,
            pr=pr,
            published_at=published_at,
            deployed_count=deployed_count,
            merge_request_url=merge_request_url,
            merge_request_branch=merge_request_branch,
        )

        context.log.info(
            "[Publish] Complete: %d patches, deployed=%d, goal=%s, %.1fs",
            len(patches), deployed_count, goal, elapsed,
        )
        context.emit_event("worker_completed", {
            "patches": len(patches),
            "goal": goal,
            "pr_url": pr.url,
            "deployed_count": deployed_count,
            "merge_request_url": merge_request_url,
        }, worker=self.name)

        return bundle

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Verify publish bundle consistency."""
        if not isinstance(output, PublishBundle):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not PublishBundle"}])

        bundle = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}

        # Check: all patches have content hashes
        missing_hash = [p.file_path for p in bundle.patches if not p.content_hash]
        if missing_hash:
            findings.append({
                "category": "missing_hash",
                "message": f"{len(missing_hash)} patches without content hash",
                "severity": "medium",
            })

        # Check: no duplicate file paths
        paths = [p.file_path for p in bundle.patches]
        dupes = [p for p in paths if paths.count(p) > 1]
        if dupes:
            findings.append({
                "category": "duplicate_patch",
                "message": f"Duplicate patch paths: {sorted(set(dupes))}",
                "severity": "high",
            })

        metrics["patch_count"] = len(bundle.patches)
        metrics["pr_state"] = bundle.pr.state
        metrics["deployed_count"] = bundle.deployed_count

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def create_worker() -> PublishWorker:
    return PublishWorker()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_content_manifest(context: WorkerContext) -> ContentManifest | None:
    """Load the content manifest from the generate checkpoint."""
    checkpoint_path = context.run_dir / "generate_checkpoint.json"
    if not checkpoint_path.exists():
        return None
    try:
        raw = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        return ContentManifest.model_validate(raw)
    except Exception as e:
        logger.warning("[Publish] Failed to load content manifest: %s", e)
        return None


def _build_patches(
    manifest: ContentManifest,
    run_dir: Path,
) -> list[Patch]:
    """Build patch list from generated pages."""
    patches: list[Patch] = []

    for page in manifest.pages:
        md_path = run_dir / page.md_path
        if not md_path.exists():
            logger.warning("[Publish] Missing file: %s", page.md_path)
            continue

        content = md_path.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()

        # Target path in the site repo
        target_path = _target_file_path(page)

        patches.append(Patch(
            file_path=target_path,
            action=PatchAction.create,
            content_hash=content_hash,
        ))

    return patches


def _target_file_path(page: GeneratedPage) -> str:
    """Compute the target file path in the site repository."""
    if page.content_path:
        return f"{page.content_path}.md"
    # Fallback for pages without content_path
    section = page.section or "docs"
    slug = page.slug
    return f"{section}/{slug}.md"


def _write_patch_bundle(patches: list[Patch], context: WorkerContext) -> None:
    """Write the patch bundle to disk for offline/draft mode."""
    bundle_dir = context.run_dir / "artifacts"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    bundle_data = {
        "patches": [p.model_dump(mode="json") for p in patches],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    bundle_path = bundle_dir / "patch_bundle.json"
    bundle_path.write_text(
        json.dumps(bundle_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("[Publish] Wrote patch bundle: %s", bundle_path)


async def _open_pr(
    patches: list[Patch],
    manifest: ContentManifest,
    context: WorkerContext,
) -> PullRequest:
    """Create a commit and open a PR via the commit service."""
    try:
        from launcher.clients.commit_service import CommitServiceClient

        config = context.config
        run_id = context.run_id

        # Build branch name
        branch_name = f"launch/{config.family}-{config.platform}/{run_id[:12]}"

        # Build commit message
        commit_message = (
            f"docs: add generated content for {config.family} ({config.platform})"
        )
        commit_body = (
            f"Generated by foss-launcher v2\n"
            f"Run ID: {run_id}\n"
            f"Pages: {len(manifest.pages)}\n"
        )

        # Build patch bundle for commit service
        patch_bundle = {
            "patches": [
                {
                    "patch_id": f"patch-{i}",
                    "type": "create_file",
                    "path": p.file_path,
                    "content_hash": p.content_hash,
                    "new_content": _read_page_content(p, manifest, context.run_dir),
                }
                for i, p in enumerate(patches)
            ],
        }

        # Allowed paths
        allowed_paths = sorted({p.file_path.split("/")[0] for p in patches})

        client = CommitServiceClient(
            endpoint_url="",
            auth_token="",
            offline_mode=True,
            run_dir=context.run_dir,
        )

        # Create commit
        commit_result = client.create_commit(
            run_id=run_id,
            repo_url=config.repo_url,
            base_ref="main",
            branch_name=branch_name,
            allowed_paths=allowed_paths,
            commit_message=commit_message,
            commit_body=commit_body,
            patch_bundle=patch_bundle,
        )

        # Open PR
        pr_title = f"[launcher] {config.family} {config.platform} content"
        pr_body = _build_pr_body(manifest, patches, run_id)

        pr_result = client.open_pr(
            run_id=run_id,
            repo_url=config.repo_url,
            base_ref="main",
            head_ref=branch_name,
            title=pr_title,
            body=pr_body,
            draft=True,
        )

        return PullRequest(
            url=pr_result.get("pr_html_url", pr_result.get("pr_url", "")),
            number=pr_result.get("pr_number", 0),
            title=pr_title,
            state="draft",
        )

    except Exception as e:
        logger.warning("[Publish] PR creation failed, falling back to offline: %s", e)
        _write_patch_bundle(patches, context)
        return PullRequest(state="offline")


def _read_page_content(
    patch: Patch,
    manifest: ContentManifest,
    run_dir: Path,
) -> str:
    """Read the content of a generated page for the patch bundle."""
    for page in manifest.pages:
        target = _target_file_path(page)
        if target == patch.file_path:
            md_path = run_dir / page.md_path
            if md_path.exists():
                return md_path.read_text(encoding="utf-8")
    return ""


def _build_pr_body(
    manifest: ContentManifest | None,
    patches: list[Patch],
    run_id: str,
) -> str:
    """Build the PR body markdown."""
    lines = [
        "## Summary",
        "",
        f"- **Run ID**: `{run_id}`",
    ]
    if manifest is not None:
        stats = manifest.generation_stats
        lines += [
            f"- **Pages**: {stats.total_pages}",
            f"- **LLM calls**: {stats.llm_calls}",
            f"- **Fallback count**: {stats.fallback_count}",
            f"- **Duration**: {stats.duration_seconds}s",
        ]
    else:
        lines.append(f"- **Pages**: {len(patches)}")
    lines += [
        "",
        "## Files",
        "",
    ]
    for p in patches[:20]:
        lines.append(f"- `{p.file_path}` ({p.action.value})")
    if len(patches) > 20:
        lines.append(f"- ... and {len(patches) - 20} more")
    lines.append("")
    lines.append("---")
    lines.append("Generated by foss-launcher v2")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deploy and MR helpers
# ---------------------------------------------------------------------------


async def _promote_to_deploy(
    context: WorkerContext,
) -> tuple[Any, int]:
    """Promote qualifying pages from run_dir into the deploy/ staging directory.

    Returns:
        Tuple of (PromotionReport | None, promoted_count).
        On any failure returns (None, 0) — never raises.
    """
    import asyncio

    from launcher.deploy.promoter import Grade, promote_run

    deploy_dir = Path(context.config.output.deploy_dir)
    if not deploy_dir.is_absolute():
        deploy_dir = Path.cwd() / deploy_dir

    try:
        report = await asyncio.to_thread(
            promote_run,
            run_dir=context.run_dir,
            deploy_dir=deploy_dir,
            min_grade=Grade.C,
        )
        context.log.info(
            "[Publish] Deploy staging: promoted=%d grade_low=%d no_improve=%d"
            " same_hash=%d missing=%d",
            report.promoted,
            report.skipped_grade_low,
            report.skipped_no_improvement,
            report.skipped_same_hash,
            report.skipped_missing_file,
        )
        context.emit_event(
            "deploy_promoted",
            {
                "promoted": report.promoted,
                "skipped_grade_low": report.skipped_grade_low,
                "deploy_dir": str(deploy_dir),
            },
            worker="publish",
        )
        return report, report.promoted
    except Exception as exc:
        context.log.warning("[Publish] promote_run failed: %s", exc)
        return None, 0


async def _push_to_content_repo(
    promotion_report: Any,
    context: WorkerContext,
) -> tuple[str, str]:
    """Copy promoted pages to per-domain content repo clones and open pull requests.

    Pages are grouped by domain (first component of content_path, e.g.
    ``"docs.aspose.org"``).  Each domain is looked up in
    ``context.config.output.content_repo_map``; domains without a mapping are
    skipped with a warning.

    Returns:
        Tuple of (first_pr_url, branch_name).  Returns ("", "") when nothing
        was pushed.  Never raises — all per-domain failures are logged and skipped.
    """
    import asyncio

    from launcher.deploy.promoter import PromotionAction
    from launcher.workers.publish._git_publisher import (
        copy_to_content_repo,
        gh_create_pr,
        git_add_and_commit,
        git_create_branch,
        git_push,
        resolve_content_repo_dir,
    )

    config = context.config
    content_repo_map = config.output.content_repo_map

    deploy_dir = Path(config.output.deploy_dir)
    if not deploy_dir.is_absolute():
        deploy_dir = Path.cwd() / deploy_dir

    # Only pages promoted in this run
    promoted_paths = [
        d.content_path
        for d in promotion_report.details
        if d.action == PromotionAction.PROMOTED
    ]
    if not promoted_paths:
        return "", ""

    # Group by TLD (last two components of subdomain, e.g. "aspose.org" / "aspose.net")
    by_tld: dict[str, list[str]] = {}
    for cp in promoted_paths:
        subdomain = cp.split("/")[0]          # e.g. "docs.aspose.org"
        parts = subdomain.split(".")
        tld_key = ".".join(parts[-2:]) if len(parts) >= 2 else subdomain
        by_tld.setdefault(tld_key, []).append(cp)

    branch_name = f"launch/{config.family}-{config.platform}/{context.run_id[:12]}"
    commit_msg = f"docs: add generated content for {config.family} ({config.platform})"
    pr_title = f"[launcher] {config.family} {config.platform} content"

    first_url = ""
    all_urls: list[str] = []

    for tld_key, paths in by_tld.items():
        repo_raw = content_repo_map.get(tld_key, "")
        if not repo_raw:
            context.log.warning("[Publish] No repo configured for TLD: %s", tld_key)
            continue

        content_repo_dir = resolve_content_repo_dir(repo_raw)
        if not content_repo_dir.is_dir():
            context.log.warning(
                "[Publish] content_repo not found for %s: %s", tld_key, content_repo_dir,
            )
            continue

        try:
            written = await asyncio.to_thread(
                copy_to_content_repo, deploy_dir, content_repo_dir, paths,
            )
            if not written:
                context.log.warning("[Publish] No files written for TLD: %s", tld_key)
                continue

            await asyncio.to_thread(git_create_branch, content_repo_dir, branch_name)
            await asyncio.to_thread(git_add_and_commit, content_repo_dir, written, commit_msg)
            await asyncio.to_thread(git_push, content_repo_dir, branch_name)

            pr_body = _build_pr_body(
                None,
                [Patch(file_path=cp + ".md", action=PatchAction.create) for cp in paths],
                context.run_id,
            )
            pr_url = await asyncio.to_thread(
                gh_create_pr, content_repo_dir, pr_title, pr_body,
            )
            all_urls.append(pr_url)
            if not first_url:
                first_url = pr_url

            context.log.info(
                "[Publish] MR created for %s: %s (branch: %s, files: %d)",
                tld_key, pr_url, branch_name, len(written),
            )

        except Exception as exc:
            context.log.warning("[Publish] Failed for TLD %s: %s", tld_key, exc)

    if all_urls:
        context.emit_event(
            "merge_request_created",
            {"urls": all_urls, "branch": branch_name, "domains": list(by_tld.keys())},
            worker="publish",
        )

    return first_url, branch_name if first_url else ""


# ---------------------------------------------------------------------------
# TC-5166: Content Index — knowledge/ link
# ---------------------------------------------------------------------------


def _write_content_index(
    promotion_report: Any,
    manifest: ContentManifest | None,
    context: WorkerContext,
) -> None:
    """Write knowledge/{family}/{platform}/content_index.yaml after a successful promote.

    Builds a per-page link table between the deployed content files and the
    knowledge/ evidence store.  The Verify worker (TC-5167) reads this file
    to detect drift between repo truth and live aspose.org/content pages.

    Silently no-ops when yaml is unavailable, knowledge_dir cannot be created,
    or the deploy_dir is not configured.  Never raises.

    Args:
        promotion_report: PromotionReport from _promote_to_deploy().
        manifest: ContentManifest with per-page metadata (page_role, slug, etc.).
        context: Worker execution context (config, run_dir, log).
    """
    if _yaml is None:
        logger.debug("[Publish] yaml unavailable — skipping content_index write")
        return

    try:
        from launcher.deploy.promoter import PromotionAction

        config = context.config
        family = config.family
        platform = config.platform

        # Resolve knowledge directory
        project_root = Path(context.run_dir).parent.parent
        knowledge_dir = project_root / "knowledge" / family / platform
        try:
            knowledge_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("[Publish] Cannot create knowledge_dir %s: %s", knowledge_dir, exc)
            return

        # Resolve deploy_dir
        deploy_dir_str = config.output.deploy_dir
        if not deploy_dir_str:
            logger.debug("[Publish] deploy_dir not configured — skipping content_index write")
            return
        deploy_dir = Path(deploy_dir_str)
        if not deploy_dir.is_absolute():
            deploy_dir = Path.cwd() / deploy_dir

        # Build page_role lookup from manifest
        role_by_path: dict[str, str] = {}
        slug_by_path: dict[str, str] = {}
        if manifest is not None:
            for page in manifest.pages:
                if page.content_path:
                    role_by_path[page.content_path] = page.page_role
                    slug_by_path[page.content_path] = page.slug

        # Try to read repo_sha from understand checkpoint
        repo_sha = ""
        understand_cp = context.run_dir / "understand_checkpoint.json"
        if understand_cp.exists():
            try:
                uc_data = json.loads(understand_cp.read_text(encoding="utf-8"))
                repo_sha = (uc_data.get("product") or {}).get("repo_sha", "")
            except Exception:
                pass

        now = datetime.now(timezone.utc).isoformat()

        # Build page entries for promoted files only
        page_entries = []
        for detail in promotion_report.details:
            if detail.action != PromotionAction.PROMOTED:
                continue
            content_path = detail.content_path
            deployed_file = deploy_dir / (content_path + ".md")
            content_sha = ""
            if deployed_file.exists():
                content_sha = "sha256:" + hashlib.sha256(deployed_file.read_bytes()).hexdigest()
            page_entries.append({
                "content_path": content_path,
                "page_role": role_by_path.get(content_path, ""),
                "slug": slug_by_path.get(content_path, content_path.rsplit("/", 1)[-1]),
                "content_sha": content_sha,
                "repo_sha_when_generated": repo_sha,
                "generated_at": now,
                "status": "live",
            })

        if not page_entries:
            logger.debug("[Publish] No promoted pages — skipping content_index write")
            return

        index_data = {
            "family": family,
            "platform": platform,
            "last_sync": now,
            "pages": page_entries,
        }

        index_path = knowledge_dir / "content_index.yaml"
        index_path.write_text(
            _yaml.dump(index_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        logger.info(
            "[Publish] Wrote content_index.yaml: %d pages → %s",
            len(page_entries),
            index_path,
        )

    except Exception as exc:
        logger.warning("[Publish] Failed to write content_index.yaml: %s", exc)
