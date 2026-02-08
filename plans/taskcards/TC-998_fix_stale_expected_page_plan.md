---
id: TC-998
title: "Fix Stale expected_page_plan.json url_path Values"
status: Draft
priority: P1
owner: Agent-B
updated: "2026-02-06"
tags: ["fixtures", "url_path", "pilot"]
depends_on: []
allowed_paths:
  - specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
  - specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
  - reports/agents/agent_b/TC-998/**
evidence_required:
  - reports/agents/agent_b/TC-998/evidence.md
  - reports/agents/agent_b/TC-998/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-998 — Fix Stale expected_page_plan.json url_path Values

## Objective

Remove section names (docs, kb, blog, reference, products) from url_path values in both pilot expected_page_plan.json files. Section is encoded in subdomain, not path.

## Problem Statement

The expected_page_plan.json files contain stale url_path values that include section names in the path (e.g., `/3d/python/kb/faq/`). Per specs/33_public_url_mapping.md, section names belong in subdomains (kb.aspose.org), not paths. The correct format is `/<family>/<platform>/<slug>/`.

## Required spec references

- specs/33_public_url_mapping.md lines 344-350 (URL format: section = subdomain, not path)
- specs/21_worker_contracts.md (W4 page_plan output format)

## Scope

### In scope
- Fix url_path values in specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- Fix url_path values in specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- Remove section names from all url_path entries

### Out of scope
- Modifying W4 compute_url_path() (already correct)
- Changing actual page_plan generation logic
- Other pilot config changes

## Inputs
- Current expected_page_plan.json files with stale url_path values
- Correct URL format: `/<family>/<platform>/<slug>/` (no section)

## Outputs
- Updated expected_page_plan.json files with correct url_path format
- Evidence report

## Allowed paths

- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- reports/agents/agent_b/TC-998/**

### Allowed paths rationale
Fixing test fixtures only. No production code changes.

## Implementation steps

### Step 1: Identify incorrect url_path values in 3D pilot
Search for url_path values containing section names:
```bash
grep -n "url_path.*/(docs|kb|blog|reference|products)/" specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
```

### Step 2: Fix url_path in 3D pilot
For each incorrect url_path:
- `/3d/python/docs/getting-started/` → `/3d/python/getting-started/`
- `/3d/python/kb/faq/` → `/3d/python/faq/`
- `/3d/python/reference/api-overview/` → `/3d/python/api-overview/`
- `/3d/python/blog/announcement/` → `/3d/python/announcement/`

### Step 3: Fix url_path in Note pilot
Same transformation for pilot-aspose-note-foss-python.

### Step 4: Verify changes
```bash
# Should return no matches
grep -E "url_path.*/(docs|kb|blog|reference|products)/" specs/pilots/*/expected_page_plan.json
```

## Failure modes

### Failure mode 1: Regex replacement breaks JSON
**Detection:** JSON parse error when loading expected_page_plan.json
**Resolution:** Validate JSON after edit; use proper JSON tools not sed
**Spec/Gate:** Gate 1 (Schema Validation)

### Failure mode 2: Missed url_path entries
**Detection:** grep still finds section names in url_path after fix
**Resolution:** Re-run search and fix any remaining entries
**Spec/Gate:** Acceptance criteria verification

### Failure mode 3: Cross_links also contain stale paths
**Detection:** cross_links array values have section in path
**Resolution:** Apply same fix to cross_links if present
**Spec/Gate:** W4 output consistency

## Task-specific review checklist

1. [ ] All url_path values in 3D pilot corrected
2. [ ] All url_path values in Note pilot corrected
3. [ ] No url_path contains section name (docs, kb, blog, reference, products)
4. [ ] JSON files remain valid after edits
5. [ ] cross_links also checked and fixed if needed
6. [ ] Changes match spec 33 URL format

## Deliverables

- Updated specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- Updated specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- reports/agents/agent_b/TC-998/evidence.md
- reports/agents/agent_b/TC-998/self_review.md

## Acceptance checks

1. [ ] No url_path in expected_page_plan.json contains section names
2. [ ] Both JSON files parse without errors
3. [ ] Format matches /<family>/<platform>/<slug>/

## E2E verification

```bash
# Verify no section names in url_path
grep -E '"url_path".*/(docs|kb|blog|reference|products)/' specs/pilots/*/expected_page_plan.json
# Expected: no output

# Validate JSON structure
.venv/Scripts/python.exe -c "import json; json.load(open('specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json')); print('3D OK')"
.venv/Scripts/python.exe -c "import json; json.load(open('specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json')); print('Note OK')"
```

**Expected artifacts:**
- **specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json** - All url_path without section names
- **specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json** - All url_path without section names

## Integration boundary proven

**Upstream:** W4 generate page_plan.json with correct url_path (already fixed by HEAL-BUG1)
**Downstream:** VFV harness compares generated vs expected page_plan
**Contract:** url_path format is /<family>/<platform>/<slug>/ with section in subdomain

## Self-review

12-dimension self-review required. All dimensions >=4/5.
