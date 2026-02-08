---
id: "TC-902"
title: "W4 Template Enumeration with Quotas"
status: In-Progress
owner: "agent-2"
updated: "2026-02-01"
depends_on:
  - TC-430
allowed_paths:
  - plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_tc_902_w4_template_enumeration.py
  - reports/agents/**/TC-902/**
evidence_required:
  - reports/agents/agent-2/TC-902/report.md
  - reports/agents/agent-2/TC-902/self_review.md
  - runs/tc902_w4_template_enum_*/tc902_evidence.zip
spec_ref: d1d440f4b809781c9bf78516deac8168c54f22a6
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-902 — W4 Template Enumeration with Quotas

## Objective

Implement template enumeration in W4 IAPlanner that reads ruleset quotas (min_pages and max_pages per section), enumerates all available templates in the specs/templates hierarchy, identifies mandatory vs optional templates, fills placeholders from evidence_map, caps total at max_pages with deterministic ordering, and generates correct V2 output paths per subdomain.

## Scope

### In scope

1. **Template Discovery**:
   - Scan specs/templates/<subdomain>/<family>/<locale>/<platform>/ for V2 layout
   - Scan specs/templates/<subdomain>/<family>/<locale>/ for V1 layout
   - Identify all template files (*.md)
   - Parse template frontmatter for metadata

2. **Template Classification**:
   - Mandatory: _index.md files or templates marked with required: true in frontmatter
   - Optional: All other templates
   - Variant detection: Extract variant from filename (e.g., .variant-minimal.md, .variant-standard.md)

3. **Quota Application**:
   - Start with all mandatory templates (MUST include all)
   - Add optional templates up to max_pages limit
   - Sort optional templates deterministically (by path/slug)
   - Select top N optional templates where N = max_pages - mandatory_count

4. **Placeholder Filling**:
   - Replace __LOCALE__ with run_config.locale (default: en)
   - Replace __PLATFORM__ with run_config.platform (default: python)
   - Replace __FAMILY__ with product_slug
   - Fill content placeholders from evidence_map where available

5. **Output Path Generation** (V2 layout):
   - products: content/products.aspose.org/<family>/<locale>/<platform>/
   - docs: content/docs.aspose.org/<family>/<locale>/<platform>/
   - reference: content/reference.aspose.org/<family>/<locale>/<platform>/
   - kb: content/kb.aspose.org/<family>/<locale>/<platform>/
   - blog: content/blog.aspose.org/<family>/<platform>/

### Out of scope

- Template discovery performance optimization with many templates
- Complex placeholder filling when evidence_map is sparse
- Auto-generation of templates (only enumeration of existing)
- Migration of existing content

## Required spec references

- specs/06_page_planning.md (Page planning algorithm)
- specs/20_rulesets_and_templates_registry.md (Template resolution)
- specs/32_platform_aware_content_layout.md (V2 layout)
- specs/33_public_url_mapping.md (URL path computation)
- specs/schemas/ruleset.schema.json (Ruleset schema with max_pages)

## Inputs

| Input | Type | Source | Validation |
|-------|------|--------|------------|
| ruleset | YAML | specs/rulesets/ruleset.v1.yaml | Must have min_pages and max_pages per section |
| templates | Markdown | specs/templates/ hierarchy | Must have valid frontmatter |
| evidence_map | Dict | W2 FactsBuilder output | Used for placeholder filling |
| run_config | RunConfig | Orchestrator | Must have locale, platform, product_slug |

## Outputs

| Output | Type | Destination | Schema |
|--------|------|-------------|--------|
| page_plan | JSON | artifacts/page_plan.json | page_plan.schema.json |
| enumerated_templates | List | In-memory | List[Dict[str, Any]] |

## Allowed paths

- plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_tc_902_w4_template_enumeration.py
- reports/agents/**/TC-902/**

### Allowed paths rationale

This task implements template enumeration logic in W4 IAPlanner worker, requiring changes to the worker implementation and corresponding unit tests. Evidence reports are needed to track implementation and validation.

## Implementation steps

1. **Implement Template Enumeration Functions** in src/launch/workers/w4_ia_planner/worker.py:

   a. `enumerate_templates(template_dir: Path, subdomain: str, family: str, locale: str, platform: str) -> List[Dict[str, Any]]`
      - Scan template directory for all .md files
      - Parse frontmatter for metadata
      - Return list of template specifications

   b. `classify_templates(templates: List[Dict]) -> Tuple[List[Dict], List[Dict]]`
      - Split into mandatory and optional lists
      - Mandatory: _index.md or required: true in frontmatter
      - Return (mandatory_templates, optional_templates)

   c. `select_templates_with_quota(mandatory: List[Dict], optional: List[Dict], max_pages: int) -> List[Dict]`
      - Include all mandatory templates
      - Sort optional templates deterministically
      - Select top N optional where N = max_pages - len(mandatory)
      - Return combined list

   d. `fill_template_placeholders(template_path: str, evidence_map: Dict, run_config: RunConfig) -> Dict[str, Any]`
      - Replace __LOCALE__, __PLATFORM__, __FAMILY__ placeholders
      - Fill content placeholders from evidence_map
      - Return page specification dictionary

2. **Modify plan_pages_for_section()**:
   - Call enumerate_templates() for the section
   - Classify templates into mandatory/optional
   - Apply quota logic with select_templates_with_quota()
   - Fill placeholders and generate page specs
   - Return enriched page list

3. **Add Deterministic Ordering**:
   - Sort templates by path (lexicographic)
   - Sort by slug as tiebreaker
   - Document sorting algorithm in code comments

4. **Create Unit Tests** in tests/unit/workers/test_tc_902_w4_template_enumeration.py:
   - Test template enumeration with quota
   - Test deterministic ordering
   - Test V2 path generation
   - Test placeholder filling
   - Test mandatory template enforcement

5. **Update Taskcard Index**:
   - Verify TC-902 is in plans/taskcards/INDEX.md

6. **Run Validation**:
   - validate_swarm_ready.py
   - pytest suite

7. **Create Evidence Bundle**:
   - Create runs/tc902_w4_template_enum_<timestamp>/
   - Generate tc902_evidence.zip

## Test plan

### Test 1: Template Enumeration with Quota
Given:
- 20 optional templates in specs/templates/docs.aspose.org/cells/en/python/
- 3 mandatory templates (_index.md files)
- max_pages = 10

Expected:
- All 3 mandatory templates selected
- 7 optional templates selected (sorted deterministically)
- Total = 10 pages

### Test 2: Deterministic Ordering
Given:
- Same input data run twice

Expected:
- Identical output (same templates in same order)

### Test 3: V2 Path Generation
Given:
- Template for docs section
- family = cells, locale = en, platform = python

Expected:
- output_path = content/docs.aspose.org/cells/en/python/<slug>.md
- url_path = /cells/python/docs/<slug>/

### Test 4: Placeholder Filling
Given:
- Template with __PLATFORM__, __LOCALE__ placeholders
- evidence_map with relevant data

Expected:
- Placeholders replaced correctly
- Evidence references populated

### Test 5: Mandatory Template Enforcement
Given:
- 5 mandatory templates
- max_pages = 3

Expected:
- All 5 mandatory templates included (quota exceeded)
- Warning logged about quota breach
- Page plan still valid

## E2E verification

**Concrete command(s) to run:**
```bash
# Activate .venv
.venv/Scripts/activate

# Run TC-902 unit tests
python -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py -v

# Validate swarm readiness
python tools/validate_swarm_ready.py

# Run full test suite
python -m pytest -q
```

**Expected artifacts:**
- src/launch/workers/w4_ia_planner/worker.py (with template enumeration functions)
- tests/unit/workers/test_tc_902_w4_template_enumeration.py (unit tests)
- Evidence bundle in runs/tc902_w4_template_enum_*/tc902_evidence.zip

