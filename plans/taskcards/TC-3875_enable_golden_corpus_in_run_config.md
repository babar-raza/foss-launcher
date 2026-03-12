---
id: TC-3875
title: "Enable golden corpus by adding GoldenConfig to RunConfig and pilot configs"
status: In-Progress
priority: High
owner: "claude-agent"
updated: "2026-03-09"
tags: [golden, generate, quality, content-density]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3875_enable_golden_corpus_in_run_config.md
  - src/launcher/models/run_config.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - configs/pilots/aspose-cells-foss-python.yaml
  - configs/pilots/aspose-note-foss-python.yaml
  - tests/unit/models/test_run_config_golden.py
evidence_required:
  - reports/TC-3875/evidence.md
---

# Taskcard TC-3875 — Enable golden corpus by adding GoldenConfig to RunConfig and pilot configs

## Objective

The golden corpus (22 A-grade reference files in `golden/`) exists and is fully
indexed by `GoldenIndex`, but it is never used during generation or healing because
`RunConfig` has no `golden` field and `extra="ignore"` silently drops any `golden:`
YAML key. This means golden reference blocks are never injected into section prompts,
and `enforce_block_spec` is never called. Adding `GoldenConfig` to `RunConfig` and
enabling it in pilot configs activates a fully-implemented quality enforcement path.

## Required spec references

- `src/launcher/models/run_config.py` — RunConfig, existing Config models
- `src/launcher/workers/generate/worker.py` — uses `context.config.golden`
- `src/launcher/workers/generate/section_prompt.py` — uses `page.golden`
- `golden/` — 22 A-grade exemplar files

## Scope

### In scope
- Add `GoldenConfig` pydantic model (`enabled: bool`, `dir: str`) to `run_config.py`
- Add `golden: GoldenConfig` field to `RunConfig`
- Add `golden:` section to both pilot configs with `enabled: true` and `dir: "golden/"`
- Add unit tests for `GoldenConfig` defaults and model validation

### Out of scope
- No changes to `GoldenIndex`, `golden_loader.py`, or generate worker logic (already correct)
- No changes to section_prompt.py or heal.py (already reference `page.golden`/`config.golden`)
- No new golden files

## Inputs

- `src/launcher/models/run_config.py` (current state — no `golden` field)
- `configs/pilots/aspose-cells-foss-python.yaml`
- `configs/pilots/aspose-note-foss-python.yaml`

## Outputs

- `src/launcher/models/run_config.py` with `GoldenConfig` and `RunConfig.golden` field
- Both pilot configs with `golden: enabled: true, dir: "golden/"`
- `tests/unit/models/test_run_config_golden.py` — validation tests

## Allowed paths

- `src/launcher/models/run_config.py`
- `configs/pilots/aspose-cells-foss-python.yaml`
- `configs/pilots/aspose-note-foss-python.yaml`
- `tests/unit/models/test_run_config_golden.py`

### Allowed paths rationale
Minimal scope: model definition, two pilot configs, tests.

## Implementation steps

### Step 1: Add GoldenConfig to run_config.py

After `SkillsConfig`, add:
```python
class GoldenConfig(LauncherBaseModel):
    """Golden reference corpus configuration."""
    enabled: bool = False
    dir: str = "golden/"
```

Add to `RunConfig`:
```python
golden: GoldenConfig = Field(default_factory=GoldenConfig)
```

### Step 2: Enable in pilot configs

Add to both pilot YAMLs:
```yaml
golden:
  enabled: true
  dir: "golden/"
```

### Step 3: Write unit tests

Test: default disabled, enabled from YAML, dir override, model_validate round-trip.

## Failure modes

### Failure mode 1: golden/ dir doesn't exist at run time
**Detection**: `GoldenIndex.load(path)` returns empty index (already handles missing dir gracefully)
**Resolution**: Graceful degradation — golden_index.get() returns None, no block injected
**Gate**: generate worker already guards: `if golden_index is not None`

### Failure mode 2: golden dir path resolution (relative vs absolute)
**Detection**: generate worker uses `Path(golden_cfg.get("dir", "golden/"))` — relative to CWD
**Resolution**: Pilot runs from project root; `golden/` resolves correctly. Log if missing.
**Gate**: GoldenIndex.load returns empty index (not error) when dir absent

### Failure mode 3: extra="ignore" already drops golden from parsed RunConfig
**Detection**: `context.config.golden` is `GoldenConfig(enabled=False)` even with YAML `golden: enabled: true`
**Resolution**: Adding the field to RunConfig BEFORE `extra="ignore"` is processed means it IS parsed; extra="ignore" only drops unknown fields
**Gate**: Unit test validates `RunConfig.model_validate({"golden": {"enabled": true}}).golden.enabled == True`

## Task-specific review checklist

1. [ ] `GoldenConfig` model added with `enabled: bool = False` and `dir: str = "golden/"`
2. [ ] `RunConfig.golden` field defaults to `GoldenConfig()` (disabled by default)
3. [ ] `RunConfig.model_validate({"golden": {"enabled": true}}).golden.enabled` is `True`
4. [ ] Both pilot configs have `golden: enabled: true` and `dir: "golden/"`
5. [ ] `getattr(context.config, "golden", {})` now returns `GoldenConfig` (not dict) — verify generate worker handles both dict and model
6. [ ] Unit tests pass for all cases
7. [ ] Full test suite passes (no regressions)

## Deliverables

1. Modified `src/launcher/models/run_config.py`
2. Modified `configs/pilots/aspose-cells-foss-python.yaml`
3. Modified `configs/pilots/aspose-note-foss-python.yaml`
4. New `tests/unit/models/test_run_config_golden.py`

## Acceptance checks

1. [ ] `GoldenConfig` model exists in `run_config.py`
2. [ ] Both pilot configs have `golden: enabled: true`
3. [ ] Unit tests pass (PYTHONHASHSEED=0)
4. [ ] Full suite passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3875/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/test_run_config_golden.py -v
```

**Expected results**:
- All tests pass
- `RunConfig` loads `golden: enabled: true` correctly from pilot YAML

## Integration boundary proven

**Upstream**: pilot YAML `golden: enabled: true` → `RunConfig.golden.enabled = True`
**Downstream**: `context.config.golden` → generate worker → `GoldenIndex.load(dir)` → section prompts get golden reference blocks
**Contract**: `GoldenConfig.enabled` bool controls whether golden enforcement path runs
