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

## Adapter Interface Contract (binding)

All adapters MUST implement the following interface methods.

### Interface Methods

```python
class RepoAdapter(Protocol):
    """Adapter interface for repo-specific ingestion logic."""

    def extract_distribution(
        self,
        repo_root: Path,
        repo_inventory: RepoInventory
    ) -> DistributionInfo:
        """
        Extract package distribution information.

        Returns:
          DistributionInfo with:
          - install_methods: list of install methods (pip, nuget, npm, etc.)
          - install_commands: list of exact install commands
          - package_name: canonical package name
          - package_url: package registry URL (if available)

        If distribution cannot be determined, return empty DistributionInfo with note.
        """
        ...

    def extract_public_api_entrypoints(
        self,
        repo_root: Path,
        repo_inventory: RepoInventory
    ) -> PublicAPIEntrypoints:
        """
        Extract public API surface entrypoints.

        Returns:
          PublicAPIEntrypoints with:
          - modules: list of public module names
          - classes: list of public class names (top-level only)
          - functions: list of public function names (top-level only)
          - entrypoint_path: main entrypoint file (e.g., __init__.py, index.js)

        If API surface cannot be determined, return empty with note.
        """
        ...

    def extract_examples(
        self,
        repo_root: Path,
        repo_inventory: RepoInventory
    ) -> List[SnippetCandidate]:
        """
        Extract example code snippets from repo.

        Returns:
          List of SnippetCandidate with:
          - source_file: relative path to source file
          - start_line, end_line: line range
          - snippet_text: raw snippet code
          - language: detected language
          - tags: list of inferred tags (quickstart, workflow name, etc.)

        Returns empty list if no examples found.
        """
        ...

    def recommended_validation(
        self,
        repo_root: Path,
        repo_inventory: RepoInventory
    ) -> ValidationRecommendations:
        """
        Recommend test/validation commands for this repo.

        Returns:
          ValidationRecommendations with:
          - test_commands: list of test commands (if tests present)
          - lint_commands: list of lint commands (if linter config present)
          - build_commands: list of build commands (if applicable)

        Returns empty if no validation commands discoverable.
        """
        ...
```

### Adapter Registration

Adapters MUST be registered in `src/launch/adapters/registry.py`:
```python
ADAPTER_REGISTRY = {
    "python:python_src_pyproject": PythonSrcPyprojectAdapter(),
    "python:python_flat_setup_py": PythonFlatSetupPyAdapter(),
    "node:node_src_package_json": NodeSrcPackageJsonAdapter(),
    "dotnet:dotnet_flat_csproj": DotNetFlatCsprojAdapter(),
    "universal:best_effort": UniversalBestEffortAdapter(),
}
```

### Adapter Fallback Behavior

All adapters MUST implement graceful fallback:
- If a method cannot extract info, return empty structure with `note` field explaining why
- Do NOT raise exceptions (except for internal errors)
- Do NOT return None (always return typed structure)

### Universal Fallback Adapter (required)

The `UniversalBestEffortAdapter` is a special adapter that MUST always be available:
- Attempts basic heuristics for all repo types
- Does not require manifests or specific structure
- Extracts minimal info (README parsing, basic file tree scan)
- Used when no platform-specific adapter matches

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

---

## Adapter Implementation Guide (binding)

This section provides concrete guidance for implementing new adapters or extending existing ones.

### Adapter Registration and Discovery

**Adapter registry location**: `src/adapters/registry.py` (or equivalent module)

**Required registration fields**:
- `adapter_id`: Unique identifier (e.g., `python_src_pyproject`, `dotnet_sdk_style`)
- `platform_family`: Platform (e.g., `python`, `dotnet`, `java`)
- `repo_archetype`: Repository structure pattern (e.g., `src_layout`, `flat_layout`, `monorepo`)
- `priority`: Selection priority (1-100, higher = preferred when multiple adapters match)
- `match_criteria`: Function that determines if adapter applies to a given repo

**Adapter selection algorithm** (binding):
1. Filter adapters by `platform_family` from `repo_profile.platform_family`
2. For each adapter, evaluate `match_criteria(repo_inventory)` → returns match score (0-100)
3. Select adapter with highest match score (or highest priority if tie)
4. If no adapters match (all score 0), fall back to `universal` adapter
5. Record selected `adapter_id` in `repo_profile.adapter_id`
6. Emit telemetry event `ADAPTER_SELECTED` with adapter_id and match score

### Implementing a New Adapter

**Step 1: Create adapter class**
```python
from src.adapters.base import RepoAdapter

class PythonSrcLayoutAdapter(RepoAdapter):
    """Adapter for Python repos with src/ layout and pyproject.toml."""

    adapter_id = "python_src_pyproject"
    platform_family = "python"
    repo_archetype = "src_layout"
    priority = 80  # Higher than flat layout (70)

    @classmethod
    def match_criteria(cls, repo_inventory: RepoInventory) -> int:
        """Return match score 0-100."""
        score = 0
        if "pyproject.toml" in repo_inventory.package_manifests:
            score += 50
        if "src/" in repo_inventory.source_roots:
            score += 40
        if "setup.py" in repo_inventory.package_manifests:
            score += 10  # Bonus if both present
        return score
```

**Step 2: Implement interface methods**
All adapters MUST implement:
- `extract_distribution()`: Parse package manifests, return install commands
- `extract_public_api_entrypoints()`: Identify public modules/classes/functions
- `extract_dependencies()`: Parse dependencies (runtime + dev + optional groups)
- `infer_test_commands()`: Recommend test commands based on repo structure
- `extract_runtime_requirements()`: Identify language version, OS requirements

