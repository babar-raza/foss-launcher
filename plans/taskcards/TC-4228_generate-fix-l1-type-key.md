---
id: TC-4228
title: "G-2: Fix L1 validator missing type key in generate LLM responses"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, l1-validator, type-key, response-format]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4228_generate-fix-l1-type-key.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-4228/evidence.md
---

# Taskcard TC-4228 — G-2: Fix L1 validator missing type key in generate LLM responses

## Objective

Tighten the output format instruction in `section_writer.txt` and add `type`-field coercion in the L1 validator before raising `FAIL_FINAL`. This eliminates `L1_VALIDATOR_FAIL_FINAL` events caused by LLM responses missing the `type` key in the expected JSON structure.

## Required spec references

- `specs/worker_generate.md` (Section: L1 validator, response format)
- `specs/schemas/` (Section: generate response schema)

## Scope

### In scope
- Strengthen `section_writer.txt` output format instruction to require `type` key explicitly
- Add type-field coercion/defaulting in the L1 validator logic in `worker.py`
- Unit tests covering missing-type-key response coercion

### Out of scope
- Changes to L2/L3 validators
- Changes to other LLM call sites

## Inputs

- `src/launcher/workers/generate/worker.py` — L1 validator implementation
- `src/launcher/prompts/section_writer.txt` — output format instruction

## Outputs

- Modified `worker.py` — type-field coercion before FAIL_FINAL
- Modified `section_writer.txt` — explicit type key requirement
- Updated tests in `tests/unit/workers/generate/`

## Allowed paths

- plans/taskcards/TC-4228_generate-fix-l1-type-key.md
- src/launcher/workers/generate/worker.py
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/

### Allowed paths rationale
Both the validator (worker.py) and the prompt (section_writer.txt) must be updated for full coverage: prompt reduces LLM failures, coercion handles remaining edge cases.

## Implementation steps

### Step 1: Read worker.py L1 validator and section_writer.txt

Understand the current L1 validation logic and what triggers FAIL_FINAL.

### Step 2: Add type-field coercion

In the L1 validator, before raising `L1_VALIDATOR_FAIL_FINAL`, attempt to coerce the response:
```python
if "type" not in response_dict:
    # Attempt coercion: infer type from content structure
    response_dict["type"] = _infer_type(response_dict)
    if response_dict["type"] is None:
        raise L1ValidatorError("missing type key and unable to infer")
```

### Step 3: Update section_writer.txt

Add explicit requirement in the output format section:
```
Your response MUST be valid JSON with the following keys:
- "type": (required) one of ["prose", "code", "mixed"]
- "content": (required) the generated section content
```

### Step 4: Write unit tests

Add tests covering:
1. Response missing `type` key — coercion succeeds with inferred type
2. Response missing `type` key and content ambiguous — FAIL_FINAL raised
3. Response with all keys present — passes L1 unchanged

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

## Failure modes

### Failure mode 1: Coercion infers wrong type

**Detection**: Section content type mismatch downstream (code section flagged as prose).
**Resolution**: Make `_infer_type` conservative — if unable to determine type with confidence, default to `"mixed"` rather than guessing.
**Gate**: Section structure evaluation gate

### Failure mode 2: Prompt change causes LLM to output type in wrong format

**Detection**: LLM outputs `"type": "Prose"` (capitalized) instead of `"prose"`.
**Resolution**: Add `.lower()` normalization in validator before coercion check.
**Gate**: Unit test with capitalized type value

### Failure mode 3: FAIL_FINAL still fires after coercion

**Detection**: `L1_VALIDATOR_FAIL_FINAL` events still in log after fix.
**Resolution**: Check if FAIL_FINAL is triggered by a different missing key. Expand coercion to cover all recoverable missing keys.
**Gate**: Log grep for `L1_VALIDATOR_FAIL_FINAL`

## Task-specific review checklist

1. [ ] L1 validator attempts type coercion before raising FAIL_FINAL
2. [ ] Coercion defaults to `"mixed"` when type cannot be inferred
3. [ ] section_writer.txt explicitly lists `type` as a required key
4. [ ] Type value normalized to lowercase before validation
5. [ ] Unit test: missing type — coercion succeeds
6. [ ] Unit test: missing type + ambiguous content — FAIL_FINAL raised
7. [ ] Docstrings updated for L1 validator function
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/generate/worker.py` — type coercion in L1 validator
2. `src/launcher/prompts/section_writer.txt` — explicit type key requirement
3. `tests/unit/workers/generate/` — 3 new test cases
4. `reports/TC-4228/evidence.md` — log output showing zero L1_VALIDATOR_FAIL_FINAL

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v`
2. [ ] L1 validator coerces missing type key — confirmed by test
3. [ ] Pilot run: zero `L1_VALIDATOR_FAIL_FINAL` events in log

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: L1_VALIDATOR_FAIL_FINAL count = 0 PASS
- [ ] Evidence captured: reports/TC-4228/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- Type coercion tests pass
- No regressions in existing generate tests

## Integration boundary proven

**Upstream**: LLM section writer — returns JSON response
**Downstream**: Section content pipeline — receives validated/coerced response
**Contract**: L1 validator never raises FAIL_FINAL for missing `type` key when content is present
