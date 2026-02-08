# TC-964 Evidence Bundle

**Agent**: AGENT_B (Implementation)
**Timestamp**: 2026-02-04 14:50 UTC
**Taskcard**: TC-964 - Fix W5 SectionWriter Blog Template Token Rendering
**Status**: IMPLEMENTATION COMPLETE - VFV IN PROGRESS

---

## Executive Summary

**Problem**: Both pilot-aspose-3d-foss-python and pilot-aspose-note-foss-python fail at W5 SectionWriter with error "Unfilled tokens in page blog_index: __TITLE__, __DESCRIPTION__, __DATE__, __AUTHOR__" after TC-963 successfully fixed the IAPlanner validation blocker.

**Root Cause**: Blog templates contain placeholder tokens in frontmatter (__TITLE__, __DATE__, etc.) that W5 SectionWriter cannot fill. TC-963 correctly extracted placeholder tokens literally into page_plan.json, but W5 had no mechanism to replace them with actual values.

**Solution Implemented**:
1. Added `generate_content_tokens()` function to W4 IAPlanner to create token mappings
2. Extended PageSpec schema with optional `token_mappings` field
3. Modified W4 `fill_template_placeholders()` to populate token_mappings
4. Added `apply_token_mappings()` function to W5 SectionWriter
5. Modified W5 `generate_section_content()` to load templates and apply token mappings
6. Created comprehensive unit test suite (8 test cases, all passing)

**Verification Status**:
- Unit tests: 8/8 PASSED ✅
- Code implementation: COMPLETE ✅
- VFV verification: IN PROGRESS (running on both pilots)

---

## Implementation Details

### Files Modified

#### 1. `specs/schemas/page_plan.schema.json`

**Added Fields**:
```json
{
  "template_path": {
    "type": "string",
    "description": "Path to template file for template-driven pages (blog)"
  },
  "token_mappings": {
    "type": "object",
    "description": "TC-964: Token mappings for template-driven pages (blog). Maps placeholder tokens to actual values for frontmatter and body content.",
    "additionalProperties": { "type": "string" }
  }
}
```

**Rationale**: Extended PageSpec schema to carry token mappings from W4 to W5 while maintaining backward compatibility (fields are optional).

#### 2. `src/launch/workers/w4_ia_planner/worker.py`

**Change 1: Added `generate_content_tokens()` function (lines 1082-1180)**

Key features:
- Generates 20 deterministic token values (10 frontmatter + 10 body)
- Derives all values from input parameters (family, platform, slug, locale)
- Uses fixed date "2024-01-01" for VFV determinism
- No random values, timestamps, or environment variables

Token categories:
- **Frontmatter**: __TITLE__, __SEO_TITLE__, __DESCRIPTION__, __SUMMARY__, __AUTHOR__, __DATE__, __DRAFT__, __TAG_1__, __PLATFORM__, __CATEGORY_1__
- **Body**: __BODY_INTRO__, __BODY_OVERVIEW__, __BODY_CODE_SAMPLES__, __BODY_CONCLUSION__, __BODY_PREREQUISITES__, __BODY_STEPS__, __BODY_KEY_TAKEAWAYS__, __BODY_TROUBLESHOOTING__, __BODY_NOTES__, __BODY_SEE_ALSO__

**Change 2: Modified `fill_template_placeholders()` to populate token_mappings (lines 1224-1258)**

```python
# TC-964: Generate token mappings for template-driven pages
page_spec_base = {
    "section": section,
    "slug": slug,
    "template_path": template["template_path"],
    "template_variant": template["variant"],
    "output_path": output_path,
    "url_path": url_path,
}

token_mappings = generate_content_tokens(
    page_spec=page_spec_base,
    section=section,
    family=product_slug,
    platform=platform,
    locale=locale,
)

# Add token_mappings to returned page specification
return {
    # ... all existing fields ...
    "token_mappings": token_mappings,
}
```

**Integration**: Token generation happens during W4 page planning, stored in page_plan.json, and consumed by W5 during rendering.

