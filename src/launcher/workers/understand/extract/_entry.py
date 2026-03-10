"""Phase B — Extract: main entry point orchestrator.

Contains:
  run_extract()                  — public W2 entry point (sandwich model)
  _harvest_docstring_claims_raw  — docstring→claim raw dict harvesting (TC-3816)
  _generate_synthetic_snippets   — template-based snippet synthesis (TC-3816)

Spec references:
- specs/03_product_facts_and_evidence.md  (Claims extraction algorithm)
- specs/04_claims_compiler_truth_lock.md  (Claim structure and ID generation)
- specs/07_code_analysis_and_enrichment.md (API surface extraction)
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ApiSurface, ProductIdentity
from launcher.models.understanding import ProductEvidence, RepoInfo
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.understand.extract._api_surface import _extract_api_surface
from launcher.workers.understand.extract._llm import _extract_claims_llm
from launcher.workers.understand.extract._snippets import _build_doc_contexts, _extract_snippets, _build_embedding_index
from launcher.workers.understand.extract._validation import _validate_and_normalize_claims, _filter_contaminated_claims

logger = logging.getLogger(__name__)


# ===================================================================
# Public entry point
# ===================================================================


async def run_extract(
    product: ProductIdentity,
    repo_info: RepoInfo,
    repo_dir: Path,
    context: WorkerContext,
) -> "tuple[list[Claim], list[Snippet], ApiSurface, ProductEvidence]":
    """Extract claims, code snippets, API surface, and product evidence.

    TC-4002 reordered sandwich model:
    1. Pre-LLM (engineering): ALL deterministic evidence first
       - API surface, format matrix, limitations, workflows, install recipe
    2. Build evidence context and inject into LLM prompt
    3. LLM: Extract claims WITH evidence context
    4. Post-LLM (engineering): Contradiction resolution, validation,
       sanitization, snippet extraction
    """
    # ── Phase B.1: Deterministic evidence extraction ──────────────────

    # Resolve platform adapter for dispatch (TC-4003)
    _adapter = None
    try:
        from launcher.workers.understand.adapters import get_extractor
        _adapter = get_extractor(product.platform)
        logger.info("adapter: resolved %s for platform %r", _adapter.platform_id, product.platform)
    except Exception:
        logger.warning("adapter resolution failed, using legacy path", exc_info=True)

    # B.1a: Extract API surface (AST-based) — dispatches through adapter
    api_surface = _extract_api_surface(repo_dir, product, adapter=_adapter)

    # B.1b: Format matrix (TC-HYBRID-03)
    _format_matrix = []
    try:
        from launcher.workers.understand.extract._deterministic import extract_format_matrix
        _format_matrix = extract_format_matrix(repo_dir, product)
        if _format_matrix:
            api_surface = api_surface.model_copy(update={"format_matrix": _format_matrix})
            logger.info("format_matrix: %d formats extracted", len(_format_matrix))
    except Exception:
        logger.warning("extract_format_matrix failed", exc_info=True)

    # B.1c: Limitations (TC-4002)
    limitations = []
    try:
        from launcher.workers.understand.extract._deterministic import extract_limitations
        limitations = extract_limitations(repo_dir, repo_info)
    except Exception:
        logger.warning("extract_limitations failed", exc_info=True)

    # B.1d: Workflow examples (TC-4002)
    workflow_examples = []
    try:
        from launcher.workers.understand.extract._deterministic import extract_workflow_examples
        workflow_examples = extract_workflow_examples(repo_dir, repo_info, api_surface)
    except Exception:
        logger.warning("extract_workflow_examples failed", exc_info=True)

    # B.1e: Install recipe (moved from worker.py Phase B.5) (TC-HYBRID-04 + TC-4002)
    install_recipe = None
    try:
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        install_recipe = extract_install_recipe(repo_dir, product)
    except Exception:
        logger.warning("extract_install_recipe failed", exc_info=True)

    # ── Phase B.2: Evidence context assembly ──────────────────────────

    evidence_context = _build_evidence_context(
        api_surface, _format_matrix, limitations, install_recipe,
    )

    # ── Phase B.3: LLM claim extraction WITH evidence ─────────────────

    repo_content = getattr(context, "repo_content", None) or {}
    doc_contexts = _build_doc_contexts(repo_dir, repo_info, repo_content=repo_content)
    raw_snippets_for_llm = _extract_snippets(repo_dir, repo_info, product, api_surface, [])

    # LLM: Extract claims (evidence context injected into prompt)
    raw_claims = await _extract_claims_llm(
        doc_contexts, product, context,
        snippets=raw_snippets_for_llm,
        evidence_context=evidence_context,
    )

    # Harvest docstring-sourced claims as raw dicts (AQ-01)
    docstring_raw = _harvest_docstring_claims_raw(api_surface, product)
    if docstring_raw:
        raw_claims.extend(docstring_raw)
        logger.info("docstring_claims_raw harvested=%d", len(docstring_raw))
        context.emit_event(
            "docstring_claims_harvested", {"count": len(docstring_raw)}, worker="understand"
        )

    # ── Phase B.4: Post-LLM validation ────────────────────────────────

    claims = _validate_and_normalize_claims(raw_claims, product, api_surface)

    # B.4a: Classify claims (user_facing / internal / developer)
    from launcher.shared.classify_claims import filter_claims
    claims = filter_claims(claims)

    # B.4b: Contradiction resolution (TC-4002)
    contradiction_log: list[dict] = []
    try:
        from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions
        claims, contradiction_log = resolve_contradictions(claims, api_surface, limitations)
        if contradiction_log:
            context.emit_event(
                "contradictions_resolved",
                {"count": len(contradiction_log)},
                worker="understand",
            )
    except Exception:
        logger.warning("resolve_contradictions failed", exc_info=True)

    # B.4c: Sanitize claim text (TC-3825)
    from launcher.shared.input_sanitizer import sanitize_input as _sanitize
    sanitized_claims: list[Claim] = []
    claim_sanitize_hits = 0
    claims_truncated = 0
    for claim in claims:
        result = _sanitize(claim.text, max_chars=2_000)
        if result.redaction_count:
            logger.warning(
                "claim_sanitized claim_id=%s kinds=%s", claim.claim_id, result.redacted_kinds,
            )
            claim_sanitize_hits += result.redaction_count
        if result.truncated:
            claims_truncated += 1
        if result.redaction_count or result.truncated:
            sanitized_claims.append(claim.model_copy(update={"text": result.text}))
        else:
            sanitized_claims.append(claim)
    claims = sanitized_claims
    logger.info(
        "claim_sanitization_summary claims_processed=%d total_redactions=%d claims_truncated=%d",
        len(claims), claim_sanitize_hits, claims_truncated,
    )

    # B.4d: Remove claims about unrelated third-party technologies (TC-3782)
    pre_filter_count = len(claims)
    claims = _filter_contaminated_claims(claims, product)
    if pre_filter_count != len(claims):
        logger.info(
            "claim_contamination_filter removed=%d kept=%d",
            pre_filter_count - len(claims), len(claims),
        )

    # ── Phase B.5: Snippet extraction ─────────────────────────────────

    snippets = _extract_snippets(repo_dir, repo_info, product, api_surface, claims)

    target_snippet_count = len(api_surface.public_classes) * 2
    if len(snippets) < target_snippet_count:
        synthetic = _generate_synthetic_snippets(api_surface, product, claims)
        if synthetic:
            snippets.extend(synthetic)
            logger.info("synthetic_snippets generated=%d", len(synthetic))
            context.emit_event(
                "synthetic_snippets_generated", {"count": len(synthetic)}, worker="understand"
            )

    # ── Phase B.6: Embedding index ────────────────────────────────────

    _build_embedding_index(claims, doc_contexts, context)

    # ── Assemble ProductEvidence ──────────────────────────────────────

    product_evidence = ProductEvidence(
        limitations=limitations,
        workflow_examples=workflow_examples,
        install_recipe=install_recipe,
    )

    logger.info(
        "Phase B complete: %d claims, %d snippets, %d public classes, "
        "%d limitations, %d workflows, %d contradictions "
        "sanitize_redactions=%d claims_truncated=%d",
        len(claims), len(snippets), len(api_surface.public_classes),
        len(limitations), len(workflow_examples), len(contradiction_log),
        claim_sanitize_hits, claims_truncated,
    )
    return claims, snippets, api_surface, product_evidence


# ===================================================================
# B.2  Evidence context assembly (TC-4002)
# ===================================================================


def _build_evidence_context(
    api_surface: ApiSurface,
    format_matrix: list,
    limitations: list,
    install_recipe: "Any | None",
    max_chars: int = 4000,
) -> str:
    """Build a structured evidence context block for LLM prompt injection.

    Budget-capped to max_chars. Prioritizes:
    1. Format matrix (highest signal for format-heavy products)
    2. Known limitations
    3. API surface summary
    4. Install command
    """
    parts: list[str] = []
    budget = max_chars

    # Section 1: Format matrix
    if format_matrix:
        lines = ["## SOURCE-VERIFIED FACTS (do NOT contradict these)", ""]
        lines.append("### Format Matrix")
        lines.append("| Format | Import | Export |")
        lines.append("|--------|--------|--------|")
        for fr in format_matrix[:30]:
            imp = "Yes" if fr.can_import else "No"
            exp = "Yes" if fr.can_export else "No"
            lines.append(f"| {fr.name} | {imp} | {exp} |")
        block = "\n".join(lines)
        if len(block) < budget:
            parts.append(block)
            budget -= len(block)

    # Section 2: Limitations
    if limitations and budget > 200:
        lines = ["", "### Known Limitations"]
        for lim in limitations[:10]:
            line = f"- {lim.feature}: {lim.constraint} ({lim.source_file})"
            lines.append(line[:150])
        block = "\n".join(lines)
        if len(block) < budget:
            parts.append(block)
            budget -= len(block)

    # Section 3: API surface summary
    if api_surface and budget > 200:
        class_names = [c.name for c in (api_surface.class_briefs or [])[:15]]
        if class_names:
            lines = [
                "",
                f"### Public API ({api_surface.confidence} confidence)",
                f"Classes: {', '.join(class_names)} ({len(api_surface.public_classes)} total)",
            ]
            block = "\n".join(lines)
            if len(block) < budget:
                parts.append(block)
                budget -= len(block)

    # Section 4: Install command
    if install_recipe and budget > 100:
        parts.append(f"\n### Install\n{install_recipe.pip_command}")

    if not parts:
        return ""

    result = "\n".join(parts)
    # Add instruction
    if result:
        result += "\n\nVERIFIED EVIDENCE takes precedence over ambiguous source material.\nDo NOT extract claims that contradict verified evidence."

    if len(result) > max_chars:
        # Truncate at newline boundary to avoid splitting markdown table rows mid-row
        cutoff = result.rfind("\n", 0, max_chars)
        result = result[:cutoff] if cutoff > 0 else result[:max_chars]
    return result


# ===================================================================
# B.2b  Docstring-to-claim harvesting (TC-3816)
# ===================================================================


def _harvest_docstring_claims_raw(
    api_surface: ApiSurface,
    product: ProductIdentity,
    max_claims: int = 50,
) -> list[dict[str, Any]]:
    """Harvest raw claim dicts from class/method docstrings.

    Returns raw dicts matching the format expected by
    _validate_and_normalize_claims() so docstring claims go through
    the same dedup, visibility, and normalization pipeline as LLM claims
    (sandwich model compliance — AQ-01).
    """
    raw_claims: list[dict[str, Any]] = []

    for brief in api_surface.class_briefs:
        if len(raw_claims) >= max_claims:
            break

        # Class-level docstring claim
        if brief.docstring_snippet and len(brief.docstring_snippet) > 30:
            raw_claims.append({
                "text": f"{brief.name}: {brief.docstring_snippet}",
                "kind": "api",
                "visibility": "public",
                "evidence": [{
                    "source_file": f"docstring:{brief.name}",
                    "snippet": brief.docstring_snippet[:200],
                }],
            })

        # Method-level claims (brief summaries)
        if brief.methods:
            method_list = ", ".join(brief.methods[:5])
            raw_claims.append({
                "text": f"{brief.name} provides methods: {method_list}",
                "kind": "api",
                "visibility": "public",
                "evidence": [{
                    "source_file": f"docstring:{brief.name}",
                    "snippet": f"Methods: {method_list}",
                }],
            })

    return raw_claims


# ===================================================================
# B.3b  Synthetic snippet generation (TC-3816)
# ===================================================================


def _generate_synthetic_snippets(
    api_surface: ApiSurface,
    product: ProductIdentity,
    claims: list[Claim],
    max_snippets: int = 20,
) -> list[Snippet]:
    """Generate template-based code snippets from ClassBrief data.

    No LLM involved — pure deterministic synthesis from API surface.
    Only generates for classes that have >= 2 methods.
    Each snippet is validated with ast.parse() before inclusion.
    """
    canonical = product.canonical_import
    # Use import_allowlist[0] for accurate import path; fall back to canonical_import (GAP-09)
    import_module = (
        api_surface.import_allowlist[0] if api_surface.import_allowlist else None
    ) or canonical
    snippets: list[Snippet] = []

    # Map class names to claim_ids for linking
    class_claim_map: dict[str, list[str]] = {}
    for claim in claims:
        for brief in api_surface.class_briefs:
            if brief.name in claim.text:
                class_claim_map.setdefault(brief.name, []).append(claim.claim_id)

    for brief in api_surface.class_briefs:
        if len(snippets) >= max_snippets:
            break
        if len(brief.methods) < 2:
            continue

        # Build a minimal usage snippet
        lines = [f"import {import_module}"]
        lines.append("")
        lines.append(f"# Create a {brief.name} instance")
        lines.append(f"obj = {import_module}.{brief.name}()")
        lines.append("")

        # Add first two method calls
        for method in brief.methods[:2]:
            lines.append(f"# Call {method}")
            lines.append(f"result = obj.{method}()")

        code = "\n".join(lines)

        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError:
            continue

        linked_claims = class_claim_map.get(brief.name, [])[:3]

        snippets.append(Snippet(
            code=code,
            language="python",
            source_type="synthetic",
            claim_ids=linked_claims,
        ))

    return snippets
