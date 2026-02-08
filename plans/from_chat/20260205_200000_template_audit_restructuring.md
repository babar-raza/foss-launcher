# Template Audit & Restructuring Plan
**Date**: 2026-02-05
**Source**: Chat-derived from template audit investigation
**Detailed plan**: `C:\Users\prora\.claude\plans\melodic-nibbling-shore.md`

## Context

User requested audit of `specs/templates/` directory: are all templates in use, properly placed, properly designed? Investigation revealed:
- ~72 template files with wrong hierarchies that don't exist in any real site
- ~51 missing templates needed for family parity
- Spec contradictions about blog platform structure
- W4/W5 code needs updates for new template filenames

## Goals

1. Correct all spec/schema artifacts to reflect ground truth template structure
2. Delete all wrong-hierarchy templates (converter, section_path, format_slug, misplaced blog)
3. Create all missing templates for full family parity (3d, cells, note)
4. Update W4 to discover and classify new template structure
5. Update W5 to follow templates for all page types
6. Verify via tests and pilot run

## Assumptions

- [VERIFIED] Blog has NO platform segment (confirmed from real site at D:\onedrive\Documents\GitHub\aspose.net\content\)
- [VERIFIED] No converter/section_path/format_slug hierarchy exists in any subdomain
- [VERIFIED] KB articles use type: "topic" with step1-step10 frontmatter
- [VERIFIED] Reference pages use layout: "reference-single" with categories
- [VERIFIED] TC-967 filter blocks placeholder filenames (new concrete filenames pass)
- [VERIFIED] Ruleset mandatory_pages use slugs not template paths (no ruleset changes needed)

## Steps

### Phase 0: Specs (TC-990, Agent-D, P0, no deps)
1. Update specs/07_section_templates.md: remove blog __PLATFORM__ claim, add ground truth structure
2. Update specs/21_worker_contracts.md: add page_role derivation from filename
3. Verify specs/schemas/page_plan.schema.json has all page_role values

### Phase 1: Delete + Audit (TC-991 + TC-996, Agent-B, P1, parallel, depends TC-990)
4. Delete ~72 wrong template files (converter, section_path, format_slug, misplaced blog, wrong V2 blog)
5. Audit all gates for template path references

### Phase 2: Create (TC-992, Agent-B, P2, depends TC-990+TC-991)
6. Create ~51 new template files for full family parity

### Phase 3: Code (TC-993 + TC-994, Agent-B, P3, parallel, depends TC-990+TC-992)
7. Update W4 enumerate_templates(): add page_role derivation, blog __PLATFORM__ filter
8. Update W5: ensure template loading for feature/howto/reference page types

### Phase 4: Tests (TC-995, Agent-C, P4, depends TC-993+TC-994)
9. Update existing template enumeration tests
10. Add tests for new page roles and template types

### Phase 5: Verify (TC-997, Agent-C, P5, depends ALL)
11. Run full test suite
12. Run 3D pilot through W4
13. Verify template parity across families
14. Produce evidence bundle

## Acceptance Criteria

- [ ] No `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__` in any template filename
- [ ] No `__PLATFORM__` in any blog template path
- [ ] No `__POST_SLUG__` in any docs template path
- [ ] Every family (3d, cells, note) has identical template tree structure
- [ ] All specs consistent with ground truth (no contradictions)
- [ ] W4 assigns page_role to every discovered template
- [ ] W5 loads templates for feature/howto/reference pages
- [ ] All tests pass (PYTHONHASHSEED=0)
- [ ] 3D pilot runs through W4 with correct template discovery

## Risks + Rollback

- **Risk**: W4 code changes break existing template discovery → **Rollback**: git revert TC-993 commit
- **Risk**: Missing template frontmatter causes W5 failures → **Rollback**: fix frontmatter in TC-992 templates
- **Risk**: Gate changes break validation → **Rollback**: git revert TC-996 commit

## Evidence Commands

```bash
# Tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x

# Pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp_pilot_tc997

# Template parity check (no wrong patterns in filenames)
find specs/templates -name "*__CONVERTER_SLUG__*" -o -name "*__FORMAT_SLUG__*" -o -name "*__SECTION_PATH__*" -o -name "*__TOPIC_SLUG__*" -o -name "*__REFERENCE_SLUG__*"
# Expected: empty

# Blog platform check
find specs/templates/blog.aspose.org -path "*__PLATFORM__*"
# Expected: empty

# Family parity
diff <(cd specs/templates && find docs.aspose.org/3d -type f | sed 's|3d/|{family}/|' | sort) <(cd specs/templates && find docs.aspose.org/cells -type f | sed 's|cells/|{family}/|' | sort)
# Expected: identical
```

## Open Questions

(none — all verified during investigation)
