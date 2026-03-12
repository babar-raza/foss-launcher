# H5 Optimization Phase — Gap Index & Taskcards

## Context

Self-review of `quirky-mapping-mccarthy.md` identified that the entire Phase H5
(8 tasks) was planned but never implemented. H5 is the efficiency layer that makes
the heal system viable at scale.

**Without H5, a 10-step heal session costs ~1,360 LLM calls, ~2.75M tokens, ~120 min.**
**With H5, the same session costs ~264 calls, ~500K tokens, ~8 min (81%/82%/93% reduction).**

H5 depends on HL-01 (pipeline re-execution hook) being complete. All H5 tasks should
be blocked until HL-01 is Done.

### Dependency order within H5
```
H5-01 (page filter)  ──▶  H5-06 (parallel gen)  ──▶  H5-07 (section-level)
H5-02 (worker skip)       independent
H5-03 (eval fast)         independent
H5-04 (cache)             independent (already partially done in HL-01)
H5-05 (budget/step)       independent
H5-08 (diagnostician)     independent
```

H5-01 must complete before H5-06 and H5-07.
H5-02, H5-03, H5-04, H5-05, H5-08 are independent of each other and of H5-01.

---

## Gap Table

| Gap ID | Description                                                         | Taskcard | Priority |
|--------|---------------------------------------------------------------------|----------|----------|
| GAP-05 | H5.1 Selective page re-generation (skip passing pages)              | H5-01    | HIGH     |
| GAP-05 | H5.2 Worker skip logic (skip Understand+Planner for Generate-only)  | H5-02    | HIGH     |
| GAP-05 | H5.3 Evaluate fast path (skip LLM review for A/B pages)             | H5-03    | HIGH     |
| GAP-05 | H5.4 Cache enablement (already partially in HL-01; document here)   | H5-04    | MEDIUM   |
| GAP-05 | H5.5 Token budget per-step + adaptive page prioritization           | H5-05    | MEDIUM   |
| GAP-05 | H5.6 Parallel section generation (asyncio.gather + semaphore)       | H5-06    | HIGH     |
| GAP-05 | H5.7 Diagnostician prompt compression (rolling summary, cap 6K)     | H5-08    | MEDIUM   |
| GAP-05 | H5.8 Section-level granularity (regenerate only failing sections)   | H5-07    | HIGH     |

> **Prerequisite:** HL-01 must be Done before any H5 taskcard starts.

---

## H5-01 — Selective Page Re-Generation

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.1)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
Currently the heal loop re-runs all pages. The LLM decision (`HealAction.target_pages`)
already provides the target list, but the pipeline ignores it and re-runs everything.

1. Add `heal_target_pages: list[str] | None` field to `WorkerContext` (in
   `src/launcher/orchestrator/worker_contract.py`). `None` means "all pages" (normal
   run). A non-empty list means heal mode: only generate pages in the list.

2. In `src/launcher/workers/generate/worker.py`, read `ctx.heal_target_pages`. If set,
   skip any page whose `page_id` is NOT in `heal_target_pages`:
   ```python
   if ctx.heal_target_pages is not None and page_id not in ctx.heal_target_pages:
       logger.debug("[generate] heal: skipping passing page %s", page_id)
       continue  # reuse existing artifact from previous run
   ```

3. In `_write_heal_metadata` (from HL-01), include `target_pages` in the metadata so
   `graph_builder.py` can pass it into `WorkerContext` when building the heal re-run.

4. When a page is skipped, copy its previous artifact from the last checkpoint
   (use `load_worker_checkpoint` to find the previous generate artifact path, then
   symlink or copy to the current run artifact location).

