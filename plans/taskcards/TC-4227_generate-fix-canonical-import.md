---
id: TC-4227
title: "G-1: Fix canonical_import injection in section prompt"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, canonical_import, section_prompt, injection]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4227_generate-fix-canonical-import.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-4227/evidence.md
---

# Taskcard TC-4227 — G-1: Fix canonical_import injection in section prompt

## Objective

Ensure `canonical_import` from the understand bundle is injected verbatim into every section prompt so the LLM uses `import {canonical_import}` not the runtime import form. This eliminates systematic wrong-import violations in generated pages.

## Required spec references

- `specs/worker_generate.md` (Section: Section prompt construction)
- `specs/worker_understand.md` (Section: canonical_import field)

## Scope

### In scope
- Verify `canonical_import` is read from understand bundle in `section_prompt.py`
- Inject `canonical_import` into the section prompt template with explicit instruction
- Update `section_writer.txt` to reference `{canonical_import}` placeholder
- Unit tests confirming injection for Python, .NET, Java, TypeScript platforms

### Out of scope
- Changes to how `canonical_import` is extracted in understand phase
- Changes to runtime_import handling

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — prompt builder
- `src/launcher/prompts/section_writer.txt` — prompt template
- Understand bundle — source of `canonical_import`

## Outputs

- Modified `section_prompt.py` — canonical_import injected
- Modified `section_writer.txt` — placeholder added
- Updated tests in `tests/unit/workers/generate/`

## Allowed paths

- plans/taskcards/TC-4227_generate-fix-canonical-import.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt
- tests/unit/workers/generate/

### Allowed paths rationale
Both the prompt builder and template must be updated together for the injection to work end-to-end.

## Implementation steps

### Step 1: Read section_prompt.py and section_writer.txt

Understand current prompt construction and where canonical_import is (or is not) injected.

### Step 2: Add canonical_import to prompt context

In `section_prompt.py`, ensure `canonical_import` from the understand bundle is added to the template context dict passed to `section_writer.txt`.

### Step 3: Update section_writer.txt

Add an explicit instruction in the prompt template:
```
CANONICAL IMPORT: Use exactly `import {canonical_import}` in all code examples. Do NOT use the runtime package name.
```

### Step 4: Write unit tests

Add tests in `tests/unit/workers/generate/` covering:
1. Python: `canonical_import = "aspose.cells"` appears verbatim in rendered prompt
2. .NET: `canonical_import = "Aspose.Cells"` appears verbatim
3. Missing canonical_import field: prompt construction does not crash (fallback to empty string or skip)

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

## Failure modes

### Failure mode 1: canonical_import missing from understand bundle

**Detection**: KeyError or empty string in prompt; LLM uses wrong import.
**Resolution**: Add guard: if `canonical_import` is empty, skip the injection line rather than injecting empty string. Log a WARNING.
**Gate**: Section prompt unit test with missing canonical_import

### Failure mode 2: Prompt template placeholder not substituted

**Detection**: Literal `{canonical_import}` appears in rendered prompt string.
**Resolution**: Verify template uses f-string or `.format()` substitution correctly. Check for escaping issues.
**Gate**: Unit test asserting `{canonical_import}` is not in rendered output

### Failure mode 3: LLM ignores canonical_import instruction

**Detection**: Generated .md files still contain wrong import despite correct injection.
**Resolution**: Move `CANONICAL IMPORT` instruction to the very top of the prompt before any other context. Add `CRITICAL:` prefix. Consider adding a post-LLM fix that replaces wrong import with canonical_import.
**Gate**: E2E pilot run — grep for wrong import forms

## Task-specific review checklist

1. [ ] `canonical_import` read from understand bundle in section_prompt.py
2. [ ] `canonical_import` appears verbatim in rendered section prompt — confirmed by test
3. [ ] section_writer.txt has explicit "Use exactly `import {canonical_import}`" instruction
4. [ ] Unit test: Python canonical_import injected correctly
5. [ ] Unit test: Missing canonical_import handled gracefully (no crash)
6. [ ] Unit test: `{canonical_import}` placeholder not in final rendered string
7. [ ] Docstrings updated for modified functions in section_prompt.py
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/generate/section_prompt.py` — canonical_import injection
2. `src/launcher/prompts/section_writer.txt` — placeholder and instruction added
3. `tests/unit/workers/generate/` — 3 new test cases
4. `reports/TC-4227/evidence.md` — grep output showing zero wrong imports in pilot run

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v`
2. [ ] `canonical_import` present in every section prompt — verified by log/test
3. [ ] Pilot run: zero `import aspose.cells` violations (wrong form) in generated drafts

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: canonical_import injection PASS
- [ ] Evidence captured: reports/TC-4227/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- canonical_import injection tests pass
- No regressions in existing generate tests

## Integration boundary proven

**Upstream**: Understand bundle — provides `canonical_import` field
**Downstream**: LLM section writer — receives prompt with canonical_import instruction
**Contract**: Every section prompt contains verbatim `canonical_import` from understand bundle
