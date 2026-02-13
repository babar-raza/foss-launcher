---
id: TC-1201
title: "Page Expansion — Ruleset Quota Expansion & New Policy Registration"
status: Draft
priority: Critical
owner: "Agent D (Docs & Specs)"
updated: "2026-02-11"
tags: ["ruleset", "quotas", "page-expansion", "phase-1"]
depends_on: ["TC-1200"]
allowed_paths:
  - plans/taskcards/TC-1201_page_expansion_ruleset_quotas.md
  - specs/rulesets/ruleset.v1.yaml
evidence_required:
  - reports/agents/AGENT_D/TC-1201/evidence.md
  - reports/agents/AGENT_D/TC-1201/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1201 — Page Expansion — Ruleset Quota Expansion & New Policy Registration

## Objective
Raise per-section `max_pages` quotas and register all 7 new `optional_page_policy` sources in `ruleset.v1.yaml` so that W4's `generate_optional_pages()` can discover and invoke them. This is the config-layer enablement that unlocks all page expansion strategies.

## Required spec references
- specs/08_content_distribution_strategy.md (updated by TC-1200 — defines the 7 new policy source contracts)
- specs/rulesets/ruleset.v1.yaml (target file — current quotas and policies)
- specs/schemas/run_config.schema.json (updated by TC-1200 — page_expansion config keys)

## Scope

### In scope
1. **Raise max_pages** per section to accommodate expanded page counts:
   - products: 1 → 1 (no change — landing page only)
   - docs: 10 → 50 (format conversion + tutorials + examples + sub-pages)
   - reference: 6 → 40 (per-namespace pages)
   - kb: 10 → 30 (per-feature showcases + FAQ decomposition + deep dives)
   - blog: 3 → 10 (deep dives + theme overviews)
2. **Register 7 new optional_page_policies** in appropriate sections with priority ordering
3. **Add family_overrides** for 3d, cells, note to include family-specific format pairs
4. **Maintain backward compatibility** — min_pages unchanged, existing mandatory pages unchanged

### Out of scope
- Spec/schema changes (TC-1200)
- W2/W4/W5 code changes (TC-1202–TC-1206)
- Template creation (TC-1205)

## Inputs
- Current specs/rulesets/ruleset.v1.yaml
- TC-1200 spec definitions for policy source contracts

## Outputs
- specs/rulesets/ruleset.v1.yaml (UPDATED — raised quotas, 7 new policies, family overrides)

## Allowed paths
- plans/taskcards/TC-1201_page_expansion_ruleset_quotas.md
- specs/rulesets/ruleset.v1.yaml

### Allowed paths rationale
Single-file config change. All policy semantics are defined in specs (TC-1200). This taskcard only registers them in the ruleset.

## Implementation steps

### Step 1: Read current ruleset state
Read `specs/rulesets/ruleset.v1.yaml` in full. Adapt to whatever the current state is — do NOT assume specific line numbers.

**Resilience note**: If max_pages values have already been raised by another agent, only raise further if needed. If some policies are already registered, skip those. Use the section names as anchors, not line numbers.

### Step 2: Raise max_pages quotas
For each section, update `max_pages` to the new values. Keep `min_pages` unchanged.

```yaml
sections:
  docs:
    max_pages: 50    # was 10 — format pairs + tutorials + examples + sub-pages
  reference:
    max_pages: 40    # was 6 — per-namespace reference pages
  kb:
    max_pages: 30    # was 10 — showcases + FAQ topics + deep dives
  blog:
    max_pages: 10    # was 3 — deep dives + theme overviews
```

### Step 3: Register new optional_page_policies per section

**docs section** — Add after existing `per_workflow` (priority 2):
```yaml
optional_page_policies:
  # ... existing per_feature (1), per_workflow (2)
  - page_role: "format_conversion"
    source: "per_format_pair"
    priority: 3
  - page_role: "tutorial"
    source: "per_workflow_tutorial"
    priority: 4
  - page_role: "example_walkthrough"
    source: "per_example"
    priority: 5
```

