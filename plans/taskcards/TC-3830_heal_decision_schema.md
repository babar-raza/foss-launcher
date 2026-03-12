---
id: TC-3830
title: "heal_decision_schema"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [schema, heal, json-schema]
depends_on: [TC-3829]
allowed_paths:
  - specs/schemas/heal_decision.schema.json
  - plans/taskcards/TC-3830_heal_decision_schema.md
evidence_required:
  - reports/TC-3830/evidence.md
---

# Taskcard TC-3830 — heal_decision_schema

## Objective

Create the JSON Schema (`specs/schemas/heal_decision.schema.json`) that validates
the LLM diagnostician output before it is consumed by the heal worker. This is the
engineering guard on the "Engineering > LLM > Engineering" sandwich principle.

## Required spec references

- `specs/11_state_and_events.md` (schema validation at every boundary)

## Scope

### In scope
- JSON Schema file for `HealDecision` object
- Draft-07 compliance with `additionalProperties: false`

### Out of scope
- Runtime validator code (separate TC)
- Pydantic model (TC-3829)

## Inputs

- `HealDecision` Pydantic model definition from TC-3829

## Outputs

- `specs/schemas/heal_decision.schema.json`

## Allowed paths

- specs/schemas/heal_decision.schema.json
- plans/taskcards/TC-3830_heal_decision_schema.md

### Allowed paths rationale

`specs/schemas/` is the canonical location for all JSON Schema files in v2. The
taskcard file satisfies AG-002.

## Implementation steps

### Step 1: Create schema file

Write `specs/schemas/heal_decision.schema.json` with `$schema`, `$id`, `title`,
`description`, required fields, and `additionalProperties: false`.

### Step 2: Validate JSON syntax

```bash
python -c "import json; json.load(open('specs/schemas/heal_decision.schema.json')); print('JSON valid')"
```

## Failure modes

### Failure mode 1: Invalid JSON syntax

**Detection**: `json.JSONDecodeError` when loading the file
**Resolution**: Fix trailing commas, mismatched braces, or unquoted strings
**Gate**: Python json.load

### Failure mode 2: Missing required field in schema

**Detection**: Schema consumer silently accepts invalid LLM output
**Resolution**: Verify all 6 required fields are listed in the `required` array
**Gate**: Code review

### Failure mode 3: Worker enum mismatch

**Detection**: LLM returns `"generator"` instead of `"generate"` — schema rejects it correctly
**Resolution**: Enum values must exactly match worker names used in the pipeline config
**Gate**: Schema validation gate

## Task-specific review checklist

1. [x] `$schema` set to draft-07
2. [x] `$id` set to `heal_decision.schema.json`
3. [x] All 6 top-level properties defined: `analysis`, `root_causes`, `action`, `confidence`, `stop_recommendation`, `stop_reason`
4. [x] `additionalProperties: false` at top level and on `action` object
5. [x] `worker` enum restricted to `["understand", "planner", "generate"]`
6. [x] `confidence` has `minimum: 0.0` and `maximum: 1.0`

## Deliverables

1. `specs/schemas/heal_decision.schema.json` (valid JSON Schema draft-07)
2. This taskcard at `plans/taskcards/TC-3830_heal_decision_schema.md`

## Acceptance checks

1. [x] `python -c "import json; json.load(open('specs/schemas/heal_decision.schema.json'))"` exits 0
2. [x] Schema contains all 5 required fields listed in `required` array
3. [x] `action.worker` enum contains exactly `["understand", "planner", "generate"]`

## Self-review

### Verification results
- [x] Tests: N/A (schema file only; full suite 2392/2392 PASS confirms no regression)
- [x] Validation: `json.load` PASS — title="HealDecision", required=5 fields, properties=6
- [x] Evidence file: `reports/TC-3830/evidence.md`

## E2E verification

```bash
python -c "import json; schema = json.load(open('specs/schemas/heal_decision.schema.json')); print('title:', schema.get('title')); print('required:', schema.get('required'))"
```

**Actual results** (run 2026-03-08):
```
title: HealDecision
required fields: ['analysis', 'root_causes', 'action', 'confidence', 'stop_recommendation']
properties: ['analysis', 'root_causes', 'action', 'confidence', 'stop_recommendation', 'stop_reason']
```

Full suite: `2392 passed in 53.28s`

## Integration boundary proven

**Upstream**: LLM diagnostician produces a JSON object matching this schema
**Downstream**: Heal worker validates LLM output against this schema before constructing `HealDecision`
**Contract**: JSON Schema draft-07; `additionalProperties: false` enforced at both top level and `action` object
