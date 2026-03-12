# SRI-06: Replace Raw I/O with V2 Utility Functions

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 3 (Integration Depth)
**Role:** Integration
**Scope:** Use v2's existing IO utilities instead of raw stdlib calls

---

## Problem

The ported intake modules use raw `open()`, `yaml.safe_load()`, `yaml.dump()`, and `json.dump()` calls instead of v2's shared utilities:
- `src/launcher/io/yamlio.py` — YAML read/write with error handling
- `src/launcher/io/atomic.py` — atomic file writes (crash-safe)
- `src/launcher/io/schema_validation.py` — JSON schema validation

This means intake modules miss crash-safety guarantees and consistent error handling that the rest of v2 provides.

## Acceptance Checks

- [ ] `config_generator.py` uses `yamlio.write_yaml()` or `atomic.atomic_write()` for config output
- [ ] `config_loader.py` uses `yamlio.load_yaml()` for intake config loading
- [ ] `org_scanner.py` uses `atomic.atomic_write()` for state file persistence
- [ ] Schema validation of intake_config.yaml uses `schema_validation` module
- [ ] All unit tests pass
- [ ] Behavior unchanged (same output, same error messages)

## Deliverables

1. Updated `src/launcher/intake/config_generator.py`
2. Updated `src/launcher/intake/config_loader.py`
3. Updated `src/launcher/intake/org_scanner.py`

## Hard Rules

- Pure refactor — no behavioral changes
- If v2 utilities have incompatible signatures, document and skip (don't force-fit)

## Review Dimensions

- Consistency with v2 codebase patterns
- Error handling preservation
- Test stability

## Runbook

1. Read `src/launcher/io/yamlio.py`, `atomic.py`, `schema_validation.py` APIs
2. Identify all raw I/O calls in 5 intake modules
3. Replace where v2 utility signatures match
4. Run tests