**Allowed paths:**
- `src/launcher/orchestrator/worker_contract.py`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/cli/heal.py`
- `tests/unit/workers/test_generate.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_heal_skips_passing_pages` — `heal_target_pages=["page-a"]`; assert generate worker processes only "page-a"; passing pages reuse artifacts
- `test_heal_none_target_runs_all_pages` — `heal_target_pages=None` → all pages generated (normal behavior)
- `test_heal_target_pages_in_heal_metadata_json` — `heal_metadata.json` contains `target_pages` list
- `test_skipped_page_artifact_copied_from_checkpoint` — skipped page output artifact exists after heal step

**CLI:**
```bash
# With heal step targeting 3 of 34 pages → ~9% of generate calls
python -m launcher.cli.main heal --run-dir /tmp/test_run --max-steps 1
# Verify: generate worker log shows "skipping passing page" for non-targeted pages
```

**Config respected end-to-end:** `heal_target_pages=None` in non-heal runs is a no-op.

### Deliverables
- Updated `worker_contract.py` with `heal_target_pages` field
- Updated `generate/worker.py` with skip logic + artifact copy
- Updated `cli/heal.py` to include `target_pages` in heal_metadata
- Tests covering all acceptance checks

### Hard rules
- `heal_target_pages=None` must be the default; non-heal runs MUST be unaffected
- Artifact copy must be atomic (use `shutil.copy2` or `atomic_write_json` equivalent)
- Skipped page log at DEBUG not INFO (to avoid log spam in normal runs)
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | 8/34 failing → ~24 Generate calls instead of 102 (76% reduction) |
| Correctness | Non-targeted pages reuse previous artifacts unchanged |
| Integration | `heal_target_pages=None` leaves all existing code paths unaffected |

### Now (runbook)
```bash
# 1. Add heal_target_pages: list[str] | None = None to WorkerContext
# 2. Add page-skip logic in generate/worker.py main loop
# 3. Add target_pages to heal_metadata written by _write_heal_metadata in heal.py
# 4. Wire heal_metadata target_pages into WorkerContext in graph_builder.py heal path
# 5. Write tests
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v -k heal
# 7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-02 — Worker Skip Logic (Earliest Responsible Worker)

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.2)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
When the LLM identifies "generate" as the responsible worker, there is no reason to
re-run Understand or Planner. The `earliest_responsible_worker()` helper (H2.5, in
`src/launcher/workers/evaluate/diagnosis.py`) already computes the correct re-entry
point. This taskcard wires it into the graph_builder's heal re-run path.

1. In `src/launcher/orchestrator/graph_builder.py`, add a `heal_entry_worker: str | None`
   parameter to the build function. When set, configure the graph to skip all workers
   that come before `heal_entry_worker` in the pipeline order:
   `["understand", "planner", "generate", "evaluate", "publish"]`

2. In `cli/heal.py`, after parsing the `HealDecision`, call
   `earliest_responsible_worker(diagnoses)` from `diagnosis.py` to determine the
   re-entry worker. Pass it through `heal_metadata` so `_trigger_worker_rerun` can
   forward it to `graph_builder`.

3. The skip must be robust: if `heal_entry_worker` is "generate", the graph builder
   must feed the existing Understand + Planner outputs (from the last checkpoint) as
   inputs to the Generate worker without re-running them.

**Allowed paths:**
- `src/launcher/orchestrator/graph_builder.py`
- `src/launcher/cli/heal.py`
- `tests/unit/orchestrator/test_graph_builder.py` (NEW or extend)

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_graph_skips_understand_when_entry_is_generate` — build graph with `heal_entry_worker="generate"`; assert Understand and Planner nodes absent from execution plan
- `test_graph_runs_all_when_no_entry_worker` — `heal_entry_worker=None` → full pipeline
- `test_graph_skips_planner_when_entry_is_planner` — `heal_entry_worker="planner"` → only Understand skipped
- `test_heal_metadata_contains_entry_worker` — `heal_metadata.json` contains `"entry_worker": "generate"`

### Deliverables
- Updated `graph_builder.py` with `heal_entry_worker` parameter
- Updated `cli/heal.py` to compute and pass entry worker
- Tests covering all acceptance checks

### Hard rules
- `heal_entry_worker=None` is the default; full pipeline for non-heal runs
- Prior checkpoint outputs must be loaded correctly as inputs when workers are skipped
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | Understand + Planner skipped for Generate-targeted heals (~100% upstream savings) |
| Correctness | Skipped worker outputs come from checkpoint, not re-computed |
| Integration | Non-heal runs unaffected |

### Now (runbook)
```bash
# 1. Read graph_builder.py to understand current pipeline node registration
# 2. Add heal_entry_worker param; add skip logic for preceding workers
# 3. Update cli/heal.py to compute entry_worker from diagnosis + pass through heal_metadata
# 4. Write tests
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-03 — Evaluate Fast Path (Skip LLM Review for A/B Pages)

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.3)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
During a heal step, pages graded A or B in the previous evaluation don't need
LLM review — they already pass. Running LLM review on them wastes ~76% of Evaluate
LLM calls when 8/34 pages are failing.

