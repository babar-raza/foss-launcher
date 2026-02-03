# Architectural Healing Plan: URL Generation and Cross-Link Fixes

**Date**: 2026-02-03
**Author**: Orchestrator (MD Generation Sprint)
**Status**: PROPOSED
**Severity**: CRITICAL (Blocks pilot validation)

---

## Executive Summary

Four related architectural bugs discovered during pilot execution debugging:

1. **Bug #1 (CRITICAL)**: URL path generation incorrectly includes section name in path
2. **Bug #2 (HIGH)**: Template collision from duplicate index pages per section
3. **Bug #3 (CRITICAL)**: Cross-subdomain link transformation not integrated (TC-938 incomplete)
4. **Bug #4 (CRITICAL)**: Template discovery loads obsolete `__LOCALE__` templates instead of spec-compliant `__PLATFORM__` templates

**Impact**: ALL generated URLs are malformed, preventing pilot validation. Cross-subdomain navigation is broken. Template structure doesn't match spec.

**Root Cause**: Misunderstanding of subdomain architecture in specs/33_public_url_mapping.md. Section is implicit in subdomain (blog.aspose.org, docs.aspose.org) and should NEVER appear in URL path.

**Estimated Scope**: 3 functions in w4_ia_planner/worker.py + link transformer integration in W5/W6

---

## Bug #1: URL Path Generation Adds Section Incorrectly (CRITICAL)

### Current Behavior

**File**: `src/launch/workers/w4_ia_planner/worker.py`
**Function**: `compute_url_path()` (lines 376-410)
**Issue**: Lines 403-404 add section name to URL when `section != "products"`

```python
# CURRENT (WRONG):
def compute_url_path(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    parts = [product_slug, platform]

    # BUG: Adds section to URL path
    if section != "products":
        parts.append(section)  # ← WRONG!

    parts.append(slug)
    url_path = "/" + "/".join(parts) + "/"
    return url_path
```

**Generated URLs (WRONG)**:
- `blog.aspose.org/3d/python/blog/something/` ❌ (has /blog/ in path)
- `docs.aspose.org/cells/python/docs/guide/` ❌ (has /docs/ in path)
- `kb.aspose.org/words/python/kb/article/` ❌ (has /kb/ in path)
- `reference.aspose.org/cells/python/reference/api/` ❌ (has /reference/ in path)

### Expected Behavior

Per **specs/33_public_url_mapping.md:83-86, 106**:
- Section is implicit in subdomain
- URL path format: `/{family}/{platform}/{slug}/`
- NO section in path

**Expected URLs (CORRECT)**:
- `blog.aspose.org/3d/python/something/` ✓
- `docs.aspose.org/cells/python/guide/` ✓
- `kb.aspose.org/words/python/article/` ✓
- `reference.aspose.org/cells/python/api/` ✓

### Spec Evidence

From **specs/33_public_url_mapping.md:83-86**:
```
Example 1 (V2, docs section):
  content/docs.aspose.org/cells/en/python/developer-guide/_index.md
  → /cells/python/developer-guide/
```

From **specs/33_public_url_mapping.md:106**:
```
Example 2 (V2, blog section):
  content/blog.aspose.org/3d/python/something.md
  → /3d/python/something/
```

**Conclusion**: Section name NEVER appears in URL path. Subdomain IS the section.

### Proposed Fix

**File**: `src/launch/workers/w4_ia_planner/worker.py`
**Function**: `compute_url_path()` (lines 376-410)

```python
# PROPOSED FIX:
def compute_url_path(
    section: str,  # Keep param for metadata, but don't use in URL
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """
    Compute URL path for a page.

    Per specs/33_public_url_mapping.md:
    - Section is implicit in subdomain (blog.aspose.org, docs.aspose.org, etc.)
    - Section name NEVER appears in URL path
    - Format: /{family}/{platform}/{slug}/

    Args:
        section: Section name (used for metadata, NOT in URL path)
        slug: Page slug
        product_slug: Product family (e.g., "3d", "cells", "words")
        platform: Target platform (e.g., "python", "java")
        locale: Language code (e.g., "en", "fr")

    Returns:
        URL path string (e.g., "/3d/python/getting-started/")
    """
    # Section is implicit in subdomain, NOT in URL path
    parts = [product_slug, platform, slug]
    url_path = "/" + "/".join(parts) + "/"
    return url_path
```

