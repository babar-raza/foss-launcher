# Public URL Mapping (binding)

## Purpose
Content files in the repository map to canonical public URLs. Without a binding contract for this mapping,
agents cannot correctly:
- Generate cross-links between pages
- Insert navigation entries with correct URLs
- Validate that produced content will be discoverable

This spec defines the deterministic mapping from content paths to public URLs.

---

## Terminology (binding)

- **content_path**: The file path relative to the site repo root, e.g., `content/docs.aspose.org/cells/en/python/getting-started.md`
- **url_path**: The canonical URL path (without scheme/host), e.g., `/cells/python/getting-started/`
- **subdomain**: The Hugo site subdomain, e.g., `docs.aspose.org`
- **family**: The product family, e.g., `cells`, `words`, `note`
- **locale**: The language code, e.g., `en`, `fr`, `de`
- **platform**: The target platform (V2 layout), e.g., `python`, `java`, `go`
- **section_path**: Nested folder path within the platform/locale root
- **page_kind**: Type of page: `section_index` (`_index.md`), `leaf_page` (`<slug>.md`), or `bundle_page` (`<slug>/index.md`)

---

## URL Computation Contract (binding)

### Input parameters
To compute a url_path, the resolver requires:
- `subdomain` (string)
- `family` (string)
- `locale` (string)
- `platform` (string, required for V2; empty string for V1)
- `section_path` (list of strings, may be empty)
- `page_kind` (enum: `section_index` | `leaf_page` | `bundle_page`)
- `slug` (string, required for `leaf_page` and `bundle_page`)
- `hugo_facts` (object with `default_language`, `default_language_in_subdir`)

### Output
- `url_path` (string): The canonical URL path with leading `/` and trailing `/`

---

## URL Rules by Section Type (binding)

### A) Non-blog sections (products, docs, kb, reference)

**Filesystem layout (V2)**:
```
content/<subdomain>/<family>/<locale>/<platform>/
  ├── _index.md                    # platform root
  ├── <section>/_index.md          # section index
  ├── <section>/<slug>.md          # leaf page (flat style)
  └── <section>/<slug>/index.md    # leaf page (bundle style)
```

**URL computation**:

For **default language** (from hugo_facts.default_language, typically `en`):
- Locale is **dropped** from the URL path (Hugo convention)
- Platform appears immediately after family

```
url_path = /<family>/<platform>/<section_path...>/<slug>/
```

For **non-default language**:
- If hugo_facts.default_language_in_subdir == true: locale is **dropped** for all languages
- Otherwise (standard Hugo): locale **prefixes** the URL path

```
url_path = /<locale>/<family>/<platform>/<section_path...>/<slug>/
```

**Examples (default_language=en, default_language_in_subdir=false)**:

| content_path | url_path |
|-------------|----------|
| `content/products.aspose.org/words/en/python/_index.md` | `/words/python/` |
| `content/products.aspose.org/words/en/python/overview.md` | `/words/python/overview/` |
| `content/products.aspose.org/words/fr/python/_index.md` | `/fr/words/python/` |
| `content/docs.aspose.org/cells/en/python/developer-guide/_index.md` | `/cells/python/developer-guide/` |
| `content/docs.aspose.org/cells/en/python/developer-guide/quickstart.md` | `/cells/python/developer-guide/quickstart/` |
| `content/kb.aspose.org/cells/en/python/troubleshooting.md` | `/cells/python/troubleshooting/` |
| `content/reference.aspose.org/cells/en/python/_index.md` | `/cells/python/` |

### B) Blog section (blog.aspose.org)

**Filesystem layout (V2)**:
```
content/blog.aspose.org/<family>/<platform>/
  ├── _index.md                    # platform root (English)
  ├── _index.<lang>.md             # platform root (other languages)
  ├── <year>-<month>-<day>-<slug>.md       # post (English)
  └── <year>-<month>-<day>-<slug>.<lang>.md # post (other languages)
```

**URL computation**:
- Blog uses filename-based i18n (no locale folder)
- Platform appears after family (V2) or is absent (V1)
- Hugo typically generates blog URLs with date segments or flat slugs based on permalinks config

**Default behavior (no custom permalinks)**:
```
url_path = /<family>/<platform>/<slug>/     # English
url_path = /<lang>/<family>/<platform>/<slug>/  # Non-default language
```