1. Add `eval_fast_path: bool = False` to `WorkerContext` in `worker_contract.py`.

2. In `src/launcher/workers/evaluate/worker.py`, when `ctx.eval_fast_path` is True:
   - Run all deterministic checks (no LLM call needed for these)
   - Skip LLM review (`_run_llm_review()`) for pages that were A/B in the previous evaluation
   - A/B page list must be read from the previous `evaluate_checkpoint.json` (disk-truth)

3. Wire `eval_fast_path=True` into `heal_metadata` so `graph_builder` sets it on
   `WorkerContext` during heal re-runs.

**Allowed paths:**
- `src/launcher/orchestrator/worker_contract.py`
- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/cli/heal.py`
- `tests/unit/workers/test_generate.py` (or new `tests/unit/workers/test_evaluate_fast.py`)

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_eval_fast_path_skips_llm_for_ab_pages` — `eval_fast_path=True`, page graded "A" in checkpoint → `_run_llm_review` not called for that page
- `test_eval_fast_path_runs_llm_for_df_pages` — `eval_fast_path=True`, page graded "D" → LLM review runs
- `test_eval_fast_path_false_runs_all_pages` — `eval_fast_path=False` → all pages get LLM review (existing behavior)
- `test_eval_fast_path_uses_disk_checkpoint` — A/B list read from `evaluate_checkpoint.json`, not in-memory state

### Deliverables
- Updated `worker_contract.py`, `evaluate/worker.py`, `cli/heal.py`
- Tests covering all acceptance checks

### Hard rules
- `eval_fast_path=False` is the default — existing non-heal behavior must be identical
- A/B determination must read from disk (disk-truth principle)
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | ~76% fewer Evaluate LLM calls when 24/34 pages are A/B |
| Correctness | D/F pages always get full LLM review regardless of fast path |
| Robustness | Missing checkpoint falls back to running LLM review for all pages |

### Now (runbook)
```bash
# 1. Add eval_fast_path to WorkerContext
# 2. Add A/B skip logic in evaluate/worker.py _run_llm_review path
# 3. Set eval_fast_path=True in heal_metadata
# 4. Write tests
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-04 — LLM Cache Enablement + Documentation

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.4)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
HL-01 already adds `os.environ["FOSS_LAUNCHER_LLM_CACHE"] = "1"` in `run_heal`.
This taskcard:

1. Verifies the env var is actually respected by `llm_cache.py` / `llm_provider.py`
   (read the code to confirm; add a warning log if the env var is set but the cache
   module is not configured to check it).

2. Documents the cache behavior in `cli/heal.py` docstring for `run_heal`:
   ```
   LLM disk cache is enabled for the duration of the heal session
   (FOSS_LAUNCHER_LLM_CACHE=1). This eliminates redundant LLM calls for
   unchanged prompts between steps. Cache is restored to its pre-session
   state on exit.
   ```

3. Adds a test:
   - `test_llm_cache_enabled_during_heal` — after `run_heal` starts, assert
     `os.environ["FOSS_LAUNCHER_LLM_CACHE"] == "1"` (mock to inspect env state
     mid-execution)
   - `test_llm_cache_restored_on_exit` — after `run_heal` completes, assert env
     var is restored to its prior value (both cases: was set, was unset)

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_llm_cache_enabled_during_heal`
- `test_llm_cache_restored_to_prior_value`
- `test_llm_cache_restored_when_was_unset`

