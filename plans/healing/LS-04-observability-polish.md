---
id: LS-04
title: "TC-4064 observability polish: word count fix, export, progress counter"
status: Done
priority: Normal
owner: senior-engineer
updated: "2026-03-11"
tags: [streaming, observability, word-count, progress]
depends_on: [LS-02]
allowed_paths:
  - plans/healing/LS-04-observability-polish.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/orchestrator/__init__.py
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/orchestrator/test_stream_progress.py
evidence_required:
  - reports/LS-04/evidence.md
---

# Taskcard LS-04 — TC-4064 observability polish: word count fix, export, progress counter

## Gap linkage

Fixes: **LS-G4** (Minor — three observability/correctness issues with no production
correctness impact but measurable operator experience impact)

Sub-issues:
- **LS-G4a**: `page_generated` event word count uses pre-render IR block estimate, not
  the canonical `GeneratedPage.word_count` (computed from `len(markdown.split())`).
  Operators see a different number in the stream vs. the final summary report.
- **LS-G4b**: `StreamEventHandler` not exported from `orchestrator/__init__.py`.
  External importers (CLI, tests) must use the private path `from
  launcher.orchestrator.run_loop import StreamEventHandler`.
- **LS-G4c**: Sub-line progress format is `page: slug (450 words)` with no position
  counter, so operators watching a 30-page run cannot tell if they are 3/30 or 29/30.

## Objective

Three minor fixes to improve operator experience and internal correctness for the
streaming output introduced in TC-4064:

