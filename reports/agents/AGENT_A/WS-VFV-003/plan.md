# Agent A Verification Plan - WS-VFV-003
## IAPlanner VFV Readiness: TC-957-960 Architectural Healing Fixes

**Agent:** Agent A (Discovery & Architecture)
**Workstream:** WS-VFV-003 (IAPlanner VFV Readiness)
**Date:** 2026-02-04
**Mode:** READ-ONLY VERIFICATION

---

## Objective

Verify that TC-957, TC-958, TC-959, and TC-960 architectural healing fixes are correctly implemented in the IAPlanner worker (`src/launch/workers/w4_ia_planner/worker.py`).

---

## Verification Strategy

### 1. TC-957: Blog Template Filter (Lines 877-884)

**What to verify:**
- Blog templates with `__LOCALE__` folder structure are skipped
- Filter logic only applies to `blog.aspose.org` subdomain
- Logger.debug message is helpful and includes full path
- Spec reference to specs/33_public_url_mapping.md:100 is present

**Evidence to collect:**
- Code excerpt showing subdomain check: `if subdomain == "blog.aspose.org":`
- Code excerpt showing locale check: `if "__LOCALE__" in path_str:`
- Logger.debug statement with [W4] prefix
- Comment referencing specs/33_public_url_mapping.md:100

**Expected implementation:**
```python
# HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
# Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder)
# Blog templates should use __PLATFORM__/__POST_SLUG__ structure, not __LOCALE__
if subdomain == "blog.aspose.org":
    path_str = str(template_path)
    if "__LOCALE__" in path_str:
        logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
        continue
```

---

### 2. TC-958: URL Path Generation (Lines 376-416)

**What to verify:**
- Section name NOT included in URL path
- URL format is `/{family}/{platform}/{slug}/` (no section)
- Docstring examples show correct format
- Spec references to specs/33_public_url_mapping.md:83-86 and 106

**Evidence to collect:**
- Code excerpt showing URL construction: `parts = [product_slug, platform, slug]`
- Absence of conditional section logic (no `if section != "products"`)
- Docstring examples showing `/cells/python/getting-started/` NOT `/cells/python/docs/getting-started/`
- Comments referencing specs/33_public_url_mapping.md

**Expected implementation:**
```python
def compute_url_path(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    Per specs/33_public_url_mapping.md:83-86 and 106:
    - Section is implicit in subdomain (blog.aspose.org, docs.aspose.org, etc.)
    - Section name NEVER appears in URL path
    - For V2 layout with default language (en), the URL format is:
      /<family>/<platform>/<slug>/

    Examples:
        compute_url_path("docs", "getting-started", "cells", "python")
        => "/cells/python/getting-started/"  (NOT /cells/python/docs/getting-started/)

        compute_url_path("blog", "announcement", "3d", "python")
        => "/3d/python/announcement/"  (NOT /3d/python/blog/announcement/)
    """
    # Per specs/33_public_url_mapping.md:83-86, 106:
    # Section is implicit in subdomain, NOT in URL path
    # Format: /<family>/<platform>/<slug>/
    parts = [product_slug, platform, slug]

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path
```

---

### 3. TC-959: Index Deduplication (Lines 941-982)

**What to verify:**
- Index page deduplication logic exists in `classify_templates()`
- Deterministic selection (alphabetical by template_path)
- `seen_index_pages` dictionary tracks index pages per section
- Debug logging when duplicates are skipped

**Evidence to collect:**
- Code excerpt showing `seen_index_pages = {}` initialization
- Code excerpt showing duplicate check: `if slug == "index": if section in seen_index_pages:`
- Logger.debug statement for skipped duplicates
- Counter for duplicates_skipped and info log

**Expected implementation:**
```python
def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Classify templates into mandatory and optional based on launch tier.

    HEAL-BUG2: De-duplicates index pages per section to prevent URL collisions.
    If multiple _index.md variants exist for the same section, only the first
    (alphabetically by template_path) is selected.
    """
    mandatory = []
    optional = []

    # HEAL-BUG2: Track index pages per section to prevent duplicates
    seen_index_pages = {}  # Key: section, Value: template

    # HEAL-BUG2: Sort templates deterministically for consistent variant selection
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

        # ... rest of classification logic

    if duplicates_skipped > 0:
        logger.info(f"[W4] De-duplicated {duplicates_skipped} duplicate index pages")
```

