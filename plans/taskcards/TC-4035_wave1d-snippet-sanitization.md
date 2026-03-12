---
id: TC-4035
title: "Wave 1D: Sanitize snippets pre-injection in section_prompt.py"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-1]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4035_wave1d-snippet-sanitization.md
  - src/launcher/workers/generate/section_prompt.py
evidence_required:
  - reports/TC-4035/evidence.md
---

# Taskcard TC-4035 — Wave 1D: Sanitize snippets pre-injection

## Objective
Snippets extracted from source code may contain HTML entities (`&reg;`, `&trade;`) and cross-language artifacts (`*/`, `using namespace`, `System.`) that appear verbatim in generated content. Sanitize snippets before they enter any code path to eliminate these artifacts.

## Required spec references
- `crispy-growing-pebble.md` Wave 1D

## Scope
### In scope
- In `_format_snippets()` in section_prompt.py: apply `html.unescape()` to snippet code
- Strip C/C# artifacts: lines starting with `*/`, `using namespace`, `System.`
- Tag snippets as `usable` (≥3 non-import/non-blank statements) vs `stub` (fewer) for downstream use

### Out of scope
- Wave 2A stub-code replacement in worker.py (separate TC)
- Snippet extraction logic in understand worker

## Inputs
- `src/launcher/workers/generate/section_prompt.py` — `_format_snippets()` function

## Outputs
- Sanitized snippet code in all prompt-injected code blocks

## Allowed paths
- plans/taskcards/TC-4035_wave1d-snippet-sanitization.md
- src/launcher/workers/generate/section_prompt.py

## Implementation steps
### Step 1: Add `_sanitize_snippet_code()` helper
Add a module-level function that:
1. `html.unescape(code)` — strips `&reg;`, `&trade;`, `&amp;` etc.
2. Strips lines that start with `*/` (C/C++ block comment ends)
3. Strips lines that start with `using namespace` (C++ namespace)
4. Strips lines that start with `System.` (C# artifact)
5. Returns cleaned code string

### Step 2: Apply in `_format_snippets()`
Call `_sanitize_snippet_code(snip.code)` on each snippet's code before it is formatted for inclusion in the prompt.

## Failure modes
### Failure mode 1: Sanitization strips valid Python code
**Detection**: Python code with `System` imports (unlikely but possible) gets stripped
**Resolution**: Restrict to line-start matches (`line.startswith("System.")`) so `system_call()` is safe
**Gate**: All existing snippet formatting tests pass

### Failure mode 2: html.unescape double-decodes already-clean snippets
**Detection**: `&amp;` in code becomes `&` in output
**Resolution**: Desired — HTML entities in code are always artifacts, not intentional in Python/TS code
**Gate**: Test with `&reg;` in fixture → should become plain character

### Failure mode 3: Strip too aggressive removes blank lines
**Detection**: Formatted code loses needed whitespace
**Resolution**: Only strip the specific artifact patterns on a per-line basis, keep blank lines
**Gate**: Spot-check formatted output against fixture

## Task-specific review checklist
1. [ ] `_sanitize_snippet_code()` applies `html.unescape()`
2. [ ] Lines starting with `*/` are stripped
3. [ ] Lines starting with `using namespace` are stripped
4. [ ] Lines starting with `System.` are stripped
5. [ ] `_format_snippets()` calls sanitizer on each snippet
6. [ ] Existing tests pass without modification

## Deliverables
1. Updated `src/launcher/workers/generate/section_prompt.py`

## Acceptance checks
1. [ ] `html.unescape()` applied in `_format_snippets()`
2. [ ] Artifact strip patterns applied
3. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "section_prompt or generate" --tb=short -q
```

## Integration boundary proven
**Upstream**: Understand worker extracts snippets from source files
**Downstream**: `_format_snippets()` output injected into LLM prompt context
**Contract**: Snippet code is a plain string; sanitization is transparent to callers
