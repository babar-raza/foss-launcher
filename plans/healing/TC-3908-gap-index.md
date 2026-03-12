# TC-3908 Post-Implementation Gap Index

Source: self-review performed after TC-3908 completion (2026-03-09).

## Gap Table

| Gap ID | Severity | Description | Taskcard(s) |
|--------|----------|-------------|-------------|
| EX-01 | Critical | `_decompose_code_block_into_steps` defined in `_snippets.py` but never called — dead code | TC-3908-H1 |
| EX-02 | Critical | `_extract_error_messages` defined in `_deterministic.py` but never called; returns `list[dict]` (v1 format), not `list[Claim]` (v2 Pydantic) | TC-3908-H2 |
| EX-03 | High | Zero unit tests for all 4 ported deterministic functions | TC-3908-H3 |
| EX-04 | Medium | `_snippets.py` at 825 lines violates 600-line submodule limit | TC-3908-H4 |
| EX-05 | Medium | `shared/extract_claims.py` compat shim imports from `workers/understand/extract/_filters.py`, reversing the normal `shared/` ← `workers/` dependency direction | TC-3908-H5 |
| EX-06 | Low | Missing TC-3908 governance deliverables: `reports/agents/B/TC-3908/plan.md`, `changes.md`; `_filters.py` and `promoter.py` changes lack formal AG-002 cover | TC-3908-H6 |

## Dependency order

```
TC-3908-H2  (fix _extract_error_messages return type)
    └── TC-3908-H1  (wire dead code into pipeline — needs correct types first)
            └── TC-3908-H3  (unit tests — needs callable functions)
TC-3908-H4  (split _snippets.py — independent)
TC-3908-H5  (relocate classify_claim_visibility — independent)
TC-3908-H6  (governance trail — independent)
```

## Files modified by these taskcards

| File | Taskcards |
|------|-----------|
| `src/launcher/workers/understand/extract/_deterministic.py` | TC-3908-H2, TC-3908-H1 |
| `src/launcher/workers/understand/extract/_snippets.py` | TC-3908-H1, TC-3908-H4 |
| `src/launcher/workers/understand/extract/_narratives.py` (new) | TC-3908-H4 |
| `src/launcher/workers/understand/extract/__init__.py` | TC-3908-H4, TC-3908-H5 |
| `src/launcher/shared/classify_claims.py` | TC-3908-H5 |
| `src/launcher/shared/extract_claims.py` | TC-3908-H5 |
| `src/launcher/workers/understand/extract/_filters.py` | TC-3908-H5 |
| `tests/unit/workers/understand/extract/test_ported_functions.py` (new) | TC-3908-H3 |
| `reports/agents/B/TC-3908/plan.md` | TC-3908-H6 |
| `reports/agents/B/TC-3908/changes.md` | TC-3908-H6 |
