---
id: SNP-04
title: "Deprecate or document source_type='synthetic' literal on Snippet after TC-4062"
status: Done
priority: Low
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, models, TC-4062, TC-4063]
depends_on: [TC-4062]
allowed_paths:
  - plans/healing/SNP-04-source-type-deprecation.md
  - src/launcher/models/claims.py
evidence_required:
  - reports/SNP-04/evidence.md
---

# SNP-04 — Deprecate or document `source_type='synthetic'` literal on `Snippet`

## Objective

After TC-4062 removed `_generate_synthetic_snippets()`, the `"synthetic"` literal in
`Snippet.source_type: Literal["extracted", "generated", "synthetic"]` has no producer.
This creates a schema/model inconsistency: the value is technically valid Pydantic but
will never appear in production output. The model should document this explicitly to
prevent future confusion and accidental re-introduction of synthetic snippets.

## Required spec references

- `specs/claims_evidence.md` (Snippet model definition)

## Scope

### In scope
- Add an inline comment to the `source_type` field on `Snippet` in `claims.py` clarifying
  that `"synthetic"` has no producer after TC-4062 and is retained for forward-compatibility
  only (to allow loading old bundles that may contain it)
- Option A (preferred): Add a comment only — no model change
  ```python
  source_type: Literal["extracted", "generated", "synthetic"] = "extracted"
  # "synthetic" has no producer after TC-4062; retained for bundle backward-compat only
  ```
- Option B (if team agrees): Remove `"synthetic"` from the Literal — this is a breaking
  change for any bundle that has `source_type="synthetic"`. Only choose this if there are
  no existing bundles with synthetic snippets (e.g., after a full re-run of all pilots).

### Out of scope
- Changing the default value of `source_type`
- Changing the schema JSON in `understanding_bundle.schema.json` (would be a separate TC)
- Searching for and updating all Snippet construction sites (there are none using "synthetic" after TC-4062)

## Inputs

- `src/launcher/models/claims.py` (current `Snippet` model)

## Outputs

- `src/launcher/models/claims.py` with comment on `source_type` field

## Allowed paths

- plans/healing/SNP-04-source-type-deprecation.md
- src/launcher/models/claims.py

### Allowed paths rationale
Only the model file needs the comment. No schema or other file changes.

## Implementation steps

### Step 1: Decide between Option A and Option B

Check whether any existing pilot output bundles or golden files contain `source_type: "synthetic"`:
```bash
grep -r '"source_type".*"synthetic"' golden/ snapshots/ 2>/dev/null || echo "none found"
```

If none found → Option B is safe. If found → use Option A (comment only).

### Step 2A (Option A): Add deprecation comment to `claims.py`

Find the `source_type` line in `Snippet`:
```python
source_type: Literal["extracted", "generated", "synthetic"] = "extracted"
```

Add inline comment:
```python
source_type: Literal["extracted", "generated", "synthetic"] = "extracted"
# TC-4062: "synthetic" has no producer; retained for backward-compat with old bundles
```

### Step 2B (Option B): Remove "synthetic" from Literal

Replace:
```python
source_type: Literal["extracted", "generated", "synthetic"] = "extracted"
```
With:
```python
source_type: Literal["extracted", "generated"] = "extracted"
# TC-4062: "synthetic" removed — _generate_synthetic_snippets() deleted in TC-4062
```

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v -q
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=short
```

If Option B chosen, watch for tests that construct `Snippet(source_type="synthetic")` —
remove those from test files (they test a removed feature).

## Failure modes

### Failure mode 1: Option B breaks existing tests that use source_type="synthetic"

**Detection**: `ValidationError: 'synthetic' is not a valid literal` in tests
**Resolution**: Either switch to Option A, or remove the failing test cases that test
the now-invalid synthetic value
**Gate**: Unit tests

### Failure mode 2: Existing golden bundles contain source_type="synthetic"

**Detection**: `grep` in Step 1 returns matches
**Resolution**: Re-run affected pilots to regenerate bundles, then apply Option B.
Or use Option A (comment only) if re-running is too costly.
**Gate**: Golden file inspection

### Failure mode 3: Comment causes `mypy` or Pydantic introspection failure

**Detection**: Type-check or schema generation fails
**Resolution**: Comments don't affect runtime — if a linter complains, the comment text is
the issue, not the code. Adjust wording.
**Gate**: CI type-check (if configured)

## Task-specific review checklist

1. [ ] `grep` in golden/ and snapshots/ run to inform Option A vs B decision
2. [ ] Comment added (Option A) OR Literal narrowed (Option B) — not both
3. [ ] If Option B: no tests remain that construct `Snippet(source_type="synthetic")`
4. [ ] `Snippet(code="x")` still constructs without error after change
5. [ ] `Snippet(code="x", source_type="extracted")` still constructs without error
6. [ ] Model docstring updated if behavior changes (Option B only)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from model comment change
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/models/claims.py` with `source_type` comment (or narrowed Literal)
2. `reports/SNP-04/evidence.md` with golden search result and rationale for A vs B

## Acceptance checks

1. [ ] `grep "source_type" src/launcher/models/claims.py` shows comment with TC-4062 reference
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v -q` passes
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-04/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v -q
```

**Expected results**:
- All model tests pass
- `Snippet` constructs with default `source_type="extracted"` without errors

## Integration boundary proven

**Upstream**: `_extract_snippets()` — always sets `source_type="extracted"` (no "synthetic" producer)
**Downstream**: `UnderstandingBundle.snippets[*].source_type` in schema validation
**Contract**: `source_type` field retains all three literals (Option A) or narrows to two (Option B); default unchanged
