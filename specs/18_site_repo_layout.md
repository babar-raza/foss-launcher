# aspose.org Content Repo Layout (authoritative)

## Purpose
The system MUST write content into the correct subdomain, family, and locale folders in the aspose.org content repo.
All path decisions MUST use this contract, not hardcoded short paths like /docs or /products.

> **Updated (2026-02-12)**: V2 platform-aware layout has been restored. Content may use V1 layout (no platform segment) or V2 layout (with platform segment) depending on `layout_mode` configuration. See `specs/32_platform_aware_content_layout.md` for the binding V2 layout contract.

## Root layout
Content is organized by subdomain folders under:

aspose.org/content/
  products.aspose.org/
  docs.aspose.org/
  kb.aspose.org/
  reference.aspose.org/
  blog.aspose.org/

## Family folders
Immediately under each subdomain folder is the product family folder:

content/products.aspose.org/<family>/
content/docs.aspose.org/<family>/
content/kb.aspose.org/<family>/
content/reference.aspose.org/<family>/
content/blog.aspose.org/<family>/

Examples:
content/products.aspose.org/note/
content/docs.aspose.org/cells/
content/kb.aspose.org/3d/
content/reference.aspose.org/pdf/
content/blog.aspose.org/words/

## Localization rule

### V1 Layout (No Platform Segment)
For all subdomains EXCEPT blog.aspose.org, localization is directory-based:

content/<subdomain>/<family>/<locale>/

Examples:
content/products.aspose.org/note/de/
content/docs.aspose.org/cells/en/
content/kb.aspose.org/3d/ja/
content/reference.aspose.org/pdf/zh/

For blog.aspose.org, localization is NOT directory-based.
Blog uses Hugo filename-based localization (example patterns: index.md + index.de.md, or post.md + post.de.md).

### V2 Layout (Platform-Aware)

For all subdomains EXCEPT blog.aspose.org, V2 adds a platform directory segment after locale:

content/<subdomain>/<family>/<locale>/<platform>/

Examples:
content/products.aspose.org/note/de/python/
content/docs.aspose.org/cells/en/python/
content/kb.aspose.org/3d/ja/java/
content/reference.aspose.org/pdf/zh/dotnet/

For blog.aspose.org, V2 adds a platform directory segment after family:

content/blog.aspose.org/<family>/<platform>/

Examples:
content/blog.aspose.org/words/python/
content/blog.aspose.org/cells/java/

See `specs/32_platform_aware_content_layout.md` for the binding V2 layout contract.

## Path resolution (MUST)
Given:
- section in {products, docs, kb, reference, blog}
- family (string)
- locale (string)
- platform (string, optional — required for V2 layout)
- layout_mode (enum: v1 | v2 | auto)

Return the section root:

**V1 layout** (no platform segment):
If section != blog:
  root = content/<section_subdomain>/<family>/<locale>/

If section == blog:
  root = content/blog.aspose.org/<family>/
  locale handling is file-based, determined from existing files.

**V2 layout** (with platform segment):
If section != blog:
  root = content/<section_subdomain>/<family>/<locale>/<platform>/

If section == blog:
  root = content/blog.aspose.org/<family>/<platform>/
  locale handling is file-based, determined from existing files.

> **Note (2026-02-12)**: V2 layout paths with `/{platform}/` segments require `layout_mode: v2` and `target_platform` to be set in run configuration. See `specs/32_platform_aware_content_layout.md`.

## Allowed paths enforcement (MUST)
A run must declare allowed_paths in run_config.
The orchestrator MUST refuse any patch outside allowed_paths.
Recommended allowed paths for a run are the section roots for the target family and locale(s).

## Frontmatter contract discovery (MUST)
FrontmatterContract must be discovered per:
- section
- family
- locale (directory-based sections)
- platform (V2 layout only)

Discovery occurs within the resolved section roots:

**V1 roots**:
- `content/<subdomain>/<family>/<locale>/` for non-blog sections
- `content/blog.aspose.org/<family>/` for blog

**V2 roots**:
- `content/<subdomain>/<family>/<locale>/<platform>/` for non-blog sections
- `content/blog.aspose.org/<family>/<platform>/` for blog

For blog (file-based localization), discovery is per family (and platform for V2), by sampling existing files under the resolved roots.


## Hugo config awareness (binding)
Planning and validation MUST be Hugo-config aware.
See `specs/31_hugo_config_awareness.md`.
