# Spec 44: Pipeline Parallelization

**Status**: Binding
**Version**: v1.0
**Author**: Agent
**Date**: 2026-02-21
**TCs**: TC-1041, TC-1045, TC-1402, TC-2362, TC-2401, TC-2403, TC-2404, TC-2405, TC-2406, TC-2407

---

## Overview

The FOSS Launcher pipeline runs eleven workers sequentially by design, but many operations
*within* individual workers are independent and can run concurrently. This spec documents every
parallelization mechanism in the pipeline: what is parallelized, how it is configured, thread
safety guarantees, and the sequential fallback contract.

The goal is to enable agents and developers to:

1. Understand which config keys control parallelism at each worker.
2. Know which operations are guaranteed thread-safe and which must remain sequential.
3. Follow the established patterns when adding new parallelism.

---

## Architecture Principle

**Worker-level execution is always sequential** (W1 → W2 → … → W11). Parallelism lives
*inside* individual workers, applied to independent sub-tasks (per-file, per-batch, per-page).

Every parallel block follows the same structure:

```python
n = min(len(items), run_config.get("config_key", default))
if n <= 1:
    for item in items:          # sequential fallback — identical output
        result = process(item)
else:
    with ThreadPoolExecutor(max_workers=n, thread_name_prefix="prefix") as pool:
        futures = {pool.submit(process, item): item for item in items}
        for fut in as_completed(futures):
            result = fut.result()
```

Setting any config key to `1` always produces output identical to the pre-parallelization
implementation. This is the canonical regression test strategy.

---

## Parallelization Inventory

### W2 — FactsBuilder

| Operation | Config key | Default | Range | TC |
|---|---|---|---|---|
| Claim enrichment batches | `max_parallel_batches` | 4 | 1–N | TC-1045 |
| Claim classification batches | `max_parallel_batches` | 4 | 1–N | TC-1402 |
| Code analysis (AST parse per file) | *(hardcoded)* | 4 | fixed | TC-1041 |
| Workflow LLM step generation | `max_parallel_batches` | 4 | 1–N | TC-2405 |
| Example enrichment | `max_parallel_batches` | 4 | 1–N | TC-2405 |

#### Claim enrichment (`enrich_claims.py`)

Claims are grouped into batches of 20. Each batch makes one LLM call. Batches run concurrently
up to `max_parallel_batches` workers. Results are merged in deterministic index order.

Thread safety: each batch receives a deep copy of its claims; no shared mutable state between
threads.

#### Claim classification (`classify_claims.py`)

Same batch pattern. Each batch classified independently. `all_classifications` dict merged
after all futures complete (main thread only).

#### Code analysis (`code_analyzer.py`)

One thread per source file. Hardcoded `max_workers=4`. File reads and AST parsing are
independent. Results aggregated via list extend in the main thread after `as_completed`.

#### Workflow step enrichment (`worker.py`, TC-2405)

Qualifying workflows (below `min_steps` threshold per `LLM_WORKFLOW_THRESHOLDS`) have their
`llm_generate_workflow_steps()` call run in parallel. **Mutations** (`wf['steps'].append`,
`claims.append`) are applied **in the main thread** after each future completes.

Thread safety guarantee: the inner function `_call_llm_for_wf` returns a snapshot of the
current steps list rather than mutating anything. All dict/list mutations happen sequentially
in the main thread via `as_completed`.

#### Example enrichment (`worker.py`, TC-2405)

`example_id` and `primary_snippet_id` are pre-assigned sequentially before the thread pool
starts. `enrich_example(example_file, repo_dir, claims)` is pure (reads files, uses claims
read-only, returns a dict). Results collected into an index-keyed dict and reassembled in
input order: `[results[i] for i in range(len(example_files))]`.

---

### W5 — SectionWriter

| Operation | Config key | Default | Range | TC |
|---|---|---|---|---|
| Per-page generation | `max_parallel_pages` | 1 | 1–16 | TC-2362 |
| Within-page section drafting | `max_parallel_sections` | 1 | 1–10 | TC-2401 |

#### Per-page generation (`worker.py`, TC-2362)

Each page gets an isolated `MultiPassOrchestrator` via `_make_page_orchestrator()`. A snapshot
of cross-page summaries is taken before the pool starts (preventing read/write races). Results
collected by `as_completed` and sorted by `(section_order, output_path)` for determinism.

Default is `1` (sequential) because page quality can improve when the previous page's summary
is available for context. Increase to `4` when speed is prioritized over cross-page coherence.

#### Within-page section drafting (`multi_pass.py`, TC-2401)

Within a single page's draft pass, individual sections can be drafted concurrently.
Results are re-indexed to preserve section order. Trade-off: `prev_section_summary` chaining
is disabled in parallel mode; the outline provides structural context as mitigation.

---

### W6 — SEOOptimizer

