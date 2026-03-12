# SRI-02: run_config.schema.json additionalProperties Incompatibility

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 2 (Schema/Contract Alignment)
**Role:** Schema / Contract Fix
**Scope:** Resolve conflict between extended fields in generated configs and strict schema validation

---

## Problem

`config_generator.py` produces configs with extended fields (`github_ref`, `product_slug`, `product_name`, `budgets`, `telemetry`) that are NOT in `specs/schemas/run_config.schema.json`. That schema has `"additionalProperties": false`, meaning any config with these fields will fail JSON Schema validation.

Two options:
1. **Add extended fields to schema** — cleanest, makes them first-class
2. **Remove extended fields from generated output** — simplest, loses metadata
3. **Split into two files** — `run_config.yaml` (schema-valid) + `run_meta.yaml` (extended)

Recommended: Option 1 — add extended fields to schema as optional properties.

## Acceptance Checks

- [ ] Generated config from `config_generator.py` passes `run_config.schema.json` validation
- [ ] Extended fields are either in schema or removed from generator output
- [ ] Existing pilot configs still validate
- [ ] Unit test proves: `generate_config()` output → schema validation → pass
- [ ] `src/launcher/io/run_config.py` loads generated config without error

## Deliverables

1. Updated `specs/schemas/run_config.schema.json` (or updated `config_generator.py`)
2. Test in `tests/unit/intake/test_config_generator.py` asserting schema validity

## Hard Rules

- Must not break existing pipeline configs
- Must not silently discard data

## Review Dimensions

- Schema correctness
- Backward compatibility
- Test coverage

## Runbook

1. Read current `specs/schemas/run_config.schema.json`
2. Read `src/launcher/models/run_config.py` (pydantic model)
3. Decide approach (add to schema vs remove from generator)
4. Implement change
5. Add test: `generate_config()` → validate against schema → assert pass
6. Run full test suite
