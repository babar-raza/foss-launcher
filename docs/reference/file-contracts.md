# File Contracts Reference

**Canonical Source**: This is the authoritative reference for all file contracts (JSON schemas) used by the FOSS Launcher.

**Source**: [`specs/schemas/`](../specs/schemas/)

---

## Table of Contents

1. [Overview](#overview)
2. [Core Artifacts](#core-artifacts)
3. [Site Context](#site-context)
4. [Rulesets & Templates](#rulesets--templates)
5. [Patch Engine](#patch-engine)
6. [Snippet & Catalog](#snippet--catalog)
7. [Git Operations](#git-operations)
8. [MCP Server](#mcp-server)
9. [Validation](#validation)

---

## Overview

All structured artifacts produced by the FOSS Launcher system MUST validate against their corresponding JSON Schema. This ensures:

- **Type safety** - Correct data types for all fields
- **Contract enforcement** - Required fields are always present
- **Validation consistency** - Gates use schemas to verify artifacts
- **Evolution tracking** - Schema versioning enables backward compatibility

---

## Core Artifacts

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`run_config.schema.json`](run_config.schema.json) | Run configuration | User/Orchestrator | Gate 0, launch_validate |
| [`repo_inventory.schema.json`](repo_inventory.schema.json) | Repository analysis | W1 RepoScout | Gate C, W2-W9 |
| [`product_facts.schema.json`](product_facts.schema.json) | Product facts | W2 FactsBuilder | Gate D, W3-W9 |
| [`evidence_map.schema.json`](evidence_map.schema.json) | Claim citations | W2 FactsBuilder | Gate E, W4-W9 |
| [`page_plan.schema.json`](page_plan.schema.json) | Page inventory | W4 IAPlanner | Gate F, W4-W9 |
| [`validation_report.schema.json`](validation_report.schema.json) | Gate results | All gates | Orchestrator |
| [`truth_lock_report.schema.json`](truth_lock_report.schema.json) | Claim markers | W4 ContentWriter | Gate I |

### Example: run_config.schema.json

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "run_config.schema.json",
  "type": "object",
  "required": ["schema_version", "product_slug", "product_name", "family", "github_repo_url", "github_ref", "required_sections", "site_layout", "allowed_paths", "llm", "mcp", "telemetry", "commit_service", "templates_version", "ruleset_version", "allow_inference", "max_fix_attempts", "budgets", "target_platform"],
  "properties": {
    "schema_version": {"type": "string"},
    "product_slug": {"type": "string", "minLength": 1},
    "target_platform": {"type": "string", "enum": ["python", "typescript", "javascript", "java", "dotnet", "cpp", "go", "ruby", "php", "kotlin", "swift", "rust"]}
  }
}
```

---

## Site Context

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`site_context.schema.json`](site_context.schema.json) | Site/workflow SHAs + Hugo config | W1 RepoScout | Gate B, Orchestrator |
| [`hugo_facts.schema.json`](hugo_facts.schema.json) | Hugo configuration | W1 RepoScout | Gate B, W3-W9 |

---

## Rulesets & Templates

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`ruleset.schema.json`](ruleset.schema.json) | Ruleset definitions | Manual authoring | launch_validate |

---

## Patch Engine

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`patch_bundle.schema.json`](patch_bundle.schema.json) | File patches | W6 LinkerAndPatcher | W7 Validator |
| [`event.schema.json`](event.schema.json) | State events | All workers | W8 TelemetryCollector |

---

## Snippet & Catalog

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`snippet_catalog.schema.json`](snippet_catalog.schema.json) | Code examples | W3 SnippetCurator | Gate H |

---

## Git Operations

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`commit_request.schema.json`](commit_request.schema.json) | Commit request | W9 PRManager | GitHub commit service |
| [`commit_response.schema.json`](commit_response.schema.json) | Commit response | GitHub commit service | W9 PRManager |
| [`open_pr_request.schema.json`](open_pr_request.schema.json) | PR request | W9 PRManager | GitHub commit service |
| [`open_pr_response.schema.json`](open_pr_response.schema.json) | PR response | GitHub commit service | Orchestrator |
| [`issue.schema.json`](issue.schema.json) | Issue metadata | W9 PRManager | GitHub service |
| [`pr.schema.json`](pr.schema.json) | Pull request metadata | W9 PRManager | GitHub service |

---

## MCP Server

| Schema | Artifact Type | Primary Producer | Validators |
|--------|---------------|------------------|------------|
| [`api_error.schema.json`](api_error.schema.json) | MCP error response | MCP server | All workers |
| [`frontmatter_contract.schema.json`](frontmatter_contract.schema.json) | Page frontmatter | W4 IAPlanner | Gate G |

---

## Validation

### Manual Validation

```bash
# Using jsonschema CLI
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

```bash
# Validate all schemas + pinned pilot configs
python scripts/validate_spec_pack.py
```

### Runtime Validation

```python
from launch.validators.schema import validate_artifact

# Validate artifact before producing it
validate_artifact(artifact_data, "run_config")

# Validate artifact after consuming it
validate_artifact(loaded_data, "product_facts")
```

---

## Schema Naming Conventions

- **Suffix**: Always use `.schema.json`
- **Case**: Use snake_case (e.g., `product_facts.schema.json`)
- **Clarity**: Name should match artifact type exactly

---

## Schema Evolution

### Backward-Compatible Changes (Safe)
- Adding optional fields
- Relaxing constraints
- Adding new enum values

### Breaking Changes (Require Versioning)
- Removing required fields
- Changing field types
- Tightening constraints

---

## See Also

- [`specs/schemas/README.md`](../specs/schemas/README.md) - Full schema documentation
- [`specs/09_validation_gates.md`](../specs/09_validation_gates.md) - Validation architecture
- [`docs/reference/config.md`](./config.md) - Run configuration reference
- [`src/launch/validators/schema.py`](../src/launch/validators/schema.py) - Schema validation utilities
