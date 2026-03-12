# HO — H5 Optimization Completion

**Source**: Self-review of TC-3853/3854/3855 (H5.1–H5.8). Six of eight H5 tasks are
unimplemented or partially implemented:
- H5.1: `heal_target_pages` skips pages but does NOT reuse cached PageIR (empty ContentManifest risk)
- H5.2: `graph_builder.py` worker-skip routing (past Understand+Planner) not implemented
- H5.4: `FOSS_LAUNCHER_LLM_CACHE=1` not set in heal session setup
- H5.5: `remaining_for_step()` done, but adaptive F→D→C page prioritization absent
- H5.6: `asyncio.gather()` page/section parallelism not implemented
- H5.8: Section-level granularity (findings → section_id, regenerate failing sections only) not implemented

**Plan target**: 81% LLM call reduction, 93% wall-clock reduction.
**Estimated current**: ~50% without HO-02, HO-03, HO-05, HO-06.

**Codebase**: `v2` branch
**Sequencing constraint**: HO-01 before HO-05; HO-05 before HO-06; HO-02 independent.

---

## Gap → Taskcard Map

| Gap ID  | Description                                                  | Taskcard |
|---------|--------------------------------------------------------------|----------|
| G-HO-01 | H5.1: Skipped pages dropped from page_results (empty manifest risk) | HO-01 |
| G-HO-02 | H5.2: Worker skip (graph_builder route past Understand+Planner) absent | HO-02 |
| G-HO-03 | H5.4: FOSS_LAUNCHER_LLM_CACHE=1 not set in heal.py session  | HO-03 |
| G-HO-04 | H5.5: Adaptive F→D→C page prioritization absent in heal.py  | HO-04 |
| G-HO-05 | H5.6: asyncio.gather page/evaluate parallelism not implemented | HO-05 |
| G-HO-06 | H5.8: Section-level finding→section_id mapping absent        | HO-06 |

---

## HO-01 — H5.1: Heal Target Pages — Safe Skip with Cached PageIR

**Status**: Done
**Evidence**: 9 tests pass (`test_selective_regen.py` TestLoadCachedPageIR class); 2603 total suite green.
**Files changed**: `src/launcher/workers/generate/worker.py` (`_load_cached_page_ir` helper added; skip block reuses cache; empty-results guard added; `getattr` → `context.heal_target_pages` direct property), `tests/unit/workers/test_selective_regen.py` (+4 TestLoadCachedPageIR tests)
**Gap linkage**: G-HO-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: When `heal_target_pages` is set and a page is not targeted, instead of dropping
it from `page_results`, load its cached PageIR from the artifact store and re-use it.
This prevents empty ContentManifest when all pages are skipped or when page_id ≠ slug.

In `generate/worker.py` per-page loop: if `heal_target_pages is not None and page_plan.page_id not in heal_target_pages`:
1. Attempt to load cached `PageIR` from the run_dir artifact (e.g., `artifacts/{page_id}.page_ir.json`)
2. If found: append `(cached_ir, page_plan, "", "")` to `page_results` with a `generate_page_skipped` event
3. If not found: log a warning and continue (current behavior) — do NOT raise

Also add a guard in the post-loop section: if `page_results` is empty after filtering, emit
a `generate_no_pages_produced` WARNING event and return an empty-manifest result rather than
crashing downstream.

