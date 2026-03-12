---
id: TC-4019
title: "HG-11: Inject limitations and API identifiers into generate worker section prompt"
status: Done
priority: Critical
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, evidence-injection, quality]
depends_on: [TC-4002, TC-4016]
ruleset_version: "1.0"
spec_ref: "7213540"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4019_hg11-generate-evidence-injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/test_section_prompt_evidence.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4019 — HG-11: Evidence Injection into Generate Worker

## Objective

The pilot quality report (HG-02) revealed that the generate worker does not use the structured evidence assembled by the understand worker (limitations, API identifiers). The LLM generates content from claims alone, ignoring the typed API surface and known limitations. This taskcard injects `product_evidence.limitations` and the `api_identifiers` prohibited-names guard into the section prompt so generated content is grounded in source-verified facts.

## Required spec references

- `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt()` function
- `src/launcher/workers/generate/worker.py` — caller of `build_section_prompt()`
- `src/launcher/models/understanding.py` — `LimitationEntry`, `ProductEvidence`
- `phase_store/pilot_quality_report.md` — root cause analysis

## Scope

### In scope

- Add `limitations` parameter to `build_section_prompt()` in `section_prompt.py`
- Build a `KNOWN LIMITATIONS` block from `product_evidence.limitations` (capped at 10 entries)
- Add explicit `api_identifiers` guard block: "DO NOT INVENT these class names — only use the ones listed"
- Inject both blocks into the `section_writer.txt` prompt template
- Pass `product_evidence.limitations` and `api_surface.api_identifiers` from `worker.py` to `build_section_prompt()`
- Write 4+ unit tests for the new block formatters

### Out of scope

- Changing understand worker (evidence is already assembled correctly)
- Adding new model fields
- Changing claims extraction

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt()` signature and prompt assembly
- `src/launcher/workers/generate/worker.py` — `_generate_page_sections()` call site
- `src/launcher/models/understanding.py` — `LimitationEntry` model
- `src/launcher/prompts/section_writer.txt` — prompt template

## Outputs

- Updated `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt()` with `limitations` and `api_identifiers` params
- Updated `src/launcher/workers/generate/worker.py` — passes evidence from understanding bundle
- Updated `src/launcher/prompts/section_writer.txt` — `{limitations_block}` and `{api_ids_guard}` placeholders
- New `tests/unit/workers/generate/test_section_prompt_evidence.py` — 4+ tests

## Allowed paths

- plans/taskcards/TC-4019_hg11-generate-evidence-injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/test_section_prompt_evidence.py

### Allowed paths rationale

All changes are confined to the generate worker (section_prompt.py, worker.py, section_writer.txt) and a new test file. No model or understand worker changes needed.

## Implementation steps

### Step 1: Add `limitations` and `api_identifiers` parameters to `build_section_prompt()`

In `section_prompt.py`, add two new optional parameters:

```python
def build_section_prompt(
    ...,
    install_recipe: "Any | None" = None,
    limitations: "list | None" = None,      # list[LimitationEntry]
    api_identifiers: "list[str] | None" = None,  # top API tokens
) -> str:
```

### Step 2: Build limitations block

Add `_format_limitations()` helper:
```python
def _format_limitations(limitations: list | None) -> str:
    if not limitations:
        return ""
    lines = []
    for lim in limitations[:10]:
        feature = getattr(lim, "feature", "") or str(lim)
        constraint = getattr(lim, "constraint", "")
        status = getattr(lim, "status", "warning")
        line = f"- {feature}: {constraint}" if constraint else f"- {feature}"
        if status in ("experimental", "unsupported", "deprecated"):
            line += f" [{status}]"
        lines.append(line)
    return "\n".join(lines)
```

Call it in `build_section_prompt()` and pass result as `{limitations_block}`.

### Step 3: Build API identifier guard

Add `_format_api_ids_guard()` helper:
```python
def _format_api_ids_guard(api_identifiers: list[str] | None, display_name: str) -> str:
    if not api_identifiers:
        return ""
    top = api_identifiers[:30]
    return (
        f"KNOWN API CLASS NAMES FOR {display_name.upper()} "
        f"(DO NOT invent any class or module name outside this list):\n"
        + ", ".join(top)
    )
