---
id: TC-1302
title: "Mandatory Pipeline Enforcement — Remove W7 Passthrough and review_enabled Flag"
status: Draft
priority: High
owner: "Agent D (Docs & Specs)"
updated: "2026-02-11"
tags: ["w5.5", "orchestrator", "schema", "config", "pipeline-hardening", "mandatory"]
depends_on: ["TC-1301"]
allowed_paths:
  - plans/taskcards/TC-1302_mandatory_pipeline_enforcement.md
  - src/launch/orchestrator/graph.py
  - specs/schemas/run_config.schema.json
  - specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
  - specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
  - specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
  - configs/pilots/pilot-aspose-3d-foss-python.yaml
  - configs/pilots/pilot-aspose-note-foss-python.yaml
  - configs/pilots/pilot-aspose-cells-foss-python.yaml
  - tests/unit/orchestrator/test_tc_300_graph.py
  - tests/integration/test_tc_300_run_loop.py
evidence_required:
  - reports/agents/AGENT_D/TC-1302/evidence.md
  - reports/agents/AGENT_D/TC-1302/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1302 — Mandatory Pipeline Enforcement

## Objective
Make W7 ContentReviewer a mandatory, non-skippable pipeline stage. Remove the `review_enabled` config flag and the passthrough early-return in the orchestrator. After this change, every pipeline run executes W7 checks + auto-fixes (and LLM agents when available per TC-1301).

### Why this matters
The `review_enabled` flag was originally added as a safety valve during W7 development. Now that W7 is stable (both pilots PASS with scores 4-5), keeping it optional creates risk: new pilots or configuration drift could silently skip quality review, shipping low-quality content without detection.

