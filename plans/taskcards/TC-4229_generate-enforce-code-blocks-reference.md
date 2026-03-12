---
id: TC-4229
title: "G-3: Enforce code blocks in reference/api_reference sections"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, code-blocks, reference, section-gate]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4229_generate-enforce-code-blocks-reference.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-4229/evidence.md
---

# Taskcard TC-4229 — G-3: Enforce code blocks in reference/api_reference sections

## Objective

Eliminate Section gate failures for reference and api_reference pages by enforcing code block generation in the section prompt and adding a retry when a code block is missing from a required-code-block role. This ensures reference pages always contain the code blocks required by the evaluate gate.

## Required spec references

- `specs/worker_generate.md` (Section: Section gate, code block enforcement)
- `specs/worker_evaluate.md` (Section: code check for reference pages)

## Scope

### In scope
- Add role-aware code block instruction to section prompt for reference/api_reference roles
- Add post-LLM check in `worker.py`: if page_role in CODE_REQUIRED_ROLES and no code block in output, trigger one retry with stronger instruction
- Unit tests for retry-on-missing-code-block logic

### Out of scope
- Changes to evaluate gate logic
- Changes to non-reference page roles

## Inputs

- `src/launcher/workers/generate/worker.py` — section generation and gate logic
- `src/launcher/prompts/section_writer.txt` — prompt template

## Outputs

- Modified `worker.py` — retry on missing code block for reference roles
- Modified `section_writer.txt` — stronger code block instruction for reference roles
- Updated tests in `tests/unit/workers/generate/`

## Allowed paths

- plans/taskcards/TC-4229_generate-enforce-code-blocks-reference.md
- src/launcher/workers/generate/worker.py
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/

### Allowed paths rationale
Both the retry logic (worker.py) and the prompt instruction (section_writer.txt) must be updated together.

## Implementation steps

### Step 1: Define CODE_REQUIRED_ROLES

In `worker.py`, define or extend:
```python
CODE_REQUIRED_ROLES = {"reference", "api_reference", "class_reference", "method_reference"}
```

### Step 2: Add post-LLM code block check with retry

After LLM response received, if `page_role in CODE_REQUIRED_ROLES` and no fenced code block (` ``` `) in response content:
1. Log `WARNING: No code block in reference section, retrying with stronger instruction`
2. Retry LLM call with additional instruction: `"CRITICAL: You MUST include at least one fenced code block (```) in your response for this reference page."`
3. If retry also lacks code block, log `ERROR` and continue (do not fail — partial content is better than no content)

### Step 3: Update section_writer.txt

For reference page roles, add:
```
REFERENCE PAGES REQUIRE CODE: This is a reference page. You MUST include at least one fenced code block showing usage. A reference page without code is incomplete.
```

### Step 4: Write unit tests

Add tests covering:
1. Reference page with code block — no retry triggered
2. Reference page missing code block — retry triggered with stronger instruction
3. Non-reference page missing code block — no retry triggered
4. Reference page retry also fails — logs ERROR, continues without raise

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

## Failure modes

### Failure mode 1: Retry loop adds excessive latency for reference-heavy runs

**Detection**: Generate phase wall-clock time doubles for reference-rich pilots.
**Resolution**: Cap retries at 1 (not 3). The retry is a single fallback, not a full retry policy.
**Gate**: Generate phase time budget

### Failure mode 2: CODE_REQUIRED_ROLES does not match evaluate gate's list

**Detection**: Section gate still fails for roles not in CODE_REQUIRED_ROLES.
**Resolution**: Read `evaluate/checks/code.py` to get the exact role list used there, and mirror it in CODE_REQUIRED_ROLES.
**Gate**: Evaluate code check

### Failure mode 3: Retry instruction is too aggressive, corrupts prose sections

**Detection**: Reference page has code but no prose explanation.
**Resolution**: Retry instruction must say "at least one code block" not "code only". Verify existing prose is preserved in retry.
**Gate**: Readability check on reference pages

## Task-specific review checklist

1. [ ] `CODE_REQUIRED_ROLES` list mirrors evaluate gate's code-required roles
2. [ ] Retry triggered only when code block absent AND page_role in CODE_REQUIRED_ROLES
3. [ ] Retry uses stronger instruction string, not same prompt
4. [ ] After retry fails: ERROR logged, execution continues (no raise)
5. [ ] section_writer.txt has reference-page code requirement instruction
6. [ ] Unit test: reference page — retry triggered on missing code block
7. [ ] Docstrings updated for modified section generation function
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/generate/worker.py` — retry logic for reference pages
2. `src/launcher/prompts/section_writer.txt` — code block requirement instruction
3. `tests/unit/workers/generate/` — 4 new test cases
4. `reports/TC-4229/evidence.md` — log showing zero Section gate FAIL for reference pages

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v`
2. [ ] Retry triggered on missing code block for reference roles — confirmed by test
3. [ ] Pilot run: zero Section gate FAIL for reference/api_reference pages

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Section gate FAIL count = 0 for reference pages PASS
- [ ] Evidence captured: reports/TC-4229/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- Retry logic tests pass
- No regressions in existing generate tests

## Integration boundary proven

**Upstream**: LLM section writer — returns section content
**Downstream**: Evaluate code check gate — verifies code block presence
**Contract**: All reference page sections contain at least one fenced code block before evaluate