### Test Plan

**Update existing tests** in `tests/unit/workers/test_tc_430_ia_planner.py`:

```python
def test_compute_url_path_blog_section():
    """Test blog URL does NOT include /blog/ in path."""
    url = compute_url_path(
        section="blog",
        slug="new-features",
        product_slug="3d",
        platform="python",
    )
    assert url == "/3d/python/new-features/"
    assert "/blog/" not in url  # Section NOT in URL

def test_compute_url_path_docs_section():
    """Test docs URL does NOT include /docs/ in path."""
    url = compute_url_path(
        section="docs",
        slug="getting-started",
        product_slug="cells",
        platform="python",
    )
    assert url == "/cells/python/getting-started/"
    assert "/docs/" not in url  # Section NOT in URL

def test_compute_url_path_kb_section():
    """Test kb URL does NOT include /kb/ in path."""
    url = compute_url_path(
        section="kb",
        slug="troubleshooting",
        product_slug="words",
        platform="python",
    )
    assert url == "/words/python/troubleshooting/"
    assert "/kb/" not in url  # Section NOT in URL
```

---

## Bug #2: Template URL Collision from Duplicate Index Pages (HIGH)

### Current Behavior

**File**: `src/launch/workers/w4_ia_planner/worker.py`
**Function**: `classify_templates()` (lines 926-956)
**Issue**: Multiple `_index.md` templates per section all marked mandatory, causing URL collision

**Example (Blog Section)**:
```
Template 1: specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.variant-full.md
  → slug="index", section="blog", url="/3d/python/"

Template 2: specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.variant-minimal.md
  → slug="index", section="blog", url="/3d/python/"

Template 3: specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.variant-medium.md
  → slug="index", section="blog", url="/3d/python/"

Template 4: specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.variant-hero.md
  → slug="index", section="blog", url="/3d/python/"
```

**Result**: 4 templates → same URL → URL collision error

### Root Cause

All `_index.md` templates are marked `is_mandatory: true` in template metadata. The `classify_templates()` function doesn't de-duplicate index pages per section.

### Expected Behavior

**Only ONE index page per section** should be included in page plan. Pilot should deterministically select the same variant on every run.

**Selection Strategy**: Use first variant alphabetically (deterministic sort)
- `_index.variant-full.md` comes before `_index.variant-hero.md`
- Keep first, discard others

### Proposed Fix

**File**: `src/launch/workers/w4_ia_planner/worker.py`
**Function**: `classify_templates()` (lines 926-956)

```python
def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Classify templates into mandatory and optional based on launch tier.

    De-duplicates index pages per section to prevent URL collisions.

    Args:
        templates: List of template metadata dicts
        launch_tier: Launch tier (pilot, production, enterprise)

    Returns:
        Tuple of (mandatory_templates, optional_templates)
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
                # Already have an index page for this section, skip duplicate
                logger.debug(f"[W4] Skipping duplicate index page: {template.get('template_path')}")
                continue
            seen_index_pages[section_key] = template

        # Classify as mandatory or optional
        if template.get("is_mandatory", False):
            mandatory.append(template)
        else:
            # Apply launch tier filtering for optional templates
            tier_value = template.get("launch_tier", 99)
            tier_map = {"pilot": 1, "production": 2, "enterprise": 3}
            current_tier_value = tier_map.get(launch_tier, 1)

            if tier_value <= current_tier_value:
                optional.append(template)

    logger.info(f"[W4] Classified {len(mandatory)} mandatory, {len(optional)} optional templates")
    logger.info(f"[W4] De-duplicated {len(templates) - len(mandatory) - len(optional)} duplicate index pages")

    return mandatory, optional
```

### Test Plan

**Add new test** in `tests/unit/workers/test_w4_template_collision.py`:

