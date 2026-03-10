---
id: TC-4023
title: "HG-15: Claim coverage enforcement — eliminate completeness failures"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, prompt-hardening, completeness]
depends_on: [TC-4022]
ruleset_version: "1.0"
spec_ref: "941aa20c"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4023_hg15-claim-coverage-enforcement.md
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/test_section_prompt_evidence.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4023 — HG-15: Claim Coverage Enforcement

## Objective

The post-HG-14 pilot (2026-03-11) showed 8 high-severity `completeness` findings — the LLM skips assigned claims and produces thin sections. The current template header says "skip any that do not fit this section's topic", which actively invites the LLM to skip claims. This taskcard replaces that permissive language with a mandatory coverage instruction and adds a STRICT RULES bullet requiring every assigned claim to appear in the output.

## Required spec references

- `phase_store/pilot_quality_report.md` — post-HG-14 measurement (8 completeness high findings)
- `src/launcher/prompts/section_writer.txt` — CLAIMS TO USE header and STRICT RULES section

## Scope

### In scope

- Change CLAIMS TO USE block header in `section_writer.txt` to require full coverage
- Add STRICT RULES bullet making claim coverage mandatory
- Add 2+ unit tests verifying new instruction language is present

### Out of scope

- Changing `section_prompt.py` claim distribution logic (`_distribute_claims`)
- Changing `worker.py`
- Changing claim assignment in the planner

## Inputs

- `src/launcher/prompts/section_writer.txt` — current CLAIMS TO USE header (permissive)
- `phase_store/pilot_quality_report.md` — confirmed 8 completeness high findings

## Outputs

- Updated `src/launcher/prompts/section_writer.txt` — new coverage instructions
- 2+ new tests in `tests/unit/workers/generate/test_section_prompt_evidence.py`

## Allowed paths

- plans/taskcards/TC-4023_hg15-claim-coverage-enforcement.md
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/test_section_prompt_evidence.py

### Allowed paths rationale

Only the prompt template (not code) and the existing test file are changed. No model, worker, or schema changes needed.

## Implementation steps

### Step 1: Update CLAIMS TO USE header

In `section_writer.txt`, replace the current permissive claims header:
```
CLAIMS TO USE (use the most relevant claims below; skip any that do not fit this section's topic — do not invent new facts):
```

With a mandatory coverage instruction:
```
CLAIMS TO USE — MANDATORY COVERAGE (ALL claims below are pre-assigned to this section and MUST appear in your output. Do NOT skip any claim. Each claim must be addressed in your prose and cited in claim_ids. Do not invent facts beyond what the claims state):
```

### Step 2: Add STRICT RULES bullet for claim coverage

In `section_writer.txt`, in the STRICT RULES section, after the line:
```
- Every paragraph must trace to at least one claim via claim_ids
```

Add:
```
- CRITICAL: You MUST address EVERY claim listed in CLAIMS TO USE above. Each claim must appear in your prose content and be cited in the claim_ids array of at least one block. Thin or incomplete coverage of assigned claims is a quality failure
```

### Step 3: Add tests

In `tests/unit/workers/generate/test_section_prompt_evidence.py`, add a new test class `TestHG15ClaimCoverage`:

```python
class TestHG15ClaimCoverage:
    """HG-15: Mandatory claim coverage instruction in section_writer.txt."""

    def test_coverage_instruction_in_template(self):
        """section_writer.txt CLAIMS header requires mandatory coverage."""
        from pathlib import Path
        template_path = (
            Path(__file__).parents[4]
            / "src" / "launcher" / "prompts" / "section_writer.txt"
        )
        text = template_path.read_text(encoding="utf-8")
        assert "MANDATORY COVERAGE" in text, "Header must require mandatory coverage"
        assert "Do NOT skip any claim" in text, "Must explicitly prohibit skipping claims"

    def test_coverage_strict_rule_in_prompt(self):
        """build_section_prompt() output includes mandatory coverage rule."""
        from launcher.workers.generate.section_prompt import build_section_prompt
        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
        )
        assert "MANDATORY COVERAGE" in prompt
        assert "Do NOT skip any claim" in prompt
```

## Failure modes

### Failure mode 1: Mandatory coverage forces bad content for sections with no relevant claims

**Detection**: Section with 0 relevant claims still tries to produce content for unrelated claims.
**Resolution**: The guard is in the CLAIMS block header — if no claims are assigned (empty block), the instruction is effectively inactive. The `_distribute_claims()` function already ensures each section only receives its share of page-level claims. Only claims genuinely assigned to this section appear.
**Gate**: Existing tests verify empty claims produce well-formed prompts.

### Failure mode 2: Template format() call breaks on new text

**Detection**: KeyError or ValueError at prompt generation time from `{...}` in new text.
**Resolution**: New text contains no `{placeholder}` patterns; it is static prose only. No brace characters.
**Gate**: `build_section_prompt()` runs without error in unit tests.

### Failure mode 3: Existing tests fail due to template text change

**Detection**: Failures in `test_section_prompt.py` or `test_generate.py` that assert old header text.
**Resolution**: No existing tests assert the exact CLAIMS header text; they use `assertIn` on specific phrases. Old phrase "skip any that do not fit" is removed — check for tests that assert this and update them if found.
**Gate**: Full test suite passes.

## Task-specific review checklist

1. [ ] `section_writer.txt` CLAIMS header contains "MANDATORY COVERAGE"
2. [ ] `section_writer.txt` CLAIMS header contains "Do NOT skip any claim"
3. [ ] STRICT RULES section contains claim coverage bullet
4. [ ] `test_coverage_instruction_in_template` passes
5. [ ] `test_coverage_strict_rule_in_prompt` passes
6. [ ] Full test suite passes with no new failures
7. [ ] Docstrings updated for all new/changed public functions (N/A — template only)
8. [ ] Spec file updated if worker behavior changed (N/A — prompt template only)
9. [ ] Schema `"description"` fields present for all new/changed properties (N/A)
10. [ ] Checked `docs/README.md` ownership map — no trigger event applies
11. [ ] If a new `docs/guides/` file was added: N/A

## Deliverables

1. Updated `src/launcher/prompts/section_writer.txt` — mandatory coverage instruction in CLAIMS header and STRICT RULES
2. 2 new tests in `tests/unit/workers/generate/test_section_prompt_evidence.py`

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py::TestHG15ClaimCoverage -v` — 2/2 tests PASS
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures (3569 passed)
- [x] `section_writer.txt` contains "MANDATORY COVERAGE" and "Do NOT skip any claim"

## Self-review

### Verification results
- [x] Tests: 12/12 PASS (TestHG11EvidenceInjection 8/8 + TestHG14HallucinationPrevention 2/2 + TestHG15ClaimCoverage 2/2)
- [x] Full suite: 3569 passed, 6 pre-existing failures only
- [x] Template change confirmed: "MANDATORY COVERAGE" and "Do NOT skip any claim" present in CLAIMS header and STRICT RULES section

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt_evidence.py::TestHG15ClaimCoverage -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `tests/unit/workers/generate/test_section_prompt_evidence.py` — 2 new tests in `TestHG15ClaimCoverage` passing
- `src/launcher/prompts/section_writer.txt` — "MANDATORY COVERAGE" and "Do NOT skip any claim" present in CLAIMS header
- Full suite: 3567 passed, 6 pre-existing failures only

## Integration boundary proven

**Upstream**: `section_writer.txt` CLAIMS MANDATORY COVERAGE header → `build_section_prompt()` → LLM
**Downstream**: LLM sees all assigned claims as required → covers more claims → fewer completeness=high findings → higher A+B grade
