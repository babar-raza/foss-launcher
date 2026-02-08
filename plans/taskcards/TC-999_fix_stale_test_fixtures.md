---
id: TC-999
title: "Fix Stale Test Fixture url_path in test_tc_450"
status: Complete
priority: P2
owner: Agent-C
updated: "2026-02-06"
tags: ["tests", "fixtures", "url_path"]
depends_on:
  - TC-998
allowed_paths:
  - tests/unit/workers/test_tc_450_linker_and_patcher.py
  - reports/agents/agent_c/TC-999/**
evidence_required:
  - reports/agents/agent_c/TC-999/evidence.md
  - reports/agents/agent_c/TC-999/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-999 — Fix Stale Test Fixture url_path in test_tc_450

## Objective

Fix the url_path value in test_tc_450_linker_and_patcher.py fixture to not include section name. Currently has `/test-product/python/docs/getting-started/`, should be `/test-product/python/getting-started/`.

## Problem Statement

The test fixture contains a stale url_path that includes the section name "docs" in the path. Per specs/33_public_url_mapping.md, section names belong in subdomains, not paths.

## Required spec references

- specs/33_public_url_mapping.md lines 344-350 (URL format)
- plans/taskcards/00_TASKCARD_CONTRACT.md (test requirements)

## Scope

### In scope
- Fix url_path in test fixture (line ~78)
- Verify test still passes after fix

### Out of scope
- Other test files
- Production code changes

## Inputs
- Current test file with stale url_path

## Outputs
- Fixed test file
- Test pass confirmation

## Allowed paths

- tests/unit/workers/test_tc_450_linker_and_patcher.py
- reports/agents/agent_c/TC-999/**

## Implementation steps

### Step 1: Locate stale url_path
```bash
grep -n "url_path.*docs" tests/unit/workers/test_tc_450_linker_and_patcher.py
```

### Step 2: Fix url_path
Change:
```python
"url_path": "/test-product/python/docs/getting-started/"
```
To:
```python
"url_path": "/test-product/python/getting-started/"
```

### Step 3: Run test
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_450_linker_and_patcher.py -v
```

## Failure modes

### Failure mode 1: Test fails after fix
**Detection:** pytest exit code non-zero
**Resolution:** Check if other parts of test depend on the old path; update accordingly
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Multiple stale fixtures
**Detection:** grep finds more than one stale url_path
**Resolution:** Fix all instances
**Spec/Gate:** Consistency

### Failure mode 3: Import errors
**Detection:** ModuleNotFoundError
**Resolution:** Ensure .venv activated
**Spec/Gate:** Environment setup

## Task-specific review checklist

1. [x] url_path fixed to not include section name
2. [x] Test passes after fix
3. [x] No other stale url_path in same file
4. [x] Format matches /<family>/<platform>/<slug>/
5. [x] No regressions in other tests
6. [x] Evidence captured

## Deliverables

- Updated tests/unit/workers/test_tc_450_linker_and_patcher.py
- reports/agents/agent_c/TC-999/evidence.md
- reports/agents/agent_c/TC-999/self_review.md

## Acceptance checks

1. [x] url_path does not contain section name
2. [x] Test passes
3. [x] No regressions

## E2E verification

```bash
# Run specific test
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_450_linker_and_patcher.py -v

# Verify no section in url_path
grep -E '"url_path".*/(docs|kb|blog|reference|products)/' tests/unit/workers/test_tc_450_linker_and_patcher.py
# Expected: no output
```

**Expected artifacts:**
- **tests/unit/workers/test_tc_450_linker_and_patcher.py** - url_path without section
- **pytest output** - All tests PASS

## Integration boundary proven

**Upstream:** TC-998 fixes expected_page_plan.json format
**Downstream:** CI runs test suite
**Contract:** Test fixtures use correct url_path format

## Self-review

12-dimension self-review required. All dimensions >=4/5.
