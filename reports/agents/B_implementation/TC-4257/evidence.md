# TC-4257 Evidence — Scout evidence pipeline hardening

**Date**: 2026-03-13
**Verified by**: Orchestrator agent (code inspection + unit test run)

---

## Acceptance Check 1: Cells Scout retains real example evidence

**Status: PASS**

`file_classifier.py` (lines 241-244) gives explicit precedence to `examples/` directory
over filename-level `test_` markers:

```python
if example_dir_index is not None and (
    test_dir_index is None or example_dir_index <= test_dir_index
):
    return FileCategory.example
```

Test assertion from `tests/unit/workers/test_scout.py`:
```
TestScoutEvidenceSelection::test_run_scout_excludes_meta_docs_and_keeps_example_test_files — PASS
```

Phase store confirms 31 example files in Cells pilot (`phase_store/cells/python/scout.json`):
```json
{
  "by_category": {
    "example": 31,
    ...
  },
  "has_examples_folder": true
}
```

---

## Acceptance Check 2: 3D Scout no longer surfaces operator/meta docs

**Status: PASS**

`scout.py` (lines 331-343) defines `_doc_skip_reason()` which excludes meta/operator
docs by exact name and root keyword:

```python
_META_DOC_EXACT_NAMES = frozenset({
    "agents.md", "claude.md", "copilot-instructions.md",
    "llms.md", "third_party_notices.md"
})
_META_DOC_ROOT_KEYWORDS = frozenset({
    "readiness", "implementation", "summary", "status",
    "backlog", "roadmap", "plan", "notes"
})
```

`AGENTS.md`, `PYPI_READINESS.md` and implementation summary docs are excluded by this filter.

Test assertion:
```
TestScoutEvidenceSelection::test_meta_docs_excluded_from_scout — PASS
```

---

## Acceptance Check 3: scout_inventory.json present after --stop-after scout

**Status: PASS**

`src/launcher/workers/scout/worker.py` (line 87) writes the artifact:
```python
context.store.write_json("scout_inventory.json", scout_inventory)
```

`build_scout_inventory()` (scout.py lines 149-206) populates the artifact with
kept/skipped decisions, file categories, budget log, and reasons.

Test assertion:
```
TestScoutInventoryArtifact::test_scout_inventory_written_after_scout — PASS
```

---

## Acceptance Check 4: scout_checkpoint.json and scout_inventory.json expose decisions

**Status: PASS**

`build_scout_inventory()` returns a dict containing:
- `doc_paths`: selected product documents with reasons
- `example_paths`: selected example files
- `skipped_paths`: excluded files with skip reason and category
- `budget_log`: per-file budget tracking

Test asserts inventory contains `skipped_paths` with per-entry `reason` field:
```
TestScoutInventoryArtifact::test_inventory_contains_skipped_paths_with_reasons — PASS
```

---

## Acceptance Check 5: Scout self-review fails deliberately polluted/starved fixtures

**Status: PASS**

`worker.py` self-review (lines 181-211) defines HIGH-severity rules:
- Meta doc selected as product doc → HIGH severity failure
- Example-heavy repo retains zero example evidence → HIGH severity failure

Test assertion:
```
TestScoutSelfReview::test_self_review_fails_on_polluted_doc_selection — PASS
TestScoutSelfReview::test_self_review_fails_on_example_starvation — PASS
```

---

## Acceptance Check 6: Regression tests pass with PYTHONHASHSEED=0

**Status: PASS**

Full unit test run (2026-03-13):
```
tests/unit/workers/test_scout.py — 45 passed
```

Command:
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py -q
```

---

## Implementation summary

All 5 code steps were found to be already implemented in the codebase:

| Step | File | Status |
|------|------|--------|
| Fix file classification precedence | `file_classifier.py` L241-244 | Done |
| Add doc eligibility filtering | `scout.py` `_doc_skip_reason()` | Done |
| Emit `scout_inventory.json` artifact | `worker.py` L87 | Done |
| Strengthen Scout self-review | `worker.py` L181-211 | Done |
| Repair boundary contract | `scout_bundle.schema.json` + `graph_builder.py` | Done |
