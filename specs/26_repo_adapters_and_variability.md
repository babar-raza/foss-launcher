# Repo Adapters and Variability (universal support)

## Purpose
To support **diverse products** and **wildly different repo structures**, the implementation MUST be adapter-driven.

This spec defines:
- what “adapter” means in this system
- how adapters are selected
- what they must output
- how the system behaves when evidence is sparse or contradictory

---

## Definitions
- **Adapter**: a deterministic strategy module keyed by `platform_family` + `repo_archetype` (and sometimes `product_type`)
  that knows how to extract:
  - distribution/install information
  - runtime requirements and optional dependency groups
  - public API entrypoints and “public vs internal” scope
  - docs/examples/tests locations and high-signal evidence
- **Repo archetype**: a stable label describing packaging/layout, e.g.:
  - `python_flat_setup_py`
  - `python_src_pyproject`
  - `monorepo_multi_package`
  - `docs_only`
  - `mixed_unknown`
- **Launch tier**: allowed depth of generated content (`minimal | standard | rich`).

---

## Adapter selection (binding)
Selection inputs:
- `RepoInventory.repo_profile.platform_family`
- `RepoInventory.repo_profile.repo_archetype` (recommended; derived during ingestion)
- `RepoInventory.repo_profile.package_manifests`
- `RepoInventory.source_roots` / `doc_roots` / `example_roots`
- `RunConfig.product_type` (optional)
- `RunConfig.repo_hints` (overrides)

Selection rule:
1) pick platform adapter (`python|dotnet|java|node|php|go|rust|multi`)
2) within platform, pick archetype adapter (flat/src/monorepo/mixed/docs-only)
3) apply `run_config.repo_hints` overrides when provided

**Requirement:** selection MUST be deterministic (same repo@ref => same adapter).

---

## Required adapter outputs (binding)
Each adapter MUST produce (best effort, without guessing):
- `ProductFacts.distribution`
- `ProductFacts.runtime_requirements`
- `ProductFacts.dependencies` (including optional groups/extras when present)
- `RepoInventory.repo_profile.public_api_entrypoints`
- `RepoInventory.repo_profile.public_api_scope` (when discoverable)
- `RepoInventory.repo_profile.recommended_test_commands` (best effort)

If any field cannot be determined, omit it or leave it empty rather than fabricate it.

---

## Public API scope (universal)
Some repos explicitly distinguish “public” vs “internal” APIs (e.g., `pkg._internal`).
Adapters SHOULD attempt to derive `public_api_scope` via:
1) explicit docs statements (“Only X is public; everything under Y is internal”)
2) package conventions (`_internal`, `_impl`, `internal`, leading underscore modules)
3) exports (`__all__`, `__init__` re-exports) when parseable

Writers MUST:
- generate reference pages for **public** scope only
- avoid documenting internal modules unless explicitly requested

---

## Sparse/contradictory evidence behavior (binding)
When evidence is sparse or contradictory:
- Default to `launch_tier=minimal`
- Produce fewer pages
- Prefer link-out to the repo and any official docs
- Avoid claiming formats/features not proven
- If README marketing conflicts with implementation notes, prefer higher-priority evidence and record the disagreement as a limitation (when grounded)

---

## Acceptance
- A new product with a new layout should only require adding an adapter (not changing the orchestrator).
- Adapters are unit-testable: given a repo snapshot, outputs are deterministic.
- The same repo at the same ref always yields the same chosen adapter.

---

## Product Type Auto-Inference (universal, binding)

If `product_type` is not provided in RunConfig, the system MUST infer it from repo signals.

### Inference rules (in priority order)

1. **CLI detection**:
   - `pyproject.toml` or `setup.py` declares `[project.scripts]` or `console_scripts`
   - Repo has `bin/`, `cli/`, or `cmd/` directories with executable entry points
   - README prominently features command-line usage examples
   → Set `product_type = "cli"`

2. **Service detection**:
   - `Dockerfile` or `docker-compose.yml` present at root
   - Contains `api/`, `server/`, `service/` directories
   - README mentions endpoints, REST API, or hosting
   → Set `product_type = "service"`

3. **Plugin detection**:
   - Package name contains "plugin", "extension", "addon"
   - Has explicit host application integration (e.g., pytest plugins, webpack plugins)
   - Declares plugin entry points (e.g., `[project.entry-points]`)
   → Set `product_type = "plugin"`

4. **SDK detection**:
   - Package name contains "sdk"
   - Multi-module public API with client/resource patterns
   - Contains API key/auth configuration patterns
   → Set `product_type = "sdk"`

5. **Library detection** (default for Python):
   - Single-package Python repo with import-based usage
   - Public API is classes/functions meant to be imported
   → Set `product_type = "library"`

6. **Tool detection**:
   - Standalone utility with clear input/output
   - Contains data processing or transformation logic
   → Set `product_type = "tool"`

7. **Other** (fallback):
   - Cannot determine type
   → Set `product_type = "other"` and log warning

### Recording inferred type
The inferred `product_type` MUST be recorded in:
- `repo_inventory.inferred_product_type`
- Telemetry event `product_type_inferred`

### Template implications
Writers MUST use `product_type` to select appropriate templates:
- **cli**: Emphasize installation, commands, flags, exit codes
- **library/sdk**: Emphasize imports, API patterns, supported formats
- **service**: Emphasize deployment, endpoints, authentication
- **plugin**: Emphasize host app integration, configuration