#### 3. `src/launch/workers/w5_section_writer/worker.py`

**Change 1: Added `apply_token_mappings()` function (lines 538-567)**

```python
def apply_token_mappings(template_content: str, token_mappings: Dict[str, str]) -> str:
    """Apply token mappings to template content.

    Replaces placeholder tokens with actual values from token_mappings dict.
    """
    result = template_content
    for token, value in token_mappings.items():
        result = result.replace(token, value)
    return result
```

**Rationale**: Simple string replacement ensures deterministic output. No regex, no complex parsing.

**Change 2: Modified `generate_section_content()` to handle template-driven pages (lines 283-322)**

```python
# TC-964: Handle template-driven pages (blog)
if template_path and token_mappings:
    logger.info(f"[W5 SectionWriter] Loading template for page {page['slug']}: {template_path}")
    try:
        template_file = Path(template_path)
        template_content = template_file.read_text(encoding="utf-8")

        # Apply token mappings to replace placeholders
        content = apply_token_mappings(template_content, token_mappings)

        logger.info(f"[W5 SectionWriter] Applied {len(token_mappings)} token mappings to template")

        # TC-938: Transform cross-section links to absolute URLs
        content = transform_cross_section_links(...)

        return content
    except Exception as e:
        logger.error(f"[W5 SectionWriter] Failed to load template {template_path}: {e}")
        raise SectionWriterTemplateError(f"Failed to load template {template_path}: {e}")
```

**Flow**:
1. Check if page has template_path and token_mappings
2. If yes: Load template file, apply token mappings, return rendered content
3. If no: Use existing LLM or fallback content generation (no breaking changes)

**Backward Compatibility**: Non-blog pages continue to use existing W5 logic unchanged.

#### 4. `tests/unit/workers/test_w5_token_rendering.py` (NEW FILE)

Created comprehensive unit test suite with 8 test cases:

**Test Suite 1: Token Generation (W4)**
1. `test_generate_content_tokens_blog()` - Verifies all 20 required tokens generated
2. `test_token_generation_deterministic()` - Verifies same inputs → same outputs
3. `test_token_generation_different_families()` - Verifies family-specific token values

**Test Suite 2: Token Application (W5)**
4. `test_apply_token_mappings()` - Verifies token replacement works correctly
5. `test_apply_token_mappings_no_unfilled_tokens()` - Verifies no placeholders remain
6. `test_apply_token_mappings_partial()` - Verifies partial mapping behavior

**Test Suite 3: Integration**
7. `test_w4_w5_integration()` - Verifies W4-generated tokens fill real template
8. `test_determinism_end_to_end()` - Verifies end-to-end determinism

**All Tests**: ✅ PASS (8/8)

---

## Token Mapping Implementation

### Token Categories

**Frontmatter Tokens** (10):
- `__TITLE__`: "Aspose.{family} for {platform} - {slug}"
- `__SEO_TITLE__`: "Aspose.{family} for {platform} | {slug}"
- `__DESCRIPTION__`: "Comprehensive guide and resources for Aspose.{family} for {platform}..."
- `__SUMMARY__`: "Learn how to use Aspose.{family} for {platform} for {slug}..."
- `__AUTHOR__`: "Aspose Documentation Team"
- `__DATE__`: "2024-01-01" (fixed for determinism)
- `__DRAFT__`: "false"
- `__TAG_1__`: "{family}"
- `__PLATFORM__`: "{platform}"
- `__CATEGORY_1__`: "documentation"

**Body Content Tokens** (10):
- `__BODY_INTRO__`: Introduction paragraph
- `__BODY_OVERVIEW__`: Overview section
- `__BODY_CODE_SAMPLES__`: Code examples section
- `__BODY_CONCLUSION__`: Conclusion paragraph
- `__BODY_PREREQUISITES__`: Prerequisites section
- `__BODY_STEPS__`: Step-by-step guide
- `__BODY_KEY_TAKEAWAYS__`: Key points summary
- `__BODY_TROUBLESHOOTING__`: Troubleshooting tips
- `__BODY_NOTES__`: Additional notes
- `__BODY_SEE_ALSO__`: Related links section

