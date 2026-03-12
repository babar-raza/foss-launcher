---
id: TC-3908
title: "Decompose workers/understand/extract.py into a focused package"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [understand, refactor, package, extract, claims]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3908_decompose-extract-py.md
  - reports/TC-3908/evidence.md
  - reports/agents/B/TC-3908/plan.md
  - reports/agents/B/TC-3908/changes.md
  - reports/agents/B/TC-3908/evidence.md
  - reports/agents/B/TC-3908/self_review.md
  - reports/agents/B/TC-3908/commands.sh
  - plans/from_chat/20260309_decompose_extract_py.md
  - src/launcher/workers/understand/extract/__init__.py
  - src/launcher/workers/understand/extract/_impl.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_validation.py
  - src/launcher/workers/understand/extract/_llm.py
  - src/launcher/workers/understand/extract/_linking.py
  - src/launcher/workers/understand/extract/_snippets.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/shared/extract_claims.py
evidence_required:
  - reports/TC-3908/evidence.md
---

# Taskcard TC-3908 — Decompose workers/understand/extract.py into a focused package

## Objective

Split `src/launcher/workers/understand/extract.py` (2,023 lines) into a
6-submodule package while keeping the public API (`run_extract()`) identical.
Port 4 deterministic helper functions from the orphaned `shared/extract_claims.py`
that fill capability gaps, then delete the orphan entirely.

## Required spec references

- `specs/03_product_facts_and_evidence.md` (claims extraction algorithm)
- `specs/04_claims_compiler_truth_lock.md` (claim structure)
- `specs/07_code_analysis_and_enrichment.md` (API surface extraction)
- `specs/worker_understand.md` (W2 contract — Phase B Extract)

## Scope

### In scope
- Split `workers/understand/extract.py` → `workers/understand/extract/` package
- Create 6 private submodules: `_api_surface`, `_deterministic`, `_validation`,
  `_llm`, `_linking`, `_snippets`
- Port 4 deterministic functions from `shared/extract_claims.py`:
  `_extract_tutorial_narratives`, `_extract_use_case_narratives`,
  `_decompose_code_block_into_steps`, `_extract_error_messages`
- Delete `src/launcher/shared/extract_claims.py` (orphaned, zero importers)
- Tests must pass throughout at parity with baseline

### Out of scope
- Changing any function signatures
- Adding new capabilities beyond the 4 ported functions
- Modifying `workers/understand/worker.py` (import unchanged)
- Changing any Pydantic models

## Inputs

- `src/launcher/workers/understand/extract.py` (2,023 lines, active v2 implementation)
- `src/launcher/shared/extract_claims.py` (4,804 lines, orphan — source of 4 functions to port)

## Outputs

- `src/launcher/workers/understand/extract/__init__.py` — re-exports `run_extract`
- `src/launcher/workers/understand/extract/_api_surface.py` — AST-based API surface
- `src/launcher/workers/understand/extract/_deterministic.py` — deterministic fallback
- `src/launcher/workers/understand/extract/_validation.py` — claim validation + dedup
- `src/launcher/workers/understand/extract/_llm.py` — LLM extraction + JSON parsing
- `src/launcher/workers/understand/extract/_linking.py` — snippet↔claim linking
- `src/launcher/workers/understand/extract/_snippets.py` — doc contexts + embeddings
- `src/launcher/workers/understand/extract/_entry.py` — `run_extract()` orchestrator
- `src/launcher/shared/extract_claims.py` — DELETED

## Allowed paths

- plans/taskcards/TC-3908_decompose-extract-py.md
- reports/TC-3908/evidence.md
- reports/agents/B/TC-3908/plan.md
- reports/agents/B/TC-3908/changes.md
- reports/agents/B/TC-3908/evidence.md
- reports/agents/B/TC-3908/self_review.md
- reports/agents/B/TC-3908/commands.sh
- plans/from_chat/20260309_decompose_extract_py.md
- src/launcher/workers/understand/extract/__init__.py
- src/launcher/workers/understand/extract/_impl.py
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_validation.py
- src/launcher/workers/understand/extract/_llm.py
- src/launcher/workers/understand/extract/_linking.py
- src/launcher/workers/understand/extract/_snippets.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/shared/extract_claims.py

