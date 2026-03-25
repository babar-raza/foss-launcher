# TC-2382 Evidence: W5 Section Templates YAML

**Agent**: W5_AGENT
**Taskcard**: TC-2382
**Date**: 2026-02-20
**Status**: Done

## Summary

Implemented role-specific required section constraints for W5 outline generation.
Created `section_templates.yaml` with 15 page roles and integrated the template
loader into the `_generate_outline()` method of `MultiPassOrchestrator`.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/launch/workers/w5_section_writer/section_templates.yaml` | Created | 15 roles + default, each with required_sections and optional_sections lists |
| `src/launch/workers/w5_section_writer/multi_pass.py` | Modified | Added `_load_section_template()` helper and integrated into `_generate_outline()` |
| `tests/unit/workers/test_tc_440_section_writer.py` | Modified | Added `TestSectionTemplatesYAML` class with 5 tests |

## Implementation Details

### section_templates.yaml (15 roles)

Roles defined: `tutorial`, `api_reference`, `feature_showcase`, `troubleshooting`,
`faq`, `landing`, `comprehensive_guide`, `best_practices`, `performance`, `blog`,
`getting_started`, `workflow_page`, `howto_article`, `format_conversion`, `default`.

Each role specifies:
- `required_sections`: sections that MUST appear in every outline for this role
- `optional_sections`: sections that should appear if relevant

### multi_pass.py Changes

1. Added `from pathlib import Path` import.
2. Added `try/except ImportError` guard for `yaml` import (graceful fallback if PyYAML missing).
3. Added module-level `_SECTION_TEMPLATES_PATH = Path(__file__).parent / "section_templates.yaml"`.
4. Added module-level `_load_section_template(page_role: str) -> dict` function that:
   - Returns empty dict gracefully if yaml unavailable or file missing.
   - Falls back to `default` template for unknown roles.
5. In `_generate_outline()`: extracted the LLM user message into `outline_user_message` variable,
   then appended the REQUIRED/OPTIONAL sections instruction block before the `chat_completion` call.

### Outline Integration Logic

```python
page_role = page.get("page_role", "default")
_tmpl = _load_section_template(page_role)
_required = _tmpl.get("required_sections", [])
_optional = _tmpl.get("optional_sections", [])
if _required:
    _tmpl_instruction = (
        "\n\nREQUIRED sections (must ALL appear in the outline, in any order):\n"
        + "\n".join(f"- {s.replace('_', ' ').title()}" for s in _required)
    )
    if _optional:
        _tmpl_instruction += (
            "\n\nOPTIONAL sections (include if relevant to the content):\n"
            + "\n".join(f"- {s.replace('_', ' ').title()}" for s in _optional)
        )
    outline_user_message += _tmpl_instruction
```

## Test Results

### Targeted tests (TC-2382)

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_440_section_writer.py -v -k "SectionTemplates or section_templates"
```

Result: **5 passed** in 1.00s

### Full test suite

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
```

Result: **4620 passed, 9 skipped, 0 failed** in 187.69s

## Acceptance Checklist

- [x] `section_templates.yaml` created with 15 roles + default
- [x] `_load_section_template()` helper in multi_pass.py (module-level)
- [x] Outline LLM prompt contains "REQUIRED sections" block for known roles
- [x] Unknown role falls back to `default` template
- [x] All 5 new tests pass; full suite has 0 regressions (4620 passed, 9 skipped)
- [ ] Tutorial pages in pilot output contain "Prerequisites" section (requires pilot run)
- [ ] API reference pages contain "Method Reference" section (requires pilot run)