```python
def test_classify_templates_deduplicates_index_pages():
    """Test that only one index page per section is selected."""
    templates = [
        {
            "slug": "index",
            "section": "blog",
            "product_slug": "3d",
            "platform": "python",
            "is_mandatory": True,
            "template_path": "specs/templates/blog/_index.variant-hero.md",
        },
        {
            "slug": "index",
            "section": "blog",
            "product_slug": "3d",
            "platform": "python",
            "is_mandatory": True,
            "template_path": "specs/templates/blog/_index.variant-full.md",
        },
        {
            "slug": "index",
            "section": "blog",
            "product_slug": "3d",
            "platform": "python",
            "is_mandatory": True,
            "template_path": "specs/templates/blog/_index.variant-minimal.md",
        },
    ]

    mandatory, optional = classify_templates(templates, launch_tier="pilot")

    # Should only have 1 index page (alphabetically first variant)
    assert len(mandatory) == 1
    assert mandatory[0]["template_path"].endswith("_index.variant-full.md")

def test_classify_templates_no_url_collision():
    """Test that classified templates have unique URLs."""
    templates = load_all_templates()  # Real template loading
    mandatory, optional = classify_templates(templates, launch_tier="pilot")

    all_templates = mandatory + optional
    urls = [compute_url_path(
        section=t["section"],
        slug=t["slug"],
        product_slug=t["product_slug"],
        platform=t.get("platform", ""),
    ) for t in all_templates]

    # Check for URL collisions
    url_counts = {}
    for url in urls:
        url_counts[url] = url_counts.get(url, 0) + 1

    collisions = [url for url, count in url_counts.items() if count > 1]
    assert collisions == [], f"URL collisions detected: {collisions}"
```

---

## Bug #3: Cross-Subdomain Link Transformation Not Integrated (CRITICAL)

### Current Status: TC-938 INCOMPLETE

**What TC-938 Implemented**:
- ✅ `build_absolute_public_url()` function in `src/launch/resolvers/public_urls.py`
- ✅ Unit tests in `tests/unit/workers/test_tc_938_absolute_links.py` (19 tests, all passing)
- ❌ **NO integration into content generation pipeline**

**What's Missing**:
- Link transformation logic to detect and convert relative cross-section links
- Integration point in W5 (SectionWriter) or W6 (LinkerAndPatcher)
- End-to-end test with actual generated content

### Current Behavior

**Generated Content** (example from blog post):
```markdown
Learn more in our [Getting Started Guide](../../docs/3d/python/getting-started/).
```

**Result**: Relative link breaks in subdomain architecture
- User on `blog.aspose.org` clicks link
- Browser resolves relative path on blog subdomain
- Link targets `blog.aspose.org/docs/3d/python/getting-started/` ❌ (404)
- Should target `docs.aspose.org/3d/python/getting-started/` ✓

### Expected Behavior

**Generated Content** (with absolute URLs):
```markdown
Learn more in our [Getting Started Guide](https://docs.aspose.org/3d/python/getting-started/).
```

**Result**: Absolute link works across subdomains ✓

### Cross-Link Detection Strategy

**Transform only cross-section links** (between different subdomains):
- Blog → Docs: Transform to absolute
- Docs → Reference: Transform to absolute
- KB → Docs: Transform to absolute
- Products → Docs: Transform to absolute

**Do NOT transform**:
- Same-section links: `./another-page/` (keep relative)
- Internal anchors: `#installation` (keep as-is)
- External links: `https://example.com` (already absolute)

### Proposed Fix: Link Transformer Integration

**Option A: Integrate in W5 SectionWriter (RECOMMENDED)**

Add link transformation during draft generation. Advantages:
- Transform once at draft creation time
- Content preview shows correct links
- Patches already contain absolute URLs

**Implementation**:

**File**: `src/launch/workers/w5_section_writer/link_transformer.py` (NEW)

