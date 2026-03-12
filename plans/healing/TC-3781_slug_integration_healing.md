# TC-3781 Slug Integration — Healing Plan

## Context

Self-review of TC-3781 (Planner Slug Integration) identified 5 concrete gaps
ranging from a silent type mismatch that disables blog workflow scoring to
missing safety validation on evidence-derived slugs. All 1363 tests pass, but
the issues below would cause degraded or incorrect behavior in production
pipeline runs.

**Parent taskcard**: TC-3781 (Done — code landed)
**Source**: Self-review dated 2026-03-07

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | `score_blog_workflow` receives pydantic `Snippet` objects but expects dicts — snippet scoring is silently dead | Critical | SR-01 |
| G-02 | Evidence-derived slugs bypass `validate_slug_safety()` — malformed URLs possible | High | SR-02 |
| G-03 | No collision disambiguation when evidence-aware slugs produce duplicate page_ids | High | SR-03 |
| G-04 | `_refine_page_slugs` URL replacement uses naive `str.replace` — can corrupt URLs | Medium | SR-04 |
| G-05 | No logging/observability for slug enrichment decisions | Medium | SR-05 |
| G-06 | LLM refinement code path (`_refine_page_slugs`) completely untested | Medium | SR-06 |

---

## Taskcards

---

### SR-01 — Fix Snippet Type Mismatch in Blog Workflow Scoring

**Status**: Done
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`_enumerate_mandatory_pages` passes `list[Snippet]` (pydantic objects) to
`score_blog_workflow(product_evidence, snippets, ...)`. Inside
`score_blog_workflow`, the loop does `isinstance(s, dict)` which returns
`False` for pydantic objects, so `snippet_tag_set` and `snippet_claim_set`
remain empty. This means the +5 (conversion+snippet) and +3 (has_snippet)
scoring bonuses never fire. Blog workflow scoring is silently degraded to
verb-only scoring (+2 max), which may fail to produce enriched blog slugs
for repos that have relevant workflows with snippet evidence.

#### Scope

**Fix**: In `_enumerate_mandatory_pages` in `plan.py`, convert `Snippet`
pydantic objects to the dict format expected by `score_blog_workflow` before
calling it. Specifically, map each `Snippet` to
`{"tags": [], "claim_ids": s.claim_ids}`.

**Allowed paths**:
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` — all pass
- **Tests**:
  - New test: `test_blog_slug_with_snippet_evidence` — provides a workflow
    with `claim_ids` matching snippet `claim_ids`; asserts score >= 3
    (snippet bonus fires)
  - New test: `test_blog_scoring_uses_snippet_claim_ids` — unit test calling
    `score_blog_workflow` with converted snippet dicts; asserts
    `snippet_claim_set` is populated
  - Existing test `test_blog_slug_with_workflow_evidence` still passes
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: Conversion is pure data mapping
- **Full suite**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q` — 0 failures

#### Deliverables

- Modified `src/launcher/workers/planner/plan.py` — snippet-to-dict conversion
  before `score_blog_workflow` call
- Updated `tests/unit/workers/test_plan_slug_integration.py` — 2 new tests

#### Hard rules

- Keep `score_blog_workflow` public signature unchanged (it already accepts
  `list[Any]`)
- No new dependencies
- Deterministic: snippet conversion is a pure map, order preserved

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | `score_blog_workflow` receives dicts with `claim_ids` keys; snippet bonuses fire for matching workflows |
| Robustness | Empty snippets still produce valid fallback; pydantic Snippet with no claim_ids produces empty list |
| Testability | Both happy path (snippet match) and edge case (empty snippets) tested |
| Integration fit | No changes to `score_blog_workflow` signature or slug_engine.py |
| Minimality | 3-5 lines changed in plan.py, 2 new tests |

#### Now (runbook)

```bash
# 1. Edit plan.py — add snippet conversion before score_blog_workflow call
# 2. Add 2 new tests to test_plan_slug_integration.py
# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### SR-02 — Add Slug Safety Validation on Evidence-Derived Slugs

**Status**: Done
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`derive_evidence_aware_slug` and `_derive_optional_slug` produce slugs from
claim text and product evidence but never validate them with
`validate_slug_safety()`. A slug with doubled hyphens, repr tokens, or
consecutive stop words could flow into `page_id` and `content_path`,
producing broken Hugo URLs. This violates the project's sandwich principle
(engineering validation wraps every derived value).

#### Scope

**Fix**: After each evidence-derived slug is produced in
`_enumerate_mandatory_pages` (KB how-to and blog enrichment) and in
`_derive_optional_slug`, call `validate_slug_safety(slug)`. If issues are
found, log a debug message and fall back to the original/default slug.

**Allowed paths**:
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` — all pass
- **Tests**:
  - New test: `test_unsafe_evidence_slug_rejected` — mock `derive_evidence_aware_slug`
    to return a slug with doubled hyphens; assert the original slug is kept
  - New test: `test_safe_evidence_slug_accepted` — normal evidence produces
    slug that passes safety check
  - Existing tests still pass
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: Safety validation is pure string checking

