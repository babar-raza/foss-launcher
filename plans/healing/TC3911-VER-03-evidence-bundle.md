# TC3911-VER-03 — Create TC-3911 Evidence Bundle

**Status**: Done
**Gap linkage**: GAP-05 (evidence bundle `reports/TC-3911/evidence.md` never created)
**Role**: Senior engineer. Drop-in, production-ready governance artifact.

---

## Context

TC-3911's taskcard listed `reports/TC-3911/evidence.md` as a required deliverable
under `evidence_required`. This file was never created. Without it, the taskcard
is formally incomplete regardless of the runtime and test results.

This taskcard also corrects the overstated pilot conclusion ("no breaking changes
proven" → accurate scoped claim) in the final summary.

**Depends on**: TC3911-VER-01 and TC3911-VER-02 must be completed first so that
the evidence file can reference real results.

---

## Scope

**Fix:**
1. Create `reports/TC-3911/evidence.md` with all verification results.
2. The file must reference the actual run IDs and log file paths from VER-01 and VER-02.

**Allowed paths:**
- `plans/healing/TC3911-VER-03-evidence-bundle.md` (this file, status update only)
- `reports/TC-3911/evidence.md` (new file — create from template below)

**Forbidden:** Any file under `src/`, `tests/`, `configs/`, `specs/`, or `plans/taskcards/`.

---

## Acceptance Checks

**CLI:**
```bash
# Confirm evidence file exists and is non-empty
test -f reports/TC-3911/evidence.md && wc -l reports/TC-3911/evidence.md
# Expected: file exists, ≥20 lines

# Confirm all acceptance checks are referenced
grep -c "\- \[x\]" reports/TC-3911/evidence.md
# Expected: ≥3 (one per AC)

# Confirm run log files exist
test -f reports/TC-3911/evaluate-run.log && echo "evaluate-run.log: OK"
test -f reports/TC-3911/dryrun-all.log && echo "dryrun-all.log: OK"
test -f reports/TC-3911/deletion-assertions.log && echo "deletion-assertions.log: OK"
test -f reports/TC-3911/smoke-import.log && echo "smoke-import.log: OK"
```

**UI/Web/API:** N/A

**Tests:** N/A (documentation artifact only)

**Config respected end-to-end:** N/A

**No mock data in production paths:** N/A

---

## Deliverables

`reports/TC-3911/evidence.md` — complete evidence file with the following structure:

```markdown
# TC-3911 Evidence Bundle

**Date**: 2026-03-09
**Taskcard**: TC-3911 — Remove orphaned / dead-code files
**Status**: Done

## Deleted Files

| File | Deletion Confirmed |
|------|--------------------|
| src/launcher/shared/extract_claims.py | [x] |
| src/launcher/shared/context_validator.py | [x] |
| src/launcher/shared/markdown_zones.py | [x] |
| src/launcher/shared/policy_check.py | [x] |
| src/launcher/shared/rich_context.py | [x] |
| src/launcher/util/diff_analyzer.py | [x] |
| src/launcher/validation_engine/ (7 files) | [x] |

## Acceptance Check Results

- [x] AC-1: grep for import-style references → 0 hits (confirmed 2026-03-09)
- [x] AC-2: All tests pass PYTHONHASHSEED=0 → 3236 passed, 0 failed, 1 skipped, 3 xfailed
- [x] AC-3: `python -c "import launcher"` → OK (see reports/TC-3911/smoke-import.log)

## Runtime Verification

### Pilot: aspose-3d-foss-python (--stop-after evaluate)
- Run ID: <populated from evaluate-run.log>
- Workers completed: intake, understand, planner, generate, evaluate
- Import errors: 0
- Log: reports/TC-3911/evaluate-run.log

### Dry-run: All 5 pilots
- Log: reports/TC-3911/dryrun-all.log
- Result: Config valid for all 5 pilots

### Negative Deletion Assertions
- Log: reports/TC-3911/deletion-assertions.log
- All 9 deleted module paths raise ModuleNotFoundError

### __pycache__ Clear Test
- Post-clear smoke import: OK
- Post-clear test run: ≥3236 passed

## Prompt-Path Warning Attribution
- Warning: `[Errno 2] No such file or directory: '...workers/prompts/claim_extractor.txt'`
- Attribution: <populated from VER-01 git log check>

## Collateral Fix
- tests/unit/shared/test_claim_visibility_spec_leakage.py: import updated from
  `launcher.shared.extract_claims` → `launcher.shared.classify_claims`
```

---

## Hard Rules

- Do NOT create the evidence file until VER-01 and VER-02 are both `Status: Done`.
- Evidence file must contain real run IDs and real log references — no placeholder values in the final version.
- Template above uses `<populated from ...>` markers; replace all markers before marking this taskcard Done.
- No new deps.

---

## Review Dimensions (what "5/5" means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Thoroughness | All 3 AC checks documented; all 5 pilots referenced; collateral fix noted |
| Correctness | Real run IDs and log paths; no `<placeholder>` remaining |
| Scope adherence | Only `reports/TC-3911/evidence.md` created; no source changes |
| Maintainability | Evidence file is self-contained and reviewable without needing to re-run |
| Observability | All log file paths cross-referenced; traceable end-to-end |

---

## Now (Runbook)

```bash
# Prerequisites: TC3911-VER-01 and TC3911-VER-02 must be Done

# 1. Extract run ID from evaluate-run.log
RUN_ID=$(grep "Starting pipeline run:" reports/TC-3911/evaluate-run.log \
  | head -1 | sed 's/.*Starting pipeline run: //')
echo "Run ID: $RUN_ID"

# 2. Extract test count
TEST_COUNT=$(grep "passed" reports/TC-3911/deletion-assertions.log | tail -1)
echo "Tests: $TEST_COUNT"

# 3. Check warning attribution
git log --oneline -- src/launcher/workers/prompts/ 2>/dev/null | head -3 \
  || echo "Directory never existed in git — warning is pre-existing"

# 4. Write evidence.md (substitute real values into template above)
# Use Edit tool or manual write — replace all <populated from ...> markers
# with actual values from the logs.

# 5. Verify
test -f reports/TC-3911/evidence.md \
  && grep -c "\- \[x\]" reports/TC-3911/evidence.md \
  && echo "Evidence bundle complete"
```
