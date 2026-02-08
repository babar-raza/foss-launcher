---
id: TC-1000
title: "Fix W6 content_preview Double Directory Bug"
status: Complete
priority: P2
owner: Agent-B
updated: "2026-02-06"
tags: ["w6", "bug", "content_preview"]
depends_on: []
allowed_paths:
  - src/launch/workers/w6_linker_and_patcher/worker.py
  - tests/unit/workers/test_w6_content_export.py
  - reports/agents/agent_b/TC-1000/**
evidence_required:
  - reports/agents/agent_b/TC-1000/evidence.md
  - reports/agents/agent_b/TC-1000/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1000 — Fix W6 content_preview Double Directory Bug

## Objective

Fix the double "content" directory bug in W6 LinkerAndPatcher where content_preview_dir incorrectly appends "content" when patch paths already include it, resulting in content_preview/content/content/... structure.

## Problem Statement

At line 867 of w6_linker_and_patcher/worker.py:
```python
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
```
Since patch["path"] already starts with "content/", this creates: content_preview/content/content/...
Should be: content_preview/content/...

## Required spec references

- specs/21_worker_contracts.md (W6 output structure)

## Scope

### In scope
- Fix content_preview_dir path in W6 worker.py (line 867)
- Update test expectations if needed

### Out of scope
- Other W6 functionality
- Patch path format changes

## Inputs
- Current W6 with double-dir bug
- Patch paths like "content/docs.aspose.org/..."

## Outputs
- Fixed W6 worker
- Correct content_preview structure

## Allowed paths

- src/launch/workers/w6_linker_and_patcher/worker.py
- tests/unit/workers/test_w6_content_export.py
- reports/agents/agent_b/TC-1000/**

## Implementation steps

### Step 1: Locate the bug
```bash
grep -n "content_preview.*content" src/launch/workers/w6_linker_and_patcher/worker.py
```

### Step 2: Fix the path
Change line 867 from:
```python
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
```
To:
```python
content_preview_dir = run_layout.run_dir / "content_preview"
```

### Step 3: Update test expectations
Check test_w6_content_export.py for path expectations and update if needed.

### Step 4: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w6_content_export.py -v
```

## Failure modes

### Failure mode 1: Tests fail after fix
**Detection:** pytest exit code non-zero
**Resolution:** Update test expectations to match new path structure
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Other code depends on double-content structure
**Detection:** Other tests fail; runtime errors
**Resolution:** Search codebase for references to double content path
**Spec/Gate:** Regression testing

### Failure mode 3: Patch paths don't include "content/"
**Detection:** Files written to wrong location
**Resolution:** Verify patch["path"] format; adjust fix if needed
**Spec/Gate:** W6 contract

## Task-specific review checklist

1. [x] Line 867 fixed to not double "content"
2. [x] Tests updated and passing
3. [x] content_preview structure is content_preview/content/... (not content_preview/content/content/...)
4. [x] No regressions in W6 tests
5. [x] Patch path format verified
6. [x] Evidence captured

## Deliverables

- Updated src/launch/workers/w6_linker_and_patcher/worker.py
- Updated tests/unit/workers/test_w6_content_export.py (if needed)
- reports/agents/agent_b/TC-1000/evidence.md
- reports/agents/agent_b/TC-1000/self_review.md

## Acceptance checks

1. [x] No double "content" in path
2. [x] Tests pass (20/20 W6 tests passing)
3. [x] Pilot runs produce correct structure

## E2E verification

```bash
# Run W6 tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w6_content_export.py -v

# Run pilot and check structure
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/tc1000
ls output/tc1000/*/content_preview/
# Should show: content/ (not content/content/)
```

**Expected artifacts:**
- **src/launch/workers/w6_linker_and_patcher/worker.py** - Fixed line 867
- **content_preview/** - Correct structure

## Integration boundary proven

**Upstream:** W5 produces patches with path like "content/docs.aspose.org/..."
**Downstream:** content_preview consumed by humans or CI for review
**Contract:** content_preview/content/<subdomain>/... structure

## Self-review

12-dimension self-review required. All dimensions >=4/5.
