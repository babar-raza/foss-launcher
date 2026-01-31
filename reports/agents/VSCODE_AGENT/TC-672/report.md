# TC-672 Report: Content Policy by Subdomain Feasibility and Spec Wiring

**Agent**: VSCODE_AGENT
**Date**: 2026-01-30
**Status**: COMPLETE (Feasibility Only - No Implementation)

## Summary

Completed feasibility analysis for per-subdomain content policy (size/quality/tone control).

## Deliverables

### Created
- [x] `plans/taskcards/TC-672_content_policy_by_subdomain_feasibility_and_spec_wiring.md`
- [x] `runs/site_hierarchy_fix_pilot2_20260130_110029/FEASIBILITY.md`
- [x] `runs/site_hierarchy_fix_pilot2_20260130_110029/NEXT_TASKCARDS.md`

## Feasibility Conclusion

**FEASIBLE** - Content policy per subdomain can be implemented by:

1. Adding OPTIONAL `style_by_section` and `limits_by_section` to ruleset schema
2. W5 SectionWriter injects tone hints into prompts
3. W7 Validator enforces content limits
4. New gate validates limits deterministically

## Proposed Schema Extension

```json
{
  "style_by_section": {
    "products": {"tone": "marketing", "formality": "semi-formal"},
    "docs": {"tone": "technical", "formality": "formal"},
    "blog": {"tone": "conversational", "formality": "informal"}
  },
  "limits_by_section": {
    "products": {"max_words": 500, "max_code_blocks": 2},
    "docs": {"max_words": 2000, "max_code_blocks": 10},
    "blog": {"max_words": 1500, "max_code_blocks": 5}
  }
}
```

## Generated Follow-up Taskcards

| TC ID | Title | Scope |
|-------|-------|-------|
| TC-673 | Implement style_by_section in W5 prompts | W5 worker |
| TC-674 | Implement limits_by_section validation in W7 | W7 worker |
| TC-675 | Add validate_content_limits gate | tools/validate_* |
| TC-676 | Create note family templates | specs/templates |

## Acceptance Criteria Status

| ID | Criterion | Status |
|----|-----------|--------|
| A | FEASIBILITY.md explains current controls | PASS |
| B | Schema extension is backward compatible | PASS (all fields optional) |
| C | Wire plan covers contracts → gates | PASS |
| D | Next taskcards generated | PASS |
| E | No runtime code changes | PASS |
