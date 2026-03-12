# TC-3778 Linker Healing Plan

## Context

Self-review of TC-3778 (linker integration) identified 7 concrete gaps
ranging from a correctness bug (slug vs page_id mismatch in self-review)
to missing telemetry and untested LLM paths. This plan converts each gap
into an executable taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | self_review Check 4 compares `p.slug` against `cl.source` (page_id) — always mismatches | **Critical** | LH-01 |
| G-02 | self_review Check 5 compares `cl.target` (page_id) against `page_slugs` — always mismatches | **Critical** | LH-01 |
| G-03 | Deleting `_build_cross_links` lost TOC→child link generation — functional regression | **High** | LH-02 |
| G-04 | `generate_anchor_texts` with a live (mocked) LLM is never tested | **Medium** | LH-03 |
| G-05 | `_infer_section` duplicated between worker.py and linker.py | **Low** | LH-04 |
| G-06 | No `emit_event` calls for linker phase; no per-page logging | **Medium** | LH-05 |
| G-07 | Unused `ir_by_id` variable in `link_pages`; unused imports in test file | **Low** | LH-06 |
| G-08 | `hasattr(context, "pipeline_config")` — WorkerContext has no such attribute | **Medium** | LH-07 |

---

## Taskcard LH-01 — Fix slug/page_id mismatch in self-review checks

**Status:** Done
**Gap linkage:** G-01, G-02

### Role
Senior engineer. Drop-in, production-ready fix.

### Scope

**Fix:**
- Check 4 (`linked_sources`): CrossLink.source contains `page_id`. The check
  compares against `p.slug`. Must build a `page_id` set from GeneratedPage
  (using `content_path` or deriving page_id) or change CrossLink to use slug.
  Cleanest fix: build a lookup `slug_to_page_id` from manifest pages, then
  compare `cl.source` against page_id values. Alternatively, since
  `GeneratedPage` doesn't store `page_id`, the linker should emit `slug` as
  `CrossLink.source` instead of `page_id`.

  **Chosen approach:** Change `link_pages` in linker.py to use `slug`
  (derived from `PlannedPage.frontmatter["slug"]` or `page_id`) as
  `CrossLink.source` and `CrossLink.target`, matching what `GeneratedPage`
  stores. This aligns the contract: manifest speaks slugs everywhere.

- Check 5 (`broken_links`): Same issue — `cl.target` is `page_id` but
  compared against `page_slugs`. Fix follows from the source fix above.

**Allowed paths:**
- `src/launcher/shared/linker.py` (change CrossLink source/target to slug)
- `src/launcher/workers/generate/worker.py` (self-review checks already correct after source fix)
- `tests/test_linker.py` (update E2E test assertions to expect slugs)

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** `test_link_pages_end_to_end` passes; new test
  `test_cross_link_uses_slug_not_page_id` verifies `cl.source` matches
  `GeneratedPage.slug` format.
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v` — all pass
- **Regression:** Full suite still passes.
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

### Deliverables

1. Updated `linker.py`: `link_pages` builds slug from PlannedPage and uses
   it as CrossLink.source/target.
2. Updated `tests/test_linker.py`: assertions verify slug-based cross-links.
3. No schema change needed (source/target are already `string` type).

### Hard rules

- Keep `CrossLink` public signature unchanged (source, target are strings).
- Deterministic: slug derivation must match worker.py's
  `page_plan.frontmatter.get("slug", page_plan.page_id)`.
- Keep code/docs/tests in sync.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Check 4 and 5 correctly identify missing/broken links using slugs |
| Testability | Dedicated test proves slug alignment between linker and manifest |
| Robustness | No KeyError if slug key missing from frontmatter (fallback to page_id) |

### Now (runbook)

```bash
# 1. Edit linker.py: in link_pages, derive slug from page_plan, use as CrossLink source/target
# 2. Edit tests: update E2E assertions, add test_cross_link_uses_slug_not_page_id
# 3. Run linker tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

---

## Taskcard LH-02 — Restore TOC→child cross-links

**Status:** Done
**Gap linkage:** G-03

### Role
Senior engineer. Drop-in, production-ready fix.

### Scope

**Fix:**
The deleted `_build_cross_links` function generated TOC→child links
(`link_type="toc_child"`). The linker's `score_links` explicitly excludes
TOC pages (correct for See Also). But TOC→child links are a separate
concern that must be preserved.

Add a `_build_toc_child_links` function in `linker.py` that:
1. Finds all TOC pages in `page_index`.
2. For each non-TOC page, finds the TOC page in the same section.
3. Creates a CrossLink with `link_type="toc_child"`.

