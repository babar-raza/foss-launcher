# Autopilot Architecture

TC-3050 | Spec: specs/48_autopilot_phase_selection.md

## Overview

The autopilot system eliminates manual `launch resume --from-worker` guesswork.
Given a run config and target repo SHA, it determines the earliest safe pipeline
entry point by inspecting existing artifacts and a persistent state store.

- **First run**: full pipeline (W1)
- **Subsequent runs (same SHA)**: reuse cached W1-W5/W8/W9 artifacts, resume from earliest missing phase
- **SHA change**: re-clone and rebuild from W1

No LLM is required for the core decision. An optional LLM planner can suggest
earlier (never later) reruns when enabled.

## Architecture Flow

```
  run_config.yaml
        |
        v
  +-------------+     +---------------+
  | State Store |---->| Provenance    |  Check ruleset/templates version match
  | (.foss_state)|    | Validation    |  (TC-3070; skip hydration if stale)
  +-------------+     +-------+-------+
                              |
                        (provenance ok?)
                              |
                     yes      |      no
                  +-----------+-----------+
                  |                       |
                  v                       v
          +-------+-------+    (skip hydration;
          | Hydrate       |     start fresh W1)
          | run_dir       |
          +-------+-------+
                  |
                  v
          +-------+-------+
          | PhaseSelector |  Deterministic: walk checkpoints
          | (baseline)    |  First failure => start_worker
          +-------+-------+
                              |
                  +-----------+-----------+
                  |                       |
            (--llm flag?)           (no --llm)
                  |                       |
                  v                       |
          +-------+-------+              |
          | LLM Planner   |              |
          | (advisory)    |              |
          | guardrail:    |              |
          | never later   |              |
          +-------+-------+              |
                  |                       |
                  +----------+------------+
                             |
                             v
                  +----------+----------+
                  | execution_plan.json |  Written BEFORE pipeline starts
                  +----------+----------+
                             |
                             v
                  +----------+----------+
                  | Pipeline Executor   |  execute_run_from_node(start_worker)
                  | W1 -> W11           |
                  +----------+----------+
                             |
                             v
                  +----------+----------+
                  | Publish to Store    |  W1-W5,W8,W9 artifacts on success
                  | + provenance.json   |  (TC-3070: version tracking)
                  +---------------------+
```

## State Store

**Location**: `.foss_state/` (default), configurable via `autopilot.state_store_root`.

**Layout**:
```
.foss_state/
  <family>/<platform>/
    manifest.json           # best_sha, available_shas[]
    artifacts/
      <repo_sha>/
        w1/  *.json         # W1 artifacts (repo_inventory, etc.)
        w2/  *.json         # W2 artifacts (product_facts, etc.)
        w3/  *.json         # W3 artifacts (snippet_catalog, etc.)
        w4/  *.json         # W4 artifacts (page_plan, shared_facts)
        w5/  *.json         # W5 artifacts (draft_manifest, metrics)
        w8/  *.json         # W8 artifacts (patch_bundle)
        w9/  *.json         # W9 artifacts (validation_report)
        provenance.json    # Version tracking (TC-3070)
    conflicts/
      <repo_sha>/
        <worker>/  *.json   # Saved on content-mismatch
```

**Key derivation**: `get_store_key(run_config)` builds the key from
`family` and `target_platform` (e.g. `cells/python`).

**Safety invariants**:
- Never overwrites existing files with different content (SHA-256 check)
- Identical content = idempotent skip (safe to re-publish)
- Content mismatch = incoming file saved to `conflicts/` + `StoreConflictError`
- W1-W5, W8, W9 artifacts are stored (W6/W7 have no artifacts, W10 does in-place fixes, W11 is external state)

**Source**: `src/launch/state_store/store.py`

## PhaseSelector

The deterministic core. Walks pipeline checkpoints in order; the first failure
determines `start_worker`.

| Checkpoint | Target Worker | Artifacts Checked |
|------------|---------------|-------------------|
| 1 | W1 | `work/repo/` dir, `repo_inventory.json` (existence + JSON + schema), repo_sha match |
| 2 | W3 | `product_facts.json`, `snippet_catalog.json` |
| 3 | W4 | `page_plan.json`, `shared_facts.json` |
| 4 | W5 | `draft_manifest.json`, at least 1 `.md` under `drafts/` |
| 5 | W8 | `patch_bundle.json` |
| 6 | W9 | `validation_report.json` |

Post-validation logic:
- If `validation_summary` has fixable issues -> W10
- If `goal=pr` and all passed -> W11
- Otherwise -> `DONE`

