---
id: TC-953
title: "Page Inventory Contract and Quotas"
status: Draft
priority: Critical
owner: "PAGE_QUOTA_ENFORCER"
updated: "2026-02-03"
tags: ["page-quotas", "w4", "ia-planner", "mandatory-pages", "optional-pages", "pilot"]
depends_on: ["TC-430", "TC-700", "TC-940"]
allowed_paths:
  - plans/taskcards/TC-953_page_inventory_contract_and_quotas.md
  - specs/schemas/ruleset.schema.json
  - specs/rulesets/ruleset.v1.yaml
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_quota_enforcement.py
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-953/**
evidence_required:
  - reports/agents/<agent>/TC-953/report.md
  - reports/agents/<agent>/TC-953/self_review.md
  - reports/agents/<agent>/TC-953/test_output.txt
  - reports/agents/<agent>/TC-953/page_count_comparison.txt
  - reports/agents/<agent>/TC-953/w4_quota_diff.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-953: Page Inventory Contract and Quotas

## Objective
Implement page quota enforcement in W4 IAPlanner to ensure pilots generate realistic page inventories (8-35 pages) instead of minimal coverage (5 pages), with proper mandatory/optional page selection.

## Problem Statement
Current pilot runs generate only **5 pages total** across all subdomains, suggesting:
1. W4 IAPlanner is only generating mandatory pages
2. Optional pages are not being added up to max_pages quotas
3. Some subdomains may be missing entirely (e.g., kb section)

**Evidence:** Page inventory from finalization bundle shows minimal coverage, preventing realistic validation.

## Required spec references
- specs/06_page_planning.md (W4 IAPlanner page quota requirements)
- specs/07_section_templates.md (Mandatory and optional page definitions)
- specs/rulesets/ruleset.v1.yaml (Page quota configuration)
- specs/schemas/ruleset.schema.json (Ruleset schema validation)

## Scope

### In scope
- Verify W4 IAPlanner enforces min_pages and max_pages per section
- Adjust pilot quotas in ruleset.v1.yaml or pilot configs (products=6, docs=10, reference=6, kb=10, blog=3)
- Ensure all mandatory pages included before optional pages
- Implement deterministic optional page selection (priority + alpha sort)
- Add unit tests verifying quota enforcement (min, max, mandatory-first)
- Document page count comparison (before/after) in evidence

### Out of scope
- Changing mandatory page definitions (defined in TC-940)
- Modifying template pack structure (TC-700)
- Altering evidence-driven prioritization algorithm (separate concern)
- Production quota values (focus on pilots)

## Inputs
- Current W4 IAPlanner generating only 5 pages total
- specs/rulesets/ruleset.v1.yaml with current quota definitions
- TC-940 mandatory page list (products=1, docs=2, reference=1, kb=3, blog=1)
- Page inventory from finalization bundle showing 5 pages

## Outputs
- Updated specs/rulesets/ruleset.v1.yaml with pilot quotas (if needed)
- Modified src/launch/workers/w4_ia_planner/worker.py with quota enforcement (if missing)
- Unit test in tests/unit/workers/test_w4_quota_enforcement.py
- Page count comparison showing increase from 5 to ~35 pages
- page_plan.json from pilot run with expanded page inventory

## Allowed paths
- plans/taskcards/TC-953_page_inventory_contract_and_quotas.md
- specs/schemas/ruleset.schema.json
- specs/rulesets/ruleset.v1.yaml
- specs/06_page_planning.md
- specs/07_section_templates.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_quota_enforcement.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-953/**

## Implementation steps

### Step 1: Verify current W4 quota enforcement
Read src/launch/workers/w4_ia_planner/worker.py to check if enforce_quota() or similar logic exists

### Step 2: Adjust pilot quotas (if needed)
Update specs/rulesets/ruleset.v1.yaml:
```yaml
sections:
  products: {min_pages: 1, max_pages: 6}
  docs: {min_pages: 2, max_pages: 10}
  reference: {min_pages: 1, max_pages: 6}
  kb: {min_pages: 3, max_pages: 10}
  blog: {min_pages: 1, max_pages: 3}
```

### Step 3: Add/verify quota enforcement in W4 (if missing)
Implement enforce_quota() function in W4 worker.py

### Step 4: Add unit tests
Create tests/unit/workers/test_w4_quota_enforcement.py with 4 test cases

### Step 5: Run pilot and compare page counts
```bash
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python
jq '.pages | length' runs/<run_id>/artifacts/page_plan.json
```

## Task-specific review checklist
1. [ ] W4 separates mandatory pages from optional pages before quota enforcement
2. [ ] Mandatory pages always included regardless of max_pages constraint
3. [ ] Optional pages sorted deterministically (priority first, then alphabetically by slug)
4. [ ] min_pages validation raises error if not enough pages generated
5. [ ] max_pages enforcement truncates optional pages list
6. [ ] Pilot quotas adjusted to meaningful levels (products=6, docs=10, reference=6, kb=10, blog=3)
7. [ ] Unit test verifies min_pages enforcement
8. [ ] Unit test verifies max_pages enforcement
9. [ ] Unit test verifies mandatory pages included when max_pages is tight
10. [ ] Page count comparison shows increase from 5 to ~35 pages

## Failure modes

### Failure mode 1: Page count still 5 after quota adjustment
**Detection:** Pilot run produces page_plan.json with only 5 pages despite updated quotas
**Resolution:** Verify W4 actually reads updated ruleset.v1.yaml; check that pilot config references correct ruleset version; ensure W4 enforce_quota() function is being called in page planning logic; add logging to show quota enforcement
**Spec/Gate:** specs/06_page_planning.md (Page planning requirements), Gate H (IA planning gate)

### Failure mode 2: Mandatory pages missing from output
**Detection:** page_plan.json missing required pages like "Getting Started" or "FAQ"
**Resolution:** Verify mandatory page list in TC-940 matches W4 implementation; check that enforce_quota() includes all mandatory pages before adding optional; ensure mandatory flag is set correctly in page metadata; validate that min_pages check includes mandatory count
**Spec/Gate:** specs/07_section_templates.md (Mandatory page definitions), TC-940

### Failure mode 3: Optional page selection non-deterministic
**Detection:** Two VFV runs produce different optional page sets despite same input
**Resolution:** Ensure optional pages sorted by (priority, slug) before truncation; verify no timestamp or random values used in selection; check that evidence coverage scores are deterministic; add test comparing two runs with identical inputs
**Spec/Gate:** specs/10_determinism_and_caching.md (Deterministic operations)

## Deliverables
- Updated specs/rulesets/ruleset.v1.yaml (if quotas adjusted)
- Modified src/launch/workers/w4_ia_planner/worker.py (if enforcement added)
- Unit test in tests/unit/workers/test_w4_quota_enforcement.py
- reports/agents/<agent>/TC-953/page_count_comparison.txt
- reports/agents/<agent>/TC-953/w4_quota_diff.txt
- reports/agents/<agent>/TC-953/test_output.txt
- reports/agents/<agent>/TC-953/report.md
- reports/agents/<agent>/TC-953/self_review.md

## Acceptance checks
1. W4 IAPlanner MUST include ALL mandatory pages for each section (per TC-940):
   - products: Overview/Landing (1 page)
   - docs: Getting Started + at least one how-to (min 2 pages)
   - reference: API Overview/Landing (1 page)
   - kb: FAQ + Known Limitations + Basic troubleshooting (3 pages)
   - blog: Announcement post (1 page)
   **Minimum total: 8 pages (not 5)**

2. W4 MUST add optional pages deterministically up to max_pages per section:
   - products: up to 10 pages (add Features, Quickstart, Supported Environments, etc.)
   - docs: up to 50 pages (add workflow how-tos)
   - reference: up to 100 pages (add module/class pages)
   - kb: up to 30 pages (add FAQs, troubleshooting guides)
   - blog: up to 20 pages (add deep-dive posts)

3. Optional page selection is deterministic and evidence-driven:
   - Prioritize pages with strong claim coverage
   - Prioritize frequently used features (snippet usage)
   - Sort deterministically (alphabetically by slug within priority tier)

4. For pilots, quotas should be meaningful but not excessive. Suggested pilot quotas:
   - products: 6 pages (landing, features, quickstart, environments, installation, FAQ)
   - docs: 10 pages (getting started, 9 how-tos)
   - reference: 6 pages (landing, 5 key modules/classes)
   - kb: 10 pages (FAQ, limitations, 8 troubleshooting guides)
   - blog: 3 pages (announcement, deep-dive, release notes)
   **Pilot total: ~35 pages (vs current 5)**

5. Unit test verifies:
   - Given ruleset with quotas, W4 generates at least min_pages per section
   - Given abundant evidence, W4 stops at max_pages per section
   - Mandatory pages are always included
   - Page count per section matches expected range

6. Gate H passes after fix
7. Unit tests pass: pytest tests/unit/workers/test_w4_quota_enforcement.py
8. Page count comparison shows ~7x increase (5 → ~35 pages)
9. All sections meet min_pages requirements
10. No section exceeds max_pages limits

## E2E verification
Run pilot and verify page counts:
```bash
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python
jq '.pages | length' runs/<run_id>/artifacts/page_plan.json
jq '.pages | group_by(.section) | map({section: .[0].section, count: length})' runs/<run_id>/artifacts/page_plan.json
```

Expected artifacts:
- page_plan.json with ~35 pages total (vs current 5)
- Section breakdown: products=6, docs=10, reference=6, kb=10, blog=3
- All mandatory pages present in output
- Optional pages selected deterministically
- W4 logs show quota enforcement ("Applying quotas: products min=1 max=6")

## Integration boundary proven
**Upstream:** W4 receives ruleset configuration with min_pages/max_pages per section; reads mandatory page definitions from specs/07_section_templates.md
**Downstream:** W4 outputs page_plan.json with correct page count per section; W5 receives expanded page list for draft generation
**Contract:** W4 must enforce min_pages (raise error if not met); must enforce max_pages (truncate optional pages); must always include ALL mandatory pages regardless of max_pages constraint

## Self-review
- [ ] Quota enforcement logic verified in W4 worker.py
- [ ] Mandatory pages included before optional pages
- [ ] Optional page selection is deterministic
- [ ] min_pages validation raises error if needed
- [ ] max_pages enforced by truncating optional list
- [ ] Unit tests cover all 4 scenarios (min, max, mandatory-first, determinism)
- [ ] All required sections present per taskcard contract
- [ ] E2E verification includes page count comparison commands
