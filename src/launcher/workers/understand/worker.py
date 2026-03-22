"""Understand worker — repo to verified facts to page plan.

Merges v1's W2 (FactsBuilder) + W3 (SnippetCurator) + W4 (IAPlanner) into
one worker with one internal phase:

  Phase B — Extract: sandwich claim extraction + AST code validation

Note: Cloning is handled by Intake (TC-3776).  File inventory and shared
facts are handled by Scout (TC-4075).  Understand receives a ScoutBundle.

TC-4076: UnderstandWorker now takes ScoutBundle as input instead of
IntakeBundle.  Phase A (Scout) has been extracted to ScoutWorker.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.scout import ScoutBundle
from launcher.models.product import ProductIdentity
from launcher.models.understanding import UnderstandingBundle
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult
logger = logging.getLogger(__name__)

_META_DOC_EXACT_NAMES: frozenset[str] = frozenset({
    "agents.md", "claude.md", "copilot-instructions.md", "llms.md",
})
_META_DOC_ROOT_KEYWORDS: frozenset[str] = frozenset({
    "readiness", "implementation", "summary", "status", "backlog",
    "roadmap", "plan", "notes",
})
_OPERATION_LABELS: frozenset[str] = frozenset({"load_file", "save_file", "convert", "create"})
_REAL_CODE_EVIDENCE_SNIPPET_CATEGORIES: frozenset[str] = frozenset({
    "example", "readme", "doc", "source", "other",
})
_CODE_EVIDENCE_SPARSE_THRESHOLD: int = 3


def _normalized_stem(rel_path: str) -> str:
    return Path(rel_path).stem.lower().replace("-", "").replace("_", "")


def _is_polluted_doc_source(rel_path: str) -> bool:
    lower = (rel_path or "").lower().replace("\\", "/")
    if not lower:
        return False
    name = Path(lower).name
    if name in _META_DOC_EXACT_NAMES:
        return True
    if "/" not in lower and _normalized_stem(lower) != "readme":
        return any(keyword in _normalized_stem(lower) for keyword in _META_DOC_ROOT_KEYWORDS)
    return False


def _snippet_source_category(source_file: str) -> str:
    lower = (source_file or "").lower().replace("\\", "/")
    parts = Path(lower).parts
    if _is_polluted_doc_source(source_file):
        return "meta_doc"
    if not lower:
        return "unknown"
    if Path(lower).name.startswith("readme"):
        return "readme"
    if any(part in {"examples", "example", "samples", "sample", "demo", "demos"} for part in parts):
        return "example"
    if any(part in {"tests", "test"} for part in parts):
        return "test"
    if any(part in {"docs", "doc", "documentation"} for part in parts):
        return "doc"
    if any(part in {"src", "launcher"} for part in parts):
        return "source"
    return "other"


def _collect_accessor_method_conflicts(api_surface: "Any") -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for brief in getattr(api_surface, "class_briefs", []) or []:
        method_names = {name for name in getattr(brief, "methods", []) or [] if name}
        property_names = {name for name in getattr(brief, "properties", []) or [] if name}
        overlap = sorted(method_names & property_names)
        if overlap:
            conflicts.append({"class_name": brief.name, "members": overlap})
    return conflicts


def _claim_source_metrics(claims: list) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for claim in claims:
        source = getattr(claim, "claim_source", "llm")
        counts[source] = counts.get(source, 0) + 1
    total = len(claims)
    docstring_count = counts.get("docstring", 0)
    llm_count = counts.get("llm", 0)
    deterministic_count = counts.get("deterministic", 0)
    return {
        "counts": counts,
        "total": total,
        "docstring_count": docstring_count,
        "docstring_fraction": (docstring_count / total) if total else 0.0,
        "llm_count": llm_count,
        "deterministic_count": deterministic_count,
        "non_docstring_count": total - docstring_count,
    }


def _count_non_test_code_snippets(snippets: list) -> int:
    count = 0
    for snippet in snippets or []:
        if getattr(snippet, "source_type", "extracted") == "synthetic":
            continue
        category = _snippet_source_category(getattr(snippet, "source_file", ""))
        if category in _REAL_CODE_EVIDENCE_SNIPPET_CATEGORIES:
            count += 1
    return count


def _compute_code_evidence_profile(repo_info: "Any", snippets: list) -> dict[str, int | bool]:
    example_file_count = len(getattr(repo_info, "example_paths", []) or [])
    non_test_snippet_count = _count_non_test_code_snippets(snippets)
    score = min(example_file_count, 10) + min(non_test_snippet_count, 10)
    return {
        "score": score,
        "example_file_count": example_file_count,
        "non_test_snippet_count": non_test_snippet_count,
        "sparse": score < _CODE_EVIDENCE_SPARSE_THRESHOLD,
    }


def _classify_richness_from_completeness(
    completeness: "ExtractionCompleteness",
    *,
    repo_info: "Any | None" = None,
    snippets: list | None = None,
) -> "RichnessResult":
    """Evidence-quality richness tier from ExtractionCompleteness.

    TC-4248: Replaces file-structure-based classify_richness_with_surface().
    Tier A requires rich, complete deterministic evidence — not just many files.

    Scoring formula (weights sum to 1.0):
      api_methods_score = min(api_method_count / 50, 1.0) * 0.30
      format_score      = min(format_count / 10, 1.0) * 0.20
      api_conf_score    = (1.0 if high, 0.5 if medium, 0.0 if low) * 0.20
      snippet_score     = min(snippet_count / 15, 1.0) * 0.15
      fmt_conf_score    = format_confidence_avg * 0.15

    Thresholds: total >= 0.70 → Tier A, >= 0.40 → Tier B, < 0.40 → Tier C
    Integer score = round(total * 100) for RichnessResult compatibility.
    """
    from launcher.models.understanding import ExtractionCompleteness as _EC  # noqa: F401
    from launcher.models.product import RichnessTier as _RT, RichnessResult as _RR

    api_methods_score = min(completeness.api_method_count / 50, 1.0) * 0.30
    format_score = min(completeness.format_count / 10, 1.0) * 0.20
    if completeness.api_confidence == "high":
        api_conf_score = 1.0 * 0.20
    elif completeness.api_confidence == "medium":
        api_conf_score = 0.5 * 0.20
    else:
        api_conf_score = 0.0
    snippet_score = min(completeness.snippet_count / 15, 1.0) * 0.15
    fmt_conf_score = completeness.format_confidence_avg * 0.15

    total = api_methods_score + format_score + api_conf_score + snippet_score + fmt_conf_score

    if total >= 0.70:
        tier = _RT.A
    elif total >= 0.40:
        tier = _RT.B
    else:
        tier = _RT.C

    int_score = round(total * 100)
    reasons = [
        f"api_methods={completeness.api_method_count}(+{api_methods_score:.2f})",
        f"formats={completeness.format_count}(+{format_score:.2f})",
        f"api_conf={completeness.api_confidence}(+{api_conf_score:.2f})",
        f"snippets={completeness.snippet_count}(+{snippet_score:.2f})",
        f"fmt_conf_avg={completeness.format_confidence_avg:.2f}(+{fmt_conf_score:.2f})",
    ]
    code_evidence_sparse = False
    if repo_info is not None:
        code_evidence = _compute_code_evidence_profile(repo_info, snippets or [])
        code_evidence_sparse = bool(code_evidence["sparse"])
        reasons.append(
            "code_evidence="
            f"{code_evidence['score']}"
            f"(example_files={code_evidence['example_file_count']},"
            f"non_test_snippets={code_evidence['non_test_snippet_count']},"
            f"sparse={code_evidence_sparse})"
        )
        if tier == _RT.A and code_evidence_sparse:
            tier = _RT.B
            reasons.append("tier_cap=lean_code_evidence")
    return _RR(
        tier=tier,
        score=int_score,
        reason="; ".join(reasons),
        code_evidence_sparse=code_evidence_sparse,
    )


def _compute_page_evidence_index(
    claims: "list",
    snippets: "list",
    extraction_db: "Any",
    product_evidence: "Any",
) -> "dict":
    """Compute per-page-role evidence sufficiency scores.

    TC-4249: Called after claim/snippet assembly. Signals to the Planner which
    page roles have sufficient evidence and which should be skipped or downgraded.
    """
    from launcher.models.understanding import PageEvidenceScore as _PES

    verified_claims = [
        c for c in claims
        if getattr(c, "confidence", 0.0) >= 0.75 and getattr(c, "visibility", "public") == "public"
    ]
    verified_count = len(verified_claims)
    api_verified = [c for c in verified_claims if getattr(c, "kind", "") == "api"]
    feature_verified = [
        c for c in verified_claims if getattr(c, "kind", "") in {"feature", "format", "config", "troubleshoot"}
    ]
    install_verified = [c for c in verified_claims if getattr(c, "kind", "") == "install"]
    non_docstring_verified = [
        c for c in verified_claims if getattr(c, "claim_source", "llm") != "docstring"
    ]

    snippet_facts = list(getattr(extraction_db, "snippet_facts", []) if extraction_db else [])
    operation_snippets = [
        s for s in snippet_facts
        if getattr(s, "operation_label", "") in _OPERATION_LABELS
    ]
    reviewable_operation_snippets = [
        s for s in operation_snippets
        if _snippet_source_category(getattr(s, "source_file", "")) in {"example", "test", "source"}
    ]
    has_op_snippets = bool(reviewable_operation_snippets)
    total_snippets = len(snippets)

    # Format evidence
    format_count = len(getattr(extraction_db, "format_facts", []) if extraction_db else [])
    api_fact_count = len(getattr(extraction_db, "api_facts", []) if extraction_db else [])
    api_class_fact_count = sum(
        1
        for fact in (getattr(extraction_db, "api_facts", []) if extraction_db else [])
        if getattr(fact, "member_type", "") == "class"
    )

    # Install recipe
    has_install = (
        product_evidence is not None
        and getattr(product_evidence, "install_recipe", None) is not None
    )

    index: dict = {}

    # _index (overview) — sufficient if any claims exist
    _missing: list[str] = []
    if verified_count < 3:
        _missing.append("no_verified_claims")
    if len(non_docstring_verified) == 0 and total_snippets == 0 and format_count == 0:
        _missing.append("docstring_only_mix")
    index["_index"] = _PES(
        page_role="_index",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=verified_count >= 3 and (
            len(non_docstring_verified) > 0 or total_snippets > 0 or format_count > 0
        ),
        missing=_missing,
    )

    # install_guide — sufficient when install_recipe present
    _missing = []
    if not has_install and not install_verified:
        _missing.append("no_install_recipe")
    index["install_guide"] = _PES(
        page_role="install_guide",
        claim_count=len(claims),
        verified_claim_count=len(install_verified),
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=has_install or len(install_verified) > 0,
        missing=_missing,
    )

    # api_reference — require direct API grounding, not just LLM/api-claim volume.
    # Lean repos often expose a strong AST surface with thin prose claims, so let
    # verified class facts satisfy the claim-side requirement when API facts are rich.
    _missing = []
    api_grounded_count = len(api_verified)
    if api_grounded_count == 0 and api_class_fact_count >= 3:
        api_grounded_count = min(api_class_fact_count, 5)
    if api_grounded_count < 3:
        _missing.append("no_verified_claims")
    if api_fact_count < 5:
        _missing.append("no_api_facts")
    index["api_reference"] = _PES(
        page_role="api_reference",
        claim_count=len(claims),
        verified_claim_count=api_grounded_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=api_grounded_count >= 3 and api_fact_count >= 5,
        missing=_missing,
    )

    # howto_article — require operational example/test evidence plus non-docstring support
    # BPW-01: Also require total_snippets >= 3 for code-heavy howto pages.
    _missing = []
    if not has_op_snippets:
        _missing.append("no_operation_examples")
    if len(non_docstring_verified) < 2 and len(api_verified) < 2:
        _missing.append("no_verified_claims")
    if total_snippets < 3:
        _missing.append("insufficient_snippets")
    index["howto_article"] = _PES(
        page_role="howto_article",
        claim_count=len(claims),
        verified_claim_count=len(non_docstring_verified),
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=(
            has_op_snippets
            and (len(non_docstring_verified) >= 2 or len(api_verified) >= 2)
            and total_snippets >= 3  # BPW-01
        ),
        missing=_missing,
    )

    # format_conversion — require format evidence plus operational example/test evidence
    _missing = []
    if format_count == 0:
        _missing.append("no_format_evidence")
    if not has_op_snippets:
        _missing.append("no_operation_examples")
    index["format_conversion"] = _PES(
        page_role="format_conversion",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=format_count > 0 and has_op_snippets,
        missing=_missing,
    )

    # feature_blog — require a broader feature/format mix, not docstring volume alone
    _missing = []
    if len(feature_verified) < 4:
        _missing.append("no_verified_claims")
    if len(non_docstring_verified) == 0 and format_count == 0 and total_snippets == 0:
        _missing.append("docstring_only_mix")
    index["feature_blog"] = _PES(
        page_role="feature_blog",
        claim_count=len(claims),
        verified_claim_count=len(feature_verified),
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=len(feature_verified) >= 4 and (
            len(non_docstring_verified) > 0 or format_count > 0 or total_snippets > 0
        ),
        missing=_missing,
    )

    return index


class UnderstandWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "understand"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> UnderstandingBundle:
        """Execute Phase B (Extract) using pre-built Scout inventory."""
        # TC-4076: Input is now ScoutBundle (not IntakeBundle).
        # ScoutBundle carries repo_info + all IntakeBundle identity fields.
        if isinstance(input_data, ScoutBundle):
            scout = input_data
        else:
            scout = ScoutBundle.model_validate(input_data.model_dump())

        repo_dir = Path(scout.repo_dir) if scout.repo_dir else None
        if not repo_dir or not repo_dir.is_dir():
            raise ValueError(
                f"[Understand] repo_dir does not exist: {scout.repo_dir!r}. "
                "Clone may have failed at Intake or the cached directory was deleted between runs."
            )
        product = ProductIdentity(
            family=scout.family,
            platform=scout.platform,
            display_name=scout.display_name,
            canonical_import=scout.canonical_import,
            runtime_import=scout.runtime_import,
            repo_url=scout.repo_url,
            repo_sha=scout.repo_sha,
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

        # -- Consume Scout output --------------------------------------------
        # TC-4076: repo_info comes from ScoutBundle, not from running run_scout().
        repo_info = scout.repo_info
        scout_budget_log = scout.budget_log
        scout_budget_log_overflow = scout.budget_log_overflow_count

        # repo_content: normally set by ScoutWorker on context.repo_content.
        # Resume fallback: if context is fresh (resume from Understand checkpoint),
        # re-read file content from disk using the file_index from ScoutBundle.
        repo_content = context.repo_content
        _stale_files_on_resume: int = 0
        if not repo_content and repo_info.file_index:
            context.log.info(
                "[Understand] Resume path: context.repo_content is empty — "
                "re-reading %d indexed files from disk",
                len(repo_info.file_index),
            )
            from launcher.workers.scout.scout import _read_repo_content
            repo_content, _, _, _, _, _, _ = _read_repo_content(repo_dir, repo_info.file_index)
            context.repo_content = repo_content
            # TC-4101: Check for files that were indexed by Scout but no longer exist on disk.
            # Stale content is not a hard failure (resume must be resilient) but must be visible.
            _stale_files_on_resume = sum(
                1 for p in repo_info.file_index
                if not (repo_dir / p).exists()
            )
            if _stale_files_on_resume > 0:
                context.log.warning(
                    "[Understand] Resume: %d/%d indexed files missing from disk — "
                    "content may be stale. Run from scratch to get accurate results.",
                    _stale_files_on_resume,
                    len(repo_info.file_index),
                )

        # Keep repo_dir alive for downstream workers
        context.repo_dir = repo_dir

        context.log.info(
            "[Understand] Scout inventory: %d files, %d read (%.1f KB), %d docs, %d examples",
            len(repo_info.file_tree),
            repo_info.content_files_read,
            repo_info.content_budget_used / 1024,
            len(repo_info.doc_paths),
            len(repo_info.example_paths),
        )

        # -- Phase B: Extract -------------------------------------------------
        context.log.info("[Understand] Phase B — Extract: claims + API surface")
        context.emit_event("worker_started", {"phase": "B_extract", "re_run_count": re_run_count}, worker=self.name)

        from launcher.workers.understand.extract import run_extract

        # TC-4244: run_extract now returns 5-tuple with ExtractionDatabase
        claims, snippets, api_surface, extract_evidence, extraction_db = await run_extract(
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

        # -- Richness classification (TC-4248: evidence-quality from ExtractionCompleteness) --
        richness = _classify_richness_from_completeness(
            extraction_db.completeness,
            repo_info=repo_info,
            snippets=snippets,
        )
        context.log.info("[Understand] Richness: Tier %s (score=%d)", richness.tier.value, richness.score)

        # -- Phase B.5: Repo-level evidence enrichment -----------------------
        # TC-4002: Merge extract-level evidence with repo-wide evidence.
        # Still call _extract_product_evidence for format/workflow/capability
        # data from code_analyzer, but install_recipe comes from extract pipeline.
        context.log.info("[Understand] Phase B.5 — Enrich: repo-wide evidence extraction")
        from launcher.models.understanding import ProductEvidence
        repo_evidence, b5_failed = await _extract_product_evidence(repo_dir, repo_info, product, context)
        # Merge: extract_evidence has limitations/workflows/install_recipe + format_matrix;
        # repo_evidence has fallback formats/conversion_pairs/capabilities.
        # TC-4040: prefer extract-level format lists (AST-verified) over repo-level (code_analyzer).
        # TC-4090 P2-D: additive dedup merge — repo_evidence extras not dropped when
        # extract_evidence is non-empty (fixed exclusive `or` which silently dropped extras).
        product_evidence = repo_evidence.model_copy(update={
            "limitations": extract_evidence.limitations,
            "workflow_examples": extract_evidence.workflow_examples,
            "install_recipe": extract_evidence.install_recipe or repo_evidence.install_recipe,
            "supported_formats": _merge_format_lists(
                extract_evidence.supported_formats, repo_evidence.supported_formats
            ),
            "input_formats": _merge_format_lists(
                extract_evidence.input_formats, repo_evidence.input_formats
            ),
            "output_formats": _merge_format_lists(
                extract_evidence.output_formats, repo_evidence.output_formats
            ),
        })

        # PH-02: Set format_evidence_source based on actual extraction outcome.
        # - "ast_verified": formats were found AND Phase B.5 succeeded (code_analyzer ran clean)
        # - "absent": no formats found anywhere (neither extract_evidence nor repo_evidence)
        # - "heuristic": formats present but B.5 failed (code_analyzer error → regex fallback)
        _has_formats = bool(
            product_evidence.supported_formats
            or product_evidence.input_formats
            or product_evidence.output_formats
        )
        if not _has_formats:
            _fmt_src = "absent"
        elif not b5_failed:
            _fmt_src = "ast_verified"
        else:
            _fmt_src = "heuristic"
        product_evidence = product_evidence.model_copy(update={"format_evidence_source": _fmt_src})

        # BPW-03: When no formats found via extraction or code_analyzer,
        # fall back to Scout's format_hints as low-confidence evidence.
        if _fmt_src == "absent" and repo_info.shared_facts and getattr(repo_info.shared_facts, "format_hints", None):
            _fallback_formats = sorted({h.upper() for h in repo_info.shared_facts.format_hints})
            if _fallback_formats:
                product_evidence = product_evidence.model_copy(update={
                    "supported_formats": _fallback_formats,
                    "format_evidence_source": "scout_hints",
                })
                context.log.info(
                    "[Understand] BPW-03: format_hints fallback -> %d formats from Scout",
                    len(_fallback_formats),
                )

        # -- Phase B.6: SEO keyword research -----------------------------------
        # TC-4086: SEO keyword research is run offline-only inside Understand as an interim
        # location. When Planner is ready to consume keyword data, this should move there.
        # Keyword research is content strategy, not repository truth-building.
        context.log.info("[Understand] Phase B.6 — SEO keyword research")
        import os
        from launcher.shared.keyword_research import research_keywords

        seo_config = getattr(context.config, "seo", None)
        # TC-4056 Fix 4: default to offline when no SEO config is present.
        # Network calls only happen when explicitly configured via seo.offline_mode=False.
        seo_offline = getattr(seo_config, "offline_mode", True) if seo_config else True
        if seo_offline:
            context.log.info(
                "[Understand] SEO offline — keyword bundle will be empty. "
                "This is expected in standard pipeline runs."
            )
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

        # -- Phase B.7: Per-page evidence sufficiency index (TC-4249) --------
        page_evidence_index = _compute_page_evidence_index(
            claims, snippets, extraction_db, product_evidence
        )
        context.log.info(
            "[Understand] page_evidence_index: sufficient=%s insufficient=%s",
            [r for r, s in page_evidence_index.items() if s.evidence_sufficient],
            [r for r, s in page_evidence_index.items() if not s.evidence_sufficient],
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
            extraction_db=extraction_db,  # TC-4244
            page_evidence_index=page_evidence_index,  # TC-4249
        )

        try:
            skip_reason_counts: dict[str, int] = {}
            for entry in scout_budget_log:
                reason = entry.get("reason", "unknown")
                skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
            context.store.write_json("scout_consumption_audit.json", {
                "files_enumerated": len(repo_info.file_tree),
                "files_read": repo_info.content_files_read,
                "content_used_bytes": repo_info.content_budget_used,
                "budget_log_overflow_count": scout_budget_log_overflow,
                "stale_files_on_resume": _stale_files_on_resume,
                "skip_reason_counts": skip_reason_counts,
                "phase_b5_failed": b5_failed,
            })
            context.log.info("[Understand] scout_consumption_audit.json written")
        except Exception:
            context.log.warning("[Understand] Failed to write scout_consumption_audit.json", exc_info=True)

        try:
            claim_mix = _claim_source_metrics(claims)
            synthetic_count = sum(
                1 for s in snippets if getattr(s, "source_type", "extracted") == "synthetic"
            )
            orphaned_snippets = [s for s in snippets if not getattr(s, "claim_ids", None)]
            orphaned_snippet_count = len(orphaned_snippets)
            polluted_sources = sorted({
                getattr(s, "source_file", "")
                for s in snippets
                if _is_polluted_doc_source(getattr(s, "source_file", ""))
            })
            snippet_source_breakdown: dict[str, int] = {}
            for snippet in snippets:
                category = _snippet_source_category(getattr(snippet, "source_file", ""))
                snippet_source_breakdown[category] = snippet_source_breakdown.get(category, 0) + 1
            workflow_examples = list(
                getattr(getattr(bundle, "product_evidence", None), "workflow_examples", []) or []
            )
            workflow_source_breakdown: dict[str, int] = {}
            for example in workflow_examples:
                category = _snippet_source_category(getattr(example, "source_file", ""))
                workflow_source_breakdown[category] = workflow_source_breakdown.get(category, 0) + 1
            code_evidence = _compute_code_evidence_profile(repo_info, snippets)
            accessor_conflicts = _collect_accessor_method_conflicts(api_surface)

            _total_claims = claim_mix["total"]
            _low_conf_claims = sum(
                1 for c in claims if getattr(c, 'confidence', 1.0) < 0.5
            )
            _estimated_hallucination_rate = (
                _low_conf_claims / _total_claims if _total_claims > 0 else 0.0
            )
            _llm_fallback_count_audit = sum(
                1 for c in claims if getattr(c, 'claim_source', 'llm') == 'llm_fallback'
            )
            _llm_fallback_rate_audit = (
                _llm_fallback_count_audit / _total_claims if _total_claims > 0 else 0.0
            )

            # Build confidence distribution
            _conf_dist: dict[str, int] = {
                "1.0": 0, "0.75": 0, "0.5": 0, "0.35": 0, "other": 0
            }
            for _c in claims:
                _cv = str(round(getattr(_c, 'confidence', 1.0), 2))
                if _cv in _conf_dist:
                    _conf_dist[_cv] += 1
                else:
                    _conf_dist["other"] += 1

            extraction_audit = {
                "claim_count": len(claims),
                "snippet_count": len(snippets),
                "synthetic_snippet_count": synthetic_count,
                "orphaned_snippet_count": orphaned_snippet_count,
                "orphaned_snippet_rate": round(orphaned_snippet_count / max(len(snippets), 1), 4),
                "orphaned_snippet_sources": [
                    {
                        "source_file": getattr(snippet, "source_file", ""),
                        "language": getattr(snippet, "language", ""),
                    }
                    for snippet in orphaned_snippets[:20]
                ],
                "snippet_source_files": sorted({
                    getattr(snippet, "source_file", "")
                    for snippet in snippets if getattr(snippet, "source_file", "")
                }),
                "snippet_source_breakdown": snippet_source_breakdown,
                "polluted_snippet_sources": polluted_sources,
                "claim_provenance_counts": claim_mix["counts"],
                "docstring_saturation": {
                    "docstring_claim_count": claim_mix["docstring_count"],
                    "non_docstring_claim_count": claim_mix["non_docstring_count"],
                    "docstring_fraction": round(claim_mix["docstring_fraction"], 4),
                },
                "accessor_method_conflicts": {
                    "count": len(accessor_conflicts),
                    "samples": accessor_conflicts[:20],
                },
                "richness_tier": richness.tier.value,
                "richness_score": richness.score,
                "code_evidence_sparse": richness.code_evidence_sparse,
                "code_evidence_score": code_evidence["score"],
                "non_test_snippet_count": code_evidence["non_test_snippet_count"],
                "api_surface_confidence": api_surface.confidence,
                "public_class_count": len(api_surface.public_classes),
                "workflow_example_count": len(workflow_examples),
                "workflow_example_source_breakdown": workflow_source_breakdown,
                "page_evidence_index": {
                    role: score.model_dump(mode="json")
                    for role, score in page_evidence_index.items()
                },
                "review_artifacts": {
                    "full_artifact": "understanding_bundle.json",
                    "summary_artifact": "understanding_summary.json",
                },
                "hallucination_metrics": {
                    "llm_fallback_rate": round(_llm_fallback_rate_audit, 4),
                    "unverified_api_claims_dropped": 0,  # updated if TC-HAL-04 ran
                    "confidence_distribution": _conf_dist,
                    "estimated_hallucination_rate": round(_estimated_hallucination_rate, 4),
                    "low_confidence_claim_count": _low_conf_claims,
                    "total_claim_count": _total_claims,
                },
                "dropped_claims_log": context.claim_drop_log,
            }
            context.store.write_json("extraction_audit.json", extraction_audit)
            context.log.info("[Understand] extraction_audit.json written")
            context.store.write_json(
                "understanding_bundle.json",
                bundle.model_dump(mode="json"),
            )
            context.log.info("[Understand] understanding_bundle.json full artifact written")
            understanding_summary = {
                "run_id": context.run_id,
                "family": product.family,
                "platform": product.platform,
                "claims": len(claims),
                "snippets": len(snippets),
                "limitations": len(extract_evidence.limitations),
                "install_recipe": (
                    extract_evidence.install_recipe.install_command
                    if extract_evidence.install_recipe else None
                ),
                "format_matrix_count": len(product_evidence.supported_formats),
                "class_briefs_count": len(api_surface.class_briefs),
                "typed_methods_classes": sum(
                    1 for b in api_surface.class_briefs if b.typed_methods
                ),
                "richness_tier": richness.tier.value,
                "code_evidence_sparse": richness.code_evidence_sparse,
                "api_confidence": api_surface.confidence,
                "docstring_claim_fraction": round(claim_mix["docstring_fraction"], 4),
                "orphaned_snippet_count": orphaned_snippet_count,
                "polluted_snippet_sources": polluted_sources,
                "workflow_example_count": len(workflow_examples),
                "missing_info": len(extract_evidence.missing_info) if hasattr(extract_evidence, "missing_info") else 0,
            }
            context.store.write_json("understanding_summary.json", understanding_summary)
            context.log.info("[Understand] understanding_summary.json written")
        except Exception:
            context.log.warning("[Understand] Failed to write extraction_audit.json", exc_info=True)

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

        TC-4056 Fix 2: Added high-severity checks so self_review actually fails
        when the bundle is semantically empty or AST extraction broke silently.

        TC-4058: Added medium-severity check when product_evidence is entirely empty
        (suggests Phase B.5 code_analyzer failed silently or found nothing substantive).
        """
        if not isinstance(output, UnderstandingBundle):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not UnderstandingBundle"}])

        bundle = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}
        claim_mix = _claim_source_metrics(bundle.claims)
        polluted_sources = sorted({
            getattr(s, "source_file", "")
            for s in bundle.snippets
            if _is_polluted_doc_source(getattr(s, "source_file", ""))
        })
        workflow_examples = list(
            getattr(getattr(bundle, "product_evidence", None), "workflow_examples", []) or []
        )
        workflow_source_breakdown: dict[str, int] = {}
        for example in workflow_examples:
            category = _snippet_source_category(getattr(example, "source_file", ""))
            workflow_source_breakdown[category] = workflow_source_breakdown.get(category, 0) + 1
        accessor_conflicts = _collect_accessor_method_conflicts(bundle.api_surface)

        # Check 1: Internal claims count (informational, not blocking)
        internal_claims = [c for c in bundle.claims if c.visibility != "public"]
        if internal_claims:
            metrics["internal_claims_filtered"] = len(internal_claims)

        # TC-4056 Fix 2a: Zero claims is a hard failure — the phase produced no evidence.
        if len(bundle.claims) == 0:
            findings.append({
                "category": "claims_empty",
                "message": "No claims extracted — Understand produced empty evidence. "
                           "LLM extraction failed and deterministic fallback found nothing.",
                "severity": "high",
            })

        # TC-4061: Platform-neutral api_surface check — fires for all platforms.
        # Python (or unknown) AST extraction is deterministic → high severity on failure.
        # Non-Python heuristics may legitimately yield lower confidence → medium severity.
        primary_lang = bundle.repo.shared_facts.primary_language.lower()
        _is_python = primary_lang in ("python", "")  # "" = unknown, treat as Python
        _api_severity = "high" if _is_python else "medium"
        if len(bundle.api_surface.public_classes) == 0:
            # TC-4085: Differentiated diagnostic for non-Python vs Python.
            if _is_python:
                _api_empty_msg = (
                    f"api_surface has no public classes for a {primary_lang or 'unknown'} repo — "
                    "package root detection or AST/regex extraction may have failed."
                )
            else:
                _ts_available = False
                try:
                    import tree_sitter  # noqa: F401
                    _ts_available = True
                except ImportError:
                    pass
                if not _ts_available:
                    _api_empty_msg = (
                        f"api_surface has no public classes for {primary_lang or 'unknown'} repo. "
                        "tree-sitter is not installed — run: "
                        f"pip install tree-sitter tree-sitter-{primary_lang or 'unknown'}"
                    )
                else:
                    _api_empty_msg = (
                        f"api_surface has no public classes for {primary_lang or 'unknown'} repo "
                        "despite tree-sitter being available. Package root detection or import "
                        "filter may have failed. Check extraction_audit.json."
                    )
            findings.append({
                "category": "api_surface_empty",
                "message": _api_empty_msg,
                "severity": _api_severity,
            })
        if bundle.api_surface.confidence == "low":
            findings.append({
                "category": "api_surface_low_confidence",
                "message": (
                    f"api_surface confidence is 'low' for a {primary_lang or 'unknown'} repo — "
                    "package root was not detected."
                ),
                "severity": _api_severity,
            })

        # TC-4083: Thin API surface for Python repos — medium, informative, not blocking.
        # Fires when exactly 1 class found (0 classes covered by api_surface_empty above).
        _public_class_count = len(bundle.api_surface.public_classes)
        if _is_python and 0 < _public_class_count <= 1:
            findings.append({
                "category": "thin_api_surface",
                "message": (
                    f"Only {_public_class_count} public class(es) found for a Python repo. "
                    "Package root detection may be incomplete (e.g. namespace packages). "
                    "Check extraction_audit.json → public_class_count. "
                    "Ensure runtime_import is set in families.yaml for this product."
                ),
                "severity": "medium",
            })

        # TC-4083: Low claim count when API surface is non-empty — medium, not blocking.
        if _public_class_count > 0 and len(bundle.claims) < 10:
            findings.append({
                "category": "low_claim_count",
                "message": (
                    f"Claim count is low ({len(bundle.claims)}) for a repo with "
                    f"{_public_class_count} public API class(es). "
                    "Evidence context may be thin or LLM extraction returned 0 claims. "
                    "Check extraction_audit.json → claim_provenance_counts."
                ),
                "severity": "medium",
            })

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

        # TC-4056 Fix 8: Warn when >50% of snippets are synthetic (medium, not blocking).
        total_snippets = len(bundle.snippets)
        synthetic_count = sum(
            1 for s in bundle.snippets
            if getattr(s, "source_type", "extracted") == "synthetic"
        )
        if total_snippets > 0 and synthetic_count / total_snippets > 0.5:
            findings.append({
                "category": "synthetic_snippets_dominant",
                "message": (
                    f"Synthetic snippets are {synthetic_count}/{total_snippets} "
                    f"({100 * synthetic_count // total_snippets}%) of all snippets. "
                    "These are template-generated and may have wrong method signatures."
                ),
                "severity": "medium",
            })

        if polluted_sources:
            findings.append({
                "category": "polluted_snippet_sources",
                "message": (
                    "Snippet evidence includes operator/meta documentation sources: "
                    f"{', '.join(polluted_sources[:5])}"
                ),
                "severity": "high",
            })

        if accessor_conflicts:
            findings.append({
                "category": "accessor_method_confusion",
                "message": (
                    f"{len(accessor_conflicts)} class brief(s) expose the same member as both "
                    "method and property. Property setters/accessors are leaking into callable API."
                ),
                "severity": "high",
            })

        if (
            workflow_source_breakdown.get("test", 0) > 0
            and sum(workflow_source_breakdown.values()) == workflow_source_breakdown.get("test", 0)
            and not getattr(bundle.repo, "example_paths", [])
        ):
            findings.append({
                "category": "test_only_workflow_examples",
                "message": (
                    "workflow_examples are sourced only from test files while the repo has "
                    "no retained example paths. This inflates lean-repo confidence and "
                    "pollutes generation prompts with assertion-heavy usage."
                ),
                "severity": "high",
            })

        # UND-05: Tightened from 40/0.85 to 30/0.60 to catch docstring flooding earlier
        if claim_mix["docstring_count"] >= 30 and claim_mix["docstring_fraction"] >= 0.60:
            findings.append({
                "category": "docstring_claim_saturation",
                "message": (
                    f"Docstring claims dominate the evidence mix "
                    f"({claim_mix['docstring_count']}/{claim_mix['total']} = "
                    f"{claim_mix['docstring_fraction']:.2f}). "
                    "High-signal non-docstring evidence is being drowned out."
                ),
                "severity": "high",
            })
        elif claim_mix["docstring_count"] >= 20 and claim_mix["docstring_fraction"] >= 0.65:
            findings.append({
                "category": "docstring_claim_saturation",
                "message": (
                    f"Docstring claims are the majority of evidence "
                    f"({claim_mix['docstring_count']}/{claim_mix['total']})."
                ),
                "severity": "medium",
            })

        # -- TC-B06: Semantic thresholds ------------------------------------------
        from launcher.models.product import RichnessTier as _RT

        # Check 3: Tier A minimum claim count
        if bundle.richness_tier.tier == _RT.A and len(bundle.claims) < 5:
            findings.append({
                "category": "claims",
                "message": (
                    f"Tier A bundle has only {len(bundle.claims)} claims "
                    "(minimum 5 required for Tier A)"
                ),
                "severity": "high",
            })

        # Check 4: No snippets despite non-empty API surface
        if (
            not bundle.snippets
            and bundle.api_surface is not None
            and len(bundle.api_surface.public_classes) > 0
        ):
            findings.append({
                "category": "snippets",
                "message": (
                    f"No snippets produced for bundle with "
                    f"{len(bundle.api_surface.public_classes)} public API classes"
                ),
                "severity": "high",
            })

        # Check 5: Most claims are deterministic fallback (warning, not blocking)
        if bundle.claims:
            llm_count = sum(
                1 for c in bundle.claims
                if getattr(c, "claim_source", "llm") in ("llm", "docstring")
            )
            if llm_count < len(bundle.claims) * 0.3:
                findings.append({
                    "category": "claims",
                    "message": (
                        f"Only {llm_count}/{len(bundle.claims)} claims from LLM/docstring sources "
                        "(most are deterministic fallback) — verify LLM is reachable"
                    ),
                    "severity": "warning",
                })

        # TC-4058: Check 6 — ProductEvidence is entirely empty.
        # When Phase B.5 code_analyzer fails or finds nothing, all evidence fields stay empty.
        # This is medium severity: it doesn't block the pipeline but signals that the
        # capabilities/formats section may be thin or wrong in generated content.
        if bundle.product_evidence is not None:
            pe = bundle.product_evidence
            _evidence_empty = (
                not pe.supported_formats
                and not pe.capabilities
                and not pe.limitations
                and pe.install_recipe is None
            )
            if _evidence_empty:
                findings.append({
                    "category": "product_evidence_empty",
                    "message": (
                        "product_evidence has no formats, capabilities, limitations, or install "
                        "recipe. Phase B.5 code_analyzer may have failed or repo has no "
                        "detectable format/capability signals. Check extraction_audit.json."
                    ),
                    "severity": "medium",
                })

        # TC-4090 P2-H: Check 7 — Orphaned snippets (claim_ids == [])
        # Snippets without linked claims indicate snippet extraction found code blocks
        # that couldn't be matched to any confirmed claim — a structural data quality issue.
        orphaned_snippets = [s for s in bundle.snippets if not getattr(s, "claim_ids", None)]
        orphaned_count = len(orphaned_snippets)
        if orphaned_count > 0:
            orphaned_fraction = orphaned_count / max(total_snippets, 1)
            if orphaned_fraction >= 0.4 or orphaned_count >= 3:
                _orphan_severity = "high"
            elif orphaned_fraction > 0.2:
                _orphan_severity = "medium"
            else:
                _orphan_severity = "low"
            findings.append({
                "category": "orphaned_snippets",
                "message": (
                    f"{orphaned_count}/{total_snippets} snippets have no linked claims "
                    f"(orphaned_fraction={orphaned_fraction:.2f}). "
                    "Snippet→claim linking may have failed for these code blocks."
                ),
                "severity": _orphan_severity,
            })
            logger.warning(
                "[Understand] self_review: %d/%d snippets are orphaned (no claim_ids) — severity=%s",
                orphaned_count, total_snippets, _orphan_severity,
            )

        if len(bundle.repo.example_paths) >= 10:
            howto_score = bundle.page_evidence_index.get("howto_article")
            format_score = bundle.page_evidence_index.get("format_conversion")
            if (
                (howto_score is None or not howto_score.evidence_sufficient)
                and (format_score is None or not format_score.evidence_sufficient)
            ):
                findings.append({
                    "category": "example_evidence_underused",
                    "message": (
                        f"Repo has {len(bundle.repo.example_paths)} retained example files, "
                        "but Understand did not produce sufficient how-to or format-conversion evidence."
                    ),
                    "severity": "high",
                })

        # Metrics
        metrics["total_claims"] = len(bundle.claims)
        metrics["total_snippets"] = total_snippets
        metrics["orphaned_snippets"] = orphaned_count
        metrics["synthetic_snippets"] = synthetic_count
        metrics["docstring_claim_count"] = claim_mix["docstring_count"]
        metrics["docstring_claim_fraction"] = round(claim_mix["docstring_fraction"], 4)
        metrics["polluted_snippet_sources"] = polluted_sources
        metrics["workflow_example_source_breakdown"] = workflow_source_breakdown
        metrics["accessor_method_conflicts"] = len(accessor_conflicts)
        metrics["tier"] = bundle.richness_tier.tier.value
        metrics["code_evidence_sparse"] = bundle.richness_tier.code_evidence_sparse
        metrics["bad_snippets"] = bad_snippets
        metrics["skipped_paths_count"] = len(bundle.repo.skipped_paths) if hasattr(bundle.repo, "skipped_paths") else 0
        metrics["product_evidence_empty"] = (
            bundle.product_evidence is not None
            and not bundle.product_evidence.supported_formats
            and not bundle.product_evidence.capabilities
            and not bundle.product_evidence.limitations
            and bundle.product_evidence.install_recipe is None
        )

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def _merge_format_lists(primary: list[str], fallback: list[str]) -> list[str]:
    """Merge two format lists, deduplicating case-insensitively.

    TC-4090 P2-D: Replaces the exclusive `or` merge which silently dropped
    repo_evidence extras when extract_evidence was non-empty.

    primary (extract_evidence) takes precedence for ordering. Items in fallback
    that are not already in primary (case-insensitive) are appended at the end.
    """
    seen_upper = {f.upper() for f in primary}
    extras = [f for f in fallback if f.upper() not in seen_upper]
    return list(primary) + extras