**Allowed paths**:
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/test_selective_regen.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_selective_regen.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_skipped_page_reuses_cached_page_ir` — when cache exists, skipped page appears in output
  - `test_skipped_page_cache_miss_emits_warning` — when cache missing, warning logged, page absent from output
  - `test_all_pages_skipped_no_crash` — all pages filtered, returns empty-manifest without exception
  - `test_generate_page_skipped_event_emitted` — event emitted for each reused page
- **Config respected end-to-end**: `heal_target_pages=None` → all pages processed (existing test preserved)
- **No mock data in production paths**: Cache loaded from real artifact path via `io.artifact_store` or equivalent — no hardcoded test data in production path

### Deliverables

- `src/launcher/workers/generate/worker.py` — full targeted section replacement (page loop only); no other sections changed
- `tests/unit/workers/test_selective_regen.py` — full replacement with 4 new test functions added
- No stubs, no TODOs; cached-IR load uses the same store path as the write path

### Hard rules

- Keep public signature of `run()` unchanged
- `getattr(context, "heal_target_pages", None)` → change to `context.heal_target_pages` now that it is a proper property
- No network; cache load is local disk read
- Deterministic: sorted page_results order preserved (same as plan.pages order)
- Guard against empty `page_results` must not suppress genuine zero-page plans (only triggers when `heal_target_pages` is active)

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D6 Production Robustness | Empty results guarded; cache-miss logged not raised; property access not getattr |
| D5 Error Isolation | cache load failure is WARNING not ERROR; does not abort worker |
| D7 Test Coverage | 4 functions: cache hit + cache miss + all-skipped + event emitted |
| D10 Performance | Cache load is single disk read per skipped page; no O(N²) |
| D13 Integration | Cached PageIR written by same artifact_store as read here |

### Now (runbook)

```bash
# 1. Find current page-skip implementation
grep -n "heal_target_pages\|generate_page_skipped\|page_results" src/launcher/workers/generate/worker.py | head -30

# 2. Find artifact store write path to know the cache key/filename
grep -n "artifact_store\|page_ir\|\.write\|save_artifact" src/launcher/workers/generate/worker.py | head -20

# 3. Read current test file
# Read tests/unit/workers/test_selective_regen.py

# 4. Implement cache-reuse in worker.py, add empty-results guard

# 5. Run focused test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_selective_regen.py -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## HO-02 — H5.2: Graph Builder Worker Skip (Route Past Understand+Planner)

**Status**: Done
**Evidence**: 4/4 bypass tests pass; 2653 total suite green.
**Files changed**: `src/launcher/orchestrator/graph_builder.py` (`__heal_router__` node + `_heal_route` conditional edge added; bypasses understand+planner when `heal_metadata.responsible_worker == "generate"` and checkpoints exist; emits `worker_skipped` events; falls back to full pipeline on missing/corrupt checkpoints), `tests/unit/orchestrator/test_graph_builder.py` (added `TestHealBypassRouting` class with 4 tests)
**Gap linkage**: G-HO-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `graph_builder.py`, when `heal_metadata.responsible_worker == "generate"` is
present in graph state, route the pipeline to skip Understand and Planner workers and
re-enter directly at Generate. Use `earliest_responsible_worker()` (from `diagnosis.py`,
already implemented) to determine the re-entry point.

Implementation:
1. In `_make_worker_node()` post-success block, read `heal_metadata` from graph state
2. Add conditional edge in `_build_graph()`: after a heal-triggered run detects `responsible_worker`, use `add_conditional_edges()` to route START → Generate (bypassing Understand → Planner)
3. When bypassing, load Understand and Planner outputs from their existing worker checkpoints (via `load_worker_checkpoint()`)
4. Emit a `worker_skipped` event for each bypassed worker

**Allowed paths**:
- `src/launcher/orchestrator/graph_builder.py`
- `tests/unit/orchestrator/test_graph_builder.py` (or nearest existing graph_builder test file)

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_heal_routes_past_understand_when_responsible_generate` — Understand node never called when `responsible_worker == "generate"` and checkpoints exist
  - `test_heal_routes_past_planner_when_responsible_generate` — Planner node never called
  - `test_worker_skipped_event_emitted_for_each_bypassed_worker` — 2 `worker_skipped` events emitted
  - `test_normal_run_unaffected` — `heal_metadata` absent → full pipeline runs normally
- **Config respected end-to-end**: only activates when `heal_metadata` is set in graph state
- **No mock data in production paths**: checkpoint loading uses real `load_worker_checkpoint()`; mock only at node execution level

### Deliverables

- `src/launcher/orchestrator/graph_builder.py` — targeted additions only (conditional edge + checkpoint load in bypass path); no other graph logic changed
- Tests for both routing paths and normal-run non-regression
- No stubs, no TODOs

### Hard rules

- Do not remove or alter existing `_make_worker_node()` behavior; add bypass as an additive conditional edge
- Checkpoint load failure (no checkpoint file) must fall back to full pipeline (not crash)
- `worker_skipped` event must include `worker` name in payload
- Deterministic: conditional edge routing must be deterministic (no random branching)
- No new dependencies (LangGraph conditional edges already used in codebase)

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D2 Contract Compliance | Bypass reads from checkpoint; checkpoint is real WorkerCheckpoint with SHA-256 verified |
| D5 Error Isolation | Missing checkpoint → graceful fallback to full pipeline; logged at WARNING |
| D7 Test Coverage | 4 functions: bypass-understand + bypass-planner + event + normal-unaffected |
| D10 Performance | Delivers 100% upstream call savings per heal step when `responsible_worker == "generate"` |
| D13 Integration | Checkpoint written by H2.1 (graph_builder post-success) is what H5.2 reads |

### Now (runbook)

```bash
# 1. Read graph_builder.py to understand existing conditional edge pattern
grep -n "add_conditional_edges\|heal_metadata\|responsible_worker\|_build_graph" src/launcher/orchestrator/graph_builder.py | head -40

