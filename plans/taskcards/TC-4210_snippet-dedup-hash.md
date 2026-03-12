---
id: TC-4210
title: "Snippet dedup — full SHA-256 hash instead of code[:200] prefix"
status: Done
priority: Normal
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [understand, snippets, dedup]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4210_snippet-dedup-hash.md
  - src/launcher/workers/understand/extract/_llm.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/wave1/TC-4210/evidence.md
evidence_required:
  - reports/agents/wave1/TC-4210/evidence.md
---

# Taskcard TC-4210 — Snippet dedup — full SHA-256 hash instead of code[:200] prefix

## Objective

Replace the `code[:200]` deduplication key in `_build_snippet_context` with a full
SHA-256 hash of the snippet body. This prevents two long snippets that share an
identical first 200 characters but differ beyond that from being incorrectly
treated as duplicates, which silently drops valid unique code examples.

## Required spec references

- `specs/worker_understand.md` (Section: Snippet handling and deduplication)

## Scope

### In scope
- Replace `key = s.code[:200]` with `key = hashlib.sha256(s.code.encode()).hexdigest()` in `_build_snippet_context`
- Add `import hashlib` at module top if not already present
- Unit tests covering: same-prefix-different-body, exact-dupe, fully-different

### Out of scope
- Changes to how snippets are extracted or stored
- Any change to `_SNIPPET_SAMPLE_MAX` or `_SNIPPET_CHAR_BUDGET`

## Inputs

- `src/launcher/workers/understand/extract/_llm.py` (current implementation)

## Outputs

- `src/launcher/workers/understand/extract/_llm.py` (patched)
- `tests/unit/workers/understand/test_extract.py` (new tests for TC-4210)
- `reports/agents/wave1/TC-4210/evidence.md`

## Allowed paths

- plans/taskcards/TC-4210_snippet-dedup-hash.md
- src/launcher/workers/understand/extract/_llm.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/wave1/TC-4210/evidence.md

### Allowed paths rationale
- `_llm.py`: site of the bug
- `test_extract.py`: existing test file for understand extraction logic
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Add hashlib import

In `_llm.py`, confirm `import hashlib` is present at the top. Add it if missing.

### Step 2: Replace dedup key

Change line 38:
```python
key = s.code[:200]  # dedup by first 200 chars
```
to:
```python
key = hashlib.sha256(s.code.encode()).hexdigest()
```

### Step 3: Write tests in test_extract.py

Add a `TestSnippetDedup` class with three tests:
- `test_same_prefix_different_body_both_survive`: snippets sharing first 200 chars but differing beyond → 2 selected
- `test_exact_duplicate_deduplicated`: identical snippets → 1 selected
- `test_fully_different_snippets_both_survive`: completely different snippets → 2 selected

## Failure modes

### Failure mode 1: hashlib not imported

**Detection**: `NameError: name 'hashlib' is not defined` at runtime
**Resolution**: Add `import hashlib` to the module-level imports
**Gate**: Unit test `test_same_prefix_different_body_both_survive` will fail

### Failure mode 2: encode() fails for non-ASCII snippet content

**Detection**: `UnicodeEncodeError` or `AttributeError`
**Resolution**: `s.code.encode()` defaults to UTF-8; use `s.code.encode("utf-8", errors="replace")` if necessary
**Gate**: `test_fully_different_snippets_both_survive` with unicode content

### Failure mode 3: SHA-256 produces collisions (extremely unlikely, but verify logic)

**Detection**: Two different snippets map to same hash (not feasible in practice)
**Resolution**: No mitigation needed; SHA-256 collision probability is negligible
**Gate**: Test with large set of snippets; all unique snippets remain after dedup

## Task-specific review checklist

1. [ ] `import hashlib` present at module top in `_llm.py`
2. [ ] `key = s.code[:200]` line is replaced with SHA-256 hash
3. [ ] Comment updated to reflect new dedup strategy
4. [ ] Three new tests present: same-prefix, exact-dupe, different
5. [ ] All three tests pass with `PYTHONHASHSEED=0`
6. [ ] No regression in existing `test_extract.py` tests
7. [ ] Docstrings updated for `_build_snippet_context`
8. [ ] Spec file confirmed — no drift introduced
9. [ ] Schema `"description"` fields — not applicable (no schema change)
10. [ ] `docs/README.md` ownership map checked — no guide update needed
11. [ ] No new `docs/guides/` file added

## Deliverables

1. Patched `src/launcher/workers/understand/extract/_llm.py`
2. Updated `tests/unit/workers/understand/test_extract.py` with three new tests
3. `reports/agents/wave1/TC-4210/evidence.md`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -v` passes
2. [ ] `TestSnippetDedup` class has 3 passing tests
3. [ ] `_build_snippet_context` no longer references `s.code[:200]`

## Self-review

### Verification results
- [ ] Tests: 3/3 PASS (TestSnippetDedup)
- [ ] Validation: dedup logic correct
- [ ] Evidence captured: reports/agents/wave1/TC-4210/evidence.md
- [ ] Doc freshness: no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -v
```

**Expected results**:
- All TestSnippetDedup tests pass
- No regressions in existing tests

## Integration boundary proven

**Upstream**: Snippet extraction produces `list[Snippet]` objects
**Downstream**: `_build_snippet_context` returns a deduped code block string for the LLM prompt
**Contract**: Unique snippets (by full body hash) all survive; exact duplicates are collapsed to one
