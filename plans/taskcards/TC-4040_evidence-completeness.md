---
id: TC-4040
title: "Evidence completeness: wire format_matrix into ProductEvidence"
status: Done
priority: Critical
owner: "orchestrator"
updated: "2026-03-11"
tags: [understand, evidence, format_matrix, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4040_evidence-completeness.md
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand_product_evidence.py
evidence_required:
  - reports/TC-4040/evidence.md
---

# Taskcard TC-4040 — Evidence completeness: wire format_matrix into ProductEvidence

## Objective

Wire `_format_matrix` (AST-extracted `FormatRecord` list) into `ProductEvidence` at the
extract phase, and update the worker.py merge step to prefer extract-level format lists
over repo-level format lists. This ensures downstream `section_prompt.py` receives
concrete format facts (OBJ, FBX, GLTF) rather than empty lists.

## Required spec references

- `specs/worker_understand.md` (Evidence extraction pipeline)
- `specs/system_contract.md` (Worker input/output contracts)

## Scope

### In scope
- `_entry.py`: Add `supported_formats`, `input_formats`, `output_formats` from `_format_matrix` to `ProductEvidence` assembly
- `worker.py`: Update merge step to prefer `extract_evidence` format lists over `repo_evidence` format lists

### Out of scope
- Changes to `section_prompt.py` (TC-4041)
- Changes to `ProductEvidence` model (fields already exist)
- Changes to `extract_format_matrix()` logic (already works correctly)

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` (lines 88-96: format_matrix extraction, lines 234-240: ProductEvidence assembly)
- `src/launcher/workers/understand/worker.py` (lines 137-141: merge step)
- `src/launcher/models/product.py` (`FormatRecord` with `name`, `can_import`, `can_export`)
- `src/launcher/models/understanding.py` (`ProductEvidence` with `supported_formats`, `input_formats`, `output_formats`)

## Outputs

- Modified `_entry.py`: ProductEvidence includes format lists from `_format_matrix`
- Modified `worker.py`: merge step prefers extract-level format lists
- Passing tests in `tests/unit/workers/test_understand_product_evidence.py`

## Allowed paths

- `plans/taskcards/TC-4040_evidence-completeness.md`
- `src/launcher/workers/understand/extract/_entry.py`
- `src/launcher/workers/understand/worker.py`
- `tests/unit/workers/test_understand_product_evidence.py`

### Allowed paths rationale
Both source files are in the understand worker pipeline. The test file already exists
and covers ProductEvidence; we extend it with format-specific assertions.

## Implementation steps

### Step 1: Verify current state in _entry.py

Read `src/launcher/workers/understand/extract/_entry.py` lines 234-240. Confirm that
`ProductEvidence` does NOT yet include `supported_formats`, `input_formats`, `output_formats`.
Expected: only `limitations`, `workflow_examples`, `install_recipe`, `missing_info`, `confidence`.

### Step 2: Add format_matrix fields to ProductEvidence in _entry.py

In the ProductEvidence assembly block (around line 234), extend the constructor to
include format lists derived from `_format_matrix`:

```python
product_evidence = ProductEvidence(
    limitations=limitations,
    workflow_examples=workflow_examples,
    install_recipe=install_recipe,
    missing_info=_missing_info,
    confidence=_confidence,
    supported_formats=[fr.name for fr in _format_matrix if fr.can_import or fr.can_export],
    input_formats=[fr.name for fr in _format_matrix if fr.can_import],
    output_formats=[fr.name for fr in _format_matrix if fr.can_export],
)
```

Note: `_format_matrix` is already in scope at this point (set at line 88-96). No import changes needed.

### Step 3: Verify current state in worker.py

Read `src/launcher/workers/understand/worker.py` lines 137-141. Confirm the merge step
does NOT yet include format list fields in the `model_copy(update={...})` call.

### Step 4: Update merge step in worker.py

Extend the `model_copy(update={...})` call at lines 137-141 to prefer extract_evidence
format lists (AST-verified from test files) over repo_evidence format lists (from code_analyzer):

```python
product_evidence = repo_evidence.model_copy(update={
    "limitations": extract_evidence.limitations,
    "workflow_examples": extract_evidence.workflow_examples,
    "install_recipe": extract_evidence.install_recipe or repo_evidence.install_recipe,
    "supported_formats": extract_evidence.supported_formats or repo_evidence.supported_formats,
    "input_formats": extract_evidence.input_formats or repo_evidence.input_formats,
    "output_formats": extract_evidence.output_formats or repo_evidence.output_formats,
})
```

Logic: prefer extract_evidence (non-empty wins); fall back to repo_evidence if extract produces empty.

### Step 5: Run targeted tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand_product_evidence.py -v
```

### Step 6: Run full test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

Confirm 0 regressions.

## Failure modes

### Failure mode 1: _format_matrix is empty (no formats extracted)

**Detection**: `product_evidence.supported_formats == []` after merge, even though repo_evidence had formats
**Resolution**: The `or` logic in the merge step falls back to `repo_evidence.supported_formats` when `extract_evidence.supported_formats` is empty. No change needed — this is the correct behavior.
**Gate**: Unit test asserting fallback works when extract list is empty.

### Failure mode 2: FormatRecord fields renamed or missing

**Detection**: `AttributeError: 'FormatRecord' object has no attribute 'can_import'`
**Resolution**: Read `src/launcher/models/product.py` to get current field names. FormatRecord has: `name`, `can_import`, `can_export`, `caveats`, `test_count`, `source_evidence`.
**Gate**: Verify grep confirms field names before writing code.

### Failure mode 3: ProductEvidence model does not accept format fields

**Detection**: `ValidationError: supported_formats field missing` or similar pydantic error
**Resolution**: Fields `supported_formats`, `input_formats`, `output_formats` already exist in `ProductEvidence` (lines 149-151 of `understanding.py`). If test fails with validation error, re-read model.
**Gate**: Model field grep before implementation.

## Task-specific review checklist

1. [ ] `_entry.py` ProductEvidence includes `supported_formats`, `input_formats`, `output_formats`
2. [ ] List comprehensions use correct `FormatRecord` field names (`fr.name`, `fr.can_import`, `fr.can_export`)
3. [ ] `worker.py` merge step includes all three format fields with `or` fallback logic
4. [ ] Merge step does NOT remove any existing fields (`limitations`, `workflow_examples`, `install_recipe`)
5. [ ] `_format_matrix` is in scope at the ProductEvidence assembly point (no NameError)
6. [ ] Empty `_format_matrix` falls back to repo_evidence format lists (not empty list)
7. [ ] Docstrings updated for changed code blocks
8. [ ] Spec file confirmed — no spec drift from this change
9. [ ] Schema `"description"` fields present where applicable
10. [ ] Checked `docs/README.md` — no ownership map trigger
11. [ ] Existing tests not broken by format list addition

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_entry.py`
2. Modified `src/launcher/workers/understand/worker.py`
3. `reports/TC-4040/evidence.md` with test output

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 pytest tests/unit/workers/test_understand_product_evidence.py` — all pass
2. [ ] `PYTHONHASHSEED=0 pytest tests/ -x -q` — 0 regressions
3. [ ] `grep "supported_formats" src/launcher/workers/understand/extract/_entry.py` — present
4. [ ] `grep "supported_formats.*extract_evidence" src/launcher/workers/understand/worker.py` — present

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: `reports/TC-4040/evidence.md`
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand_product_evidence.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All existing understand product evidence tests pass
- No regressions across full suite

## Integration boundary proven

**Upstream**: `extract_format_matrix()` in `_deterministic.py` provides `list[FormatRecord]`
**Downstream**: `section_prompt.py` receives `product_evidence.supported_formats` (via TC-4041)
**Contract**: `ProductEvidence.supported_formats: list[str]` — display names of readable/writable formats