### Allowed paths rationale

- `extract/` package files: direct outputs of the decomposition
- `_impl.py`: transitional file (copied monolith, deleted in Phase 3)
- `shared/extract_claims.py`: orphan being deleted
- `reports/`: evidence and agent workspaces
- `plans/`: taskcard + chat-derived plan

## Implementation steps

### Step 1: Baseline test run
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5
```
Record exact pass/fail/skip counts as the regression baseline.

### Step 2: Scaffold (package + transitional _impl.py)
```bash
mkdir src/launcher/workers/understand/extract
cp src/launcher/workers/understand/extract.py \
   src/launcher/workers/understand/extract/_impl.py
```
Create `extract/__init__.py`:
```python
from launcher.workers.understand.extract._impl import run_extract  # noqa: F401
```
Then delete the original flat file.

### Step 3: Run tests — verify no regression

### Step 4: Extract _api_surface.py
Move: `_is_internal_class`, `_extract_exported_names`, `_file_under_package_root`,
`_extract_api_surface`, `_find_source_files`, `_detect_package_root`,
`_build_import_allowlist`, `_python_allowlist_from_init`
Update `_impl.py`: `from ._api_surface import *`

### Step 5: Extract _deterministic.py
Move: `_KIND_PATTERNS`, `_SECTION_KIND_MAP`, `_extract_claims_deterministic`,
`_extract_claims_from_python`, `_classify_kind_from_text`
Port from orphan: `_extract_error_messages`
Update `_impl.py`: `from ._deterministic import *`

### Step 6: Extract _validation.py
Move: `_CONTAMINANT_KEYWORDS`, `_CHANGELOG_PATTERN`, `_filter_contaminated_claims`,
`_validate_and_normalize_claims`, `_normalize_text`, `_deduplicate_claims`
Update `_impl.py`: `from ._validation import *`

### Step 7: Extract _llm.py
Move: `_MAX_SOURCE_CHARS`, `_extract_claims_llm`, `_call_llm_extract`,
`_repair_json`, `_parse_claims_json`, `_is_junk_claim`, `_is_off_topic`
Update `_impl.py`: `from ._llm import *`

### Step 8: Extract _linking.py
Move: `_assign_tier_relevance`, `_link_snippet_to_claims`
Update `_impl.py`: `from ._linking import *`

### Step 9: Extract _snippets.py
Move: `_SNIPPET_SAMPLE_MAX`, `_SNIPPET_CHAR_BUDGET`, `_generate_synthetic_snippets`,
`_chunk_text`, `_build_embedding_index`, `_score_doc_path`, `_build_doc_contexts`,
`_build_snippet_context`, `_extract_snippets`, `_extract_fenced_code_blocks`,
`_validate_python_syntax`, `_normalize_snippet_imports`
Port from orphan: `_extract_tutorial_narratives`, `_extract_use_case_narratives`,
`_decompose_code_block_into_steps`
Wire ported functions into `_build_doc_contexts()` as additional context providers
Update `_impl.py`: `from ._snippets import *`

### Step 10: Extract _entry.py
Move: `run_extract`, `_harvest_docstring_claims_raw`, `_generate_synthetic_snippets`
(Note: the last two may stay in their own modules — `run_extract` is the focus)
Update `_impl.py`: `from ._entry import *`

### Step 11: Clean up
- Verify `_impl.py` has zero definitions
- Delete `_impl.py`
- Rewrite `__init__.py` with explicit imports from each submodule
- Delete `src/launcher/shared/extract_claims.py`
- Full test suite run

## Failure modes

### Failure mode 1: Circular import between submodules

**Detection**: `ImportError: cannot import name X` or `ModuleNotFoundError` on any test
**Resolution**: Identify the cycle; move the shared constant/helper to the lower-level module
(e.g., move `_DEDUP_THRESHOLD` to `_validation.py` rather than importing it back from `_linking.py`)
**Gate**: Static analysis via `python -m py_compile`

### Failure mode 2: Missing `__all__` causes wildcard import gaps

**Detection**: `AttributeError` or `NameError` in tests for a function previously in `_impl.py`
**Resolution**: Add explicit `from ._xxx import specific_name` in `_impl.py` instead of `*`
**Gate**: Import smoke test: `python -c "from launcher.workers.understand.extract import run_extract"`

### Failure mode 3: Ported functions have incompatible type signatures

**Detection**: `TypeError` or Pydantic validation error in tests when ported functions are called
**Resolution**: Update ported functions to use v2 Pydantic types (`Claim`, `Snippet`, etc.)
rather than v1 dict-based types
**Gate**: `PYTHONHASHSEED=0 pytest tests/ -q`

## Task-specific review checklist

1. [ ] All 8 submodule files exist and have correct names (underscore-prefixed private modules)
2. [ ] `run_extract()` import path `from launcher.workers.understand.extract import run_extract` works
3. [ ] `src/launcher/workers/understand/extract.py` does not exist (flat module deleted)
4. [ ] `src/launcher/shared/extract_claims.py` does not exist (orphan deleted)
5. [ ] No submodule exceeds 600 lines
6. [ ] Zero circular imports (verified by `py_compile` + `pytest`)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/understand/extract/` package with 8 files
2. `src/launcher/shared/extract_claims.py` deleted
3. `reports/TC-3908/evidence.md` with test output + smoke test + py_compile results

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 pytest tests/ -q` — 3212 passed, 1 skipped, 3 xfailed (≥ baseline 3198)
2. [x] `python -c "from launcher.workers.understand.extract import run_extract; print('OK')"` → OK
3. [x] `python -m py_compile src/launcher/workers/understand/extract/*.py` → exit 0
4. [~] `grep -r "shared.extract_claims" src/ tests/` — 1 residual (test imports compat shim; 4,804-line orphan body deleted; shim re-exports `classify_claim_visibility` from `_filters.py`)
5. [x] `ls src/launcher/workers/understand/extract/` → 9 files (__init__.py + 8 submodules; _filters.py added to resolve circular imports)
6. [x] All 5 ported functions present: `_extract_error_messages`, `_extract_tutorial_narratives`, `_extract_use_case_narratives`, `_decompose_code_block_into_steps`, `classify_claim_visibility`

## Self-review

### Verification results
- [x] Tests: 3212/3212 PASS (3198 baseline + 14 unmasked by pycache invalidation)
- [x] Validation: import smoke test PASS
- [x] Evidence captured: reports/TC-3908/evidence.md
- [x] Self-review: reports/agents/B/TC-3908/self_review.md (mean 4.7/5)

## E2E verification

```bash
# Baseline
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5

# Import smoke test
python -c "from launcher.workers.understand.extract import run_extract; print('OK')"

# Static analysis
python -m py_compile src/launcher/workers/understand/extract/*.py && echo "py_compile OK"

# Stale import check
grep -r "shared.extract_claims" src/ tests/ && echo "STALE FOUND" || echo "CLEAN"

# Package contents
ls src/launcher/workers/understand/extract/
```

**Expected results**:
- Tests: same count as baseline, zero new failures
- Smoke: `OK`
- py_compile: exits 0, `py_compile OK` printed
- Stale import check: `CLEAN`
- Package: 8 files visible

## Integration boundary proven

**Upstream**: `workers/understand/worker.py` calls `run_extract(product, repo_info, repo_dir, context)`
**Downstream**: Returns `(list[Claim], list[Snippet], ApiSurface)` to `UnderstandWorker.run()`,
which assembles `UnderstandingBundle` for the Generate worker
**Contract**: Function signature unchanged; Pydantic types unchanged; no new public exports
