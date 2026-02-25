# Spec 43: Resumable Pipeline Execution

**Status**: Binding
**Version**: v1.0
**Author**: Agent
**Date**: 2026-02-21
**TC**: TC-2398 (spec), TC-2399 (implementation)

---

## Overview

By default every `launch run` starts from W1 (clone_inputs) and re-runs the entire 11-worker
pipeline. When a bug is isolated to a single worker (e.g., W5), the developer must wait
30–60 min for all preceding workers to complete before reaching the failure — then repeat the
cycle after fixing the code.

This spec defines the `launch resume` command, which takes the artifacts already produced by
a prior run and re-enters the pipeline at any specified worker. Earlier workers are skipped
entirely; later workers execute as normal.

---

## Command Contract

```
launch resume --run-dir <path> --from-worker <alias> [--verbose]
```

### Parameters

| Parameter | Required | Description |
|---|---|---|
| `--run-dir` | Yes | Path to an existing run directory (`runs/<run_id>/`). Must be under the `runs/` root enforced by `validate_run_dir_under_runs()`. |
| `--from-worker` | Yes | Worker alias (see §Node Aliases). Case-sensitive. Both short form (`W5`) and full node name (`draft_sections`) are accepted. |
| `--verbose` | No | Increase logging verbosity. |

### Behaviour

1. `run_config.yaml` is loaded from `--run-dir`. No `--config` flag is accepted — the config
   is always taken from the run directory so resumed runs use identical configuration.
2. The existing `run_dir` is used **in-place**. Artifacts produced by `--from-worker` and
   later workers are overwritten. Artifacts produced by earlier workers are preserved unchanged.
3. Events are **appended** to the existing `events.ndjson`. The event log is never truncated
   or reset. A `RUN_RESUMED` event is emitted before graph execution begins (see §Events).
4. `snapshot.json` is re-written at each state transition, exactly as in a normal run.
5. The run ID (`run_dir.name`) is unchanged; the resume is a continuation of the same run,
   not a new run.

---

## Node Aliases

Both short form (`W1`–`W11`) and full graph node names are accepted as `--from-worker` values.

| Short alias | Graph node | Pre-execution `run_state` |
|---|---|---|
| `W1` | `clone_inputs` | `CREATED` |
| `W2` | `ingest` | `CLONED_INPUTS` |
| `W3` | `build_facts` | `INGESTED` |
| `W4` | `plan_pages` | `FACTS_READY` |
| `W5` | `draft_sections` | `PLAN_READY` |
| `W6` | `optimize_seo` | `DRAFT_READY` |
| `W7` | `review_content` | `DRAFT_READY` |
| `W8` | `link_and_patch` | `DRAFT_READY` |
| `W9` | `validate` | `LINKING` |
| `W10` | `fix` | `VALIDATING` |
| `W11` | `open_pr` | `READY_FOR_PR` |

Full node names (`clone_inputs`, `ingest`, `build_facts`, `plan_pages`, `draft_sections`,
`optimize_seo`, `review_content`, `link_and_patch`, `validate`, `fix`, `open_pr`) are
accepted as equivalent aliases.

---

## Artifact Pre-validation

Before the LangGraph execution begins, the CLI validates that all artifacts required as inputs
by `--from-worker` are present in `run_dir`. If any required path is missing the command fails
immediately with exit code 1 and a message listing all missing paths.

Required artifacts are **cumulative** — each row in the table below lists the **additional**
artifacts required on top of the previous row.

| Entry point | Additional required paths (relative to `run_dir/`) |
|---|---|
| `W1` / `clone_inputs` | *(none)* |
| `W2` / `ingest` | `work/repo/` (directory) |
| `W3` / `build_facts` | `artifacts/repo_inventory.json`, `artifacts/frontmatter_contract.json` |
| `W4` / `plan_pages` | `artifacts/product_facts.json`, `artifacts/snippet_catalog.json` |
| `W5` / `draft_sections` | `artifacts/page_plan.json` |
| `W6` / `optimize_seo` | `artifacts/draft_manifest.json`, `drafts/` with ≥1 `.md` file |
| `W7` / `review_content` | `artifacts/seo_report.json` |
| `W8` / `link_and_patch` | *(same as W7)* |
| `W9` / `validate` | `artifacts/patch_bundle.json` |
| `W10` / `fix` | `artifacts/validation_report.json` |
| `W11` / `open_pr` | `artifacts/patch_bundle.json` |

