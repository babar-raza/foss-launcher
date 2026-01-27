# Repo Ingestion

## Purpose
Turn an unstructured public GitHub repo into deterministic structured knowledge.
This MUST adapt to different repo structures and product platforms/languages.

## Outputs
- RepoInventory (`schemas/repo_inventory.schema.json`) including `repo_profile`
- ProductFacts (`schemas/product_facts.schema.json`)
- EvidenceMap (`schemas/evidence_map.schema.json`)
- SnippetCatalog seed (may be refined later)

---

## Repo profiling (non-negotiable, binding)
Ingestion MUST produce a `repo_profile` that supports adaptation:

- `platform_family`: `python | dotnet | java | node | php | go | rust | multi | unknown`
- `primary_languages`: detected list (best effort)
- `build_systems`: detected list (pip/poetry/uv, nuget, maven/gradle, npm/yarn/pnpm, make/cmake, etc.)
- `package_manifests`: detected manifest paths (sorted)
- `example_locator`: how examples were found (rules + paths)
- `doc_locator`: how docs were found (rules + entrypoints)
- `recommended_test_commands`: best effort commands if present in repo docs

**Universality additions (recommended):**
- `repo_archetype`: a stable label for layout and packaging, used for adapter selection
- `public_api_scope`: which packages/modules are considered “public” vs internal (when discoverable)

If detection is uncertain, values may be `"unknown"` but MUST still be present where required by schema.

---

## Steps

### 1) Clone and fingerprint
- Clone repo at `github_ref`.
- Extract:
  - default branch
  - latest release tag if present
  - license file and license type (best effort)
  - primary language(s)
  - directory map (top-level and depth-limited scan)
- Record commit SHA and hashes.

### 2) Detect structure (adapter selection)
Deterministic heuristics (in order):
- Identify manifests: `pyproject.toml`, `requirements.txt`, `setup.py`, `*.csproj`, `*.sln`, `pom.xml`, `build.gradle`, `package.json`, `composer.json`, `go.mod`, `Cargo.toml`
- Identify example roots: `examples/`, `samples/`, `demo/`, `test-examples/`, `docs/examples/`
- Identify docs entrypoints: `README*`, `docs/`, `documentation/`, `site/`, `mkdocs.yml`, docusaurus configs, API reference folders
- Detect **monorepo signals**: multiple manifests, multiple language roots, or workspaces

Select `platform_family` based on strongest evidence (manifests + folder patterns). If multiple platforms are first-class, use `platform_family="multi"`.

### 3) Source roots discovery
Compute `source_roots` (sorted):
- If `src/` exists and contains language roots, prefer `src/` as primary.
- Else, detect top-level package roots (e.g., `aspose/`, `lib/`, `pkg/`).
- Else, fall back to repo root.
Store:
- `repo_inventory.source_roots`
- `repo_profile.source_layout` (`src_layout | flat_package | monorepo | mixed | unknown`)
- `repo_profile.repo_archetype` (optional but recommended)

### Edge Case: Empty Repository

**Detection:** Repository has zero files after clone (excluding .git/ directory)

**Behavior:**
1. Emit ERROR with code: `REPO_EMPTY` (see specs/01)
2. Do NOT generate repo_inventory.json (validation fails before artifact creation)
3. Exit with non-zero status code

**Rationale:** Cannot proceed without any content to document. User must provide repository with at least one file.

**Test Case:** See `pilots/pilot-empty-repo/` (TO BE CREATED during implementation phase)

### 4) Docs discovery
`doc_roots` MUST include:
- `docs/` if present
- any root-level `*.md` beyond README that look like product docs or implementation notes
  (heuristic: contains headings like Features/Installation/Usage/Architecture/Limitations/Implementation)
Store `repo_inventory.doc_roots` and `doc_entrypoints` (sorted).

#### Root-level documentation discovery (universal, binding)
Doc discovery MUST explicitly scan root-level `*.md` files beyond README:

**Pattern-based detection** (include if filename matches):
- `*_IMPLEMENTATION*.md`, `*_SUMMARY*.md`
- `ARCHITECTURE*.md`, `DESIGN*.md`, `SPEC*.md`
- `CHANGELOG*.md`, `CONTRIBUTING*.md` (metadata, not content evidence)
- `*_NOTES*.md`, `*_PLAN*.md`, `ROADMAP*.md`

**Content-based detection** (scan first 50 lines for headings):
- "Features", "Limitations", "Implementation", "Architecture"
- "Supported", "Not supported", "TODO", "Known Issues"
- "API", "Public API", "Usage", "Quick Start"

Files matching these patterns MUST be added to `doc_entrypoints` with:
- `doc_type: "implementation_notes" | "architecture" | "changelog" | "other"`
- `evidence_priority: high` for implementation notes (see 03_product_facts_and_evidence.md)

