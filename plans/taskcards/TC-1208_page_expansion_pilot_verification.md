---
id: TC-1208
title: "Page Expansion — Pilot Config Updates & E2E Verification"
status: Draft
priority: Critical
owner: "Agent C (Testing & Verification)"
updated: "2026-02-11"
tags: ["pilots", "verification", "page-expansion", "phase-5"]
depends_on: ["TC-1201", "TC-1202", "TC-1203", "TC-1204", "TC-1205", "TC-1206", "TC-1207"]
allowed_paths:
  - plans/taskcards/TC-1208_page_expansion_pilot_verification.md
  - configs/pilots/pilot-aspose-3d-foss-python.yaml
  - configs/pilots/pilot-aspose-note-foss-python.yaml
  - configs/pilots/pilot-aspose-cells-foss-python.yaml
  - specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
  - specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
  - specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
  - reports/agents/AGENT_C/TC-1208/evidence.md
  - reports/agents/AGENT_C/TC-1208/self_review.md
  - reports/agents/AGENT_C/TC-1208/page_count_comparison.md
evidence_required:
  - reports/agents/AGENT_C/TC-1208/evidence.md
  - reports/agents/AGENT_C/TC-1208/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1208 — Page Expansion — Pilot Config Updates & E2E Verification

## Objective
Update all pilot configs to enable page expansion features, run all pilots end-to-end, verify page count increase, validate content quality, and produce a comparison report documenting the before/after page counts per section.

## Required spec references
- specs/schemas/run_config.schema.json (page_expansion config object)
- configs/pilots/ (pilot config files)
- specs/pilots/ (pinned pilot configs)
- All TC-120x taskcards (understanding what was implemented)

## Scope

### In scope
1. **Update pilot configs** — Add `page_expansion` section to all 3 pilots:
   - `pilot-aspose-3d-foss-python`: Enable all policies, add 3D-specific format pair overrides
   - `pilot-aspose-note-foss-python`: Enable all policies, add Note-specific format pair overrides
   - `pilot-aspose-cells-foss-python`: Enable all policies, add Cells-specific format pair overrides
2. **Run baselines** — Run each pilot WITHOUT page expansion to capture baseline page counts
3. **Run expanded** — Run each pilot WITH page expansion to capture expanded page counts
4. **Validate content** — For each pilot:
   - All pages have non-empty content
   - No raw `__TOKEN__` strings in output
   - Claim markers `[claim: ...]` present in content pages
   - Hugo frontmatter valid
   - No duplicate URLs
   - W7 validation passes
5. **Produce comparison report** — Per-section page count: before vs after, per pilot
6. **Determinism check** — Run expanded pilot twice, verify identical output

### Out of scope
- Code changes (all code is done in TC-1202–TC-1206)
- Test writing (TC-1207)
- Spec changes (TC-1200)

## Inputs
- All implemented code from TC-1200–TC-1207
- Existing pilot configs
- Existing pilot run outputs (for baseline comparison)

## Outputs
- Updated pilot configs (3 configs/ + 3 specs/pilots/)
- reports/agents/AGENT_C/TC-1208/page_count_comparison.md (comparison table)
- reports/agents/AGENT_C/TC-1208/evidence.md
- reports/agents/AGENT_C/TC-1208/self_review.md

## Allowed paths
- plans/taskcards/TC-1208_page_expansion_pilot_verification.md
- configs/pilots/pilot-aspose-3d-foss-python.yaml
- configs/pilots/pilot-aspose-note-foss-python.yaml
- configs/pilots/pilot-aspose-cells-foss-python.yaml
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
- specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml
- specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
- reports/agents/AGENT_C/TC-1208/evidence.md
- reports/agents/AGENT_C/TC-1208/self_review.md
- reports/agents/AGENT_C/TC-1208/page_count_comparison.md

### Allowed paths rationale
Pilot configs and reports only. No code, no specs, no shared libraries.

## Implementation steps

### Step 1: Read current pilot configs
Read all 6 pilot config files (3 in configs/, 3 in specs/pilots/) to understand current structure.

**Resilience note**: Config structure may have changed. Add `page_expansion` section using whatever YAML structure the configs currently use. Do NOT overwrite existing fields.

### Step 2: Add page_expansion config to 3D pilot
```yaml
page_expansion:
  enabled_policies: []  # All enabled
  format_pairs_override:
    add:
      - ["FBX", "USD"]
      - ["FBX", "USDZ"]
    remove: []
  reference_granularity: "namespace"
  max_feature_sub_pages: 4
  combination_top_n: 5
```

