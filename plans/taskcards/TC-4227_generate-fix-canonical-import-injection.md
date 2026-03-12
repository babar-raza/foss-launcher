---
id: TC-4227
title: "G-1: Fix canonical_import injection in section prompt"
status: Done
priority: High
owner: "agent"
updated: "2026-03-12"
tags: [generate, canonical-import, prompt]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4227_generate-fix-canonical-import-injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - reports/TC-4227/evidence.md
---

# Taskcard TC-4227 — G-1: Fix canonical_import injection in section prompt

## Objective

Strengthen the canonical import instruction in the section writer prompt so the LLM consistently uses `import aspose_cells_foss` instead of `import aspose.cells`. The understand bundle already carries the correct `canonical_import` but the prompt does not make it prominent enough to override the LLM's world-knowledge bias.

## Required spec references

- `specs/worker_generate.md` (Section: Section prompt construction, canonical import enforcement)
- `specs/system_contract.md` (Section: Engineering sandwich model — post-LLM normalization)

## Scope

### In scope
- Add a `CANONICAL IMPORT` block near the top of the prompt template so it appears before any code instructions
- Add a `NEVER` rule explicitly naming the wrong import path alongside the correct one
- Ensure `runtime_import` (which is used as `code_import` in `build_section_prompt`) is the value being injected

### Out of scope
- Changes to `_sanitize_code_blocks` (already corrects wrong imports post-LLM)
- Changes to the understand worker (already extracts canonical_import correctly)
- Any other workers or files

## Inputs

- `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt` function, line ~931 where `code_import` is computed
- `src/launcher/prompts/section_writer.txt` — the STRICT RULES block (lines 31-51)

## Outputs

- Modified `section_writer.txt` with a stronger canonical-import rule near the top of STRICT RULES
- Modified `section_prompt.py` to inject a pre-template CANONICAL IMPORT block as a prepended section

## Allowed paths

- plans/taskcards/TC-4227_generate-fix-canonical-import-injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt

### Allowed paths rationale
The fix lives entirely in the prompt template and the function that builds it. No model or schema changes are required.

## Implementation steps

### Step 1: Strengthen the STRICT RULES in section_writer.txt

In the STRICT RULES block, replace the existing two import-related rules (lines 32-33) with a combined, more prominent rule that includes a NEVER clause with the specific wrong import pattern. Add a `CANONICAL IMPORT` heading line just below the CONTEXT block to front-load the instruction.

### Step 2: Inject canonical import block in build_section_prompt

After the template `result = template.format(...)` call in `section_prompt.py` (~line 959), prepend a CANONICAL IMPORT reminder block so it appears at the absolute top of the final prompt string. This block states the exact import to use and the exact wrong import to never use.

### Step 3: Verify tests pass

Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_prompt.py tests/unit/workers/generate/ -x -q`.

## Failure modes

### Failure mode 1: Template format key collision

**Detection**: `KeyError` during `template.format(...)` if a new `{placeholder}` is added to section_writer.txt without a matching kwarg in `build_section_prompt`.
**Resolution**: Only add the import warning via Python string prepend (not a template placeholder). Keep template changes to literal text only.
**Gate**: Unit test `test_section_prompt.py` — any `KeyError` surfaces immediately.

### Failure mode 2: runtime_import vs canonical_import mismatch

**Detection**: Generated code still uses wrong import despite fix. Check that `code_import = product.runtime_import or product.canonical_import` is the value used in both the template and the prepend block.
**Resolution**: Verify `product.runtime_import` is set correctly for the pilot. If None, `canonical_import` is the fallback — both point to `aspose_cells_foss`.
**Gate**: Manual inspection of generated `.md` files for `import aspose.cells` occurrences.

### Failure mode 3: Prepended block makes prompt too long

**Detection**: `finish_reason: length` events increase. Check LLM call logs.
**Resolution**: Keep the prepend block under 3 lines (~60 tokens). Do not include API surface in the prepend.
**Gate**: Token budget stays within configured `max_tokens` limit.

## Task-specific review checklist

1. [ ] `section_writer.txt` STRICT RULES has explicit `NEVER use import {wrong} — ALWAYS use import {canonical}` phrasing
2. [ ] `build_section_prompt` injects canonical import block BEFORE the template body so LLM sees it first
3. [ ] The `code_import` variable (runtime_import or canonical_import) is used consistently in both places
4. [ ] No new template `{placeholder}` keys added to section_writer.txt without corresponding kwargs
5. [ ] `_sanitize_code_blocks` post-LLM sanitizer still runs as a backstop (no change required)
6. [ ] Unit tests pass without modification (existing tests should still pass)
7. [ ] Docstrings updated for any changed public functions
8. [ ] Spec file confirmed — no spec drift (generate worker spec not changed)
9. [ ] Schema description fields not impacted (no schema changes)
10. [ ] `docs/README.md` ownership map checked — no guide update required for this fix
11. [ ] No new `docs/guides/` file created

## Deliverables

1. Modified `src/launcher/prompts/section_writer.txt` (stronger STRICT RULES)
2. Modified `src/launcher/workers/generate/section_prompt.py` (prepended canonical import block)

## Acceptance checks

1. [ ] `grep -c "import aspose\." generated_pages/*.md` returns 0 after a pilot run
2. [ ] Unit tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_prompt.py -x -q`
3. [ ] The prompt returned by `build_section_prompt` contains `CANONICAL IMPORT` text at the top

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: section_prompt unit tests PASS
- [ ] Evidence captured: reports/TC-4227/evidence.md
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_section_prompt.py tests/unit/workers/generate/ -x -q
```

**Expected results**:
- All tests pass
- `build_section_prompt` output starts with CANONICAL IMPORT block naming the exact import

## Integration boundary proven

**Upstream**: `UnderstandingBundle.product.canonical_import` (already correct)
**Downstream**: LLM receives the strengthened prompt; `_sanitize_code_blocks` backstop removes any remaining wrong imports
**Contract**: `build_section_prompt` returns a string prompt; LLM processes it; `_sanitize_code_blocks` normalizes code blocks post-LLM
