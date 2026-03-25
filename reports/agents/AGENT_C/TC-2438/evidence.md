# TC-2438 Evidence: W1+W2 Integration — repo_profile.json + citation_quality_score

**Date**: 2026-02-22
**Agent**: agent_c
**Status**: Done

---

## Changes Made

### 1. W1 Integration: `src/launch/workers/w1_repo_scout/worker.py`

Added block after the `hugo_facts.json` write (line ~642) and before `Emit WORK_ITEM_FINISHED`.
When `LAUNCH_REPO_PROFILING=1` environment variable is set:
- Calls `build_repo_profile_artifact(inventory)` from `repo_profiler.py`
- Writes `repo_profile.json` using the same atomic write pattern (temp + rename) as `repo_inventory.json`
- Logs `[W1] repo_profile.json written quality_tier=<tier>` at INFO
- On any exception: logs WARNING and continues (non-fatal)
- Sets `result["artifacts"]["repo_profile"]` on success

Pattern used: matches `write_repo_inventory_artifact()` in `fingerprint.py` (temp `.tmp` + `replace()`).

### 2. W2 Integration: `src/launch/workers/w2_facts_builder/worker.py`

Added `citation_quality_score` annotation to claims at TWO locations where `product_facts.json` is written:

**Location A** (~line 2225): W2b synthesis path (`execute_facts_builder_w2b`)
**Location B** (~line 3102): Main path (`execute_facts_builder`)

For each location, when `LAUNCH_REPO_PROFILING=1`:
- Reads `repo_profile.json` from `run_layout.artifacts_dir`
- Extracts `source_type_weights` dict
- Calls `score_citation_quality(claim["citations"], source_weights)` from `repo_profiler.py`
- Adds `claim["citation_quality_score"] = round(score, 4)` to each claim
- Never modifies `claim_id` or any other claim field
- On any exception: logs WARNING and continues (non-fatal)
- If `repo_profile.json` does not exist: silently skips

### 3. Schema: `specs/schemas/product_facts.schema.json`

Added `citation_quality_score` to the `claim` `$defs` `properties` section:
```json
"citation_quality_score": {
  "type": "number",
  "minimum": 0.0,
  "maximum": 1.0,
  "description": "Optional [0,1] evidence quality score from repo_profiler. Present only when LAUNCH_REPO_PROFILING=1."
}
```
Not included in `required` — it is optional.

---

## Test Results

**Command**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w1_repo_profiler.py tests/unit/test_validation_engine.py --tb=short -q`

**Result**: 69 passed, 0 failed, 1 warning

**Broader regression check** (`test_w1_repo_profiler.py`, `workers/w9/`, `test_validation_engine.py`, `test_validation_engine_golden.py`):

**Result**: 226 passed, 1 skipped, 0 failed

Pre-existing collection errors in `tests/unit/mcp/`, `tests/unit/orchestrator/`, and some `test_w5_*` files are unrelated to TC-2438 (confirmed by `git stash` verification).

---

## Safety Properties

- All new reads are wrapped in `try/except Exception` — pipeline never crashes
- `claim_id` is never modified
- `citation_quality_score` is opt-in (env var gate)
- Write pattern matches existing artifact writes in W1 (atomic temp+rename)
- Schema field is optional (not in `required`)