#### Deliverables

- Modified `src/launcher/workers/planner/plan.py` — add `validate_slug_safety`
  import and calls at 3 sites (KB enrichment, blog enrichment, optional slug)
- Updated `tests/unit/workers/test_plan_slug_integration.py` — 2 new tests

#### Hard rules

- Import `validate_slug_safety` from `launcher.shared.slug_engine` (already
  available, just not imported in plan.py)
- No changes to `validate_slug_safety` signature
- Fallback must preserve original behavior exactly (not a new slug, but the
  pre-enrichment slug)
- Deterministic: safety check is pure string validation

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Every evidence-derived slug passes safety validation before use |
| Robustness | Unsafe slugs silently fall back to defaults; no crash, no corrupt URL |
| Observability | Debug log emitted when a slug is rejected with the reason |
| Spec alignment | Implements the sandwich principle per CLAUDE.md |
| Minimality | ~10 lines added to plan.py across 3 sites, 2 new tests |

#### Now (runbook)

```bash
# 1. Add validate_slug_safety to imports in plan.py
# 2. Add safety check after KB evidence slug derivation (line ~227)
# 3. Add safety check after blog workflow slug derivation (line ~265)
# 4. Add safety check in _derive_optional_slug before returning semantic slug
# 5. Add 2 tests
# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### SR-03 — Add Collision Disambiguation for Evidence-Derived Slugs

**Status**: Done
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

When evidence-aware slug derivation produces the same slug for two different
pages (e.g., two how-to pages that both resolve to
`how-to-load-pdf-files-python`), `_validate_plan` logs an error but does not
fix it. In production, this creates a Hugo build failure (duplicate
permalinks). The taskcard FM-1 explicitly requires appending a disambiguating
suffix on collision.

Additionally, `_derive_optional_slug` uses
`min(index, len(relevant) - 1)` which saturates — multiple optional pages
of the same kind get the same claim and thus the same slug. The existing
duplicate check (`any(p["page_id"] == page_id for p in pages)`) silently
drops the page, reducing page count without warning.

#### Scope

**Fix**: Add a `_disambiguate_slugs` function called after
`_apply_optional_expansion` that detects duplicate `page_id` values and
appends `-2`, `-3` suffixes. Also update `_derive_optional_slug` to
advance the claim index uniquely per-call by deduplicating claim selection
across calls for the same `kind`.

**Allowed paths**:
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` — all pass
- **Tests**:
  - New test: `test_collision_disambiguation_appends_suffix` — provide evidence
    that makes two KB how-to pages produce the same slug; assert both pages
    exist with unique page_ids (one with `-2` suffix)
  - New test: `test_optional_pages_no_silent_drop` — provide 3-budget optional
    policy with claims that produce same semantic slug; assert all 3 pages
    are present with distinct slugs
  - Existing `test_no_duplicate_page_ids` still passes
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: Disambiguation is pure string logic

#### Deliverables

- Modified `src/launcher/workers/planner/plan.py` — new `_disambiguate_slugs`
  function + call site in `run_plan` between steps 3 and 4
- Updated `tests/unit/workers/test_plan_slug_integration.py` — 2 new tests

#### Hard rules

- Disambiguation suffix must be deterministic (sorted page order, sequential counter)
- Must update both `page_id` and `content_path` when slug changes
- Keep `_validate_plan` permalink check as a secondary safety net
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Zero duplicate page_ids in any plan output regardless of evidence |
| Robustness | Disambiguation handles 2+ collisions (not just pairs) |
| Spec alignment | Implements FM-1 from TC-3781 taskcard |
| Testability | Collision scenario reproducible with controlled evidence input |
| Minimality | ~25 lines for disambiguator + 2 tests |

#### Now (runbook)

```bash
# 1. Add _disambiguate_slugs function to plan.py
# 2. Call it in run_plan between steps 3 and 4
# 3. Add 2 collision tests
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### SR-04 — Fix Naive URL Replacement in `_refine_page_slugs`

**Status**: Done
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`_refine_page_slugs` uses `fm["url"].replace(old_slug, new_slug)` which is a
global string replacement. If the old slug is a common substring (e.g.,
`"pdf"`), it matches in unrelated parts of the URL path (e.g.,
`/docs/pdf-manipulation/` would become `/docs/new-slug-manipulation/`).
This corrupts Hugo URLs.

#### Scope

**Fix**: Replace the naive `str.replace` with targeted last-segment
replacement. Parse the URL, replace only the final path segment if it matches
the old slug exactly, then reconstruct.

**Allowed paths**:
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` — all pass
- **Tests**:
  - New test: `test_refine_url_no_partial_match` — page with slug `"pdf"` and
    URL `/docs/pdf-manipulation/pdf/`; after refinement, only the last
    segment changes, not the middle one
  - Existing tests still pass