```python
"""
Link transformer for cross-subdomain absolute URL conversion (TC-938).

Transforms relative cross-section links to absolute URLs during draft generation.
"""

import re
from typing import Dict, Any, Optional
from ...resolvers.public_urls import build_absolute_public_url

def transform_cross_section_links(
    markdown_content: str,
    current_section: str,
    page_metadata: Dict[str, Any],
) -> str:
    """
    Transform relative cross-section links to absolute URLs.

    Detects markdown links [text](url) and converts relative cross-section
    links to absolute URLs with scheme + subdomain.

    Args:
        markdown_content: Raw markdown content with links
        current_section: Current page section (blog, docs, kb, reference, products)
        page_metadata: Page metadata (family, platform, locale)

    Returns:
        Markdown content with transformed links
    """
    # Section URL patterns (relative paths that indicate cross-section links)
    section_patterns = {
        "docs": r"(?:\.\.\/)*docs\/",
        "reference": r"(?:\.\.\/)*reference\/",
        "products": r"(?:\.\.\/)*products\/",
        "kb": r"(?:\.\.\/)*kb\/",
        "blog": r"(?:\.\.\/)*blog\/",
    }

    # Regex to match markdown links: [text](url)
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"

    def transform_link(match):
        link_text = match.group(1)
        link_url = match.group(2)

        # Skip external links (already absolute)
        if link_url.startswith("http://") or link_url.startswith("https://"):
            return match.group(0)  # No change

        # Skip internal anchors
        if link_url.startswith("#"):
            return match.group(0)  # No change

        # Detect target section from URL pattern
        target_section = None
        for section, pattern in section_patterns.items():
            if re.search(pattern, link_url):
                target_section = section
                break

        # If no section detected, assume same-section link (keep relative)
        if target_section is None or target_section == current_section:
            return match.group(0)  # No change

        # Parse URL components (family, platform, slug)
        # Example: ../../docs/3d/python/getting-started/
        parts = [p for p in link_url.split("/") if p and p != ".."]

        # Remove section name if present
        if parts and parts[0] in section_patterns:
            parts = parts[1:]

        if len(parts) < 2:
            # Can't parse, keep original
            return match.group(0)

        family = parts[0]
        platform = parts[1] if len(parts) > 1 else ""
        slug = parts[-1] if len(parts) > 2 else ""
        subsections = parts[2:-1] if len(parts) > 3 else []

        # Build absolute URL
        try:
            absolute_url = build_absolute_public_url(
                section=target_section,
                family=family,
                locale=page_metadata.get("locale", "en"),
                platform=platform,
                slug=slug,
                subsections=subsections,
            )
            return f"[{link_text}]({absolute_url})"
        except Exception as e:
            # If transformation fails, keep original
            logger.warning(f"Failed to transform link {link_url}: {e}")
            return match.group(0)

    # Apply transformation to all links
    transformed_content = re.sub(link_pattern, transform_link, markdown_content)
    return transformed_content
```

**File**: `src/launch/workers/w5_section_writer/worker.py` (MODIFY)

```python
# Add import
from .link_transformer import transform_cross_section_links

# In generate_draft_content() function (after LLM generates content):
def generate_draft_content(
    template: Dict[str, Any],
    page_metadata: Dict[str, Any],
    ...
) -> str:
    # ... existing code to generate content ...

    draft_content = llm_response.content  # Raw markdown from LLM

    # TC-938: Transform cross-section links to absolute URLs
    current_section = page_metadata["section"]
    draft_content = transform_cross_section_links(
        markdown_content=draft_content,
        current_section=current_section,
        page_metadata=page_metadata,
    )

    return draft_content
```

**Option B: Integrate in W6 LinkerAndPatcher**

Transform links during patch application. Advantages:
- No changes to W5
- Transformation happens close to final output

Disadvantages:
- More complex (need to parse patches)
- Content preview shows pre-transformation links

**Recommendation**: Use Option A (W5 integration) for cleaner architecture.

### Test Plan

**Unit Tests** (NEW file: `tests/unit/workers/test_w5_link_transformer.py`):

