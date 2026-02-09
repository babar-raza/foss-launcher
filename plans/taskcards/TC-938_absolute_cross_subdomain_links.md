---
id: TC-938
title: "Absolute Cross-Subdomain Links"
status: Done
owner: agent_b
created: "2026-02-03"
updated: "2026-02-03"
spec_ref: 403ca6d5a19cbf1ad5aec8da58008aa8ac99a5d3
ruleset_version: v1
templates_version: v1
tags: [finalization, content-quality, cross-section-links]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-938_absolute_cross_subdomain_links.md
  - src/launch/resolvers/public_urls.py
  - src/launch/workers/w6_linker_and_patcher/worker.py
  - src/launch/workers/w6_linker_and_patcher/link_transformer.py
  - tests/unit/workers/test_tc_938_absolute_links.py
  - runs/tc938_content_20260203_121910/**
  - reports/agents/**/TC-938/**
evidence_required:
  - runs/tc938_content_20260203_121910/reports/TC-938/**
  - tests/unit/workers/test_tc_938_absolute_links.py
---

# Taskcard TC-938 — Absolute Cross-Subdomain Links

## Objective

Fix cross-section navigation by converting relative links to absolute URLs when linking between different subdomains (docs.aspose.org, reference.aspose.org, products.aspose.org, kb.aspose.org, blog.aspose.org).

## Required spec references

- specs/33_public_url_mapping.md
- specs/06_page_planning.md
- specs/08_patch_engine.md

## Problem Statement

Generated pages currently use relative cross-section links (e.g., `../reference/api/` or `/cells/python/overview/`) when linking between different sections. This causes broken navigation when:

1. Sections live on different subdomains (docs.aspose.org vs reference.aspose.org vs blog.aspose.org)
2. Users click links expecting to stay within the same subdomain
3. Search engines can't properly index cross-section relationships

**Production Impact**: Cross-section navigation (docs <-> reference <-> products <-> kb <-> blog) is broken because relative links don't work across subdomains.

## Allowed paths

- `plans/taskcards/TC-938_absolute_cross_subdomain_links.md`
- `src/launch/resolvers/public_urls.py`
- `src/launch/workers/w6_linker_and_patcher/worker.py`
- `src/launch/workers/w6_linker_and_patcher/link_transformer.py`
- `tests/unit/workers/test_tc_938_absolute_links.py`
- `runs/tc938_content_20260203_121910/**`
- `reports/agents/**/TC-938/**`## Scope

### In scope
- Create `build_absolute_public_url()` function in `src/launch/resolvers/public_urls.py`
- Add link transformation logic to W6 LinkerAndPatcher
- Transform only cross-section links (between different subdomains)
- Unit tests for absolute URL generation

### Out of scope
- Same-section relative links (keep as-is)
- Internal anchor links (keep as-is)
- External links (already absolute)

## Inputs

- Current page section (products/docs/reference/kb/blog)
- Target URL (relative or path-only)
- Page metadata (family, locale, platform, slug)

## Outputs

- Absolute URLs with scheme + subdomain for cross-section links
- Unchanged relative URLs for same-section links
- Unchanged anchor links for internal navigation

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

## Implementation steps

1. Create `build_absolute_public_url()` function in `src/launch/resolvers/public_urls.py`
2. Add link transformation function to W6 LinkerAndPatcher or new helper module
3. Update W6 to detect and transform cross-section links during patch generation
4. Add unit tests in `tests/unit/workers/test_tc_938_absolute_links.py`
5. Test: docs → reference link becomes absolute
6. Test: blog → products link becomes absolute
7. Test: same-section link remains relative
8. Test: internal anchor link remains unchanged
9. Run validation gates
10. Collect evidence in `reports/agents/tc938_content_20260203_121910/TC-938/`

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

## Deliverables

- `src/launch/resolvers/public_urls.py` - Added `build_absolute_public_url()` function
- `src/launch/workers/w6_linker_and_patcher/worker.py` - Integrated link transformation (if inline)
- (Optional) `src/launch/workers/w6_linker_and_patcher/link_transformer.py` - Link transformation logic
- `tests/unit/workers/test_tc_938_absolute_links.py` - Unit tests
- Evidence package in `reports/agents/tc938_content_20260203_121910/TC-938/`

## Acceptance checks

- `build_absolute_public_url()` function exists in `src/launch/resolvers/public_urls.py`
- Function correctly maps section → subdomain
- Function generates absolute URLs with scheme + subdomain + url_path
- Cross-section links in generated content use absolute URLs
- Blog links follow pattern: `https://blog.aspose.org/<family>/python/<slug>/`
- Internal same-page anchors remain unchanged (e.g., `#heading`)
- Unit tests pass for all test cases
- `validate_swarm_ready` passes all gates
- Evidence collected in `reports/agents/tc938_content_20260203_121910/TC-938/`

## Failure modes

### Failure mode 1: Over-transformation converts internal anchors to absolute URLs
**Detection:** Same-page navigation broken; anchor links start with https://; unit test test_preserve_internal_anchor_link fails
**Resolution:** Add explicit check to skip links starting with # before transformation; verify link pattern detection excludes fragment-only URLs
**Spec/Gate:** specs/08_patch_engine.md (link transformation rules)

### Failure mode 2: Wrong subdomain mapping generates URLs pointing to incorrect section
**Detection:** Cross-section links 404; reference URLs point to docs.aspose.org instead of reference.aspose.org; users report navigation errors
**Resolution:** Review subdomain_map in build_absolute_public_url(); verify section parameter matches expected values (products/docs/reference/kb/blog); add validation for section parameter
**Spec/Gate:** specs/33_public_url_mapping.md (subdomain to section mapping)

### Failure mode 3: Function breaks on pages without family/platform metadata
**Detection:** AttributeError or ValueError when building absolute URL for non-standard pages; W6 worker fails during patch generation
**Resolution:** Add defensive checks for missing metadata; provide fallback values or skip transformation for pages without required attributes; log warning for missing metadata
**Spec/Gate:** specs/06_page_planning.md (page metadata requirements)

## Task-specific review checklist
1. [ ] build_absolute_public_url() function exists in src/launch/resolvers/public_urls.py
2. [ ] Subdomain mapping covers all five sections: products, docs, reference, kb, blog
3. [ ] Function generates absolute URLs with https:// scheme
4. [ ] Cross-section link transformation detects section boundary crossings correctly
5. [ ] Internal anchor links (#heading) remain unchanged after transformation
6. [ ] Same-section relative links are preserved or correctly normalized
7. [ ] Unit tests cover all subdomain mappings and edge cases (anchors, same-section)
8. [ ] W6 LinkerAndPatcher integration doesn't break existing patch generation logic

## Self-review

**Implementation Quality**:
- [x] All code follows existing patterns in codebase
- [x] Function signature matches PublicUrlTarget model
- [x] Subdomain mapping covers all sections
- [x] Link detection preserves internal anchors
- [x] Tests cover all cross-section combinations

**Completeness**:
- [x] All required functions implemented
- [x] All unit tests passing
- [x] Validation gates passing
- [x] Evidence collected and documented

**Documentation**:
- [x] Taskcard includes clear problem statement
- [x] Solution design with code examples
- [x] Test strategy documented
- [x] Risks identified with mitigations

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

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Over-transformation (transform internal anchors) | Broken same-page navigation | Explicit check: skip links starting with `#` |
| Wrong subdomain mapping | Links point to wrong section | Unit tests verify subdomain mapping for all sections |
| Hugo config variation | URL path mismatch | Use HugoFacts from artifacts; fallback to defaults |
| Performance overhead from link parsing | Slower patch generation | Only parse markdown links once during patch creation |

## E2E verification

**Expected artifacts**:
- src/launch/resolvers/public_urls.py with build_absolute_public_url() function
- tests/unit/workers/test_tc_938_absolute_links.py with passing tests
- runs/tc938_content_20260203_121910/reports/TC-938/ with evidence

**Verification commands**:
```bash
# Verify function exists
grep "def build_absolute_public_url" src/launch/resolvers/public_urls.py && echo "PASS: Function exists"

# Verify unit tests created and passing
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py::test_build_absolute_public_url_docs_section -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py::test_build_absolute_public_url_reference_section -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py::test_transform_cross_section_link -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py::test_preserve_internal_anchor_link -v

# Verify validation passes for Gates A2, B, P
.venv/Scripts/python.exe tools/validate_swarm_ready.py 2>&1 | grep -E "(Gate A2|Gate B|Gate P)" | grep PASS && echo "PASS: Gates passing"

# Verify evidence collected
test -d runs/tc938_content_20260203_121910/reports/TC-938 && echo "PASS: Evidence collected"
```

## Integration boundary proven

**Upstream integration**:
- Reads existing specs/33_public_url_mapping.md for URL path computation
- Uses existing PublicUrlTarget and HugoFacts models
- Integrates with W6 LinkerAndPatcher worker

**Downstream integration**:
- Generated content uses absolute URLs for cross-section links
- Same-section links remain relative (unchanged behavior)
- Internal anchors remain unchanged (unchanged behavior)
- All existing tests continue to pass

**Verification**:
- All unit tests pass (pytest)
- TC-938 taskcard validates against Gate A2 and Gate B schemas
- No breaking changes to existing link handling
- validate_swarm_ready passes all gates

## Related Work

- **TC-940**: Page inventory policy (mandatory vs optional pages)
- **specs/33_public_url_mapping.md**: URL path computation contract
- **specs/06_page_planning.md**: Cross-link requirements

## Sign-off

**Completed by**: Agent B
**Reviewed by**: TBD
**Date**: 2026-02-03
**Status**: ✅ DONE
