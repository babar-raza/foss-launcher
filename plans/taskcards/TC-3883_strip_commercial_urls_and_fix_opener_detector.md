---
id: TC-3883
title: "Strip commercial URLs after enforce_block_spec and fix artifacts opener false positive"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [safety, artifacts, generate, evaluate, false_positive]
depends_on: [TC-3882]
allowed_paths:
  - plans/taskcards/TC-3883_strip_commercial_urls_and_fix_opener_detector.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/checks/artifacts.py
  - tests/unit/workers/evaluate/checks/test_artifacts.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-3883/evidence.md
---

# Taskcard TC-3883 — Strip commercial URLs after enforce_block_spec and fix artifacts opener false positive

## Objective

Two safety-critical HIGH findings are blocking GO:

1. **safety HIGH (4 pages)**: `https://docs.aspose.com` appears in prose — not stripped because
   `_strip_commercial_urls` is only applied to initial LLM-generated blocks, NOT to blocks produced
   by `enforce_block_spec` pass 2 LLM retry or the fallback renderer. Fix: apply stripping at the
   end of `_generate_section` regardless of which path produced the section.

2. **artifacts HIGH (5 pages)**: "Repeated section opener 'aspose.'" — false positive because the
   `check_artifacts` opener detector splits at the first `.` character, truncating the product name
   "Aspose.Cells" to "aspose." The intent is to catch repeated *sentence* starters, not product
   name prefixes. Fix: use period+whitespace (`. `) as the sentence boundary.

## Required spec references

- `specs/09_quality_evaluation.md` (artifacts and safety check definitions)

## Scope

### In scope
- Apply `_strip_commercial_urls` after `enforce_block_spec` return and after fallback render
- Fix `check_artifacts` opener detection to use `. ` (period+space) as sentence boundary
- Update tests for both changes

### Out of scope
- Changing the commercial domain list (`_COMMERCIAL_URL_RE` pattern)
- Changing the repeat threshold (currently ≥5 triggers HIGH)
- Any other checks or workers

## Inputs

- `src/launcher/workers/generate/worker.py` — `_generate_section` function
- `src/launcher/workers/evaluate/checks/artifacts.py` — `check_artifacts` function

## Outputs

- Fixed generate worker (commercial URLs stripped on ALL code paths)
- Fixed artifacts check (opener uses sentence boundary, not first period)

## Allowed paths

- plans/taskcards/TC-3883_strip_commercial_urls_and_fix_opener_detector.md
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/checks/artifacts.py
- tests/unit/workers/evaluate/checks/test_artifacts.py
- tests/unit/workers/generate/

### Allowed paths rationale
- generate/worker.py — contains `_generate_section` and `_strip_commercial_urls`
- artifacts.py — contains the opener detection logic
- test files — update/add tests

## Implementation steps

### Step 1: Fix generate/worker.py — apply stripping after ALL paths

In `_generate_section`, AFTER `enforce_block_spec` and the fallback path, apply
`_strip_commercial_urls` to the final `section_ir.blocks` before returning.

Change the section return from:
```python
if golden_index is not None:
    section_ir, pass_used = await enforce_block_spec(...)
    ...

return section_ir, _llm, _fb
```

To also apply stripping:
```python
if golden_index is not None:
    section_ir, pass_used = await enforce_block_spec(...)
    ...

# Final commercial URL strip — catches pass2 retry and fallback paths
clean_blocks = _strip_commercial_urls(list(section_ir.blocks))
if clean_blocks is not section_ir.blocks:
    section_ir = section_ir.model_copy(update={"blocks": clean_blocks})

return section_ir, _llm, _fb
```

### Step 2: Fix artifacts.py — sentence boundary detection

Change the opener detection from `stripped.find(".")` to use period+space boundary:

```python
# Before (wrong — truncates at product name periods like "Aspose.Cells"):
dot_idx = stripped.find(".")
first_sentence = stripped[: dot_idx + 1] if dot_idx >= 0 else stripped

# After (correct — only truncates at sentence-ending periods):
m = re.search(r'\.\s', stripped)
first_sentence = stripped[: m.end() - 1 + 1] if m else stripped
```

### Step 3: Add/update tests

Add tests in `test_artifacts.py`:
- Test that "Aspose.Cells for Python provides..." repeated in 5+ sections does NOT trigger HIGH
- Test that actually repeated openers ("This section covers..." × 6) DO trigger HIGH

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/test_artifacts.py tests/unit/workers/generate/ -v
```

## Failure modes

### Failure mode 1: Stripping breaks valid blocks

**Detection**: Blocks that should NOT have commercial URLs lose content accidentally
**Resolution**: The `_COMMERCIAL_URL_RE` pattern is conservative and only matches known commercial domains
**Gate**: test suite

### Failure mode 2: Opener fix causes new false negatives

**Detection**: Truly repeated openers no longer detected
**Resolution**: Test with actual repeated openers ("This section covers..." × 6)
**Gate**: test_artifacts.py

### Failure mode 3: model_copy on SectionIR fails

**Detection**: AttributeError on `section_ir.model_copy`
**Resolution**: Check SectionIR is a pydantic model (it is — extends BlockIR parent model)
**Gate**: generate tests

## Task-specific review checklist

1. [x] `_strip_commercial_urls` applied after `enforce_block_spec` return
2. [x] `_strip_commercial_urls` applied after fallback render path
3. [x] Artifacts opener uses `. ` (period+space) not `.` for sentence boundary
4. [x] Tests confirm "Aspose.Cells" openers no longer trigger false positive
5. [x] Tests confirm genuinely repeated openers still trigger HIGH
6. [x] Full pytest suite passes
7. [x] Docstrings updated for changed functions
8. [x] Spec file confirmed no drift
9. [x] Schema descriptions present
10. [x] docs/README.md ownership checked
11. [x] No new docs/guides files needed

## Deliverables

1. `src/launcher/workers/generate/worker.py` — final commercial URL stripping
2. `src/launcher/workers/evaluate/checks/artifacts.py` — sentence boundary fix
3. Reports via test pass output

## Acceptance checks

1. [ ] `check_artifacts` does NOT flag pages where every section starts with "Aspose.Cells..."
2. [ ] `check_artifacts` DOES flag pages with genuinely repeated openers (≥5)
3. [ ] `_strip_commercial_urls` is applied after `enforce_block_spec` in `_generate_section`
4. [ ] All tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3883/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/test_artifacts.py -v
```

## Integration boundary proven

**Upstream**: LLM generates content (via initial call + enforce_block_spec retry)
**Downstream**: check_artifacts evaluates rendered prose; check_safety evaluates URLs
**Contract**: Commercial URLs stripped before render; opener uses sentence boundary
