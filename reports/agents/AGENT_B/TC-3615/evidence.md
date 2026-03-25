# TC-3615 Evidence — Freeze Triage Rule IDs

**Date**: 2026-02-28
**Status**: Done

## Changes

### src/launch/cli/triage.py

1. `_RECOMMENDATION_RULES` — each entry now has `"rule_id"` slug (7 entries):
   - `"truth"`, `"code_fence_integrity"`, `"frontmatter_required_fields"`,
   - `"scaffold_or_fmt"`, `"kb_howto"`, `"g20_consistency"`, `"link_patch"`

2. `recommend_action()` — updated id generation:
   ```python
   # Before (TC-3614):
   rec_id = f"triage:{rule['match'].__name__}->{rule['worker']}"

   # After (TC-3615):
   id_slug = rule.get("rule_id") or rule["match"].__name__
   rec_id = f"triage:{id_slug}->{rule['worker']}"
   ```

### tests/unit/cli/test_triage.py

Added 2 tests to `TestRecommendationId`:
- `test_rule_id_takes_priority_over_function_name`
- `test_renaming_match_function_does_not_change_id`

## Test Result

```
7834 passed, 13 skipped, 3 xfailed, 0 failed
```

Previous baseline: 7832 passed. Net new: +2.
