# Run ID Unification — Healing Plan

## Context

The run ID was unified from three inconsistent generators into a single
`generate_run_id()` producing `r_{YYMMDD}_{hex4}` (13 chars). Self-review
identified 6 gaps preventing the change from being production-grade:
collision risk with only 4 hex chars, missing unit tests, AG-002 taskcard
violation, lost product-family observability in directory names, no collision
guard at the call sites, and incomplete docstring.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-RID-01 | `hex4` gives only 65K IDs/day — birthday-paradox collision risk at production volumes | Robustness/Critical | RID-01 |
| G-RID-02 | No collision guard at call sites — `mkdir(exist_ok=True)` silently overwrites | Robustness/Critical | RID-01 |
| G-RID-03 | No unit test for `generate_run_id()` format, length, or uniqueness | Testability/High | RID-02 |
| G-RID-04 | AG-002 taskcard violation — code was written under `src/launcher/**` without a taskcard | Governance/High | RID-03 |
| G-RID-05 | Run directory names lost product-family context (`pilot_cells_` → `r_260307_xxxx`) | Observability/Medium | RID-04 |
| G-RID-06 | Docstring doesn't explain design rationale (MAX_PATH, collision characteristics) | Maintainability/Low | RID-01 |
