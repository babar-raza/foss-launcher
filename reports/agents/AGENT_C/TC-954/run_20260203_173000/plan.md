# TC-954 Verification Plan: Absolute Cross-Subdomain Links

## Objective
Verify that TC-938 implementation correctly generates absolute URLs for cross-subdomain links without running pilots.

## Approach

### 1. Code Review
- **Target**: `src/launch/resolvers/public_urls.py`
- **Function**: `build_absolute_public_url()`
- **Verification Points**:
  - Function signature and parameters
  - Subdomain mapping for all 5 sections (products, docs, reference, kb, blog)
  - URL construction logic (scheme + subdomain + path)
  - Integration with existing `resolve_public_url()` function

### 2. Test Execution
- **Target**: `tests/unit/workers/test_tc_938_absolute_links.py`
- **Command**: `pytest tests/unit/workers/test_tc_938_absolute_links.py -v`
- **Expected**: All 19 tests pass
- **Coverage Areas**:
  - All 5 subdomains tested
  - Cross-section link scenarios
  - Edge cases (section index, non-default locale, subsections)

### 3. Code Example Analysis
- **Target**: Search codebase for actual usage of `build_absolute_public_url()`
- **Goal**: Find 5 examples showing cross-subdomain link generation
- **Criteria**:
  - Each example must show different subdomain target
  - Document source file and line number
  - Verify absolute URL format (https://subdomain.aspose.org/...)

### 4. Spec Traceability
- **Source**: `specs/33_public_url_mapping.md`
- **Verification**: Confirm implementation follows spec requirements
- **Cross-reference**: TC-938 taskcard requirements vs implementation

## Success Criteria
- [ ] `build_absolute_public_url()` function reviewed and documented
- [ ] All 19 unit tests pass
- [ ] 5 cross-subdomain link examples identified with file:line references
- [ ] All examples use absolute URLs (https://...)
- [ ] Spec traceability established

## Evidence Collection
- Test output (pytest -v)
- Code snippets with line numbers
- Function signature and implementation notes
- Subdomain mapping verification

## Timeline
- Code review: 10 minutes
- Test execution: 5 minutes
- Example analysis: 15 minutes
- Documentation: 20 minutes
- Total: ~50 minutes
