# Code Changes: HEAL-BUG2 - Defensive Index Page De-duplication

**Date**: 2026-02-03
**Agent**: Agent B (Implementation)
**Task**: HEAL-BUG2 - Add Defensive Index Page De-duplication (Phase 2)

## Summary

Added defensive de-duplication logic to `classify_templates()` function in W4 IAPlanner to prevent URL collisions from multiple `_index.md` template variants. Also created comprehensive unit tests to verify the de-duplication behavior.

## Files Modified

### 1. src/launch/workers/w4_ia_planner/worker.py

**Function**: `classify_templates()` (lines 941-995)

**Changes**:
- Added `seen_index_pages` dictionary to track index pages per section
- Added deterministic sorting by `template_path` before processing
- Added de-duplication logic for templates with `slug == "index"`
- Added debug logging for skipped duplicates
- Added info logging for total duplicates skipped
- Updated docstring to document HEAL-BUG2 changes

**Before** (lines 941-971):
```python
def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Classify templates into mandatory and optional based on launch tier.

    Args:
        templates: List of template descriptors
        launch_tier: Launch tier (minimal, standard, rich)

    Returns:
        Tuple of (mandatory_templates, optional_templates)
    """
    mandatory = []
    optional = []

    for template in templates:
        if template["is_mandatory"]:
            mandatory.append(template)
        else:
            # Filter optional templates by launch tier variant
            variant = template["variant"]

            if launch_tier == "minimal" and variant in ["minimal", "default"]:
                optional.append(template)
            elif launch_tier == "standard" and variant in ["minimal", "standard", "default"]:
                optional.append(template)
            elif launch_tier == "rich":
                optional.append(template)

    return mandatory, optional
```

**After** (lines 941-995):
```python
def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Classify templates into mandatory and optional based on launch tier.

    HEAL-BUG2: De-duplicates index pages per section to prevent URL collisions.
    If multiple _index.md variants exist for the same section, only the first
    (alphabetically by template_path) is selected.

    Args:
        templates: List of template descriptors
        launch_tier: Launch tier (minimal, standard, rich)

    Returns:
        Tuple of (mandatory_templates, optional_templates)
    """
    mandatory = []
    optional = []

    # HEAL-BUG2: Track index pages per section to prevent duplicates
    seen_index_pages = {}  # Key: section, Value: template

    # HEAL-BUG2: Sort templates deterministically for consistent variant selection
    # Templates are sorted alphabetically by template_path to ensure the first
    # variant alphabetically is always selected when duplicates exist
    sorted_templates = sorted(templates, key=lambda t: t.get("template_path", ""))

    duplicates_skipped = 0

    for template in sorted_templates:
        slug = template["slug"]
        section = template["section"]

        # HEAL-BUG2: De-duplicate index pages per section
        if slug == "index":
            if section in seen_index_pages:
                logger.debug(f"[W4] Skipping duplicate index page for section '{section}': {template.get('template_path')}")
                duplicates_skipped += 1
                continue
            seen_index_pages[section] = template

        # Classify as mandatory or optional
        if template["is_mandatory"]:
            mandatory.append(template)
        else:
            # Filter optional templates by launch tier variant
            variant = template["variant"]

            if launch_tier == "minimal" and variant in ["minimal", "default"]:
                optional.append(template)
            elif launch_tier == "standard" and variant in ["minimal", "standard", "default"]:
                optional.append(template)
            elif launch_tier == "rich":
                optional.append(template)

    if duplicates_skipped > 0:
        logger.info(f"[W4] De-duplicated {duplicates_skipped} duplicate index pages")

    return mandatory, optional
```

**Key Changes**:
1. **Line 946-948**: Added docstring note about HEAL-BUG2 de-duplication
2. **Line 957**: Added `seen_index_pages` dict to track index pages per section
3. **Line 959-962**: Added deterministic sorting by template_path
4. **Line 964**: Added `duplicates_skipped` counter
5. **Line 966-977**: Added de-duplication logic for index pages
   - Check if slug is "index"
   - If section already seen, skip with debug log
   - If section not seen, add to tracking dict
