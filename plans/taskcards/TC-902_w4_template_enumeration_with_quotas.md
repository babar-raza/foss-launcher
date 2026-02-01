# TC-902: W4 Template Enumeration with Quotas

## Status
ACTIVE

## Context
W4 currently falls back to 1-page-per-section when evidence is sparse. We need deterministic template enumeration with mandatory/optional quotas to generate MANY pages by discovering and enumerating all available templates in the specs/templates hierarchy.

## Mission
Implement template enumeration in W4 IAPlanner that:
1. Reads ruleset to get min_pages and max_pages per section
2. Enumerates all templates in specs/templates/<subdomain>/<family>/
3. Identifies mandatory vs optional templates
4. Fills placeholders from evidence_map when possible
5. Caps total at max_pages with deterministic ordering
6. Generates correct V2 output paths per subdomain

## Specifications

### Template Enumeration Algorithm
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

### Ruleset Integration
Extend ruleset schema to support max_pages per section:
```yaml
sections:
  products:
    min_pages: 1
    max_pages: 10
  docs:
    min_pages: 2
    max_pages: 20
  reference:
    min_pages: 1
    max_pages: 15
  kb:
    min_pages: 3
    max_pages: 12
  blog:
    min_pages: 1
    max_pages: 5
```

## Implementation Tasks

### 1. Extend Ruleset Schema
File: specs/schemas/ruleset.schema.json
- Add max_pages field to sectionMinPages definition
- Update all section objects to support optional max_pages

### 2. Implement Template Enumeration Functions
File: src/launch/workers/w4_ia_planner/worker.py

New functions:
- `enumerate_templates(template_dir: Path, subdomain: str, family: str, locale: str, platform: str) -> List[Dict[str, Any]]`
  - Scan template directory for all .md files
  - Parse frontmatter for metadata
  - Return list of template specifications

- `classify_templates(templates: List[Dict]) -> Tuple[List[Dict], List[Dict]]`
  - Split into mandatory and optional lists
  - Mandatory: _index.md or required: true in frontmatter
  - Return (mandatory_templates, optional_templates)

- `select_templates_with_quota(mandatory: List[Dict], optional: List[Dict], max_pages: int) -> List[Dict]`
  - Include all mandatory templates
  - Sort optional templates deterministically
  - Select top N optional where N = max_pages - len(mandatory)
  - Return combined list

- `fill_template_placeholders(template_path: str, evidence_map: Dict, run_config: RunConfig) -> Dict[str, Any]`
  - Replace __LOCALE__, __PLATFORM__, __FAMILY__ placeholders
  - Fill content placeholders from evidence_map
  - Return page specification dictionary

### 3. Modify plan_pages_for_section()
Update the existing function to:
- Call enumerate_templates() for the section
- Classify templates into mandatory/optional
- Apply quota logic with select_templates_with_quota()
- Fill placeholders and generate page specs
- Return enriched page list

### 4. Add Deterministic Ordering
Ensure all template enumeration is deterministic:
- Sort templates by path (lexicographic)
- Sort by slug as tiebreaker
- Document sorting algorithm in code comments

## Test Cases

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

## Acceptance Criteria
- [ ] Template enumeration discovers all templates in hierarchy
- [ ] Mandatory templates always included regardless of quota
- [ ] Optional templates selected up to max_pages limit
- [ ] Output deterministic (same input → same output)
- [ ] Correct V2 paths generated per subdomain
- [ ] Placeholder filling works from evidence_map
- [ ] Unit tests pass with 100% coverage of new code
- [ ] Integration with existing W4 worker seamless
- [ ] Schema validation passes

## Files Changed
- plans/taskcards/TC-902_w4_template_enumeration_with_quotas.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_tc_902_w4_template_enumeration.py
- specs/schemas/ruleset.schema.json (optional enhancement)

## Dependencies
- TC-430 (W4 IAPlanner base implementation)
- specs/templates/ hierarchy must exist
- V2 layout per specs/32_platform_aware_content_layout.md

## Risks
- Template discovery performance with many templates
- Placeholder filling complexity if evidence_map is sparse
- Quota logic edge cases (mandatory > max_pages)

## Evidence Bundle
Create: runs/tc902_w4_template_enum_20260201_HHMMSS/tc902_evidence.zip

Contents:
- Test output (pytest -v)
- Sample page_plan.json with enumerated templates
- Validation results
- Code coverage report

## References
- specs/06_page_planning.md (Page planning algorithm)
- specs/20_rulesets_and_templates_registry.md (Template resolution)
- specs/32_platform_aware_content_layout.md (V2 layout)
- specs/33_public_url_mapping.md (URL path computation)
