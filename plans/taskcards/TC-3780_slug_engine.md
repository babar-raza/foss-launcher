---
id: TC-3780
title: "Slug Engine — Full v1 Port"
status: In-Progress
priority: High
owner: Agent-B
updated: "2026-03-07"
tags: [phase-2, slug, port]
depends_on: [TC-3779]
allowed_paths:
  - plans/taskcards/TC-3780_slug_engine.md
  - src/launcher/shared/slug_engine.py
  - src/launcher/workers/evaluate/checks/slug_safety.py
  - tests/unit/shared/test_slug_engine.py
  - reports/agents/B/TC-3780/
evidence_required:
  - reports/agents/B/TC-3780/evidence.md
---

# Taskcard TC-3780 — Slug Engine — Full v1 Port

## Objective

Port v1's full 6-layer slug generation system into a centralized `slug_engine.py` module and a `slug_safety.py` evaluation check, adapted for v2's typed models. This provides the foundation for SEO-aware slug derivation across all page types in the v2 pipeline.

## Required spec references

- `specs/45_seo_slug_strategy.md` (v1 — slug strategy: 6 layers, evidence-aware derivation, blog workflow scoring)
- `specs/06_page_planning.md` (v1 — page roles: how roles map to slug patterns and howto templates)

## Scope

### In scope

- Create `src/launcher/shared/slug_engine.py` with all 6 slug layers:
  - `FAMILY_KEYWORD_MAP` (cells->spreadsheets, 3d->3d-models, note->notebooks, words->documents, pdf->pdf-files, slides->presentations, imaging->images)
  - `TOPIC_CATEGORY_MAP` (open->load_file, save->save_file, convert->convert_formats, etc.)
  - `SLUG_LEADING_STOP_WORDS` (~40 filler words)
  - `_HOWTO_SLUG_TEMPLATES` (5 intent templates)
  - `extract_family_keyword(family) -> str`
  - `derive_evidence_aware_slug(title, family, product_evidence, platform) -> str`
  - `derive_semantic_slug(text, max_length=40) -> str`
  - `derive_blog_evidence_slug(title, family, product_evidence, platform) -> str`
  - `strip_leading_stop_words(slug, min_remaining=2) -> str`
  - `score_blog_workflow(product_evidence, snippets, family, platform) -> dict`
  - `refine_slugs_batch(slugs, llm_client?) -> list[str]`
  - `validate_slug_safety(slug) -> list[str]`
- Create `src/launcher/workers/evaluate/checks/slug_safety.py` — port Gate 19 (slug safety evaluation check)
- Create `tests/unit/shared/test_slug_engine.py` — comprehensive tests for all layers

### Out of scope

- Planner integration (deferred to TC-3781 — planner will call slug_engine functions)
- Understand worker changes (deferred to TC-3779 — provides ProductEvidence model)

## Inputs

- v1 source code read via:
  - `git show main:src/launch/workers/_shared/slug_constants.py`
  - `git show main:src/launch/workers/w4_ia_planner/worker.py` (slug derivation functions)
- `ProductEvidence` model from TC-3779 (dependency)

## Outputs

- `src/launcher/shared/slug_engine.py` (~350 lines)
- `src/launcher/workers/evaluate/checks/slug_safety.py` (~80 lines)
- `tests/unit/shared/test_slug_engine.py` (~200 lines)

## Allowed paths

- `plans/taskcards/TC-3780_slug_engine.md`
- `src/launcher/shared/slug_engine.py`
- `src/launcher/workers/evaluate/checks/slug_safety.py`
- `tests/unit/shared/test_slug_engine.py`
- `reports/agents/B/TC-3780/`

### Allowed paths rationale

