# PM-00: Per-Module Claim-Gated Expansion — Healing Gap Index

## Context

TC-3813 implemented claim-gated per_module page expansion. The self-review
identified 7 concrete gaps ranging from a correctness bug (case-sensitive
class matching) to missing tests and code hygiene issues. This healing
batch converts each gap into an executable taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| PM-G1 | Case-sensitive class matching in `_build_class_claim_index` misses lowercase mentions | Bug | PM-01 |
| PM-G2 | `import re as _re` mid-file + constants not in constants block | Hygiene | PM-02 |
| PM-G3 | Unused `product` parameter in `_class_name_to_slug` | Hygiene | PM-02 |
| PM-G4 | No test for class-aware claim assignment priority | Coverage | PM-03 |
| PM-G5 | No logging of viable/skipped class details | Observability | PM-04 |
| PM-G6 | `skeleton_variant` preservation in `_assign_skeletons` is overly broad | Correctness | PM-05 |
| PM-G7 | Possible other PlannedPage reconstruction sites missing `target_class` | Robustness | PM-05 |
| PM-G8 | Multiple classes falling back to `"reference-object"` slug will collide poorly | Edge case | PM-06 |
| PM-G9 | No test for slug collision between two class names | Coverage | PM-06 |

## Taskcard Summary

| ID | Title | Gaps Fixed |
|----|-------|-----------|
| PM-01 | Fix case-insensitive class-claim matching | PM-G1 |
| PM-02 | Code hygiene: imports, constants, dead parameter | PM-G2, PM-G3 |
| PM-03 | Add claim-assignment priority test | PM-G4 |
| PM-04 | Add viable-class observability logging | PM-G5 |
| PM-05 | Scope skeleton_variant preservation + audit PlannedPage reconstructions | PM-G6, PM-G7 |
| PM-06 | Slug collision robustness + test | PM-G8, PM-G9 |
