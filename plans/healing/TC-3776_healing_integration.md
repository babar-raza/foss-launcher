# TC-3776 Healing: Integration Testing & Resume Resilience

## Context

TC-3776 moved cloning to Intake and all 933 unit tests pass, but there is
no integration test that verifies the Intake → Understand data flow
end-to-end through the graph builder, and no handling for the case where
a run is resumed from "understand" but the cached clone directory has been
cleaned between runs.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-04 | No integration test for Intake → Understand data flow | IT-01 |
| G-06 | Resume-from with stale repo_dir — checkpoint load succeeds but repo_dir gone | IT-01 |

---

## Taskcard IT-01: Integration test + resume-from resilience

**Status:** Not Started
**Gap linkage:** G-04, G-06
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Create `tests/integration/test_intake_understand_flow.py` with a test
   that mocks `clone_repo_cached` to return a real temp directory populated
   with a fake repo (README, source files), then runs IntakeWorker.run()
   followed by UnderstandWorker.run() using the intake output, verifying:
   - IntakeBundle has repo_sha and repo_dir populated
   - UnderstandingBundle has non-empty file_tree and claims
   - context.repo_dir is set correctly
2. Add a test that simulates resume-from "understand" where the intake
   checkpoint has `repo_dir` pointing to a deleted directory. Verify that
   UnderstandWorker raises a clear error (requires SR-01 guard from the
   robustness healing plan).

**Allowed paths:**
- `tests/integration/test_intake_understand_flow.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_intake_understand_flow.py -v` — all pass
- **Tests:**
  - `test_intake_to_understand_produces_understanding_bundle` — passes
  - `test_resume_with_stale_repo_dir_fails_cleanly` — passes
  - No network calls (clone mocked)
- **Config respected end-to-end:** Uses real worker classes, not mocks
- **No mock data in production paths:** Only `clone_repo_cached` is mocked

### Deliverables

- New `tests/integration/test_intake_understand_flow.py`
  - Happy path: Intake → Understand produces valid bundle
  - Failure path: stale repo_dir at Understand entry raises ValueError

### Hard rules

- Keep public signatures unchanged
- No network in offline tests — mock `clone_repo_cached` only
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Tests must work on Windows (forward-slash path normalization)
- This taskcard depends on SR-01 (repo_dir guard) for the failure path test

### Review dimensions — what 5/5 means for IT-01

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Both happy + failure paths tested across two workers |
| Correctness | Real worker classes used, only clone mocked |
| Testability | Tests are self-contained, create their own temp directories |
| Robustness | Failure path test proves clean error, not opaque traceback |
| Integration fit | Tests mirror the graph builder's data flow (output → input) |
| Minimality | One new file with 2 test classes |

### Now (runbook)

```bash
# 1. Ensure SR-01 is complete (repo_dir guard in Understand)
# 2. Create tests/integration/ directory if needed
mkdir -p tests/integration
# 3. Write test_intake_understand_flow.py
# 4. Run integration tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_intake_understand_flow.py -v
# 5. Run full suite to confirm no regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
```
