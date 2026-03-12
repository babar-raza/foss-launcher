# TC3911-VER-02 — Smoke Import + Negative Deletion Assertions

**Status**: Done
**Gap linkage**: GAP-02 (taskcard acceptance checks AC-2 and AC-3 skipped)
**Role**: Senior engineer. Drop-in, production-ready assertion suite.

---

## Context

TC-3911's taskcard listed three acceptance checks:
1. `grep` for import-style references → done (0 hits confirmed)
2. All tests pass (PYTHONHASHSEED=0) → done (3236 passed)
3. `python -c "import launcher"` smoke import → **never run**

Additionally, no negative assertion was made to confirm that deleted modules
raise `ModuleNotFoundError` (vs. being silently shadowed by stale `.pyc` cache
or a sys.path artifact). This taskcard closes both gaps.

---

## Scope

**Fix:**
1. Run the TC-3911 acceptance check AC-3: `python -c "import launcher"`.
2. Run negative deletion assertions for each deleted module — confirm `ModuleNotFoundError`, not a successful import.
3. Clear `__pycache__` and repeat to rule out stale bytecode.

**Allowed paths:**
- `plans/healing/TC3911-VER-02-deletion-assertions.md` (this file, status update only)
- `reports/TC-3911/` (evidence output)

**Forbidden:** Any file under `src/`, `tests/`, `configs/`, `specs/`.

---

## Acceptance Checks

**CLI:**
```bash
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2

# AC-3: Smoke import (from TC-3911 taskcard)
.venv/Scripts/python.exe -c "import launcher; print('smoke import: OK')"
# Expected: "smoke import: OK" with exit code 0

# Negative assertions — each must raise ModuleNotFoundError
DELETED_MODULES=(
  "launcher.shared.extract_claims"
  "launcher.shared.context_validator"
  "launcher.shared.markdown_zones"
  "launcher.shared.policy_check"
  "launcher.shared.rich_context"
  "launcher.util.diff_analyzer"
  "launcher.validation_engine"
  "launcher.validation_engine.runner"
  "launcher.validation_engine.registry_loader"
)

for mod in "${DELETED_MODULES[@]}"; do
  result=$(.venv/Scripts/python.exe -c "import $mod" 2>&1)
  if echo "$result" | grep -q "ModuleNotFoundError\|No module named"; then
    echo "PASS: $mod correctly absent"
  else
    echo "FAIL: $mod import succeeded or gave unexpected error: $result"
  fi
done

# Stale .pyc check: clear __pycache__ and re-run
find src/launcher -name "*.pyc" -delete
find src/launcher -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Re-run smoke import after cache clear
.venv/Scripts/python.exe -c "import launcher; print('post-cache-clear smoke import: OK')"

# Re-run one negative assertion after cache clear (representative)
.venv/Scripts/python.exe -c "import launcher.validation_engine" 2>&1 \
  | grep -q "ModuleNotFoundError" && echo "PASS: validation_engine absent post-cache-clear" \
  || echo "FAIL: unexpected result"
```

**UI/Web/API:** N/A

**Tests:** Full test suite must still pass after `__pycache__` clear:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -3
# Expected: same pass count as before (≥3236 passed, 0 failed)
```

**Config respected end-to-end:** N/A for this taskcard.

**No mock data in production paths:** N/A — no LLM calls in this taskcard.

---

## Deliverables

1. `reports/TC-3911/deletion-assertions.log` — output of all negative assertion checks
2. `reports/TC-3911/smoke-import.log` — smoke import output (AC-3)
3. Updated status in this file: `Status: Done`

---

## Hard Rules

- Do NOT restore any deleted file, even temporarily.
- `__pycache__` clear must be followed by a full test run to confirm nothing broke.
- Each deleted module must raise `ModuleNotFoundError` specifically — a generic `ImportError` (caused by a broken dependency of an existing module) is a different failure mode and must be investigated.
- No new deps.
- Determinism: PYTHONHASHSEED=0 for test runs.

---

## Review Dimensions (what "5/5" means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Thoroughness | All 9 deleted module paths tested with negative assertions |
| Correctness | Every deleted module raises exactly `ModuleNotFoundError` |
| Robustness | Cache cleared and re-tested; no stale `.pyc` shadow possible |
| Testability | Assertions are scripted and repeatable; output logged to file |
| Scope adherence | No source changes; verification only |
| Observability | All assertion results written to `reports/TC-3911/deletion-assertions.log` |
| Minimality | Only the assertions needed to close GAP-02; no extra checks |

---

## Now (Runbook)

```bash
# 0. Setup
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
mkdir -p reports/TC-3911

# 1. Smoke import (AC-3)
.venv/Scripts/python.exe -c "import launcher; print('smoke import: OK')" \
  | tee reports/TC-3911/smoke-import.log

# 2. Negative assertions
{
echo "=== Negative Deletion Assertions ==="
for mod in \
  launcher.shared.extract_claims \
  launcher.shared.context_validator \
  launcher.shared.markdown_zones \
  launcher.shared.policy_check \
  launcher.shared.rich_context \
  launcher.util.diff_analyzer \
  launcher.validation_engine \
  launcher.validation_engine.runner \
  launcher.validation_engine.registry_loader; do
    result=$(.venv/Scripts/python.exe -c "import $mod" 2>&1)
    if echo "$result" | grep -q "ModuleNotFoundError\|No module named"; then
      echo "PASS: $mod"
    else
      echo "FAIL: $mod -> $result"
    fi
  done
} | tee reports/TC-3911/deletion-assertions.log

# 3. Clear __pycache__
find src/launcher -name "*.pyc" -delete 2>/dev/null
find src/launcher -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "Cache cleared."

# 4. Post-cache smoke import
.venv/Scripts/python.exe -c "import launcher; print('post-cache-clear: OK')" \
  | tee -a reports/TC-3911/smoke-import.log

# 5. Post-cache test run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -5 \
  | tee -a reports/TC-3911/deletion-assertions.log
```
