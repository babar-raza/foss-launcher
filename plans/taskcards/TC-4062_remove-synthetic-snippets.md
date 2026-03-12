---
id: TC-4062
title: "Remove _generate_synthetic_snippets() — stop injecting fabricated evidence"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, quality, evidence]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4062_remove-synthetic-snippets.md
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/extract/__init__.py
  - tests/unit/workers/understand/test_extract.py
evidence_required:
  - reports/TC-4062/evidence.md
---

# Taskcard TC-4062 — Remove `_generate_synthetic_snippets()`

## Objective

Remove the template-based synthetic snippet generator from the Understand worker.
It synthesizes `obj.method()` calls without understanding required arguments, producing
semantically wrong code that passes AST validation but misleads downstream generation.
An external review explicitly flagged this as "not safe as downstream evidence."

## Required spec references

- `specs/worker_understand.md` (Phase B.3: snippet extraction — must be evidence-grounded)
- `specs/claims_evidence.md` (Snippet model: source_type values)

## Scope

### In scope
- Remove `_generate_synthetic_snippets()` function from `_entry.py`
- Remove the call site that invokes it (Phase B.5 fallback block)
- Remove its export from `extract/__init__.py`
- Remove all unit tests that test this function directly

### Out of scope
- LLM-based fallback generation (not replacing — trusting existing "EVIDENCE ABSENT" path)
- Changes to `Snippet.source_type` — keeping `"synthetic"` for forward-compat
- Planner or generate worker changes

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` (current state with synthetic generator)
- `src/launcher/workers/understand/extract/__init__.py` (exports the function)
- `tests/unit/workers/understand/test_extract.py` (tests for synthetic generation)

## Outputs

- `_entry.py` without `_generate_synthetic_snippets()` and without the Phase B.5 fallback block
- `__init__.py` without the `_generate_synthetic_snippets` export
- `test_extract.py` without `TestSyntheticSnippetGeneration` and `TestSyntheticSnippetImportPath` classes

## Allowed paths

- plans/taskcards/TC-4062_remove-synthetic-snippets.md
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/extract/__init__.py
- tests/unit/workers/understand/test_extract.py

### Allowed paths rationale
Only files that directly contain the function, its export, or its tests.

## Implementation steps

### Step 1: Remove call site in `_entry.py` (Phase B.5 fallback block)

Remove lines 210-227 (the `if len(snippets) < target_snippet_count:` block).
Keep line 208 (`snippets = _extract_snippets(...)`) intact.

### Step 2: Remove the function body in `_entry.py`

Remove the entire B.3b section comment block and `_generate_synthetic_snippets()`
function (lines 402-494).

Remove from module docstring (lines 6):
`  _generate_synthetic_snippets   — template-based snippet synthesis (TC-3816)`

### Step 3: Remove export from `__init__.py`

Remove `_generate_synthetic_snippets,` from the import in `extract/__init__.py`.

### Step 4: Remove tests from `test_extract.py`

Remove `TestSyntheticSnippetGeneration` class and `TestSyntheticSnippetImportPath` class.

## Failure modes

### Failure mode 1: Other code imports `_generate_synthetic_snippets`

**Detection**: `grep -r "_generate_synthetic_snippets"` shows hits outside `_entry.py`
**Resolution**: Remove those import sites too; `_generate_synthetic_snippets` has no
legitimate callers after this TC
**Gate**: Import error on module load

### Failure mode 2: Tests fail due to test referencing removed function

**Detection**: `pytest tests/unit/workers/understand/test_extract.py` → ImportError
**Resolution**: Remove all test cases that import `_generate_synthetic_snippets`
**Gate**: Test suite

### Failure mode 3: Pages that relied on synthetic snippets now have zero snippets

**Detection**: Evaluate gate `structure.py:306-311` raises findings for code-required roles
**Resolution**: This is the CORRECT behavior — those pages should be flagged and healed.
The synthetic snippets were masking this gap. No fix needed here.
**Gate**: structure check in Evaluate worker

## Task-specific review checklist

1. [ ] `grep -r "_generate_synthetic_snippets" src/` returns no matches
2. [ ] `grep -r "_generate_synthetic_snippets" tests/` returns no matches
3. [ ] `grep "source_type.*synthetic" tests/` returns no matches (synthetic test data gone)
4. [ ] `_extract_snippets()` call in `_entry.py` is still present and unchanged
5. [ ] `run_extract()` function signature and return type unchanged
6. [ ] `__init__.py` still exports `_harvest_docstring_claims_raw` and `_build_evidence_context`
7. Docstrings updated for all new/changed public functions
8. Spec file updated if worker behavior changed (or confirmed no spec drift)
9. Schema `"description"` fields present for all new/changed properties
10. Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_entry.py`
2. Modified `src/launcher/workers/understand/extract/__init__.py`
3. Modified `tests/unit/workers/understand/test_extract.py`

## Acceptance checks

1. [ ] `grep -r "_generate_synthetic_snippets" src/ tests/` → no matches
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v` passes
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-4062/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=short
```

**Expected results**:
- No `TestSyntheticSnippetGeneration` or `TestSyntheticSnippetImportPath` test classes
- All remaining tests pass

## Integration boundary proven

**Upstream**: `_extract_snippets()` returns `list[Snippet]` (unchanged)
**Downstream**: `UnderstandingBundle.snippets` — will no longer contain `source_type="synthetic"` entries
**Contract**: `Snippet` model unchanged; `source_type: "synthetic"` literal remains valid for forward-compat