Call this at the end of `link_pages`, after the See Also pass.

**Allowed paths:**
- `src/launcher/shared/linker.py`
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New test `test_toc_child_links_generated` verifies TOC→child
  CrossLinks appear with `link_type="toc_child"`.
- **Tests:** Existing `test_inject_links_skips_toc` still passes (TOC pages
  don't get See Also sections, but do emit toc_child links).
- **CLI:** All linker tests pass.
- **Regression:** Full suite passes.

### Deliverables

1. New function `_build_toc_child_links(page_index)` in linker.py.
2. `link_pages` calls it and appends results to `all_cross_links`.
3. New test in test_linker.py.

### Hard rules

- TOC pages must NOT get See Also injection (existing behavior preserved).
- TOC→child links use `link_type="toc_child"`, not `"see_also"`.
- Deterministic ordering: sorted by target page_id.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Every non-TOC page in a section with a TOC gets a toc_child link |
| Consistency | link_type field matches schema enum `["see_also", "toc_child"]` |
| Testability | Test verifies both presence of toc_child links and absence of see_also on TOC |

### Now (runbook)

```bash
# 1. Add _build_toc_child_links to linker.py
# 2. Call from link_pages after See Also loop
# 3. Add test_toc_child_links_generated to test_linker.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

---

## Taskcard LH-03 — Add mock LLM test for anchor text generation

**Status:** Done
**Gap linkage:** G-04

### Role
Senior engineer. Drop-in, production-ready test.

### Scope

**Fix:**
The `generate_anchor_texts` function is only tested via the E2E test with
`context=None` (fallback path). Need a test that mocks the LLM call and
verifies the full sandwich: pre-LLM prompt building, LLM response parsing,
post-LLM validation.

**Allowed paths:**
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New tests:
  - `test_anchor_text_llm_success`: Mock `_call_llm_for_anchors` returning
    valid JSON array. Verify anchors are applied to ScoredLinks.
  - `test_anchor_text_llm_returns_garbage`: Mock returns non-JSON. Verify
    fallback to titles.
  - `test_anchor_text_llm_returns_too_long`: Mock returns anchors with >10
    words. Verify individual fallback per anchor.
- **No mock data in production paths:** Tests use `unittest.mock.patch`.
- **No network in offline tests:** LLM is mocked, no real calls.

### Deliverables

1. Three new test functions in `tests/test_linker.py`.
2. Remove unused imports (`AsyncMock`, `MagicMock`, `patch`) if not yet used,
   or use them properly.

### Hard rules

- No network calls in tests.
- Tests must be deterministic (PYTHONHASHSEED=0).
- Mock target is `launcher.shared.linker._call_llm_for_anchors`.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | All three LLM paths tested: success, garbage, partial failure |
| Robustness | Fallback behavior verified for each failure mode |
| Coverage | The most complex function in the module is now fully covered |

### Now (runbook)

```bash
# 1. Add 3 test functions to test_linker.py using @patch on _call_llm_for_anchors
# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
```

---

## Taskcard LH-04 — Deduplicate _infer_section helper

**Status:** Done
**Gap linkage:** G-05

### Role
Senior engineer. Drop-in refactor.

### Scope

**Fix:**
`_infer_section(page_id)` is duplicated in `worker.py` (takes PlannedPage)
and `linker.py` (takes str page_id). Extract to a shared location and
import in both.

Best location: keep in `linker.py` as the canonical version (takes str),
and have `worker.py` call it. The worker.py version takes `PlannedPage`
and extracts `page_id` — change it to a thin wrapper that calls the
linker version.

**Allowed paths:**
- `src/launcher/shared/linker.py` (export `_infer_section` as `infer_section`)
- `src/launcher/workers/generate/worker.py` (import and call)

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes (no behavior change).
- **CLI:** `_infer_section` produces identical results.

### Deliverables

1. Rename `_infer_section` to `infer_section` in linker.py (public API for Generate worker).
2. Worker.py imports `infer_section` from linker and uses it.
3. Remove duplicate function body from worker.py.

### Hard rules

- Behavior must be identical: `page_id.split("-", 1)[0]` with fallback to `"docs"`.
- Keep public API stable for worker.py.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | Single source of truth for section inference |
| Minimality | Pure rename+import, no logic change |

### Now (runbook)

```bash
# 1. Rename _infer_section to infer_section in linker.py
# 2. Import in worker.py, replace local _infer_section
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

---

## Taskcard LH-05 — Add linker telemetry events

**Status:** Done
**Gap linkage:** G-06

### Role
Senior engineer. Drop-in observability improvement.

### Scope

**Fix:**
The linker pass emits no pipeline events, breaking the pattern where every
worker phase emits `*_started` / `*_completed` events.

Add:
1. `linker_started` event (emitted before scoring) with `{pages: N}`.
2. `linker_completed` event (emitted after injection) with
   `{cross_links: N, pages_with_see_also: N, llm_anchor_calls: N}`.
3. Debug-level per-page logging: scored link count per page.

**Allowed paths:**
- `src/launcher/shared/linker.py`
- `src/launcher/workers/generate/worker.py`
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New test `test_linker_emits_events` with a mock context that
  captures `emit_event` calls. Verifies both events are emitted.
- **Regression:** Full suite passes.

### Deliverables

1. `link_pages` emits events via `context.emit_event()` (guarded by
   `if context`).
2. Debug logging for per-page link counts.
3. One new test.

### Hard rules

- Events guarded by `if context` (linker can run without context in tests).
- Event schema matches existing `emit_event(type, data, worker=)` pattern.
- No new dependencies.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Observability | Both events emitted; per-page debug logging present |
| Testability | Mock context verifies event emission |

### Now (runbook)

```bash
# 1. Add emit_event calls to link_pages in linker.py
# 2. Add context.emit_event in worker.py after linker call
# 3. Add test_linker_emits_events to test_linker.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
```

---

## Taskcard LH-06 — Remove dead code and unused imports

**Status:** Done
**Gap linkage:** G-07

### Role
Senior engineer. Cleanup.

### Scope

**Fix:**
1. `ir_by_id` in `link_pages` (linker.py line 477) is assigned but never
   used. Remove it.
2. `unittest.mock` imports (`AsyncMock`, `MagicMock`, `patch`) in
   test_linker.py are unused. Remove them (unless LH-03 uses them first —
   if LH-03 is done before this, only remove the ones still unused).

**Allowed paths:**
- `src/launcher/shared/linker.py`
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes.
- **CLI:** No linter warnings for unused imports/variables.

### Deliverables

1. Remove `ir_by_id = ...` line from linker.py.
2. Clean up unused imports from test_linker.py.

### Hard rules

- Do not remove imports that LH-03 will add usage for. If LH-03 runs
  first, this taskcard adjusts accordingly.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Minimality | Zero dead code, zero unused imports |

### Now (runbook)

```bash
# 1. Remove ir_by_id line from linker.py
# 2. Remove unused imports from test_linker.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
```

---

## Taskcard LH-07 — Fix pipeline_config access on WorkerContext

**Status:** Done
**Gap linkage:** G-08

### Role
Senior engineer. Drop-in fix.

### Scope

**Fix:**
Worker.py line 103-104 uses `hasattr(context, "pipeline_config")` but
`WorkerContext` has no such attribute. The linker config should be loaded
from `context.config` (which is a `RunConfig`) or from a raw YAML read.

Two approaches:
- **A (recommended):** Load pipeline.yaml directly in worker.py using the
  existing `configs/pipeline.yaml` path, parse the `linker` section.
  This matches how other pipeline config is loaded.
- **B:** Add a `pipeline_config` dict to WorkerContext. Too invasive.

Choose A: read pipeline.yaml, parse linker section, pass to `load_linker_config`.

**Allowed paths:**
- `src/launcher/workers/generate/worker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes.
- **Config respected end-to-end:** `pipeline.yaml` linker section values
  are actually used (not silently defaulted).
- **Regression:** No behavior change when `pipeline.yaml` has no `linker`
  section (defaults apply).

### Deliverables

1. Worker.py: load `configs/pipeline.yaml`, extract linker section, pass
   to `load_linker_config`. Remove `hasattr` guard.

### Hard rules

- No changes to WorkerContext.
- Graceful default if `pipeline.yaml` missing or has no `linker` section.
- No new dependencies.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Pipeline linker config is actually loaded and used |
| Robustness | Missing file/section → defaults apply without error |

### Now (runbook)

```bash
# 1. In worker.py, load pipeline.yaml at top of run(), extract linker config
# 2. Remove hasattr guard
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

---

## Execution Order

Recommended sequence (dependencies):

```
LH-01 (critical bug fix)     ← do first, blocks correct self-review
LH-02 (restore TOC links)    ← independent
LH-07 (fix config loading)   ← independent
LH-03 (mock LLM tests)       ← before LH-06 (imports)
LH-05 (telemetry)            ← independent
LH-04 (dedup helper)         ← independent
LH-06 (dead code cleanup)    ← after LH-03
```

Parallelizable: {LH-01, LH-02, LH-07} then {LH-03, LH-04, LH-05} then {LH-06}.