6. **Line 991-992**: Added info log for total duplicates skipped

## Files Created

### 2. tests/unit/workers/test_w4_template_collision.py

**New File**: Complete unit test suite for template collision de-duplication

**Test Cases** (8 total):

1. **test_classify_templates_deduplicates_index_pages**
   - Verifies only 1 index page per section when duplicates exist
   - Tests with 3 variants: default, minimal, standard
   - Asserts first alphabetically is selected

2. **test_classify_templates_alphabetical_selection**
   - Verifies deterministic alphabetical selection
   - Tests with variants: weight, sidebar, minimal
   - Asserts minimal selected (alphabetically first)

3. **test_classify_templates_no_url_collision**
   - Verifies no URL collisions after de-duplication
   - Tests multiple sections with duplicates
   - Asserts each section has exactly 1 index

4. **test_classify_templates_preserves_non_index_templates**
   - Verifies non-index templates unaffected by de-duplication
   - Tests mix of index and non-index templates
   - Asserts all non-index templates present

5. **test_classify_templates_multiple_sections_independent**
   - Verifies de-duplication is independent per section
   - Tests 3 sections each with duplicates
   - Asserts each section keeps 1 index (total 3)

6. **test_classify_templates_empty_list**
   - Verifies empty list handling
   - Tests with no templates
   - Asserts empty results

7. **test_classify_templates_no_duplicates**
   - Verifies behavior when no duplicates exist
   - Tests with unique index pages per section
   - Asserts all templates present

8. **test_classify_templates_launch_tier_filtering_with_deduplication**
   - Verifies launch tier filtering works with de-duplication
   - Tests with minimal, standard, rich tiers
   - Asserts consistent selection across tiers

**Lines of Code**: ~480 lines

## Implementation Details

### De-duplication Algorithm

1. **Input**: List of template descriptors
2. **Sort**: Templates sorted alphabetically by `template_path`
3. **Track**: Dictionary tracks seen index pages per section
4. **Process**: For each template:
   - If slug is "index":
     - Check if section already in tracking dict
     - If yes: skip with debug log
     - If no: add to tracking dict
   - Continue with normal classification (mandatory/optional)
5. **Log**: Info log if any duplicates skipped
6. **Output**: Tuple of (mandatory, optional) templates

### Deterministic Selection

**Key Principle**: First variant alphabetically is always selected

**Example**:
- Templates: `_index.md`, `_index.variant-minimal.md`, `_index.variant-standard.md`
- Sorted order: Same as above (already alphabetical)
- Selected: `_index.md` (comes first)

**Example 2**:
- Templates: `_index.variant-weight.md`, `_index.variant-sidebar.md`, `_index.variant-minimal.md`
- Sorted order: `_index.variant-minimal.md`, `_index.variant-sidebar.md`, `_index.variant-weight.md`
- Selected: `_index.variant-minimal.md` (comes first alphabetically)

### Edge Cases Handled

1. **Empty Template List**: Returns empty mandatory/optional lists
2. **No Duplicates**: All templates processed normally
3. **Multiple Sections**: De-duplication independent per section
4. **Non-Index Templates**: Unaffected by de-duplication logic
5. **Launch Tier Filtering**: Works correctly with de-duplication

## Backward Compatibility

**No Breaking Changes**:
- Function signature unchanged
- Return type unchanged
- Behavior unchanged when no duplicates exist
- Only adds de-duplication (removes duplicates that would cause errors)

**Preserves Existing Behavior**:
- Mandatory/optional classification still works
- Launch tier filtering still works
- Template sorting now more deterministic (improvement)

## Performance Impact

**Time Complexity**:
- Sorting: O(n log n) where n = number of templates
- De-duplication: O(n) where n = number of templates
- Overall: O(n log n) dominated by sorting