#### Phantom path detection (universal, binding)

**Detection algorithm**:
1. Scan file types: `*.md`, `*.rst`, `*.txt` (documentation files)
2. Extract path references using regex: `(?:examples?|samples?|demos?|docs?|documentation)/[a-zA-Z0-9_/.-]+`
3. For each extracted path:
   a. Normalize to relative path from repo root
   b. Check if path exists in `repo_inventory.file_tree`
   c. If not exists, record as phantom_path

**Recording behavior** (when phantom path detected):
1. Record a `phantom_path` entry in `repo_inventory.phantom_paths` with:
   - `claimed_path`: the path mentioned (normalized)
   - `source_file`: relative path where it was claimed
   - `source_line`: line number (via regex match position)
   - `detection_pattern`: the regex pattern that matched
2. Emit telemetry warning event: `phantom_path_detected` with all fields
3. Do NOT fail the run - proceed with fallback discovery chains
4. If the phantom path was claimed as an examples source, mark related claims with `confidence: low`

**Schema requirement**:
Add to `repo_inventory.schema.json`:
```json
"phantom_paths": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["claimed_path", "source_file", "detection_pattern"],
    "properties": {
      "claimed_path": {"type": "string"},
      "source_file": {"type": "string"},
      "source_line": {"type": "integer", "minimum": 1},
      "detection_pattern": {"type": "string"}
    }
  }
}
```

This prevents silent failures when READMEs promise resources that don't exist.

### 5) Examples discovery

**Discovery order** (binding):
1. Scan for standard example directories in order: `examples/`, `samples/`, `demo/`
2. For each directory that exists in `repo_inventory.file_tree`, add to `example_roots`
3. If docs/README mention additional example paths (via phantom path detection), verify existence before adding
4. Sort `example_roots` alphabetically for determinism

**Edge case handling**:
- If `example_roots` is empty after scanning all standard directories, treat test directories as "example candidates" for snippet extraction (mark snippets with `source_type: "test_example"`)
- If docs mention an examples path that does not exist, record as phantom_path (see phantom path detection section) and do NOT add to `example_roots`
- MUST emit telemetry event `EXAMPLE_DISCOVERY_COMPLETED` with count of example roots found

Store `repo_inventory.example_roots` and `example_paths` (sorted).

### Repository Fingerprinting Algorithm

**Purpose:** Deterministic repo_fingerprint for caching and validation

**Algorithm:**
1. List all non-phantom files (exclude paths in phantom_paths)
2. For each file: Compute `SHA-256(file_path + "|" + file_content)`
3. Sort file hashes lexicographically (C locale, byte-by-byte)
4. Concatenate sorted hashes (no delimiters)
5. Compute `SHA-256(concatenated_hashes)` → **repo_fingerprint**
6. Store in repo_inventory.json field: `repo_fingerprint` (string, 64-char hex)

**Determinism:** Guaranteed (SHA-256 is deterministic, sorting is deterministic)

**Example:**
```json
{
  "repo_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
}
```

### 6) Test discovery
`test_roots` MUST include any of the following directories that exist in the repository: `tests/`, `test/`, `__tests__/`, `spec/`.
Store `repo_inventory.test_roots` (sorted list of discovered test directories) and update `repo_profile.recommended_test_commands`.

**Test command discovery**:
- Check for common test commands in order: `npm test`, `pytest`, `go test`, `mvn test`, `dotnet test`, `cargo test`
- Verify command is callable (check package.json scripts, Makefile, or CI configs)
- If no test commands are discoverable, set `recommended_test_commands` to empty array and record `note: "No test commands found in repo"`
- MUST emit telemetry event `TEST_DISCOVERY_COMPLETED` with count of test roots and commands found

### 7) Binary assets discovery (universal, binding)
Binary and large artifacts (e.g., `testfiles/`, `assets/`, `.pdf`, `.one`, `.png`, `.zip`) MUST be recorded in:
- `repo_inventory.binary_assets`

Rules:
- Ingestion MUST NOT send binary payloads to LLMs.
- Snippet extraction MUST skip binary files (only reference paths/filenames).
- Writers MAY link to sample files but MUST NOT embed binary contents.

### 8) Extract capabilities and workflows
Parse docs and code to identify:
- what the product does
- top features
- workflows (common user journeys)
- supported formats (if applicable)
- platform constraints
- install and quickstart steps
- explicit limitations (“not supported / not implemented yet”)
- **public vs internal API scope** (when declared, e.g., “only package X is public”)

### 9) Build EvidenceMap (TruthLock-ready)
Every claim that will later appear in content must map to:
- repo path
- commit SHA
- line ranges

---

