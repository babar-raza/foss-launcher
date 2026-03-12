# Run ID v3 (Family+Platform) — Healing Gap Index

## Context

Run IDs were changed from `r_YYMMDD_hex6` to `YYMMDD_HHMMSS_{family}_{platform}`
to restore at-a-glance family/platform identification and Explorer sort order.
Self-review identified 6 gaps that must be closed before this change is
production-grade.

**Current state of code** (as shipped):
- `src/launcher/util/run_id.py`: `generate_run_id(family, platform)` → `YYMMDD_HHMMSS_{fam}_{plat}`
- `src/launcher/orchestrator/run_loop.py`: calls `generate_run_id(config.family, config.platform)`, **no collision guard**
- `scripts/run_pilot.py`: same call, **no collision guard**, `mkdir(exist_ok=True)` silently reuses dirs
- `tests/unit/util/test_run_id.py`: updated but missing edge-case and collision tests
- `tests/unit/orchestrator/test_run_manifest.py`: hardcoded IDs updated

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-RV3-01 | Same-second collision: two parallel runs for same family+platform produce identical IDs — no uniqueness suffix, no collision guard | Critical | RID-11 |
| G-RV3-02 | `run_pilot.py` has `mkdir(exist_ok=True)` after generation — silently merges into existing dir on collision, corrupting artifacts | Critical | RID-11 |
| G-RV3-03 | Empty/whitespace family or platform produces malformed IDs like `260307_082430__python` — no input validation | High | RID-12 |
| G-RV3-04 | Missing edge-case tests: empty inputs, max-length slugs, collision scenario, slug with only special chars | High | RID-12 |
| G-RV3-05 | AG-002 taskcard violation: `src/launcher/**` modified without taskcard (repeat offense) | Governance | RID-13 |
| G-RV3-06 | No logging when `_sanitize_slug` transforms values; docstring doesn't explain MAX_PATH or `aspose-` stripping rationale | Low | RID-14 |
