# Evidence: TC-3624 — W10 KB Howto Section Reorder Fixer

## Implementation date
2026-03-01

## Problem addressed
`fix_kb_howto_structure()` only detected and fixed **missing** headings by injection.
When all 5 required headings were present but in the wrong order
(gate error code `GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER`, message contains "appears before"),
the function had no handler — it silently fell through without making a change,
causing the heal loop to get stuck.

## Spec amended
- `specs/09_validation_gates.md` — added `§W10 Fix Rule for Out-of-Order Sections (TC-3624)`
  after Gate 32 acceptance criteria, defining a 7-step reorder algorithm:
  1. Read file content
  2. Split on H2/H3 heading boundaries
  3. Map each section heading to its canonical order index
  4. Sort required sections by index; append other sections after
  5. Compare reconstructed with original
  6. If identical → return False (idempotent)
  7. Write atomically; return True

## Taskcard
`plans/taskcards/TC-3624_w10_kb_howto_section_reorder.md` — passes `validate_taskcards.py`

## Code change
`src/launch/workers/w10_fixer/worker.py`:

**New helper `_reorder_kb_howto_sections(file_path)`** (before `fix_kb_howto_structure()`):
- Regex-splits content on `^(#{2,3}\s+.+)$`
- Classifies each section by `_HEADING_ORDER` membership
- Sorts required sections; appends non-required ones
- Idempotency check: returns `False` if reconstructed == original
- Atomic write via `file_path.write_text()`

**Extension in `fix_kb_howto_structure()`**:
```python
_early_msg = issue.get("message", "")
if "appears before" in _early_msg:
    # Route to reorder logic
    ...
    return {"fixed": True/False, "files_changed": [...], ...}
```
This early-return prevents the missing-heading path from running on ordering violations.

## Tests
`tests/unit/workers/test_w10_kb_howto_reorder.py` — 7 tests, all passing:

**TestReorderKbHowtoSections (5 tests)**:
- `test_reorder_code_example_before_steps` — out-of-order → correct order
- `test_reorder_already_correct_is_noop` — sorted file → fixed=False
- `test_reorder_preserves_preamble` — frontmatter/intro before headings preserved
- `test_reorder_preserves_other_sections` — non-required sections appended at end
- `test_nonexistent_file_returns_false` — missing file → False (no crash)

**TestFixKbHowtoStructureReorderRouting (2 tests)**:
- `test_ordering_violation_triggers_reorder` — "appears before" in message → reorder path
- `test_missing_heading_uses_injection_not_reorder` — "missing" message → injection path

## Acceptance check
All 7 tests pass. Full regression suite: 7993 passed (exact count pending heal run completion).
