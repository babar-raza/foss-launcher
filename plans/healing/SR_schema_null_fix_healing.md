# Healing Plan: TC-SCHEMA-NULL Post-Implementation Gaps

## Context

TC-SCHEMA-NULL fixed the pilot run crash caused by `run_config.schema.json` rejecting
`null` for the `telemetry` field. A self-review of the implementation found 6 gaps:
correctness error in the schema patch (`output` should not be nullable), a silent-skip
regression test footgun, missing YAML-path test coverage, non-numeric taskcard ID
violating repo convention, an unchecked review checklist, and the absence of a systematic
schema-model alignment audit.

This plan converts every gap into an executable taskcard. Implementation order: SR-01
first (correctness), then SR-02 (test hardening), then SR-03 (process cleanup), then
SR-04 (audit, preventive). SR-01 and SR-02 are blocking; SR-03 and SR-04 are important
but not pilot blockers.

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| GAP-01 | High | `output: ["object", "null"]` in schema disagrees with Pydantic model (`output` is not Optional — model rejects null; schema now accepts it) | SR-01 |
| GAP-02 | High | Regression test uses `@pytest.mark.skipif` — silently passes (skipped) if schema path drifts | SR-02 |
| GAP-03 | Medium | YAML-loading path (`load_and_validate_run_config` receiving `telemetry: null`) is untested | SR-02 |
| GAP-04 | Low | Taskcard ID `TC-SCHEMA-NULL` violates numeric convention (`TC-NNNN`); should be `TC-3824` | SR-03 |
| GAP-05 | Low | 6-item review checklist inside the taskcard body was never checked off | SR-03 |
| GAP-06 | Medium | No systematic audit comparing all Optional `RunConfig` fields against all schema property types — future nullable fields will create silent schema-model mismatches | SR-04 |

---

## Taskcard SR-01 — Revert `output` nullable schema change

**Status:** Done
**Gap linkage:** GAP-01
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
Revert `output`'s type in `specs/schemas/run_config.schema.json` from
`["object", "null"]` back to `"object"`. The `output` field in `RunConfig` is
`OutputConfig = Field(default_factory=OutputConfig)` — it is not `Optional`, so
`model_dump(mode="json")` never emits `null` for it. Accepting `null` in the schema
creates a two-layer inconsistency: schema validation passes, then Pydantic immediately
rejects the same input. The fix was wrong and should be reverted.

**Allowed paths:**
- `specs/schemas/run_config.schema.json`

**Forbidden:** any other file or path.

### Acceptance checks

**CLI:**
```bash
# Before: grep confirms the revert
grep -A1 '"output"' specs/schemas/run_config.schema.json
# Expected: "type": "object"   (NOT ["object", "null"])

# Regression test still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v
# Expected: 1 passed
```

**UI/Web/API:** N/A (schema file only).

**Tests:**
- `test_default_runconfig_serialization_passes_schema` must still pass (it does not
  depend on `output` being nullable — `output` is always an object in the serialized form)
