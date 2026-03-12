# SR-07: Expand Test Coverage for Template-Directive System

**Status**: Open
**Gap**: Only 2 tests cover the directive system (FAQ directive in prompt, content_hint in prompt). No tests for: steps directive, code-example directive, table directive, see-also directive, empty directive fallback, heading-alias edge cases, template-driven skeleton generation end-to-end, or parameterized sweep of all 17 page roles.

## Scope

- `tests/unit/workers/test_generate.py` — existing `TestTemplateIntegration` class
- `tests/unit/content/test_template_loader.py` — new or existing

## Acceptance Checks

1. Parametrized test: every entry in `_STRUCTURE_DIRECTIVES` appears in the prompt when its heading is used
2. Test: headings NOT in `_STRUCTURE_DIRECTIVES` produce a prompt with empty `{structure_directive}`
3. Test: `build_section_prompt()` for "steps" section includes "numbered step-by-step"
4. Test: `build_section_prompt()` for "properties" section includes "table block"
5. Test: `build_section_prompt()` for "see also" section includes "list block"
6. Test: `parse_and_validate_blocks()` strips heading matching section_heading (already exists — verify edge cases: case mismatch, markdown prefix, partial match should NOT strip)
7. Test: `extract_template_sections()` for each real template file produces correct number of sections
8. Test: `extract_template_frontmatter()` strips all placeholder values
9. Integration test: full `_generate_page()` with template produces PageIR with correct section count and headings

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | `tests/unit/workers/test_generate.py` | Parametrized directive-in-prompt test (all headings) |
| 2 | `tests/unit/workers/test_generate.py` | Empty directive fallback test |
| 3 | `tests/unit/workers/test_generate.py` | Section-type-specific directive tests (steps, table, list) |
| 4 | `tests/unit/workers/test_generate.py` | Heading strip edge cases (partial match, case, prefix) |
| 5 | `tests/unit/content/test_template_loader.py` | Template parsing tests against real template files |
| 6 | `tests/unit/workers/test_generate.py` | End-to-end skeleton-from-template test |

## Hard Rules

- Tests must be deterministic (PYTHONHASHSEED=0)
- Do NOT mock template files — read real templates from `specs/templates/`
- Parametrized tests must cover ALL entries, not a hardcoded subset

## Runbook

```bash
# 1. Write tests
# 2. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v
# 3. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/content/ -v
# 4. Run full suite: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest
```
