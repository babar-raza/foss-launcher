# CB-05 — Taskcard + Spec Alignment

## Status: Done

## Checklist
- [x] TC-3815 frontmatter `allowed_paths` fixed: `tests/test_circuit_breaker.py` → `tests/unit/resilience/test_circuit_breaker.py`
- [x] TC-3815 body `## Allowed paths` section fixed (same)
- [x] TC-3815 status set to Done
- [x] `specs/llm_provider.md` Circuit Breaker section updated with all 8 config keys
- [x] Spec documents probe timeout, exponential backoff, and reset behavior

## Gap Linkage
- **CB-G7**: Taskcard TC-3815 frontmatter declares `allowed_paths: tests/test_circuit_breaker.py` but the actual test file was created at `tests/unit/resilience/test_circuit_breaker.py`. This is a governance violation — the taskcard's allowed paths don't match reality.
- **CB-G8**: The new recovery behavior (probe timeout, exponential backoff, backoff cap) is not documented in any spec file. `specs/llm_provider.md` describes the circuit breaker but does not mention probe-specific timeouts or backoff. A future engineer reading the spec would not know this behavior exists.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Update TC-3815 taskcard frontmatter and body to reference the correct test path: `tests/unit/resilience/test_circuit_breaker.py`.
2. Update `specs/llm_provider.md` (or the relevant circuit breaker section) to document:
   - Probe timeout: HALF_OPEN probes use a configurable shorter timeout (`probe_timeout_s`, default 15s)
   - Exponential backoff: recovery interval doubles after each failed probe, capped at `recovery_max_timeout_s`
   - Backoff reset: successful probe resets all backoff state to base values
   - Config keys: `probe_timeout_s`, `recovery_backoff_factor`, `recovery_max_timeout_s`

### Allowed paths
- `plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md`
- `specs/llm_provider.md`

### Forbidden
- Any other file/path. No code changes.

## Acceptance Checks

### CLI
- N/A (doc-only changes)

### Tests
- N/A (doc-only changes)

### Config respected end-to-end
- [ ] All 3 new config keys documented in spec with their defaults and valid ranges

### No mock data in production paths
- N/A

## Deliverables
- Updated `plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md`: Fix `allowed_paths` in frontmatter and body
- Updated `specs/llm_provider.md`: Add "Recovery Behavior" subsection under circuit breaker documentation

## Hard Rules
- Keep spec format consistent with existing sections in `specs/llm_provider.md`
- Document actual defaults, not aspirational ones
- Taskcard path fix must match both frontmatter and body `## Allowed paths` section
- No code changes
- Keep code/docs/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Consistency | Taskcard paths match actual file locations |
| Thoroughness | All 3 config fields documented with defaults, valid ranges, and behavior |
| Maintainability | Future engineer can understand recovery behavior from spec alone |
| Correctness | Spec accurately describes implemented behavior |
| Minimality | Only the necessary sections added/updated |

## Now (Runbook)

```bash
# 1. Fix taskcard TC-3815 allowed_paths
# (edit plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md)
# Change: tests/test_circuit_breaker.py → tests/unit/resilience/test_circuit_breaker.py

# 2. Read current spec
cat specs/llm_provider.md

# 3. Add recovery behavior section to spec
# (edit specs/llm_provider.md)

# 4. Verify consistency
grep -n "test_circuit_breaker" plans/taskcards/TC-3815_circuit_breaker_intelligent_recovery.md
# Expected: all references point to tests/unit/resilience/test_circuit_breaker.py
```
