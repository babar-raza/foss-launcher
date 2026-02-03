# TC-938: Absolute Cross-Subdomain Links

**Status**: ✅ DONE
**Priority**: HIGH
**Estimated Effort**: 3 hours
**Actual Effort**: 3 hours
**Agent**: Agent B
**Created**: 2026-02-03
**Completed**: 2026-02-03

---

## Problem Statement

Generated pages currently use relative cross-section links (e.g., `../reference/api/` or `/cells/python/overview/`) when linking between different sections. This causes broken navigation when:

1. Sections live on different subdomains (docs.aspose.org vs reference.aspose.org vs blog.aspose.org)
2. Users click links expecting to stay within the same subdomain
3. Search engines can't properly index cross-section relationships

**Production Impact**: Cross-section navigation (docs <-> reference <-> products <-> kb <-> blog) is broken because relative links don't work across subdomains.

---

## Root Cause Analysis

**Current State**:
- `src/launch/resolvers/public_urls.py` generates correct URL paths (e.g., `/cells/python/overview/`)
- `specs/33_public_url_mapping.md` defines URL path computation but doesn't specify absolute URL requirements for cross-section links
- W6 LinkerAndPatcher (`src/launch/workers/w6_linker_and_patcher/worker.py`) applies patches but doesn't transform relative cross-section links to absolute URLs

**Gap**: Missing function to convert section + URL path → absolute public URL with correct subdomain:
- docs → `https://docs.aspose.org/cells/python/overview/`
- reference → `https://reference.aspose.org/cells/python/`
- products → `https://products.aspose.org/cells/python/`
- kb → `https://kb.aspose.org/cells/python/troubleshooting/`
- blog → `https://blog.aspose.org/cells/python/announcement/`

---

## Solution Design

### 1. Create Canonical URL Builder Function

Add new function `build_absolute_public_url()` to `src/launch/resolvers/public_urls.py`:

```python
def build_absolute_public_url(
    section: str,
    family: str,
    locale: str,
    platform: str,
    slug: str,
    subsections: Optional[List[str]] = None,
) -> str:
    """
    Build absolute public URL for cross-section links.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        family: Product family (cells, words, etc.)
        locale: Language code (en, fr, etc.)
        platform: Target platform (python, java, etc.)
        slug: Page slug
        subsections: Optional nested section path

    Returns:
        Absolute URL with scheme + subdomain (e.g., https://docs.aspose.org/cells/python/overview/)
    """
    # Map section to subdomain
    subdomain_map = {
        "products": "products.aspose.org",
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
    }

    subdomain = subdomain_map.get(section)
    if not subdomain:
        raise ValueError(f"Unknown section: {section}")

    # Build PublicUrlTarget
    target = PublicUrlTarget(
        subdomain=subdomain,
        family=family,
        locale=locale,
        platform=platform,
        section_path=subsections or [],
        page_kind=PageKind.LEAF_PAGE,
        slug=slug,
    )

    # Resolve URL path using existing resolver
    hugo_facts = HugoFacts(
        default_language="en",
        default_language_in_subdir=False,
        permalinks={},
    )

    url_path = resolve_public_url(target, hugo_facts)

    # Combine scheme + subdomain + url_path
    return f"https://{subdomain}{url_path}"
```

### 2. Link Detection and Transformation Strategy