## Determinism requirements
- Same `github_ref` must produce identical RepoInventory and equivalent ProductFacts.
- Sorting must be stable (paths, lists).
- EvidenceMap claim_id must be stable (see `04_claims_compiler_truth_lock.md`).

---

## Failure modes
- Missing docs: still produce ProductFacts but mark fields as unknown/empty and require writers to avoid those claims.
- Examples absent: writers may generate minimal samples and label as generated, then validate syntax at minimum.
- Contradictory claims: default to higher-priority evidence and consider forcing `launch_tier=minimal`.

---

## Artifacts location
- `runs/<run_id>/work/repo` (clone)
- `runs/<run_id>/artifacts/repo_inventory.json`
- `runs/<run_id>/artifacts/product_facts.json`
- `runs/<run_id>/artifacts/evidence_map.json`

---

## Adapter Selection Algorithm (binding)

After discovery, RepoIngest MUST select an adapter using this deterministic algorithm:

### Algorithm Steps

1. **Determine Platform Family** (see step 2 in main flow):
   - Score each platform based on manifest presence (primary=3, secondary=1)
   - Platform with highest score → `platform_family`
   - Tie-breaking: prefer order `python > node > dotnet > java > go > rust > php`
   - If score < 2 → `platform_family = "unknown"`
   - If multiple platforms score >= 3 → `platform_family = "multi"`

2. **Determine Repo Archetype**:
   ```
   IF src/ exists AND contains language-specific package root:
       archetype = "{platform}_src_{manifest_type}"
       # Examples: python_src_pyproject, node_src_package_json
   ELSE IF flat package root at repo root (setup.py, package.json, etc.):
       archetype = "{platform}_flat_{manifest_type}"
       # Examples: python_flat_setup_py, dotnet_flat_csproj
   ELSE IF multiple package manifests at different levels:
       archetype = "monorepo_multi_package"
   ELSE IF doc_roots present BUT no manifests:
       archetype = "docs_only"
   ELSE:
       archetype = "mixed_unknown"
   ```

3. **Apply Run Config Overrides** (optional):
   - If `run_config.repo_hints.platform_family` present → override platform_family
   - If `run_config.repo_hints.repo_archetype` present → override archetype
   - Record overrides in telemetry event `adapter_selection_override`

4. **Select Adapter**:
   ```
   adapter_key = f"{platform_family}:{repo_archetype}"

   # Lookup in adapter registry (priority order):
   1. Exact match: {platform_family}:{repo_archetype}
   2. Platform fallback: {platform_family}:default
   3. Universal fallback: "universal:best_effort"
   ```

### Adapter Selection Failure Handling (binding)

If adapter selection fails (no exact match, no platform fallback, and universal fallback is not available):
1. Emit telemetry event `ADAPTER_SELECTION_FAILED` with platform_family and repo_archetype
2. Open BLOCKER issue with error_code `REPO_SCOUT_MISSING_ADAPTER`
3. Fail the run with exit code 5 (unexpected internal error)
4. Include in issue.message: "No adapter available for {platform_family}:{repo_archetype}. Add adapter or use repo_hints to override."

The universal fallback adapter MUST always exist and be registered as "universal:best_effort".

5. **Record Selection**:
   - Write `repo_inventory.adapter_selected = adapter_key`
   - Emit telemetry event `adapter_selected` with scores and selection rationale

### Determinism Requirements

- Same repo at same ref MUST select same adapter
- Adapter selection MUST be logged to telemetry
- Selection logic MUST NOT depend on timestamps, environment vars, or random values
- Tie-breaking MUST be deterministic (use defined order)

### Example Adapter Keys

- `python:python_src_pyproject` - Python repo with src/ layout and pyproject.toml
- `python:python_flat_setup_py` - Python repo with setup.py at root
- `node:node_src_package_json` - Node.js repo with src/ layout
- `dotnet:dotnet_flat_csproj` - .NET repo with .csproj at root
- `multi:monorepo_multi_package` - Multi-language monorepo
- `unknown:docs_only` - Documentation-only repo
- `universal:best_effort` - Fallback adapter (minimal extraction)

---

## Adapter Contract (binding)

Adapters MUST expose:
- `extract_distribution()` -> ProductFacts.distribution + runtime_requirements
- `extract_public_api_entrypoints()` -> repo_profile.public_api_entrypoints + ProductFacts.api_surface_summary
- `extract_examples()` -> snippet seed candidates
- `recommended_validation()` -> test commands, lint commands (best effort)

If the adapter cannot determine a fact, it MUST leave it unknown/empty and rely on EvidenceMap + gates to prevent unsupported claims.

**Related specs**:
- [specs/26_repo_adapters_and_variability.md](26_repo_adapters_and_variability.md) - Detailed adapter requirements and outputs
- [specs/27_universal_repo_handling.md](27_universal_repo_handling.md) - Universal repo handling guidelines