1. Emit `page_generated` after `GeneratedPage` is constructed (Phase 3 of the generate
   worker's `run()` method), using the authoritative `page.word_count` value.
2. Export `StreamEventHandler` from `orchestrator/__init__.py`.
3. Pass `total_pages` into the `page_generated` event payload, and format sub-lines as
   `page: slug (N/T, K words)` in `StreamEventHandler._on_custom_event`.

None of these changes alter the streaming protocol, the state schema, or the public
API. All are purely presentational/exporting improvements.

## Role

Senior engineer. Drop-in, production-ready.

## Required spec references

- `specs/worker_generate.md` (Section: Phase 3 — page construction and word count)
- `specs/system_contract.md` (Section: orchestrator module public API)

## Scope

### Fix
- **G4a**: In `generate/worker.py`, move the `page_generated` event emission to after
  `GeneratedPage(...)` is constructed; use `page.word_count` as the `words` value.
  Remove the early `sum(len(b.content.split()) ...)` estimate.
- **G4b**: Add `from .run_loop import StreamEventHandler` to `orchestrator/__init__.py`
  (LS-02 may already add `safe_stream_event` there; this adds `StreamEventHandler`).
- **G4c**: Add an optional `total` key to the `page_generated` event payload (emitted
  by the generate worker when `total_pages` is known). Update
  `StreamEventHandler._on_custom_event` for `page_generated` to format
  `(N/T, K words)` when `total` is present, `(K words)` when absent.

### Allowed paths
- `src/launcher/workers/generate/worker.py`
- `src/launcher/orchestrator/__init__.py`
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Forbidden
Any other file. In particular: do NOT touch `evaluate/worker.py` (G4a fix is
generate-only), `state.py` (that is LS-03's scope), or `graph_builder.py`.

## Inputs

- `src/launcher/workers/generate/worker.py` — current `_process_page` + `run()` Phase 3
- `src/launcher/orchestrator/run_loop.py` — current `_on_custom_event` formatting
- `src/launcher/orchestrator/__init__.py` — current exports

## Outputs

- Updated `generate/worker.py` — event emission after `GeneratedPage` construction
- Updated `run_loop.py` — `(N/T, K words)` formatting in `_on_custom_event`
- Updated `orchestrator/__init__.py` — `StreamEventHandler` re-exported
- Updated test — verify `(3/12)` format and canonical word count

## Allowed paths (frontmatter echo)

- `plans/healing/LS-04-observability-polish.md`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/orchestrator/__init__.py`
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_stream_progress.py`

### Allowed paths rationale
- `generate/worker.py` — contains the early word-count estimate that must be removed
- `orchestrator/__init__.py` — must export `StreamEventHandler`
- `run_loop.py` — contains the `_on_custom_event` formatting logic
- `test_stream_progress.py` — primary test file for `StreamEventHandler` formatting

## Implementation steps

### Step 1: Fix G4a — canonical word count in `page_generated` event

In `generate/worker.py`, locate `_process_page` (or wherever the early word-count
estimate is computed and `_safe_stream_event("page_generated", ...)` is called).

**Remove** the block:
```python
word_count = sum(
    len(b.content.split()) if b.content else 0
    for s in p_ir.sections for b in s.blocks
)
await _safe_stream_event("page_generated", {
    "slug": page_plan.page_id,
    "words": word_count,
    ...
})
```

**Add** in Phase 3 of `run()`, immediately after `generated_pages.append(GeneratedPage(...))`:
```python
await _safe_stream_event("page_generated", {
    "slug": slug,
    "words": page.word_count,  # authoritative value from GeneratedPage
    "fallback": page.used_fallback,
    "total": len(page_plans),  # total pages in this run — enables N/T display
})
```

If `page_plans` is not in scope at that point, pass `total_pages: int` as a parameter
to the inner helper, or store it as a local in `run()`.

### Step 2: Fix G4b — export `StreamEventHandler`

In `src/launcher/orchestrator/__init__.py`, add (alongside `safe_stream_event`
from LS-02):
```python
from .run_loop import StreamEventHandler  # noqa: F401
```

### Step 3: Fix G4c — N/T progress counter in `_on_custom_event`

In `run_loop.py`, in `StreamEventHandler._on_custom_event`, find the block that
handles `"page_generated"`. Update the sub-line format:

```python
if name == "page_generated":
    slug = data.get("slug", "?")
    words = data.get("words", 0)
    total = data.get("total")
    fallback = data.get("fallback", False)
    position = f"{self._page_counters.get('generate', 0) + 1}"
    if total:
        position = f"{position}/{total}"
    suffix = f" [fallback]" if fallback else ""
    print(f"  page: {slug} ({position}, {words} words){suffix}", file=sys.stderr, flush=True)
    self._page_counters["generate"] = self._page_counters.get("generate", 0) + 1
```

Add `self._page_counters: dict[str, int] = {}` to `StreamEventHandler.__init__`.

### Step 4: Update tests

In `test_stream_progress.py`, find `test_custom_events_displayed_as_sub_lines`.
Update the expected output format to match `(1/1, 450 words)` when `total` is present.

Add a test for the no-total fallback:
```python
@pytest.mark.asyncio
async def test_page_generated_without_total_omits_counter() -> None:
    """When total is absent from event data, format is (N, K words) not (N/T, K words)."""
    # ...verify format string
```

### Step 5: Verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    tests/unit/workers/test_generate.py \
    -v --tb=short
```

## Failure modes

### Failure mode 1: `page.word_count` is 0 because `GeneratedPage` is constructed before markdown rendering

**Detection**: `test_custom_events_displayed_as_sub_lines` shows `0 words` in the
stream output.
**Resolution**: Verify that `GeneratedPage.word_count` is populated in the constructor
from `len(markdown.split())`. If construction happens before markdown is rendered,
move the event emission to after the markdown render step.
**Gate**: `page.word_count > 0` for any non-empty page.

### Failure mode 2: `page_plans` not accessible at Phase 3 emit point

**Detection**: `NameError: name 'page_plans'` or `len(page_plans)` is 1 (only one
page in scope at that point because we are inside a per-page helper).
**Resolution**: Pass `total_pages=len(page_plans)` as an argument to `_process_page`
(or equivalent inner function) at the call site in `run()`. This value is known
before the page loop starts.
**Gate**: Event payload `data["total"]` equals the actual number of pages in the plan.

### Failure mode 3: `_page_counters` is a class variable (shared across instances)

**Detection**: Multiple `StreamEventHandler` instances in the same test session show
accumulated counter values from previous tests.
**Resolution**: Ensure `self._page_counters: dict[str, int] = {}` is in `__init__`
not at the class level. Run tests in order and verify counters reset per instance.
**Gate**: Each test that checks the `(N/T, ...)` format starts from counter 1.

## Task-specific review checklist

1. [ ] `page_generated` event is emitted after `GeneratedPage(...)` construction, not before
2. [ ] `page.word_count` is the source of `words` in the event (not a re-computed estimate)
3. [ ] `total` key in event payload equals `len(page_plans)` (full run total, not batch size)
4. [ ] `_page_counters` is an instance variable in `__init__` (not class-level)
5. [ ] `StreamEventHandler` exported from `orchestrator/__init__.py`
6. [ ] Test `test_custom_events_displayed_as_sub_lines` updated to expect new format
7. [ ] Docstrings updated for `_on_custom_event` and `page_generated` event format
8. [ ] Spec file `specs/worker_generate.md` reviewed — word count emission is now in Phase 3
9. [ ] Schema changes: none (`total` is an optional event payload key, not a schema boundary)
10. [ ] `docs/README.md` ownership map checked — no trigger event applies
11. [ ] No early `sum(len(b.content.split()) ...)` block remains in generate worker

## Deliverables

1. `src/launcher/workers/generate/worker.py` — event emission moved to Phase 3; canonical word count used
2. `src/launcher/orchestrator/run_loop.py` — N/T counter in `_on_custom_event`; `_page_counters` in `__init__`
3. `src/launcher/orchestrator/__init__.py` — `StreamEventHandler` re-exported
4. `tests/unit/orchestrator/test_stream_progress.py` — updated format assertions + new no-total test
5. `reports/LS-04/evidence.md` — test run output

## Acceptance checks

1. [ ] No `sum(len(b.content.split())...)` pattern in `generate/worker.py`
2. [ ] `from launcher.orchestrator import StreamEventHandler` works in REPL
3. [ ] Sub-line format for `page_generated` is `page: slug (N/T, K words)` when `total` present
4. [ ] Sub-line format is `page: slug (N, K words)` when `total` absent
5. [ ] All generate + orchestrator tests pass with `PYTHONHASHSEED=0`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: generate + orchestrator suite PASS
- [ ] Evidence captured: `reports/LS-04/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean

## E2E verification

```bash
# Verify no early estimate remains
grep -n "sum(len(b.content.split" src/launcher/workers/generate/worker.py

# Verify export
python -c "from launcher.orchestrator import StreamEventHandler; print('ok')"

# Run targeted suites
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    tests/unit/workers/test_generate.py \
    -v --tb=short
```

**Expected results**:
- `grep` returns zero matches
- Import check prints `ok`
- All tests pass

## Integration boundary proven

**Upstream**: `generate/worker.py` Phase 3 — `GeneratedPage` construction and word count
**Downstream**: `StreamEventHandler._on_custom_event` — formats and prints sub-line
**Contract**: `page_generated` event payload is `{"slug": str, "words": int,
"fallback": bool, "total": int | None}` where `words` equals `GeneratedPage.word_count`.

## Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All three sub-issues fixed; tests updated; no pre-render estimate remains |
| Consistency | Word count in stream output matches final summary report (GeneratedPage.word_count) |
| Production grading | Operators see accurate word count + position counter; no divergence between stream and report |
| Systematic approach | Read worker Phase 3 → move emit point → update formatter → update tests → verify |
| Correctness | `page.word_count` is computed from the final rendered markdown (authoritative) |
| Scope adherence | Only 4 files; evaluate worker untouched |
| Maintainability | `_page_counters` dict allows extending to other event types without new fields |
| Testability | Format assertions are substring-based; fragility noted and acceptable for display output |
| Robustness | `total` is optional in the formatter — gracefully handles events that omit it |
| Performance | No additional computation; `page.word_count` was already computed |
| Integration fit | Export follows existing pattern (`StreamEventHandler` alongside other orchestrator symbols) |
| Observability | `(N/T, K words)` gives operators full positional context during long runs |
| Minimality | ~15 lines changed across 3 files; no new abstractions |

## Now (runbook)

```bash
# 1. Find current page_generated emit in generate/worker.py
grep -n "page_generated\|word_count\|_process_page" \
    src/launcher/workers/generate/worker.py

# 2. Find Phase 3 (GeneratedPage construction) in run()
grep -n "GeneratedPage\|generated_pages.append" \
    src/launcher/workers/generate/worker.py

# 3. Remove early word-count block; add emit after GeneratedPage (Edit tool)

# 4. Find _on_custom_event in run_loop.py
grep -n "_on_custom_event\|page_generated\|_page_counters" \
    src/launcher/orchestrator/run_loop.py

# 5. Update formatter + add _page_counters to __init__ (Edit tool)

# 6. Add StreamEventHandler export to orchestrator/__init__.py (Edit tool)

# 7. Update test assertions (Edit tool on test_stream_progress.py)

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/orchestrator/test_stream_progress.py \
    tests/unit/workers/test_generate.py \
    -v --tb=short

# 9. Capture evidence
mkdir -p reports/LS-04
```