**Space Complexity**:
- Tracking dict: O(s) where s = number of sections (typically 5)
- Sorted list: O(n) where n = number of templates
- Overall: O(n) dominated by template list

**Typical Performance**:
- ~10-50 templates per call
- Sorting 50 templates: ~300 comparisons (~0.1ms)
- Tracking 5 sections: 5 dict operations (~0.001ms)
- **Total overhead**: < 1ms (negligible)

## Testing

**New Tests**: 8 tests in test_w4_template_collision.py
**Existing Tests**: 33 tests in test_tc_430_ia_planner.py
**Total Coverage**: 41 tests

**Results**:
- New tests: 8/8 passed (0.34s)
- Existing tests: 33/33 passed (0.67s)
- Total: 41/41 passed (1.01s)
- **No regressions detected**

## Documentation

**Inline Comments**:
- HEAL-BUG2 markers for all changes
- Clear explanation of de-duplication logic
- Explanation of deterministic sorting

**Docstring Updates**:
- Added HEAL-BUG2 note to classify_templates() docstring
- Explained de-duplication behavior
- Documented alphabetical selection

**Test Documentation**:
- Comprehensive docstrings for each test
- Scenario descriptions
- Expected outcomes
- Proof assertions

## Spec Compliance

**Spec References**:
- specs/06_page_planning.md (mandatory page policy)
- specs/07_section_templates.md (template structure)
- specs/33_public_url_mapping.md (URL path computation)
- specs/10_determinism_and_caching.md (deterministic ordering)

**Compliance**:
- ✅ Prevents URL collisions (specs/33_public_url_mapping.md)
- ✅ Deterministic template selection (specs/10_determinism_and_caching.md)
- ✅ Preserves mandatory page policy (specs/06_page_planning.md)
- ✅ Respects template structure (specs/07_section_templates.md)

## Risk Assessment

**Low Risk**:
- Defensive implementation (only removes problematic duplicates)
- Comprehensive test coverage (8 new tests)
- No regressions in existing tests (33/33 passed)
- Preserves existing behavior when no duplicates

**Mitigation**:
- Debug logging for skipped duplicates (aids troubleshooting)
- Info logging for total duplicates (visibility)
- Clear HEAL-BUG2 markers (easy to locate changes)
- Extensive test coverage (validates behavior)

## Integration Points

**Called By**:
- `execute_ia_planner()` in worker.py (line 1183)

**Calls**:
- `logger.debug()` for skipped duplicates
- `logger.info()` for total duplicates

**Data Flow**:
1. `enumerate_templates()` → list of template descriptors
2. `classify_templates()` → de-duplicate and classify → (mandatory, optional)
3. `select_templates_with_quota()` → select templates respecting quota
4. `fill_template_placeholders()` → create page specs

**No Changes Required**:
- Upstream: `enumerate_templates()` unchanged
- Downstream: `select_templates_with_quota()` unchanged
- Integration: Seamless (function signature unchanged)

## Rollback Plan

**If Issues Arise**:
1. Revert changes to classify_templates() function
2. Remove test_w4_template_collision.py file
3. Test suite will pass (no dependencies on new behavior)
4. System will return to Phase 0 state (relying only on HEAL-BUG4)

**Revert Command**:
```bash
git checkout HEAD -- src/launch/workers/w4_ia_planner/worker.py
git rm tests/unit/workers/test_w4_template_collision.py
```

## Future Considerations

1. **Monitor Production**: Check if de-duplication ever triggers (expect 0)
2. **Template Validation**: Add pre-flight check to detect duplicates earlier
3. **Pattern Reuse**: Consider similar de-duplication for other page types
4. **Documentation**: Add pattern to architecture docs

## Conclusion

Successfully implemented defensive de-duplication logic with comprehensive test coverage and no regressions. Changes are low-risk, well-documented, and provide valuable future-proofing against template duplicates.
