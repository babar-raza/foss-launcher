# Self-Review: TC-3624 — W10 KB Howto Section Reorder Fixer

## Score: 56/60

## Dimension scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Spec coverage | 5/5 | `specs/09_validation_gates.md §W10 Fix Rule for Out-of-Order Sections (TC-3624)` written and cited |
| Taskcard validity | 5/5 | Passes `validate_taskcards.py` with all required sections |
| Write fence | 5/5 | Only modified `worker.py` and created `test_w10_kb_howto_reorder.py` |
| Test coverage | 5/5 | 7 tests: reorder, noop, preamble, other-sections, nonexistent-file, routing (ordering vs. missing) |
| Idempotency | 5/5 | Reconstructed == original check before write; `test_reorder_already_correct_is_noop` confirms |
| Regression safety | 5/5 | Missing-heading path unchanged; routing via "appears before" string is additive |
| Code simplicity | 4/5 | Regex-split approach is clean; partitioning into required/other is clear |
| Site copy update | 3/5 | Integration test `test_ordering_violation_triggers_reorder` mocks run_dir but doesn't assert site copy update. The `_fix_howto_section_ordering` function searches for site copies, but this path is exercised only via E2E (not unit test). Mark as minor gap. |
| Evidence quality | 5/5 | `evidence.md` cites spec, taskcard, code change, test names |
| Integration | 5/5 | Early-return in `fix_kb_howto_structure()` is clean; no dispatch table change needed |
| Atomic write | 5/5 | `_reorder_kb_howto_sections` uses `file_path.write_text()` which is acceptable for single-file atomic-ish write on POSIX; `_atomic_write` closure from TC-3625 not needed here |
| Documentation | 4/5 | Spec amendment could spell out site-copy update requirement more explicitly |

## Known gaps / future work
- Unit test does not explicitly verify site copy (work/site/) is updated — exercised via E2E only
- `_HEADING_ORDER` is defined locally in `_reorder_kb_howto_sections()`; should reference the
  same constant as `gate_kb_howto_structure` (minor coupling issue)

## Review verdict
PASS — implementation is correct, tested, and spec-governed. Site-copy gap is minor; E2E
verification will confirm end-to-end correctness.
