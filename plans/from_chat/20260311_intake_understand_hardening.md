# Intake + Understand Phase Hardening — SR-01..SR-07
**Generated**: 2026-03-11
**Source**: Self-review of TC-4057 + TC-4058 healing plan
**Primary plan**: `plans/healing/SR-intake-understand-hardening.md`

## Context
TC-4057 (Intake platform coverage + provenance) and TC-4058 (Understand silent failure removal)
were completed, but self-review revealed 8 remaining gaps that must be closed before the pipeline
is production-ready.

## Goals
1. Close all 8 gaps (G-01..G-08) from the TC-4057/TC-4058 self-review
2. All existing tests must continue to pass
3. No silent failure paths remain in intake or understand workers

## Assumptions
- VERIFIED: `_FAMILIES_YAML = Path("configs/families.yaml")` at line 27 of intake/worker.py — CWD-relative
- VERIFIED: test_understand.py has 2 duplicate class definitions (lines 3786+3928, 3898+4043)
- VERIFIED: No `TestExtractProductEvidenceErrorHandling` class exists in test_understand.py
- VERIFIED: `launcher.shared.code_analyzer` module exists at src/launcher/shared/code_analyzer.py
- VERIFIED: Phase B.5 ERROR log at understand/worker.py:531 lacks structured fields

## Steps (execution order)
1. SR-02: Fix test_understand.py (remove duplicate lines 3780-3921, add TestExtractProductEvidenceErrorHandling)
2. SR-01: Fix _FAMILIES_YAML path in intake/worker.py (line 27)
3. SR-05: Add family/platform/repo_url to Phase B.5 ERROR log
4. SR-03: Add IdentityResolution NamedTuple to intake/worker.py
5. SR-04: Add families.yaml module-level cache
6. SR-06: Add Scout integration test at tests/unit/workers/understand/test_scout.py
7. SR-07: Add E2E integration test at tests/integration/test_intake_understand_flow.py

## Acceptance criteria
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — all pass, no duplicates
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all pass (46+ tests)
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_scout.py -v` — new tests pass
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_intake_understand_flow.py -v` — new tests pass
- `cd /tmp && python -c "from launcher.workers.intake.worker import _resolve_identity; print(_resolve_identity('cells','python')[3])"` returns families_yaml provenance

## Evidence commands
```bash
# Verify no duplicates
python -c "
content = open('tests/unit/workers/test_understand.py').read()
classes = ['TestSelfReviewProductEvidence', 'TestScoutInventorySkipReasonCounts', 'TestExtractProductEvidenceErrorHandling']
for c in classes:
    print(c, content.count('class ' + c))
"

# Run understand tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v --tb=short

# Run intake tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v --tb=short

# Verify path fix
.venv/Scripts/python.exe -c "
import os; os.chdir('/tmp')
from launcher.workers.intake.worker import _resolve_identity
r = _resolve_identity('cells', 'python')
print('Provenance:', r[3])
"
```

## Risks + rollback
- SR-02 file edit: If something goes wrong, restore from git: `git checkout tests/unit/workers/test_understand.py`
- SR-01 path change: If parent count is wrong, run manual verification immediately
- Rollback any file: `git checkout <file>` since all changes are on branch `v2`

## Open questions
(none — all verified against live codebase before materialization)
