# SR-01: Structure Directive Completeness Validation

**Status**: Open
**Gap**: No validation that every skeleton/template heading has a matching `_STRUCTURE_DIRECTIVES` entry — headings without directives get an empty string, producing generic LLM output.

## Scope

- `src/launcher/workers/generate/section_prompt.py` — `_STRUCTURE_DIRECTIVES` dict
- `src/launcher/shared/page_skeletons.py` — `PAGE_ROLE_SKELETONS` (17 roles)
- `specs/templates/` — all Hugo templates (H2 headings)

## Acceptance Checks

1. Every H2 heading in every `PAGE_ROLE_SKELETONS` entry has a matching `_STRUCTURE_DIRECTIVES` key (case-insensitive)
2. Every H2 heading in every `specs/templates/**/*.md` file has a matching directive
3. A unit test enforces this: if a new heading is added to a skeleton or template without a directive, the test fails
4. `_get_structure_directive()` logs a warning when no directive is found (debug-level)

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | `section_prompt.py` | Add any missing directive entries discovered by audit |
| 2 | `section_prompt.py` | Add `logger.debug` in `_get_structure_directive()` when returning empty |
| 3 | `tests/unit/workers/test_generate.py` | Parametrized test scanning all skeleton headings against `_STRUCTURE_DIRECTIVES` |
| 4 | `tests/unit/workers/test_generate.py` | Parametrized test scanning all template H2s against `_STRUCTURE_DIRECTIVES` |

## Hard Rules

- Do NOT remove or weaken existing directives
- Do NOT change heading text in skeletons/templates — only add directive entries
- New directives must follow existing style: imperative verb, output shape, concrete block types

## Runbook

```bash
# 1. Audit: list all skeleton headings missing directives
python -c "
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS
from launcher.workers.generate.section_prompt import _STRUCTURE_DIRECTIVES
missing = set()
for role, secs in PAGE_ROLE_SKELETONS.items():
    for s in secs:
        if s.heading.strip().lower() not in _STRUCTURE_DIRECTIVES:
            missing.add(s.heading)
print('Missing:', sorted(missing) or 'NONE')
"

# 2. Audit: list all template H2s missing directives
python -c "
import re
from pathlib import Path
from launcher.workers.generate.section_prompt import _STRUCTURE_DIRECTIVES
templates = Path('specs/templates').rglob('*.md')
missing = set()
for t in templates:
    for line in t.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^## (.+)$', line)
        if m:
            h = m.group(1).strip().lower()
            if h not in _STRUCTURE_DIRECTIVES:
                missing.add(m.group(1).strip())
print('Missing:', sorted(missing) or 'NONE')
"

# 3. Add missing entries to _STRUCTURE_DIRECTIVES
# 4. Add warning log
# 5. Write tests
# 6. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v
```