# 2. Read earliest_responsible_worker signature
grep -n "def earliest_responsible_worker" src/launcher/workers/evaluate/diagnosis.py

# 3. Find existing graph_builder test file
# Glob tests/**/*graph_builder*

# 4. Implement bypass conditional edge and checkpoint-load path

# 5. Run orchestrator tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## HO-03 — H5.4: LLM Cache Enablement in Heal Session

**Status**: Done
**Evidence**: 3/3 tests pass (test_heal_sets_llm_cache_env_var, test_heal_restores_cache_env_on_exit, test_cache_env_not_set_when_heal_not_active); 2618 total suite green. Files changed: src/launcher/cli/heal.py (added `import os`, set/restore FOSS_LAUNCHER_LLM_CACHE around heal loop in run_heal()), tests/unit/cli/test_heal_cli.py (+3 tests). FOSS_LAUNCHER_LLM_CACHE already wired in llm_cache.py — no change needed there.
**Gap linkage**: G-HO-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `heal.py` `run_heal()` session setup, set `os.environ["FOSS_LAUNCHER_LLM_CACHE"] = "1"`
before the heal loop. Restore the prior value in `finally`. Add a `cache_enabled: bool`
field to the `HealResult` or emit a `heal_cache_enabled` event so callers can observe it.

Also: verify `llm_provider.py` or `llm_cache.py` reads `FOSS_LAUNCHER_LLM_CACHE` and
activates caching when `"1"`. If the env var is not wired, wire it in those files too
(they are in the allowed paths for this taskcard since the env var must actually work).

**Allowed paths**:
- `src/launcher/cli/heal.py`
- `src/launcher/clients/llm_cache.py` (only if env var wiring is absent)
- `src/launcher/clients/llm_provider.py` (only if env var wiring is absent)
- `tests/unit/cli/test_heal_cli.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_heal_sets_llm_cache_env_var` — after `run_heal()` setup, `os.environ["FOSS_LAUNCHER_LLM_CACHE"] == "1"`
  - `test_heal_restores_cache_env_on_exit` — env var restored to prior value in finally (even on exception)
  - `test_cache_env_not_set_when_heal_not_active` — normal (non-heal) pipeline does not set this env var
- **Config respected end-to-end**: cache activated only during heal session; restored after
- **No mock data in production paths**: `os.environ` set/restore is real; no hardcoded env in production

### Deliverables

- `src/launcher/cli/heal.py` — set + restore env var in `run_heal()` setup/finally
- `tests/unit/cli/test_heal_cli.py` — full replacement adding 3 cache-related tests
- If `llm_cache.py` or `llm_provider.py` do not read `FOSS_LAUNCHER_LLM_CACHE`, add the read there too (minimal change: one `os.getenv` check)

### Hard rules

- Restore prior env value in `finally` — use `os.environ.pop("FOSS_LAUNCHER_LLM_CACHE", prior)` pattern
- If `FOSS_LAUNCHER_LLM_CACHE` was already set before heal, preserve that value on exit
- No new dependencies
- Emit a `heal_cache_enabled` event with `{"enabled": True}` for observability

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D6 Production Robustness | env var restored in finally even on exception; prior value preserved |
| D11 Security | No credentials or API keys — env var is a feature flag only |
| D7 Test Coverage | 3 functions: set during session + restored after + not set outside heal |
| D13 Integration | `llm_cache.py` actually reads the var and caches; verified by tracing the read path |