| Operation | Config key | Default | Range | TC |
|---|---|---|---|---|
| Per-page SEO optimization | `max_parallel_pages` | 4 | 1–N | — |

W6 parallelizes SEO calls per page using the same `max_parallel_pages` key as W5. All pages
are independent (no cross-page state during SEO). Default 4 (not 1) because SEO optimization
has no coherence dependency between pages.

---

### W7 — ContentReviewer

| Operation | Config key | Default | Range | TC |
|---|---|---|---|---|
| Phase 0 format-fix LLM (per page) | `max_parallel_workers_w7` | 4 | 1–8 | TC-2406 |
| Check dimension execution | `max_parallel_workers_w7` | 4 | 1–8 | TC-2403 |
| Phase 4 regen per-file LLM (per agent) | `max_parallel_workers_w7` | 4 | 1–8 | TC-2407 |
| Post-sanitization (per file) | `max_parallel_workers_w7` | 4 | 1–8 | TC-2403 |

#### Phase 0 format-fix (`llm_format_fix.py`, TC-2406)

Before the 36-check cycle, each draft page receives one LLM call to detect and correct 7
formatting defect types (FQ-1 through FQ-7). With `max_parallel_workers_w7=4` and a
`_FORMAT_FIX_TIMEOUT_S=120` per-call cap, a 21-page run completes in ~12 min instead of
~84–294 min on local hardware.

`_process_one_page(draft_path, system_text, llm_client)` is pure: reads one file, makes one
LLM call, writes back the corrected content. No shared mutable state between threads.
`system_text` is loaded once before the pool starts.

#### Parallel check dimensions (`worker.py`, TC-2403)

W7 runs four check dimensions: Content Quality (CQ), Technical Accuracy (TA), Usability (US),
and Semantic Accuracy (SA). These are submitted concurrently via `_run_checks_parallel()`.

```python
_dim_issues, _semantic_cache = _run_checks_parallel(
    drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan,
    llm_client, n_workers, include_semantic=True,
)
```

`_run_checks_parallel` returns `(all_issues, semantic_issues)`. The `semantic_issues` list is
stored as `_semantic_cache` and **reused** across deterministic re-check passes (fix pass 1,
fix pass 2). Only after LLM regen is semantic accuracy re-run with `include_semantic=True`
(because LLM regen can introduce new API hallucinations).

**Semantic caching saves ~40 minutes** on a typical 82-minute W7 run by avoiding 2–3 redundant
LLM-based semantic accuracy sweeps.

Thread safety: all four check modules (`content_quality`, `technical_accuracy`, `usability`,
`semantic_accuracy`) read artifacts read-only. No shared mutable state between threads.

#### Phase 4 LLM regen (`llm_regen.py`, TC-2407)

When W7 routes to NEEDS_CHANGES or REJECT, specialist agents regenerate affected pages.
`_run_agent_on_files()` parallelizes the per-file LLM calls within each agent type using
`_process_one_regen_file(file_path_str, ...)` as a pure helper. The 4 agent types themselves
remain sequential (content_enhancer → technical_fixer → usability_improver → factual_verifier)
because they may fix different issues in the same file. A `_REGEN_TIMEOUT_S=120` per-call cap
prevents stalls. Mutations (`files_modified`, `files_failed`) are accumulated in the main thread.

#### Post-sanitization (`_sanitize_draft_file`, TC-2403)

After all fix and regen passes, 22 sanitizers are applied to each draft file. Files are
independent — `_sanitize_draft_file(draft_file, family, platform)` reads and writes only its
own file. Runs in a `ThreadPoolExecutor` with `n_workers` workers.

---

### W9 — Validator

| Operation | Config key | Default | Range | TC |
|---|---|---|---|---|
| Gate 17 per-file LLM checks | `max_parallel_files_g17` | 4 | 1–8 | TC-2404 |

#### Gate 17 per-file LLM parallelization (`gate_17_formatting_quality.py`, TC-2404)

Gate 17 calls the LLM format-fixer checklist once per markdown file. With `max_parallel_files=4`
and a 30-second per-file timeout, a 20-file run takes ~150s instead of ~600s.

The system prompt is loaded **once** before the pool starts. `_check_one_page(path, system_text,
llm_client)` is pure (reads one file, makes one LLM call, returns issues). Error flags are
accumulated in a list (`error_flags: List[bool]`); `gate_failed = any(error_flags)` is
evaluated after all futures complete.

W9 worker passes the config value with bounds enforcement:

```python
_g17_parallel = max(1, min(8, run_config.get("max_parallel_files_g17", 4)))
g17_passed, g17_issues = run_gate_17(md_files_g17, gate17_llm_client, max_parallel_files=_g17_parallel)
```

---

## Configuration Reference

All keys live in `run_config.yaml` / `run_config.schema.json`.

