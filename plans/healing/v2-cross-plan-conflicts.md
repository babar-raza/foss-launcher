# v2 Self-Review Healing — Cross-Plan Conflicts

> Source: Self-review of quirky-mapping-mccarthy (Heal), twinkly-beaming-wren (Golden),
>          sparkling-discovering-walrus (SEO-Phase-2)
> Severity: Critical / High
> Filed: 2026-03-08

Structural conflicts *between* the three v2 plans that would cause one plan's implementation
to silently overwrite or break another's. All fixes are production-grade code implementations,
not patches.

---

## Gap Table

| Gap ID | Description | Taskcard | Status |
|--------|-------------|----------|--------|
| GAP-01 | `golden_loader.py` has two incompatible APIs across heal plan H2.4 and golden plan G001 | V2CP-01 | Done |
| GAP-02 | `GoldenIndex` runtime instantiation point never specified — every implementer will choose differently | V2CP-02 | Done |
| GAP-04 | `GoldenBlockSpec.max_retries` defined in G001 but never read in G003 enforcement cascade | V2CP-04 | Done |
| GAP-16 | G003 OPT-5 parallelises section generation but cross-section deduplication requires a complete list — conflict unresolved in plan | V2CP-03 | Done |

---

## V2CP-01 — Reconcile `golden_loader.py` API: Remove H2.4 Duplicate Creator

**Status:** Done
**Gap linkage:** GAP-01

### Role
Senior engineer. Drop-in, production-ready. No stubs, no TODOs.

### Context
`quirky-mapping-mccarthy.md` H2.4 creates `src/launcher/shared/golden_loader.py` as a simple
function returning a plain string excerpt. `twinkly-beaming-wren.md` G001 creates the same
file as a full `GoldenIndex` class with `GoldenSection`, `GoldenBlockSpec`, section parsing,
Jaccard matching, and tier selection. Whichever agent runs second silently overwrites the
first. The heal code that calls the simple loader will break when G001's `GoldenIndex` lands.

