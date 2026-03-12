---
id: TC-4229
title: "G-3: Enforce code blocks in reference/api_reference sections"
status: Done
priority: High
owner: "agent"
updated: "2026-03-12"
tags: [generate, code-blocks, reference-pages]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4229_generate-enforce-code-blocks-reference-pages.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - reports/TC-4229/evidence.md
---

# Taskcard TC-4229 — G-3: Enforce code blocks in reference/api_reference sections

## Objective

Fix the persistent "Missing required code block for this page role" gate failure on `api_reference` and `reference_object_page` sections. The existing retry logic only retries for thin prose; it does not retry specifically for missing code blocks. Adding a code-block retry instruction and strengthening the prompt for reference roles eliminates the zero-improvement pattern across all 3 generate→evaluate cycles.

## Required spec references

- `specs/worker_generate.md` (Section: Section retry logic, code-required roles)
- `specs/worker_evaluate.md` (Section: Missing code block gate for reference pages)

## Scope

### In scope
- In `worker.py` `_generate_section`: when code block is missing for a code-required role, extend the retry instruction to explicitly demand a code block
- In `section_writer.txt` STRICT RULES: add an explicit code block requirement for reference page roles
- The fix applies to roles in `_CODE_REQUIRED_ROLES`: api_reference, reference_object_page, howto_article, getting_started, installation

### Out of scope
- Changes to `_quick_section_quality_check` gate logic (already detects the violation correctly)
- Changes to the evaluate worker (it already gates correctly)
- Changes to golden enforcement (separate pass)

## Inputs

- `src/launcher/workers/generate/worker.py` — `_generate_section` retry loop (lines ~1086-1098)
- `src/launcher/prompts/section_writer.txt` — HALLUCINATION PREVENTION block (lines 53-61)

## Outputs

- Modified `worker.py` with code-block-aware retry instruction
- Modified `section_writer.txt` with explicit code requirement for reference page roles

## Allowed paths

- plans/taskcards/TC-4229_generate-enforce-code-blocks-reference-pages.md
- src/launcher/workers/generate/worker.py
- src/launcher/prompts/section_writer.txt

### Allowed paths rationale
The retry loop fix is in worker.py `_generate_section`. The prompt fix is in section_writer.txt.

## Implementation steps

### Step 1: Add code-block check to the retry condition in worker.py

In the `_generate_section` retry loop (after `_prose_count` check), add a secondary check: if the page_role is in `_CODE_REQUIRED_ROLES` and no code blocks exist, build a stronger retry prompt that includes `CRITICAL: This section REQUIRES at least one code block...`. Apply this retry independently from the prose-word-count retry so both conditions can trigger a retry.

The combined retry logic should be:
1. Check prose count (existing)
2. Check code block presence for code-required roles (new)
3. Build retry prompt addressing whichever condition(s) failed
4. Accept if both conditions pass

### Step 2: Add reference-role code requirement in section_writer.txt

In the STRICT RULES block (or in a new REFERENCE PAGE REQUIREMENTS block prepended by `build_section_prompt` for reference roles), add:
"For api_reference and reference_object_page roles: ALWAYS include at least one executable code example per section. A reference section without a code block is incomplete and will fail evaluation."

Since `_REFERENCE_PREAMBLE` is already prepended for reference roles, add the code block requirement there.

### Step 3: Run tests

Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q`.

## Failure modes

### Failure mode 1: EVIDENCE ABSENT instruction conflicts with new code requirement

**Detection**: `build_section_prompt` injects `EVIDENCE ABSENT: Do NOT generate any fenced code block` when no snippets exist for a code-required role. The new code requirement contradicts this.
**Resolution**: When `_no_snippets and _code_role` → the EVIDENCE ABSENT instruction should WIN over the new requirement (no snippets means no basis for code). The new requirement only applies when snippets ARE available. Add a guard: only inject the code-requirement retry instruction when `sec_snippets` is non-empty.
**Gate**: `test_section_prompt.py` tests for EVIDENCE ABSENT injection.

### Failure mode 2: Retry prompt exceeds token budget

**Detection**: Additional retry instruction causes `finish_reason: length` on retries.
**Resolution**: Keep the code-block retry addition short (<50 words). It is appended to the existing retry prompt string.
**Gate**: Monitor `finish_reason` events in LLM call logs.

### Failure mode 3: _REFERENCE_PREAMBLE change breaks table-only sections

**Detection**: Constructors / Properties / Methods sections (which legitimately use tables, not code) fail because code is now required.
**Resolution**: The code requirement is page-role-level, not section-type-level. Reference pages that have "Constructors" or "Properties" headings should not be forced to have code; the requirement targets sections like "Overview" and "Example". Limit the retry to sections whose heading matches code-expected patterns (not constructor/property/method table sections).
**Gate**: `_quick_section_quality_check` only fires on sections in `_CODE_REQUIRED_ROLES` pages — the fix must match the same scope.

## Task-specific review checklist

1. [ ] Retry instruction for missing code block only fires when `sec_snippets` is non-empty (evidence exists)
2. [ ] Retry instruction is concise (<50 words) and clearly states "at least one code block required"
3. [ ] `_REFERENCE_PREAMBLE` or reference-role prompt injection includes explicit code block requirement
4. [ ] The fix does not contradict EVIDENCE ABSENT instruction (EVIDENCE ABSENT wins when no snippets)
5. [ ] Constructor/property/method table sections are not forced to have code blocks by this fix
6. [ ] Retry instruction is only added on `_attempt < _MAX_SECTION_RETRIES` (not on final attempt)
7. [ ] Docstrings updated for `_generate_section` to document code-block retry
8. [ ] Spec file confirmed — generate worker spec not changed
9. [ ] Schema description fields not impacted
10. [ ] `docs/README.md` ownership map checked — no guide update required
11. [ ] No new `docs/guides/` file created

## Deliverables

1. Modified `src/launcher/workers/generate/worker.py` (code-block retry in `_generate_section`)
2. Modified `src/launcher/prompts/section_writer.txt` (reference-role code requirement)

## Acceptance checks

1. [ ] Reference page sections with available snippets include code blocks in generated output
2. [ ] `_quick_section_quality_check` violations for "Missing required code block" decrease to <20% of reference sections
3. [ ] Unit tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -x -q`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: generate worker unit tests PASS
- [ ] Evidence captured: reports/TC-4229/evidence.md
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py tests/unit/workers/generate/ -x -q
```

**Expected results**:
- All tests pass
- Reference page sections with snippets trigger code-block retry when code is absent

## Integration boundary proven

**Upstream**: `_generate_section` builds retry prompt from `section_prompt_str + retry_instruction`
**Downstream**: `_quick_section_quality_check` gate still validates the final section
**Contract**: Retry prompt is passed to `_call_llm`; response is validated by `parse_and_validate_blocks`
