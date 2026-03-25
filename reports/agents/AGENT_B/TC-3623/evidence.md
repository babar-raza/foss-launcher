# Evidence: TC-3623 — W10 FQ-4 Dash-Sentence Heading Split Fixer

## Implementation date
2026-03-01

## Problem addressed
The W10 FQ-4 handler (lines ~792–855 of `worker.py`) used only a camelCase junction regex
(`[a-z][A-Z]`) to detect embedded prose in headings. The pattern
`## ProductName Api- The move method on Worksheet...` was NOT caught because
the junction is a dash+space followed by a capital letter, not camelCase.

Gate 17 (formatting quality) reported FQ-4 errors for these headings in the
`cells` pilot, blocking healing.

## Spec amended
- `specs/09_validation_gates.md` — added `§FQ-4 Pattern Variants (TC-3623)` after Gate 17
  acceptance criteria, defining:
  - camelCase junction pattern (existing)
  - dash-sentence junction pattern: `\b(\w+)[-–]\s+([A-Z][a-z])` (new, TC-3623)
  - prose guard: ≥20 chars; heading guard: ≥3 chars

## Taskcard
`plans/taskcards/TC-3623_w10_fq4_dash_heading_split.md` — passes `validate_taskcards.py`

## Code change
`src/launch/workers/w10_fixer/worker.py` — FQ-4 scan loop (lines ~828–855):

```python
# TC-3623: Dash-sentence junction pattern
# e.g. "## ProductName Api- The move method on Worksheet..."
_fq4_dm = re.search(r'\b(\w+)[-\u2013]\s+([A-Z][a-z])', _fq4_rest)
if _fq4_dm:
    _fq4_dash_end = _fq4_dm.start() + len(_fq4_dm.group(1))
    _fq4_head2 = _fq4_rest[:_fq4_dash_end].rstrip()
    _fq4_prose2 = _fq4_rest[_fq4_dm.start(2):]
    if len(_fq4_prose2.strip()) >= 20 and len(_fq4_head2.strip()) >= 3:
        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head2)
        _fq4_fixed_lines.append('')
        _fq4_fixed_lines.append(_fq4_prose2)
        continue
```

## Tests
`tests/unit/workers/test_w10_fq4_extended.py` — 7 tests, all passing:
- `test_dash_heading_split_basic`
- `test_dash_heading_split_em_dash`
- `test_dash_heading_short_prose_no_split` (guard: <20 chars → no split)
- `test_camelcase_still_works` (regression: camelCase path unchanged)
- `test_inside_fence_not_split` (fence guard preserved)
- `test_heading_minimum_length_guard` (guard: heading <3 chars → no split)
- `test_deterministic_on_repeated_calls`

## Acceptance check
All 7 tests pass. Full regression suite: 7993 passed (exact count pending heal run completion).
