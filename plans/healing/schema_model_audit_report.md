# Schema-Model Alignment Audit Report
# RunConfig ↔ run_config.schema.json

**Date:** 2026-03-08
**Taskcard:** SR-04
**Triggered by:** TC-3824 self-review (GAP-06)
**Tool:** Python 3.13 — `types.UnionType` + `typing.Union` dual check required for 3.10+ `X | None` syntax

---

## Field Alignment Table

| OPT | Field | Python Optional? | Schema type | Result |
|-----|-------|-----------------|-------------|--------|
| | `family` | No | `string` | OK |
| | `platform` | No | `string` | OK |
| | `repo_url` | No | `string` | OK |
| | `launch_tier` | No | `string` | OK |
| | `validation_profile` | No | `string` | OK |
| | `product_name` | No | `string` | OK |
| | `display_name` | No | `string` | OK |
| | `canonical_import` | No | `string` | OK |
| OPT | `llm` | Yes (`LLMConfig \| None`) | `["object", "null"]` | OK |
| | `seo` | No (`SEOConfig` default_factory) | ABSENT | OK (additionalProperties: true) |
| OPT | `telemetry` | Yes (`TelemetryConfig \| None`) | `["object", "null"]` | OK |
| | `output` | No (`OutputConfig` default_factory) | `object` | OK |

## Schema-Only Fields (not in RunConfig.model_fields)

These fields appear in the schema but are not `RunConfig` Pydantic fields. They are
accepted from YAML via `extra="ignore"` and passed through as raw dict values.

| Field | Schema type | Rationale |
|-------|-------------|-----------|
| `github_ref` | `string` | Intake config generator metadata; silently ignored by RunConfig |
| `product_slug` | `string` | Derived slug; silently ignored by RunConfig |
| `budgets` | `["object", "null"]` | Resource budget metadata; silently ignored by RunConfig. Nullable in schema to allow `budgets: null` in YAML without crashing the schema validation step |

## Findings

**All 12 RunConfig model fields are correctly aligned with the schema.**

No mismatches found after TC-3824 (telemetry fix) and SR-01 (output revert).

Key decisions documented:
- `seo` is absent from the schema intentionally — it was added after the schema was
  authored; `additionalProperties: true` allows it through without schema changes needed.
- `budgets` is nullable in the schema as a defensive measure: it is not a Pydantic field
  (silently ignored), but YAML configs may have `budgets: null` and the schema validation
  step in `load_and_validate_run_config` sees it before Pydantic parsing.
- `output` schema is `"object"` (not nullable) because `RunConfig.output` has a
  `default_factory` and is never Optional — `model_dump()` always produces a dict.

## Python 3.10+ Note

The `X | None` syntax (PEP 604) creates `types.UnionType`, not `typing.Union`. A correct
Optional check must handle both:
```python
import types
from typing import get_args, get_origin, Union

def is_optional(ann) -> bool:
    if isinstance(ann, types.UnionType):          # Python 3.10+ X | None
        return type(None) in ann.__args__
    return get_origin(ann) is Union and type(None) in get_args(ann)
```
The fitness test (`test_run_config_schema_fitness.py`) implements this correctly.

## Follow-up Taskcards

None required. Audit is clean.

If `seo` is ever added to the schema explicitly, annotate it as:
`"type": "object"` (not nullable — `SEOConfig` has a default factory).
