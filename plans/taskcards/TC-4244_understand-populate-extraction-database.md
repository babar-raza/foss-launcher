---
id: TC-4244
title: "Populate ExtractionDatabase from api_surface, format_matrix, snippets, limitations"
status: Done
priority: P0
owner: "B_implementation"
updated: "2026-03-12"
tags: ["understand", "extraction-database", "wiring"]
depends_on: ["TC-4241", "TC-4242"]
allowed_paths:
  - plans/taskcards/TC-4244_understand-populate-extraction-database.md
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_snippets.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B_implementation/TC-4244/evidence.md
  - reports/agents/B_implementation/TC-4244/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4244/evidence.md
---

## Objective

Wire the ExtractionDatabase (added in TC-4242) with real data from existing
extraction functions. After this task, `understanding_bundle.extraction_db`
will contain real ApiFact, FormatFact, SnippetFact, and LimitationFact records
whenever Understand runs.

## Required spec references

- specs/worker_understand.md
- specs/schemas/understanding_bundle.schema.json

## Scope In

- Add 5 helper functions to `_entry.py`: `_build_api_facts`, `_build_format_facts`,
  `_build_snippet_facts`, `_build_limitation_facts`, `_compute_extraction_completeness`
- Wire `ExtractionDatabase` assembly into `run_extract()`
- Change `run_extract()` return type from 4-tuple to 5-tuple
- Update `worker.py` call site to unpack 5 values and pass `extraction_db` to `UnderstandingBundle`

## Scope Out

- No changes to `_extract_api_surface()`, `extract_format_matrix()`, `_extract_snippets()`,
  `extract_limitations()` function signatures
- No changes to LLM prompts
- No schema changes

## Implementation steps

1. Create this taskcard (Done)
2. Add helper functions to `_entry.py` before `run_extract()`
3. Add `ExtractionDatabase` assembly block in `run_extract()` before the return
4. Change return from 4-tuple to 5-tuple
5. Update `worker.py` call site (unpack 5 values, pass `extraction_db` to bundle)
6. Run targeted tests
7. Run full test suite
8. Write evidence and self-review

## Failure modes

1. Circular import: `ExtractionDatabase` import causes circular dependency — mitigate by
   importing inside helper function bodies
2. AttributeError on ClassBrief fields: typed_methods/typed_properties may not exist on
   all adapter outputs — mitigate by using `getattr(..., [])` fallback
3. Call site mismatch: `worker.py` unpacks 4 values from 5-tuple — mitigated by searching
   ALL call sites before editing
4. None product_evidence: limitations access crashes if `product_evidence` is None —
   mitigated by guarding with `if product_evidence else []`
5. Empty format_matrix: `api_surface.format_matrix` may be None — mitigated by using
   `or []` fallback

## Task-specific review checklist

- [ ] All 5 helper functions added before `run_extract()`
- [ ] `ExtractionDatabase` import at top of `_entry.py` (not inside helpers)
- [ ] `run_extract()` return is 5-tuple
- [ ] `worker.py` call site updated to unpack 5 values
- [ ] `UnderstandingBundle(extraction_db=extraction_db)` added to bundle construction
- [ ] `ExtractionDatabase` fields never None (use `[]` defaults)
- [ ] Tests pass: `test_understand.py`, `test_extract.py`, integration

## Deliverables

- Modified `_entry.py` with 5 helpers + 5-tuple return
- Modified `worker.py` with updated call site and bundle field
- `reports/agents/B_implementation/TC-4244/evidence.md`

## Acceptance checks

- [ ] `run_extract()` returns 5-tuple `(claims, snippets, api_surface, product_evidence, extraction_db)`
- [ ] `UnderstandingBundle.extraction_db` is populated (not default empty) when API surface has classes
- [ ] `ExtractionDatabase.api_facts` count > 0 in test scenarios with classes
- [ ] Tests pass: `test_understand.py` + `test_extract.py` + integration
- [ ] Full suite passes (ignoring known-skipped tests)

## Self-review

Completed after implementation — see `reports/agents/B_implementation/TC-4244/self_review.md`.

## E2E verification

Run full test suite with `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no`
and confirm no regressions.

## Integration boundary proven

`worker.py` call site updated to unpack 5-tuple and pass `extraction_db` to bundle.
