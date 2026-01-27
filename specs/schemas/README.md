# JSON Schema Specifications

This directory contains **JSON Schema** definitions for all structured artifacts produced by the FOSS Launcher system. These schemas enforce data contracts between workers, validation gates, and external services.

## Overview

Every runtime artifact that crosses worker boundaries or is persisted to disk MUST validate against its corresponding schema. This ensures:

- **Type safety** - Correct data types for all fields
- **Contract enforcement** - Required fields are always present
- **Validation consistency** - Gates use schemas to verify artifacts
- **Evolution tracking** - Schema versioning enables backward compatibility

## Schema Files

### Core Artifacts

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `run_config.schema.json` | Run configuration | User/Orchestrator | Gate 0, launch_validate |
| `repo_inventory.schema.json` | Repository analysis | W1 RepoIngester | Gate C, W2-W9 |
| `product_facts.schema.json` | Product facts | W2 FactsBuilder | Gate D, W3-W9 |
| `evidence_map.schema.json` | Claim citations | W2 FactsBuilder | Gate E, W4-W9 |
| `page_plan.schema.json` | Page inventory | W3 PagePlanner | Gate F, W4-W9 |
| `validation_report.schema.json` | Gate results | All gates | Orchestrator |
| `truth_lock_report.schema.json` | Claim markers | W4 ContentWriter | Gate I |

### Site Context

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `site_context.schema.json` | Site/workflow SHAs + Hugo config | W1 RepoIngester | Gate B, Orchestrator |
| `hugo_facts.schema.json` | Hugo configuration | W1 RepoIngester | Gate B, W3-W9 |

### Rulesets & Templates

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `ruleset.schema.json` | Ruleset definitions | Manual authoring | launch_validate |

### Patch Engine

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `patch_bundle.schema.json` | File patches | W4 ContentWriter | W5 PatchValidator |
| `event.schema.json` | State events | All workers | W8 TelemetryCollector |

### Snippet & Catalog

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `snippet_catalog.schema.json` | Code examples | W7 SnippetCurator | Gate H |

### Git Operations

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `commit_request.schema.json` | Commit request | W9 PRCreator | GitHub commit service |
| `commit_response.schema.json` | Commit response | GitHub commit service | W9 PRCreator |
| `open_pr_request.schema.json` | PR request | W9 PRCreator | GitHub commit service |
| `open_pr_response.schema.json` | PR response | GitHub commit service | Orchestrator |
| `issue.schema.json` | Issue metadata | W9 PRCreator | GitHub service |
| `pr.schema.json` | Pull request metadata | W9 PRCreator | GitHub service |

### MCP Server

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| `api_error.schema.json` | MCP error response | MCP server | All workers |
| `frontmatter_contract.schema.json` | Page frontmatter | W4 ContentWriter | Gate G |

## Schema Validation

### Manual Validation

Validate any artifact against its schema:

```bash
# Using jsonschema CLI (install: pip install jsonschema)
jsonschema -i path/to/artifact.json specs/schemas/<schema_name>.schema.json

# Using Python
python -c "
import json, jsonschema
schema = json.load(open('specs/schemas/<schema_name>.schema.json'))
artifact = json.load(open('path/to/artifact.json'))
jsonschema.validate(artifact, schema)
print('Valid')
"
```

### Automated Validation

The spec pack validator checks all pinned pilot configs against schemas:

```bash
# Validate all schemas + pinned pilot configs
python scripts/validate_spec_pack.py

# Output on success:
# Validating spec pack...
# [OK] All schemas are valid
# [OK] All pinned configs validate
# Spec pack validation PASSED
```

### Runtime Validation

All workers and gates validate artifacts using the schemas:

```python
from launch.validators.schema import validate_artifact

# Validate artifact before producing it
validate_artifact(artifact_data, "run_config")  # Uses run_config.schema.json

# Validate artifact after consuming it
validate_artifact(loaded_data, "product_facts")  # Uses product_facts.schema.json
```

## Adding New Schemas

When adding a new schema:

1. **Create the schema file**
   - Use JSON Schema Draft 2020-12 format
   - Follow existing naming: `<artifact_type>.schema.json`
   - Include `$schema`, `$id`, `title`, `description`, `type`, `properties`, `required`

2. **Update this README**
   - Add entry to relevant table above
   - Document primary producer and validators

3. **Update validation tooling**
   - Add schema to `scripts/validate_spec_pack.py` if it has pinned examples
   - Update `src/launch/validators/schema.py` if runtime validation needed

4. **Update spec documentation**
   - Reference schema in relevant spec files (specs/*.md)
   - Add examples in spec text using schema-valid JSON/YAML

5. **Validate the schema itself**
   ```bash
   # Ensure schema is valid JSON Schema
   python -c "
   import json, jsonschema
   schema = json.load(open('specs/schemas/<new_schema>.schema.json'))
   jsonschema.Draft202012Validator.check_schema(schema)
   print('Schema is valid')
   "
   ```

## Schema Naming Conventions

- **Suffix**: Always use `.schema.json` (not `.json`)
- **Case**: Use snake_case for filenames (e.g., `product_facts.schema.json`)
- **Clarity**: Name should match artifact type exactly
- **Versioning**: If breaking changes needed, create `<artifact>.v2.schema.json`

## Schema Evolution

### Backward-Compatible Changes (Safe)
- Adding optional fields (`"required"` list unchanged)
- Relaxing constraints (e.g., `minLength: 5` → `minLength: 3`)
- Adding new enum values (if consumers handle unknowns)

### Breaking Changes (Require Versioning)
- Removing required fields
- Changing field types
- Tightening constraints
- Removing enum values

**Policy**: Prefer backward-compatible changes. If breaking change needed, create versioned schema and migration guide.

## Validation Reports

All validation gate results follow `validation_report.schema.json`:

```json
{
  "gate_id": "Gate-D",
  "status": "PASS",
  "timestamp": "2026-01-27T13:00:00Z",
  "checks": [
    {
      "check_id": "product_facts_schema",
      "status": "PASS",
      "message": "Artifact validates against schema"
    }
  ]
}
```

This enables:
- **Deterministic pass/fail** - No subjective checks
- **Automated fix loops** - Failed checks include fix hints
- **Audit trails** - All validation results logged

## Common Issues

### Schema Not Found
```
FileNotFoundError: specs/schemas/unknown.schema.json
```
**Fix**: Ensure schema file exists and name matches exactly (case-sensitive).

### Validation Failure
```
jsonschema.ValidationError: 'required_field' is a required property
```
**Fix**: Check artifact has all required fields. Review schema's `"required"` list.

### Schema Invalid
```
jsonschema.SchemaError: 'properties' must be an object
```
**Fix**: Schema itself is malformed. Validate schema structure using `jsonschema.Draft202012Validator.check_schema()`.

## References

- **Spec**: [specs/09_validation_gates.md](../09_validation_gates.md) - Validation architecture
- **Implementation**: `src/launch/validators/schema.py` - Schema validation utilities
- **Tooling**: `scripts/validate_spec_pack.py` - Spec pack validator
- **JSON Schema Docs**: https://json-schema.org/draft/2020-12/json-schema-validation

## Schema Authority

All schemas in this directory are **BINDING**. Workers MUST produce schema-valid artifacts. Gates MUST validate artifacts against schemas before passing them downstream.

**Enforcement**: Gates B-K validate artifacts. Non-compliant artifacts trigger fix loops (see [specs/09_validation_gates.md](../09_validation_gates.md)).