## Required spec references
- src/launch/orchestrator/graph.py (current passthrough at `review_content_node()`)
- specs/schemas/run_config.schema.json (current `review_enabled` property)
- specs/pilots/*/run_config.pinned.yaml (pilot configs with `review_enabled: true`)
- configs/pilots/*.yaml (runtime pilot configs)

## Scope

### In scope
1. **Remove passthrough in graph.py** — Delete the `if not run_config.get("review_enabled", True)` early return from `review_content_node()`
2. **Deprecate `review_enabled` in schema** — Mark as deprecated with `"const": true` and deprecation description (backward compat — field may exist but must be `true`)
3. **Clean up pilot configs** — Remove explicit `review_enabled: true` from all pilot YAML files (no longer needed; always-on)
4. **Remove `review_enabled` check in llm_regen.py** — This check is in `spawn_enhancement_agents()` (TC-1301 may or may not have removed it; verify at execution time)
5. **Update tests** — Any tests that use `review_enabled=False` to skip W7 must be updated

### Out of scope
- Modifying W7 worker logic (that's TC-1301)
- Modifying check modules or scoring
- Removing the `review_enabled` field entirely from schema (keeping for backward compat)
- Modifying LLM client code (`src/launch/clients/**`)

## Inputs
- Current `graph.py` (passthrough logic to remove)
- Current `run_config.schema.json` (property to deprecate)
- All pilot YAML configs (lines to clean up)

## Outputs
- `graph.py` (UPDATED — passthrough removed, ~8 lines deleted)
- `run_config.schema.json` (UPDATED — `review_enabled` deprecated with `const: true`)
- All 6 pilot config YAMLs (UPDATED — `review_enabled` lines removed)
- `test_tc_300_graph.py` (UPDATED — tests adapted)
- `test_tc_300_run_loop.py` (UPDATED — if references `review_enabled`)
- Evidence bundle

## Allowed paths
- plans/taskcards/TC-1302_mandatory_pipeline_enforcement.md
- src/launch/orchestrator/graph.py
- specs/schemas/run_config.schema.json
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
- specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
- specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
- configs/pilots/pilot-aspose-3d-foss-python.yaml
- configs/pilots/pilot-aspose-note-foss-python.yaml
- configs/pilots/pilot-aspose-cells-foss-python.yaml
- tests/unit/orchestrator/test_tc_300_graph.py
- tests/integration/test_tc_300_run_loop.py

### Allowed paths rationale
Orchestrator graph is the enforcement point. Schema and configs are where the flag lives. Tests must be updated to not rely on the removed passthrough. No worker code changes (done in TC-1301).

## Implementation steps

### Step 1: Read current state of all target files
Read `graph.py`, `run_config.schema.json`, all pilot YAMLs, and test files. Identify:
- The exact passthrough block in `review_content_node()` (search for `"review_content_skipped"` or `"review_enabled"`)
- The `review_enabled` property in the schema (search for `"review_enabled"`)
- Any `review_enabled` lines in pilot configs
- Any test cases that set `review_enabled=False`

**Resilience note**: Use string search, not line numbers. If TC-1301 already removed the `review_enabled` check from `llm_regen.py`, skip that change. If the passthrough was already removed by another taskcard, verify and document.

### Step 2: Remove passthrough from graph.py
Find and delete the block:
```python
if not run_config.get("review_enabled", True):
    logger.info(
        "review_content_skipped",
        run_id=state["run_id"],
        reason="review_enabled is False",
    )
    return state
```

The function should now unconditionally proceed to invoke W7.

**Resilience note**: If the function has other early-returns (e.g., missing artifacts), leave those intact. Only remove the `review_enabled` check.

### Step 3: Deprecate `review_enabled` in schema
In `run_config.schema.json`, find the `"review_enabled"` property and change it to:

```json
"review_enabled": {
    "type": "boolean",
    "const": true,
    "deprecated": true,
    "description": "DEPRECATED (TC-1302): W7 ContentReviewer is now mandatory. This field is ignored. Kept for backward compatibility — existing configs with 'review_enabled: true' remain valid."
}
```

**Resilience note**: If `"const"` is not supported by the project's JSON Schema draft, use `"enum": [true]` instead. Check existing schema for the draft version used.

### Step 4: Remove `review_enabled` from pilot configs
For each of the 6 config files (3 in `specs/pilots/`, 3 in `configs/pilots/`):
- Find and remove any line containing `review_enabled:`
- If the line is the only line in a section, remove the section header too (if empty)

**Resilience note**: Some configs may not have the field (it was optional). Skip files where the field doesn't exist. Do NOT add the field just to remove it.

### Step 5: Remove `review_enabled` check from llm_regen.py (if still present)
Search `llm_regen.py` for `review_enabled`. If TC-1301 left the check in place, remove:
```python
if not run_config.get("review_enabled", True):
    return [{"agent_type": "all", "status": "skipped", ...}]
```

If TC-1301 already removed it, skip this step.

### Step 6: Update tests
Search test files for `review_enabled`:

**In `test_tc_300_graph.py`**: If there's a test like `test_review_skipped_when_disabled`, either:
- Remove the test entirely (the behavior no longer exists), OR
- Convert it to test that W7 always runs regardless of config flag

**In `test_tc_300_run_loop.py`**: If integration tests use `review_enabled=False` to speed up runs, they now need W7 mocked or a minimal drafts directory. Update accordingly.

**Resilience note**: Do NOT break tests that test other orchestrator behavior. Only change assertions related to `review_enabled`.

### Step 7: Run orchestrator + W7 tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ tests/integration/test_tc_300_run_loop.py tests/unit/workers/w7_content_reviewer/ -v
```

## Failure modes

### Failure mode 1: Existing configs with `review_enabled: false` fail schema validation
**Detection**: Schema validation rejects configs with `review_enabled: false` (because of `const: true`).
**Resolution**: Use `"deprecated": true` description to warn, but do NOT add `const: true` if any known configs use `false`. Check all configs first. If all configs say `true` or omit the field, `const: true` is safe.
**Spec/Gate**: specs/schemas/run_config.schema.json validation

### Failure mode 2: Integration tests timeout with mandatory W7
**Detection**: Tests that previously skipped W7 now run it, taking longer or failing.
**Resolution**: Mock W7 in integration tests that are not testing review behavior. Or provide minimal valid drafts so W7 passes quickly.
**Spec/Gate**: tests/integration/ timeout constraints

### Failure mode 3: TC-1301 not yet implemented when TC-1302 executes
**Detection**: W7 is now mandatory but LLM agents are still stubs.
**Resolution**: This is acceptable. W7 with stubs still runs checks + auto-fixes + scoring. The stubs just return "skipped". No degradation vs making it mandatory. TC-1302 depends on TC-1301 for ordering but is not blocked by it.
**Spec/Gate**: Taskcard contract — depends_on ordering

## Task-specific review checklist
1. [ ] Passthrough `if not review_enabled` block deleted from `graph.py`
2. [ ] `review_enabled` marked as deprecated in schema with `const: true`
3. [ ] All 6 pilot config files cleaned up (no `review_enabled` lines)
4. [ ] `llm_regen.py` no longer checks `review_enabled` (if it did before)
5. [ ] Tests updated — no test relies on `review_enabled=False` passthrough
6. [ ] No other early-returns in `review_content_node()` were accidentally removed
7. [ ] Schema backward compatible (existing valid configs still validate)
8. [ ] Orchestrator tests pass
9. [ ] Integration tests pass (or mocked for W7)
10. [ ] W7 test suite passes (no regressions)

## Deliverables
- src/launch/orchestrator/graph.py (UPDATED)
- specs/schemas/run_config.schema.json (UPDATED)
- 6 pilot config YAMLs (UPDATED)
- tests/unit/orchestrator/test_tc_300_graph.py (UPDATED)
- tests/integration/test_tc_300_run_loop.py (UPDATED — if needed)
- reports/agents/AGENT_D/TC-1302/evidence.md
- reports/agents/AGENT_D/TC-1302/self_review.md

## Acceptance checks
1. [ ] `review_content_node()` has no `review_enabled` early return
2. [ ] Schema shows `review_enabled` as deprecated
3. [ ] Pipeline run with no `review_enabled` in config → W7 runs
4. [ ] Pipeline run with `review_enabled: true` in config → W7 runs (backward compat)
5. [ ] All orchestrator and W7 tests pass
6. [ ] No pilot config files contain `review_enabled`

## Preconditions / dependencies
- TC-1301 should be completed first (W7 agents implemented) so mandatory review has full capability
- However, TC-1302 is valid even with stubs — checks + auto-fixes still run

## Test plan
1. Orchestrator unit tests: verify `review_content_node()` always invokes W7
2. Schema validation: verify deprecated field handling
3. Integration: verify pipeline runs complete with W7 mandatory

## Self-review
[To be completed by Agent D after implementation]
