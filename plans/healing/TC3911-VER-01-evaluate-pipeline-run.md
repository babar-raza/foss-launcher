# TC3911-VER-01 — Run Pipeline Through Evaluate + Cross-Pilot Coverage

**Status**: Done
**Gap linkage**: GAP-01 (evaluate worker not exercised), GAP-03 (single pilot), GAP-04 (unverified warning)
**Role**: Senior engineer. Drop-in, production-ready verification step.

---

## Context

The TC-3911 smoke test stopped at `--stop-after understand`. The `evaluate` worker
runs all `checks/` modules and is the closest runtime sibling to the deleted
`validation_engine/` package. Four workers (planner, generate, evaluate, publish)
were never exercised. This taskcard completes the runtime coverage.

Additionally, 4 of 5 pilots were never dry-run validated, and a prompt-path warning
was dismissed without baseline evidence.

---

## Scope

**Fix:**
1. Run `aspose-3d-foss-python` pilot with `--stop-after evaluate` (exercises planner, generate, evaluate in addition to the already-verified intake + understand).
2. Run `--dry-run` on all 5 remaining pilot configs to confirm no import-time errors.
3. Establish a baseline for the prompt-path warning by checking whether it appears on a run that predates TC-3911 (use the existing `runs/` directory or git-stash approach).

**Allowed paths:**
- `plans/healing/TC3911-VER-01-evaluate-pipeline-run.md` (this file, status update only)
- `reports/TC-3911/` (evidence artifacts created here)

**Forbidden:** Any file under `src/`, `tests/`, `configs/`, `specs/` — this is verification only.

---

## Acceptance Checks

**CLI:**
```bash
# Step 1: Run through evaluate worker
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
.venv/Scripts/python.exe -m launcher.cli.main run \
  configs/pilots/aspose-3d-foss-python.yaml \
  --stop-after evaluate 2>&1 | tee reports/TC-3911/evaluate-run.log

# Expected: All 5 workers complete with no ImportError, no ModuleNotFoundError
# Grep for failures:
grep -i "importerror\|modulenotfounderror\|no module named" reports/TC-3911/evaluate-run.log
# Expected: 0 matches

# Step 2: Dry-run all 5 pilots
for cfg in configs/pilots/aspose-3d-foss-python.yaml \
           configs/pilots/aspose-3d-foss-typescript.yaml \
           configs/pilots/aspose-cells-foss-python.yaml \
           configs/pilots/aspose-note-foss-python.yaml \
           configs/pilots/aspose-slides-foss-python.yaml; do
  echo "=== $cfg ===" | tee -a reports/TC-3911/dryrun-all.log
  .venv/Scripts/python.exe -m launcher.cli.main run "$cfg" --dry-run 2>&1 \
    | tee -a reports/TC-3911/dryrun-all.log
done
# Expected: "Config valid" for each pilot, no errors

# Step 3: Baseline the prompt-path warning
# Check if the warning exists in a pre-TC-3911 run log (if one exists)
ls runs/ | sort | head -5
# If a prior run exists, grep it:
grep "No such file or directory.*prompts" runs/<prior-run-id>/pipeline.log 2>/dev/null \
  || echo "No prior run log available — warning is pre-existing if it appeared before TC-3911"
# Alternatively, check git log for the prompts directory:
git log --oneline -- src/launcher/workers/prompts/ 2>/dev/null | head -5
```

**UI/Web/API:** N/A — CLI-only verification.

**Tests:** All 3236 existing tests continue to pass:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -3
# Expected: "3236 passed" (or higher if tests were added)
```

**Config respected end-to-end:** Each pilot config dry-run must print "Config valid: <family>/<platform>".

**No mock data in production paths:** The `--stop-after evaluate` run must use the real LLM endpoint (or the deterministic fallback if LLM is unavailable) — no `--mock` flag.

---

## Deliverables

1. `reports/TC-3911/evaluate-run.log` — full log of `--stop-after evaluate` run
2. `reports/TC-3911/dryrun-all.log` — dry-run output for all 5 pilots
3. Updated status in this file: `Status: Done`
4. Summary note in `reports/TC-3911/evidence.md` (TC3911-VER-03 owns that file, but add the run ID here for reference)

---

## Hard Rules

- No changes to source code or tests — verification only.
- No network-dependent assertions — the dry-run validates config/import only; LLM calls are acceptable for the evaluate run (already tested path).
- If `--stop-after evaluate` fails due to LLM timeout, re-run with `--stop-after planner` to confirm the import graph (generate/evaluate use fewer new imports than planner).
- Determinism: PYTHONHASHSEED=0 for all test runs.
- No new deps.

---

## Review Dimensions (what "5/5" means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Thoroughness | All 5 workers covered OR explicitly justified why remaining workers can't import deleted modules |
| Consistency | Log confirms same pilot config as TC-3911 original run; no config drift |
| Production grading | `evaluate` run clean with real LLM endpoint (or verified fallback) |
| Systematic approach | Workers covered in order; each verified before moving to next |
| Correctness | Zero import errors in all runs; grep confirms no ModuleNotFoundError |
| Scope adherence | Only verification commands run; no source changes |
| Robustness | Warning baseline established; warning explicitly attributed |
| Observability | Full logs captured and persisted to `reports/TC-3911/` |
| Minimality | Only the minimum runs needed to close GAP-01/03/04 |

---

## Now (Runbook)

```bash
# 0. Setup
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
mkdir -p reports/TC-3911

# 1. Run through evaluate
.venv/Scripts/python.exe -m launcher.cli.main run \
  configs/pilots/aspose-3d-foss-python.yaml \
  --stop-after evaluate 2>&1 | tee reports/TC-3911/evaluate-run.log

# 2. Check for import errors
grep -i "importerror\|modulenotfounderror\|no module named" \
  reports/TC-3911/evaluate-run.log && echo "FAIL: import errors found" || echo "PASS: no import errors"

# 3. Dry-run all pilots
for cfg in configs/pilots/*.yaml; do
  echo "--- $cfg ---"
  .venv/Scripts/python.exe -m launcher.cli.main run "$cfg" --dry-run 2>&1
done | tee reports/TC-3911/dryrun-all.log

# 4. Baseline the warning
git log --oneline -- src/launcher/workers/prompts/ 2>/dev/null | head -5
# If directory never existed → warning is definitively pre-existing
```