### Now (runbook)

```bash
# 1. Check if env var is already read anywhere
grep -rn "FOSS_LAUNCHER_LLM_CACHE" src/launcher/

# 2. Read heal.py session setup block
grep -n "def run_heal\|BudgetTracker\|try:\|finally:" src/launcher/cli/heal.py | head -30

# 3. Read llm_cache.py to understand cache activation mechanism
# Read src/launcher/clients/llm_cache.py

# 4. Wire env var set/restore in run_heal() + wire read in llm_cache.py if needed

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## HO-04 — H5.5: Adaptive Page Prioritization (F→D→C) in Heal

**Status**: Done
**Evidence**: 4/4 tests pass (test_prioritization_*); 2649 total suite green. Files: heal.py (_GRADE_SEVERITY constant, _prioritize_target_pages() helper), tests/unit/cli/test_heal_cli.py (+4 prioritization tests).
**Gap linkage**: G-HO-04
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `heal.py`, when building the list of `target_pages` for a heal step, sort
failing pages by grade severity: F-grade first, then D, then C, then B. Use
`remaining_for_step()` from `BudgetTracker` to compute `max_pages_this_step` and slice
the sorted list to that count.

This adaptive prioritization maximizes improvement per LLM token by attacking the worst
content first. Implementation is in the heal loop where `HealDecision.action.target_pages`
is constructed or where pages are filtered before being passed to `heal_target_pages`.

**Allowed paths**:
- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_cli.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_prioritization_orders_f_before_d_before_c` — given a mix of F/D/C pages, F-pages appear first in `target_pages`
  - `test_prioritization_respects_budget_cap` — if `calls_per_step == 5`, at most 5 pages targeted
  - `test_prioritization_empty_fails_no_crash` — no failing pages → empty target_pages, session stops gracefully
  - `test_prioritization_deterministic` — same input → same output with PYTHONHASHSEED=0 (sort is stable)
- **Config respected end-to-end**: page count adapts to `remaining_for_step()` output
- **No mock data in production paths**: `remaining_for_step()` uses real `BudgetTracker` state

### Deliverables

- `src/launcher/cli/heal.py` — targeted addition of sort+slice logic in target_pages construction
- `tests/unit/cli/test_heal_cli.py` — full replacement with 4 new prioritization test functions
- No stubs, no TODOs

### Hard rules

- Sort key: `grade_severity = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}`
- Within same grade, sort by page_id ascending for determinism
- `sorted()` not `sort()` to preserve immutability of original list
- `calls_per_step` from `remaining_for_step()` is the cap; minimum cap is 1 (never 0)
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D4 Determinism | Stable sort with secondary key (page_id); PYTHONHASHSEED=0 verified |
| D6 Production Robustness | Empty failing pages handled; cap enforced (min 1) |
| D7 Test Coverage | 4 functions: ordering + cap + empty + determinism |
| D10 Performance | O(N log N) sort on page list; build grade_severity dict once not per page |

### Now (runbook)