### Deliverables
- Updated docstring in `run_heal`
- 3 unit tests confirming cache enable/restore behavior

### Hard rules
- No change to the existing cache enable/restore logic unless a bug is found
- If `FOSS_LAUNCHER_LLM_CACHE` is not respected by `llm_cache.py`, log a WARNING at session start

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | Cache enabled before first LLM call; restored unconditionally |
| Observability | `[heal] LLM disk cache enabled for heal session` logged at INFO |
| Testability | Both enable and restore tested with mock |

### Now (runbook)
```bash
# 1. Read src/launcher/clients/llm_cache.py to confirm FOSS_LAUNCHER_LLM_CACHE is respected
# 2. Update run_heal docstring
# 3. Write 3 tests
# 4. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py -v -k cache
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-05 — Token Budget Per-Step + Adaptive Page Prioritization

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.5)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
Currently the heal loop uses a global BudgetTracker with a single call to
`budget.check_runtime()`. The plan calls for per-step token envelopes and
adaptive page prioritization (F→D→C first).

The `_prioritize_target_pages` helper is already implemented in `cli/heal.py`
(it sorts F→D→C and caps by `budget.remaining_for_step()`). This taskcard
verifies it's actually called and wires it into the LLM decision:

1. Confirm `_prioritize_target_pages` is called after parsing the `HealDecision`
   and its output is used as the effective `target_pages` (overriding the LLM's
   raw list if the budget cap is smaller). Add this call if missing.

2. Add `remaining_for_step(step_idx, max_steps) -> dict` to `BudgetTracker` if
   not already present. Must return `{"calls_per_step": int, "tokens_per_step": int}`.

3. Log the effective target list at INFO:
   ```python
   logger.info(
       "[heal] Step %d: effective target_pages=%s (budget cap=%d)",
       step_idx, effective_pages, cap,
   )
   ```

4. If `effective_pages` is empty after budget cap (budget exhausted), set
   `stop_reason = "budget_exceeded"` and break.

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `src/launcher/util/budget_tracker.py`
- `tests/unit/util/test_budget_tracker.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_prioritize_target_pages_sorts_f_before_d` — F-graded pages appear before D-graded in output
- `test_prioritize_respects_budget_cap` — `calls_per_step=2` → at most 2 pages returned
- `test_budget_cap_zero_stops_session` — `calls_per_step=0` → `stop_reason="budget_exceeded"`
- `test_remaining_for_step_returns_correct_envelope` — verify `remaining_for_step(0, 10)` allocates correctly

### Deliverables
- Updated `cli/heal.py` with confirmed `_prioritize_target_pages` wiring
- Updated `budget_tracker.py` with `remaining_for_step` if missing
- 4 tests

### Hard rules
- LLM decision `target_pages` is treated as a preference; budget cap is the hard limit
- `_prioritize_target_pages` must be called after the LLM decision, before re-run
- Sort must be deterministic: `(grade_severity, slug)` key (already implemented)

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | Per-step envelope prevents token exhaustion on large runs |
| Correctness | F/D pages always prioritized; A/B pages not targeted |
| Observability | Effective target list logged before each re-run |

### Now (runbook)
```bash
# 1. Read _prioritize_target_pages in heal.py — verify it's called in the main loop
# 2. Check budget_tracker.py for remaining_for_step — add if missing
# 3. Wire effective_pages into _trigger_worker_rerun call
# 4. Add budget_exceeded guard for empty effective_pages
# 5. Write 4 tests
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-06 — Parallel Section Generation (asyncio.gather + Semaphore)

