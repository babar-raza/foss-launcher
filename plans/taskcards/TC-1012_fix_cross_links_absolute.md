---
id: TC-1012
title: "Fix expected_page_plan.json cross_links to ABSOLUTE URLs"
status: Done
priority: Normal
owner: Agent-B
updated: "2026-02-07"
tags: ["cross_links", "absolute_urls", "pilots"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1012*.md
  - specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
  - specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
  - reports/agents/agent_b/TC-1012/**
evidence_required:
  - reports/agents/agent_b/TC-1012/evidence.md
  - reports/agents/agent_b/TC-1012/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1012 --- Fix expected_page_plan.json cross_links to ABSOLUTE URLs

## Objective
Update both pilot expected_page_plan.json files to use absolute URLs (https://subdomain/...) in cross_links, matching the W4 IAPlanner output after TC-1001 made cross_links absolute.

## Problem Statement
TC-1001 changed W4 to produce absolute cross_links using `build_absolute_public_url()` (e.g. `https://docs.aspose.org/3d/python/getting-started/`). However, the expected_page_plan.json files still contain relative paths (e.g. `/3d/python/getting-started/`), causing VFV mismatch failures during pilot verification.

## Required spec references
- src/launch/resolvers/public_urls.py (build_absolute_public_url function)
- src/launch/workers/w4_ia_planner/worker.py (add_cross_links function, lines 1537-1609)
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- plans/taskcards/00_TASKCARD_CONTRACT.md

## Scope

### In scope
- Update cross_links in pilot-aspose-3d-foss-python/expected_page_plan.json from relative to absolute
- Update cross_links in pilot-aspose-note-foss-python/expected_page_plan.json from relative to absolute
- Match exact URL format produced by build_absolute_public_url()

### Out of scope
- Modifying W4 IAPlanner logic
- Changing url_path fields (those remain relative)
- Modifying public_urls.py resolver

## Inputs
- Current expected_page_plan.json files with relative cross_links
- build_absolute_public_url() subdomain mapping: docs->docs.aspose.org, reference->reference.aspose.org, etc.
- add_cross_links() rules: docs->reference, kb->docs, blog->products

## Outputs
- Updated pilot-aspose-3d-foss-python/expected_page_plan.json with absolute cross_links
- Updated pilot-aspose-note-foss-python/expected_page_plan.json with absolute cross_links
- Evidence report at reports/agents/agent_b/TC-1012/evidence.md
- Self-review at reports/agents/agent_b/TC-1012/self_review.md

## Allowed paths
- plans/taskcards/TC-1012*.md
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- reports/agents/agent_b/TC-1012/**

### Allowed paths rationale
TC-1012 only modifies the expected_page_plan.json golden files to match the actual W4 output after TC-1001.

## Implementation steps

### Step 1: Analyze current cross_links
Read both expected_page_plan.json files and identify all cross_links entries.

3D pilot cross_links:
- docs/getting-started -> reference/api-overview: `/3d/python/api-overview/` must become `https://reference.aspose.org/3d/python/api-overview/`
- kb/faq -> docs/getting-started: `/3d/python/getting-started/` must become `https://docs.aspose.org/3d/python/getting-started/`
- blog/announcement -> products/overview: `/3d/python/overview/` must become `https://products.aspose.org/3d/python/overview/`

Note pilot cross_links:
- docs/getting-started -> reference/api-overview: `/note/python/api-overview/` must become `https://reference.aspose.org/note/python/api-overview/`
- kb/faq -> docs/getting-started: `/note/python/getting-started/` must become `https://docs.aspose.org/note/python/getting-started/`
- blog/announcement -> products/overview: `/note/python/overview/` must become `https://products.aspose.org/note/python/overview/`

### Step 2: Update both files
Replace each relative cross_link with its absolute equivalent.

### Step 3: Run tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --timeout=120
```

## Failure modes

### Failure mode 1: Wrong subdomain in cross_link URL
**Detection:** VFV mismatch shows expected vs actual URL difference in subdomain
**Resolution:** Re-check add_cross_links() mapping: docs->reference, kb->docs, blog->products; verify subdomain_map in build_absolute_public_url()
**Spec/Gate:** src/launch/resolvers/public_urls.py subdomain_map

### Failure mode 2: Trailing slash mismatch
**Detection:** VFV reports URL path difference (missing or extra trailing slash)
**Resolution:** Ensure all URLs end with trailing slash per _normalize_path() in public_urls.py
**Spec/Gate:** specs/33_public_url_mapping.md URL normalization

### Failure mode 3: JSON syntax error after edit
**Detection:** JSON parse error in test or pilot run
**Resolution:** Validate JSON with `python -c "import json; json.load(open('file.json'))"`
**Spec/Gate:** page_plan.schema.json

## Task-specific review checklist
1. [ ] All cross_links use https:// scheme
2. [ ] Subdomain matches target page's section (docs->docs.aspose.org, reference->reference.aspose.org, etc.)
3. [ ] URL path matches build_absolute_public_url() output format
4. [ ] All URLs have trailing slash
5. [ ] JSON is valid after edit
6. [ ] No changes to non-cross_links fields
7. [ ] Both pilot files updated consistently
8. [ ] Cross-link direction matches add_cross_links() rules

## Deliverables
- Modified specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- Modified specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- Evidence at reports/agents/agent_b/TC-1012/evidence.md
- Self-review at reports/agents/agent_b/TC-1012/self_review.md

## Acceptance checks
1. [ ] All cross_links in 3D pilot expected_page_plan.json are absolute URLs
2. [ ] All cross_links in Note pilot expected_page_plan.json are absolute URLs
3. [ ] URLs match build_absolute_public_url() output exactly
4. [ ] All tests pass
5. [ ] Evidence report written

## Preconditions / dependencies
- TC-1001 (Make cross_links Absolute URLs in W4) is COMPLETE
- Python virtual environment activated (.venv)

## Test plan
1. Run full test suite to verify no regressions
2. Verify JSON validity of both files

## Self-review

### 12D Checklist
1. **Determinism:** Golden files are static; no runtime nondeterminism
2. **Dependencies:** No new dependencies
3. **Documentation:** TC-1012 taskcard documents the change
4. **Data preservation:** Only cross_links fields modified; all other fields unchanged
5. **Deliberate design:** URLs follow exact build_absolute_public_url() format
6. **Detection:** VFV mismatch would detect any remaining relative URLs
7. **Diagnostics:** N/A (static golden files)
8. **Defensive coding:** N/A (static golden files)
9. **Direct testing:** Full test suite run
10. **Deployment safety:** Golden file update; no runtime impact
11. **Delta tracking:** Only cross_links fields in 2 JSON files
12. **Downstream impact:** Fixes VFV mismatch for pilot verification

### Verification results
- [ ] Tests: PENDING
- [ ] JSON validity: PENDING
- [ ] Evidence captured: reports/agents/agent_b/TC-1012/evidence.md

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --timeout=120
```

## Integration boundary proven
**Upstream:** W4 IAPlanner produces page_plan.json with absolute cross_links via build_absolute_public_url()
**Downstream:** VFV harness compares actual page_plan.json against expected_page_plan.json
**Contract:** cross_links must be absolute URLs with format https://{subdomain}/{product}/{platform}/{slug}/

## Evidence Location
`reports/agents/agent_b/TC-1012/evidence.md`
