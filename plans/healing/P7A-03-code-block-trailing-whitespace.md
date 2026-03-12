# P7A-03 — Code Block Citation Stripping: Trailing Whitespace Fix

## Status: Done

## Gap Linkage: G-03

The regex `_CLM_CITATION_RE = re.compile(r"\s*\[CLM-[^\]]*\]")` strips leading
whitespace before the citation. In code blocks, this produces artifacts:

- `x = 1  [CLM-a]` → `x = 1 ` (trailing space)
- `x = 1  # [CLM-a]` → `x = 1  #` (dangling empty comment)

While not a publication blocker, these are cosmetic defects that would fail a
careful code review of generated content.

## Role

Senior engineer. Surgical fix to the ir_renderer code block rendering.

## Scope

### Fix

In `src/launcher/shared/ir_renderer.py`, change the code block rendering to strip
trailing whitespace per line after citation removal:

```python
if bt == BlockType.code:
    lang = block.language or ""
    cleaned = "\n".join(
        _CLM_CITATION_RE.sub("", line).rstrip()
        for line in block.content.split("\n")
    )
    return f"```{lang}\n{cleaned}\n```"
```

This:
- Strips citations per-line (same regex, same behavior)
- `.rstrip()` removes any trailing whitespace left behind
- Handles multi-line code blocks correctly
- Removes dangling `#` comments that become empty after citation removal

Also consider the same treatment in `section_validator.py` for the `_strip_claim_citations`
call on code blocks — but `_strip_claim_citations` operates on the full content string,
not per-line. The ir_renderer is the last-chance defense so fixing it there is sufficient.

### Allowed paths

- `src/launcher/shared/ir_renderer.py`
- `tests/unit/test_ir_renderer.py`

### Forbidden

Any path not listed above.

## Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_ir_renderer.py -v` — all pass
- Tests: existing test `test_code_block_citations_stripped` updated to assert no trailing whitespace
- Tests: new test case — code block with `x = 1  # [CLM-a]` renders as `x = 1` (no trailing `#` or spaces)
- No mock data in production paths

## Deliverables

- Modified `src/launcher/shared/ir_renderer.py` — code block rendering with per-line rstrip
- Updated `tests/unit/test_ir_renderer.py` — tightened assertions, new edge case test

## Hard Rules

- Do not change the regex itself — it works correctly for all block types
- Only add per-line rstrip for code blocks (other block types don't have this issue since their content is prose, not structured)
- No new dependencies
- Keep existing test assertions compatible

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Handles all trailing whitespace patterns: spaces, tabs, dangling `#` |
| Correctness | Code blocks preserve intentional indentation (only trailing stripped) |
| Robustness | Empty lines in code blocks preserved, not collapsed |
| Minimality | 3-line change in renderer, 1 updated + 1 new test |
| Testability | Deterministic string comparison in tests |

## Now (Runbook)

```bash
# 1. Edit ir_renderer.py — replace code block rendering

# 2. Update test: change assertion from "x = 1  #" to "x = 1"
# 3. Add test: "x = 1  # [CLM-a]\nprint('hi')" → "x = 1\nprint('hi')"

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_ir_renderer.py -v

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/test_planner_per_module.py
```