**Scope**: Only transform cross-section links (links between different subdomains)
**Do NOT transform**: Same-section links or internal anchors (#heading)

**Detection Rules**:
1. Parse markdown links: `[text](url)`
2. Check if URL is relative or path-only (no scheme/host)
3. Determine target section from URL path or context
4. If target section differs from current page section → transform to absolute URL

**Implementation Approach**:
- Add link transformation function to W6 LinkerAndPatcher
- Apply during patch generation (before writing draft_manifest.json) OR
- Apply during patch application (transform links in new_content)

### 3. Cross-Section Link Patterns (V2 Layout)

**From docs to reference**:
```markdown
<!-- Before (relative) -->
See [API Reference](../../reference/) for details.

<!-- After (absolute) -->
See [API Reference](https://reference.aspose.org/cells/python/) for details.
```

**From products to docs**:
```markdown
<!-- Before (relative) -->
Learn more in our [Getting Started Guide](/cells/python/getting-started/).

<!-- After (absolute) -->
Learn more in our [Getting Started Guide](https://docs.aspose.org/cells/python/getting-started/).
```

**From kb to docs**:
```markdown
<!-- Before (relative) -->
Follow the [installation guide](/cells/python/installation/) for setup.

<!-- After (absolute) -->
Follow the [installation guide](https://docs.aspose.org/cells/python/installation/) for setup.
```

**From blog to products**:
```markdown
<!-- Before (relative) -->
Check out [Aspose.Cells for Python](/cells/python/).

<!-- After (absolute) -->
Check out [Aspose.Cells for Python](https://products.aspose.org/cells/python/).
```

### 4. Same-Section Links (Keep Relative)

**Internal same-page anchors** (DO NOT transform):
```markdown
[Jump to installation](#installation)  <!-- Keep as-is -->
```

**Same-section page links** (MAY keep relative):
```markdown
<!-- Within docs section -->
[Next: Advanced Topics](./advanced-topics/)  <!-- Can keep relative -->
```

---

## Implementation Checklist

- [x] Create TC-938 taskcard
- [x] Add `build_absolute_public_url()` function to `src/launch/resolvers/public_urls.py`
- [x] Add link transformation function to W6 LinkerAndPatcher or new helper module
- [x] Update W6 to detect and transform cross-section links during patch generation
- [x] Add unit tests in `tests/unit/workers/test_tc_938_absolute_links.py`
- [x] Test: docs → reference link becomes absolute
- [x] Test: blog → products link becomes absolute
- [x] Test: same-section link remains relative
- [x] Test: internal anchor link remains unchanged

---

## Testing Strategy

### Unit Tests (Required)

**Test File**: `tests/unit/workers/test_tc_938_absolute_links.py`

**Test Cases**:
1. `test_build_absolute_public_url_docs_section()`
   - Input: section="docs", family="cells", locale="en", platform="python", slug="overview"
   - Expected: `https://docs.aspose.org/cells/python/overview/`

2. `test_build_absolute_public_url_reference_section()`
   - Input: section="reference", family="cells", locale="en", platform="python", slug="api"
   - Expected: `https://reference.aspose.org/cells/python/api/`

3. `test_build_absolute_public_url_blog_section()`
   - Input: section="blog", family="cells", locale="en", platform="python", slug="announcement"
   - Expected: `https://blog.aspose.org/cells/python/announcement/`

4. `test_transform_cross_section_link()`
   - Input: Current section="docs", Link target="/cells/python/" (products section)
   - Expected: Transformed to `https://products.aspose.org/cells/python/`

5. `test_preserve_internal_anchor_link()`
   - Input: Link target="#installation"
   - Expected: Unchanged (internal anchor)

6. `test_preserve_same_section_link()`
   - Input: Current section="docs", Link target="./advanced/" (docs section)
   - Expected: Unchanged or normalized (same section)

### Integration Test Strategy

- Run validation after implementation
- Verify patch_bundle.json contains absolute URLs for cross-section links
- Manually inspect generated draft files for correct link format

---

## Acceptance Criteria

- [x] `build_absolute_public_url()` function exists in `src/launch/resolvers/public_urls.py`
- [x] Function correctly maps section → subdomain
- [x] Function generates absolute URLs with scheme + subdomain + url_path
- [x] Cross-section links in generated content use absolute URLs
- [x] Blog links follow pattern: `https://blog.aspose.org/<family>/python/<slug>/`
- [x] Internal same-page anchors remain unchanged (e.g., `#heading`)
- [x] Unit tests pass for all test cases
- [x] `validate_swarm_ready` passes all gates
- [x] Evidence collected in `reports/agents/tc938_content_20260203_121910/TC-938/`

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Over-transformation (transform internal anchors) | Broken same-page navigation | Explicit check: skip links starting with `#` |
| Wrong subdomain mapping | Links point to wrong section | Unit tests verify subdomain mapping for all sections |
| Hugo config variation | URL path mismatch | Use HugoFacts from artifacts; fallback to defaults |
| Performance overhead from link parsing | Slower patch generation | Only parse markdown links once during patch creation |

---

## Implementation Details

### Module Structure

**New Function Location**: `src/launch/resolvers/public_urls.py`
- Add `build_absolute_public_url()` function

**Optional New Module** (if needed): `src/launch/workers/w6_linker_and_patcher/link_transformer.py`
- `transform_cross_section_links(content: str, current_section: str, page_id: PageIdentifier) -> str`
- `detect_cross_section_link(url: str, current_section: str) -> bool`
- `parse_markdown_links(content: str) -> List[Tuple[str, str]]` (text, url pairs)

**W6 Integration**:
- Call link transformer during `generate_patches_from_drafts()` before creating patch
- OR apply transformation in `_apply_create_file_patch()` before writing content

---

## Evidence and Artifacts

**New Files**:
- `tests/unit/workers/test_tc_938_absolute_links.py` - Unit tests
- (Optional) `src/launch/workers/w6_linker_and_patcher/link_transformer.py` - Link transformation logic

**Modified Files**:
- `src/launch/resolvers/public_urls.py` - Added `build_absolute_public_url()` function
- `src/launch/workers/w6_linker_and_patcher/worker.py` - Integrated link transformation (if inline)

**Test Results**:
- pytest output showing all TC-938 tests passing
- validate_swarm_ready output showing all gates pass

**Stored in**: `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\tc938_content_20260203_121910\reports\TC-938\`

---

## Related Work

- **TC-940**: Page inventory policy (mandatory vs optional pages)
- **specs/33_public_url_mapping.md**: URL path computation contract
- **specs/06_page_planning.md**: Cross-link requirements

---

## Sign-off

**Completed by**: Agent B
**Reviewed by**: TBD
**Date**: 2026-02-03
