"""Scout worker — repository inventory and shared facts extraction.

TC-4075: ScoutWorker is the first runtime phase after Intake.
It fingerprints the cloned repo, reads file content under budget, and
extracts multi-platform shared facts (manifest metadata).

Pipeline position: Intake → Scout → Understand → Planner → …

Scout inputs:  IntakeBundle (from Intake worker)
Scout outputs: ScoutBundle (repo inventory + identity pass-through)

The raw repo_content dict (bulk file text) is set on context.repo_content
so Understand can consume it without re-reading from disk.
On resume (context.repo_content is None or empty), Understand re-reads
files from the file_index stored in ScoutBundle.repo_info.

Spec reference: specs/worker_understand.md  Phase A
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.intake import IntakeBundle
from launcher.models.scout import ScoutBundle
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult

logger = logging.getLogger(__name__)


class ScoutWorker(WorkerContract):
    """Phase A: fingerprint a pre-cloned repository and extract shared facts."""

    @property
    def name(self) -> str:
        return "scout"

    async def run(
        self, input_data: LauncherBaseModel, context: WorkerContext,
    ) -> ScoutBundle:
        """Execute Scout phase: walk file tree, read content, extract shared facts."""
        # Resolve input from IntakeBundle
        if isinstance(input_data, IntakeBundle):
            intake = input_data
        else:
            intake = IntakeBundle.model_validate(input_data.model_dump())

        repo_dir = Path(intake.repo_dir) if intake.repo_dir else None
        if not repo_dir or not repo_dir.is_dir():
            raise ValueError(
                f"[Scout] repo_dir does not exist: {intake.repo_dir!r}. "
                "Clone may have failed at Intake or the cached directory was deleted."
            )

        context.log.info("[Scout] Starting: fingerprinting %s", repo_dir)
        context.emit_event("worker_started", {"phase": "scout"}, worker=self.name)

        from launcher.workers.scout.scout import build_scout_inventory, run_scout

        repo_info, repo_content, budget_log, budget_log_overflow = await run_scout(
            repo_dir, platform=intake.platform or "",
            canonical_import=intake.canonical_import or "",
        )

        # Set in-memory content for Understand (same-process fresh run)
        context.repo_content = repo_content
        context.repo_dir = repo_dir

        context.log.info(
            "[Scout] Complete: %d files, %d read (%.1f KB), %d docs, %d examples, "
            "budget_log=%d overflow=%d",
            len(repo_info.file_tree),
            repo_info.content_files_read,
            repo_info.content_budget_used / 1024,
            len(repo_info.doc_paths),
            len(repo_info.example_paths),
            len(budget_log),
            budget_log_overflow,
        )

        # Write Scout artifacts: concise summary + full reviewable inventory.
        scout_inventory = build_scout_inventory(
            repo_info=repo_info,
            repo_content=repo_content,
            budget_log=budget_log,
            budget_log_overflow=budget_log_overflow,
        )
        context.store.write_json("scout_inventory.json", scout_inventory)
        context.log.info("[Scout] scout_inventory.json written")

        try:
            cat_counts: dict[str, int] = {}
            for entry in repo_info.file_index.values():
                cat_counts[entry.category.value] = cat_counts.get(entry.category.value, 0) + 1

            scout_artifact: dict[str, Any] = {
                "files_enumerated": len(repo_info.file_tree),
                "files_read": repo_info.content_files_read,
                "content_used_bytes": repo_info.content_budget_used,
                "by_category": cat_counts,
                "budget_log_overflow_count": budget_log_overflow,
                "package_name": repo_info.shared_facts.package_name,
                "primary_language": repo_info.shared_facts.primary_language,
                "build_systems": repo_info.shared_facts.build_systems,
                "has_tests": repo_info.shared_facts.has_tests,
                "has_ci": repo_info.shared_facts.has_ci,
                "has_docs_folder": repo_info.shared_facts.has_docs_folder,
                "has_examples_folder": repo_info.shared_facts.has_examples_folder,
            }
            context.store.write_json("scout_bundle.json", scout_artifact)
            context.log.info("[Scout] scout_bundle.json written")
            # TC-4104: also write scout.json so phase_promoter can promote it to
            # phase_store/{family}/{platform}/scout.json for cross-run comparison.
            context.store.write_json("scout.json", scout_artifact)
        except Exception:
            context.log.warning("[Scout] Failed to write scout_bundle.json", exc_info=True)

        context.emit_event(
            "worker_completed",
            {
                "files_enumerated": len(repo_info.file_tree),
                "files_read": repo_info.content_files_read,
                "primary_language": repo_info.shared_facts.primary_language,
            },
            worker=self.name,
        )

        return ScoutBundle(
            # Identity pass-through
            family=intake.family,
            platform=intake.platform,
            repo_url=intake.repo_url,
            display_name=intake.display_name,
            canonical_import=intake.canonical_import,
            runtime_import=intake.runtime_import,
            launch_tier=intake.launch_tier,
            repo_sha=intake.repo_sha,
            repo_dir=intake.repo_dir,
            discovered_at=intake.discovered_at,
            # Scout outputs
            repo_info=repo_info,
            budget_log=budget_log,
            budget_log_overflow_count=budget_log_overflow,
        )

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Semantic self-review of the ScoutBundle."""
        if not isinstance(output, ScoutBundle):
            return SelfReviewResult(
                passed=False,
                findings=[{"message": "Output is not ScoutBundle"}],
            )

        bundle = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}
        from launcher.workers.scout.scout import _doc_skip_reason
        from launcher.workers.understand.file_classifier import has_example_dir

        # Check 1: No files enumerated — something went wrong with the file walk
        if len(bundle.repo_info.file_tree) == 0:
            findings.append({
                "category": "scout_empty",
                "severity": "high",
                "message": (
                    "Scout found no files — repo_dir may be empty or file walk failed. "
                    f"repo_dir={bundle.repo_dir!r}"
                ),
            })

        # Check 2: No files read — budget or permission failure
        if bundle.repo_info.content_files_read == 0:
            findings.append({
                "category": "scout_no_content",
                "severity": "high",
                "message": (
                    "No files read by Scout — budget exhausted immediately or all files "
                    "are binary. Check budget_log for details."
                ),
            })

        meta_docs = [path for path in bundle.repo_info.doc_paths if _doc_skip_reason(path, is_external_repo=True)]
        if meta_docs:
            findings.append({
                "category": "scout_meta_docs_selected",
                "severity": "high",
                "message": (
                    "Scout selected operator/meta docs as product evidence: "
                    + ", ".join(meta_docs[:5])
                ),
            })

        example_dir_candidates = [
            path for path in bundle.repo_info.file_tree
            if has_example_dir(path)
            and bundle.repo_info.file_index.get(path)
            and bundle.repo_info.file_index[path].language
        ]
        selected_examples = list(bundle.repo_info.example_paths)
        if (
            bundle.repo_info.shared_facts.has_examples_folder
            and len(example_dir_candidates) >= 5
            and len(selected_examples) < 2
        ):
            findings.append({
                "category": "scout_example_starvation",
                "severity": "high",
                "message": (
                    "Scout retained too little example evidence for an example-heavy repo. "
                    f"selected_examples={len(selected_examples)} candidate_example_files={len(example_dir_candidates)}"
                ),
            })

        # Check 5: No package name extracted (medium — install recipe may fall back)
        if not bundle.repo_info.shared_facts.package_name:
            findings.append({
                "category": "scout_no_package_name",
                "severity": "medium",
                "message": (
                    "No package name extracted from any manifest file. "
                    "Install recipe generation will fall back to derivation heuristics."
                ),
            })

        # Check 6: High-rank files skipped by budget (TC-4236)
        if bundle.repo_info.important_files_skipped > 0:
            findings.append({
                "category": "scout_important_files_skipped",
                "severity": "medium",
                "message": (
                    f"Scout budget skipped {bundle.repo_info.important_files_skipped} "
                    f"high-rank file(s) (rank>=4). Check repo_info.skipped_paths for details."
                ),
            })

        # Check 7: TC-5189 — C# repo should have "dotnet" in build_systems
        if (
            bundle.repo_info.shared_facts.primary_language == "csharp"
            and "dotnet" not in bundle.repo_info.shared_facts.build_systems
        ):
            findings.append({
                "category": "scout_csharp_no_build_system",
                "severity": "medium",
                "message": (
                    "C# repo detected (primary_language='csharp') but 'dotnet' not "
                    "in build_systems. Expected .csproj detection to populate this."
                ),
            })

        # Check 8: Java repo should have "maven" or "gradle" in build_systems
        if (
            bundle.repo_info.shared_facts.primary_language == "java"
            and not {"maven", "gradle"} & set(bundle.repo_info.shared_facts.build_systems)
        ):
            findings.append({
                "category": "scout_java_no_build_system",
                "severity": "medium",
                "message": (
                    "Java repo detected (primary_language='java') but neither 'maven' "
                    "nor 'gradle' in build_systems."
                ),
            })

        # Metrics
        metrics["files_enumerated"] = len(bundle.repo_info.file_tree)
        metrics["files_read"] = bundle.repo_info.content_files_read
        metrics["primary_language"] = bundle.repo_info.shared_facts.primary_language
        metrics["package_name"] = bundle.repo_info.shared_facts.package_name
        metrics["budget_log_overflow"] = bundle.budget_log_overflow_count
        metrics["selected_doc_count"] = len(bundle.repo_info.doc_paths)
        metrics["selected_example_count"] = len(bundle.repo_info.example_paths)
        metrics["example_dir_candidate_count"] = len(example_dir_candidates)
        metrics["meta_doc_count"] = len(meta_docs)

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def create_worker() -> ScoutWorker:
    return ScoutWorker()