```python
def test_transform_blog_to_docs_link():
    """Test blog → docs link transformed to absolute URL."""
    content = "See [Getting Started](../../docs/3d/python/getting-started/)."
    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata={"locale": "en", "family": "3d", "platform": "python"},
    )
    assert "https://docs.aspose.org/3d/python/getting-started/" in result

def test_preserve_same_section_link():
    """Test same-section link remains relative."""
    content = "See [Next Page](./next-page/)."
    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata={"locale": "en", "family": "cells", "platform": "python"},
    )
    assert content == result  # Unchanged

def test_preserve_internal_anchor():
    """Test internal anchor remains unchanged."""
    content = "Jump to [Installation](#installation)."
    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata={"locale": "en", "family": "cells", "platform": "python"},
    )
    assert content == result  # Unchanged
```

**Integration Test** (in pilot VFV):

```python
def test_pilot_cross_links_are_absolute():
    """Test generated pilot content uses absolute cross-section links."""
    # Run pilot
    run_pilot_vfv(pilot="pilot-aspose-3d-foss-python")

    # Audit content preview
    content_files = glob("runs/*/content_preview/content/**/*.md")

    cross_section_links = []
    for file_path in content_files:
        content = Path(file_path).read_text()

        # Find cross-section links
        for match in re.finditer(r"\[([^\]]+)\]\(([^\)]+)\)", content):
            url = match.group(2)
            if "aspose.org" in url:
                cross_section_links.append((file_path, url))

    # Verify all cross-section links are absolute
    for file_path, url in cross_section_links:
        assert url.startswith("https://"), f"Relative cross-link in {file_path}: {url}"
```

---

## Bug #4: Template Discovery Loads Obsolete `__LOCALE__` Templates (CRITICAL)

### Current Behavior

**Issue**: W4 IAPlanner discovers and loads TWO sets of blog templates with different structures:

**Obsolete templates** (WRONG - has `__LOCALE__` folder):
```
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
```

**Spec-compliant templates** (CORRECT - no `__LOCALE__` folder):
```
specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/index.variant-minimal.md
specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/index.variant-standard.md
specs/templates/blog.aspose.org/3d/__POST_SLUG__/index.variant-minimal.md
```

