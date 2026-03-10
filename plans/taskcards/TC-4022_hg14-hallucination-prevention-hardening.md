---
id: TC-4022
title: "HG-14: Strengthen hallucination prevention — format-option class pattern guard"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, prompt-hardening, hallucination]
depends_on: [TC-4019, TC-4021]
ruleset_version: "1.0"
spec_ref: "5234ff10"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4022_hg14-hallucination-prevention-hardening.md
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/test_section_prompt_evidence.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4022 — HG-14: Hallucination Prevention Hardening

## Objective

The post-HG-11/12 pilot (2026-03-11) showed 27 factual_accuracy + 17 api_consistency high findings from hallucinated format-option class names (`ObjLoadOptions`, `StlFormat`, `StlSaveOptions`). These classes follow Aspose naming patterns from the LLM's training data but do NOT exist in the aspose-3d-foss-python API. The existing HALLUCINATION PREVENTION section lists `Paragraph, Run, TextRange` as examples but does not call out format-option class patterns. This taskcard adds an explicit pattern guard to stop format-option class hallucination.

## Required spec references

- `phase_store/pilot_quality_report.md` — post-HG-11/12 measurement (27 factual_accuracy, 17 api_consistency)
- `src/launcher/prompts/section_writer.txt` — HALLUCINATION PREVENTION section

## Scope

### In scope

- Add format-option class pattern guard to `section_writer.txt` HALLUCINATION PREVENTION section
- Add 2+ unit tests verifying the new guard language is present in the template

### Out of scope

- Changing `section_prompt.py` code logic
- Changing `worker.py`
- Moving the HG-11 api_ids_guard placement (that is a larger change with risk of breaking existing tests)

## Inputs

- `src/launcher/prompts/section_writer.txt` — current HALLUCINATION PREVENTION section
- `phase_store/pilot_quality_report.md` — confirmed hallucinated class patterns

## Outputs

- Updated `src/launcher/prompts/section_writer.txt` — new bullet in HALLUCINATION PREVENTION
- 2+ new tests in `tests/unit/workers/generate/test_section_prompt_evidence.py`

## Allowed paths

- plans/taskcards/TC-4022_hg14-hallucination-prevention-hardening.md
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/test_section_prompt_evidence.py

### Allowed paths rationale

Only the prompt template (not code) and the existing test file are changed. No model, worker, or schema changes needed.

## Implementation steps

### Step 1: Add format-option class guard to HALLUCINATION PREVENTION

In `section_writer.txt`, in the HALLUCINATION PREVENTION section, after the line:
```
- NEVER generate classes like Paragraph, Run, TextRange, or any class not in the API SURFACE
```

Add:
```
- NEVER generate format-specific option or settings classes like `ObjLoadOptions`, `StlSaveOptions`, `FbxLoadOptions`, `XlsxSaveOptions`, or ANY class whose name ends in `LoadOptions`, `SaveOptions`, `Options`, `Settings`, or `Format` unless that exact class name appears in the API SURFACE above. These patterns are common in OTHER Aspose libraries but may NOT exist in THIS library
```

### Step 2: Add tests

In `tests/unit/workers/generate/test_section_prompt_evidence.py`, add a new test class `TestHG14HallucinationPrevention`:

```python
class TestHG14HallucinationPrevention:
    """HG-14: Format-option class pattern guard in section_writer.txt."""

    def test_format_option_guard_in_template(self):
        """section_writer.txt HALLUCINATION PREVENTION contains format-option guard."""
        from pathlib import Path
        template_path = (
            Path(__file__).parents[4]
            / "src" / "launcher" / "prompts" / "section_writer.txt"
        )
        text = template_path.read_text(encoding="utf-8")
        assert "LoadOptions" in text, "Guard must mention LoadOptions pattern"
        assert "SaveOptions" in text, "Guard must mention SaveOptions pattern"

    def test_format_option_guard_in_prompt(self):
        """build_section_prompt() output includes LoadOptions guard from template."""
        from launcher.workers.generate.section_prompt import build_section_prompt
        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
        )
        assert "LoadOptions" in prompt
        assert "SaveOptions" in prompt
```

## Failure modes

### Failure mode 1: Guard adds ambiguity for libraries that DO have LoadOptions classes

**Detection**: Other product pilots (aspose-cells, aspose-note) generate valid code using OdsLoadOptions, PdfSaveOptions, etc. that are in their API surface
**Resolution**: Guard says "unless that exact class name appears in the API SURFACE above" — the API SURFACE block is still the authoritative check
**Gate**: aspose-cells pilot does not regress

### Failure mode 2: Template format() call breaks on new text

**Detection**: KeyError or ValueError at prompt generation time
**Resolution**: New text contains no `{placeholder}` patterns; it is static prose only
**Gate**: `build_section_prompt()` runs without error

### Failure mode 3: Existing tests fail due to template text change

**Detection**: test_section_prompt.py or test_generate.py failures
**Resolution**: No existing tests assert exact template content; they use assertIn
**Gate**: Full test suite passes

## Task-specific review checklist

1. [ ] `section_writer.txt` HALLUCINATION PREVENTION section mentions `LoadOptions` pattern
2. [ ] `section_writer.txt` HALLUCINATION PREVENTION section mentions `SaveOptions` pattern
3. [ ] Guard text references "unless that exact class name appears in the API SURFACE above"
4. [ ] `test_format_option_guard_in_template` passes
5. [ ] `test_format_option_guard_in_prompt` passes
6. [ ] Full test suite passes with no new failures

## Deliverables

1. Updated `src/launcher/prompts/section_writer.txt`
2. 2 new tests in `tests/unit/workers/generate/test_section_prompt_evidence.py`

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py::TestHG14HallucinationPrevention -v` — 2/2 tests PASS
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures (3567 passed)
- [x] `section_writer.txt` contains "LoadOptions" and "SaveOptions" in HALLUCINATION PREVENTION section

## Self-review

### Verification results
- [x] Tests: 10/10 PASS (TestHG11EvidenceInjection 8/8 + TestHG14HallucinationPrevention 2/2)
- [x] Full suite: 3567 passed, 6 pre-existing failures only
- [x] Template change confirmed: "LoadOptions", "SaveOptions" present in HALLUCINATION PREVENTION section

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py::TestHG14HallucinationPrevention -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `tests/unit/workers/generate/test_section_prompt_evidence.py` — 2 new tests in `TestHG14HallucinationPrevention` passing
- `src/launcher/prompts/section_writer.txt` — "LoadOptions" and "SaveOptions" present in HALLUCINATION PREVENTION section
- Full suite: 3567 passed, 6 pre-existing failures only

## Integration boundary proven

**Upstream**: `section_writer.txt` HALLUCINATION PREVENTION → `build_section_prompt()` → LLM
**Downstream**: LLM prompted with format-option class prohibition → fewer `ObjLoadOptions`/`StlSaveOptions` hallucinations → lower factual_accuracy + api_consistency finding counts
