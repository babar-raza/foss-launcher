# Chat-Derived Plan: Decompose workers/understand/extract.py

**Created**: 2026-03-09
**Slug**: decompose-extract-py
**TC**: TC-3908

## Context

Planning conversation identified that `src/launcher/shared/extract_claims.py`
(4,804 lines) is an orphaned v1 migration with zero importers. The actual v2
claim extraction lives in `src/launcher/workers/understand/extract.py` (2,023 lines,
ACTIVE, WorkerContract-compliant, fully Pydantic, async).

Decision: decompose `extract.py` into a package, port 4 deterministic helper
functions from the orphan, then delete the orphan.

## Goals

1. Split `workers/understand/extract.py` into a focused 6-submodule package
2. Port 4 valuable deterministic functions from orphan `shared/extract_claims.py`
3. Delete orphan `shared/extract_claims.py`
4. Keep public API identical (`run_extract()` import path unchanged)

## Assumptions

- [VERIFIED] `shared/extract_claims.py` has zero importers in v2
- [VERIFIED] `workers/understand/extract.py` is WorkerContract-compliant, Pydantic, async
- [VERIFIED] `workers/understand/worker.py` imports `from launcher.workers.understand.extract import run_extract`
- [VERIFIED] Claim extraction is exclusively the Understand worker's responsibility
- [UNVERIFIED] Test suite covers `extract.py` functionality sufficiently to detect regressions

## Steps

### Phase 0: Governance
1. Create TC-3908 taskcard with all 14 sections, status In-Progress

### Phase 1: Scaffold (no functional change)
2. Run baseline tests, record counts
3. `mkdir src/launcher/workers/understand/extract/`
4. Copy monolith → `extract/_impl.py`
5. Create transitional `__init__.py` that re-exports `run_extract`
6. Delete `src/launcher/workers/understand/extract.py`
7. Run tests — must match baseline

### Phase 2: Extract submodules (test after each)
8. Extract `_api_surface.py` → run tests
9. Extract `_deterministic.py` + port `_extract_error_messages` → run tests
10. Extract `_validation.py` → run tests
11. Extract `_llm.py` → run tests
12. Extract `_linking.py` → run tests
13. Extract `_snippets.py` + port 3 orphan functions → run tests

### Phase 3: Clean-up
14. Verify `_impl.py` is empty
15. Delete `_impl.py`
16. Rewrite `__init__.py` with explicit named imports
17. Delete `src/launcher/shared/extract_claims.py`
18. Full test suite run

### Phase 4: Verification
19. Import smoke test
20. Static analysis (`py_compile`)
21. Grep for stale import references
22. Doc freshness check
23. Self-review (AG-020)

## Acceptance Criteria

- [ ] Tests pass with same count as baseline
- [ ] `from launcher.workers.understand.extract import run_extract` works
- [ ] `src/launcher/workers/understand/extract.py` does not exist
- [ ] `src/launcher/shared/extract_claims.py` does not exist
- [ ] 7 files under `src/launcher/workers/understand/extract/`
- [ ] No submodule exceeds 600 lines
- [ ] `py_compile *.py` exits 0
- [ ] Zero grep results for `shared.extract_claims`

## Risks + Rollback

- **Risk**: Test failures due to missed internal cross-references
  - **Rollback**: `git checkout src/launcher/workers/understand/extract.py`
- **Risk**: Circular imports between submodules
  - **Fix**: Resolve by moving shared constants to `_core.py`

## Evidence Commands

```bash
# Baseline
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5

# Smoke test
python -c "from launcher.workers.understand.extract import run_extract; print('OK')"

# Static analysis
python -m py_compile src/launcher/workers/understand/extract/*.py

# Stale import check
grep -r "shared.extract_claims" src/ tests/

# File existence
ls src/launcher/workers/understand/extract/
```

## Open Questions

(empty — all resolved in planning)
