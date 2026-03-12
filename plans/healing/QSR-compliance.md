# Healing Plan — Compliance & Bookkeeping (QSR-07, QSR-08, QSR-09)
# Source: Self-review gaps G-07, G-08, G-09
# Date: 2026-03-11

---

## Taskcard QSR-07 — Update TASK_BACKLOG, taskcard self-reviews, CHANGELOG

**Status**: Not Started
**Gap linkage**: G-07 — TASK_BACKLOG.md TC-4040–4043 still show ACTIVE/NEXT/QUEUED; taskcard self-review sections unfilled; CHANGELOG.md not updated
**Role**: Senior engineer. Bookkeeping/compliance only.

### Scope

**Fix**: Update TASK_BACKLOG.md to mark TC-4040–4043 as DONE; fill self-review sections
in each taskcard; append a CHANGELOG entry for the quality sprint if CHANGELOG.md exists.

**Allowed paths**:
- `plans/healing/QSR-compliance.md` (this file)
- `TASK_BACKLOG.md`
- `plans/taskcards/TC-4040_evidence-completeness.md`
- `plans/taskcards/TC-4041_evidence-injection-generate.md`
- `plans/taskcards/TC-4042_api-surface-allowlist.md`
- `plans/taskcards/TC-4043_readability-calibration.md`
- `CHANGELOG.md` (if file exists)

**Forbidden**: Any src/ files. No logic changes.

### Acceptance checks

**CLI**:
```bash
# TASK_BACKLOG must not show ACTIVE/NEXT/QUEUED for TC-4040 through TC-4043
grep -E "TC-404[0-3]" TASK_BACKLOG.md

# Each taskcard must show Status: Done
grep -n "^Status:" \
  plans/taskcards/TC-4040_evidence-completeness.md \
  plans/taskcards/TC-4041_evidence-injection-generate.md \
  plans/taskcards/TC-4042_api-surface-allowlist.md \
  plans/taskcards/TC-4043_readability-calibration.md

# All 4 must show "Done"
```
Expected: TC-404x in TASK_BACKLOG show DONE; all 4 taskcards show `Status: Done`.

**UI/Web/API**: N/A

**Tests**: No test required (bookkeeping only).

### Deliverables

1. **Edit `TASK_BACKLOG.md`**:
   - Find each row for TC-4040, TC-4041, TC-4042, TC-4043
   - Change status column from ACTIVE/NEXT/QUEUED → **DONE**
   - Add brief outcome note: "Evidence wiring done; evidence injection done; allowlist-first done; FK prompt added"

2. **Edit each taskcard** (`TC-4040` through `TC-4043`):
   - Find the `## Self-review` / `### Self-review` section
   - Fill in actual results:
     - What acceptance checks passed
     - Test counts (before/after)
     - Any gaps found (reference QSR IDs for G-01 through G-09)
   - Change `Status: In-Progress` → `Status: Done`

3. **Edit `CHANGELOG.md`** (if file exists):
   - Prepend entry:
     ```markdown
     ## [Unreleased] — 2026-03-11

     ### Added (Quality Sprint — TC-4040 to TC-4043)
     - TC-4040: Wire `_format_matrix` → `ProductEvidence` format fields (`supported_formats`, `input_formats`, `output_formats`) in `extract/_entry.py` and `worker.py`
     - TC-4041: Inject `workflow_examples` and `supported_formats` into `build_section_prompt()` (role-gated; capped at 3 examples × 500 chars)
     - TC-4042: Fix `_is_internal_class()` to check allowlist before markers (allowlist-first)
     - TC-4043: Add FK grade 12–16 readability target + active voice guidance to `section_writer.txt`

     ### Fixed
     - API surface contamination from Aspose-specific internal markers on non-Aspose products
     ```

### Hard rules

- No logic changes — status and text only
- Do not invent test counts; read the actual evidence files in `reports/TC-40*/evidence.md`
- Do not overwrite existing CHANGELOG entries; prepend only
- If CHANGELOG.md does not exist, skip that step (do not create it)

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Completeness | All 4 taskcards marked Done; all 4 TASK_BACKLOG rows updated |
| Accuracy | Self-review text references actual test counts from evidence files |
| Compliance | CHANGELOG follows Keep A Changelog format if file exists |
| Minimality | No other changes |

### Now (runbook)

```bash
# 1. Read evidence files for test counts
cat reports/TC-4040/evidence.md
cat reports/TC-4041/evidence.md
cat reports/TC-4042/evidence.md
cat reports/TC-4043/evidence.md

# 2. Check if CHANGELOG exists
ls CHANGELOG.md 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"

# 3. Find TC rows in TASK_BACKLOG
grep -n "TC-404" TASK_BACKLOG.md

# 4. Update files (TASK_BACKLOG, taskcards, CHANGELOG if present)
```

