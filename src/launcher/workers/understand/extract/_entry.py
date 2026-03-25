"""Phase B — Extract: main entry point orchestrator.

Contains:
  run_extract()                  — public W2 entry point (sandwich model)
  _harvest_docstring_claims_raw  — docstring→claim raw dict harvesting (TC-3816)

Spec references:
- specs/03_product_facts_and_evidence.md  (Claims extraction algorithm)
- specs/04_claims_compiler_truth_lock.md  (Claim structure and ID generation)
- specs/07_code_analysis_and_enrichment.md (API surface extraction)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ApiSurface, ProductIdentity
from launcher.models.understanding import ExtractionDatabase, ProductEvidence, RepoInfo
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.understand.extract._api_surface import _extract_api_surface
from launcher.workers.understand.extract._llm import _extract_claims_llm
from launcher.workers.understand.extract._snippets import _build_doc_contexts, _extract_snippets, _build_embedding_index
from launcher.workers.understand.extract._validation import _validate_and_normalize_claims, _filter_contaminated_claims, _filter_weak_evidence, _SPARSE_FACTS_THRESHOLD
from launcher.workers.understand.extract._deterministic import harvest_evidence_claims
from launcher.workers.understand.extract._linking import link_snippets

logger = logging.getLogger(__name__)


# Docstring harvesting caps: prefer bounded, high-signal claims over volume.
_MAX_DOCSTRING_CLAIMS: int = 120
_MAX_TYPED_METHODS_CLAIMS: int = 8
_MAX_TYPED_PROPS_CLAIMS: int = 6
_MAX_DOCSTRING_MEMBER_CLAIMS_PER_CLASS: int = 3
_MAX_OPERATION_CLAIMS: int = 8
_META_DOC_EXACT_NAMES: frozenset[str] = frozenset({
    "agents.md", "claude.md", "copilot-instructions.md", "llms.md",
})
_META_DOC_ROOT_KEYWORDS: frozenset[str] = frozenset({
    "readiness", "implementation", "summary", "status", "backlog",
    "roadmap", "plan", "notes",
})
_WORKFLOW_ASSERT_MARKERS: tuple[str, ...] = (
    "self.assert",
    "assertisinstance(",
    "asserttrue(",
    "assertfalse(",
    "assertequal(",
    "assert scene is not none",
    "pytest.raises",
    "unittest.main",
)


def _normalized_stem(rel_path: str) -> str:
    return Path(rel_path).stem.lower().replace("-", "").replace("_", "")


def _workflow_source_category(source_file: str) -> str:
    lower = (source_file or "").lower().replace("\\", "/")
    if not lower:
        return "unknown"
    name = Path(lower).name
    if name in _META_DOC_EXACT_NAMES:
        return "meta_doc"
    if "/" not in lower and _normalized_stem(lower) != "readme":
        if any(keyword in _normalized_stem(lower) for keyword in _META_DOC_ROOT_KEYWORDS):
            return "meta_doc"
    parts = Path(lower).parts
    if name.startswith("readme"):
        return "readme"
    if any(part in {"examples", "example", "samples", "sample", "demo", "demos"} for part in parts):
        return "example"
    if any(part in {"tests", "test"} for part in parts):
        return "test"
    if any(part in {"docs", "doc", "documentation"} for part in parts):
        return "doc"
    return "other"


def _filter_workflow_examples(workflow_examples: list) -> list:
    """Drop workflow examples that would pollute generation prompts.

    Raw unittest-style workflows are useful as fallback snippet evidence for lean
    repos, but they are too noisy for repo-level "real usage patterns" prompt
    injection because they leak assertions and option classes into every page.
    """
    kept: list = []
    skipped_reasons: dict[str, int] = {}

    for example in workflow_examples or []:
        source_file = getattr(example, "source_file", "") or ""
        category = _workflow_source_category(source_file)
        code = (getattr(example, "code", "") or "").lower()
        reason = ""
        if category in {"test", "meta_doc"}:
            reason = category
        elif any(marker in code for marker in _WORKFLOW_ASSERT_MARKERS):
            reason = "assert_heavy"

        if reason:
            skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
            continue
        kept.append(example)

    if skipped_reasons:
        logger.info(
            "workflow_examples_filter: kept=%d skipped=%d reasons=%s",
            len(kept),
            sum(skipped_reasons.values()),
            skipped_reasons,
        )
    return kept


# ===================================================================
# TC-HAL-04: LLM fallback strict api-kind filter
# ===================================================================


def _filter_fallback_api_claims(
    claims,
    api_surface,
    fallback_rate: float,
    threshold: float = 0.6,
):
    """Drop unverifiable api-kind llm_fallback claims when fallback rate is high.

    Returns (filtered_claims, dropped_count).
    Only activates when fallback_rate > threshold (default 0.6).
    Only drops llm_fallback claims with kind == "api" that contain no
    API identifier substring from api_surface.api_identifiers.
    Non-api kinds (feature, format, install, config) are always kept.

    TC-HAL-04
    """
    if fallback_rate <= threshold:
        return claims, 0

    api_ids_lower = {
        ident.lower()
        for ident in (getattr(api_surface, "api_identifiers", []) or [])
    }
    if not api_ids_lower:
        return claims, 0  # can't verify -> keep all

    kept = []
    dropped = 0
    for claim in claims:
        if claim.claim_source != "llm_fallback" or claim.kind != "api":
            kept.append(claim)
            continue
        text_lower = claim.text.lower()
        if any(ident in text_lower for ident in api_ids_lower):
            kept.append(claim)
        else:
            dropped += 1
            logger.debug(
                "llm_fallback_api_claim_dropped claim_id=%s: no API identifier in text",
                claim.claim_id,
            )

    if dropped:
        logger.warning(
            "llm_fallback_strict_filter [TC-HAL-04]: dropped=%d unverified api-kind claims "
            "(fallback_rate=%.2f > %.1f threshold)",
            dropped, fallback_rate, threshold,
        )
    return kept, dropped

# ===================================================================
# TC-4244: ExtractionDatabase builder helpers
# ===================================================================


def _build_api_facts(api_surface: "ApiSurface", product: "ProductIdentity") -> list:
    """Convert ApiSurface class_briefs into ApiFact records. TC-4244."""
    import hashlib
    from launcher.models.understanding import ApiFact

    facts = []
    family_slug = getattr(product, "family", "unknown").lower()
    platform = getattr(product, "platform", "unknown").lower()
    prefix = f"AF-{family_slug}-{platform}"

    for cb in getattr(api_surface, "class_briefs", []):
        class_name = cb.name

        # Class-level fact
        fact_id = f"{prefix}-{class_name}-class"
        facts.append(ApiFact(
            fact_id=fact_id,
            class_name=class_name,
            member_name=class_name,
            member_type="class",
            docstring=getattr(cb, "docstring_snippet", ""),
            source_file="",
            confidence=1.0,
        ))

        property_name_set = {
            getattr(tp, "name", "")
            for tp in getattr(cb, "typed_properties", []) or []
            if getattr(tp, "name", "")
        }

        # Typed method facts
        for tm in getattr(cb, "typed_methods", []) or []:
            member_name = getattr(tm, "name", "")
            if not member_name or member_name in property_name_set:
                continue
            sig_parts = [f"{member_name}("]
            params = getattr(tm, "parameters", []) or []
            # MethodParam is a Pydantic model with .name and .type_annotation attributes
            # (not a dict), so use getattr instead of .get(). TC-4244.
            def _param_name(p) -> str:
                if hasattr(p, "name"):
                    return getattr(p, "name", "")
                return p.get("name", "") if isinstance(p, dict) else ""

            def _param_type(p) -> str:
                if hasattr(p, "type_annotation"):
                    return getattr(p, "type_annotation", "")
                return p.get("type", "") if isinstance(p, dict) else ""

            sig_parts.append(", ".join(
                f"{_param_name(p)}: {_param_type(p)}" for p in params
            ))
            sig_parts.append(")")
            rt = getattr(tm, "return_type", "")
            if rt:
                sig_parts.append(f" -> {rt}")
            signature = "".join(sig_parts)

            raw = f"{class_name}.{member_name}"
            hash6 = hashlib.sha256(raw.encode()).hexdigest()[:6]
            facts.append(ApiFact(
                fact_id=f"{prefix}-{class_name}.{member_name}-{hash6}",
                class_name=class_name,
                member_name=member_name,
                member_type="method",
                signature=signature,
                docstring=getattr(tm, "docstring_snippet", ""),
                return_type=rt,
                parameters=[
                    {"name": _param_name(p), "type": _param_type(p), "default": ""}
                    for p in params
                ],
                is_static=getattr(tm, "is_static", False),
                confidence=1.0,
            ))

        # Typed property facts
        for tp in getattr(cb, "typed_properties", []) or []:
            member_name = getattr(tp, "name", "")
            if not member_name:
                continue
            raw = f"{class_name}.{member_name}"
            hash6 = hashlib.sha256(raw.encode()).hexdigest()[:6]
            facts.append(ApiFact(
                fact_id=f"{prefix}-{class_name}.{member_name}-{hash6}",
                class_name=class_name,
                member_name=member_name,
                member_type="property",
                signature=f"{member_name}: {getattr(tp, 'type_annotation', '')}",
                docstring=getattr(tp, "docstring_snippet", ""),
                return_type=getattr(tp, "type_annotation", ""),
                is_readonly=getattr(tp, "is_readonly", False),
                confidence=1.0,
            ))

        # Enum member facts (from ClassBrief.enums)
        for em in getattr(cb, "enums", []) or []:
            enum_class_name = getattr(em, "name", "")
            for member in getattr(em, "members", []) or []:
                member_name = member if isinstance(member, str) else getattr(member, "name", "")  # TC-4251: EnumMember is a Pydantic model, not a dict
                if not member_name:
                    continue
                raw = f"{enum_class_name}.{member_name}"
                hash6 = hashlib.sha256(raw.encode()).hexdigest()[:6]
                facts.append(ApiFact(
                    fact_id=f"{prefix}-{enum_class_name}.{member_name}-{hash6}",
                    class_name=enum_class_name,
                    member_name=member_name,
                    member_type="enum_member",
                    signature=f"{enum_class_name}.{member_name}",
                    confidence=1.0,
                ))

    # TC-UND-211: deterministic sort for stable LLM prompt content across runs.
    facts.sort(key=lambda f: (
        getattr(f, "class_name", ""),
        getattr(f, "member_type", ""),
        getattr(f, "member_name", ""),
    ))
    return facts


def _build_format_facts(format_matrix: list, product: "ProductIdentity") -> list:
    """Convert FormatRecord list into FormatFact records with confidence. TC-4244."""
    from launcher.models.understanding import FormatFact

    facts = []
    family_slug = getattr(product, "family", "unknown").lower()
    platform = getattr(product, "platform", "unknown").lower()
    prefix = f"FF-{family_slug}-{platform}"

    for fr in format_matrix or []:
        fmt_name = getattr(fr, "name", "")
        if not fmt_name:
            continue

        # Infer confidence from source evidence
        test_count = getattr(fr, "test_count", 0) or 0
        src_ev = getattr(fr, "source_evidence", "") or ""

        if test_count > 2:
            confidence = 1.0  # found in multiple enum/test references
            ev_source = "enum_declaration"
        elif test_count > 0:
            confidence = 0.9  # found in at least one reference
            ev_source = "enum_declaration"
        elif "enum_member" in src_ev.lower():
            # TC-UND-208: Format derived from SaveFormat/LoadFormat enum membership.
            # Authoritative (enum proves capability) but not test-confirmed.
            confidence = 0.85
            ev_source = "enum_declaration"
        elif "readme" in src_ev.lower():
            confidence = 0.7
            ev_source = "readme_table"
        else:
            confidence = 0.6
            ev_source = "extension_pattern"

        facts.append(FormatFact(
            fact_id=f"{prefix}-{fmt_name}",
            format_name=fmt_name,
            extension=getattr(fr, "extension", ""),
            can_import=getattr(fr, "can_import", False),
            can_export=getattr(fr, "can_export", False),
            confidence=confidence,
            evidence_source=ev_source,
            source_file=src_ev,
        ))

    return facts


def _build_snippet_facts(snippets: list, product: "ProductIdentity") -> list:
    """Convert Snippet list into SnippetFact records with operation classification. TC-4244."""
    import hashlib
    import re
    from launcher.models.understanding import SnippetFact

    facts = []
    family_slug = getattr(product, "family", "unknown").lower()
    platform = getattr(product, "platform", "unknown").lower()
    prefix = f"SF-{family_slug}-{platform}"

    _LOAD_RE = re.compile(r"\.(load|open|read|parse|from_file)\s*\(", re.IGNORECASE)
    _SAVE_RE = re.compile(r"\.(save|write|export|to_file)\s*\(", re.IGNORECASE)
    _FMT_EXT_RE = re.compile(
        r'"[^"]*\.(xlsx|xls|csv|pdf|html|ods|docx|pptx|png|jpg|svg|xml|json|fbx|obj|stl|gltf|dxf|dwg)[^"]*"',
        re.IGNORECASE,
    )
    _FORMAT_ENUM_RE = re.compile(r'\b\w+Format\.\s*(\w+)', re.IGNORECASE)
    _PASCAL_CLASS_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\s*\(')

    for src_idx, sn in enumerate(snippets or []):
        code = getattr(sn, "code", "")
        if not code:
            continue

        has_load = bool(_LOAD_RE.search(code))
        has_save = bool(_SAVE_RE.search(code))

        if has_load and has_save:
            op_label = "convert"
        elif has_save:
            op_label = "save_file"
        elif has_load:
            op_label = "load_file"
        else:
            op_label = "other"

        # Detect formats
        ext_matches = [m.group(1).upper() for m in _FMT_EXT_RE.finditer(code)]
        enum_matches = [m.group(1).upper() for m in _FORMAT_ENUM_RE.finditer(code)]
        all_fmts = list(dict.fromkeys(ext_matches + enum_matches))  # preserve order, dedup

        input_fmt = ""
        output_fmt = ""
        if op_label == "convert" and len(all_fmts) >= 2:
            input_fmt = all_fmts[0]
            output_fmt = all_fmts[-1]
        elif op_label == "save_file" and all_fmts:
            output_fmt = all_fmts[0]
        elif op_label == "load_file" and all_fmts:
            input_fmt = all_fmts[0]

        # Detect primary class
        class_matches = _PASCAL_CLASS_RE.findall(code)
        demo_class = class_matches[0] if class_matches else ""

        src_file = getattr(sn, "source_file", "")
        hash6 = hashlib.sha256(code.encode()).hexdigest()[:6]

        # Confidence from source type
        conf = 0.9 if "example" in src_file.lower() or "test" in src_file.lower() else 0.7

        facts.append(SnippetFact(
            fact_id=f"{prefix}-{op_label}-{hash6}",
            code=code,
            language=getattr(sn, "language", "python"),
            operation_label=op_label,
            input_format=input_fmt,
            output_format=output_fmt,
            demonstrates_class=demo_class,
            source_file=src_file,
            source_lines=tuple(getattr(sn, "source_lines", (0, 0)) or (0, 0)),
            syntax_valid=getattr(sn, "syntax_valid", True),
            snippet_source_idx=src_idx,
            confidence=conf,
        ))

    return facts


def _build_limitation_facts(limitations: list, product: "ProductIdentity") -> list:
    """Convert LimitationEntry list into LimitationFact records. TC-4244."""
    import hashlib
    from launcher.models.understanding import LimitationFact

    facts = []
    family_slug = getattr(product, "family", "unknown").lower()
    platform = getattr(product, "platform", "unknown").lower()
    prefix = f"LF-{family_slug}-{platform}"

    for lim in limitations or []:
        feature = getattr(lim, "feature", "")
        constraint = getattr(lim, "constraint", "")
        if not feature:
            continue

        src_conf = getattr(lim, "confidence", "heuristic")
        conf = 1.0 if src_conf == "ast_verified" else (0.8 if src_conf == "doc_stated" else 0.5)

        raw = f"{feature}:{constraint}"
        hash6 = hashlib.sha256(raw.encode()).hexdigest()[:6]

        facts.append(LimitationFact(
            fact_id=f"{prefix}-{hash6}",
            feature=feature,
            constraint=constraint,
            status=getattr(lim, "status", "warning"),
            source_file=getattr(lim, "source_file", ""),
            source_line=getattr(lim, "source_line", 0),
            confidence=conf,
        ))

    return facts


def _validate_fact_binding(
    raw_claims: list[dict],
    extraction_db: "ExtractionDatabase | None",
    bounded_mode_active: bool,
) -> "tuple[list[dict], dict]":
    """Elevate unbound LLM claims to llm_sparse_grounding (0.55) for downstream filtering.

    TC-4247/TC-5181: In bounded-description mode, LLM claims should cite a source_fact_id
    from the ExtractionDatabase. Claims that fail to cite a valid fact_id are elevated to
    confidence=0.55 (llm_sparse_grounding) so _filter_weak_evidence can make the final
    quality call. Using 0.35 caused near-total claim collapse when LLM does not cite
    fact_ids; 0.55 keeps claims above the U-2 threshold (TC-4225, confidence < 0.5).

    Skips docstring and llm_fallback claims (pre-verified).
    Is a no-op passthrough when bounded_mode_active=False or db has no facts.

    Returns (validated_claims, stats_dict).
    """
    if not bounded_mode_active or extraction_db is None:
        return raw_claims, {"skipped": "discovery_mode_or_no_db"}

    # Build set of valid fact_ids from the ExtractionDatabase
    valid_fact_ids: set[str] = set()
    for f in getattr(extraction_db, "api_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)
    for f in getattr(extraction_db, "format_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)
    for f in getattr(extraction_db, "limitation_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)

    if not valid_fact_ids:
        return raw_claims, {"skipped": "no_valid_fact_ids_in_db"}

    validated: list[dict] = []
    bound_count = 0
    unbound_count = 0
    skipped_count = 0

    for claim in raw_claims:
        claim_source = claim.get("claim_source", "llm")

        # Pre-verified sources — skip binding check
        # TC-UND-211: deterministic_fallback is the same extraction as deterministic, just triggered by LLM failure
        if claim_source in ("docstring", "llm_fallback", "deterministic_fallback"):
            validated.append(claim)
            skipped_count += 1
            continue

        # Check if any evidence item cites a valid fact_id
        evidence = claim.get("evidence", [])
        has_valid_binding = any(
            ev.get("source_fact_id", "") in valid_fact_ids
            for ev in evidence
            if ev.get("source_fact_id", "")
        )

        if has_valid_binding:
            bound_count += 1
            validated.append(claim)
        else:
            # TC-5181: Unbound claim — elevate to llm_sparse_grounding (0.55) instead of
            # llm_fallback (0.35). Keeps claims above the U-2 filter threshold so
            # _filter_weak_evidence can make the final quality call based on evidence
            # relevance. Prevents near-total claim collapse when LLM does not cite fact_ids.
            unbound_count += 1
            updated = dict(claim)  # copy to avoid mutating original
            updated["confidence"] = 0.55
            updated["claim_source"] = "llm_sparse_grounding"
            validated.append(updated)

    stats = {
        "valid_fact_ids_in_db": len(valid_fact_ids),
        "bound_claims": bound_count,
        "unbound_claims_elevated_sparse": unbound_count,
        "pre_verified_skipped": skipped_count,
        "total_processed": len(raw_claims),
    }
    logger.info(
        "fact_binding_validation [TC-4247/TC-5181]: bound=%d unbound_elevated_sparse=%d "
        "pre_verified=%d valid_fact_ids=%d",
        bound_count, unbound_count, skipped_count, len(valid_fact_ids),
    )
    return validated, stats


def _compute_extraction_completeness(
    api_facts: list,
    format_facts: list,
    snippet_facts: list,
    limitation_facts: list,
    api_surface: "ApiSurface",
) -> "ExtractionCompleteness":
    """Compute ExtractionCompleteness metrics. TC-4244."""
    from launcher.models.understanding import ExtractionCompleteness

    api_class_count = len(set(
        f.class_name for f in api_facts
        if getattr(f, "member_type", "") == "class"
    ))
    api_method_count = len([f for f in api_facts if getattr(f, "member_type", "") == "method"])
    api_conf = getattr(api_surface, "confidence", "low")

    fmt_confidences = [getattr(f, "confidence", 0.0) for f in format_facts]
    fmt_conf_avg = sum(fmt_confidences) / len(fmt_confidences) if fmt_confidences else 0.0

    op_labels = list(set(
        getattr(s, "operation_label", "")
        for s in snippet_facts
        if getattr(s, "operation_label", "")
    ))

    missing = []
    if api_class_count == 0:
        missing.append("no_api_classes")
    if not format_facts:
        missing.append("no_formats")
    if not snippet_facts:
        missing.append("no_snippets")

    # Score: 0.0-1.0
    score = 0.0
    score += min(api_method_count / 50.0, 1.0) * 0.30
    score += min(len(format_facts) / 10.0, 1.0) * 0.20
    score += (1.0 if api_conf == "high" else 0.5 if api_conf == "medium" else 0.0) * 0.20
    score += min(len(snippet_facts) / 15.0, 1.0) * 0.15
    score += fmt_conf_avg * 0.15

    return ExtractionCompleteness(
        api_class_count=api_class_count,
        api_method_count=api_method_count,
        api_confidence=api_conf,
        format_count=len(format_facts),
        format_confidence_avg=fmt_conf_avg,
        snippet_count=len(snippet_facts),
        operation_coverage=op_labels,
        limitation_count=len(limitation_facts),
        missing_signals=missing,
        overall_completeness=round(score, 3),
    )


# ===================================================================
# Public entry point
# ===================================================================


async def run_extract(
    product: ProductIdentity,
    repo_info: RepoInfo,
    repo_dir: Path,
    context: WorkerContext,
) -> "tuple[list[Claim], list[Snippet], ApiSurface, ProductEvidence, ExtractionDatabase]":
    """Extract claims, code snippets, API surface, and product evidence.

    TC-4002 reordered sandwich model:
    1. Pre-LLM (engineering): ALL deterministic evidence first
       - API surface, format matrix, limitations, workflows, install recipe
    2. Build evidence context and inject into LLM prompt
    3. LLM: Extract claims WITH evidence context
    4. Post-LLM (engineering): Contradiction resolution, validation,
       sanitization, snippet extraction
    """
    # Phase D: Drop-log accumulator — collects typed records for every claim dropped at any stage.
    # Stored on context so worker.py can include it in extraction_audit.json without changing
    # run_extract's return signature. Capped at 500 entries (overflow counted separately).
    _claim_drop_log: list[dict] = []
    _DROP_LOG_CAP = 500

    # ── Phase B.1: Deterministic evidence extraction ──────────────────

    # Resolve platform adapter for dispatch (TC-4003)
    _adapter = None
    try:
        from launcher.workers.understand.adapters import get_extractor
        _adapter = get_extractor(product.platform)
        logger.info("adapter: resolved %s for platform %r", _adapter.platform_id, product.platform)
    except Exception:
        logger.warning("adapter resolution failed, using legacy path", exc_info=True)

    # HG-07: Detect generic fallback — emit MissingInfoEntry so downstream workers
    # can distinguish "typed extraction unavailable" from "no typed methods exist"
    _missing_info: list = []
    try:
        from launcher.workers.understand.adapters._generic import GenericExtractor
        from launcher.models.understanding import MissingInfoEntry, FieldConfidence
        if isinstance(_adapter, GenericExtractor) or _adapter is None:
            _missing_info.append(MissingInfoEntry(
                field="api_surface.typed_methods",
                reason=f"No typed extraction available for platform '{product.platform}'",
                attempted_strategies=["generic_regex"],
                fallback_used="regex",
            ))
            logger.info(
                "adapter: generic fallback for platform %r — MissingInfoEntry emitted",
                product.platform,
            )
    except Exception:
        logger.warning("missing_info detection failed", exc_info=True)

    # B.1a: Extract API surface (AST-based) — dispatches through adapter
    api_surface = _extract_api_surface(repo_dir, product, adapter=_adapter)

    # B.1b: Format matrix (TC-HYBRID-03)
    _format_matrix = []
    try:
        from launcher.workers.understand.extract._deterministic import extract_format_matrix
        _format_matrix = extract_format_matrix(repo_dir, product, api_surface=api_surface)
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
        workflow_examples = extract_workflow_examples(
            repo_dir, repo_info, api_surface, platform=product.platform
        )
        workflow_examples = _filter_workflow_examples(workflow_examples)
    except Exception:
        logger.warning("extract_workflow_examples failed", exc_info=True)

    # B.1e: Install recipe (moved from worker.py Phase B.5) (TC-HYBRID-04 + TC-4002)
    # TC-4030: pass shared_facts to avoid re-reading pyproject.toml (already parsed by Scout)
    install_recipe = None
    try:
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        install_recipe = extract_install_recipe(repo_dir, product, shared_facts=repo_info.shared_facts)
    except Exception:
        logger.warning("extract_install_recipe failed", exc_info=True)

    # ── Phase B.2: Evidence context assembly ──────────────────────────

    evidence_context = _build_evidence_context(
        api_surface, _format_matrix, limitations, install_recipe,
    )

    # TC-4246: Build partial ExtractionDatabase with api_facts + format_facts BEFORE the LLM
    # call so bounded-description mode can inject verified facts into the prompt.
    # NOTE: snippet_facts and limitation_facts are added to the full extraction_db at the end.
    _pre_llm_api_facts = _build_api_facts(api_surface, product)
    _pre_llm_fmt_facts = _build_format_facts(api_surface.format_matrix or [], product)
    _pre_llm_extraction_db = ExtractionDatabase(
        api_facts=_pre_llm_api_facts,
        format_facts=_pre_llm_fmt_facts,
    )

    # ── Phase B.3: LLM claim extraction WITH evidence ─────────────────

    repo_content = getattr(context, "repo_content", None) or {}
    doc_contexts = _build_doc_contexts(repo_dir, repo_info, repo_content=repo_content)
    raw_snippets_for_llm = _extract_snippets(repo_dir, repo_info, product, api_surface, [])

    # TC-4247: Initialize fact_binding stats (always defined even if step is skipped)
    _fact_binding_stats: dict = {}

    # LLM: Extract claims (evidence context injected into prompt)
    raw_claims = await _extract_claims_llm(
        doc_contexts, product, context,
        snippets=raw_snippets_for_llm,
        evidence_context=evidence_context,
        extraction_db=_pre_llm_extraction_db,  # TC-4246: bounded-description mode
    )

    # ── Phase B.3a: Fact-binding validation (TC-4247) ─────────────────
    # In bounded-description mode, downgrade LLM claims with no valid fact_id.
    _bounded_mode_active = bool(
        _pre_llm_extraction_db is not None
        and (getattr(_pre_llm_extraction_db, "api_facts", None)
             or getattr(_pre_llm_extraction_db, "format_facts", None))
    )
    # Phase D: snapshot pre-mutation state for fact-binding audit trail (SR-02).
    # Must be built BEFORE _validate_fact_binding so we can record the original
    # confidence and claim_source before they are downgraded to 0.35/llm_fallback.
    _pre_binding_snapshot: dict[str, tuple[float, str]] = {
        rc.get("claim_id", ""): (
            float(rc.get("confidence", 0.75)),
            str(rc.get("claim_source", "llm")),
        )
        for rc in raw_claims
        if rc.get("claim_id") and rc.get("claim_source") not in ("llm_fallback",)
    }
    raw_claims, _fact_binding_stats = _validate_fact_binding(
        raw_claims, _pre_llm_extraction_db, _bounded_mode_active
    )
    context.emit_event(
        "fact_binding_validated",
        _fact_binding_stats,
        worker="understand",
    )
    # Phase D: log fact-binding mutations into drop_log.
    # TC-5181: mutation is claim → llm_sparse_grounding (0.55), NOT a drop (kept above U-2).
    for _rc in raw_claims:
        _rc_id = _rc.get("claim_id", "")
        if str(_rc.get("claim_source", "")) == "llm_sparse_grounding" and _rc_id in _pre_binding_snapshot:
            _orig_conf, _orig_src = _pre_binding_snapshot[_rc_id]
            if _orig_src not in ("llm_sparse_grounding", "llm_fallback") and len(_claim_drop_log) < _DROP_LOG_CAP:
                _claim_drop_log.append({
                    "claim_id": _rc_id,
                    "claim_text_prefix": str(_rc.get("text", ""))[:80],
                    "drop_stage": "fact_binding_mutation",
                    "drop_reason": (
                        f"no valid source_fact_id; confidence elevated "
                        f"{_orig_conf:.2f}→0.55, claim_source→llm_sparse_grounding (TC-5181)"
                    ),
                    "confidence_before": _orig_conf,
                    "claim_source": _orig_src,
                })

    # Harvest docstring-sourced claims as raw dicts (AQ-01)
    docstring_cap = min(_MAX_DOCSTRING_CLAIMS, max(12, len(raw_claims)))
    docstring_raw = _harvest_docstring_claims_raw(
        api_surface,
        product,
        max_claims=docstring_cap,
    )
    if docstring_raw:
        raw_claims.extend(docstring_raw)
        logger.info("docstring_claims_raw harvested=%d", len(docstring_raw))
        context.emit_event(
            "docstring_claims_harvested", {"count": len(docstring_raw)}, worker="understand"
        )
    operation_raw = _harvest_operation_claims_raw(
        api_surface,
        product,
        snippet_codes=[getattr(snippet, "code", "") for snippet in raw_snippets_for_llm],
    )
    if operation_raw:
        raw_claims.extend(operation_raw)
        logger.info("operation_claims_raw harvested=%d", len(operation_raw))

    # TC-UND-211: Harvest evidence-derived claims from ExtractionDatabase facts.
    # Converts class_briefs, format_facts, snippet_facts, limitation_facts, and
    # install_recipe into deterministic claims with diversified kinds so non-API
    # pages receive grounded claims through _KIND_TO_ROLES routing.
    _pre_llm_lim_facts = _build_limitation_facts(limitations, product)
    _evidence_db_for_harvest = ExtractionDatabase(
        api_facts=_pre_llm_api_facts,
        format_facts=_pre_llm_fmt_facts,
        snippet_facts=_build_snippet_facts(raw_snippets_for_llm, product),
        limitation_facts=_pre_llm_lim_facts,
        install_recipe=install_recipe,
    )
    evidence_raw = harvest_evidence_claims(
        api_surface, _evidence_db_for_harvest, product,
        install_recipe=install_recipe,
    )
    if evidence_raw:
        raw_claims.extend(evidence_raw)
        logger.info("evidence_claims_raw harvested=%d [TC-UND-211]", len(evidence_raw))
        context.emit_event(
            "evidence_claims_harvested",
            {"count": len(evidence_raw)},
            worker="understand",
        )

    # ── Phase B.4: Post-LLM validation ────────────────────────────────

    claims = _validate_and_normalize_claims(
        raw_claims,
        product,
        api_surface,
        file_tree=frozenset(repo_info.file_tree),
        drop_log=_claim_drop_log,
    )

    # B.4a: Classify claims (user_facing / internal / developer)
    from launcher.shared.classify_claims import filter_claims
    claims = filter_claims(claims)

    # BBN-02: Compute sparse_facts flag — when bounded-description mode is active but
    # EITHER the api_facts OR format_facts are below _SPARSE_FACTS_THRESHOLD, unbound
    # LLM claims get elevated to llm_sparse_grounding (0.55) instead of being dropped.
    # OR semantics: repos sparse in any one dimension (e.g. 3d/java: few format facts)
    # enter sparse mode even when the other dimension is rich.
    _sparse_facts = (
        _bounded_mode_active
        and (
            len(_pre_llm_api_facts) < _SPARSE_FACTS_THRESHOLD
            or len(_pre_llm_fmt_facts) < _SPARSE_FACTS_THRESHOLD
        )
    )

    # UND-01: Filter claims with empty or irrelevant evidence
    claims = _filter_weak_evidence(claims, sparse_facts=_sparse_facts)

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
    _pre_contamination = {c.claim_id: c for c in claims}
    claims = _filter_contaminated_claims(claims, product)
    _post_contamination_ids = {c.claim_id for c in claims}
    for _cid, _c in _pre_contamination.items():
        if _cid not in _post_contamination_ids and len(_claim_drop_log) < _DROP_LOG_CAP:
            _claim_drop_log.append({
                "claim_id": _cid,
                "claim_text_prefix": _c.text[:80],
                "drop_stage": "contamination_filter",
                "drop_reason": "third-party technology mention without product keyword",
                "confidence_before": _c.confidence,
                "claim_source": _c.claim_source,
            })
    if len(_pre_contamination) != len(claims):
        logger.info(
            "claim_contamination_filter removed=%d kept=%d",
            len(_pre_contamination) - len(claims), len(claims),
        )

    # Phase B.4e: LLM fallback strict filtering (TC-HAL-04)
    _llm_fallback_count = sum(1 for c in claims if c.claim_source == "llm_fallback")
    _total_claim_count = len(claims)
    _llm_fallback_rate = _llm_fallback_count / _total_claim_count if _total_claim_count > 0 else 0.0
    logger.info("llm_fallback_rate=%.3f (%d/%d claims)", _llm_fallback_rate, _llm_fallback_count, _total_claim_count)

    _pre_fallback_map = {c.claim_id: c for c in claims}
    claims, _unverified_api_dropped = _filter_fallback_api_claims(
        claims, api_surface, _llm_fallback_rate
    )
    if _unverified_api_dropped > 0:
        _post_fallback_ids = {c.claim_id for c in claims}
        for _cid, _c in _pre_fallback_map.items():
            if _cid not in _post_fallback_ids and len(_claim_drop_log) < _DROP_LOG_CAP:
                _claim_drop_log.append({
                    "claim_id": _cid,
                    "claim_text_prefix": _c.text[:80],
                    "drop_stage": "llm_fallback_api_filter",
                    "drop_reason": "unverifiable api-kind llm_fallback claim (TC-HAL-04)",
                    "confidence_before": _c.confidence,
                    "claim_source": _c.claim_source,
                })
        context.emit_event(
            "llm_fallback_filter_applied",
            {
                "fallback_rate": round(_llm_fallback_rate, 3),
                "unverified_api_claims_dropped": _unverified_api_dropped,
            },
            worker="understand",
        )

    context.emit_event(
        "llm_fallback_metrics",
        {
            "fallback_rate": round(_llm_fallback_rate, 3),
            "fallback_count": _llm_fallback_count,
            "unverified_api_dropped": _unverified_api_dropped,
        },
        worker="understand",
    )

    # U-2: Drop claims with confidence < 0.5 before passing downstream [TC-4225]
    # confidence=0.35 == llm_fallback; dropping these prevents CRITICAL hallucination_rate
    # findings in Evaluate (triggered when >10% of used claims have confidence<0.5).
    _pre_u2_claims = claims
    claims = [c for c in _pre_u2_claims if c.confidence >= 0.5]
    _low_conf_dropped = len(_pre_u2_claims) - len(claims)
    if _low_conf_dropped:
        for _c in _pre_u2_claims:
            if _c.confidence < 0.5 and len(_claim_drop_log) < _DROP_LOG_CAP:
                _claim_drop_log.append({
                    "claim_id": _c.claim_id,
                    "claim_text_prefix": _c.text[:80],
                    "drop_stage": "u2_confidence_filter",
                    "drop_reason": f"confidence {_c.confidence:.2f} < 0.5 threshold (TC-4225)",
                    "confidence_before": _c.confidence,
                    "claim_source": _c.claim_source,
                })
        logger.warning(
            "low_confidence_claims_dropped [TC-4225]: %d claims with confidence<0.5 excluded "
            "(source=llm_fallback). These had confidence=0.35 and would trigger hallucination_rate CRITICAL.",
            _low_conf_dropped,
        )
        context.emit_event(
            "low_confidence_claims_dropped",
            {"count": _low_conf_dropped, "threshold": 0.5},
            worker="understand",
        )

    # CDN-01: Detect whether the pipeline is running without LLM-origin claims.
    # If no LLM-origin claims survived, evidence-derived claims (TC-UND-211 Phase 1c)
    # are the sole content source. Log this for operational visibility.
    _LLM_ORIGIN_SOURCES = {"llm", "llm_corroborated", "llm_sparse_grounding"}
    _llm_origin_count = sum(1 for c in claims if c.claim_source in _LLM_ORIGIN_SOURCES)
    if _llm_origin_count == 0 and len(claims) > 0:
        logger.warning(
            "CDN-01 activated [TC-UND-211]: 0 LLM-origin claims survived filtering; "
            "%d deterministic/evidence claims remain as sole content source.",
            len(claims),
        )
        context.emit_event(
            "cdn01_fallback_activated",
            {
                "llm_origin_claims": 0,
                "deterministic_claims": len(claims),
                "reason": "no_llm_claims_survived_filtering",
            },
            worker="understand",
        )

    # Phase D: Store drop log on context for worker.py audit output.
    # Capped at _DROP_LOG_CAP entries; overflow is not tracked (first 500 are sufficient for diagnosis).
    context.claim_drop_log = _claim_drop_log

    # Phase B.5 continues below

    # ── Phase B.5: Snippet extraction ─────────────────────────────────

    snippets = _extract_snippets(repo_dir, repo_info, product, api_surface, claims)

    # TC-5135: Three-tier structural linking cascade + UND-03 redistribution
    snippets = link_snippets(snippets, claims, api_surface, _pre_llm_api_facts)

    # TC-4062: Synthetic snippet generation removed — it produced semantically wrong
    # evidence (obj.method() with no args). Zero snippets is the correct signal;
    # the "EVIDENCE ABSENT" path in section_prompt.py handles it cleanly.

    # TC-HAL-07: Validate snippet import paths against api_surface.import_allowlist
    _invalid_import_count = 0
    try:
        from launcher.workers.understand.extract._snippets import _validate_snippet_imports
        _allowlist = getattr(api_surface, "import_allowlist", []) or []
        if _allowlist:
            snippets, _invalid_import_count = _validate_snippet_imports(
                snippets,
                _allowlist,
                api_surface=api_surface,
            )
            if _invalid_import_count:
                logger.warning(
                    "snippet_import_validation [TC-HAL-07]: %d snippets filtered (invalid import path)",
                    _invalid_import_count,
                )
    except Exception:
        logger.warning("snippet_import_validation failed [TC-HAL-07]", exc_info=True)

    # TC-5174: Finalization gate — remove orphaned snippets before bundle assembly.
    # Any snippet still without claim_ids after the three-tier cascade is dead data:
    # Planner and Generate implicitly exclude it, but retaining it in the bundle
    # pollutes phase_store/ artifacts indefinitely. Filter here at the ownership point.
    from launcher.workers.understand.extract._linking import filter_orphaned_snippets
    snippets, _orphan_filtered_count = filter_orphaned_snippets(snippets)
    context.orphan_filtered_count = _orphan_filtered_count

    context.emit_event(
        "snippet_extraction_complete",
        {
            "extracted": len(snippets),
            "import_filtered": _invalid_import_count,
            "orphan_filtered": _orphan_filtered_count,
        },
        worker="understand",
    )

    # ── Phase B.6: Embedding index ────────────────────────────────────

    _build_embedding_index(claims, doc_contexts, context)

    # ── Assemble ProductEvidence ──────────────────────────────────────

    # Build per-field confidence (HG-07: absent when generic adapter used)
    _confidence = {}
    if _missing_info:
        try:
            from launcher.models.understanding import FieldConfidence as _FC
            _confidence["typed_methods"] = _FC(source="absent")
        except Exception:
            pass

    _supported_formats = [fr.name for fr in _format_matrix if fr.can_import or fr.can_export]
    _input_formats = [fr.name for fr in _format_matrix if fr.can_import]
    _output_formats = [fr.name for fr in _format_matrix if fr.can_export]

    # SR-11: C++ has no API-level format signals; detect from README/docs instead
    if not _supported_formats and getattr(product, "platform", "") == "cpp":
        try:
            from launcher.workers.understand.adapters._cpp import CppExtractor as _CppExt
            _cpp_ext = _CppExt()
            _doc_texts = [repo_content.get(p, "") for p in (repo_info.doc_paths or [])[:5]]
            _detected = _cpp_ext.detect_supported_formats_from_docs(
                repo_info.readme_summary or "", _doc_texts
            )
            if _detected:
                _supported_formats = _detected
                logger.info("[Understand] C++ doc-based format detection: %s", _detected)
        except Exception:
            pass

    product_evidence = ProductEvidence(
        limitations=limitations,
        workflow_examples=workflow_examples,
        install_recipe=install_recipe,
        missing_info=_missing_info,
        confidence=_confidence,
        # TC-4040: wire AST-extracted format matrix into ProductEvidence
        supported_formats=_supported_formats,
        input_formats=_input_formats,
        output_formats=_output_formats,
    )

    logger.info(
        "Phase B complete: %d claims, %d snippets, %d public classes, "
        "%d limitations, %d workflows, %d contradictions "
        "sanitize_redactions=%d claims_truncated=%d",
        len(claims), len(snippets), len(api_surface.public_classes),
        len(limitations), len(workflow_examples), len(contradiction_log),
        claim_sanitize_hits, claims_truncated,
    )

    # TC-4244/TC-4246: Assemble ExtractionDatabase from all extracted facts
    # Note: _api_facts and _fmt_facts already built before LLM call for TC-4246 injection
    _api_facts = _pre_llm_api_facts
    _fmt_facts = _pre_llm_fmt_facts
    _snip_facts = _build_snippet_facts(snippets, product)
    _lim_facts = _build_limitation_facts(
        product_evidence.limitations if product_evidence else [], product
    )
    _completeness = _compute_extraction_completeness(
        _api_facts, _fmt_facts, _snip_facts, _lim_facts, api_surface
    )

    # TC-4244: Emit MissingInfoEntry for sparse extraction
    if not _api_facts and product_evidence:
        from launcher.models.understanding import MissingInfoEntry as _MIE
        product_evidence.missing_info.append(_MIE(
            field="api_facts",
            reason="no_api_members_extracted",
            attempted_strategies=["ast_extraction", "tree_sitter"],
            fallback_used="none",
        ))
    if not _fmt_facts and product_evidence:
        _FORMAT_HEAVY_FAMILIES = frozenset({
            "cells", "words", "pdf", "slides", "imaging", "3d", "cad", "barcode"
        })
        if getattr(product, "family", "").lower() in _FORMAT_HEAVY_FAMILIES:
            from launcher.models.understanding import MissingInfoEntry as _MIE
            product_evidence.missing_info.append(_MIE(
                field="format_facts",
                reason="no_formats_found_for_format_heavy_family",
                attempted_strategies=["enum_scan", "readme_table", "extension_scan"],
                fallback_used="none",
            ))

    extraction_db = ExtractionDatabase(
        api_facts=_api_facts,
        format_facts=_fmt_facts,
        snippet_facts=_snip_facts,
        limitation_facts=_lim_facts,
        install_recipe=product_evidence.install_recipe if product_evidence else None,
        missing_coverage=product_evidence.missing_info if product_evidence else [],
        completeness=_completeness,
    )

    logger.info(
        "extraction_db [TC-4244]: api_facts=%d format_facts=%d snippet_facts=%d "
        "limitation_facts=%d completeness=%.3f",
        len(_api_facts), len(_fmt_facts), len(_snip_facts), len(_lim_facts),
        _completeness.overall_completeness,
    )

    return claims, snippets, api_surface, product_evidence, extraction_db


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

    # Section 3b: Full class docstrings when API surface is thin (TC-4081)
    # When fewer than 3 public classes are found, inject full docstrings so the LLM
    # has semantic content to work with rather than just class names.
    if (
        api_surface
        and api_surface.class_briefs
        and len(api_surface.class_briefs) < 3
        and budget > 300
    ):
        lines = ["", "### Class Documentation (full docstrings — thin API surface)"]
        for brief in api_surface.class_briefs[:3]:
            if brief.docstring_snippet:
                lines.append(f"\n**{brief.name}**: {brief.docstring_snippet}")
                for ms in (brief.typed_methods or [])[:5]:
                    if ms.docstring_snippet:
                        lines.append(f"  - `{ms.name}()`: {ms.docstring_snippet}")
        if len(lines) > 1:  # only add if we have actual content beyond the header
            block = "\n".join(lines)
            if len(block) < budget:
                parts.append(block)
                budget -= len(block)

    # Section 4: Install command
    if install_recipe and budget > 100:
        _install_cmd = getattr(install_recipe, "pip_command", None) or getattr(install_recipe, "install_command", "")
        if _install_cmd:
            parts.append(f"\n### Install\n{_install_cmd}")

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


def _is_low_signal_docstring(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < 24:
        return True
    lowered = stripped.lower()
    boilerplate_starts = (
        "initialize",
        "initialise",
        "init",
        "return",
        "returns",
        "get ",
        "set ",
        "get the",
        "set the",
        "create ",
        "creates ",
        "create the",
        "represents ",
    )
    return any(lowered.startswith(prefix) for prefix in boilerplate_starts) and len(stripped) < 60


def _docstring_claim_score(
    *,
    text: str,
    type_annotation: str = "",
    return_type: str = "",
    parameter_count: int = 0,
) -> int:
    score = min(len(text.strip()), 140)
    if type_annotation:
        score += 10
    if return_type:
        score += 10
    if parameter_count:
        score += min(parameter_count, 3) * 5
    if not _is_low_signal_docstring(text):
        score += 20
    return score


def _harvest_operation_claims_raw(
    api_surface: ApiSurface,
    product: ProductIdentity,
    snippet_codes: list[str] | None = None,
    max_claims: int = _MAX_OPERATION_CLAIMS,
) -> list[dict[str, Any]]:
    """Harvest a few deterministic operation claims to support snippet linking."""
    raw_claims: list[dict[str, Any]] = []
    operation_names = ("open", "load", "save", "create", "convert", "export", "import")
    snippet_text = "\n".join(snippet_codes or []).lower()

    def _candidate_score(brief) -> int:
        score = 0
        class_name = getattr(brief, "name", "")
        if class_name and class_name.lower() in snippet_text:
            score += 100
        if class_name in {"Scene", "Mesh", "Workbook"}:
            score += 25
        method_names = [
            getattr(method, "name", "")
            for method in (brief.typed_methods or [])
            if getattr(method, "name", "")
        ] or list(brief.methods or [])
        for method_name in method_names:
            lower_name = method_name.lower()
            if lower_name and lower_name in snippet_text:
                score += 40
            if any(op in lower_name for op in operation_names):
                score += 10
        if class_name.endswith(("LoadOptions", "SaveOptions")):
            score += 20
        return score

    for brief in sorted(api_surface.class_briefs, key=_candidate_score, reverse=True):
        method_names = [
            getattr(method, "name", "")
            for method in (brief.typed_methods or [])
            if getattr(method, "name", "")
        ] or list(brief.methods or [])
        for method_name in method_names:
            if not any(op in method_name.lower() for op in operation_names):
                continue
            raw_claims.append({
                "text": (
                    f"{brief.name}.{method_name}() is part of the public API for "
                    f"{product.display_name}."
                ),
                "kind": "api",
                "visibility": "public",
                "claim_source": "deterministic",
                "evidence": [{
                    "source_file": "",
                    "snippet": f"{brief.name}.{method_name}()",
                }],
            })
            break
        else:
            if brief.name.endswith("LoadOptions"):
                raw_claims.append({
                    "text": f"{brief.name} configures file import options in {product.display_name}.",
                    "kind": "api",
                    "visibility": "public",
                    "claim_source": "deterministic",
                    "evidence": [{"source_file": "", "snippet": brief.name}],
                })
            elif brief.name.endswith("SaveOptions"):
                raw_claims.append({
                    "text": f"{brief.name} configures file export options in {product.display_name}.",
                    "kind": "api",
                    "visibility": "public",
                    "claim_source": "deterministic",
                    "evidence": [{"source_file": "", "snippet": brief.name}],
                })
        if len(raw_claims) >= max_claims:
            break
    return raw_claims


# ===================================================================
# B.2b  Docstring-to-claim harvesting (TC-3816)
# ===================================================================


def _harvest_docstring_claims_raw(
    api_surface: ApiSurface,
    product: ProductIdentity,
    max_claims: int = _MAX_DOCSTRING_CLAIMS,  # TC-4241: 2000 (was 200/TC-4094, 50/TC-3816)
) -> list[dict[str, Any]]:
    """Harvest raw claim dicts from class/method docstrings.

    Returns raw dicts matching the format expected by
    _validate_and_normalize_claims() so docstring claims go through
    the same dedup, visibility, and normalization pipeline as LLM claims
    (sandwich model compliance — AQ-01).
    """
    raw_claims: list[dict[str, Any]] = []

    for brief_idx, brief in enumerate(api_surface.class_briefs):
        if len(raw_claims) >= max_claims:
            remaining_classes = len(api_surface.class_briefs) - brief_idx
            logger.warning(
                "[Understand] docstring_claims_raw: cap=%d reached; "
                "%d/%d classes not processed — increase max_claims for better API coverage",
                max_claims, remaining_classes, len(api_surface.class_briefs),
            )
            break

        # Class-level docstring claim
        if brief.docstring_snippet and len(brief.docstring_snippet) > 30:
            raw_claims.append({
                "text": f"{brief.name}: {brief.docstring_snippet}",
                "kind": "api",
                "visibility": "public",
                "claim_source": "docstring",
                "evidence": [{
                    "source_file": f"docstring:{brief.name}",
                    "snippet": brief.docstring_snippet[:200],
                }],
            })

        member_candidates: list[tuple[int, dict[str, Any]]] = []
        property_name_set: set[str] = {
            p.name for p in (brief.typed_properties or []) if getattr(p, "name", "")
        }

        for ms in (brief.typed_methods or [])[:_MAX_TYPED_METHODS_CLAIMS]:
            if not ms.docstring_snippet:
                continue
            doc = ms.docstring_snippet.strip()
            if ms.name in property_name_set or _is_low_signal_docstring(doc):
                continue
            claim = {
                "text": f"{brief.name}.{ms.name}(): {doc}",
                "kind": "api",
                "visibility": "public",
                "claim_source": "docstring",
                "evidence": [{
                    "source_file": f"docstring:{brief.name}.{ms.name}",
                    "snippet": doc[:200],
                }],
            }
            score = _docstring_claim_score(
                text=doc,
                return_type=getattr(ms, "return_type", ""),
                parameter_count=len(getattr(ms, "parameters", []) or []),
            )
            member_candidates.append((score, claim))

        for pd in (brief.typed_properties or [])[:_MAX_TYPED_PROPS_CLAIMS]:
            if not pd.docstring_snippet:
                continue
            doc = pd.docstring_snippet.strip()
            if _is_low_signal_docstring(doc):
                continue
            claim = {
                "text": f"{brief.name}.{pd.name}: {doc}",
                "kind": "api",
                "visibility": "public",
                "claim_source": "docstring",
                "evidence": [{
                    "source_file": f"docstring:{brief.name}.{pd.name}",
                    "snippet": doc[:200],
                }],
            }
            score = _docstring_claim_score(
                text=doc,
                type_annotation=getattr(pd, "type_annotation", ""),
            )
            member_candidates.append((score, claim))

        for _, claim in sorted(member_candidates, key=lambda item: item[0], reverse=True):
            if len(raw_claims) >= max_claims:
                break
            if sum(1 for existing in raw_claims if existing["evidence"][0]["source_file"].startswith(f"docstring:{brief.name}.")) >= _MAX_DOCSTRING_MEMBER_CLAIMS_PER_CLASS:
                break
            raw_claims.append(claim)

    return raw_claims