```

### Step 4: Update `section_writer.txt` prompt template

Add two new blocks to the prompt template, before STRICT RULES:

```
{limitations_block_section}
{api_ids_guard_section}
```

Where:
- `{limitations_block_section}` renders as `\nKNOWN LIMITATIONS (verified from source):\n{limitations_block}\n` when non-empty, else empty string
- `{api_ids_guard_section}` renders as the api_ids_guard string when non-empty

### Step 5: Update `worker.py` call site

In `_generate_page_sections()` (or equivalent function), pass `limitations` and `api_identifiers` from the understanding bundle:

```python
prompt = build_section_prompt(
    ...,
    install_recipe=install_recipe,
    limitations=getattr(understanding_bundle.product_evidence, "limitations", None),
    api_identifiers=getattr(understanding_bundle.api_surface, "api_identifiers", None),
)
```

Find where `understanding_bundle` or its fields are accessible in the generate worker.

### Step 6: Write unit tests

In new `tests/unit/workers/generate/test_section_prompt_evidence.py`:
- Test that limitations block appears in prompt when limitations present
- Test that limitations block absent when limitations list is empty
- Test that api_ids_guard appears in prompt when api_identifiers present
- Test that api_ids_guard capped at 30 identifiers

## Failure modes

### Failure mode 1: `understanding_bundle.product_evidence` not available in generate worker

**Detection**: AttributeError or KeyError when accessing product_evidence in worker.py
**Resolution**: Check how the understanding bundle is loaded in the generate worker. It may be loaded from disk via checkpoint. Access via `getattr(..., None)` with fallback.
**Gate**: Generate worker runs without error on pilot config

### Failure mode 2: Prompt template grows too large (token budget exceeded)

**Detection**: LLM returns 429 or timeout; or `_sec_max_tokens` exceeded
**Resolution**: Cap limitations at 10 entries (already in design). Cap api_identifiers at 30 tokens. Add char budget check: if combined block > 500 chars, trim further.
**Gate**: Pilot run completes all 22 pages without LLM errors

### Failure mode 3: Existing tests break due to prompt template change

**Detection**: Test failures in `test_section_prompt.py` or `test_generate.py`
**Resolution**: Update test fixtures that assert on exact prompt text. Use `assertIn` for block presence rather than full-string equality.
**Gate**: Full test suite passes

### Failure mode 4: `{limitations_block_section}` placeholder breaks format() call

**Detection**: `KeyError: 'limitations_block_section'` at prompt format time
**Resolution**: Ensure both new placeholders are passed to `template.format()` call in `build_section_prompt()`. Use empty string as default.
**Gate**: `build_section_prompt()` returns without error on all page roles

## Task-specific review checklist

1. [ ] `build_section_prompt()` has `limitations` and `api_identifiers` params
2. [ ] `_format_limitations()` helper correctly renders LimitationEntry objects
3. [ ] `_format_api_ids_guard()` helper caps at 30 and uses MUST NOT language
4. [ ] `section_writer.txt` has `{limitations_block_section}` and `{api_ids_guard_section}` placeholders
5. [ ] `worker.py` passes `product_evidence.limitations` to `build_section_prompt()`
6. [ ] `worker.py` passes `api_surface.api_identifiers` to `build_section_prompt()`
7. [ ] 4+ unit tests in new test file all pass
8. [ ] Full test suite passes with no new failures
9. [ ] Docstrings updated for modified functions
10. [ ] Spec file `specs/worker_generate.md` checked for drift (or confirmed no spec change)
11. [ ] Schema `"description"` fields not affected (no schema changes)

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py`
2. Updated `src/launcher/workers/generate/worker.py`
3. Updated `src/launcher/prompts/section_writer.txt`
4. New `tests/unit/workers/generate/test_section_prompt_evidence.py`

## Acceptance checks

- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py -v` — 4+ tests PASS
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures
- [ ] `build_section_prompt()` prompt string contains "KNOWN LIMITATIONS" when limitations non-empty
- [ ] `build_section_prompt()` prompt string contains "DO NOT invent" when api_identifiers non-empty

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: build_section_prompt() smoke test PASS
- [ ] Evidence captured: pilot run prompt dump showing new blocks
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~1` — clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `tests/unit/workers/generate/test_section_prompt_evidence.py` — 4+ tests passing
- Prompt output containing KNOWN LIMITATIONS block (verifiable via test assertions)

## Integration boundary proven

**Upstream integration**: `understand_checkpoint.json` → `product_evidence.limitations` + `api_surface.api_identifiers` → generate worker.

**Downstream integration**: `build_section_prompt()` → LLM prompt → generated sections with fewer hallucinated class names and limitation violations.