```bash
# 1. Find where target_pages is constructed in heal.py
grep -n "target_pages\|heal_target\|failing\|grade" src/launcher/cli/heal.py | head -30

# 2. Find remaining_for_step usage
grep -n "remaining_for_step\|calls_per_step" src/launcher/cli/heal.py

# 3. Find where page grades are available (evaluation report structure)
grep -n "grades\|grade\|PageEvaluation" src/launcher/cli/heal.py | head -20

# 4. Implement sort+slice; add 4 test functions

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## HO-05 — H5.6: asyncio.gather Page-Level Parallelism

**Status**: Done
**Evidence**: 4/4 gather tests pass (TestPageGatherParallelism); 2657 total suite green.
**Files changed**: `src/launcher/workers/generate/worker.py` (added `_PAGE_CONCURRENCY=4`, replaced page loop with `asyncio.gather` + `_process_page` closure with semaphore), `src/launcher/workers/evaluate/worker.py` (replaced page loop with `asyncio.gather` + `_evaluate_page_llm` closure with `_eval_sem`), `tests/unit/workers/test_selective_regen.py` (added `TestPageGatherParallelism` class with 4 tests)
**Gap linkage**: G-HO-05
**Depends on**: HO-01 complete (generate/worker.py stable); GE-02 complete (section parallelism stable)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `generate/worker.py`, wrap the per-page generation loop in `asyncio.gather()`
with a semaphore of concurrency=4. In `evaluate/worker.py`, wrap per-page LLM review
calls in `asyncio.gather()` with concurrency=4. Both use the existing `LLMProvider`
semaphore to cap concurrent LLM calls at the provider level.

Implementation:
1. `generate/worker.py`: Extract per-page body into `async def _generate_page(page_plan, ...)`. Wrap with `asyncio.Semaphore(4)`. Gather with `asyncio.gather(*[_generate_page(...) for page in plan.pages])`.
2. `evaluate/worker.py`: Extract per-page LLM review into `async def _evaluate_page_llm(page, ...)`. Gather all pages. Collect results in original page order.
3. Results must be collected in the original `plan.pages` order (sort by page_plan index after gather).

**Allowed paths**:
- `src/launcher/workers/generate/worker.py`
- `src/launcher/workers/evaluate/worker.py`
- `tests/unit/workers/test_selective_regen.py`
- `tests/unit/workers/test_evaluate_worker.py` (or nearest evaluate worker test file)

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_generate_pages_gathered_in_order` — output page order matches input plan.pages order
  - `test_generate_semaphore_limits_concurrency` — mock verifies ≤4 concurrent calls
  - `test_evaluate_llm_gathered_in_order` — evaluate output order preserved
  - `test_parallel_page_failure_isolated` — one page error does not abort other pages
- **Config respected end-to-end**: concurrency=4 default; verify LLMProvider semaphore still respected
- **No mock data in production paths**: asyncio.Semaphore is stdlib; no production path hardcoding

### Deliverables

- `src/launcher/workers/generate/worker.py` — full replacement of page loop with `asyncio.gather()` pattern
- `src/launcher/workers/evaluate/worker.py` — full replacement of LLM review loop with `asyncio.gather()` pattern
- Tests covering: order preservation + concurrency limit + per-page error isolation
- No stubs, no TODOs

### Hard rules

- Result order MUST match `plan.pages` order — gather results as list, zip with original plan
- Per-page exceptions caught inside each coroutine; `asyncio.gather(return_exceptions=True)` then filter
- No new dependencies (asyncio is stdlib)
- Semaphore size 4 as named constant `_PAGE_CONCURRENCY = 4` at module level
- PYTHONHASHSEED=0 must pass: no dict-based ordering in gather

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D4 Determinism | Output order locked to plan.pages order; PYTHONHASHSEED=0 stable |
| D5 Error Isolation | `return_exceptions=True`; failed page → Warning + skip, not abort |
| D7 Test Coverage | 4 functions: order + concurrency limit + evaluate order + page failure isolated |
| D10 Performance | 4x wall-clock reduction verified by concurrency limit test |
| D13 Integration | LLMProvider semaphore still active beneath asyncio.gather (double-gated) |

### Now (runbook)

