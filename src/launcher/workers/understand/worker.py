"""Understand worker — repo to verified facts to page plan.

Merges v1's W1 (RepoScout) + W2 (FactsBuilder) + W3 (SnippetCurator) +
W4 (IAPlanner) into one worker with 2 internal phases:

  Phase A — Scout:   fingerprint files, read content, extract facts
  Phase B — Extract: sandwich claim extraction + AST code validation

Note: Cloning is handled by Intake (TC-3776). Scout receives repo_dir.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.intake import IntakeBundle
from launcher.models.product import ProductIdentity
from launcher.models.understanding import UnderstandingBundle
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult
from launcher.shared.surface_classifier import classify_richness_with_surface

logger = logging.getLogger(__name__)


class UnderstandWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "understand"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> UnderstandingBundle:
        """Execute phases A and B sequentially."""
        # Resolve input from IntakeBundle
        if isinstance(input_data, IntakeBundle):
            intake = input_data
        else:
            intake = IntakeBundle.model_validate(input_data.model_dump())

        repo_dir = Path(intake.repo_dir) if intake.repo_dir else None
        if not repo_dir or not repo_dir.is_dir():
            raise ValueError(
                f"[Understand] repo_dir does not exist: {intake.repo_dir!r}. "
                "Clone may have failed at Intake or the cached directory was deleted between runs."
            )
        product = ProductIdentity(
            family=intake.family,
            platform=intake.platform,
            display_name=intake.display_name,
            canonical_import=intake.canonical_import,
            runtime_import=getattr(intake, "runtime_import", ""),
            repo_url=intake.repo_url,
            repo_sha=intake.repo_sha,
        )

        # Heal mode: read directives from heal_metadata if present
        heal_metadata: dict = context.heal_metadata or {}
        re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
        if re_run_count > 0:
            context.log.info(
                "[Understand] Heal mode (re_run=%d): tightening extraction focus",
                re_run_count,
            )
            context.emit_event(
                "understand_heal_mode",
                {
                    "re_run_count": re_run_count,
                    "focus_page_roles": heal_metadata.get("focus_page_roles", []),
                    "page_directives": heal_metadata.get("page_directives", []),
                },
                worker=self.name,
            )

        # -- Phase A: Scout --------------------------------------------------
        context.log.info("[Understand] Phase A — Scout: fingerprinting %s", repo_dir)
        context.emit_event("worker_started", {"phase": "A_scout"}, worker=self.name)

        from launcher.workers.understand.scout import run_scout

        repo_info, repo_content = await run_scout(repo_dir)

        # Keep repo_dir and content alive for downstream workers
        context.repo_dir = repo_dir
        context.repo_content = repo_content

        context.log.info(
            "[Understand] Scout complete: %d files, %d read (%.1f KB), %d docs, %d examples",
            len(repo_info.file_tree),
            repo_info.content_files_read,
            repo_info.content_budget_used / 1024,
            len(repo_info.doc_paths),
            len(repo_info.example_paths),
        )

        # -- Phase B: Extract -------------------------------------------------
        context.log.info("[Understand] Phase B — Extract: claims + API surface")
        context.emit_event("worker_started", {"phase": "B_extract"}, worker=self.name)

        from launcher.workers.understand.extract import run_extract

        # TC-4002: run_extract now returns 4-tuple with ProductEvidence
        claims, snippets, api_surface, extract_evidence = await run_extract(
            product, repo_info, repo_dir, context,
        )

        context.log.info(
            "[Understand] Extract complete: %d claims, %d snippets, %d public classes, "
            "%d limitations, %d workflows",
            len(claims),
            len(snippets),
            len(api_surface.public_classes),
            len(extract_evidence.limitations),
            len(extract_evidence.workflow_examples),
        )

        # -- Richness classification (uses repo_info + api_surface + snippets) --
        extracted_snippet_count = sum(
            1 for s in snippets if getattr(s, "source_type", "extracted") == "extracted"
        )
        richness = classify_richness_with_surface(
            repo_info,
            api_confidence=api_surface.confidence,
            public_class_count=len(api_surface.public_classes),
            extracted_snippet_count=extracted_snippet_count,
        )
        context.log.info("[Understand] Richness: Tier %s (score=%d)", richness.tier.value, richness.score)

        # -- Phase B.5: Repo-level evidence enrichment -----------------------
        # TC-4002: Merge extract-level evidence with repo-wide evidence.
        # Still call _extract_product_evidence for format/workflow/capability
        # data from code_analyzer, but install_recipe comes from extract pipeline.
        context.log.info("[Understand] Phase B.5 — Enrich: repo-wide evidence extraction")
        from launcher.models.understanding import ProductEvidence
        repo_evidence = await _extract_product_evidence(repo_dir, repo_info, product, context)
        # Merge: extract_evidence has limitations/workflows/install_recipe;
        # repo_evidence has formats/conversion_pairs/capabilities
        product_evidence = repo_evidence.model_copy(update={
            "limitations": extract_evidence.limitations,
            "workflow_examples": extract_evidence.workflow_examples,
            "install_recipe": extract_evidence.install_recipe or repo_evidence.install_recipe,
        })

        # -- Phase B.6: SEO keyword research -----------------------------------
        context.log.info("[Understand] Phase B.6 — SEO keyword research")
        import os
        from launcher.shared.keyword_research import research_keywords

        seo_config = getattr(context.config, "seo", None)
        seo_offline = getattr(seo_config, "offline_mode", False) if seo_config else False
        keyword_bundle = research_keywords(
            product_name=product.display_name,
            family=product.family,
            platform=product.platform,
            claims=claims,
            cache_root=context.run_dir.parent / ".seo_cache",
            offline=seo_offline,
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        )
        context.log.info(
            "[Understand] SEO keywords: %d primary, %d long-tail, gemini=%s",
            len(keyword_bundle.primary_keywords),
            len(keyword_bundle.long_tail),
            keyword_bundle.gemini_available,
        )

        # -- Assemble output bundle -------------------------------------------
        bundle = UnderstandingBundle(
            product=product,
            repo=repo_info,
            richness_tier=richness,
            api_surface=api_surface,
            claims=claims,
            snippets=snippets,
            product_evidence=product_evidence,
            keyword_research=keyword_bundle,
        )

        context.emit_event(
            "worker_completed",
            {
                "claims": len(claims),
                "snippets": len(snippets),
                "tier": richness.tier.value,
            },
            worker=self.name,
        )

        return bundle

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Semantic self-review of the understanding bundle.

        Checks (Rule 1):
        - All claims have visibility='public'
        - All snippets are syntactically valid Python (if applicable)
        """
        if not isinstance(output, UnderstandingBundle):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not UnderstandingBundle"}])

        bundle = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}

        # Check 1: Internal claims count (informational, not blocking)
        internal_claims = [c for c in bundle.claims if c.visibility != "public"]
        if internal_claims:
            metrics["internal_claims_filtered"] = len(internal_claims)

        # Check 2: Snippet syntax (all languages)
        bad_snippets = 0
        for i, snippet in enumerate(bundle.snippets):
            is_valid = True
            if snippet.language == "python":
                try:
                    import ast
                    ast.parse(snippet.code)
                except SyntaxError:
                    is_valid = False
            else:
                try:
                    from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
                    is_valid = _ts_analyzer.validate_snippet(snippet.code, snippet.language)
                except ImportError:
                    pass  # tree-sitter not available — skip validation
            if not is_valid:
                bad_snippets += 1
                findings.append({
                    "category": "code_syntax",
                    "message": f"Snippet {i} has invalid {snippet.language} syntax",
                    "severity": "medium",
                })

        # Metrics
        metrics["total_claims"] = len(bundle.claims)
        metrics["total_snippets"] = len(bundle.snippets)
        metrics["tier"] = bundle.richness_tier.tier.value
        metrics["bad_snippets"] = bad_snippets

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