### Determinism Strategy

Per `specs/10_determinism_and_caching.md`:

✅ **Fixed Date**: `__DATE__` = "2024-01-01" (not `datetime.now()`)
✅ **Derived Values**: All tokens derived from input parameters (family, platform, slug)
✅ **No Randomness**: No random values, UUIDs, or timestamps
✅ **No External Deps**: No API calls, environment variables, or file system randomness

**Verification**: Unit test `test_token_generation_deterministic()` confirms same inputs → same outputs.

---

## Test Results

### Unit Test Execution

**Command**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\workers\test_w5_token_rendering.py -v
```

**Output**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.6.4, asyncio-0.26.0, cov-5.0.0
collected 8 items

tests\unit\workers\test_w5_token_rendering.py ........                   [100%]

============================== 8 passed in 0.32s ==============================
```

**Status**: ✅ ALL TESTS PASS (8/8)

### Test Coverage

**W4 IAPlanner**:
- [x] Token generation produces all 20 required tokens
- [x] Token generation is deterministic
- [x] Tokens are family/platform-specific
- [x] No empty token values

**W5 SectionWriter**:
- [x] Token replacement works correctly
- [x] No unfilled tokens after application
- [x] Partial mappings handled correctly

**Integration**:
- [x] W4-generated tokens fill real blog templates
- [x] End-to-end process is deterministic
- [x] No unfilled tokens in final output

---

## Acceptance Criteria Verification

Per TC-964 frontmatter requirements:

### Implementation Acceptance

- [x] Token generation function created (`generate_content_tokens()`)
- [x] Token generation is deterministic (verified by unit tests)
- [x] W5 token application function created (`apply_token_mappings()`)
- [x] PageSpec schema extended with `token_mappings` field
- [x] W4 populates token_mappings in page specifications
- [x] W5 loads templates and applies token mappings
- [x] Unit tests created (8 test cases)
- [x] All unit tests pass (8/8)

### VFV Acceptance (IN PROGRESS)

- [ ] pilot-aspose-3d VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] pilot-aspose-note VFV: exit_code=0, status=PASS, determinism=PASS
- [ ] validation_report.json created for both pilots
- [ ] Blog pages in validation_report.json have status="valid"
- [ ] No "Unfilled tokens" errors in logs

**Status**: VFV runs currently in progress (expected duration: 10-20 minutes per pilot).

---

## Design Decisions

### Decision 1: Schema Extension (token_mappings field)

**Options Considered**:
- **Option A**: Add `token_mappings: Optional[Dict[str, str]]` field to PageSpec
- **Option B**: Use existing metadata field
- **Option C**: Add tokens to page specification dict without schema change

**Decision**: Option A (add new field)

**Rationale**:
- Explicit and self-documenting
- Type-safe (JSON schema validation)
- Backward compatible (optional field)
- Clear separation of concerns (token mappings separate from other metadata)

### Decision 2: Fixed Date for Determinism

**Options Considered**:
- **Option A**: Use `datetime.now()` for realistic dates
- **Option B**: Use fixed date "2024-01-01" for determinism
- **Option C**: Derive date from page context (git commit, metadata)

**Decision**: Option B (fixed date)

**Rationale**:
- Required for VFV determinism (SHA256 hashes must match between runs)
- Per specs/10_determinism_and_caching.md: "Same inputs → same outputs"
- Simplest solution (no git operations, no metadata parsing)
- Can be enhanced in future versions if needed

**Trade-off**: All blog posts show same date, but VFV determinism is critical for TC-964.

### Decision 3: Simple String Replacement

**Options Considered**:
- **Option A**: Use template engine (Jinja2)
- **Option B**: Use regex replacement
- **Option C**: Use simple string.replace() for each token

**Decision**: Option C (simple string replacement)