**Step 3: Handle edge cases gracefully**
- If manifest file is malformed (invalid TOML/JSON/XML), emit warning, return empty result
- If multiple manifests conflict (e.g., setup.py and pyproject.toml disagree), prefer newer format (pyproject.toml)
- If no manifests found, attempt heuristic detection (e.g., look for import statements), mark as low confidence
- Always emit telemetry for missing/malformed manifests

**Step 4: Test adapter thoroughly**
Required tests:
- Match criteria correctly identifies target repos (true positives)
- Match criteria rejects non-matching repos (true negatives)
- Extract methods handle missing manifests gracefully
- Extract methods handle malformed manifests gracefully
- Adapter is deterministic (same repo → same outputs)

### Adapter Best Practices

**Manifest parsing**:
- MUST validate manifest schema before extraction (use jsonschema, toml validator)
- MUST handle missing optional fields gracefully (return None or empty list)
- MUST NOT assume manifest structure (always check field existence before access)
- SHOULD cache parsed manifests (avoid re-parsing same file multiple times)

**API surface detection**:
- MUST respect explicit public API declarations (e.g., `__all__` in Python, `public` modifier in Java)
- SHOULD use static analysis tools when available (e.g., AST parsing, reflection)
- MUST NOT expose internal/private APIs (those prefixed with `_` in Python, `internal` namespace in .NET)
- SHOULD mark inferred APIs as `confidence: low` when heuristic-based

**Dependency extraction**:
- MUST extract runtime dependencies separately from dev dependencies
- MUST extract optional dependency groups (e.g., pip extras, NuGet groups)
- SHOULD include version constraints in dependency records (e.g., `>=1.0.0,<2.0.0`)
- MUST NOT include system dependencies in language dependencies (keep separate)

**Error handling**:
- MUST emit telemetry event `ADAPTER_EXTRACTION_FAILED` with error_code and details
- MUST return partial results when possible (e.g., if install method found but dependencies failed, return install method)
- MUST log warnings for ambiguous situations (e.g., multiple install methods detected)
- MUST NOT raise exceptions (catch and convert to error results with notes)

**Performance**:
- SHOULD minimize file system operations (batch reads, avoid repeated stat() calls)
- SHOULD parallelize independent extractions (e.g., parse pyproject.toml and scan API simultaneously)
- MUST respect timeout limits (default: 60s per adapter method)
- SHOULD implement caching for expensive operations (AST parsing, package index lookups)

### Adapter Testing and Validation

**Required test coverage**:
- Unit tests for each adapter method (mock file system, test edge cases)
- Integration tests with real repos (test against 5+ representative repos per adapter)
- Determinism tests (run adapter 10x on same repo, assert identical outputs)
- Performance tests (adapter completes within timeout on large repos)

**Test repos selection criteria**:
- Include repos with minimal/sparse manifests (test graceful degradation)
- Include repos with conflicting manifests (test conflict resolution)
- Include repos with no manifests (test heuristic detection)
- Include repos with unusual structures (test robustness)

### Adapter Versioning and Evolution

**Adapter version tracking**:
- Each adapter MUST have `version` field (semantic versioning: `1.0.0`)
- Version MUST increment on breaking changes (e.g., output schema change)
- Version MUST be recorded in `repo_profile.adapter_version` for traceability

**Backward compatibility**:
- MUST maintain compatibility with existing `repo_inventory.schema.json` and `product_facts.schema.json`
- SHOULD add new optional fields rather than modifying existing required fields
- MUST document breaking changes in adapter changelog

**Migration guide**:
- When updating adapter (e.g., improving manifest parsing), test against all known repos using that adapter
- Document expected output differences (e.g., "now extracts optional dependencies that were previously missed")
- Provide migration instructions for consumers (e.g., "re-run ingestion to get updated API surface")

### Fallback Behavior (universal adapter)

The `universal` adapter is the fallback when no platform-specific adapter matches.

**Universal adapter behavior**:
- Attempts generic manifest detection (package.json, Gemfile, Cargo.toml, etc.)
- Uses file extension heuristics to identify language (e.g., .py → Python)
- Scans for common patterns (README install instructions, CI config files)
- Returns low-confidence results with notes indicating "universal adapter used"
- MUST emit telemetry event `UNIVERSAL_ADAPTER_USED` with reason

**When to trigger universal adapter**:
- No platform_family detected in repo_profile
- Platform_family detected but no matching adapter (e.g., rare language)
- All platform-specific adapters score 0 in match_criteria

### Adapter Debugging and Troubleshooting

**Enable adapter debug logging**:
- Set `ADAPTER_DEBUG=1` environment variable
- Logs include: match scores, extracted values, warnings, execution time
- Logs written to `RUN_DIR/reports/adapter_debug.log`

**Common adapter issues**:
1. **Adapter not selected**: Check match_criteria logic, ensure priority is set correctly
2. **Empty extractions**: Check manifest file paths, validate parsing logic
3. **Incorrect API surface**: Verify public/private detection logic, check `__all__` handling
4. **Performance issues**: Profile adapter methods, add caching, reduce file I/O

**Acceptance criteria**:
- Adapter implementation follows interface contract
- All edge cases handled gracefully (no exceptions raised)
- Deterministic outputs verified by tests
- Performance within timeout limits
- Documentation includes usage examples and test repos
