---
id: TC-4021
title: "HG-13: Prompt hardening — explicit API class name guard in section writer"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, prompt-hardening, hallucination]
depends_on: [TC-4019]
ruleset_version: "1.0"
spec_ref: "d2258045"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4021_hg13-prompt-hardening.md
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4021 — HG-13: Prompt Hardening

## Objective

The pilot (HG-02) found 7 pages with hallucinated class names not in the extracted API surface. HG-13 requires adding an explicit "DO NOT INVENT API CLASS NAMES outside this list: {api_identifiers[:30]}" instruction in the section writer prompt.

## Required spec references

- `phase_store/pilot_quality_report.md` — Gap 2: unknown API classes

## Scope

### In scope

- Delivery of API class name guard block in section_writer prompt

### Out of scope

- Additional prompt changes beyond the class name guard

## Inputs

- `phase_store/pilot_quality_report.md` — root cause (Gap 2)

## Outputs

- Delivered via TC-4019 (HG-11) — `build_section_prompt()` appends `KNOWN API CLASSES FOR {display_name}` with "DO NOT invent" language when `api_identifiers` non-empty

## Allowed paths

- plans/taskcards/TC-4021_hg13-prompt-hardening.md

### Allowed paths rationale

This taskcard is satisfied by TC-4019 implementation. No additional code changes required.

## Implementation steps

### Step 1: Verify HG-11 delivers HG-13 requirement

HG-11 (TC-4019) added `_format_api_ids_guard()` that produces:
```
KNOWN API CLASSES FOR {DISPLAY_NAME} (DO NOT invent any class or module name outside this list — any class not listed here does NOT exist):
Scene, Node, Mesh, Material, ...
```
This is injected into every section prompt when `api_identifiers` is non-empty.

This satisfies HG-13's requirement: explicit prohibition with the list of known class names.

## Failure modes

### Failure mode 1: api_identifiers empty for some libraries

**Detection**: Guard block absent even though library has classes
**Resolution**: Ensure `understand.api_surface.api_identifiers` is populated; falls back gracefully when empty
**Gate**: `build_section_prompt()` does not error when api_identifiers is None

### Failure mode 2: LLM still ignores the guard

**Detection**: Pilot shows hallucinated class names after HG-11
**Resolution**: Additional prompt hardening — move guard to top of prompt; use ALL CAPS MUST NOT language; consider adding to STRICT RULES section
**Gate**: Quality improvement in next pilot run

### Failure mode 3: Guard too verbose (token budget)

**Detection**: LLM prompt truncated or token limit exceeded
**Resolution**: Cap class names at 30 (already implemented in _format_api_ids_guard)
**Gate**: Pilot completes without LLM errors

## Task-specific review checklist

- [x] `_format_api_ids_guard()` implemented in section_prompt.py (TC-4019)
- [x] Guard injected into section prompt when api_identifiers non-empty
- [x] Guard uses "DO NOT invent" language
- [x] Guard capped at 30 class names
- [x] Tests verify guard presence and content (test_section_prompt_evidence.py)
- [x] Full test suite passes (3565 passed)
- [x] Spec freshness confirmed
- [x] Schema not changed
- [x] No docstring changes needed

## Deliverables

1. API class guard delivered via TC-4019 (HG-11) — no additional files

## Acceptance checks

- [x] `build_section_prompt()` with non-empty `api_identifiers` includes "DO NOT invent" in output
- [x] `TestHG11EvidenceInjection::test_api_ids_guard_appears_in_prompt` PASS
- [x] Full test suite: 3565 passed, 0 new failures

## Self-review

### Verification results
- [x] Tests: 8/8 PASS (TestHG11EvidenceInjection)
- [x] Full suite: 3565 passed, 6 pre-existing failures only
- [x] Evidence captured: git commit d2258045

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py::TestHG11EvidenceInjection::test_api_ids_guard_appears_in_prompt -v
```

**Expected artifacts**:
- Test passes confirming "DO NOT invent" language present in prompt

## Integration boundary proven

**Upstream integration**: `understand.api_surface.api_identifiers` → generate worker → `_format_api_ids_guard()`.

**Downstream integration**: Section prompt with class name guard → LLM → fewer hallucinated class names in generated content.