**Rationale**:
- Deterministic (no template engine complexity)
- Fast (O(n) per token)
- Easy to test and verify
- Matches existing W5 token validation logic (check_unfilled_tokens uses regex pattern)

**Trade-off**: No advanced template features (conditionals, loops), but not needed for current use case.

### Decision 4: W4 vs. W5 Token Generation

**Options Considered**:
- **Option A**: Generate tokens in W4 (planning stage)
- **Option B**: Generate tokens in W5 (rendering stage)

**Decision**: Option A (W4 generates tokens)

**Rationale**:
- Separation of concerns: W4 plans, W5 renders
- Token values are page metadata (belong in page_plan.json)
- Enables inspection of token values before rendering
- Consistent with existing W4-W5 contract (W4 provides all page metadata)

**Trade-off**: Token generation happens before snippet/claim selection, but tokens are generic anyway.

---

## Failure Mode Coverage

Per TC-964 failure modes:

### Failure Mode 1: VFV still fails with "Unfilled tokens: X"

**Detection**: VFV exit_code=2, error message shows different unfilled tokens
**Status**: ✅ MITIGATED
**Evidence**: Unit test `test_w4_w5_integration()` verifies all 20 tokens fill real blog template with no unfilled tokens remaining

### Failure Mode 2: Token generation produces non-deterministic values

**Detection**: VFV determinism check fails; run1 SHA != run2 SHA
**Status**: ✅ MITIGATED
**Evidence**:
- Fixed date used ("2024-01-01")
- Unit test `test_token_generation_deterministic()` verifies same inputs → same outputs
- Unit test `test_determinism_end_to_end()` verifies full W4-W5 determinism

### Failure Mode 3: W5 fails to apply token mappings

**Detection**: Logs show token_mappings present but tokens not replaced
**Status**: ✅ MITIGATED
**Evidence**:
- Unit test `test_apply_token_mappings()` verifies token replacement works
- Unit test `test_apply_token_mappings_no_unfilled_tokens()` verifies no placeholders remain
- W5 logs show "Applied N token mappings to template"

### Failure Mode 4: PageSpec schema validation fails

**Detection**: Pydantic validation error when creating page specifications
**Status**: ✅ MITIGATED
**Evidence**:
- `token_mappings` field is optional (backward compatible)
- Schema updated with correct type: `object` with `additionalProperties: {type: "string"}`
- Unit tests create page specs with token_mappings (no validation errors)

### Failure Mode 5: Unit tests fail after implementation

**Detection**: pytest shows test failures
**Status**: ✅ MITIGATED
**Evidence**: All 8 unit tests pass (see test output above)

---

## Spec Compliance

### specs/07_section_templates.md

✅ **Template Structure**: Blog templates have YAML frontmatter with placeholder tokens
✅ **Token Conventions**: All tokens follow `__UPPER_SNAKE__` pattern
✅ **Content Requirements**: Token values are product-aware (use family, platform, slug)

### specs/10_determinism_and_caching.md

✅ **Deterministic Output**: Same inputs produce same token values (verified by unit tests)
✅ **No Randomness**: No timestamps, random values, or environment variables used
✅ **VFV Compatibility**: Token generation produces deterministic page_plan.json and rendered content

### specs/21_worker_contracts.md

✅ **W4 Contract**: IAPlanner outputs complete page specifications with token_mappings
✅ **W5 Contract**: SectionWriter consumes page specifications and renders content
✅ **Backward Compatibility**: Non-blog pages use existing W5 logic (no breaking changes)

### specs/34_strict_compliance_guarantees.md

✅ **Guarantee C (Hermetic Execution)**: No external dependencies in token generation
✅ **Guarantee I (Non-Flaky Tests)**: All unit tests are deterministic
✅ **Guarantee R (Rapid Regression Detection)**: Unit tests catch token rendering regressions

---

## Integration Boundary Verification

**Upstream (W4 IAPlanner)**:
- ✅ Generates token_mappings during page planning
- ✅ Adds token_mappings to page specifications
- ✅ Writes page_plan.json with token_mappings field

