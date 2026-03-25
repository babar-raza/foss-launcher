# TC-3214 Evidence — W10 KB Howto Heading Robustness

## Changes Made

### src/launch/workers/w10_fixer/worker.py — `fix_kb_howto_structure()`

1. **Added `_detect_heading_level()`** — counts H3 vs H2 occurrences, returns dominant level
2. **Adjusted placeholder heading level** — `placeholder.replace("## ", f"{heading_prefix} ", 1)` adapts to document
3. **Updated regexes** — `^##\s+` → `^#{2,3}\s+` for both inject-before and See-Also fallback
4. **Added append-at-end fallback** — if no injection point found, appends at end of file (was: returned False)
5. **Canonical package name** — loads `shared_facts.json` for `package_name`; neutral text if absent; no `<package>` literal

## Tests Added (tests/unit/workers/test_w10_kb_howto_fix.py — 7 tests, 5 classes)

1. `TestH3LevelDetection::test_missing_goal_injected_at_h3_level` — H3 document → ### Goal
2. `TestH3LevelDetection::test_missing_goal_injected_at_h2_level_by_default` — H2 document → ## Goal
3. `TestCodeExampleInjection::test_missing_code_example_injected_before_see_also` — correct ordering
4. `TestPipInstallPlaceholder::test_with_shared_facts_uses_canonical_package` — pip install aspose-cells-python
5. `TestPipInstallPlaceholder::test_without_shared_facts_uses_neutral_text` — no `<package>`, no `pip install`
6. `TestAppendFallback::test_append_at_end_when_no_see_also` — appends at end when no insertion point
7. `TestIdempotency::test_fix_is_idempotent` — second run returns `fixed: False`

## Test Results
```
tests/unit/workers/test_w10_kb_howto_fix.py — 7 passed
```
