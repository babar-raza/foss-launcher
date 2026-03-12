# SR-05: Heading Alias Normalization

**Status**: Open
**Gap**: `_STRUCTURE_DIRECTIVES` has near-duplicate entries (e.g., "key features" / "key highlights", "steps" / "solution steps", "troubleshooting" / "common issues", "code examples" / "code example"). Adding aliases manually doesn't scale and invites drift.

## Scope

- `src/launcher/workers/generate/section_prompt.py` — `_STRUCTURE_DIRECTIVES`, `_get_structure_directive()`

## Acceptance Checks

1. An alias map or normalization function reduces heading variants to canonical forms before lookup
2. "Key Highlights" and "Key Features" resolve to the same directive
3. "Solution Steps" and "Steps" resolve to the same directive
4. "Common Issues" and "Troubleshooting" resolve to the same directive
5. Singular/plural variants ("Code Example" / "Code Examples") resolve to the same directive
6. The canonical directive dict has no redundant entries
7. All existing tests still pass

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | `section_prompt.py` | Add `_HEADING_ALIASES: dict[str, str]` mapping variants to canonical keys |
| 2 | `section_prompt.py` | Update `_get_structure_directive()` to check aliases before dict lookup |
| 3 | `section_prompt.py` | Remove redundant entries from `_STRUCTURE_DIRECTIVES` (keep canonical only) |
| 4 | `tests/unit/workers/test_generate.py` | Test alias resolution for known variants |

## Hard Rules

- Aliases must be explicit — do NOT use fuzzy matching or edit distance
- Every alias must map to an existing canonical key
- Do NOT change behavior for headings that already match exactly

## Runbook

```bash
# 1. Identify duplicate directives with identical text
python -c "
from launcher.workers.generate.section_prompt import _STRUCTURE_DIRECTIVES
from collections import defaultdict
by_value = defaultdict(list)
for k, v in _STRUCTURE_DIRECTIVES.items():
    by_value[v].append(k)
for v, keys in by_value.items():
    if len(keys) > 1:
        print(f'DUPLICATE: {keys}')
"

# 2. Build alias map
# 3. Update _get_structure_directive()
# 4. Remove redundant entries
# 5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v
```