### Step 3: Add page_expansion config to Note pilot
```yaml
page_expansion:
  enabled_policies: []
  format_pairs_override:
    add: []
    remove: []
  reference_granularity: "namespace"
  max_feature_sub_pages: 3  # Note has fewer features, 3 sub-pages sufficient
  combination_top_n: 4
```

### Step 4: Add page_expansion config to Cells pilot
```yaml
page_expansion:
  enabled_policies: []
  format_pairs_override:
    add:
      - ["XLSX", "NUMBERS"]
    remove: []
  reference_granularity: "namespace"
  max_feature_sub_pages: 4
  combination_top_n: 5
```

### Step 5: Run baseline pilots (without page expansion)
```bash
# Temporarily use old configs or set enabled_policies to disable all
# Run each pilot and count pages
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/baseline_3d
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output tmp/baseline_note
```

Record page counts per section from page_plan.json.

### Step 6: Run expanded pilots
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/expanded_3d
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output tmp/expanded_note
```

### Step 7: Validate expanded output
For each pilot:
1. Parse page_plan.json — verify all pages have required fields
2. Check content files — verify non-empty, no raw tokens
3. Check W7 validation report — verify all gates pass
4. Check URL uniqueness — no duplicates
5. Check Hugo frontmatter — valid YAML

### Step 8: Run determinism check
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/determinism_3d_run1
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/determinism_3d_run2
# Compare outputs
diff -r tmp/determinism_3d_run1 tmp/determinism_3d_run2
```

### Step 9: Produce comparison report
Create `reports/agents/AGENT_C/TC-1208/page_count_comparison.md`:

```markdown
# Page Expansion — Before/After Comparison

## pilot-aspose-3d-foss-python

| Section | Baseline | Expanded | Delta | New Page Types |
|---------|----------|----------|-------|----------------|
| products | X | X | +0 | — |
| docs | X | X | +N | format_conversion, tutorial, example, sub-pages |
| reference | X | X | +N | namespace_reference |
| kb | X | X | +N | topic_faq, feature_deep_dive |
| blog | X | X | +N | theme_overview |
| **Total** | **X** | **X** | **+N** | |

## pilot-aspose-note-foss-python
[Same table format]

## Summary
- Average page count increase: X%
- New page types contributing most: ...
- Sub-pages generated: N for M parent features
- Format conversion pages: N pairs
```

## Failure modes

### Failure mode 1: Pilot fails to run with new config
**Detection:** `run_pilot.py` exits non-zero. Error in W4 or W5 processing new page types.
**Resolution:** Check error log. Common causes: missing template, unknown page_role in W5 dispatch, schema validation error. Report blocker to relevant TC (1203/1204/1206).
**Spec/Gate:** Pilot E2E requirement

### Failure mode 2: Page count doesn't increase
**Detection:** Expanded run has same page count as baseline.
**Resolution:** Check page_plan.json for evidence volume. If format_capabilities is empty, TC-1202 may have issues. If optional pages are 0, check if policies are registered in ruleset (TC-1201).
**Spec/Gate:** specs/08 evidence-driven scaling

### Failure mode 3: Determinism check fails
**Detection:** Two runs produce different output.
**Resolution:** Ensure PYTHONHASHSEED=0. Check for non-deterministic dict iteration in new code. Report to TC-1203/1204/1206.
**Spec/Gate:** specs/34 Guarantee E (determinism)

## Task-specific review checklist
1. [ ] All 6 pilot configs updated with page_expansion section
2. [ ] Baseline page counts captured for both pilots
3. [ ] Expanded page counts captured for both pilots
4. [ ] Page count increased for all non-products sections
5. [ ] All content files non-empty
6. [ ] No raw `__TOKEN__` strings in output
7. [ ] W7 validation passes for expanded runs
8. [ ] No duplicate URLs
9. [ ] Determinism verified (2 runs identical)
10. [ ] Comparison report produced with per-section breakdown

## Deliverables
- Updated pilot configs (6 files)
- reports/agents/AGENT_C/TC-1208/page_count_comparison.md
- reports/agents/AGENT_C/TC-1208/evidence.md
- reports/agents/AGENT_C/TC-1208/self_review.md

## Acceptance checks
1. [ ] Both pilots complete E2E with exit code 0
2. [ ] Page count increased vs baseline
3. [ ] All content validates
4. [ ] Determinism verified
5. [ ] Comparison report complete

## Preconditions / dependencies
- ALL TC-1200 through TC-1207 completed
- Pilots can run end-to-end (existing infrastructure works)

## Self-review
[To be completed by Agent C after implementation]