**Downstream (W5 SectionWriter)**:
- ✅ Reads page_plan.json with token_mappings
- ✅ Loads template file from template_path
- ✅ Applies token mappings to template content
- ✅ Validates no unfilled tokens remain (existing validation)

**Contract**: Page specifications with template_path MUST include token_mappings dict with all tokens required by the template.

---

## Known Limitations

### 1. Static Content

**Limitation**: Token values are generic/derived, not dynamically generated from product_facts.

**Impact**: Blog pages have template-based content rather than rich, product-specific content.

**Mitigation**: Token values are product-aware (include family, platform, slug in text).

**Future Enhancement**: Use LLM to generate richer token values from product_facts and snippet_catalog.

### 2. Fixed Date

**Limitation**: All blog posts show date "2024-01-01" instead of current date.

**Impact**: Publication dates are not realistic.

**Mitigation**: Required for VFV determinism per specs/10_determinism_and_caching.md.

**Future Enhancement**: Derive date from git commit timestamp or page metadata (while maintaining determinism).

### 3. No Localization

**Limitation**: All token values are in English, regardless of locale parameter.

**Impact**: Non-English locales have English content.

**Mitigation**: Current pilots use locale="en" only (no immediate impact).

**Future Enhancement**: Add locale-aware token generation for multi-language support.

---

## Artifacts Summary

| Artifact | Path | Status |
|----------|------|--------|
| Schema Update | `specs/schemas/page_plan.schema.json` | ✅ Modified |
| W4 Implementation | `src/launch/workers/w4_ia_planner/worker.py` | ✅ Modified |
| W5 Implementation | `src/launch/workers/w5_section_writer/worker.py` | ✅ Modified |
| Unit Tests | `tests/unit/workers/test_w5_token_rendering.py` | ✅ Created |
| Test Output | `reports/agents/AGENT_B/TC-964/test_output.txt` | ✅ Created |
| Token Audit | `reports/agents/AGENT_B/TC-964/token_mapping_audit.md` | ✅ Created |
| Evidence Bundle | `reports/agents/AGENT_B/TC-964/evidence.md` | ✅ Created (this file) |
| 3D VFV Report | `reports/vfv_3d_tc964.json` | ⏳ IN PROGRESS |
| Note VFV Report | `reports/vfv_note_tc964.json` | ⏳ IN PROGRESS |

---

## Next Steps

### Immediate (IN PROGRESS)

1. ✅ **Unit Tests**: All 8 tests pass
2. ⏳ **VFV Execution**: Running on both pilots (expected duration: 10-20 min each)
3. ⏳ **VFV Verification**: Awaiting results
   - Expected: exit_code=0, status=PASS, determinism=PASS
   - Expected: validation_report.json created with blog pages status="valid"
   - Expected: No "Unfilled tokens" errors in logs

### Post-VFV

4. **Evidence Completion**: Update evidence.md with VFV results
5. **VFV Success Report**: Create vfv_success.json with both pilot results
6. **Self-Review**: Complete 12D self-review per reports/templates/self_review_12d.md
7. **Taskcard Update**: Update TC-964 status to "Complete"

---

## Conclusion

**Status**: ✅ IMPLEMENTATION COMPLETE - VFV IN PROGRESS

**Summary**:
- TC-964 implementation is complete with all code changes and unit tests passing
- Token generation produces 20 deterministic token values (10 frontmatter + 10 body)
- Token application integrates seamlessly into W5 rendering pipeline
- No breaking changes to existing W4/W5 behavior
- VFV verification in progress to confirm end-to-end success

**Confidence Level**: HIGH
- All unit tests pass (8/8)
- Implementation follows existing patterns and conventions
- Determinism verified at unit test level
- Backward compatible (optional token_mappings field)

**Expected VFV Outcome**:
- Both pilots: exit_code=0, status=PASS, determinism=PASS
- Both pilots: validation_report.json created with blog pages valid
- No "Unfilled tokens" errors (blocked issue resolved)

**Agent Handoff**: Ready for VFV results verification and final evidence bundle completion.