- **Taskcard**: Required by AG-002 governance.
- **slug_engine.py**: Central module housing all 6 slug layers and public API functions.
- **slug_safety.py**: Evaluation check (Gate 19 port) that validates slugs during the Evaluate worker phase.
- **test_slug_engine.py**: Unit tests proving all layers work correctly.
- **reports/agents/B/TC-3780/**: Evidence artifacts for acceptance verification.

## Implementation steps

### Step 1: Read v1 source

Read the v1 slug constants and derivation functions from the main branch:

```bash
git show main:src/launch/workers/_shared/slug_constants.py > /tmp/v1_slug_constants.py
git show main:src/launch/workers/w4_ia_planner/worker.py > /tmp/v1_w4_worker.py
```

Identify all constants (FAMILY_KEYWORD_MAP, TOPIC_CATEGORY_MAP, SLUG_LEADING_STOP_WORDS, _HOWTO_SLUG_TEMPLATES) and all slug-related functions.

### Step 2: Create slug_engine.py

Create `src/launcher/shared/slug_engine.py` with:

1. All 4 constant maps ported verbatim from v1.
2. All public functions adapted for v2 types:
   - `derive_evidence_aware_slug` takes `ProductEvidence` (pydantic model) instead of raw `product_facts` dict.
   - All functions use type annotations.
   - `refine_slugs_batch` accepts an optional `llm_client` parameter; falls back to algorithmic refinement (strip_leading_stop_words) when no client is provided.
3. `validate_slug_safety` returns a list of defect strings (empty = safe). Checks 5 defect classes:
   - Too short (< 2 segments)
   - Too long (> 60 chars)
   - Contains forbidden tokens (e.g., "untitled", "page", raw UUIDs)
   - Missing family keyword for non-blog pages
   - Duplicate consecutive segments

### Step 3: Create slug_safety.py evaluation check

Create `src/launcher/workers/evaluate/checks/slug_safety.py` that:

1. Implements the standard check interface (`def check(page, context) -> CheckResult`).
2. Calls `validate_slug_safety` from slug_engine.
3. Returns FAIL with defect details if any issues found; PASS otherwise.
4. Maps to Gate 19 severity (safety_critical = False, compensating gate).

### Step 4: Create test file

Create `tests/unit/shared/test_slug_engine.py` with:

1. Tests for `extract_family_keyword` — all 8 families produce expected keywords.
2. Tests for `derive_semantic_slug` — strips preambles, spec-headers, respects max_length.
3. Tests for `derive_evidence_aware_slug` — uses ProductEvidence, includes family keyword.
4. Tests for `derive_blog_evidence_slug` — adds family keyword when missing.
5. Tests for `strip_leading_stop_words` — removes filler, keeps min_remaining parts.
6. Tests for `validate_slug_safety` — detects all 5 defect classes.
7. Tests for `score_blog_workflow` — returns dict with expected keys.
8. Tests for `refine_slugs_batch` — algorithmic fallback when no LLM client.
9. Tests for all 5 howto templates producing valid slugs.

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
```

Verify all tests pass. Then run the full suite to check for regressions:

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

### Step 6: Capture evidence

Write test output and import verification to `reports/agents/B/TC-3780/evidence.md`.

## Failure modes

### Failure mode 1: Import cycle with models

**Detection**: `ImportError` or circular import traceback when importing `slug_engine`.
**Resolution**: `slug_engine.py` must only import from `launcher.models` (leaf dependency). It must never import from workers, orchestrator, or other shared modules that themselves import models. If ProductEvidence is not yet available (TC-3779 not merged), use a Protocol or TYPE_CHECKING import.
**Gate**: Build-time import validation.

### Failure mode 2: Slug collision from evidence-aware expansion

**Detection**: Two different pages with similar titles produce identical slugs in tests.
**Resolution**: `validate_slug_safety` catches duplicate consecutive segments. The planner (TC-3781) will handle cross-page collision detection by appending disambiguating suffixes. slug_engine itself is stateless and does not track seen slugs.
**Gate**: Gate 6 (permalink uniqueness) — downstream in planner.

### Failure mode 3: LLM refinement fails silently

**Detection**: `refine_slugs_batch` returns slugs unchanged after an LLM call that returned empty or malformed output.
**Resolution**: `refine_slugs_batch` must validate LLM output (each slug non-empty, no special chars, length within bounds). On any validation failure, fall back to algorithmic refinement via `strip_leading_stop_words`. Log a warning when fallback is triggered.
**Gate**: Sandwich principle — engineering validation wraps LLM output.

## Task-specific review checklist

1. [ ] `FAMILY_KEYWORD_MAP` covers all 8 families from v1 (cells, 3d, note, words, pdf, slides, imaging, and any additional)
2. [ ] All 5 howto templates produce valid slugs (no empty segments, no special chars)
3. [ ] `derive_semantic_slug` strips preambles and spec-headers before slugifying
4. [ ] `strip_leading_stop_words` keeps minimum 2 parts even when all parts are stop words
5. [ ] `derive_blog_evidence_slug` adds family keyword when missing from the generated slug
6. [ ] `validate_slug_safety` detects all 5 defect classes (too short, too long, forbidden tokens, missing family keyword, duplicate segments)
7. [ ] Tests cover each layer with at least 2 cases per function

## Deliverables

1. `src/launcher/shared/slug_engine.py` (~350 lines, all 6 layers + public API)
2. `src/launcher/workers/evaluate/checks/slug_safety.py` (~80 lines, Gate 19 port)
3. `tests/unit/shared/test_slug_engine.py` (~200 lines, comprehensive coverage)

## Acceptance checks

1. [ ] All slug_engine functions importable: `from launcher.shared.slug_engine import derive_evidence_aware_slug, validate_slug_safety`
2. [ ] Tests pass: `.venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v`
3. [ ] No import errors from other modules (no circular dependencies introduced)
4. [ ] Full test suite still passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q`

## Self-review

### Verification results

- [ ] Tests: X/X PASS
- [ ] Validation: slug_safety check PASS on sample pages
- [ ] Evidence captured: reports/agents/B/TC-3780/evidence.md

## E2E verification

```bash
# Import check
.venv/Scripts/python.exe -c "from launcher.shared.slug_engine import derive_evidence_aware_slug, derive_semantic_slug, validate_slug_safety; print('OK')"

# Unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v

# Full suite regression check
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

**Expected results**:
- Import check prints "OK" with no errors
- All unit tests in test_slug_engine.py pass
- Full test suite passes with 0 failures

## Integration boundary proven

**Upstream**: TC-3779 (Understand worker) provides `ProductEvidence` model consumed by `derive_evidence_aware_slug` and `derive_blog_evidence_slug`. v1 slug constants and functions provide the porting source.
**Downstream**: TC-3781 (Planner integration) will call `derive_evidence_aware_slug` and `derive_blog_evidence_slug` during page planning. The Evaluate worker will invoke `slug_safety.py` check during quality evaluation.
**Contract**: `slug_engine.py` functions accept primitive types (str, int) plus `ProductEvidence` (pydantic model) and return `str` or `list[str]`. `validate_slug_safety` returns `list[str]` (empty = no defects). `slug_safety.py` implements the standard check interface (`check(page, context) -> CheckResult`).
