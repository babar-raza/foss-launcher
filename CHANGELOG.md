# Changelog

All notable changes to the foss-launcher project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Healing] - 2026-02-03

### Fixed

Four critical architectural bugs fixed during pilot validation debugging:

#### HEAL-BUG1: URL Generation - Section Removed from Path
- **File**: `src/launch/workers/w4_ia_planner/worker.py::compute_url_path()` (lines 376-416)
- **Issue**: URL path generation incorrectly included section name in path
- **Fix**: Removed section from URL path per subdomain architecture
- **Impact**: All generated URLs now follow correct format: `/{family}/{platform}/{slug}/`
- **Example**: `blog.aspose.org/3d/python/announcement/` (NOT `/3d/python/blog/announcement/`)
- **Spec**: Per specs/33_public_url_mapping.md:83-86, 106 - section is implicit in subdomain

#### HEAL-BUG2: Template Collision - Index Page De-duplication
- **File**: `src/launch/workers/w4_ia_planner/worker.py::classify_templates()` (lines 941-1000)
- **Issue**: Multiple `_index.md` template variants per section caused URL collisions
- **Fix**: Added defensive de-duplication - only first variant alphabetically selected per section
- **Impact**: No URL collisions from duplicate index pages
- **Example**: Of 4 blog index variants, only `_index.variant-full.md` is used (alphabetically first)

#### HEAL-BUG3: Cross-Section Links - Link Transformation Integration
- **File**: `src/launch/workers/w5_section_writer/link_transformer.py` (NEW)
- **Issue**: TC-938 implemented `build_absolute_public_url()` but never integrated into pipeline
- **Fix**: Created link transformer module and integrated into W5 SectionWriter
- **Impact**: Cross-subdomain links now use absolute URLs and work correctly
- **Example**: `[Guide](../../docs/3d/python/guide/)` → `[Guide](https://docs.aspose.org/3d/python/guide/)`
- **Spec**: Per specs/06_page_planning.md (cross-link transformation section added)

#### HEAL-BUG4: Template Discovery - Blog Template Filtering
- **File**: `src/launch/workers/w4_ia_planner/worker.py::enumerate_templates()` (lines 877-884)
- **Issue**: Template discovery loaded obsolete blog templates with `__LOCALE__` folder structure
- **Fix**: Filter blog templates to exclude `__LOCALE__` paths (blog uses filename-based i18n)
- **Impact**: Blog templates follow spec-compliant structure, no locale folders
- **Example**: Uses `blog.aspose.org/3d/__PLATFORM__/...`, excludes `blog.aspose.org/3d/__LOCALE__/__PLATFORM__/...`
- **Spec**: Per specs/33_public_url_mapping.md:100, specs/07_section_templates.md

### Documentation

- **specs/33_public_url_mapping.md**: Added implementation notes clarifying subdomain architecture
- **specs/07_section_templates.md**: Added template discovery and filtering rules section
- **specs/06_page_planning.md**: Added cross-section link transformation section
- **docs/architecture.md**: Added URL generation and link transformation sections

### Impact Summary

**Before Healing**:
- ❌ All URLs malformed (included section in path)
- ❌ URL collisions from duplicate index pages
- ❌ Cross-subdomain links broken (relative paths)
- ❌ Obsolete blog templates caused structural mismatches

**After Healing**:
- ✅ All URLs correct format: `/{family}/{platform}/{slug}/`
- ✅ No URL collisions (de-duplicated index pages)
- ✅ Cross-subdomain links work (absolute URLs)
- ✅ Blog templates match spec (no locale folders)

### Spec References

- specs/33_public_url_mapping.md (subdomain architecture)
- specs/07_section_templates.md (template structure and filtering)
- specs/06_page_planning.md (cross-links and link transformation)
- plans/healing/url_generation_and_cross_links_fix.md (healing plan)

### Related Work

- TC-938: Implemented `build_absolute_public_url()` (completed with HEAL-BUG3)
- Agent E (DEBUG-PILOT): Identified and fixed VFV preflight and W4 path resolution bugs

---

## [Unreleased]

Changes that are in progress or planned for future releases will be listed here.

---

## Notes

This CHANGELOG tracks significant changes to the foss-launcher system. For detailed commit history, see `git log`.
