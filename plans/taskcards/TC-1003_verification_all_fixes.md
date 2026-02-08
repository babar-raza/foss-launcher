---
id: TC-1003
title: "Verification: All Fixes + Pilots"
status: Draft
priority: P4
owner: Agent-C
updated: "2026-02-06"
tags: ["verification", "pilots", "e2e"]
depends_on:
  - TC-998
  - TC-999
  - TC-1000
  - TC-1001
  - TC-1002
allowed_paths:
  - reports/agents/agent_c/TC-1003/**
evidence_required:
  - reports/agents/agent_c/TC-1003/evidence.md
  - reports/agents/agent_c/TC-1003/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1003 — Verification: All Fixes + Pilots

## Objective

Run full test suite and both pilots to verify all TC-998 through TC-1002 fixes work correctly with no regressions.

## Problem Statement

After implementing fixes for stale fixtures (TC-998, TC-999), content_preview bug (TC-1000), absolute cross_links (TC-1001), and spec updates (TC-1002), need comprehensive verification.

## Required spec references

- specs/21_worker_contracts.md (all worker contracts)
- plans/taskcards/00_TASKCARD_CONTRACT.md (verification requirements)

## Scope

### In scope
- Run full pytest suite
- Run pilot-aspose-3d-foss-python E2E
- Run pilot-aspose-note-foss-python E2E
- Verify all acceptance criteria from TC-998 through TC-1002
- Produce evidence bundle

### Out of scope
- Additional code changes (verification only)
- New feature implementation

## Inputs
- Completed TC-998 through TC-1002
- Test suite
- Pilot configs

## Outputs
- Test results
- Pilot run outputs
- Evidence bundle confirming all fixes

## Allowed paths

- reports/agents/agent_c/TC-1003/**

## Implementation steps

### Step 1: Run full test suite
```bash
.venv/Scripts/python.exe -m pytest tests/ -v --tb=short 2>&1 | tee output/tc1003_tests.txt
```

### Step 2: Run 3D pilot
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/tc1003-3d
```

### Step 3: Run Note pilot
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/tc1003-note
```

### Step 4: Verify TC-998 (no section in url_path)
```bash
grep -E '"url_path".*/(docs|kb|blog|reference|products)/' output/tc1003-3d/*/artifacts/page_plan.json
# Expected: no output
```

### Step 5: Verify TC-1000 (no double content)
```bash
ls output/tc1003-3d/*/content_preview/
# Should show: content/ (not content/content/)
```

### Step 6: Verify TC-1001 (absolute cross_links)
```bash
grep '"cross_links"' output/tc1003-3d/*/artifacts/page_plan.json -A5 | grep "https://"
# Expected: absolute URLs
```

### Step 7: Produce evidence bundle
Collect all verification outputs into evidence.md.

## Failure modes

### Failure mode 1: Test failures
**Detection:** pytest exit code non-zero
**Resolution:** Report failures; route back to relevant TC
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Pilot fails
**Detection:** Pilot exit code non-zero
**Resolution:** Check logs; identify failing worker; route back
**Spec/Gate:** Pilot verification

### Failure mode 3: Verification check fails
**Detection:** grep finds unexpected output
**Resolution:** Identify which TC fix is incomplete; route back
**Spec/Gate:** Acceptance criteria

## Task-specific review checklist

1. [ ] All tests pass (pytest exit 0)
2. [ ] 3D pilot passes (exit 0)
3. [ ] Note pilot passes (exit 0)
4. [ ] No section names in url_path (TC-998 verified)
5. [ ] No double content in content_preview (TC-1000 verified)
6. [ ] cross_links are absolute URLs (TC-1001 verified)
7. [ ] Evidence bundle complete

## Deliverables

- reports/agents/agent_c/TC-1003/evidence.md
- reports/agents/agent_c/TC-1003/self_review.md
- output/tc1003_tests.txt
- output/tc1003-3d/ (pilot output)
- output/tc1003-note/ (pilot output)

## Acceptance checks

1. [ ] pytest tests/ passes (exit 0)
2. [ ] pilot-aspose-3d-foss-python passes (exit 0)
3. [ ] pilot-aspose-note-foss-python passes (exit 0)
4. [ ] All TC-998 through TC-1002 acceptance criteria verified

## E2E verification

```bash
# Complete verification sequence
.venv/Scripts/python.exe -m pytest tests/ -x
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/tc1003-3d
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/tc1003-note

# Verify all criteria
echo "=== TC-998: url_path check ==="
grep -rE '"url_path".*/(docs|kb|blog|reference|products)/' specs/pilots/*/expected_page_plan.json || echo "PASS: no section in url_path"

echo "=== TC-1000: content_preview structure ==="
ls output/tc1003-3d/*/content_preview/ 2>/dev/null || echo "No output yet"

echo "=== TC-1001: cross_links absolute ==="
grep -A5 '"cross_links"' output/tc1003-3d/*/artifacts/page_plan.json 2>/dev/null | head -20 || echo "No output yet"
```

**Expected artifacts:**
- **output/tc1003_tests.txt** - All tests PASS
- **output/tc1003-3d/** - Pilot 3D exit_code=0
- **output/tc1003-note/** - Pilot Note exit_code=0
- **evidence.md** - All verification checks documented

## Integration boundary proven

**Upstream:** TC-998 through TC-1002 complete all fixes
**Downstream:** CI/CD uses verified codebase
**Contract:** All pilots pass, all tests pass, all acceptance criteria met

## Self-review

12-dimension self-review required. All dimensions >=4/5.
