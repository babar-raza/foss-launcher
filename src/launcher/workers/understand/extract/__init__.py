"""Phase B — Extract: claim extraction package.

Public API: run_extract()

Submodules (private):
  _filters       — junk/off-topic claim filters shared across submodules
  _api_surface   — AST-based API surface extraction (multi-language)
  _deterministic — deterministic claim fallback + error message extraction
  _linking       — snippet↔claim linking + tier relevance assignment
  _llm           — LLM-based claim extraction + JSON parsing
  _validation    — claim normalization + dedup + contamination filtering
  _snippets      — doc context builder + embedding index + snippet extraction
  _entry         — run_extract() orchestrator (main entry point)
"""
# Public entry point
from launcher.workers.understand.extract._entry import run_extract  # noqa: F401

# Private symbols accessed by tests — re-exported at package level to preserve
# the original flat-module API surface (import path unchanged for callers).
from launcher.workers.understand.extract._entry import (  # noqa: F401
    _harvest_docstring_claims_raw,
    _build_evidence_context,
)
from launcher.workers.understand.extract._filters import (  # noqa: F401
    _THIRD_PARTY_INDICATORS,
    _is_junk_claim,
    _is_off_topic,
)
from launcher.shared.classify_claims import (  # noqa: F401
    classify_claim_visibility,
    _INTERNAL_VISIBILITY_TERMS,
    _INTERNAL_VISIBILITY_PATTERN,
)
from launcher.workers.understand.extract._api_surface import (  # noqa: F401
    _INTERNAL_CLASS_MARKERS,
    _is_internal_class,
    _extract_exported_names,
    _file_under_package_root,
    _extract_api_surface,
    _CODE_EXTENSIONS,
    _EXCLUDE_DIRS,
    _find_source_files,
    _detect_package_root,
    _build_import_allowlist,
    _python_allowlist_from_init,
)
from launcher.workers.understand.extract._deterministic import (  # noqa: F401
    _KIND_PATTERNS,
    _SECTION_KIND_MAP,
    _extract_error_messages,
    _extract_claims_deterministic,
    _extract_claims_from_python,
    _extract_method_docstring_claims,
    _classify_kind_from_text,
    extract_limitations,
    extract_workflow_examples,
)
from launcher.workers.understand.extract._contradiction_resolver import (  # noqa: F401
    resolve_contradictions,
)
from launcher.workers.understand.extract._linking import (  # noqa: F401
    _assign_tier_relevance,
    _link_snippet_to_claims,
    _redistribute_snippets,
    _LINKING_STOPWORDS,
)
from launcher.workers.understand.extract._llm import (  # noqa: F401
    _MAX_SOURCE_CHARS,
    _SNIPPET_SAMPLE_MAX,
    _SNIPPET_CHAR_BUDGET,
    _build_snippet_context,
    _extract_claims_llm,
    _call_llm_extract,
    _repair_json,
    _parse_claims_json,
)
from launcher.workers.understand.extract._validation import (  # noqa: F401
    _DEDUP_THRESHOLD,
    _CONTAMINANT_KEYWORDS,
    _CHANGELOG_PATTERN,
    _filter_contaminated_claims,
    _filter_weak_evidence,
    _score_evidence_relevance,
    _validate_and_normalize_claims,
    _normalize_text,
    _deduplicate_claims,
)
from launcher.workers.understand.extract._snippets import (  # noqa: F401
    _MAX_EMBEDDING_CHUNKS,
    _RELEVANCE_SCORES,
    _EXCLUDED_DOC_NAMES,
    _README_BUDGET_FRACTION,
    _DOC_DIR_NAMES,
    _EXAMPLE_DIR_NAMES,
    _score_doc_path,
    _build_doc_contexts,
    _extract_snippets,
    _extract_fenced_code_blocks,
    _validate_python_syntax,
    _normalize_snippet_imports,
    _chunk_text,
    _build_embedding_index,
)
from launcher.workers.understand.extract._narratives import (  # noqa: F401
    _extract_tutorial_narratives,
    _extract_use_case_narratives,
    _decompose_code_block_into_steps,
    _MAX_CLAIM_TEXT_LENGTH_EXTRACT,
    _MULTI_STMT_RE,
    _is_parameter_description,
    _is_code_like,
    _is_prose_like,
)