**reference section** — Add after existing `per_api_symbol` (priority 1):
```yaml
optional_page_policies:
  # ... existing per_api_symbol (1)
  - page_role: "namespace_reference"
    source: "per_namespace_reference"
    priority: 2
```

**kb section** — Add after existing `per_key_feature` (priority 1):
```yaml
optional_page_policies:
  # ... existing per_key_feature (1)
  - page_role: "topic_faq"
    source: "per_faq_topic"
    priority: 2
  - page_role: "feature_deep_dive"
    source: "per_feature_combination"
    priority: 3
```

**blog section** — Add after existing `per_deep_dive` (priority 2):
```yaml
optional_page_policies:
  # ... existing per_deep_dive (2)
  - page_role: "theme_overview"
    source: "per_theme_group"
    priority: 3
```

### Step 4: Add family-specific format pair hints
Under `family_overrides`, add format pair hints so W2 knows what to look for:

```yaml
family_overrides:
  "3d":
    page_expansion:
      known_formats: ["FBX", "GLTF", "GLB", "OBJ", "STL", "3DS", "PLY", "DAE", "USD", "USDZ"]
  "cells":
    page_expansion:
      known_formats: ["XLSX", "XLS", "CSV", "PDF", "HTML", "ODS", "JSON", "XML", "TXT"]
  "note":
    page_expansion:
      known_formats: ["ONE", "PDF", "HTML", "PNG", "JPEG", "BMP", "GIF"]
```

### Step 5: Validate YAML syntax
Parse the updated file to ensure valid YAML.

## Failure modes

### Failure mode 1: YAML syntax error breaks ruleset loading
**Detection:** W4 fails to parse ruleset.v1.yaml. Python `yaml.safe_load()` raises exception.
**Resolution:** Validate YAML after edit with `python -c "import yaml; yaml.safe_load(open('specs/rulesets/ruleset.v1.yaml'))"`. Fix indentation (YAML is indent-sensitive).
**Spec/Gate:** CONTRIBUTING.md rule #6

### Failure mode 2: Priority collisions between existing and new policies
**Detection:** Two policies in the same section have the same priority integer. Sorting becomes nondeterministic.
**Resolution:** Verify unique priorities per section. New policies use higher numbers than existing ones.
**Spec/Gate:** specs/08_content_distribution_strategy.md priority ordering rules

### Failure mode 3: max_pages too low for evidence-rich repos
**Detection:** W4 generates fewer pages than evidence supports because quota caps at max_pages.
**Resolution:** The values chosen (50/40/30/10) are based on worst-case estimates. If insufficient, raise further. The system already caps at max_pages gracefully.
**Spec/Gate:** specs/08 evidence-driven scaling rules

## Task-specific review checklist
1. [ ] max_pages raised for docs (50), reference (40), kb (30), blog (10)
2. [ ] min_pages unchanged for all sections
3. [ ] All 7 new policies registered in correct sections
4. [ ] Priority numbers are unique within each section
5. [ ] Priority numbers are higher than existing policies (no reordering)
6. [ ] family_overrides include known_formats for 3d, cells, note
7. [ ] Existing mandatory_pages untouched
8. [ ] Existing optional_page_policies untouched (only appended)
9. [ ] YAML syntax valid (parseable)
10. [ ] No duplicate policy source names within a section

## Deliverables
- specs/rulesets/ruleset.v1.yaml (UPDATED)
- reports/agents/AGENT_D/TC-1201/evidence.md
- reports/agents/AGENT_D/TC-1201/self_review.md

## Acceptance checks
1. [ ] YAML parses without error
2. [ ] max_pages values match spec (50/40/30/10)
3. [ ] 7 new policies registered across 4 sections
4. [ ] All priorities unique per section
5. [ ] family_overrides include known_formats
6. [ ] Existing config untouched (additive only)

## Preconditions / dependencies
- TC-1200 completed (specs define the policy contracts this taskcard registers)

## Self-review
[To be completed by Agent D after implementation]
