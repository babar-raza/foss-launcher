---
id: TC-HO-06
title: "Inject missing_info as DO NOT CLAIM guard in section prompt"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [generate, section_prompt, missing_info, hallucination_prevention, wave4b]
depends_on: [TC-4041]
allowed_paths:
  - plans/taskcards/TC-HO-06_missing-info-guard.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_tc_ho06_missing_info.py
  - reports/agents/wave4b/TC-HO-06/evidence.md
evidence_required:
  - reports/agents/wave4b/TC-HO-06/evidence.md
---

# Taskcard TC-HO-06 — Inject missing_info as DO NOT CLAIM guard

## Objective

Surface `product_evidence.missing_info` (MissingInfoEntry list) as a DO NOT CLAIM/INVENT
block near the top of the section prompt to prevent the LLM from fabricating install commands,
workflows, or capabilities that Understand explicitly recorded as unknowable.

## Required spec references

- `specs/worker_generate.md` (Section: hallucination prevention)
- `specs/worker_understand.md` (Section: MissingInfoEntry)

## Scope

### In scope
- Add `missing_info: list | None = None` to `build_section_prompt()`
- Add `_format_missing_info()` helper
- Prepend DO NOT CLAIM block to prompt when missing_info is non-empty

### Out of scope
- Changing MissingInfoEntry model
- Injecting into evaluate worker

## Inputs

- `understand.product_evidence.missing_info` — list[MissingInfoEntry]

## Outputs

- Modified `section_prompt.py`
- Modified `generate/worker.py`
- Test file

## Allowed paths

- plans/taskcards/TC-HO-06_missing-info-guard.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_tc_ho06_missing_info.py
- reports/agents/wave4b/TC-HO-06/evidence.md

### Allowed paths rationale

Prompt builder and worker call site only.

## Implementation steps

### Step 1: Add `_format_missing_info()` to section_prompt.py

Format each MissingInfoEntry as:
`DO NOT CLAIM OR INVENT: {field_name} (could not be extracted: {reason})`

Use `field` attribute for field_name, `reason` for reason.

### Step 2: Add `missing_info` parameter to `build_section_prompt()`

Prepend the DO NOT CLAIM block to the final result (before EVIDENCE CONSTRAINT and REFERENCE PREAMBLE prepends).

### Step 3: Extract and pass from worker.py

Extract `understand.product_evidence.missing_info`.

### Step 4: Write tests

- Non-empty missing_info → DO NOT CLAIM block appears
- None/[] → block absent

## Failure modes

### Failure mode 1: MissingInfoEntry lacks 'field' or 'reason' attributes

**Detection**: AttributeError at format time
**Resolution**: Use `getattr(entry, "field", "") or str(entry)` pattern; same for reason

### Failure mode 2: Block placement conflicts with EVIDENCE CONSTRAINT prepend

**Detection**: Double-prepended text in tests
**Resolution**: DO NOT CLAIM block is appended to `result` BEFORE the existing prepends,
so the order ends up: DO NOT CLAIM → EVIDENCE CONSTRAINT → (template content)

### Failure mode 3: Existing tests fail due to param change

**Detection**: pytest failures
**Resolution**: Parameter default is None; no change for callers that don't pass it

## Task-specific review checklist

1. [ ] `_format_missing_info()` handles missing attributes gracefully
2. [ ] Block is injected near the top of the prompt (before context block)
3. [ ] Only injected when missing_info is non-empty
4. [ ] Worker extracts from product_evidence.missing_info
5. [ ] Test: non-empty missing_info → DO NOT CLAIM text in prompt
6. [ ] Test: None → block absent
7. [ ] Docstrings updated
8. [ ] Spec confirmed — no drift
9. [ ] Schema N/A
10. [ ] docs/README.md checked — no update needed
11. [ ] No new docs/guides/ file

## Deliverables

1. Modified `section_prompt.py`
2. Modified `worker.py`
3. `tests/unit/workers/generate/test_tc_ho06_missing_info.py`
4. `reports/agents/wave4b/TC-HO-06/evidence.md`

## Acceptance checks

1. [ ] All new tests pass
2. [ ] No regressions in `tests/unit/workers/generate/`
3. [ ] DO NOT CLAIM block appears in prompt output when missing_info is populated

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/wave4b/TC-HO-06/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc_ho06_missing_info.py -v
```

**Expected results**:
- All tests pass

## Integration boundary proven

**Upstream**: `ProductEvidence.missing_info` (MissingInfoEntry list) from Understand worker
**Downstream**: LLM prompt — explicit "do not invent" instruction near top
**Contract**: MissingInfoEntry has `field` and `reason` string attributes
