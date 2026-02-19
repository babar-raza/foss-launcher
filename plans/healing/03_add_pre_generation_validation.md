# Healing Plan: Pre-Generation Validation

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Validate page inputs before invoking the LLM to save tokens and surface failures early.

## Context

W5 calls the LLM for every page regardless of input quality. Pages with 0 claims, empty descriptions, or unresolved template tokens produce low-quality output that requires expensive W7 and gate_17 correction passes. Pre-generation validation costs < 1ms and produces actionable errors.

## Gap → Taskcard Mapping

| Gap ID | Description                                        | Taskcard |
|--------|----------------------------------------------------|----------|
| RD-03  | W5 invokes LLM without validating input quality    | RD-03    |

---

## Taskcard RD-03 — W5 Pre-Generation Input Validation

**Status**: Not Started
**Gap linkage**: RD-03 (00_REDESIGN.md §2.1 item 2, TC-2372)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add `context_validator.py` (new standalone module) exposing `validate_page_inputs(page, product_facts, run_config) -> ValidationResult`. Call it inside `_generate_single_page()` before the LLM call. On hard skip → emit stub page + `EVENT_PRE_GEN_SKIPPED`. On warnings only → log and proceed.

**Five checks**:
1. `claims_available` — page has ≥ 1 prose claim (not purely code-like)
2. `description_present` — page has non-empty `section_description` or `title`
3. `token_budget_nonzero` — effective token budget > 0
4. `no_placeholder_title` — title contains no `__TOKEN__` or `{{token}}` patterns
5. `claim_text_non_empty` — every assigned claim has non-empty `claim_text`

**Allowed paths**:
```
src/launch/workers/w5_section_writer/worker.py
src/launch/workers/w5_section_writer/context_validator.py    (new)
tests/unit/workers/test_context_validator.py                 (new)
```

**Forbidden**: any other file or path.

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd03_verify
# draft_manifest.json must have no "pre_gen_skipped" entries for valid pages
# All 21 pages must still be generated (no regressions)
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_context_validator.py -x -v
# 11 tests: each check (trigger + pass) + 1 all-OK
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Full suite must pass
```

**Config respected end-to-end**: `pre_gen_validation_enabled: true` (default). Set `false` to bypass.

**No mock data in production paths**: Validator reads live `page` and `product_facts` dicts only.

### Deliverables

- `context_validator.py` (new): `validate_page_inputs()` pure function; `ValidationResult` namedtuple with `(is_valid: bool, skip_reason: Optional[str], warnings: List[str])`
- `worker.py`: call validator before LLM; emit stub + event on `skip_reason`; log warnings and continue otherwise
- 11 unit tests: each of 5 checks × (trigger + pass) = 10 tests; plus 1 all-OK test
- `draft_manifest.json`: optional `pre_gen_skipped: bool`, `pre_gen_warnings: List[str]` per page entry (no schema change required for optional fields)

### Hard Rules

- Validator is a pure function — no I/O, no LLM calls, no side effects
- Skipped pages produce a valid stub `.md` (frontmatter + 1-line body) so downstream gates don't fail on missing files
- `_generate_single_page()` signature unchanged (validator wired internally)
- No new external deps
- `pre_gen_validation_enabled: false` escape hatch is a single `if not rc.get("pre_gen_validation_enabled", True): skip` guard — no separate code path

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All 5 checks implemented; skip path produces valid stub; no LLM called for skipped pages |
| Correctness | Zero valid pages skipped; zero invalid pages reach LLM |
| Evidence | Pilot manifest showing warnings; test output showing 11/11 |
| Test Quality | 11 unit tests, each check independently exercised; stub validity confirmed |
| Maintainability | `context_validator.py` standalone with docstrings; no entanglement with generator logic |
| Safety | Default-on; escape hatch via config; stub prevents downstream failures |
| Security | N/A |
| Reliability | Pure function; deterministic |
| Observability | `EVENT_PRE_GEN_SKIPPED` emitted; warnings visible in manifest |
| Performance | < 1ms per page (pure dict inspection) |
| Compatibility | No signature changes; new optional config key |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §W5 updated with pre-gen validation |

### Now (Runbook)

```bash
# 1. Create context_validator.py with ValidationResult namedtuple + validate_page_inputs()
# 2. Wire into worker.py _generate_single_page:
#      if rc.get("pre_gen_validation_enabled", True):
#          vr = validate_page_inputs(page, product_facts, rc)
#          if vr.skip_reason:
#              return _make_stub_manifest_entry(page, vr.skip_reason)
#          for w in vr.warnings: logger.warning("[W5] pre-gen: %s", w)
# 3. Add tests: tests/unit/workers/test_context_validator.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_context_validator.py -x -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Run pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd03_verify
```
