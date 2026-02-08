# Implementation Plan: HEAL-BUG2 - Defensive Index Page De-duplication

## Task Overview
**Phase**: Phase 2 - DEFENSIVE
**Agent**: Agent B (Implementation)
**Task ID**: HEAL-BUG2

**Context**:
- Bug: Multiple `_index.md` template variants for the same section cause URL collisions
- Phase 0 (HEAL-BUG4): Eliminated most collisions by filtering obsolete templates
- This Phase: Add defensive de-duplication in case variants still collide
- Expected Impact: MEDIUM (Phase 0 should have fixed root cause)

## Objectives
1. Implement defensive de-duplication logic in `classify_templates()` function
2. Ensure deterministic template selection (alphabetical by template_path)
3. Add comprehensive unit tests to verify de-duplication
4. Document whether Phase 0 eliminated all collisions (this is defensive)

## Current State Analysis

### File to Modify
- **Location**: `src/launch/workers/w4_ia_planner/worker.py`
- **Function**: `classify_templates()` (lines 941-971)
- **Current Logic**:
  - Classifies templates as mandatory or optional based on `is_mandatory` flag
  - Filters optional templates by launch tier variant
  - No de-duplication logic present

### Phase 0 (HEAL-BUG4) Context
- Lines 877-884 in `enumerate_templates()` already skip obsolete blog templates with `__LOCALE__`
- This should have eliminated most URL collisions at the source
- Our de-duplication is defensive - may never trigger if Phase 0 worked

## Implementation Strategy

### 1. Add De-duplication Logic to classify_templates()

**Key Changes**:
- Add `seen_index_pages` dictionary to track processed index pages
- Key format: `f"{section}_{family}_{platform}"`
- Sort templates deterministically BEFORE processing (alphabetical by template_path)
- For each template with slug="index":
  - Check if section_key already in seen_index_pages
  - If yes: skip duplicate with debug log
  - If no: add to seen_index_pages and process

**Implementation Pattern**:
```python
def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Classify templates into mandatory and optional based on launch tier.
    De-duplicates index pages per section to prevent URL collisions.
    """
    mandatory = []
    optional = []

    # Track index pages per section to prevent duplicates
    seen_index_pages = {}  # Key: f"{section}_{family}_{platform}", Value: template

    # Sort templates for deterministic processing
    sorted_templates = sorted(templates, key=lambda t: (
        t["section"],
        t.get("product_slug", ""),
        t.get("platform", ""),
        t["slug"],
        t.get("template_path", ""),  # Alphabetical variant selection
    ))

    for template in sorted_templates:
        slug = template["slug"]
        section = template["section"]
        family = template.get("product_slug", "")
        platform = template.get("platform", "")

        # De-duplicate index pages per section
        if slug == "index":
            section_key = f"{section}_{family}_{platform}"
            if section_key in seen_index_pages:
                logger.debug(f"[W4] Skipping duplicate index page: {template.get('template_path')}")
                continue
            seen_index_pages[section_key] = template

        # Classify as mandatory or optional (existing logic)
        if template["is_mandatory"]:
            mandatory.append(template)
        else:
            variant = template["variant"]
            if launch_tier == "minimal" and variant in ["minimal", "default"]:
                optional.append(template)
            elif launch_tier == "standard" and variant in ["minimal", "standard", "default"]:
                optional.append(template)
            elif launch_tier == "rich":
                optional.append(template)

    logger.info(f"[W4] De-duplicated {len(templates) - len(mandatory) - len(optional)} duplicate index pages")

    return mandatory, optional
```

### 2. Create Unit Tests

**New File**: `tests/unit/workers/test_w4_template_collision.py`

**Test Cases**:
1. `test_classify_templates_deduplicates_index_pages()` - Verify only 1 index per section
2. `test_classify_templates_alphabetical_selection()` - Verify deterministic selection
3. `test_classify_templates_no_url_collision()` - Verify unique URLs

**Test Structure**:
```python
def test_classify_templates_deduplicates_index_pages():
    """Test that classify_templates de-duplicates index pages per section."""
    templates = [
        {
            "section": "docs",
            "slug": "index",
            "template_path": "templates/docs/_index.md",
            "variant": "default",
            "is_mandatory": True,
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "templates/docs/_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    # Should only have one index page for docs section
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index" and t["section"] == "docs"]
    assert len(index_pages) == 1
```

### 3. Evidence Collection

**Document in evidence.md**:
- Test outputs showing de-duplication works
- Whether de-duplication actually triggers (0 duplicates if Phase 0 worked)
- Analysis of Phase 0 effectiveness
- Regression test results

## Expected Outcomes

1. **Code Changes**:
   - `classify_templates()` function updated with de-duplication logic
   - Templates sorted deterministically
   - Debug logging for skipped duplicates

2. **Test Coverage**:
   - 3 new unit tests created and passing
   - No regressions in existing W4 tests

3. **Evidence**:
   - Proof that Phase 0 eliminated most/all collisions
   - Proof that defensive de-duplication works (if needed)
   - Complete test output logs

4. **Self-Review**:
   - All 12 dimensions scored ≥4/5
   - Known Gaps section empty

## Risk Mitigation

1. **Preserve Existing Logic**: Only add de-duplication, don't modify classification logic
2. **Debug Logging**: Use debug level to avoid noise if no duplicates found
3. **Deterministic Sorting**: Ensure alphabetical selection is consistent
4. **Template Metadata**: Extract family/platform from template metadata (may not be present)

## Success Criteria

- [ ] classify_templates() tracks seen_index_pages dict
- [ ] Duplicate index pages skipped with debug log
- [ ] Templates sorted deterministically for consistent variant selection
- [ ] 3 unit tests created and passing
- [ ] No regressions (W4 tests still pass)
- [ ] Evidence documents whether Phase 0 eliminated all collisions
- [ ] Self-review complete with ALL dimensions ≥4/5
- [ ] Known Gaps section empty

## Timeline

1. Implement de-duplication: 15 minutes
2. Create unit tests: 20 minutes
3. Run tests and collect evidence: 10 minutes
4. Create documentation: 15 minutes
5. Self-review: 10 minutes

**Total Estimated Time**: 70 minutes