```bash
# 1. Read current page loop in generate/worker.py
grep -n "for page_plan\|for page\|await.*gen\|asyncio" src/launcher/workers/generate/worker.py | head -30

# 2. Read evaluate/worker.py LLM review loop
grep -n "for.*page\|llm_review\|asyncio\|gather" src/launcher/workers/evaluate/worker.py | head -30

# 3. Find LLMProvider semaphore
grep -n "semaphore\|Semaphore" src/launcher/clients/llm_provider.py | head -10

# 4. Implement _generate_page coroutine + gather; implement _evaluate_page_llm + gather

# 5. Run worker tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## HO-06 — H5.8: Section-Level Finding→section_id Granularity

**Status**: Done
**Evidence**: 5/5 section_id tests pass (TestSectionIdMapping); 2662 total suite green.
**Files changed**: `src/launcher/models/evaluation.py` (added `section_id: str | None = None` to `Finding`), `src/launcher/workers/evaluate/checks/density.py` (section_id=heading for per-section density findings), `src/launcher/workers/evaluate/checks/structure.py` (section_id=text for per-heading findings: hierarchy skip, template-label, deep heading, long heading), `src/launcher/workers/generate/worker.py` (added `cached_page_ir` parameter to `_generate_page`; added section-skip logic using `heal_metadata.failing_section_ids`; emits `generate_section_skipped` for reused cached sections), `tests/unit/workers/test_selective_regen.py` (added `TestSectionIdMapping` class with 5 tests)
**Gap linkage**: G-HO-06
**Depends on**: HO-01 complete (generate/worker.py stable); HO-05 complete (parallel loop stable)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Map evaluation findings to `section_id` (section heading) so that during heal,
only the failing sections within a failing page are regenerated — not all sections.

Part A — `evaluate/checks/*.py` (structure, density, code, seo, readability):
- Add `section_id: str | None = None` field to `Finding` model (if not already present)
- In each check function, when iterating sections, set `finding.section_id = section_heading`

Part B — `generate/worker.py` (section loop):
- When `heal_target_pages` is set and `heal_metadata` contains `failing_section_ids` for a page,
  skip sections NOT in `failing_section_ids`; reuse their existing SectionIR from checkpoint
- Emit `generate_section_skipped` event for each reused section

**Allowed paths**:
- `src/launcher/models/evaluation.py` (add `section_id` to `Finding` if missing)
- `src/launcher/workers/evaluate/checks/structure.py`
- `src/launcher/workers/evaluate/checks/density.py`
- `src/launcher/workers/evaluate/checks/code.py`
- `src/launcher/workers/evaluate/checks/seo.py`
- `src/launcher/workers/evaluate/checks/readability.py`
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/test_selective_regen.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_finding_has_section_id_when_section_scoped` — structure/density findings carry `section_id`
  - `test_finding_section_id_is_none_for_global_checks` — safety/slug_safety findings have `section_id=None`
  - `test_section_skip_reuses_cached_section` — when `failing_section_ids` set, non-failing section reused
  - `test_section_skipped_event_emitted` — `generate_section_skipped` event emitted per reused section
- **Config respected end-to-end**: section-level skip only when `heal_metadata.failing_section_ids` present
- **No mock data in production paths**: reused SectionIR loaded from artifact checkpoint, not hardcoded

### Deliverables

- `Finding` model with `section_id: str | None = None` (backward-compatible: default None)
- 5 check files updated to set `section_id` from section heading when iterating sections
- `generate/worker.py` section loop with section-level skip logic
- Tests covering: section_id populated + global checks have None + section reuse + event emitted
- No stubs, no TODOs; all call sites of `Finding()` updated to pass `section_id` where applicable

### Hard rules

- `section_id` field must be `Optional[str]` with default `None` — no breaking change to existing Finding usages
- Section-level skip only activates when `heal_metadata.failing_section_ids` is non-empty — normal pipeline unaffected
- Cached SectionIR load failure → fall back to regenerating that section (not crashing)
- Deterministic: sections processed in original skeleton order regardless of skip pattern
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D2 Contract Compliance | `Finding.section_id` is `Optional[str]`; no existing call site breaks |
| D5 Error Isolation | Section cache miss → regenerate (not crash); per-section try/except preserved |
| D7 Test Coverage | 4 functions: section_id populated + global None + reuse + event |
| D10 Performance | ~50% further Generate reduction for pages with mixed pass/fail sections |
| D13 Integration | `failing_section_ids` set by `heal.py` from findings with non-None section_id |

### Now (runbook)

```bash
# 1. Check if Finding model already has section_id
grep -n "section_id\|class Finding" src/launcher/models/evaluation.py

# 2. Check structure.py section iteration pattern
grep -n "section\|heading\|Finding(" src/launcher/workers/evaluate/checks/structure.py | head -20

# 3. Check generate/worker.py section loop
grep -n "for.*skel_section\|for.*section\|failing_section" src/launcher/workers/generate/worker.py | head -20

# 4. Implement: add Finding.section_id → update 5 check files → add section-skip in generate/worker.py

# 5. Run worker tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -v

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```
