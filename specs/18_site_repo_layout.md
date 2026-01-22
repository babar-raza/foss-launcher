# aspose.org Content Repo Layout (authoritative)

## Purpose
The system MUST write content into the correct subdomain, family, and locale folders in the aspose.org content repo.
All path decisions MUST use this contract, not hardcoded short paths like /docs or /products.

**Platform-Aware Layout**: This document describes the general layout structure. For platform-aware V2 layout with `{locale}/{platform}/` directory segments, see the binding specification:
[specs/32_platform_aware_content_layout.md](32_platform_aware_content_layout.md)

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

### V1 Layout (Legacy)
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
For all subdomains EXCEPT blog.aspose.org, localization is directory-based AND includes platform:

content/<subdomain>/<family>/<locale>/<platform>/

**HARD REQUIREMENT**: Products MUST remain language-folder based: `/{locale}/{platform}/` NOT `/{platform}/` alone.

Examples:
content/products.aspose.org/words/en/typescript/
content/docs.aspose.org/cells/es/python/
content/kb.aspose.org/slides/en/go/
content/reference.aspose.org/pdf/de/python/

For blog.aspose.org, platform is added as a directory segment:

content/blog.aspose.org/<family>/<platform>/

Examples:
content/blog.aspose.org/words/python/
content/blog.aspose.org/cells/typescript/

Blog localization remains filename-based (unchanged).
The system MUST detect the existing pattern for a family by scanning existing blog content and following it.

## Path resolution (MUST)
Given:
- section in {products, docs, kb, reference, blog}
- family (string)
- locale (string)
- platform (string, optional depending on layout_mode)
- layout_mode in {auto, v1, v2} (see [specs/32_platform_aware_content_layout.md](32_platform_aware_content_layout.md))

Return the section root:

**V1 layout** (legacy, no platform segment):
If section != blog:
  root = content/<section_subdomain>/<family>/<locale>/

If section == blog:
  root = content/blog.aspose.org/<family>/
  locale handling is file-based, determined from existing files.

**V2 layout** (platform-aware):
If section != blog:
  root = content/<section_subdomain>/<family>/<locale>/<platform>/

If section == blog:
  root = content/blog.aspose.org/<family>/<platform>/
  locale handling is file-based, determined from existing files.

**Auto-detection**: When `layout_mode: auto`, the system MUST detect V2 by checking if the platform directory exists at the expected path depth. See [specs/32_platform_aware_content_layout.md](32_platform_aware_content_layout.md) for the deterministic detection algorithm.

## Allowed paths enforcement (MUST)
A run must declare allowed_paths in run_config.
The orchestrator MUST refuse any patch outside allowed_paths.
Recommended allowed paths for a run are the section roots for the target family and locale(s).

## Frontmatter contract discovery (MUST)
FrontmatterContract must be discovered per:
- section
- family
- locale (directory-based sections)
- platform (V2 layout only, when resolved)

For V2 layout, discovery MUST occur within platform-specific roots:
- `content/<subdomain>/<family>/<locale>/<platform>/` for non-blog sections
- `content/blog.aspose.org/<family>/<platform>/` for blog

For blog (file-based localization), discovery is per family and platform, by sampling existing files under the resolved roots.


## Hugo config awareness (binding)
Planning and validation MUST be Hugo-config aware.
See `specs/31_hugo_config_awareness.md`.