**Result**: Both template sets are loaded, causing:
1. URL collisions (Bug #2 root cause)
2. Wrong content structure (has locale folders when spec says no locale folders)
3. Wrong filenames (`_index.md` vs `index.md`)

### Spec Evidence

From **specs/33_public_url_mapping.md:88-96** (Blog section):
```
Filesystem layout (V2):
content/blog.aspose.org/<family>/<platform>/
  ├── _index.md                    # platform root (English)
  ├── _index.<lang>.md             # platform root (other languages)
  ├── <year>-<month>-<day>-<slug>.md       # post (English)
  └── <year>-<month>-<day>-<slug>.<lang>.md # post (other languages)
```

**Key point from line 100**: "Blog uses filename-based i18n (no locale folder)"

**Template comment from correct template**:
```markdown
# Template: V2 blog post minimal (platform-aware)
# Source pattern: content/blog.aspose.org/{family}/{platform}/{post}/index.md
```

### Analysis

**Obsolete Templates**:
- Path: `specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/...`
- Structure: Has `__LOCALE__` folder (WRONG per spec line 100)
- Filename: Uses `_index.md` (section index)
- When instantiated: Generates `content/blog.aspose.org/3d/en/python/_index.md` ❌

**Spec-Compliant Templates**:
- Path: `specs/templates/blog.aspose.org/3d/__PLATFORM__/__POST_SLUG__/...`
- Structure: No `__LOCALE__` folder (CORRECT per spec)
- Filename: Uses `index.md` (page bundle)
- When instantiated: Generates `content/blog.aspose.org/3d/python/my-post/index.md` ✓

### Root Cause of Bug #2

Bug #2 (template collision) is NOT just about duplicate variants - it's about loading the WRONG template structure entirely!

The obsolete `__LOCALE__/__PLATFORM__` templates should NOT be discovered at all for blog section.

### Expected Behavior

**W4 IAPlanner template discovery should**:
1. For blog section: ONLY load templates matching `blog.aspose.org/{family}/__PLATFORM__/` pattern
2. For blog section: EXCLUDE any templates with `__LOCALE__/` in path
3. For non-blog sections: May include `__LOCALE__/` (docs, products, kb, reference use locale folders)

### Proposed Fix

**File**: `src/launch/workers/w4_ia_planner/worker.py`
**Function**: Template enumeration/discovery (likely `enumerate_templates()` or similar)

**Strategy**: Filter out obsolete template paths during discovery

```python
def enumerate_templates(template_dir: Path, section: str) -> List[Dict[str, Any]]:
    """
    Enumerate template files for a given section.

    Filters out obsolete template structures that don't match spec.

    Args:
        template_dir: Base template directory
        section: Section name (blog, docs, products, kb, reference)

    Returns:
        List of template metadata dictionaries
    """
    templates = []
    section_dir = template_dir / f"{section}.aspose.org"

    if not section_dir.exists():
        return templates

    # Find all .md files recursively
    for template_path in section_dir.rglob("*.md"):
        rel_path = template_path.relative_to(section_dir)
        path_str = str(rel_path).replace("\\", "/")

        # FILTER: Blog section should NOT have __LOCALE__ in path
        if section == "blog":
            if "__LOCALE__" in path_str:
                logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
                continue

        # Parse template metadata
        template_meta = parse_template_metadata(template_path, section)
        if template_meta:
            templates.append(template_meta)

    logger.info(f"[W4] Discovered {len(templates)} templates for section '{section}'")
    return templates
```

### Impact on Other Sections

**Check if docs, products, kb, reference have similar issues**:

Current investigation shows:
- `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/...` ← Has `__LOCALE__` (may be correct for docs)
- `specs/templates/products.aspose.org/cells/__LOCALE__/__PLATFORM__/...` ← Has `__LOCALE__` (may be correct for products)

**Per spec line 80-86**: Non-blog sections DO use locale folders in content structure:
```
content/products.aspose.org/words/en/python/_index.md
content/docs.aspose.org/cells/en/python/developer-guide/_index.md
```

**Conclusion**: `__LOCALE__` filtering should ONLY apply to blog section. Other sections correctly use locale folders.

### Test Plan

**Add test** in `tests/unit/workers/test_w4_template_discovery.py`:

```python
def test_blog_templates_exclude_locale_folder():
    """Test that blog template discovery excludes obsolete __LOCALE__ templates."""
    templates = enumerate_templates(
        template_dir=Path("specs/templates"),
        section="blog"
    )

    # Check no template paths contain __LOCALE__
    for template in templates:
        path = template["template_path"]
        assert "__LOCALE__" not in path, \
            f"Blog template should not have __LOCALE__ folder: {path}"

def test_blog_templates_use_platform_structure():
    """Test that blog templates follow __PLATFORM__ structure."""
    templates = enumerate_templates(
        template_dir=Path("specs/templates"),
        section="blog"
    )

    # Check all templates have __PLATFORM__ or __POST_SLUG__ in path
    for template in templates:
        path = template["template_path"]
        assert "__PLATFORM__" in path or "__POST_SLUG__" in path, \
            f"Blog template should follow platform structure: {path}"

def test_docs_templates_allow_locale_folder():
    """Test that docs templates correctly use __LOCALE__ folder."""
    templates = enumerate_templates(
        template_dir=Path("specs/templates"),
        section="docs"
    )

    # Docs templates MAY have __LOCALE__ (it's valid per spec)
    # Just verify we're not over-filtering
    assert len(templates) > 0, "Should discover docs templates"
```

---

## Implementation Strategy

### Phase 0: Fix Template Discovery (Bug #4) — HIGHEST PRIORITY

**Order**: Must fix FIRST (root cause of Bug #2)

**Steps**:
1. Locate template enumeration function in W4 IAPlanner
2. Add `__LOCALE__` filter for blog section
3. Add unit tests for template discovery filtering
4. Verify obsolete templates are excluded from discovery
5. Commit: "fix(w4): exclude obsolete __LOCALE__ templates from blog discovery"

**Expected Impact**:
- Blog templates follow spec-compliant structure (no `__LOCALE__` folder)
- Reduces template collision (Bug #2)
- Content structure matches spec

**Risk**: Medium (affects template discovery, need to verify no over-filtering)

### Phase 1: Fix URL Generation (Bug #1) — HIGH PRIORITY

**Order**: Second (can run in parallel with Phase 0)

**Steps**:
1. Update `compute_url_path()` to remove section from URL path
2. Update unit tests in `test_tc_430_ia_planner.py`
3. Run pytest to verify no regressions
4. Commit: "fix(w4): remove section from URL path per subdomain architecture"

**Expected Impact**:
- All URLs now correct format: `/{family}/{platform}/{slug}/`
- Works with Phase 0 to eliminate collisions

**Risk**: Low (simple logic change, well-tested)

### Phase 2: De-duplicate Index Pages if Needed (Bug #2 residual) — LOW PRIORITY

**Order**: Third (after Phase 0 and Phase 1)

**Note**: Phase 0 should eliminate most collisions. This phase adds defensive de-duplication if variants still collide.

**Steps**:
1. Check if URL collisions still occur after Phase 0 + Phase 1
2. If yes: Update `classify_templates()` to de-duplicate index pages
3. Add unit test `test_classify_templates_deduplicates_index_pages()`
4. Run pytest to verify de-duplication works
5. Commit: "fix(w4): add defensive de-duplication for index page variants"

**Expected Impact**:
- Defensive guard against future template collisions
- Only 1 index page per section/family/platform combination

**Risk**: Low (additive change, doesn't break existing logic)

### Phase 3: Integrate Link Transformation (Bug #3) — HIGH PRIORITY

**Order**: Fourth (can run in parallel with Phase 0-2, but test after)

**Steps**:
1. Create `src/launch/workers/w5_section_writer/link_transformer.py`
2. Add `transform_cross_section_links()` function
3. Integrate into W5 `generate_draft_content()` function
4. Create unit tests in `tests/unit/workers/test_w5_link_transformer.py`
5. Run pytest to verify transformation logic
6. Commit: "feat(w5): integrate cross-section link transformation (TC-938 completion)"

**Expected Impact**:
- Cross-subdomain links use absolute URLs
- Content preview shows correct links
- TC-954 verification passes

**Risk**: Medium (regex-based link parsing, edge cases possible)

### Phase 4: End-to-End Validation

**Steps**:
1. Run Pilot-1 (3D) with `--approve-branch` after all fixes integrated
2. Inspect content_preview for correct URLs
3. Verify no URL collisions
4. Verify cross-subdomain links are absolute
5. Run `validate_swarm_ready` to check all gates
6. If passing: Run with `--goldenize` to capture golden
7. Commit: "test: goldenize Pilot-1 with URL and link fixes"

**Expected Outcome**: Pilot-1 passes all gates, content is production-ready

---

## Rollback Strategy

If any phase fails:

**Phase 0 Rollback** (template discovery):
```bash
git revert <commit-hash>
# Fix: Revert template enumeration filter (but will load obsolete templates)
```

**Phase 1 Rollback** (URL generation):
```bash
git revert <commit-hash>
# Fix: Revert compute_url_path() to original (but will have wrong URLs)
```

**Phase 2 Rollback** (template de-duplication):
```bash
git revert <commit-hash>
# Fix: Revert classify_templates() to original (but may have collisions)
```

**Phase 3 Rollback** (link transformation):
```bash
git revert <commit-hash>
# Fix: Remove link_transformer.py, revert W5 integration
```

**Critical Path**: Phase 0 + Phase 1 are REQUIRED for pilot to run with correct structure. Phase 3 is REQUIRED for correct cross-subdomain links.

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Template filter over-excludes valid templates | HIGH | MEDIUM | Unit tests for each section, verify discovery counts |
| Template filter breaks non-blog sections | HIGH | LOW | Only apply `__LOCALE__` filter to blog section |
| URL format breaks existing tests | HIGH | HIGH | Update tests in same commit, run full pytest |
| Regex link parser misses edge cases | MEDIUM | MEDIUM | Comprehensive unit tests, fallback to original link |
| Performance impact from link transformation | LOW | LOW | Transformation is O(n) in content length, negligible |
| Breaking changes to W4 API | HIGH | LOW | compute_url_path() signature unchanged, only logic |
| Pilot fails after fixes | HIGH | LOW | Incremental testing, rollback strategy ready |

---

## Testing Checklist

**Before Integration**:
- [ ] Unit tests pass for template discovery filtering (Bug #4)
- [ ] Unit tests pass for compute_url_path() changes (Bug #1)
- [ ] Unit tests pass for classify_templates() changes (Bug #2, if needed)
- [ ] Unit tests pass for link transformation logic (Bug #3)
- [ ] No regressions in existing W4 tests
- [ ] No regressions in existing TC-938 tests

**After Integration**:
- [ ] Blog templates exclude obsolete `__LOCALE__` structure
- [ ] Pilot-1 (3D) executes without URL collision errors
- [ ] Content preview shows correct URL format (no /blog/, /docs/ in paths)
- [ ] Content structure matches spec (blog has no locale folders)
- [ ] Cross-subdomain links are absolute (grep verification)
- [ ] All validation gates pass (validate_swarm_ready)
- [ ] Golden outputs captured (--goldenize)

**Success Criteria**:
- ✅ Blog templates follow `{family}/__PLATFORM__/` structure (no `__LOCALE__`)
- ✅ All URLs match format: `/{family}/{platform}/{slug}/`
- ✅ No URL collisions (only 1 index page per section/family/platform)
- ✅ Cross-subdomain links start with `https://`
- ✅ Pilot VFV passes with exit code 0
- ✅ 12-dimension self-review scores ≥4/5 for all phases

---

## Related Work

**Completed**:
- TC-938: `build_absolute_public_url()` function (needs integration)
- TC-940: Mandatory page policy (works correctly)
- TC-953: Page quota system (works correctly)
- TC-954: Link verification (found TC-938 incomplete)

**Dependencies**:
- specs/33_public_url_mapping.md (URL format specification)
- specs/06_page_planning.md (cross-link requirements)

**Blocking**:
- Pilot-1 (3D) validation (blocked by Bug #1, #2, #3, #4)
- Pilot-2 (Note) validation (blocked by Bug #1, #2, #3, #4)

---

## Sign-off Requirements

**Before Implementation**:
- [ ] User approves architectural plan
- [ ] All 3 bugs confirmed with spec evidence
- [ ] Implementation phases reviewed
- [ ] Test strategy approved

**After Implementation**:
- [ ] All unit tests passing (pytest)
- [ ] Pilot-1 validation passing (VFV exit code 0)
- [ ] Content preview audit shows correct URLs and links
- [ ] Self-review completed with ≥4/5 on all dimensions
- [ ] Evidence package committed to reports/

---

## Appendix A: Spec References

**specs/33_public_url_mapping.md:83-86** (V2 docs example):
```
content/docs.aspose.org/cells/en/python/developer-guide/_index.md
→ /cells/python/developer-guide/
```

**specs/33_public_url_mapping.md:106** (V2 blog example):
```
content/blog.aspose.org/3d/python/something.md
→ /3d/python/something/
```

**Key Insight**: Section name NEVER in URL path. Subdomain IS the section.

---

## Appendix B: Example Link Transformations

**Before (Relative, BROKEN)**:
```markdown
<!-- From blog post (blog.aspose.org) -->
Learn more in our [Getting Started Guide](../../docs/3d/python/getting-started/).

<!-- From docs page (docs.aspose.org) -->
See the [API Reference](../../reference/cells/python/api/).

<!-- From KB article (kb.aspose.org) -->
Follow the [installation tutorial](../../docs/cells/python/installation/).
```

**After (Absolute, WORKS)**:
```markdown
<!-- From blog post (blog.aspose.org) -->
Learn more in our [Getting Started Guide](https://docs.aspose.org/3d/python/getting-started/).

<!-- From docs page (docs.aspose.org) -->
See the [API Reference](https://reference.aspose.org/cells/python/api/).

<!-- From KB article (kb.aspose.org) -->
Follow the [installation tutorial](https://docs.aspose.org/cells/python/installation/).
```

---

**END OF HEALING PLAN**