- **Config respected end-to-end**: No config changes

#### Deliverables

- Modified `src/launcher/workers/planner/plan.py` — `_refine_page_slugs` URL
  replacement logic (4-5 lines changed)
- Updated `tests/unit/workers/test_plan_slug_integration.py` — 1 new test

#### Hard rules

- Keep trailing slash convention (`/section/slug/`)
- URL reconstruction must handle edge cases (root URL, single-segment URL)
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | URL replacement only touches the target segment |
| Robustness | Handles edge cases: root URLs, slugs that don't appear in URL |
| Testability | Partial-match scenario explicitly tested |
| Minimality | 4-5 lines changed |

#### Now (runbook)

```bash
# 1. Replace str.replace with targeted segment replacement in _refine_page_slugs
# 2. Add 1 test
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### SR-05 — Add Observability Logging for Slug Enrichment Decisions

**Status**: Done
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

There is no logging when evidence-aware slug enrichment fires, falls back, or
when blog workflow scoring completes. In production, when a pilot run produces
unexpected slugs, there is no way to debug whether the enrichment was
attempted, succeeded, or fell back — and why.

#### Scope

**Fix**: Add `logger.debug` calls at 4 sites in `plan.py`:
1. After KB evidence slug enrichment succeeds (log old → new slug)
2. After KB evidence slug enrichment falls back (log reason)
3. After blog workflow scoring completes (log slug, score)
4. In `_derive_optional_slug` when claim-derived slug is used vs fallback

**Allowed paths**:
- `src/launcher/workers/planner/plan.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q` — all pass (logging doesn't break tests)
- **Tests**: No new tests needed (logging is observability, not behavior)
- **Config respected end-to-end**: Uses existing `logger` instance

#### Deliverables

- Modified `src/launcher/workers/planner/plan.py` — 4 `logger.debug` calls

#### Hard rules

- Use `logger.debug` (not info/warning) — this is diagnostic detail
- Log both old and new slug values for traceability
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Observability | Every enrichment decision path has a log statement |
| Minimality | 4 one-line log calls, no behavioral changes |
| Production grading | DEBUG level won't spam production logs |

#### Now (runbook)

```bash
# 1. Add 4 logger.debug calls to plan.py
# 2. Run full suite to verify no regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### SR-06 — Add Tests for LLM Refinement Code Path

**Status**: Done
**Gap linkage**: G-06
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`_refine_page_slugs` (lines 569-611 of plan.py) is completely untested.
The code path is only activated when `llm_client is not None`, which no
current caller provides. When the LLM integration is eventually wired in,
any bugs in this function will be discovered in production, not tests.

#### Scope

**Fix**: Add tests using a mock LLM client that exercises `_refine_page_slugs`
through `run_plan(llm_client=mock)`. Test both successful refinement and
fallback when the mock returns invalid output.

**Allowed paths**:
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden**: Any other file/path (no code changes, tests only).

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` — all pass
- **Tests**:
  - New test: `test_llm_refinement_updates_frontmatter_slug` — mock LLM returns
    valid cleaned slugs; assert frontmatter slugs are updated
  - New test: `test_llm_refinement_fallback_on_invalid_output` — mock LLM
    returns wrong number of lines; assert original slugs preserved
  - New test: `test_llm_refinement_rejects_unsafe_slug` — mock LLM returns
    slug with special characters; assert original kept
- **No mock data in production paths**: Tests only
- **No network in offline tests**: Mock LLM client, no network calls

#### Deliverables

- Updated `tests/unit/workers/test_plan_slug_integration.py` — 3 new tests
  with `MockLLMClient` helper class

#### Hard rules

- Mock must implement `chat_completion(messages, temperature)` matching the
  interface expected by `refine_slugs_batch`
- No network calls in tests
- Deterministic: mock returns fixed strings

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Testability | Happy path, error path, and safety-rejection path all covered |
| Robustness | Mock exercises the exact interface contract |
| Coverage | `_refine_page_slugs` lines 569-611 fully exercised |
| Minimality | 3 tests + 1 mock class, no code changes |

#### Now (runbook)

```bash
# 1. Add MockLLMClient class to test file
# 2. Add 3 new tests
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