---

### 4. TC-960: Blog Output Path (Lines 438-489)

**What to verify:**
- Blog special case at lines 470-477
- Empty product_slug handling at lines 479-484
- Path format: `content/blog.aspose.org/<family>/<platform>/<slug>/index.md`
- Comment referencing TC-926

**Evidence to collect:**
- Code excerpt showing blog special case: `if section == "blog":`
- Blog path construction without locale segment
- Empty product_slug check: `if product_slug and product_slug.strip():`
- Path components list building with conditional segments

**Expected implementation:**
```python
def compute_output_path(
    section: str,
    slug: str,
    product_slug: str,
    subdomain: str = None,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute content file path relative to site repo root.

    For V2 layout:
    - Non-blog: content/<subdomain>/<family>/<locale>/<platform>/<section>/<slug>.md
    - Blog: content/blog.aspose.org/<family>/<platform>/<slug>/index.md (no locale)
    """
    # TC-681: Auto-determine subdomain from section if not provided
    if subdomain is None:
        subdomain = get_subdomain_for_section(section)

    # TC-926: Blog posts use special format per specs/18_site_repo_layout.md
    # Path: content/blog.aspose.org/<family>/<platform>/<slug>/index.md
    # Note: NO locale segment, uses index.md instead of <slug>.md
    if section == "blog":
        # Build path components, skip empty product_slug to avoid double slash
        components = ["content", subdomain]
        if product_slug and product_slug.strip():
            components.append(product_slug)
        components.extend([platform, slug, "index.md"])
        output_path = "/".join(components)
        return output_path

    # TC-926: Handle empty product_slug gracefully (prevent double slashes)
    # Build path components list, skip empty segments
    components = ["content", subdomain]
    if product_slug and product_slug.strip():
        components.append(product_slug)
    components.extend([locale, platform])

    # ... rest of path construction
```

---

## Verification Commands

```bash
# Read the worker file
Read src/launch/workers/w4_ia_planner/worker.py

# Search for specific implementation patterns
grep -n "HEAL-BUG4" src/launch/workers/w4_ia_planner/worker.py
grep -n "HEAL-BUG2" src/launch/workers/w4_ia_planner/worker.py
grep -n "TC-926" src/launch/workers/w4_ia_planner/worker.py
grep -n "compute_url_path" src/launch/workers/w4_ia_planner/worker.py
grep -n "classify_templates" src/launch/workers/w4_ia_planner/worker.py
grep -n "compute_output_path" src/launch/workers/w4_ia_planner/worker.py

# Verify spec references
grep -n "specs/33_public_url_mapping" src/launch/workers/w4_ia_planner/worker.py
```

---

## Quality Gates

All 4 TC fixes must meet these criteria:

1. **Implementation Correctness:** Code matches spec requirements exactly
2. **Spec References:** Comments cite specific spec lines (e.g., specs/33_public_url_mapping.md:100)
3. **Error Handling:** Edge cases handled gracefully
4. **Logging:** Debug/info logs present for observability
5. **Determinism:** Logic is deterministic (no random/time-based behavior)
6. **Backward Compatibility:** Function signatures unchanged

---

## Evidence Package Structure

```
reports/agents/AGENT_A/WS-VFV-003/
├── plan.md              # This file
├── evidence.md          # Verification findings
├── self_review.md       # 12D self-assessment
└── commands.sh          # All verification commands
```

---

## Success Criteria

- All 4 TC fixes verified as correctly implemented
- Code excerpts captured with exact line numbers
- Spec references validated against source files
- Error handling and logging confirmed
- All 12 self-review dimensions score 4+/5
- No Known Gaps identified

---

## Timeline

- **Start:** 2026-02-04
- **Duration:** 1 hour (read-only verification)
- **Deliverables:** Complete evidence package with self-review