**If permalinks specify date-based URLs**:
- Derive from hugo_facts.permalinks if present
- Otherwise use Hugo defaults

---

## Hugo Facts Required for URL Mapping (binding)

The hugo_facts.json artifact MUST include these fields for URL resolution:

| Field | Type | Description |
|-------|------|-------------|
| `default_language` | string | The default language code (e.g., "en") |
| `default_language_in_subdir` | boolean | If true, all languages (including default) use subdir URLs |
| `permalinks` | object | Custom permalink patterns by section (may be empty) |

### Discovery approach (binding)

1. **default_language**: Read from Hugo config `defaultContentLanguage` key. If absent, default to `"en"`.

2. **default_language_in_subdir**: Read from Hugo config `defaultContentLanguageInSubdir` key. If absent, default to `false`.

3. **permalinks**: Read from Hugo config `permalinks` section. If absent, use empty object `{}`.

If the Hugo config does not expose these values:
- Use Hugo defaults (default_language="en", default_language_in_subdir=false)
- Record discovery method in OPEN_QUESTIONS.md if heuristic fallback was required

---

## Section Index vs Leaf Page vs Bundle Page (binding)

### Section index (_index.md)
- Always maps to the parent URL without a slug
- `_index.md` in `/<family>/<platform>/guide/` maps to `/family/platform/guide/`

### Leaf page (<slug>.md - flat style)
- Maps to parent URL + slug
- `guide/quickstart.md` maps to `/family/platform/guide/quickstart/`

### Bundle page (<slug>/index.md - bundle style)
- Maps identically to flat style
- `guide/quickstart/index.md` maps to `/family/platform/guide/quickstart/`
- The `index.md` file name is stripped; the folder name becomes the slug

---

## Algorithm (binding)

```
function resolve_public_url(target, hugo_facts):
    subdomain = target.subdomain
    family = target.family
    locale = target.locale
    platform = target.platform
    section_path = target.section_path
    page_kind = target.page_kind
    slug = target.slug

    # Determine locale prefix
    if locale == hugo_facts.default_language and not hugo_facts.default_language_in_subdir:
        locale_prefix = ""
    else:
        locale_prefix = "/" + locale

    # Determine platform segment (empty for V1)
    platform_segment = "/" + platform if platform else ""

    # Build section path
    section_segment = "/" + "/".join(section_path) if section_path else ""

    # Build slug segment
    if page_kind == "section_index":
        slug_segment = ""
    else:
        slug_segment = "/" + slug

    # Compose URL path
    if subdomain == "blog.aspose.org":
        # Blog: no locale folder in content, but URL may have locale prefix
        url_path = locale_prefix + "/" + family + platform_segment + slug_segment + "/"
    else:
        # Non-blog: locale_prefix + family + platform + section + slug
        url_path = locale_prefix + "/" + family + platform_segment + section_segment + slug_segment + "/"

    # Normalize (remove double slashes, ensure leading/trailing /)
    url_path = normalize_path(url_path)

    return url_path
```

---

## V1 (Legacy) URL Mapping (reference)

For V1 layouts without platform:
- Simply omit the platform segment
- `content/docs.aspose.org/cells/en/getting-started.md` maps to `/cells/getting-started/` (default lang)
- `content/docs.aspose.org/cells/fr/getting-started.md` maps to `/fr/cells/getting-started/` (non-default lang)

---

## Validation Requirements (binding)

1. Every page in page_plan.json MUST have a `url_path` field populated by the resolver
2. Cross-links MUST use url_path (not content_path) for href values
3. Navigation inserts MUST use url_path for menu URLs

---

## OPEN QUESTIONS

If any of the following cannot be determined from Hugo config:
- Log to `RUN_DIR/reports/OPEN_QUESTIONS.md`
- Use Hugo defaults as fallback
- Mark the fallback in artifacts for audit

---

## Acceptance

- The resolver produces identical url_path for identical inputs
- Default language URLs drop the locale prefix
- Non-default language URLs include the locale prefix (unless default_language_in_subdir=true)
- Platform appears immediately after family in V2 layouts
- Blog URLs follow filename-based i18n conventions
- All examples in this spec are verified by unit tests
