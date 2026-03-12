# SR-03: Read and Integrate Unread Template Variants

**Status**: Open
**Gap**: Three template variants were never read during implementation. Their H2 headings may introduce section types not covered by `_STRUCTURE_DIRECTIVES` or `PAGE_ROLE_SKELETONS`.

## Unread Templates

1. `specs/templates/docs.aspose.org/__FAMILY__/__PLATFORM__/developer-guide/feature.variant-steps.md`
2. `specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-steps.md`
3. `specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-minimal.md`

## Scope

- `specs/templates/` — the three files above
- `src/launcher/workers/generate/section_prompt.py` — may need new directives
- `src/launcher/shared/page_skeletons.py` — may need variant-specific skeletons
- `src/launcher/content/template_loader.py` — verify variant resolution works

## Acceptance Checks

1. All three templates are read and their H2 structure documented
2. Every H2 heading in these templates has a matching `_STRUCTURE_DIRECTIVES` entry
3. `select_template()` correctly resolves `variant-steps` when tier/variant logic selects it
4. No heading in these templates is missing from the directive registry (SR-01 dependency)

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | This file | Document H2 structure of each template |
| 2 | `section_prompt.py` | Add any missing directives for new headings |
| 3 | `template_loader.py` | Verify `_TIER_VARIANT_MAP` includes steps variant or add mapping |
| 4 | `tests/` | Test that variant-steps templates are resolvable |

## Hard Rules

- Do NOT modify template files — they are authored externally
- Do NOT guess template content — read every file before making changes

## Runbook

```bash
# 1. Read all three templates
cat specs/templates/docs.aspose.org/__FAMILY__/__PLATFORM__/developer-guide/feature.variant-steps.md
cat specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-steps.md
cat specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-minimal.md

# 2. Extract H2 headings
grep "^## " specs/templates/docs.aspose.org/__FAMILY__/__PLATFORM__/developer-guide/feature.variant-steps.md
grep "^## " specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-steps.md
grep "^## " specs/templates/kb.aspose.org/__FAMILY__/__PLATFORM__/howto.variant-minimal.md

# 3. Cross-check against _STRUCTURE_DIRECTIVES
# 4. Add missing directives
# 5. Verify variant resolution
# 6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v
```