---

## Taskcard QSR-08 — Run Pre-Flight Checks 1–3 and document results

**Status**: Not Started
**Gap linkage**: G-08 — Pre-Flight Checks 1–3 never run: heal loop config unverified, FK backtick stripping unverified — could silently neutralize TC-4043
**Role**: Senior engineer. Diagnostic + documentation only. May require one src/ fix if FK stripping is absent.

### Scope

**Fix**: Execute Pre-Flight Checks 1, 2, and 3 from the plan file
(`C:\Users\prora\.claude\plans\hidden-enchanting-puppy.md`). Document the findings.
If FK stripping is absent in readability.py, that constitutes a new TC that must be
filed before TC-4043's impact can be measured.

**Allowed paths**:
- `plans/healing/QSR-compliance.md` (this file)
- `plans/healing/QSR-08-preflight-results.md` (new — findings doc)
- `src/launcher/workers/evaluate/checks/readability.py` ← **ONLY if FK backtick strip is absent AND a new TC is filed first**

**Forbidden**: Any other path without a new taskcard.

### Acceptance checks

**CLI**:

**Check 1 — Heal loop active**:
```bash
grep -rn "heal_iterations\|num_heal" configs/pilots/ configs/pipeline.yaml 2>/dev/null || echo "NOT FOUND"
```
Expected: value ≥ 1.

**Check 2 — D-page safety-critical finding**:
```bash
python -c "
import json, pathlib
runs = sorted(pathlib.Path('runs').iterdir(), key=lambda p: p.name)
if not runs:
    print('No runs found')
else:
    run = runs[-1]
    r = json.load(open(run / 'evaluation_report.json'))
    for p in r['pages']:
        if p['grade'] == 'D':
            print(p['slug'], [f for f in p['findings'] if f['severity'] in ('critical','high')])
"
```
Expected: D-page slug + its safety-critical finding(s) identified.

**Check 3 — FK backtick stripping**:
```bash
grep -n "backtick\|code_span\|re.sub.*\`\|strip" \
  src/launcher/workers/evaluate/checks/readability.py | head -20
```
Expected: Either confirms backtick stripping exists (TC-4043 sufficient as-is), OR
confirms it is absent (new TC required before TC-4043 can be validated).

**Documentation**:
```bash
# After running all 3 checks, results must exist:
cat plans/healing/QSR-08-preflight-results.md
```
Expected: File exists with findings for all 3 checks.

**UI/Web/API**: N/A

**Tests**: No test required (diagnostic only).

### Deliverables

1. **Run Check 1** and record result in `QSR-08-preflight-results.md`:
   - Config path where `heal_iterations` is set
   - Current value
   - PASS / FAIL verdict
   - If FAIL: note that grades will not improve on D-page until fixed

2. **Run Check 2** and record result in `QSR-08-preflight-results.md`:
   - D-page slug (or "no D-grade pages in most recent run")
   - Finding(s) causing D grade
   - Recommended micro-TC to fix (or "already resolved")

3. **Run Check 3** and record result in `QSR-08-preflight-results.md`:
   - Whether readability.py strips backtick spans before FK calculation
   - Relevant line numbers
   - PASS / FAIL verdict
   - If FAIL: file a new TC (`TC-4043b`) to add backtick stripping; do NOT modify readability.py under QSR-08

4. **Write `plans/healing/QSR-08-preflight-results.md`**:
   ```markdown
   # QSR-08 Pre-Flight Results
   # Date: <date>

   ## Check 1 — Heal loop

   - Config path: <...>
   - heal_iterations value: <...>
   - Verdict: PASS / FAIL
   - Action required: <none / set heal_iterations: 2 in pilot config>

   ## Check 2 — D-page finding

   - Most recent run: <run dir>
   - D-grade pages: <slug> / none
   - Finding(s): <...>
   - Action required: <micro-TC / none>

   ## Check 3 — FK backtick stripping

   - File: src/launcher/workers/evaluate/checks/readability.py
   - Lines checked: <line range>
   - Backtick stripping present: YES / NO
   - Verdict: PASS / FAIL
   - Action if FAIL: file TC-4043b (new allowed_paths includes readability.py)
   ```

### Hard rules

- Do NOT modify readability.py under this taskcard — file a new TC if stripping is absent
- Do NOT modify pilot configs under this taskcard — file a new TC if heal_iterations=0
- Results file must be in `plans/healing/`, not `reports/`
- All 3 checks must be documented regardless of outcome

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Completeness | All 3 checks documented |
| Accuracy | Line numbers + config paths cited |
| Actionability | Each FAIL produces a named follow-on TC or micro-TC |
| Scope discipline | No src/ changes without new TC |