**Success criteria:**
- [ ] Template enumeration discovers all templates in hierarchy
- [ ] Mandatory templates always included regardless of quota
- [ ] Optional templates selected up to max_pages limit
- [ ] Output deterministic (same input → same output)
- [ ] Correct V2 paths generated per subdomain
- [ ] Placeholder filling works from evidence_map
- [ ] Unit tests pass with 100% coverage of new code
- [ ] Integration with existing W4 worker seamless
- [ ] validate_swarm_ready.py passes

## Integration boundary proven

What upstream/downstream wiring was validated:
- Upstream: TC-430 (W4 IAPlanner base implementation)
- Upstream: TC-901 (Ruleset schema with max_pages)
- Downstream: W5 SectionWriter (TC-440) will consume enumerated templates
- Contracts: page_plan.schema.json, template frontmatter structure

## Failure modes

### Failure mode 1: Template discovery performance degrades with many templates
**Detection:** Slow enumeration (>10s for 1000 templates); pilot E2E runs timeout at W4 stage
**Resolution:** Add caching of template discovery results; implement lazy loading of template content; consider pagination for very large template sets; profile code to identify bottlenecks (filesystem I/O vs parsing); optimize with Path.glob() instead of os.walk()
**Spec/Gate:** specs/06_page_planning.md (performance requirements for page planning)

### Failure mode 2: Placeholder filling fails when evidence_map is sparse
**Detection:** Missing placeholder values in generated pages; warnings logged about unfilled placeholders; KeyErrors during template processing
**Resolution:** Use sensible defaults for common placeholders (__LOCALE__=en, __PLATFORM__=python); document required evidence keys in specs/03; add fallback logic to skip optional placeholders gracefully; validate evidence_map completeness before template enumeration
**Spec/Gate:** specs/03_product_facts_and_evidence.md (evidence structure and required fields)

### Failure mode 3: Quota logic edge case - mandatory templates exceed max_pages
**Detection:** More pages than max_pages in output page_plan.json; quota enforcement appears broken
**Resolution:** Log warning when mandatory templates exceed quota; include all mandatory templates regardless of max_pages limit; document behavior in quota enforcement section; update acceptance criteria to allow quota override for mandatory content; verify downstream workers can handle quota overrides
**Spec/Gate:** specs/06_page_planning.md (quota enforcement and mandatory template rules)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] Template enumeration is deterministic (sorted output)
- [ ] Mandatory templates always included (quota override logic)
- [ ] V2 path generation follows specs/32_platform_aware_content_layout.md
- [ ] Placeholder filling handles missing evidence gracefully
- [ ] No hardcoded paths (all paths from config/ruleset)
- [ ] Evidence files include validation outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME) in code

## Deliverables

- Code:
  - src/launch/workers/w4_ia_planner/worker.py (with template enumeration)
  - tests/unit/workers/test_tc_902_w4_template_enumeration.py (unit tests)
- Documentation:
  - plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md (this file)
- Reports (required):
  - reports/agents/agent-2/TC-902/report.md
  - reports/agents/agent-2/TC-902/self_review.md
  - runs/tc902_w4_template_enum_*/tc902_evidence.zip

## Acceptance checks

- [ ] enumerate_templates() implemented and working
- [ ] classify_templates() splits mandatory/optional correctly
- [ ] select_templates_with_quota() applies quota logic
- [ ] fill_template_placeholders() replaces placeholders
- [ ] plan_pages_for_section() updated to use new functions
- [ ] Deterministic ordering verified (sorted by path/slug)
- [ ] All unit tests pass
- [ ] validate_swarm_ready.py passes
- [ ] pytest suite passes (no regressions)
- [ ] Evidence bundle created
- [ ] No write fence violations

## Self-review

Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