### Scope
**Fix:**
- Delete the H2.4 "NEW file" instruction from the heal plan.
- Implement H2.4's functional intent as a thin adapter inside `cli/heal.py` or `shared/golden_loader.py` that calls `GoldenIndex.get_section()` and returns `.excerpt[:500]`.
- Add `Depends on: G001` to H2.4 in the plan.
- In `golden_loader.py` (G001's file), add a module-level helper `get_heal_excerpt(golden_index, page_role, variant, section_heading) -> str | None` so the heal loop has a stable, tested call surface.

**Allowed paths:**
```
src/launcher/shared/golden_loader.py    (add get_heal_excerpt helper)
src/launcher/cli/heal.py                (consume get_heal_excerpt)
tests/unit/shared/test_golden_loader.py (add tests for get_heal_excerpt)
C:\Users\prora\.claude\plans\quirky-mapping-mccarthy.md  (amend H2.4 row)
```

**Forbidden:** Any other file. Do not create a second `golden_loader` anywhere.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "from launcher.shared.golden_loader import GoldenIndex, get_heal_excerpt; print('ok')"
  grep -n "golden_loader" src/launcher/cli/heal.py | head -5   # must show single import
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_golden_loader.py -v -k heal_excerpt
  ```
  Must pass: `test_heal_excerpt_found`, `test_heal_excerpt_missing_returns_none`, `test_heal_excerpt_truncated_at_500`.
- **Config respected end-to-end:** `golden_index=None` → `get_heal_excerpt` returns `None` without loading any file.
- **No mock data in production paths:** `get_heal_excerpt` reads only from the `GoldenIndex` already loaded; no hardcoded strings.

### Deliverables
- **`src/launcher/shared/golden_loader.py`** — full file with `GoldenIndex` class (G001 spec) PLUS new `get_heal_excerpt(golden_index: GoldenIndex | None, page_role: str, variant: str, section_heading: str) -> str | None` helper at module level. Excerpt capped at 500 chars; returns `None` if `golden_index is None` or no match found.
- **`tests/unit/shared/test_golden_loader.py`** — tests for `get_heal_excerpt` added to existing G001 test file. Three test cases minimum (found, missing, truncation).
- **Amended `quirky-mapping-mccarthy.md`** — H2.4 row updated: removes "NEW", adds "Depends on: G001", references `get_heal_excerpt`.

### Hard Rules
- `get_heal_excerpt` must have type annotations and a one-line docstring.
- `get_heal_excerpt(None, ...)` must return `None` in O(1) — no filesystem access.
- No new dependencies.
- Keep existing `GoldenIndex` public signature intact.
- Determinism: `get_heal_excerpt` result is deterministic given same inputs (Jaccard uses sorted sets).

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | One canonical file, one canonical API; both plans reference same import |
| Consistency | `get_heal_excerpt` uses `GoldenIndex.get_section()` — no parallel implementation |
| Production grading | `golden_index=None` guard prevents crash in heal loop before G001 ships |
| Systematic approach | Helper added to G001 file (not heal file) so it's tested alongside G001 |
| Correctness | Excerpt capped at 500 chars; corrupt golden (< 20 words) returns None |
| Scope adherence | Only `golden_loader.py`, `heal.py`, one test file, one plan file |
| Maintainability | Thin helper is 10 lines; no logic duplication |
| Testability | Three distinct unit tests; no LLM calls needed |
| Robustness | None guard, missing section guard, truncation — all explicit |
| Performance | Reads from in-memory GoldenIndex; O(1) lookup |
| Integration fit | Extends existing G001 file; heal code has a clean, typed call surface |
| Observability | Caller (heal CLI) logs when `golden_excerpt is None` at DEBUG level |
| Minimality | 10-line helper + 3 tests; no restructuring of GoldenIndex |

### Now (Runbook)
```
1. Confirm G001 golden_loader.py is complete or start there first (H2.4 depends on it).
2. Open src/launcher/shared/golden_loader.py (G001 output).
3. Append after GoldenIndex class:

def get_heal_excerpt(
    golden_index: "GoldenIndex | None",
    page_role: str,
    variant: str,
    section_heading: str,
) -> str | None:
    """Return first 500 chars of the matching golden section excerpt, or None."""
    if golden_index is None:
        return None
    section = golden_index.get_section(page_role, variant, section_heading)
    if section is None:
        return None
    return section.excerpt[:500] or None

4. In tests/unit/shared/test_golden_loader.py, add:
   - test_heal_excerpt_found: build fixture index, call get_heal_excerpt → str
   - test_heal_excerpt_missing_returns_none: missing heading → None
   - test_heal_excerpt_none_index: golden_index=None → None (no filesystem I/O)
   - test_heal_excerpt_truncated_at_500: excerpt >500 chars → len == 500
5. In src/launcher/cli/heal.py (when implementing H2.4):
   from launcher.shared.golden_loader import get_heal_excerpt
   golden_excerpt = get_heal_excerpt(golden_index, page_role, variant, section_heading)
6. Amend quirky-mapping-mccarthy.md H2.4 row to reference get_heal_excerpt and add Depends on: G001.
7. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_golden_loader.py -v
8. Confirm no "golden_loader.py" "NEW" reference remains in heal plan.
```

---

## V2CP-02 — Implement `GoldenIndex` Runtime Instantiation in Worker `__init__`

**Status:** Done
**Gap linkage:** GAP-02

### Role
Senior engineer. Drop-in, production-ready.

### Context
G002 and G003 both use `golden_index` but neither plan specifies WHERE it is created. Options
considered: module singleton (breaks test isolation), WorkerContext field (couples context
to a subsystem), re-instantiated per page (parses 22 files per page — wasteful). The correct
pattern is worker `__init__`: stateful worker, stateful shared read-only index, loaded once.

### Scope
**Fix:**
- Add `self._golden_index: GoldenIndex | None` to `GenerateWorker.__init__` and `EvaluateWorker.__init__`.
- Load from `pipeline_config.golden.dir` when `pipeline_config.golden.enabled is True`.
- Pass as explicit parameter to all functions that need it.
- Add `golden: {dir: "golden/", enabled: true}` to `configs/pipeline.yaml`.

**Allowed paths:**
```
src/launcher/workers/generate/worker.py
src/launcher/workers/evaluate/worker.py
configs/pipeline.yaml
tests/workers/generate/test_generate_worker.py
tests/workers/evaluate/test_evaluate_worker.py
```

**Forbidden:** `src/launcher/orchestrator/worker_contract.py` (do not add GoldenIndex to WorkerContext).

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.workers.generate.worker import GenerateWorker
  import inspect
  sig = inspect.signature(GenerateWorker.__init__)
  print('config param:', 'config' in sig.parameters)
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_generate_worker.py tests/workers/evaluate/test_evaluate_worker.py -v -k golden
  ```
  Must pass: `test_golden_index_loaded_when_enabled`, `test_golden_index_none_when_disabled`, `test_golden_index_not_on_worker_context`.
- **Config respected end-to-end:** `golden.enabled: false` in pipeline.yaml → `self._golden_index` is `None`; all callers degrade gracefully.
- **No mock data in production paths:** `GoldenIndex.load()` reads real `.md` files from `golden/`; tests use `tmp_path` fixture.

### Deliverables
- **`src/launcher/workers/generate/worker.py`** — full file with `self._golden_index` in `__init__`, passed to `build_section_prompt()` and `enforce_block_spec()`.
- **`src/launcher/workers/evaluate/worker.py`** — full file with `self._golden_index` in `__init__`, passed to `check_block_spec_compliance()`.
- **`configs/pipeline.yaml`** — full file with `golden: {dir: "golden/", enabled: true}` section added.
- **Tests** — `test_golden_index_loaded_when_enabled`, `test_golden_index_none_when_disabled`, `test_golden_index_not_on_worker_context` added to respective test files.

### Hard Rules
- `WorkerContext` must NOT gain a `golden_index` field — keep it as a plain data carrier.
- `GoldenIndex` is read-only after `__init__`; safe for `asyncio.gather` parallelism.
- `golden.enabled: false` must short-circuit before any `Path.glob()` or file I/O.
- Tests use `tmp_path` fixture for `golden_dir` — never the real `golden/` directory.
- No new Python dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Both workers updated; config toggle fully wired; test isolation guaranteed |
| Consistency | Same `__init__` pattern in both GenerateWorker and EvaluateWorker |
| Production grading | No global state; `tmp_path` fixture prevents test coupling to real data |
| Systematic approach | Config → `__init__` → explicit param passing — all three steps implemented |
| Correctness | `enabled: false` → `None`; all callers already guard on `if golden_index is not None` |
| Scope adherence | WorkerContext not touched; only worker files and config |
| Maintainability | Pattern is simple and repeatable for future workers |
| Testability | Three named unit tests; fixture-based; no LLM calls |
| Robustness | `golden/` dir missing → `GoldenIndex.load()` raises `FileNotFoundError` caught in `__init__`, logged as warning, self._golden_index = None |
| Performance | Parse 22 files once per run; read-only access is safe for async |
| Integration fit | Explicit parameter passing (not service locator) keeps function signatures honest |
| Observability | `__init__` logs `INFO: GoldenIndex loaded (22 files)` or `INFO: GoldenIndex disabled` |
| Minimality | Two `__init__` methods + one config block + three tests |

### Now (Runbook)
```
1. Add to configs/pipeline.yaml (after existing sections):
   golden:
     dir: "golden/"
     enabled: true

2. In src/launcher/workers/generate/worker.py __init__:
   from launcher.shared.golden_loader import GoldenIndex
   golden_cfg = getattr(pipeline_config, "golden", None)
   if golden_cfg and getattr(golden_cfg, "enabled", False):
       try:
           self._golden_index = GoldenIndex.load(Path(golden_cfg.dir))
           log.info("GoldenIndex loaded (%d files)", len(self._golden_index._pages))
       except Exception as exc:
           log.warning("GoldenIndex load failed: %s — degrading gracefully", exc)
           self._golden_index = None
   else:
       log.info("GoldenIndex disabled")
       self._golden_index = None

3. Pass self._golden_index to build_section_prompt() and enforce_block_spec() calls.
4. Repeat step 2-3 for EvaluateWorker.
5. Add tests:
   - test_golden_index_loaded_when_enabled: tmp_path golden dir with one .md file → self._golden_index is not None
   - test_golden_index_none_when_disabled: golden.enabled=false → self._golden_index is None
   - test_golden_index_none_on_missing_dir: nonexistent dir → warning logged, self._golden_index is None
   - test_golden_index_not_on_worker_context: WorkerContext instance has no golden_index attr
6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/ -v -k golden
```

---

## V2CP-03 — Fix Section Parallelism vs Cross-Section Deduplication Execution Order

**Status:** Done
**Gap linkage:** GAP-16

### Role
Senior engineer. Drop-in, production-ready.

### Context
G003 OPT-5 adds `asyncio.gather()` for per-section LLM calls within a page. The plan
simultaneously requires that cross-section deduplication in `section_validator.py` runs
"post-collect". However, the plan also states "Enforcement cascade runs per-section after
each LLM call (not batched)" — which implies deduplication runs *during* gather. These two
statements contradict. Deduplication is a cross-section operation requiring the full list;
it cannot run inside individual gather coroutines.

### Scope
**Fix:**
Implement OPT-5 in `generate/worker.py` with an explicit 4-phase execution model:
1. **Parallel generate**: `asyncio.gather(*[_generate_section(s) for s in sections], return_exceptions=True)`
2. **Error isolation**: replace any `BaseException` result with `render_section_deterministic(s)`
3. **Per-section enforcement**: enforce_block_spec on each (can be parallel — no cross-section state)
4. **Sequential dedup**: `section_validator.deduplicate(results)` on complete ordered list

**Allowed paths:**
```
src/launcher/workers/generate/worker.py
src/launcher/workers/generate/section_validator.py
tests/workers/generate/test_enforcement.py
```

**Forbidden:** Any other file.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  import asyncio, inspect
  from launcher.workers.generate.worker import _generate_sections_parallel
  src = inspect.getsource(_generate_sections_parallel)
  assert 'return_exceptions=True' in src, 'Missing return_exceptions'
  assert 'deduplicate' in src, 'Dedup must run post-gather'
  print('ok')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v -k dedup
  ```
  Must pass: `test_cross_section_dedup_runs_on_complete_list`, `test_section_order_preserved_after_parallel_gather`, `test_exception_in_one_section_does_not_cancel_others`.
- **Config respected end-to-end:** Parallelism is bounded by `LLMProvider` semaphore (existing config).
- **No mock data in production paths:** LLM calls use real provider in integration tests; unit tests use mock via `LLMMockProvider`.

### Deliverables
- **`src/launcher/workers/generate/worker.py`** — full file. New `_generate_sections_parallel(sections, ...) -> list[list[BlockIR]]` function implementing the 4-phase model. Called from the main per-page generation loop.
- **`src/launcher/workers/generate/section_validator.py`** — full file. Existing `deduplicate()` function confirmed to accept a complete list and return an ordered list. Add type annotation if missing.
- **`tests/workers/generate/test_enforcement.py`** — full file. Three new test cases for: cross-section dedup on complete list, section order preservation, single section exception isolation.

### Hard Rules
- `asyncio.gather(..., return_exceptions=True)` — mandatory, no exceptions.
- Output list order MUST match input skeleton order regardless of asyncio completion order.
- A `BaseException` in one section coroutine MUST NOT cancel other sections.
- Deduplication MUST run after ALL sections are collected, never inside a coroutine.
- No new dependencies (`asyncio` is stdlib).
- Determinism: sections sorted by stable key before gather; output list reconstructed by index.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All 4 phases implemented, named, and individually testable |
| Consistency | Aligns with existing section_validator.deduplicate() contract |
| Production grading | Exception isolation prevents one flaky LLM call from losing a whole page |
| Systematic approach | 4-phase model is a named function, not inline logic |
| Correctness | Dedup sees complete list; order matches skeleton |
| Scope adherence | Only worker.py, section_validator.py, test file |
| Maintainability | `_generate_sections_parallel` is independently understandable |
| Testability | Three targeted test cases; mock provider avoids network |
| Robustness | `return_exceptions=True` + BaseException fallback covers all failure modes |
| Performance | Parallel generate is the entire point of OPT-5; dedup is O(n²) but n is small (sections per page) |
| Integration fit | 4-phase function slots into existing per-page loop |
| Observability | Log when BaseException triggers fallback: `WARNING: section %s generation failed, using deterministic fallback` |
| Minimality | One new function + one test class; no restructuring of worker |

### Now (Runbook)
```
1. In src/launcher/workers/generate/worker.py, add:

async def _generate_sections_parallel(
    sections: list[SectionSpec],
    ...,  # same params as current per-section loop
) -> list[list[BlockIR]]:
    # Phase 1: parallel generate
    coros = [_generate_section(s, ...) for s in sections]
    raw = await asyncio.gather(*coros, return_exceptions=True)

    # Phase 2: error isolation (preserve index position)
    results: list[list[BlockIR]] = []
    for i, r in enumerate(raw):
        if isinstance(r, BaseException):
            log.warning("Section %s failed (%s), using deterministic fallback", sections[i].heading, r)
            results.append(render_section_deterministic(sections[i], ...))
        else:
            results.append(r)

    # Phase 3: per-section enforcement (can also be gathered)
    enforced = []
    for i, (section, blocks) in enumerate(zip(sections, results)):
        spec = golden_index.get_spec(...) if golden_index else None
        enforced_blocks, _ = enforce_block_spec(blocks, spec, ...)
        enforced.append(enforced_blocks)

    # Phase 4: cross-section dedup on COMPLETE list
    return section_validator.deduplicate(enforced, sections)

2. Replace the existing sequential section loop with a call to this function.
3. Add tests:
   - test_cross_section_dedup_runs_on_complete_list: inject duplicate phrase in S1 and S3; verify S3 deduped
   - test_section_order_preserved_after_parallel_gather: use asyncio.sleep stagger, verify output order == input order
   - test_exception_in_one_section_does_not_cancel_others: mock S2 to raise; verify S1 and S3 are present
4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v
```

---

## V2CP-04 — Wire `GoldenBlockSpec.max_retries` Into Enforcement Cascade Pass 2

**Status:** Done
**Gap linkage:** GAP-04

### Role
Senior engineer. Drop-in, production-ready.

### Context
`GoldenBlockSpec.max_retries: int = 1` is defined in G001 but the G003 enforcement cascade
hardcodes "call LLM once" in Pass 2. The field is never read. This is a dead field from
day one. Wiring it to Pass 2 provides meaningful tunability: `max_retries=0` for Tier C
(skip LLM entirely), `max_retries=1` default, `max_retries=2` for high-priority roles.

### Scope
**Fix:**
- In `enforce_block_spec()` Pass 2: replace single LLM call with a loop `for attempt in range(spec.max_retries)`.
- `max_retries=0` short-circuits Pass 2 entirely (go directly to Pass 3).
- Add `validate` parameter to avoid duplicate spec check: `check_against_spec(retry_blocks, spec)`.

**Allowed paths:**
```
src/launcher/workers/generate/section_validator.py
tests/workers/generate/test_enforcement.py
```

**Forbidden:** Any other file. Do not change `GoldenBlockSpec` definition.

### Acceptance Checks
- **CLI:**
  ```bash
  python -c "
  from launcher.workers.generate.section_validator import enforce_block_spec
  from launcher.shared.golden_loader import GoldenBlockSpec
  spec0 = GoldenBlockSpec(required_block_types=['code'], min_words=50, max_retries=0)
  # Pass max_retries=0 spec; verify LLM not called (use mock that raises if called)
  print('max_retries=0 path exists')
  "
  ```
- **UI/Web/API:** N/A
- **Tests:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v -k retries
  ```
  Must pass: `test_max_retries_zero_skips_pass2`, `test_max_retries_two_calls_llm_twice_on_failure`, `test_max_retries_one_default_behavior_unchanged`.
- **Config respected end-to-end:** Default `max_retries=1` is backward-compatible; no existing behavior changes.
- **No mock data in production paths:** Tests mock LLM calls via `LLMMockProvider`; production uses real provider.

### Deliverables
- **`src/launcher/workers/generate/section_validator.py`** — full file. `enforce_block_spec` Pass 2 uses `for attempt in range(spec.max_retries if spec else 1)`. `spec is None` or `spec.max_retries == 0` skips Pass 2 entirely.
- **`tests/workers/generate/test_enforcement.py`** — full file. Three new test cases for max_retries behavior.

### Hard Rules
- Default `max_retries=1` must not change existing behavior (backward compatible).
- Tier C (richness_tier == "C") still skips Pass 2 regardless of `max_retries` value.
- `max_retries=0` never calls LLM — `range(0)` is empty loop.
- No new dependencies.

### Review Dimensions (what 5/5 means here)
| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All three values (0, 1, 2) tested; Tier C override still works |
| Consistency | G001 definition now has a live consumer in G003 |
| Production grading | Default unchanged; `max_retries=0` is a free performance win for Tier C |
| Systematic approach | One loop replacing one call — minimal structural change |
| Correctness | `range(0)` is the correct guard for zero retries |
| Scope adherence | Only section_validator.py and its test file |
| Maintainability | Loop is self-documenting; `max_retries` field intent is now clear |
| Testability | Three targeted test cases; mocked LLM verifies call count |
| Robustness | Tier C override preserved; spec=None short-circuits |
| Performance | `max_retries=0` eliminates LLM call for Tier C |
| Integration fit | No change to call site signatures |
| Observability | Log: `DEBUG: enforce Pass 2 attempt %d/%d` |
| Minimality | 3-line change (single call → loop) + 3 tests |

### Now (Runbook)
```
1. Open src/launcher/workers/generate/section_validator.py
2. Find Pass 2 block in enforce_block_spec().
3. Replace:
   # OLD: single call
   retry_resp = llm_client.complete(retry_prompt)
   retry_blocks = parse_blocks(retry_resp)
   if check_against_spec(retry_blocks, spec) == []:
       return (retry_blocks, "llm_retry")

   WITH:
   # NEW: respect max_retries
   max_attempts = spec.max_retries if spec is not None else 1
   if richness_tier == "C":
       max_attempts = 0  # Tier C always skips Pass 2
   for attempt in range(max_attempts):
       log.debug("enforce Pass 2 attempt %d/%d", attempt + 1, max_attempts)
       retry_resp = llm_client.complete(retry_prompt)
       retry_blocks = parse_blocks(retry_resp)
       if check_against_spec(retry_blocks, spec) == []:
           return (retry_blocks, "llm_retry")
   # fall through to Pass 3

4. Add tests:
   - test_max_retries_zero_skips_pass2: spec.max_retries=0 → mock LLM raises if called; no exception
   - test_max_retries_two_calls_llm_twice_on_failure: spec.max_retries=2, LLM always returns non-compliant → called exactly 2 times
   - test_max_retries_one_default_behavior_unchanged: spec.max_retries=1 → behavior same as before this change
5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_enforcement.py -v -k retries
```
