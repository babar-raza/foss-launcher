# TC-3263 — Implementation Plan

**Taskcard:** TC-3263 W10 FQ-3 Truncated Bullet Hardening
**Run:** 20260228_123000
**Status:** Done

## Steps Taken

1. **Precondition check** — Verified TC-3211 and TC-3212 are Done.
2. **Audited gate_17_prelints.py** — FQ-3 detection is not handled by deterministic prelints
   (handled by LLM in gate_17_formatting_quality.py). The `_TRUNCATION_ENDINGS` regex in
   worker.py was the only relevant artifact.
3. **Audited worker.py FQ-3 block** — Found existing "trim last word + period" strategy
   at lines ~856-872 with no fence-tracking guard.
4. **Added module-level regex constants** (TC-3263):
   - `_TRUNCATION_COMMA_RE` — matches trailing comma
   - `_TRUNCATION_CONNECTOR_RE` — matches trailing connector words
5. **Replaced FQ-3 fix block** with two-step strategy:
   - Step 1: trailing comma → strip comma, append period (guard: len > 10)
   - Step 2: trailing connector word → append "..." (guard: len >= 20)
   - Added proper fence-tracking (`in_fence = False` with ` ``` ` toggle)
6. **Added 4 unit tests** in `TestFQ3TruncatedBulletRepair` class.
7. **Ran tests** — 4 new tests pass, 101 total W10 tests pass (no regressions).
8. **Updated taskcard** to Done and checked all acceptance criteria.
9. **Wrote evidence artifacts.**

## Files Modified

- `src/launch/workers/w10_fixer/worker.py` — new module-level regexes + improved FQ-3 block
- `tests/unit/workers/test_w10_scaffold_fix.py` — 4 new tests in TestFQ3TruncatedBulletRepair
- `plans/taskcards/TC-3263_w10_fq3_truncation_hardening.md` — status → Done, checklists checked