async def _extract_product_evidence(
    repo_dir: Path,
    repo_info,
    product: ProductIdentity,
    context: WorkerContext,
) -> "ProductEvidence":
    """Phase B.5: Extract product evidence via build_repo_truth.

    Returns empty ProductEvidence on any failure (never blocks pipeline).
    """
    from launcher.models.understanding import ProductEvidence
    try:
        from launcher.shared.code_analyzer import (
            analyze_repository_code,
            build_repo_truth,
            detect_source_roots,
        )

        # Build repo_inventory (not actually used by analyze_repository_code
        # but required by its signature)
        repo_inventory = {
            "source_files": repo_info.source_paths,
            "doc_files": repo_info.doc_paths,
            "example_files": repo_info.example_paths,
        }

        code_analysis = analyze_repository_code(
            repo_dir, repo_inventory, product.display_name,
        )

        # Build manifest_data from code_analysis internals
        # analyze_repository_code already parsed manifests; we need to
        # replicate minimal manifest data for build_repo_truth
        from launcher.shared.code_analyzer import discover_manifests, parse_pyproject_toml
        manifest_data: dict = {}
        manifests = discover_manifests(repo_dir)
        for mp in manifests:
            if mp.name == "pyproject.toml":
                manifest_data = parse_pyproject_toml(mp)
                break

        source_roots = detect_source_roots(repo_dir)

        repo_truth = build_repo_truth(
            repo_dir, manifest_data, code_analysis, source_roots,
        )

        evidence = ProductEvidence(
            supported_formats=repo_truth.get("supported_formats", {}).get("values", []),
            input_formats=repo_truth.get("input_formats", {}).get("values", []),
            output_formats=repo_truth.get("output_formats", {}).get("values", []),
            conversion_pairs=repo_truth.get("conversion_pairs", {}).get("values", []),
            workflows=repo_truth.get("workflows", {}).get("values", []),
            capabilities=repo_truth.get("capabilities", {}).get("values", []),
        )

        context.log.info(
            "[Understand] ProductEvidence: %d formats, %d conversion_pairs, %d workflows",
            len(evidence.supported_formats),
            len(evidence.conversion_pairs),
            len(evidence.workflows),
        )

        # TC-HYBRID-04: extract install recipe deterministically
        try:
            from launcher.workers.understand.extract._deterministic import (
                extract_install_recipe as _extract_recipe,
            )
            _recipe = _extract_recipe(repo_dir, product)
            if _recipe:
                evidence = evidence.model_copy(update={"install_recipe": _recipe})
                context.log.info(
                    "[Understand] InstallRecipe: pip_command=%s", _recipe.pip_command,
                )
        except Exception:
            context.log.debug("[Understand] extract_install_recipe skipped", exc_info=True)

        return evidence

    except Exception:
        context.log.warning(
            "[Understand] Phase B.5 failed; returning empty ProductEvidence",
            exc_info=True,
        )
        return ProductEvidence()


def create_worker() -> UnderstandWorker:
    return UnderstandWorker()