---

## Events

### `RUN_RESUMED`

Emitted to `events.ndjson` (appended, never replacing prior events) immediately before
`compiled_graph.stream()` is called:

```json
{
  "event_id": "<uuid>",
  "run_id": "<run_id>",
  "ts": "<ISO-8601>",
  "type": "RUN_RESUMED",
  "payload": {
    "from_worker_alias": "W5",
    "from_node": "draft_sections",
    "initial_run_state": "PLAN_READY"
  },
  "trace_id": "<trace_id>",
  "span_id": "<span_id>",
  "parent_span_id": "<parent_span_id>"
}
```

Subsequent state-transition events (`RUN_STATE_CHANGED`) and work-item events are written
exactly as in a normal run.

---

## Dynamic Graph Entry Point

The LangGraph `StateGraph` is built with a configurable entry point:

```python
# src/launch/orchestrator/graph.py
def build_orchestrator_graph(start_node: str = "clone_inputs") -> StateGraph:
    ...
    graph.set_entry_point(start_node)   # was hard-coded to "clone_inputs"
```

The default value preserves full backward compatibility — all existing callers of
`build_orchestrator_graph()` without arguments are unaffected.

---

## `run_pilot.py` Integration

```bash
python scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --from-worker W5
```

When `--from-worker` is provided:
1. The most recent run directory for that pilot is read from `runs/manifest.jsonl`
   (latest entry matching `pilot == product_slug`).
2. `launch resume --run-dir <output_dir> --from-worker <alias>` is called via subprocess.
3. If no prior run exists for that pilot, the script exits with an error message.

`--from-worker` and the normal `--dry-run` / `--output` flags are mutually compatible.

---

## Governance

### validation_profile
- `local` profile: no taskcard required (same behaviour as `launch run`).
- `prod` profile: taskcard required in `run_config.yaml` (same as `launch run`).

The resumed run inherits the `validation_profile` from the stored `run_config.yaml`.

### Scope
`launch resume` is a **debugging and development tool**. It is not intended for production
content-generation pipelines. Production runs must use `launch run` from W1 to ensure
full reproducibility and an unbroken event log.

### Determinism
Because earlier workers are skipped, the event log of a resumed run is not fully equivalent
to a fresh full run. Resumed runs MUST NOT be used as golden baselines for VFV determinism
testing (`TC-903`).

---

## Exit Codes

| Condition | Exit code |
|---|---|
| Run completes successfully (DONE state) | 0 |
| Unknown `--from-worker` alias | 1 |
| Missing required artifact(s) | 1 |
| `run_dir` not under `runs/` root | 1 |
| `run_config.yaml` missing from `run_dir` | 1 |
| Graph execution failure (FAILED state) | 2 |

---

## Page-Level Incremental Caching

While `launch resume` provides **worker-level** granularity (skip all work before the
specified worker), the following run_config flags add **page-level** granularity within W5:

| Mechanism | Granularity | Description |
|-----------|-------------|-------------|
| `launch resume --from-worker W5` | Worker-level | Skip W1–W4; all W5 pages regenerate |
| `caching.enabled: true` | Page-level | Skip individual pages whose input hash matches cache |
| `regen_failed_only: true` | Page-level (failures only) | Only regenerate pages with gate failures |

**Combining both mechanisms**: `launch resume --from-worker W5` + `regen_failed_only: true`
gives the most targeted re-run — skip W1–W4, then within W5 only regenerate the specific
pages that failed gates in the prior run.

For full details on page input hashing, cache hit contract, and `page_status` values,
see `specs/47_worker_cache_and_incremental_execution.md`.

---

## Implementation Reference

- `src/launch/orchestrator/graph.py` — `build_orchestrator_graph(start_node)` (TC-2399)
- `src/launch/orchestrator/run_loop.py` — `RESUME_NODE_MAP`, `execute_run_from_node()` (TC-2399)
- `src/launch/cli/main.py` — `resume` command (TC-2399)
- `scripts/run_pilot.py` — `--from-worker` flag (TC-2399)
- `tests/unit/orchestrator/test_resume_from_node.py` — unit tests (TC-2399)
- `src/launch/workers/_shared/worker_cache.py` — page-level cache (TC-2450)