async def _extract_product_evidence(
    repo_dir: Path,
    repo_info,
    product: ProductIdentity,
    context: WorkerContext,
) -> "tuple[ProductEvidence, bool]":
    """Phase B.5: Extract product evidence via build_repo_truth.

    TC-4058: Returns (evidence, failed_flag).
    - ImportError / ModuleNotFoundError: propagate immediately (broken installation = hard stop).
    - All other exceptions: log at ERROR level (not WARNING) and return empty evidence
      with failed=True so the artifact and self_review can surface the gap.

    Returns (ProductEvidence, failed: bool)
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

        # TC-4030: Build manifest_data from SharedFacts (cached by Scout in Phase A)
        # instead of re-reading pyproject.toml from disk.
        sf = repo_info.shared_facts
        manifest_data: dict = {
            "name": sf.package_name or None,
            "version": sf.version or None,
            "description": sf.description or None,
            "python_requires": sf.python_requires or None,
            "dependencies": sf.dependencies,
            "entrypoints": sf.entrypoints,
        }

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
                    "[Understand] InstallRecipe: install_command=%s", _recipe.install_command,
                )
        except Exception:
            context.log.debug("[Understand] extract_install_recipe skipped", exc_info=True)

        return evidence, False

    except (ImportError, ModuleNotFoundError):
        # TC-4058: Import failures mean the installation is broken — let them propagate.
        # Swallowing an ImportError would hide a broken code_analyzer module permanently.
        raise

    except Exception:
        # TC-4058: Analysis-level failures: log at ERROR (was WARNING before) so they are
        # visible in monitoring. Return empty evidence with failed=True so the artifact
        # and self_review can surface the gap without blocking the pipeline.
        # SR-05: Include family/platform/repo_url so the log entry can be correlated to
        # a specific product without reading surrounding context.
        context.log.error(
            "[Understand] Phase B.5 code_analyzer failed for %s/%s (repo=%s) — "
            "returning empty ProductEvidence. Downstream generate may lack capability/format signals.",
            product.family,
            product.platform,
            getattr(product, "repo_url", "unknown"),
            exc_info=True,
        )
        return ProductEvidence(), True


def create_worker() -> UnderstandWorker:
    return UnderstandWorker()
