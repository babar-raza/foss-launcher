---
id: TC-984
title: "W4 IAPlanner: Evidence-Driven Page Scaling + Configurable Page Requirements"
status: Done
owner: Agent-B
updated: "2026-02-06"
depends_on:
  - TC-983
priority: P1
spec_ref: fad128dc63faba72bad582ddbc15c19a4c29d684
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w4_ia_planner/worker.py
  - reports/agents/agent_b/TC-984/**
evidence_required:
  - reports/agents/agent_b/TC-984/evidence.md
  - reports/agents/agent_b/TC-984/self_review.md
---

## Objective

Implement evidence-driven page scaling and configurable page requirements in W4 IAPlanner. Richer repos must produce more pages than simpler repos. Mandatory page lists come from ruleset config (TC-983) instead of hardcoded logic.

## Required spec references

- specs/06_page_planning.md — Optional Page Selection Algorithm (lines 257-287), Launch Tier Adjustments
- specs/08_content_distribution_strategy.md — Content distribution rules, configurable page requirements
- specs/rulesets/ruleset.v1.yaml — mandatory_pages, optional_page_policies, family_overrides (from TC-983)
- specs/schemas/page_plan.schema.json — evidence_volume, effective_quotas fields (from TC-983)

## Scope

### In scope
1. Soften CI-absent tier reduction in `determine_launch_tier()` (~line 412)
2. Add `load_and_merge_page_requirements()` function — reads ruleset mandatory_pages + family_overrides
3. Add `compute_evidence_volume()` function — quality_score formula from spec 06
4. Add `compute_effective_quotas()` function — tier coefficients × evidence targets
5. Add `generate_optional_pages()` function — spec 06 Optional Page Selection Algorithm
6. Refactor `execute_ia_planner()` to use config-driven mandatory pages + evidence scaling
7. Add evidence_volume + effective_quotas to page_plan.json output dict

### Out of scope
- Spec/schema changes (TC-983, must be complete first)
- W7 Gate 14 changes (TC-985)
- Test creation (TC-986)

## Inputs
- Updated specs from TC-983
- src/launch/workers/w4_ia_planner/worker.py (current)
- Plan: plans/from_chat/20260205_160000_evidence_driven_page_scaling.md

## Outputs
- Updated src/launch/workers/w4_ia_planner/worker.py with 5 new functions + refactored execute_ia_planner

## Allowed paths
- src/launch/workers/w4_ia_planner/worker.py
- reports/agents/agent_b/TC-984/**

## Implementation steps

1. **Soften tier reduction** (~line 412-423): Change CI-absent logic to only reduce when BOTH CI and tests are missing. If CI absent but tests present, log adjustment but keep tier.
2. **Add load_and_merge_page_requirements()** (~after line 478): Read mandatory_pages + optional_page_policies from ruleset sections. Read family_overrides for current product_slug. Merge: global mandatory_pages + family mandatory_pages (union, deduplicate by slug). Return per-section merged config.
3. **Add compute_evidence_volume()**: Compute quality_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1). Return dict with total_score, claim_count, snippet_count, api_symbol_count, workflow_count, key_feature_count.
4. **Add compute_effective_quotas()**: Apply tier coefficients (minimal=0.3, standard=0.7, rich=1.0) to ruleset max_pages. Compute evidence-based section targets. Clamp to [min_pages, tier_adjusted_max].
5. **Add generate_optional_pages()**: For each section, use optional_page_policies to generate candidates from evidence (per_feature, per_workflow, per_key_feature, per_api_symbol). Score each candidate. Sort deterministically. Select top N = effective_max - mandatory_count. Deduplicate by slug against existing pages.
6. **Refactor execute_ia_planner()** (~lines 1718-1820): Call load_and_merge_page_requirements(). Call compute_evidence_volume(). Call compute_effective_quotas(). Replace hardcoded plan_pages_for_section with config-driven mandatory page creation. Replace static quota lookup with effective quotas. Add evidence-driven optional page injection after main loop.
7. **Add output fields**: Include evidence_volume and effective_quotas in page_plan dict.

## Failure modes

### Failure mode 1: Existing tests break

**Detection:** pytest failures after implementation changes.
**Resolution:** Update test assertions for new page counts; ensure plan_pages_for_section backward-compatible for direct callers.
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Slug collisions in merged config

**Detection:** check_url_collisions() catches duplicates during page planning.
**Resolution:** Deduplicate by slug in merge step (family extends, not replaces).
**Spec/Gate:** W4 URL collision check

### Failure mode 3: Non-deterministic output

**Detection:** Two runs produce different page_plan.json SHA.
**Resolution:** All lists sorted, all scoring deterministic, all tie-breaking by slug asc.
**Spec/Gate:** Gate T, specs/10_determinism_and_caching.md

## Task-specific review checklist

1. [ ] determine_launch_tier() only reduces to minimal when BOTH CI and tests are absent
2. [ ] load_and_merge_page_requirements() correctly merges global + family (union by slug)
3. [ ] compute_evidence_volume() matches spec 06 quality_score formula
4. [ ] compute_effective_quotas() respects tier coefficients and ruleset max_pages ceiling
5. [ ] generate_optional_pages() sorts by (priority asc, quality_score desc, slug asc)
6. [ ] execute_ia_planner() reads mandatory_pages from config (not hardcoded)
7. [ ] page_plan output includes evidence_volume + effective_quotas
8. [ ] All new functions are deterministic (sorted inputs, no randomness)

## Deliverables

- Updated src/launch/workers/w4_ia_planner/worker.py
- reports/agents/agent_b/TC-984/evidence.md
- reports/agents/agent_b/TC-984/self_review.md

## Acceptance checks

- [ ] All 5 new functions exist and are callable
- [ ] execute_ia_planner() uses config-driven mandatory pages
- [ ] evidence_volume and effective_quotas present in page_plan output
- [ ] Tier reduction softened (CI-absent alone doesn't force minimal)
- [ ] No regressions in existing test suite

## E2E verification

```bash
# Run unit tests for W4
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_evidence_scaling.py -v

# Run both pilots end-to-end
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/e2e-984
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/e2e-984-note
```

**Expected artifacts:**
- **src/launch/workers/w4_ia_planner/worker.py** - Contains compute_evidence_volume, compute_effective_quotas, generate_optional_pages, load_and_merge_page_requirements
- **tests/unit/workers/test_w4_evidence_scaling.py** - All tests PASS
- **output/e2e-984/** - Pilot 3D pass with exit_code=0
- **output/e2e-984-note/** - Pilot Note pass with exit_code=0

## Integration boundary proven

**Upstream:** TC-983 specs define evidence_volume formula, mandatory_pages config, and family_overrides merge behavior.
**Downstream:** W5 consumes page_plan with evidence_volume and effective_quotas; W7 Gate 14 validates mandatory pages.
**Contract:** W4 outputs page_plan.json with evidence_volume and effective_quotas fields. Config-driven mandatory pages replace hardcoded logic.

## Self-review

12-dimension self-review required per reports/templates/self_review_12d.md.
All dimensions must score >=4/5 with concrete evidence.