| Key | Worker | Default | Min | Max | Description |
|---|---|---|---|---|---|
| `max_parallel_batches` | W2 | 4 | 1 | — | Concurrent batches for claim enrichment, classification, workflow + example enrichment |
| `max_parallel_pages` | W5, W6 | 1 (W5) / 4 (W6) | 1 | 16 | Concurrent pages |
| `max_parallel_sections` | W5 | 1 | 1 | 10 | Concurrent sections within one page's draft pass |
| `max_parallel_workers_w7` | W7 | 4 | 1 | 8 | Concurrent check dimensions + post-sanitization files |
| `max_parallel_files_g17` | W9 | 4 | 1 | 8 | Concurrent per-file LLM calls in Gate 17 |

### Recommended pilot overrides for maximum speed

```yaml
max_parallel_batches: 4
max_parallel_pages: 4          # W5 — quality trade-off; use 1 for best cross-page coherence
max_parallel_sections: 4       # W5 — disables prev_section_summary chaining
max_parallel_workers_w7: 4
max_parallel_files_g17: 4
```

### Recommended conservative (quality-first) settings

```yaml
max_parallel_batches: 4        # Safe — batch outputs are independent
max_parallel_pages: 1          # W5 — preserves cross-page context
max_parallel_sections: 1       # W5 — preserves prev_section_summary chaining
max_parallel_workers_w7: 4     # Safe — check dims read-only
max_parallel_files_g17: 4      # Safe — gate 17 is detection-only
```

---

## Thread Safety Contract

### Safe to parallelize (read-only artifacts)

- Reading `product_facts.json`, `snippet_catalog.json`, `evidence_map.json`, `page_plan.json`
- Reading markdown files from `work/site/content/`
- Making LLM calls (HTTP, stateless)
- Pure transformation functions (sanitizers, claim ID hashing, TF-IDF scoring)

### Must remain sequential (shared mutable state)

- Appending to `claims` list (W2 workflow enrichment mutations)
- Appending to `wf['steps']` / `wf['claim_ids']` (W2 workflow dict mutations)
- Writing results to `example_inventory` list (W2 example enrichment)
- Writing per-gate results to `gate_results` list (W9)
- Writing per-page results to the manifest (W5)

The pattern for all mutable aggregations: threads return values, main thread applies mutations
after `fut.result()`.

---

## Adding New Parallelism

Follow this checklist when parallelizing a new loop:

1. **Identify independence**: confirm no item in the loop writes state read by another item.
2. **Add config key** to `run_config.schema.json` with `minimum: 1`, `maximum: N`, `default: D`.
3. **Sequential fallback**: wrap the original loop in `if n_workers <= 1:` — no behavior change.
4. **Pure inner function**: extract the loop body into a function that accepts only its inputs
   and returns its outputs. Never mutate shared state inside the function.
5. **Apply mutations in main thread**: collect `fut.result()` values, then mutate shared lists/dicts
   sequentially in the main thread.
6. **Test**: add a test asserting `n_workers=1` and `n_workers=4` produce identical output.
7. **Update this spec**.

---

## Performance Estimates

Based on typical 20-page pilot runs with `max_parallel_*: 4`:

| Worker | Before | After | Speedup |
|---|---|---|---|
| W2 claim enrichment | ~8 min | ~2 min | ~4x |
| W5 page generation | ~30 min | ~8 min | ~4x |
| W7 Phase 0 format fix | ~168 min (21 pages seq.) | ~12 min cap | ~14x |
| W7 (all optimizations) | ~82 min | ~20 min | ~4x |
| W7 Phase 4 regen (per agent) | ~2.5h worst-case | ~6 min/agent cap | ~25x |
| W7 semantic skipping | included above | — | saves ~40 min alone |
| W9 Gate 17 | ~10 min | ~2.5 min | ~4x |

End-to-end pipeline estimate: **~120 min → ~35 min** with all parallelism at `max_workers=4`.

---

## Spec Impact Log

| TC | Change |
|---|---|
| TC-1041 | W2 code analysis: hardcoded 4-worker AST parse pool |
| TC-1045 | W2 claim enrichment: `max_parallel_batches` |
| TC-1402 | W2 claim classification: `max_parallel_batches` |
| TC-2362 | W5 per-page: `max_parallel_pages` |
| TC-2401 | W5 within-page sections: `max_parallel_sections` |
| TC-2403 | W7 check dims + post-sanitization: `max_parallel_workers_w7`; semantic caching |
| TC-2404 | W9 Gate 17 per-file: `max_parallel_files_g17` |
| TC-2405 | W2 workflow + example enrichment: reuses `max_parallel_batches` |
| TC-2406 | W7 Phase 0 format-fix: `max_parallel_workers_w7`; `_FORMAT_FIX_TIMEOUT_S=120` per-call cap |
| TC-2407 | W7 Phase 4 regen per-file: `max_parallel_workers_w7`; `_REGEN_TIMEOUT_S=120` per-call cap |
