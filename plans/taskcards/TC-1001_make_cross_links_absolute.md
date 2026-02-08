---
id: TC-1001
title: "Make cross_links Absolute URLs in W4"
status: Complete
priority: P2
owner: Agent-B
updated: "2026-02-06"
tags: ["w4", "cross_links", "url"]
depends_on: []
allowed_paths:
  - src/launch/workers/w4_ia_planner/worker.py
  - reports/agents/agent_b/TC-1001/**
evidence_required:
  - reports/agents/agent_b/TC-1001/evidence.md
  - reports/agents/agent_b/TC-1001/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1001 — Make cross_links Absolute URLs in W4

## Objective

Modify the add_cross_links() function in W4 IAPlanner to generate absolute URLs (https://...) instead of relative url_path values, using the existing build_absolute_public_url() function.

## Problem Statement

The add_cross_links() function at lines 1536-1572 stores relative paths in cross_links:
```python
page["cross_links"] = [p["url_path"] for p in by_section["reference"][:2]]
```
User requirement: cross_links should contain absolute URLs like `https://docs.aspose.org/cells/python/overview/`.

## Required spec references

- specs/33_public_url_mapping.md (absolute URL format)
- specs/06_page_planning.md (cross_links definition)
- src/launch/resolvers/public_urls.py (build_absolute_public_url function)

## Scope

### In scope
- Modify add_cross_links() to use build_absolute_public_url()
- Import build_absolute_public_url from resolvers

### Out of scope
- Changing url_path format (remains relative)
- Modifying build_absolute_public_url() itself
- Other W4 functions

## Inputs
- Current add_cross_links() with relative paths
- build_absolute_public_url() at src/launch/resolvers/public_urls.py:153-234

## Outputs
- Updated add_cross_links() generating absolute URLs
- page_plan.json with absolute cross_links

## Allowed paths

- src/launch/workers/w4_ia_planner/worker.py
- reports/agents/agent_b/TC-1001/**

## Implementation steps

### Step 1: Add import
At top of w4_ia_planner/worker.py, add:
```python
from src.launch.resolvers.public_urls import build_absolute_public_url
```

### Step 2: Locate add_cross_links function
```bash
grep -n "def add_cross_links" src/launch/workers/w4_ia_planner/worker.py
```

### Step 3: Modify cross_links generation
Change from:
```python
page["cross_links"] = [p["url_path"] for p in by_section["reference"][:2]]
```
To:
```python
page["cross_links"] = [
    build_absolute_public_url(
        section=p["section"],
        family=product_slug,
        locale="en",
        platform=p.get("platform", "python"),
        slug=p["slug"],
    )
    for p in by_section["reference"][:2]
]
```

### Step 4: Apply same pattern to all cross_link sources
Check all places where cross_links is set and apply absolute URL generation.

### Step 5: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v
```

## Failure modes

### Failure mode 1: Import error
**Detection:** ModuleNotFoundError for build_absolute_public_url
**Resolution:** Check import path; may need from launch.resolvers.public_urls
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Missing parameters for build_absolute_public_url
**Detection:** TypeError: missing required argument
**Resolution:** Check function signature; ensure all required params provided
**Spec/Gate:** Function contract

### Failure mode 3: Tests expect relative paths
**Detection:** Test assertions fail on cross_links format
**Resolution:** Update test expectations to match new absolute format
**Spec/Gate:** Gate T (tests)

## Task-specific review checklist

1. [ ] Import added correctly
2. [ ] All cross_links generation uses build_absolute_public_url
3. [ ] Absolute URLs have correct scheme (https://)
4. [ ] Subdomain matches section (docs.aspose.org for docs, etc.)
5. [ ] Tests pass or updated
6. [ ] Evidence captured

## Deliverables

- Updated src/launch/workers/w4_ia_planner/worker.py
- reports/agents/agent_b/TC-1001/evidence.md
- reports/agents/agent_b/TC-1001/self_review.md

## Acceptance checks

1. [ ] cross_links in page_plan.json are absolute URLs
2. [ ] URLs have format https://<subdomain>/<family>/<platform>/<slug>/
3. [ ] Tests pass

## E2E verification

```bash
# Run W4 tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v

# Run pilot and check cross_links
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/tc1001
grep -A5 '"cross_links"' output/tc1001/*/artifacts/page_plan.json | head -20
# Should show: https://... URLs
```

**Expected artifacts:**
- **src/launch/workers/w4_ia_planner/worker.py** - Modified add_cross_links()
- **page_plan.json** - cross_links with absolute URLs

## Integration boundary proven

**Upstream:** Pages with sections provide slug, section, platform for URL generation
**Downstream:** cross_links consumed by W5 for link insertion (currently unused but ready)
**Contract:** cross_links contains absolute URLs: https://<subdomain>/<family>/<platform>/<slug>/

## Self-review

12-dimension self-review required. All dimensions >=4/5.