**Reason codes**: `REPO_DIR_MISSING`, `REPO_SHA_MISMATCH`, `ARTIFACT_MISSING:<name>`,
`ARTIFACT_INVALID_JSON:<name>`, `ARTIFACT_SCHEMA_FAIL:<name>`, `DRAFTS_EMPTY`,
`VALIDATION_HAS_FIXABLE`, `ALL_PASSED`, `DONE`.

**Source**: `src/launch/autopilot/phase_selector.py`

## LLM Planner (Optional)

An advisory layer invoked only when `--llm` is passed to `launch drive`.

**Hard constraint**: the LLM may suggest an earlier start worker than baseline
but can NEVER skip past it. If it suggests a later worker, the suggestion is
rejected and baseline is used (`guardrail_applied=true`).

Example:
- Baseline = W5 (PhaseSelector determined W1-W4 artifacts are ready)
- LLM suggests W1 (wants to rebuild everything) -> accepted
- LLM suggests W9 (wants to skip ahead) -> rejected, W5 used

**Fallback**: if the LLM is unavailable or returns invalid JSON, the baseline
decision is used unchanged. No error is raised.

**Source**: `src/launch/autopilot/llm_planner.py`

## execution_plan.json

Written to `run_dir/artifacts/execution_plan.json` BEFORE pipeline execution
starts. This provides an audit trail regardless of whether the pipeline succeeds.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Always `"1.0"` |
| `baseline_start_worker` | string | PhaseSelector's deterministic decision |
| `final_start_worker` | string | Actual start worker (may differ if LLM used) |
| `reasons` | array | `[{code, message}]` — why this worker was chosen |
| `target_repo_sha` | string | Target git commit SHA |
| `hydrate_source` | string | Store path or `"none"` / `"failed"` |
| `hydrated_artifact_count` | int | Number of artifacts copied from store |
| `llm_planner_used` | bool | Whether LLM planner was consulted |
| `guardrail_applied` | bool | Whether LLM suggestion was rejected |
| `llm_rationale` | string | LLM's explanation (empty if not used) |
| `goal` | string | `"draft"` / `"validate"` / `"pr"` |
| `ruleset_version` | string | Ruleset version from run_config (TC-3070) |
| `templates_version` | string | Templates version from run_config (TC-3070) |
| `provenance_status` | string | `"none"`, store path, `"provenance_mismatch"`, or `"failed"` |
| `timestamp` | string | ISO-8601 UTC |

**Schema**: `specs/schemas/execution_plan.schema.json`

## Configuration

Add the optional `autopilot` block to `run_config.yaml`:

```yaml
autopilot:
  enabled: true
  state_store_root: ".foss_state"    # optional, default: .foss_state/
  llm_planner_enabled: false         # optional, default: false
```

**Schema**: `specs/schemas/run_config.schema.json` — the `autopilot` property is
optional with `additionalProperties: false`. Existing configs without this field
remain valid.

## Failure Modes and Recovery

| Scenario | Symptom | Recovery |
|----------|---------|----------|
| Provenance mismatch | `Provenance mismatch: RULESET_VERSION_MISMATCH` | Hydration skipped; fresh pipeline from W1 |
| Store hydration fails | `WARNING: Hydration failed` in output | Falls back to W1 automatically |
| Store content conflict | `StoreConflictError` on publish | Check `conflicts/` dir; re-run with `--force` or clean store |
| Schema validation fails | `ARTIFACT_SCHEMA_FAIL` reason | PhaseSelector rewinds to the worker that produces the artifact |
| LLM returns invalid JSON | `WARNING: LLM planner returned no suggestion` | Baseline used; no action needed |
| LLM suggests later worker | `guardrail_applied=true` in plan | Expected behavior; baseline used |
| Run dir already exists | `WARNING: RUN_DIR already exists` | Use `launch resume` instead, or delete the existing run |

## Provenance (TC-3070)

The provenance module (`src/launch/provenance/provenance.py`) provides:
- `compute_file_sha256(path)` — deterministic file hashing (binary mode, 8KB chunks)
- `compute_tree_hash(paths)` — sorted multi-file hashing
- `build_provenance(run_config, repo_sha, ...)` — schema-compliant provenance record
- `validate_provenance_compat(provenance, ...)` — compatibility checking

**Active integration** (TC-3070):
- **On publish**: `build_provenance()` + `write_provenance()` writes `provenance.json` alongside worker dirs
- **Before hydration**: `read_provenance()` + `validate_provenance_compat()` checks `ruleset_version` and `templates_version` match current run config
- **Mismatch**: hydration is skipped, pipeline starts from W1 (fresh)
- **Missing provenance.json**: backward compatible — warns but still hydrates (old stores)

This implements Spec 48 Readiness Rules (lines 94-107): an artifact set is reusable only if (1) SHA matches, (2) schemas valid, and (3) provenance compatible.

**Schema**: `specs/schemas/provenance.schema.json`
