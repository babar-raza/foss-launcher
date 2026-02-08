# Implementation Plan: Cross-Section Link Transformation Integration (HEAL-BUG3)

**Agent**: Agent B (Implementation)
**Task**: TASK-HEAL-BUG3 - Phase 3 Integration
**Date**: 2026-02-03 21:56:17
**Priority**: HIGH

## Objective

Integrate TC-938's `build_absolute_public_url()` into the W5 SectionWriter pipeline to transform relative cross-section links to absolute URLs at draft generation time.

## Background

### Problem Statement
- **Current Bug**: TC-938 implemented `build_absolute_public_url()` but NEVER integrated into content pipeline
- **Current Wrong Output**: `[Guide](../../docs/3d/python/guide/)` (relative, breaks in subdomain architecture)
- **Expected Correct Output**: `[Guide](https://docs.aspose.org/3d/python/guide/)` (absolute, works across subdomains)
- **Root Cause**: W5 SectionWriter generates content with relative links, no transformation happens

### Spec Requirements
- **specs/06_page_planning.md**: Cross-section links must be absolute
- **specs/33_public_url_mapping.md**: URL format specification
- **TC-938**: Provides `build_absolute_public_url()` in `src/launch/resolvers/public_urls.py`

## Implementation Strategy

### Phase 1: Create Link Transformer Module

**File**: `src/launch/workers/w5_section_writer/link_transformer.py` (NEW)

**Function**: `transform_cross_section_links()`
- Detect markdown links: `[text](url)` using regex
- Identify target section from URL pattern (../../docs/, ../../blog/, etc.)
- Transform to absolute URL if target section != current section
- Preserve relative links for same-section navigation
- Preserve internal anchors (#something)
- Preserve already absolute URLs (https://)
- Use TC-938's `build_absolute_public_url()` for transformation

**Detection Patterns**:
```python
section_patterns = {
    "docs": r"(?:\.\.\/)*docs\/",
    "reference": r"(?:\.\.\/)*reference\/",
    "products": r"(?:\.\.\/)*products\/",
    "kb": r"(?:\.\.\/)*kb\/",
    "blog": r"(?:\.\.\/)*blog\/",
}
```

**Link Regex**: `\[([^\]]+)\]\(([^\)]+)\)`

**Safety Strategy**:
- If transformation fails, keep original link (fallback)
- Log warnings for failed transformations
- No exceptions thrown (graceful degradation)

### Phase 2: Integrate into W5 SectionWriter

**File**: `src/launch/workers/w5_section_writer/worker.py` (MODIFY)

**Integration Point**: `generate_section_content()` function (lines 254-359)
- Add import: `from .link_transformer import transform_cross_section_links`
- Apply transformation AFTER LLM generates content
- Transform before returning content

**Code Addition** (after line 358):
```python
# TC-938: Transform cross-section links to absolute URLs
current_section = page["section"]
page_metadata = {
    "locale": page.get("locale", "en"),
    "family": product_facts.get("product_family", ""),
    "platform": page.get("platform", ""),
}
content = transform_cross_section_links(
    markdown_content=content,
    current_section=current_section,
    page_metadata=page_metadata,
)
```

### Phase 3: Create Unit Tests

**File**: `tests/unit/workers/test_w5_link_transformer.py` (NEW)

**Test Coverage**:
1. `test_transform_blog_to_docs_link()` - Verify blog→docs becomes absolute
2. `test_transform_docs_to_reference_link()` - Verify docs→reference becomes absolute
3. `test_preserve_same_section_link()` - Verify same-section stays relative
4. `test_preserve_internal_anchor()` - Verify #anchor stays as-is
5. `test_preserve_external_link()` - Verify https:// stays as-is
6. `test_transform_multiple_links()` - Verify multiple links in same content
7. `test_transform_malformed_link()` - Verify graceful handling of bad links

### Phase 4: Verification

1. Run new unit tests: `pytest tests/unit/workers/test_w5_link_transformer.py -v`
2. Run TC-938 tests (no regressions): `pytest tests/unit/workers/test_tc_938_absolute_links.py -v`
3. Run full W5 test suite: `pytest tests/unit/workers/test_w5* -v`

## Expected Outcomes

1. **Link Transformation**:
   - Cross-section links become absolute: `https://docs.aspose.org/...`
   - Same-section links remain relative: `./another-page/`
   - Internal anchors preserved: `#installation`
   - External links unchanged: `https://example.com`

2. **Content Quality**:
   - Content preview shows correct absolute links
   - Links work across subdomain architecture
   - No broken relative paths

3. **Test Coverage**:
   - All 7 unit tests passing
   - TC-938 tests still passing (19 tests)
   - No regressions in W5 worker

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Regex parsing misses edge cases | MEDIUM | MEDIUM | Comprehensive unit tests, fallback to original |
| Performance impact | LOW | LOW | O(n) regex scan, negligible for typical content |
| Breaking W5 existing behavior | MEDIUM | LOW | Only adds transformation, doesn't change generation |
| URL parsing errors | MEDIUM | MEDIUM | Try-except with fallback, log warnings |

## Success Criteria

- [ ] `link_transformer.py` created with `transform_cross_section_links()`
- [ ] W5 worker integrates transformation after content generation
- [ ] 7 unit tests created and passing
- [ ] TC-938 tests still pass (19 tests, no regressions)
- [ ] Cross-section links become absolute, same-section stay relative
- [ ] Evidence package complete with all documentation
- [ ] 12-dimension self-review complete with ALL dimensions ≥4/5
- [ ] Known Gaps section empty

## Implementation Timeline

1. **Step 1**: Create `link_transformer.py` module (30 min)
2. **Step 2**: Integrate into W5 worker (15 min)
3. **Step 3**: Create unit tests (45 min)
4. **Step 4**: Run tests and verify (15 min)
5. **Step 5**: Create evidence documentation (30 min)
6. **Step 6**: Self-review and validation (30 min)

**Total Estimated Time**: 2.5 hours

## References

- **Healing Plan**: `plans/healing/url_generation_and_cross_links_fix.md` (lines 402-581)
- **Spec**: `specs/06_page_planning.md` (cross-link requirements)
- **Spec**: `specs/33_public_url_mapping.md` (URL format)
- **TC-938**: `src/launch/resolvers/public_urls.py` (build_absolute_public_url)
- **W5 Worker**: `src/launch/workers/w5_section_writer/worker.py`