### Now (runbook)

```bash
# Check 1
grep -rn "heal_iterations\|num_heal" configs/pilots/ configs/pipeline.yaml

# Check 2
python -c "
import json, pathlib
runs = sorted(pathlib.Path('runs').iterdir(), key=lambda p: p.name)
run = runs[-1]
r = json.load(open(run / 'evaluation_report.json'))
for p in r['pages']:
    if p['grade'] == 'D':
        print(p['slug'], [f for f in p['findings'] if f['severity'] in ('critical','high')])
"

# Check 3
grep -n "backtick\|code_span\|re.sub\|strip" \
  src/launcher/workers/evaluate/checks/readability.py | head -20

# Write results
# plans/healing/QSR-08-preflight-results.md
```

---

## Taskcard QSR-09 — Fix TC-4042 allowed_paths mismatch + document TS import decision

**Status**: Not Started
**Gap linkage**: G-09 — TC-4042 taskcard `allowed_paths` lists wrong test file path (`test_api_surface.py` vs `test_extract.py`); TS import fix decision (Part B of TC-UW-02) is undocumented
**Role**: Senior engineer. Compliance/documentation only.

### Scope

**Fix**:
1. Correct the `allowed_paths` in `TC-4042_api-surface-allowlist.md` to match the
   file actually modified (`tests/unit/workers/understand/test_extract.py`).
2. Add a decision note section to TC-4042 explaining why the TS import regex fix
   (Part B of TC-UW-02) was deferred and what would trigger implementation.

**Allowed paths**:
- `plans/healing/QSR-compliance.md` (this file)
- `plans/taskcards/TC-4042_api-surface-allowlist.md`

**Forbidden**: Any other path. No src/ changes.

### Acceptance checks

**CLI**:
```bash
# test_extract.py must be in allowed_paths; test_api_surface.py must NOT
grep -n "allowed_paths\|test_api_surface\|test_extract" \
  plans/taskcards/TC-4042_api-surface-allowlist.md

# Expected: test_extract.py present, test_api_surface.py absent from allowed_paths section

# Decision note must exist
grep -n "TS import\|Part B\|deferred\|ts_analyzer" \
  plans/taskcards/TC-4042_api-surface-allowlist.md
```
Expected: allowed_paths corrected; decision note section present.

**UI/Web/API**: N/A

**Tests**: No test required (documentation only).

### Deliverables

1. **Edit `plans/taskcards/TC-4042_api-surface-allowlist.md`**:

   **Correction 1 — allowed_paths**:
   - Find the `allowed_paths` frontmatter or section
   - Replace any reference to `tests/unit/workers/understand/extract/test_api_surface.py`
     with `tests/unit/workers/understand/test_extract.py`
   - Confirm the actual modified file path matches

   **Addition 2 — Decision note section** (append at end of taskcard):
   ```markdown
   ## Decision Log

   ### TS Import Regex Fix (Part B of TC-UW-02) — Deferred

   **What**: TC-UW-02 Part B specified a fix to `ts_analyzer.py` lines 428-429
   (`(@aspose/\w+)` → hyphen-aware regex) and a tree-sitter fallback hardening.

   **Why deferred**: The 3D Python pilot has no TypeScript products in scope. The
   dominant findings were `factual_accuracy HIGH` and `api_consistency HIGH` on Python
   pages — not TS import errors. Fixing TS imports would have zero impact on current
   A+B rate.

   **Trigger for implementation**: When a TypeScript product (e.g., Aspose.Words for
   Node.js) enters the pilot set, or when `api_consistency HIGH` findings cite import
   path errors on TS pages. File as TC-4042b with allowed_paths:
   - `src/launcher/shared/ts_analyzer.py`
   - `tests/unit/shared/test_ts_analyzer_imports.py`

   **Risk**: Low. Python product pipeline is unaffected by TS analyzer. Deferral is
   safe until TS products enter scope.
   ```

### Hard rules

- Do NOT create `test_api_surface.py` — the correct path is `test_extract.py`
- Decision note must be honest about why Part B was skipped (not just "out of scope")
- No src/ changes under this taskcard

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Accuracy | allowed_paths matches the file that was actually modified |
| Completeness | Decision note covers what, why, trigger, and risk |
| Scope | Zero src/ changes |
| Traceability | TC-4042b stub created in decision log with allowed_paths |

### Now (runbook)

```bash
# 1. Confirm which test file was actually modified
grep -rn "test_is_internal_class_allowlist" tests/

# 2. Read current TC-4042 taskcard
cat plans/taskcards/TC-4042_api-surface-allowlist.md | grep -A 5 "allowed_paths"

# 3. Edit taskcard to correct path + add decision note
```
