---
id: TC-3874
title: "Fix _load_run_config to find run_config.json when run_config.yaml absent"
status: In-Progress
priority: High
owner: "claude-agent"
updated: "2026-03-08"
tags: [heal, run-config, blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3874_heal_load_run_config_json_fallback.md
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_load_run_config.py
evidence_required:
  - reports/TC-3874/evidence.md
---

# Taskcard TC-3874 — Fix _load_run_config to find run_config.json when run_config.yaml absent

## Objective

`_load_run_config` in `heal.py` only looks for `run_config.yaml`. Pipeline run
directories write `run_config.json` (not YAML). This means every heal step
silently returns `outcome="unchanged", fallback_reason="config_not_found"` —
the re-execution never runs. Fix by trying `run_config.json` as a fallback.

## Required spec references

- `src/launcher/cli/heal.py` — `_load_run_config`, `_execute_worker_rerun`

## Scope

### In scope
- Extend `_load_run_config` to probe `run_config.yaml` first, then `run_config.json`
- Add unit tests for both code paths and "neither found" case

### Out of scope
- No changes to how `run_config.json` is written by the orchestrator
- No changes to heal orchestration logic beyond `_load_run_config`

## Inputs

- `src/launcher/cli/heal.py` (current `_load_run_config`)

## Outputs

- `src/launcher/cli/heal.py` — `_load_run_config` probes both filenames
- `tests/unit/cli/test_heal_load_run_config.py` — new unit tests

## Allowed paths

- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_load_run_config.py`

### Allowed paths rationale
Direct fix to the broken function and its unit tests.

## Implementation steps

### Step 1: Update `_load_run_config`

Try `run_config.yaml` first (backward compat), then `run_config.json`.
Use `json.loads` for JSON, `yaml.safe_load` for YAML.

### Step 2: Add unit tests

Cover: YAML found, JSON found, neither found, malformed JSON.

## Failure modes

### Failure mode 1: YAML loader not available
**Detection**: `import yaml` raises ImportError
**Resolution**: JSON fallback still works; YAML case logs warning and continues
**Gate**: `_load_run_config` returns None only when both files absent

### Failure mode 2: Malformed JSON in run_config.json
**Detection**: `json.loads` raises JSONDecodeError
**Resolution**: Function logs warning and returns None → heal skips re-execution
**Gate**: Existing `config_dict is None` guard in `_execute_worker_rerun`

### Failure mode 3: Both files exist (YAML wins)
**Detection**: N/A — YAML is tried first, JSON never read
**Resolution**: Correct behavior — YAML takes precedence
**Gate**: Unit test verifies YAML wins when both present

## Task-specific review checklist

1. [ ] `_load_run_config` tries `run_config.yaml` first
2. [ ] `_load_run_config` tries `run_config.json` if YAML absent
3. [ ] JSON loaded with `json.loads` (no yaml import required for JSON path)
4. [ ] Warning log message updated to reflect both filenames
5. [ ] Unit tests cover: yaml-only, json-only, neither, malformed-json
6. [ ] Existing tests still pass (no regressions)
7. [ ] Docstrings updated for `_load_run_config`

## Deliverables

1. Modified `src/launcher/cli/heal.py`
2. New `tests/unit/cli/test_heal_load_run_config.py`

## Acceptance checks

1. [ ] `_load_run_config` returns config dict when `run_config.json` present
2. [ ] Heal step outcomes are no longer `config_not_found` for existing runs
3. [ ] All new tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3874/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_load_run_config.py -v
```

**Expected results**:
- All new tests pass
- `_load_run_config` returns dict for JSON-only run dirs

## Integration boundary proven

**Upstream**: `_execute_worker_rerun` calls `_load_run_config(run_dir)`
**Downstream**: returned dict is validated into `RunConfig` then passed to `execute_run`
**Contract**: dict must be JSON-serializable and pass `RunConfig.model_validate`