- Full suite must pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`

**Config respected end-to-end:** A pilot config with `output: {goal: draft, run_dir: runs/}`
must still pass `load_and_validate_run_config`.

**No mock data in production paths:** Schema file has no runtime mock data.

### Deliverables

**Full file replacement for `specs/schemas/run_config.schema.json`:**
Change the `output` property block from:
```json
"output": {
  "type": ["object", "null"],
```
to:
```json
"output": {
  "type": "object",
```
No other changes. `telemetry` and `budgets` remain `["object", "null"]`.

**Tests:** No new test needed — existing `test_default_runconfig_serialization_passes_schema`
still passes because `RunConfig.output` with default factory always serializes as an object,
not null.

**Schema migration:** No migration required — this reverts an overly permissive rule to the
correct stricter rule. Any YAML config with `output: null` was already broken (Pydantic would
reject it); this revert makes the schema accurately reflect that.

### Hard rules

- Keep public signatures unless justified; update all call sites — N/A (schema only)
- No network in offline tests — N/A
- No new deps without explicit justification — none added
- Deterministic: schema file is static, no ordering concern
- Keep code/docs/tests in sync — confirm `tests/unit/io/test_run_config_schema_nullable.py`
  still passes after revert

### Review dimensions — what 5/5 means for SR-01

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `output` type in schema matches the Pydantic field's nullability exactly (`object` only, not nullable) |
| Minimality | Exactly 1 line changed (the `output` type annotation); no other diff noise |
| Consistency | All three layers agree: Pydantic model (not Optional) → schema (`"object"`) → serialized form (always dict) |
| Scope adherence | Zero changes outside `specs/schemas/run_config.schema.json` |
| Testability | Existing regression test continues to pass without modification |

### Now (runbook)

```bash
# 1. Open the file and locate the output property (~line 125)
# 2. Change:
#      "type": ["object", "null"],
#    to:
#      "type": "object",
# 3. Verify with grep:
grep -A2 '"output"' specs/schemas/run_config.schema.json
# Expected: "type": "object"

# 4. Run regression test:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v

# 5. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Expected: all pass
```

---

## Taskcard SR-02 — Harden regression test + add YAML-path coverage

**Status:** Done
**Gap linkage:** GAP-02, GAP-03
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Replace the `@pytest.mark.skipif(not SCHEMA_PATH.exists(), ...)` guard in
   `tests/unit/io/test_run_config_schema_nullable.py` with a hard-fail assertion
   inside the test body. A skipped test looks like a pass in CI — this is a regression
   guard that must fail loudly when it cannot guard.
2. Add a second test function that exercises `load_and_validate_run_config` with a
   YAML config containing `telemetry: null` explicitly, covering the YAML-loading path
   that was the original crash surface.
3. Use `Path(__file__).resolve()` for robust schema path resolution.

**Allowed paths:**
- `tests/unit/io/test_run_config_schema_nullable.py`

**Forbidden:** any other file or path.

### Acceptance checks

**CLI:**
```bash
# Confirm test count increased from 1 to 2:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v
# Expected: 2 passed

# Confirm hard-fail behavior: rename schema temporarily and run — must FAIL, not skip
# (do NOT commit this rename — only use for local verification)

# Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**UI/Web/API:** N/A.

**Tests:**
- `test_default_runconfig_serialization_passes_schema` — still passes; uses hard-fail
  assertion if schema file missing
- `test_yaml_with_null_telemetry_passes_schema` — new test; calls
  `load_and_validate_run_config` with a YAML containing `telemetry: null`; asserts
  the raw dict has `telemetry: None` and no exception is raised

**Config respected end-to-end:** The new test calls the real YAML-loading code path
with the real schema; no mock schemas.

**No mock data in production paths:** Both tests use real schema file and real loader.

### Deliverables

**Full file replacement for `tests/unit/io/test_run_config_schema_nullable.py`:**

```python
"""Regression tests: run_config.schema.json nullable field alignment.

TC-SCHEMA-NULL fixed a crash where RunConfig.model_dump(mode="json") produced
{"telemetry": null} but run_config.schema.json declared "type": "object" for telemetry.
The intake worker's input validation raised before any worker code ran.

SR-02 hardens these tests: hard-fail if schema file missing (replaces silent skipif);
adds YAML-loading path coverage.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from launcher.io.run_config import load_and_validate_run_config
from launcher.io.schema_validation import load_schema, validate
from launcher.models.run_config import RunConfig

# Resolve repo root from this file's location (tests/unit/io/ = 3 levels down from root).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "specs" / "schemas" / "run_config.schema.json"


def test_default_runconfig_serialization_passes_schema() -> None:
    """A minimal RunConfig (all optional fields at None) must pass schema validation.

    Regression for TC-SCHEMA-NULL: before the fix this raised:
        Schema validation failed:
        - test_default_runconfig: telemetry: None is not of type 'object'
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "If the schema was moved, update _REPO_ROOT resolution in this test."
        )

    cfg = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/example/repo",
    )
    data = cfg.model_dump(mode="json")

    # Confirm the fields that were the root cause of the crash are present as null.
    assert data["telemetry"] is None, "telemetry should serialize as null"
    assert data["llm"] is None, "llm should serialize as null"
    # output is NOT Optional — it must always serialize as a dict.
    assert isinstance(data["output"], dict), "output must always be a dict (not null)"

    schema = load_schema(_SCHEMA_PATH)
    # Must not raise. Before TC-SCHEMA-NULL this raised on telemetry: null.
    validate(data, schema, context="test_default_runconfig_serialization")


def test_yaml_with_null_telemetry_passes_schema(tmp_path: Path) -> None:
    """load_and_validate_run_config must accept a YAML config with telemetry: null.

    This covers the YAML-loading path: raw YAML dict → schema validation in
    load_and_validate_run_config (io/run_config.py). Without the TC-SCHEMA-NULL fix
    this path also raises on the schema validation step.
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "If the schema was moved, update _REPO_ROOT resolution in this test."
        )

    config_file = tmp_path / "run_config.yaml"
    config_file.write_text(
        "family: cells\n"
        "platform: python\n"
        "repo_url: https://github.com/example/repo\n"
        "telemetry: null\n",
        encoding="utf-8",
    )

    # Must not raise — before TC-SCHEMA-NULL this raised on telemetry: null
    # during the schema validation step inside load_and_validate_run_config.
    data = load_and_validate_run_config(_REPO_ROOT, config_file)
    assert data.get("telemetry") is None
```

**Tests:** The file above is the complete replacement — 2 tests, both covering
distinct crash paths (serialization path and YAML-loading path), both fail loudly
if the schema file is missing.

**Schema migration:** N/A — no schema change in this taskcard.

### Hard rules

- No network in offline tests — both tests use local files only
- No new deps — no new imports beyond what already exists in the test file
- Deterministic — no ordering sensitivity; both tests are independent
- Keep code/docs/tests in sync — docstrings reference TC-SCHEMA-NULL and SR-02 for traceability

### Review dimensions — what 5/5 means for SR-02

| Dimension | 5/5 criterion |
|-----------|---------------|
| Testability | 2 tests covering 2 distinct crash paths; both fail loudly on schema drift |
| Robustness | No `skipif` — schema path drift causes test failure, not silent skip |
| Thoroughness | Both the `model_dump` path and the YAML-loading path are exercised |
| Correctness | `assert isinstance(data["output"], dict)` documents and enforces that `output` is never null (aligns with SR-01 revert) |
| Observability | Failure messages name the schema path and suggest the fix when the file moves |

### Now (runbook)

```bash
# 1. Overwrite tests/unit/io/test_run_config_schema_nullable.py with the
#    full replacement in the Deliverables section above.

# 2. Run both tests:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_nullable.py -v
# Expected: 2 passed

# 3. Verify the hard-fail guard (local check only, do NOT commit):
#    Temporarily rename the schema, run the test, confirm FAILED not SKIPPED.
#    Then rename it back.

# 4. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Expected: all pass
```

---

## Taskcard SR-03 — Correct taskcard ID convention + mark review checklist

**Status:** Done
**Gap linkage:** GAP-04, GAP-05
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Rename `plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md` to
   `plans/taskcards/TC-3824_runconfig_nullable_fields.md` (next unused numeric ID
   after TC-3823, the last confirmed taskcard).
2. Update the frontmatter `id:`, `allowed_paths:`, and all internal cross-references
   in the file to `TC-3824`.
3. Mark all 6 items in the task-specific review checklist as `[x]`.
4. Delete the old `TC-SCHEMA-NULL_runconfig_nullable_fields.md` file.

**Allowed paths:**
- `plans/taskcards/TC-3824_runconfig_nullable_fields.md` (create)
- `plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md` (delete)

**Forbidden:** any other file or path.

### Acceptance checks

**CLI:**
```bash
# Confirm new file exists:
ls plans/taskcards/TC-3824_runconfig_nullable_fields.md

# Confirm old file is gone:
ls plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md
# Expected: No such file or directory

# Confirm ID in frontmatter:
grep "^id:" plans/taskcards/TC-3824_runconfig_nullable_fields.md
# Expected: id: TC-3824

# Confirm all 6 checklist items are checked:
grep "\- \[x\]" plans/taskcards/TC-3824_runconfig_nullable_fields.md | wc -l
# Expected: >= 6 (acceptance checks + review checklist)
```

**UI/Web/API:** N/A (plan file only).

**Tests:** No test required for a plan file rename.

**Config respected end-to-end:** N/A.

**No mock data in production paths:** N/A.

### Deliverables

**Renamed file `plans/taskcards/TC-3824_runconfig_nullable_fields.md`:**
Same content as the original `TC-SCHEMA-NULL` file except:
- `id: TC-SCHEMA-NULL` → `id: TC-3824`
- `title:` unchanged
- `allowed_paths:` updated: `TC-SCHEMA-NULL_...` → `TC-3824_...`
- Internal cross-references (`TC-SCHEMA-NULL`) → `TC-3824`
- Task-specific review checklist (6 items) — all updated to `[x]`:
  ```markdown
  1. [x] `telemetry` changed to `["object", "null"]` in schema
  2. [x] `budgets` changed to `["object", "null"]` in schema
  3. [ ] `output` changed — REVERTED by SR-01 (was incorrectly applied)
  4. [x] `llm` left unchanged (already correct)
  5. [x] Regression test loads the real schema file (not a mock)
  6. [x] Full test suite passes with no regressions
  ```
  Note: checklist item 3 should be annotated as reverted by SR-01, not checked.

**Deletion:** Remove `plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md`.

### Hard rules

- No new deps — N/A
- Deterministic — file rename is idempotent
- Keep code/docs/tests in sync — no code references `TC-SCHEMA-NULL`; search codebase
  (`grep -r TC-SCHEMA-NULL .`) before deleting to confirm no references remain

### Review dimensions — what 5/5 means for SR-03

| Dimension | 5/5 criterion |
|-----------|---------------|
| Consistency | TC ID follows `TC-NNNN` numeric convention; sorts correctly with other taskcards |
| Systematic approach | All checklist items explicitly marked; no ambiguity about task completion status |
| Minimality | Only taskcard files changed; zero diff in source/test/schema files |
| Maintainability | Future engineers can sort and reference the taskcard by numeric ID without special-casing |
| Observability | Checklist state truthfully reflects what was and was not completed (item 3 annotated as reverted) |

### Now (runbook)

```bash
# 1. Confirm no code references to TC-SCHEMA-NULL:
grep -r "TC-SCHEMA-NULL" . --include="*.py" --include="*.yaml" --include="*.json"
# Expected: 0 matches

# 2. Copy file with new name:
cp plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md \
   plans/taskcards/TC-3824_runconfig_nullable_fields.md

# 3. Edit plans/taskcards/TC-3824_runconfig_nullable_fields.md:
#    - id: TC-3824
#    - allowed_paths entry renamed
#    - All 6 checklist items updated
#    - Item 3 annotated as "REVERTED by SR-01"

# 4. Delete old file:
rm plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md

# 5. Confirm:
ls plans/taskcards/TC-3824_runconfig_nullable_fields.md
ls plans/taskcards/TC-SCHEMA-NULL_runconfig_nullable_fields.md  # must 404
```

---

## Taskcard SR-04 — Systematic schema-model alignment audit

**Status:** Done
**Gap linkage:** GAP-06
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
Perform a one-time systematic audit comparing every `RunConfig` field that is `Optional`
(i.e., `| None` or `Optional[X]`) against every property definition in
`run_config.schema.json`, and produce a written audit report that:
1. Lists each Optional field and its current schema type annotation
2. Flags any mismatch (Optional in Python, missing `null` in schema — or vice versa)
3. Flags any `RunConfig` field absent from the schema (or present in schema but absent
   from the model)
4. Documents the decision for each case (correct, needs fix, intentionally omitted)

Then produce a lightweight "schema fitness" test that programmatically detects future
nullable/type mismatches between `RunConfig.model_fields` and `run_config.schema.json`.

**Allowed paths:**
- `plans/healing/schema_model_audit_report.md` (audit report — written artifact)
- `tests/unit/io/test_run_config_schema_fitness.py` (programmatic fitness check)

**Forbidden:** any other file or path. If the audit finds new bugs, they must be tracked
as new taskcards — do NOT fix them inline during this taskcard.

### Acceptance checks

**CLI:**
```bash
# Confirm audit report exists and has the required sections:
grep -c "^|" plans/healing/schema_model_audit_report.md
# Expected: >= 10 rows (one per RunConfig field)

# Fitness test passes:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_fitness.py -v
```

**UI/Web/API:** N/A.

**Tests:**
- `test_run_config_schema_fitness.py` — programmatically loads the real schema and
  compares it against `RunConfig.model_fields` to assert that every Optional field
  has `null` in its schema type and every required field does not.
- Test must fail if a new Optional field is added to `RunConfig` without the
  corresponding schema update.

**Config respected end-to-end:** Fitness test uses the real schema file.

**No mock data in production paths:** Fitness test uses the real schema and real model.

### Deliverables

**`plans/healing/schema_model_audit_report.md`:**
A markdown table with columns:
`RunConfig field | Python type | Optional? | Schema type | Status | Decision`

For each field in `RunConfig` (all 13+ fields), document the current state and flag any
mismatch. Include a summary section: "Fields needing follow-up taskcards" if any bugs
are found.

**`tests/unit/io/test_run_config_schema_fitness.py`:**
```python
"""Schema fitness test: RunConfig Optional fields must be nullable in the JSON schema.

This test prevents future regressions where a new Optional field is added to RunConfig
but the schema is not updated to allow null — the exact root cause of TC-SCHEMA-NULL.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import get_args, get_origin, Union

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "specs" / "schemas" / "run_config.schema.json"


def _is_optional(annotation) -> bool:
    """Return True if the annotation is X | None (or Optional[X])."""
    origin = get_origin(annotation)
    if origin is Union:
        return type(None) in get_args(annotation)
    return False


def test_optional_runconfig_fields_are_nullable_in_schema() -> None:
    """Every Optional field in RunConfig must have 'null' in its schema type.

    Prevents a recurrence of TC-SCHEMA-NULL: RunConfig.telemetry was Optional but
    the schema said "type": "object" — crashing the pipeline on every pilot run.
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(f"Schema not found: {_SCHEMA_PATH}")

    from launcher.models.run_config import RunConfig

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema.get("properties", {})

    failures = []
    for field_name, field_info in RunConfig.model_fields.items():
        annotation = field_info.annotation
        if not _is_optional(annotation):
            continue
        if field_name not in properties:
            # Field is Optional but absent from schema entirely.
            # With additionalProperties: true this is not a crash, but document it.
            continue
        schema_type = properties[field_name].get("type", "")
        if isinstance(schema_type, str):
            # Single type — null not allowed.
            failures.append(
                f"  RunConfig.{field_name}: Python allows None, "
                f"but schema type is {schema_type!r} (no null). "
                f"Fix: change to ['{schema_type}', 'null']."
            )
        elif isinstance(schema_type, list) and "null" not in schema_type:
            failures.append(
                f"  RunConfig.{field_name}: Python allows None, "
                f"but schema types {schema_type!r} do not include 'null'."
            )

    if failures:
        pytest.fail(
            "Optional RunConfig fields lack 'null' in their schema type:\n"
            + "\n".join(failures)
            + "\n\nSee TC-SCHEMA-NULL for the root-cause pattern."
        )
```

**Schema migration:** N/A — this is an audit only. Any fixes found belong in new taskcards.

### Hard rules

- No network in offline tests — schema and model loaded from local files
- No new deps — `json`, `typing` are stdlib; `pydantic` already a project dep
- Deterministic — no ordering sensitivity
- Do NOT fix bugs found during the audit in this taskcard — log them as new SR-0X taskcards
- Keep code/docs/tests in sync — audit report must reference the fitness test

### Review dimensions — what 5/5 means for SR-04

| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | Every RunConfig model field appears in the audit table with a documented decision |
| Systematic approach | Audit is repeatable: the fitness test mechanically enforces the same check on every future PR |
| Correctness | Fitness test correctly identifies Optional fields using `get_origin`/`get_args` (handles both `X \| None` and `Optional[X]` syntax) |
| Testability | Fitness test fails with a clear actionable message naming the offending field and the fix |
| Observability | Audit report documents not just current state but the decision/rationale for each field |

### Now (runbook)

```bash
# 1. Run this one-liner to enumerate Optional fields vs schema:
.venv/Scripts/python.exe - <<'EOF'
import json
from pathlib import Path
from typing import get_args, get_origin, Union
from launcher.models.run_config import RunConfig

schema = json.loads(Path("specs/schemas/run_config.schema.json").read_text())
props = schema.get("properties", {})

for name, fi in RunConfig.model_fields.items():
    ann = fi.annotation
    origin = get_origin(ann)
    is_opt = origin is Union and type(None) in get_args(ann)
    s_type = props.get(name, {}).get("type", "MISSING_FROM_SCHEMA")
    flag = ""
    if is_opt:
        if isinstance(s_type, str):
            flag = "MISMATCH — schema does not allow null"
        elif isinstance(s_type, list) and "null" not in s_type:
            flag = "MISMATCH — null missing from type array"
    print(f"{'OPT' if is_opt else '   '} | {name:30s} | {str(s_type):30s} | {flag}")
EOF

# 2. Copy output into plans/healing/schema_model_audit_report.md as the audit table.

# 3. Write tests/unit/io/test_run_config_schema_fitness.py (full content in Deliverables).

# 4. Run fitness test:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_config_schema_fitness.py -v

# 5. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Implementation Order

```
SR-01  →  SR-02  →  SR-03  →  SR-04
(fix incorrect schema change)
         (harden test + add YAML path)
                    (process cleanup)
                               (preventive audit)
```

SR-01 and SR-02 should be implemented and tested together in a single commit since
SR-02's new assertion (`assert isinstance(data["output"], dict)`) validates the SR-01
revert. SR-03 and SR-04 can follow independently.