**Status:** Blocked (on H5-01)
**Gap linkage:** GAP-05 (H5.6)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
`generate/worker.py` currently processes sections sequentially. With
`heal_target_pages` limiting the page set (H5-01), parallelizing section generation
within each page yields a further 3-4x wall-clock reduction.

1. Wrap per-section LLM calls in `asyncio.gather()`, limited by the existing
   `LLMProvider` semaphore (concurrency=4 as per H5.6 spec).

2. Section order in the output must be the same as input order (sort by section index
   after gather).

3. The enforcement cascade (`enforce_block_spec`) runs per-section after each LLM
   result (not batched).

4. Cross-section deduplication in `section_validator.py` still runs post-collect on
   the full ordered section list.

5. Only the LLM call within each section is parallelized; deterministic pre- and
   post-processing remains sequential.

**Allowed paths:**
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/test_generate.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_sections_generated_in_parallel` — mock LLM; assert all sections complete (order preserved)
- `test_section_order_preserved` — 5 sections in order; after gather, output order matches input
- `test_semaphore_limits_concurrency` — semaphore with maxsize=1; assert sections processed serially when semaphore=1
- `test_enforcement_runs_per_section` — mock enforcement; assert called once per section after its LLM result

**Performance:**
```bash
# Spot-check: 10 sections with 0.1s mock LLM latency should complete in ~0.1s (parallel) not ~1s (serial)
```

### Deliverables
- Updated `generate/worker.py` with `asyncio.gather()` section parallelism
- Tests confirming order preservation, semaphore, enforcement

### Hard rules
- `PYTHONHASHSEED=0` still required — parallelism must not affect output determinism
- Section output list sorted by original section index before downstream processing
- Existing `section_validator.py` cross-section deduplication called unchanged post-collect
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | Concurrency=4; 10-section page completes in ~1/4 the serial time |
| Correctness | Output identical to serial execution with same inputs |
| Robustness | Single section failure does not cancel other sections (use `return_exceptions=True`) |

### Now (runbook)
```bash
# 1. Identify per-section LLM call site in generate/worker.py
# 2. Wrap section generation coroutines in asyncio.gather(return_exceptions=True)
# 3. Sort results by section index; handle exceptions by falling back to deterministic
# 4. Run enforcement cascade per-section in the gather result loop
# 5. Write tests
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v
# 7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-07 — Section-Level Granularity (Regenerate Only Failing Sections)

**Status:** Blocked (on H5-01, H5-06)
**Gap linkage:** GAP-05 (H5.8)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
Even within a targeted failing page, only some sections are actually failing. Regenerating
every section of a D-graded page wastes ~50% of calls on already-passing sections.

1. Add `heal_target_sections: dict[str, list[str]] | None` to `WorkerContext`:
   `{page_id: [section_id, ...]}`. `None` = all sections.

2. In each evaluate check that can be localized to a section (density, code, repetition,
   structure), add `section_id` to the `Finding` object if not already present.
   The `Finding` model already has a `location` field — use it as `section_id`.

3. In `generate/worker.py`, when `ctx.heal_target_sections` is set for a page,
   skip LLM generation for sections not in the list; reuse the previous section
   output from the last checkpoint.

4. In `cli/heal.py`, after the LLM decision, call a new helper
   `_extract_failing_sections(report, target_pages) -> dict[str, list[str]]`
   that maps page_id → list of section location strings from findings. Include
   this in `heal_metadata`.

**Allowed paths:**
- `src/launcher/orchestrator/worker_contract.py`
- `src/launcher/workers/generate/worker.py`
- `src/launcher/cli/heal.py`
- `tests/unit/workers/test_generate.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_section_skip_for_passing_sections` — page with 5 sections, 2 failing → LLM called only 2 times
- `test_section_none_runs_all` — `heal_target_sections=None` → all sections generated
- `test_extract_failing_sections_returns_correct_map` — findings with location → correct page→section map
- `test_passing_section_output_copied_from_checkpoint` — skipped section output exists in artifact

### Deliverables
- Updated `worker_contract.py`, `generate/worker.py`, `cli/heal.py`
- `_extract_failing_sections` helper in `cli/heal.py`
- Tests covering all acceptance checks

