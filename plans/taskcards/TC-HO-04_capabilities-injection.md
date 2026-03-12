---
id: TC-HO-04
title: "Inject product_evidence.capabilities into section prompt"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [generate, section_prompt, capabilities, wave4b]
depends_on: [TC-4041]
allowed_paths:
  - plans/taskcards/TC-HO-04_capabilities-injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/test_tc_ho04_capabilities.py
  - reports/agents/wave4b/TC-HO-04/evidence.md
evidence_required:
  - reports/agents/wave4b/TC-HO-04/evidence.md
---

# Taskcard TC-HO-04 — Inject product_evidence.capabilities

## Objective

Inject `product_evidence.capabilities` (list[dict] with text/source/evidence) into the
`build_section_prompt()` call so the LLM has explicit capability statements from
README/docstrings rather than inferring from claims alone.

## Required spec references

- `specs/worker_generate.md` (Section: prompt injection)
- `specs/worker_understand.md` (Section: ProductEvidence.capabilities)

## Scope

### In scope
- Add `capabilities: list[dict] | None = None` parameter to `build_section_prompt()`
- Add `_format_capabilities()` helper in `section_prompt.py`
- Append capabilities block to prompt when non-empty
- Pass `capabilities` from `generate/worker.py`

### Out of scope
- Changing ProductEvidence model
- Changing evaluate worker

## Inputs

- `understand.product_evidence.capabilities` — list[dict] from UnderstandingBundle
- Existing `build_section_prompt()` signature

## Outputs

- Modified `section_prompt.py` with new parameter + helper
- Modified `generate/worker.py` extracting capabilities from understanding bundle
- New test file `tests/unit/workers/generate/test_tc_ho04_capabilities.py`

## Allowed paths

- plans/taskcards/TC-HO-04_capabilities-injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_tc_ho04_capabilities.py
- reports/agents/wave4b/TC-HO-04/evidence.md

### Allowed paths rationale

Section prompt and worker are the only files affected. Tests validate new behaviour.

## Implementation steps

### Step 1: Add `_format_capabilities()` helper to section_prompt.py

Format up to 5 capability dicts as bullet lines. Each dict has keys: text, source, evidence.

### Step 2: Add `capabilities` parameter to `build_section_prompt()`

Append formatted block to `result` after the format-matrix block (TC-4041).

### Step 3: Extract and pass capabilities in worker.py

In `_process_page` / `_generate_page` call chain, extract from `understand.product_evidence.capabilities` and pass through.

### Step 4: Write tests

- Non-empty capabilities → PRODUCT CAPABILITIES block in prompt
- Empty / None → block absent

## Failure modes

### Failure mode 1: capabilities is list of dicts without 'text' key

**Detection**: KeyError in `_format_capabilities()` at format time
**Resolution**: Use `.get("text", "")` with fallback to str(cap)
**Gate**: Unit test covers missing keys

### Failure mode 2: capabilities injection breaks existing tests

**Detection**: `pytest tests/unit/workers/generate/` failures
**Resolution**: Ensure parameter is optional with default None; no change to existing callers

### Failure mode 3: Token budget bloat

**Detection**: Prompt length > 16000 chars in tests
**Resolution**: Cap at 5 entries max

## Task-specific review checklist

1. [ ] `_format_capabilities()` handles missing 'text' key gracefully
2. [ ] Parameter is `list[dict] | None = None` with no default change to existing callers
3. [ ] Block only appears when capabilities is non-empty
4. [ ] Worker extracts from `understand.product_evidence.capabilities` correctly
5. [ ] Test: non-empty caps → block present
6. [ ] Test: None or [] → block absent
7. [ ] Docstrings updated for new parameter
8. [ ] Spec file confirmed no drift
9. [ ] Schema description fields present for new properties (N/A — no schema change)
10. [ ] Checked docs/README.md — no new guide needed
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` with `_format_capabilities()` + parameter
2. `src/launcher/workers/generate/worker.py` with extraction pass-through
3. `tests/unit/workers/generate/test_tc_ho04_capabilities.py`
4. `reports/agents/wave4b/TC-HO-04/evidence.md`

## Acceptance checks

1. [ ] `pytest tests/unit/workers/generate/test_tc_ho04_capabilities.py -q` all pass
2. [ ] `pytest tests/unit/workers/generate/ -q` all pass (no regressions)
3. [ ] capabilities block appears in prompt when non-empty; absent when empty

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/wave4b/TC-HO-04/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc_ho04_capabilities.py -v
```

**Expected results**:
- All tests pass

## Integration boundary proven

**Upstream**: `UnderstandingBundle.product_evidence.capabilities` (already populated by Understand worker)
**Downstream**: LLM prompt text (injected for generation quality)
**Contract**: capabilities is `list[dict]` with at minimum a 'text' key per entry
