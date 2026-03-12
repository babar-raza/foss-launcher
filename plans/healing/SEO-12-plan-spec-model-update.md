# SEO-12: Update Plan Spec Gemini Model Reference

## Status: Done

## Gap Linkage
- **G-SR4**: The plan spec (`sparkling-discovering-walrus.md`) still references
  `gemini-2.0-flash` in multiple places. The actual code now uses
  `gemini-2.5-flash` after the deprecation fix. Plan and code must agree.

## Role
Senior engineer. Documentation update.

## Scope

### Fix
Update the plan file at `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md`:

1. Replace all occurrences of `gemini-2.0-flash` with `gemini-2.5-flash`
2. Add a note about Gemini 2.5 thinking-part handling in the Gemini Integration
   section (one sentence: "Gemini 2.5+ returns thinking parts before text;
   the client filters these automatically.")
3. Update the `seo.gemini.model` default in the Configuration section

### Allowed paths
- `C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md`
- `plans/healing/SEO-12-plan-spec-model-update.md`

### Forbidden
Any production code.

## Acceptance Checks

### Grep
- `grep -c "gemini-2.0-flash" <plan-file>` returns 0
- `grep -c "gemini-2.5-flash" <plan-file>` returns >0

## Deliverables
- 1 file updated: plan spec

## Hard Rules
- No production code changes
- No behavior changes

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Accuracy | Plan matches actual code |
| Completeness | All occurrences updated |

## Runbook

```bash
# 1. Find all occurrences
grep -n "gemini-2.0-flash" "C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md"
# 2. Replace all
# 3. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-12
title: Update Plan Spec Gemini Model Reference
status: Not Started
priority: P2
gaps: [G-SR4]
allowed_paths:
  - C:\Users\prora\.claude\plans\sparkling-discovering-walrus.md
depends_on: []
```