### Hard rules
- `heal_target_sections=None` is the default — non-heal runs identical
- Section reuse must be atomic — copy from checkpoint before overwriting
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | ~50% further reduction in Generate LLM calls within failing pages |
| Correctness | Passing sections byte-identical to previous run output |
| Integration | Combines with H5-01 (page filter) for compound savings |

### Now (runbook)
```bash
# 1. Add heal_target_sections to WorkerContext
# 2. Add _extract_failing_sections in heal.py
# 3. Add section-skip logic in generate/worker.py
# 4. Include section targets in heal_metadata
# 5. Write tests
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## H5-08 — Diagnostician Prompt Compression (Rolling Summary, Cap 6K Tokens)

**Status:** Blocked (on HL-01)
**Gap linkage:** GAP-05 (H5.7)

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
The rolling compression in `_build_diagnostician_prompt` (last 3 full, older compressed)
is implemented in HL-04's scope. This taskcard adds the remaining H5.7 requirements:

1. **Prompt length cap** — measure total prompt length before returning from
   `_build_diagnostician_prompt`. If over 6000 chars (~1500 tokens):
   - Truncate `eval_summary` (the failing_pages list) to top 5 instead of 10
   - Compress all history to one-line summaries (no full JSON steps)
   - Log WARNING: `[heal] Diagnostician prompt exceeds 6K chars (%d); compressing history`
   - Re-measure; if still over 6K, truncate `eval_summary` further (top 3 failing)

2. **Dedup persistent findings** — before building the prompt, identify findings that
   appear in ALL steps of history (persistent failures). Add them to a
   `"persistent_findings"` key in the prompt context with the note
   `"These checks have not improved across all heal steps — consider engineering fix."`.

```python
def _extract_persistent_findings(history: list[HealStep]) -> list[str]:
    """Return finding check names that appear in every step's before_metrics."""
    if len(history) < 2:
        return []
    # Collect failing checks per step
    sets = []
    for step in history:
        checks = set()
        # (Requires access to eval report — pass it in or derive from history context)
        sets.append(checks)
    if not sets:
        return []
    return sorted(set.intersection(*sets))
```

Note: persistent finding extraction requires access to the per-step eval state.
Simplification: extract from `step.decision.action.priority_checks` as a proxy
(checks the LLM kept targeting). Use the intersection of `priority_checks` across
all steps where `outcome != "improved"`.

3. All compression must be tested at step 10 (10 steps of history) to confirm
   prompt stays under 6K chars.

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_prompt_under_6k_at_step_10` — build prompt with 10 steps of history + 34 failing pages; assert `len(prompt) < 6000`
- `test_prompt_compression_triggered_over_6k` — mock large history; assert WARNING logged
- `test_persistent_findings_in_prompt` — 3 steps all targeting "density" check (not improved); assert `"persistent_findings"` in prompt
- `test_no_persistent_findings_if_outcome_improved` — step where "density" improved → not in persistent

### Deliverables
- Updated `_build_diagnostician_prompt` with length cap + persistent findings section
- `_extract_persistent_findings` helper
- 4 tests

### Hard rules
- Prompt cap is a soft limit (warn, compress, proceed) — never raise
- Compression must not remove quarantine or budget sections (they are safety-critical context)
- `PYTHONHASHSEED=0` — test with 10 steps must be deterministic

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Performance | Step-10 prompt ≤6K chars regardless of history depth |
| Correctness | Persistent findings accurately reflect multi-step stagnation |
| Observability | WARNING logged when compression triggers |

### Now (runbook)
```bash
# 1. Add prompt length measurement at end of _build_diagnostician_prompt
# 2. Add two-level compression logic (truncate failing_pages, compress history)
# 3. Add _extract_persistent_findings helper
# 4. Inject persistent_findings section into prompt
# 5. Write 4 tests (including step-10 length check)
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py -v -k compression
# 7. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```
